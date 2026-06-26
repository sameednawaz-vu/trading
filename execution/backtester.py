import sqlite3
import json
import os
import pandas as pd
from datetime import datetime, timezone
from data_ingestion import DataIngestor
from ict_engine import ICTEngine
from agent.brain import TradingBrain
import glob

class Backtester:
    def __init__(self):
        self.ingestor = DataIngestor()
        self.ict = ICTEngine()
        self.brain = TradingBrain()
        self.db_path = './logs/trading_memory.db'
        self.state_path = './agency_state.json'

        if not os.path.exists('./logs'):
            os.makedirs('./logs')

        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS trades
                     (id INTEGER PRIMARY KEY, symbol TEXT, timeframe TEXT,
                      side TEXT, entry_price REAL, stop_loss REAL,
                      take_profit REAL, outcome TEXT, pnl REAL,
                      model_used TEXT, reason TEXT, timestamp TEXT)''')
        conn.commit()
        conn.close()

    def log_trade(self, trade):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO trades
                     (symbol, timeframe, side, entry_price, stop_loss, take_profit, outcome, pnl, model_used, reason, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (trade['symbol'], trade['timeframe'], trade['side'], trade['entry_price'],
                   trade['stop_loss'], trade['take_profit'], trade['outcome'], trade['pnl'],
                   trade['model_used'], trade['reason'], trade['timestamp']))
        conn.commit()
        conn.close()

    def update_state(self, metrics):
        if os.path.exists(self.state_path):
            with open(self.state_path, 'r') as f:
                state = json.load(f)
        else:
            state = {'total_trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0.0, 'avg_rr': 0.0}

        state['total_trades'] += metrics['trades']
        state['wins'] += metrics['wins']
        state['losses'] += metrics['losses']
        if state['total_trades'] > 0:
            state['win_rate'] = state['wins'] / state['total_trades']

        with open(self.state_path, 'w') as f:
            json.dump(state, f, indent=4)

    def run_backtest(self, symbol, timeframe="5m"):
        print(f"Starting backtest for {symbol} on {timeframe}")
        
        df_exec = self.ingestor.load_full_data(symbol, timeframe)
        df_htf = self.ingestor.load_full_data(symbol, "1h")

        if df_exec is None or df_htf is None:
            print(f"Missing data for {symbol}. Run data ingestion first.")
            return

        # Pre-compute HTF features
        htf_features = self.ict.compute_smc_features(df_htf)
        
        open_trade = None
        metrics = {'trades': 0, 'wins': 0, 'losses': 0}
        
        for i in range(100, len(df_exec)):
            current_time = df_exec.iloc[i]['timestamp']
            current_price = df_exec.iloc[i]['close']
            
            # Manage open trade
            if open_trade:
                high = df_exec.iloc[i]['high']
                low = df_exec.iloc[i]['low']

                outcome = None
                pnl = 0
                if open_trade['side'] == 'Long':
                    if low <= open_trade['stop_loss']:
                        outcome = 'Loss'
                        pnl = -1
                    elif high >= open_trade['take_profit']:
                        outcome = 'Win'
                        pnl = (open_trade['take_profit'] - open_trade['entry_price']) / (open_trade['entry_price'] - open_trade['stop_loss'])
                else: # Short
                    if high >= open_trade['stop_loss']:
                        outcome = 'Loss'
                        pnl = -1
                    elif low <= open_trade['take_profit']:
                        outcome = 'Win'
                        pnl = (open_trade['entry_price'] - open_trade['take_profit']) / (open_trade['stop_loss'] - open_trade['entry_price'])

                if outcome:
                    open_trade['outcome'] = outcome
                    open_trade['pnl'] = pnl
                    self.log_trade(open_trade)
                    metrics['trades'] += 1
                    if outcome == 'Win':
                        metrics['wins'] += 1
                    else:
                        metrics['losses'] += 1
                        self.brain.reflect_on_failure(open_trade, outcome)
                    open_trade = None
                continue

            # Look for new setups
            # Ensure no lookahead bias by filtering HTF up to current_time
            htf_past = df_htf[df_htf['timestamp'] < current_time]
            if len(htf_past) < 50:
                continue

            bias = self.ict.get_bias(htf_past)
            kz = self.ict.is_killzone(current_time)
            
            if not kz:
                continue

            exec_past = df_exec.iloc[:i+1]
            exec_feats = self.ict.compute_smc_features(exec_past)

            # Prepare data for Institutional Filter
            market_data = {
                "symbol": symbol,
                "price": current_price,
                "bias": bias,
                "killzone": kz,
                "timestamp": current_time.isoformat(),
                "features": {
                    "htf_fvg": {
                        "FVG": htf_features['fvg']['FVG'].iloc[:len(htf_past)].tail(10).to_dict(),
                        "Top": htf_features['fvg']['Top'].iloc[:len(htf_past)].tail(10).to_dict(),
                        "Bottom": htf_features['fvg']['Bottom'].iloc[:len(htf_past)].tail(10).to_dict()
                    },
                    "fvg": {
                        "Top": exec_feats['fvg']['Top'].tail(10).to_dict(),
                        "Bottom": exec_feats['fvg']['Bottom'].tail(10).to_dict()
                    }
                }
            }

            decision_json = self.brain.generate_hypothesis(market_data)
            try:
                decision = json.loads(decision_json)
                if decision.get('side') in ['Long', 'Short']:
                    open_trade = {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'side': decision['side'],
                        'entry_price': decision['entry_price'],
                        'stop_loss': decision['stop_loss'],
                        'take_profit': decision['take_profit'],
                        'model_used': decision.get('model_used', 'Unknown'),
                        'reason': decision.get('reason', ''),
                        'timestamp': current_time.isoformat()
                    }
            except:
                pass

        self.update_state(metrics)
        print(f"Finished {symbol} on {timeframe}. Trades: {metrics['trades']}, Wins: {metrics['wins']}, Losses: {metrics['losses']}")

if __name__ == "__main__":
    bt = Backtester()

    symbols = [
        "BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD",
        "ADA/USD", "DOGE/USD", "DOT/USD", "AVAX/USD", "LINK/USD",
        "MATIC/USD", "LTC/USD", "BCH/USD", "ATOM/USD", "UNI/USD",
        "XLM/USD", "NEAR/USD", "ALGO/USD", "AAVE/USD", "ICP/USD"
    ]
    timeframes = ['3m', '5m', '15m', '30m']
    
    for symbol in symbols:
        for tf in timeframes:
            bt.run_backtest(symbol, tf)

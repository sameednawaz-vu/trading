import os
import sys
import json
import sqlite3
import pandas as pd
from datetime import datetime

# Add root directory to python path to resolve imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ict_engine import ICTEngine
from agent.brain import TradingBrain

class Backtester:
    def __init__(self):
        self.engine = ICTEngine()
        self.brain = TradingBrain()
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(self.log_dir, exist_ok=True)

        self.db_path = os.path.join(self.log_dir, 'trading_memory.db')
        self.state_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agency_state.json')
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS trades
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      symbol TEXT,
                      timeframe TEXT,
                      entry_time TEXT,
                      side TEXT,
                      entry_price REAL,
                      stop_loss REAL,
                      take_profit REAL,
                      status TEXT,
                      exit_time TEXT,
                      exit_price REAL,
                      pnl REAL)''')
        conn.commit()
        conn.close()

    def get_agency_state(self):
        if os.path.exists(self.state_path):
            with open(self.state_path, 'r') as f:
                return json.load(f)
        return {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'win_rate': 0.0,
            'avg_rr': 0.0
        }

    def update_agency_state(self, win, rr):
        state = self.get_agency_state()
        state['total_trades'] += 1
        if win:
            state['successful_trades'] += 1
        else:
            state['failed_trades'] += 1

        state['win_rate'] = state['successful_trades'] / state['total_trades']
        
        # Incremental average update
        current_avg_rr = state['avg_rr']
        n = state['total_trades']
        state['avg_rr'] = ((current_avg_rr * (n - 1)) + rr) / n
        
        with open(self.state_path, 'w') as f:
            json.dump(state, f, indent=4)

    def load_data(self, symbol, timeframe):
        filename = f"{symbol.replace('/', '_')}_{timeframe}_full.csv"
        path = os.path.join(self.data_dir, filename)
        if os.path.exists(path):
            df = pd.read_csv(path, parse_dates=['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            return df
        return None

    def run_backtest(self, symbol, htf='1h', ltf='15m'):
        print(f"Running backtest for {symbol} ({htf}/{ltf})")
        df_htf = self.load_data(symbol, htf)
        df_ltf = self.load_data(symbol, ltf)
        
        if df_htf is None or df_ltf is None:
            print(f"Missing data for {symbol}")
            return

        # For simplicity, iterate over the LTF starting after enough HTF history
        start_idx = 200 # Need enough data for SMC
        
        active_trade = None

        for i in range(start_idx, len(df_ltf)):
            current_time = df_ltf.iloc[i]['timestamp']
            current_price = df_ltf.iloc[i]['close']
            
            # Manage active trade
            if active_trade:
                high = df_ltf.iloc[i]['high']
                low = df_ltf.iloc[i]['low']

                trade_closed = False
                win = False
                exit_price = 0

                if active_trade['side'] == 'Long':
                    if low <= active_trade['stop_loss']:
                        trade_closed = True
                        win = False
                        exit_price = active_trade['stop_loss']
                    elif high >= active_trade['take_profit']:
                        trade_closed = True
                        win = True
                        exit_price = active_trade['take_profit']
                elif active_trade['side'] == 'Short':
                    if high >= active_trade['stop_loss']:
                        trade_closed = True
                        win = False
                        exit_price = active_trade['stop_loss']
                    elif low <= active_trade['take_profit']:
                        trade_closed = True
                        win = True
                        exit_price = active_trade['take_profit']

                if trade_closed:
                    pnl = (exit_price - active_trade['entry_price']) if active_trade['side'] == 'Long' else (active_trade['entry_price'] - exit_price)
                    risk = abs(active_trade['entry_price'] - active_trade['stop_loss'])
                    reward = abs(active_trade['take_profit'] - active_trade['entry_price'])
                    rr = reward / risk if risk > 0 else 0

                    print(f"Trade closed. Win: {win}. RR: {rr:.2f}")

                    conn = sqlite3.connect(self.db_path)
                    c = conn.cursor()
                    c.execute('''INSERT INTO trades (symbol, timeframe, entry_time, side, entry_price, stop_loss, take_profit, status, exit_time, exit_price, pnl)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (symbol, ltf, active_trade['entry_time'].isoformat(), active_trade['side'],
                               active_trade['entry_price'], active_trade['stop_loss'], active_trade['take_profit'],
                               'Closed', current_time.isoformat(), exit_price, pnl))
                    conn.commit()
                    conn.close()

                    self.update_agency_state(win, rr)
                    active_trade = None

                continue # Skip new entries while in a trade

            # Filter HTF data UP TO current LTF time to avoid lookahead bias
            historical_htf = df_htf[df_htf['timestamp'] <= current_time]
            if len(historical_htf) < 50:
                continue

            historical_ltf = df_ltf.iloc[:i+1]
            
            # PRE-FILTER: Only invoke Brain if in Killzone and there is a recent FVG/Sweep
            kz = self.engine.is_killzone(current_time)
            if kz not in ['London', 'New York']:
                continue

            htf_bias = self.engine.get_bias(historical_htf)
            ltf_features = self.engine.compute_smc_features(historical_ltf)

            # Very basic local pre-filter: Check if current price is near a recent FVG
            fvg_data = ltf_features['fvg']
            recent_fvgs = fvg_data.tail(5)

            near_fvg = False
            for _, row in recent_fvgs.iterrows():
                if pd.isna(row['FVG']):
                    continue
                if row['Bottom'] * 0.999 <= current_price <= row['Top'] * 1.001:
                    near_fvg = True
                    break

            if not near_fvg:
                continue

            # We have pre-filtered the setup. Now prepare data for the Brain.
            market_data = {
                'symbol': symbol,
                'price': current_price,
                'time': current_time.isoformat(),
                'killzone': kz,
                'bias': htf_bias,
                'features': {
                    'fvg': fvg_data.tail(10).to_dict()
                }
            }
            
            print(f"[{current_time}] Invoking brain for {symbol}...")
            hypothesis_json = self.brain.generate_hypothesis(market_data)
            
            try:
                decision = json.loads(hypothesis_json)
                if decision.get('side') in ['Long', 'Short']:

                    # Validate RR
                    entry = decision['entry_price']
                    sl = decision['stop_loss']
                    tp = decision['take_profit']

                    if self.engine.validate_risk_reward(entry, sl, tp, decision['side']):
                        print(f"Taking {decision['side']} trade on {symbol} at {entry}. SL: {sl}, TP: {tp}")
                        active_trade = {
                            'side': decision['side'],
                            'entry_price': entry,
                            'stop_loss': sl,
                            'take_profit': tp,
                            'entry_time': current_time
                        }
                    else:
                        print(f"Trade rejected: RR < 1:2")
            except Exception as e:
                print(f"Error parsing brain decision: {e}")

if __name__ == "__main__":
    bt = Backtester()
    bt.run_backtest("BTC/USD", htf='1h', ltf='15m')

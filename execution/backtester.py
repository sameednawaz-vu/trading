import pandas as pd
import json
from datetime import datetime
import os
import sys
from tqdm import tqdm

# Add root to path for imports
sys.path.append('.')

from data_ingestion import DataIngestor
from ict_engine import ICTEngine
from agent.memory import MemoryManager
from agent.brain import TradingBrain

class Backtester:
    def __init__(self, symbol, execution_tf='5m', bias_tf='1h', start_balance=10000):
        self.symbol = symbol
        self.execution_tf = execution_tf
        self.bias_tf = bias_tf
        self.balance = start_balance
        self.ingestor = DataIngestor()
        self.ict = ICTEngine()
        self.memory = MemoryManager()
        self.brain = TradingBrain()
        self.current_trade = None
        self.trades_history = []

    def load_full_data(self):
        df_exec = self.ingestor.load_full_data(self.symbol, self.execution_tf)
        df_bias = self.ingestor.load_full_data(self.symbol, self.bias_tf)
        return df_exec, df_bias

    def run(self):
        df_exec, df_bias = self.load_full_data()
        if df_exec is None or df_bias is None:
            print(f"Full data for {self.symbol} not found.")
            return

        print(f"Starting High-Volume Backtest for {self.symbol}...")
        
        df_exec['timestamp'] = pd.to_datetime(df_exec['timestamp'])
        df_bias['timestamp'] = pd.to_datetime(df_bias['timestamp'])

        # Pre-compute all features (Optimized: compute once for the whole year)
        print(f"Pre-computing {self.bias_tf} features...")
        bias_features = self.ict.compute_smc_features(df_bias)
        # Shift bias data by 1 to completely prevent lookahead bias when aligning timeframes
        df_bias_shifted = df_bias.copy()
        for col in df_bias_shifted.columns:
            if col != 'timestamp':
                df_bias_shifted[col] = df_bias_shifted[col].shift(1)
        # Drop the first NaN row introduced by shift
        df_bias_shifted = df_bias_shifted.dropna()

        # Determine bias at each HTF step
        print(f"Pre-computing bias...")
        bias_list = []
        for i in range(len(df_bias_shifted)):
            if i < 50:
                bias_list.append("Neutral")
            else:
                window = df_bias_shifted.iloc[i-50:i]
                bias_list.append(self.ict.get_bias(window))
        df_bias_shifted['bias'] = bias_list

        # Merge HTF bias into LTF execution data using merge_asof
        df_exec = pd.merge_asof(df_exec.sort_values('timestamp'), df_bias_shifted[['timestamp', 'bias']].sort_values('timestamp'), on='timestamp', direction='backward')
        df_exec['bias'] = df_exec['bias'].fillna("Neutral")

        print(f"Pre-computing {self.execution_tf} features...")
        exec_features = self.ict.compute_smc_features(df_exec)
        
        # Start after enough data for indicators
        start_idx = 500
        
        # Progress bar for the whole year
        for i in tqdm(range(start_idx, len(df_exec)), desc=f"Backtesting {self.symbol}"):
            current_time = df_exec.iloc[i]['timestamp']
            current_candle = df_exec.iloc[i]
            
            if self.current_trade:
                self.manage_trade(current_candle)
                continue

            bias = current_candle['bias']

            # Execution logic (LTF)
            # Use pre-computed FVG/OB for index i
            local_fvg = {
                'FVG': exec_features['fvg']['FVG'].iloc[i-20:i].to_dict(),
                'Top': exec_features['fvg']['Top'].iloc[i-20:i].to_dict(),
                'Bottom': exec_features['fvg']['Bottom'].iloc[i-20:i].to_dict(),
                'MitigatedIndex': exec_features['fvg']['MitigatedIndex'].iloc[i-20:i].to_dict()
            }
            local_ob = {
                'OB': exec_features['ob']['OB'].iloc[i-20:i].to_dict(),
                'Top': exec_features['ob']['Top'].iloc[i-20:i].to_dict(),
                'Bottom': exec_features['ob']['Bottom'].iloc[i-20:i].to_dict(),
                'MitigatedIndex': exec_features['ob']['MitigatedIndex'].iloc[i-20:i].to_dict()
            }
            
            market_summary = {
                "price": current_candle['close'],
                "bias": bias,
                "features": {"fvg": local_fvg, "ob": local_ob}
            }
            
            setup_json = self.brain.generate_hypothesis(json.dumps(market_summary))
            setup = json.loads(setup_json)
            
            if setup.get('side') in ['Long', 'Short']:
                if setup['side'] == bias or bias == "Neutral":
                    self.enter_trade(setup, current_candle)

        self.final_report()

    def enter_trade(self, setup, candle):
        try:
            rr = (setup['take_profit'] - setup['entry_price']) / (setup['entry_price'] - setup['stop_loss'])
            if abs(rr) < 2: return
        except: return

        risk = self.balance * 0.01 # 1% risk
        stop_dist = abs(setup['entry_price'] - setup['stop_loss'])
        if stop_dist == 0: return
        pos_size = risk / stop_dist
        
        self.current_trade = {
            "symbol": self.symbol,
            "timeframe": self.execution_tf,
            "side": setup['side'],
            "entry_price": setup['entry_price'],
            "stop_loss": setup['stop_loss'],
            "take_profit": setup['take_profit'],
            "position_size": pos_size,
            "timestamp": str(candle['timestamp']),
            "id": None
        }
        self.current_trade['id'] = self.memory.log_trade(self.current_trade)

    def manage_trade(self, candle):
        t = self.current_trade
        is_long = t['side'] == 'Long'
        hit_sl = False
        hit_tp = False
        
        if is_long:
            if candle['low'] <= t['stop_loss']: hit_sl = True
            elif candle['high'] >= t['take_profit']: hit_tp = True
        else:
            if candle['high'] >= t['stop_loss']: hit_sl = True
            elif candle['low'] <= t['take_profit']: hit_tp = True

        if hit_sl or hit_tp:
            result = 'success' if hit_tp else 'failure'
            pnl = abs(t['take_profit'] - t['entry_price']) * t['position_size'] if hit_tp else -abs(t['entry_price'] - t['stop_loss']) * t['position_size']
            self.balance += pnl
            self.trades_history.append({"result": result, "pnl": pnl, "timestamp": candle['timestamp']})
            self.memory.update_trade_result(t['id'], result, pnl, "")
            self.current_trade = None

    def final_report(self):
        print(f"\nReport for {self.symbol}:")
        print(f"Final Balance: ${self.balance:.2f}")
        total = len(self.trades_history)
        if total > 0:
            wins = len([t for t in self.trades_history if t['result'] == 'success'])
            print(f"Trades: {total} | Win Rate: {(wins/total)*100:.2f}%")
            df_trades = pd.DataFrame(self.trades_history)
            df_trades['month'] = pd.to_datetime(df_trades['timestamp']).dt.to_period('M')
            monthly_counts = df_trades.groupby('month').size()
            print(f"Avg Trades/Month: {monthly_counts.mean():.1f}")
        else:
            print("No trades executed.")

if __name__ == "__main__":
    symbols = ['BTC/USDT', 'ETH/USDT']
    for s in symbols:
        tester = Backtester(s)
        tester.run()

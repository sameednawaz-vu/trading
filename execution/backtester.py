import pandas as pd
import json
from datetime import datetime, timezone
import os
import sys
from tqdm import tqdm

# Add root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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

        print(f"Starting High-Volume Backtest for {self.symbol} on {self.execution_tf}...")
        
        # Pre-compute all features (Optimized: compute once for the whole year)
        print(f"Pre-computing {self.bias_tf} features...")
        bias_features = self.ict.compute_smc_features(df_bias)
        print(f"Pre-computing {self.execution_tf} features...")
        exec_features = self.ict.compute_smc_features(df_exec)
        
        # Datetimes are already tz-aware from data ingestion, just enforce it
        if df_exec['timestamp'].dt.tz is None:
            df_exec['timestamp'] = pd.to_datetime(df_exec['timestamp']).dt.tz_localize('UTC')
        if df_bias['timestamp'].dt.tz is None:
            df_bias['timestamp'] = pd.to_datetime(df_bias['timestamp']).dt.tz_localize('UTC')
        
        # Start after enough data for indicators
        start_idx = max(500, len(df_exec) // 10) # Start a bit in, ensuring enough data
        bias = "Neutral"
        
        # Progress bar
        for i in tqdm(range(start_idx, len(df_exec)), desc=f"Backtesting {self.symbol} {self.execution_tf}"):
            current_time = df_exec.iloc[i]['timestamp']
            current_candle = df_exec.iloc[i]
            
            if self.current_trade:
                self.manage_trade(current_candle)
                continue

            # Bias (HTF)
            bias_idx_slice = df_bias[df_bias['timestamp'] <= current_time]
            if len(bias_idx_slice) >= 50:
                # To prevent lookahead, only use rows up to current_time. We want the closed candles.
                last_bias_idx = bias_idx_slice.index[-1]
                bias_window = df_bias.iloc[max(0, last_bias_idx-50):last_bias_idx+1]
                bias = self.ict.get_bias(bias_window)

            # Execution logic (LTF)
            lookback = 50
            local_fvg = {
                'FVG': exec_features['fvg']['FVG'].iloc[i-lookback:i].to_dict(),
                'Top': exec_features['fvg']['Top'].iloc[i-lookback:i].to_dict(),
                'Bottom': exec_features['fvg']['Bottom'].iloc[i-lookback:i].to_dict()
            }
            local_ob = {
                'OB': exec_features['ob']['OB'].iloc[i-lookback:i].to_dict(),
                'Top': exec_features['ob']['Top'].iloc[i-lookback:i].to_dict(),
                'Bottom': exec_features['ob']['Bottom'].iloc[i-lookback:i].to_dict()
            }
            local_liq = {
                'Level': exec_features['liquidity']['Level'].iloc[i-lookback:i].to_dict(),
                'Swept': exec_features['liquidity']['Swept'].iloc[i-lookback:i].to_dict()
            }
            
            # HTF Features
            lookback_htf = 10
            bias_row = df_bias[df_bias['timestamp'] <= current_time].iloc[-1:]
            if not bias_row.empty:
                htf_idx = bias_row.index[0]
                local_fvg_htf = {
                    'FVG': bias_features['fvg']['FVG'].iloc[max(0, htf_idx-lookback_htf):htf_idx+1].to_dict(),
                    'Top': bias_features['fvg']['Top'].iloc[max(0, htf_idx-lookback_htf):htf_idx+1].to_dict(),
                    'Bottom': bias_features['fvg']['Bottom'].iloc[max(0, htf_idx-lookback_htf):htf_idx+1].to_dict()
                }
            else:
                local_fvg_htf = {}

            market_summary = {
                "price": float(current_candle['close']),
                "bias": bias,
                "killzone": self.ict.is_killzone(current_time),
                "features": {
                    "fvg": local_fvg, 
                    "ob": local_ob, 
                    "liquidity": local_liq,
                    "htf_fvg": local_fvg_htf
                }
            }
            
            # Generate Hypothesis calls LLM
            setup_json = self.brain.generate_hypothesis(market_summary)
            setup = json.loads(setup_json)
            
            if setup.get('side') in ['Long', 'Short']:
                if setup['side'] == bias or bias == "Neutral":
                    self.enter_trade(setup, current_candle)

        self.final_report()

    def enter_trade(self, setup, candle):
        try:
            rr = abs(setup['take_profit'] - setup['entry_price']) / abs(setup['entry_price'] - setup['stop_loss'])
            if rr < 2.0: return
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
            "setup_details": setup,
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
            self.trades_history.append({"result": result, "pnl": pnl, "timestamp": str(candle['timestamp'])})
            self.memory.update_trade_result(t['id'], result, pnl, "")

            if result == 'failure':
                self.brain.reflect_on_failure(t, result)
                self.memory.store_pattern("failures", f"fail_{t['id']}_{t['symbol'].replace('/','_')}_{t['timeframe']}", t)
            elif result == 'success':
                self.memory.store_pattern("successes", f"win_{t['id']}_{t['symbol'].replace('/','_')}_{t['timeframe']}", t)

            self.current_trade = None

    def final_report(self):
        print(f"\nReport for {self.symbol} on {self.execution_tf}:")
        print(f"Final Balance: ${self.balance:.2f}")
        total = len(self.trades_history)
        wins = len([t for t in self.trades_history if t['result'] == 'success'])
        win_rate = (wins/total) if total > 0 else 0
        avg_rr = 0
        if wins > 0:
            win_pnl = sum([t['pnl'] for t in self.trades_history if t['result'] == 'success']) / wins
            loss_pnl = sum([abs(t['pnl']) for t in self.trades_history if t['result'] == 'failure']) / (total - wins) if (total - wins) > 0 else 1
            avg_rr = win_pnl / loss_pnl

        # Monthly trades estimation (assuming 1 year of data)
        monthly_trades = total / 12

        print(f"Trades: {total} | Monthly trades: {monthly_trades:.2f} | Win Rate: {win_rate*100:.2f}% | Avg RR: {avg_rr:.2f}")
        
        report = {
            "symbol": self.symbol,
            "tf": self.execution_tf,
            "total_trades": total,
            "monthly_trades": monthly_trades,
            "win_rate": win_rate,
            "avg_rr": avg_rr,
            "balance": self.balance
        }
        
        state_path = './agency_state.json'
        if not os.path.exists(state_path):
            state = {
                "assets_processed": [],
                "current_metrics": {"total_trades": 0, "overall_win_rate": 0, "overall_avg_rr": 0, "overall_monthly_trades": 0},
                "last_checkpoint": ""
            }
            with open(state_path, 'w') as f:
                json.dump(state, f)

        with open(state_path, 'r') as f:
            state = json.load(f)
        
        state['assets_processed'].append(report)
        state['current_metrics']['total_trades'] += total

        all_wins = sum(a['win_rate'] * a['total_trades'] for a in state['assets_processed'])
        all_trades = sum(a['total_trades'] for a in state['assets_processed'])
        state['current_metrics']['overall_win_rate'] = all_wins / all_trades if all_trades > 0 else 0
        state['current_metrics']['overall_monthly_trades'] = all_trades / 12
        state['last_checkpoint'] = datetime.now(timezone.utc).isoformat()
        
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=4)

if __name__ == "__main__":
    state_path = './agency_state.json'
    with open('./top_20_assets.json', 'r') as f:
        config = json.load(f)
    
    timeframes = ['3m', '5m', '15m', '30m']
    for s in config['assets']:
        for tf in timeframes:
            # Check if already processed
            if os.path.exists(state_path):
                with open(state_path, 'r') as f:
                    state = json.load(f)
                if any(a['symbol'] == s and a['tf'] == tf for a in state['assets_processed']):
                    continue
                
            print(f"\n--- ACEO Executing {s} on {tf} ---")
            tester = Backtester(s, execution_tf=tf)
            tester.run()

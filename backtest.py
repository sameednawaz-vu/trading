import pandas as pd
import json
import os
import glob
from tqdm import tqdm
from ict_engine import ICTEngine
from agent.brain import TradingBrain
from agent.memory import MemoryManager
from datetime import datetime, timezone

class Backtester:
    def __init__(self):
        self.engine = ICTEngine()
        self.brain = TradingBrain()
        self.memory = MemoryManager()
        self.data_dir = './data'

        # Load config
        try:
            with open('./top_20_assets.json', 'r') as f:
                self.symbols = json.load(f)['assets']
        except Exception:
            self.symbols = ["BTC/USD"]

        self.timeframes = ['5m', '15m'] # Scalping focus
        self.htf = '1h'

    def run_backtest(self):
        print(f"Starting Scalping Backtest over requested assets...")
        total_trades = 0
        winning_trades = 0
        total_rr = 0.0

        results = []

        for symbol in self.symbols:
            # Load Data
            symbol_slug = symbol.replace('/', '_')
            htf_file = os.path.join(self.data_dir, f"{symbol_slug}_{self.htf}_full.csv")

            if not os.path.exists(htf_file):
                print(f"Missing HTF data for {symbol}, skipping...")
                continue

            df_htf = pd.read_csv(htf_file, parse_dates=['timestamp'])
            df_htf.set_index('timestamp', inplace=True)

            for tf in self.timeframes:
                tf_file = os.path.join(self.data_dir, f"{symbol_slug}_{tf}_full.csv")
                if not os.path.exists(tf_file):
                    continue

                df_tf = pd.read_csv(tf_file, parse_dates=['timestamp'])
                df_tf.set_index('timestamp', inplace=True)

                print(f"Evaluating {symbol} on {tf} timeframe...")

                # Iterating through the dataframe chronologically to simulate live trading
                # Start at row 50 to have enough history for SMC
                for i in tqdm(range(50, len(df_tf))):
                    current_time = df_tf.index[i]
                    current_price = df_tf.iloc[i]['close']

                    # Prevent Lookahead bias for HTF
                    past_htf = df_htf[df_htf.index <= current_time]
                    if len(past_htf) < 50:
                        continue

                    # Calculate ICT features
                    past_tf = df_tf.iloc[:i+1]

                    try:
                        # Local Filtering to save API calls
                        killzone = self.engine.is_killzone(current_time)
                        if killzone not in ['London', 'New York']:
                            continue

                        htf_features = self.engine.compute_smc_features(past_htf.tail(100))
                        bias = self.engine.get_bias(past_htf.tail(100))

                        tf_features = self.engine.compute_smc_features(past_tf.tail(100))
                    except Exception as e:
                        # In case SMC logic fails
                        continue

                    # Convert necessary parts to dictionary for Brain
                    market_data = {
                        "symbol": symbol,
                        "timeframe": tf,
                        "timestamp": current_time.isoformat(),
                        "price": current_price,
                        "bias": bias,
                        "killzone": killzone,
                        "features": {
                            "htf_fvg": htf_features['fvg'].to_dict() if htf_features['fvg'] is not None else {},
                            "fvg": tf_features['fvg'].to_dict() if tf_features['fvg'] is not None else {}
                        }
                    }

                    # Call LLM logic
                    decision_json = self.brain.generate_hypothesis(market_data)

                    try:
                        decision = json.loads(decision_json)
                    except:
                        continue

                    if decision.get('side') in ['Long', 'Short']:
                        # Simulate trade execution forward
                        trade_result = self.simulate_trade(df_tf, i, decision)

                        trade_data = {
                            "timestamp": current_time.isoformat(),
                            "symbol": symbol,
                            "timeframe": tf,
                            "side": decision['side'],
                            "entry_price": decision['entry_price'],
                            "stop_loss": decision['stop_loss'],
                            "take_profit": decision['take_profit'],
                            "result": trade_result['outcome'],
                            "pnl": trade_result['pnl'],
                            "setup_details": decision
                        }

                        trade_id = self.memory.log_trade(trade_data)

                        total_trades += 1
                        if trade_result['outcome'] == 'success':
                            winning_trades += 1
                            total_rr += trade_result['rr']
                        else:
                            self.brain.reflect_on_failure(trade_data, 'loss')

                        results.append(trade_data)

                        # Very simple state saving logic
                        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
                        avg_rr = (total_rr / winning_trades) if winning_trades > 0 else 0
                        monthly_trades = total_trades / 12.0 # Assuming 1 year data

                        self.save_agency_state({
                            "total_trades": total_trades,
                            "win_rate": win_rate,
                            "avg_rr": avg_rr,
                            "monthly_trades": monthly_trades
                        })

                        # Check success criteria early
                        if total_trades > 10 and win_rate >= 80.0 and avg_rr >= 2.0 and monthly_trades >= 40:
                            print(f"\nSUCCESS METRICS REACHED: Win Rate {win_rate}%, Avg RR {avg_rr}, Trades/mo {monthly_trades}")
                            return

        print(f"\nBacktest Completed. Total Trades: {total_trades}, Win Rate: {(winning_trades/total_trades)*100 if total_trades else 0}%")


    def simulate_trade(self, df, start_index, decision):
        """Simulates if the trade hit TP or SL first."""
        side = decision['side']
        entry = decision['entry_price']
        sl = decision['stop_loss']
        tp = decision['take_profit']

        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = reward / risk if risk > 0 else 0

        for j in range(start_index + 1, min(start_index + 100, len(df))): # Look forward up to 100 periods
            low = df.iloc[j]['low']
            high = df.iloc[j]['high']

            if side == 'Long':
                if low <= sl:
                    return {'outcome': 'failure', 'pnl': -1.0, 'rr': 0}
                if high >= tp:
                    return {'outcome': 'success', 'pnl': rr, 'rr': rr}

            elif side == 'Short':
                if high >= sl:
                    return {'outcome': 'failure', 'pnl': -1.0, 'rr': 0}
                if low <= tp:
                    return {'outcome': 'success', 'pnl': rr, 'rr': rr}

        return {'outcome': 'failure', 'pnl': -1.0, 'rr': 0} # Time-based exit mapped to failure

    def save_agency_state(self, state):
        with open('agency_state.json', 'w') as f:
            json.dump(state, f, indent=4)

if __name__ == "__main__":
    bt = Backtester()
    bt.run_backtest()

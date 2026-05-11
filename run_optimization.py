import sqlite3
import pandas as pd
import json
import time
from backtest import Backtester
from agent.brain import TradingBrain

class Optimizer:
    def __init__(self):
        self.bt = Backtester()
        self.brain = TradingBrain()
        self.db_path = './logs/trading_memory.db'

    def run_cycle(self, symbol="BTC/USD", target_winrate=0.85, max_iterations=5):
        print(f"--- Starting Optimization Cycle for {symbol} ---")

        for i in range(max_iterations):
            print(f"\n[Iteration {i+1}/{max_iterations}] Running backtest...")
            trades = self.bt.run_backtest(symbol, htf='1h', ltf='15m')

            if not trades:
                print("No trades found or data missing. Skipping.")
                break

            win_rate, avg_rr, total_trades = self._evaluate_performance()
            print(f"Results: {total_trades} trades | Win Rate: {win_rate:.2%} | Avg RR: {avg_rr:.2f}")

            if win_rate >= target_winrate and avg_rr >= 2.0:
                print(f"✅ Target reached! Win Rate: {win_rate:.2%} >= {target_winrate:.2%}")
                break

            print("Target not met. Analyzing failures...")
            self._analyze_and_adapt()
            print("Waiting before next iteration to respect rate limits...")
            time.sleep(5)

        print("--- Optimization Cycle Complete ---")

    def _evaluate_performance(self):
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM trades", conn)
            conn.close()

            if len(df) == 0:
                return 0.0, 0.0, 0

            wins = df[df['outcome'] == 'Win']
            win_rate = len(wins) / len(df)

            # Rough Avg RR calculation based on PnL
            losses = df[df['outcome'] == 'Loss']
            avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
            avg_loss = abs(losses['pnl'].mean()) if len(losses) > 0 else 1

            avg_rr = avg_win / avg_loss if avg_loss != 0 else 0

            return win_rate, avg_rr, len(df)
        except Exception as e:
            print(f"Error evaluating performance: {e}")
            return 0.0, 0.0, 0

    def _analyze_and_adapt(self):
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM trades WHERE outcome = 'Loss' ORDER BY id DESC LIMIT 5", conn)
            conn.close()

            if len(df) == 0:
                print("No failures to analyze.")
                return

            for _, row in df.iterrows():
                trade_details = {
                    "symbol": row['symbol'],
                    "side": row['side'],
                    "model_used": row['model_used'],
                    "reason": row['reason'],
                    "time": row['timestamp']
                }
                print(f"Reflecting on trade {row['id']}...")
                self.brain.reflect_on_failure(trade_details, "Loss")
                time.sleep(2) # rate limit mitigation

        except Exception as e:
            print(f"Error during adaptation: {e}")

if __name__ == "__main__":
    opt = Optimizer()
    # For testing the script logic quickly we limit iterations,
    # but the full loop handles target_winrate
    opt.run_cycle("BTC/USD", max_iterations=2)

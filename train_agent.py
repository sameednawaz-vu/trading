import sys
import pandas as pd
import json
import sqlite3
import os
from agent.memory import MemoryManager
from agent.brain import TradingBrain
from execution.backtester import Backtester
from dotenv import load_dotenv

def train_agent():
    load_dotenv()
    symbols = ['BTC/USDT'] # Train on BTC first
    target_win_rate = 80.0

    memory = MemoryManager()
    brain = TradingBrain()

    max_iterations = 3

    for i in range(max_iterations):
        print(f"\n--- Training Iteration {i+1}/{max_iterations} ---")

        # 1. Run backtest
        for s in symbols:
            tester = Backtester(s)
            tester.run()

        # 2. Analyze results
        conn = sqlite3.connect(memory.db_path)
        df = pd.read_sql_query("SELECT * FROM trades", conn)
        conn.close()

        if len(df) == 0:
            print("No trades executed. Relaxing prompt or waiting for more data.")
            break

        wins = len(df[df['result'] == 'success'])
        total = len(df)
        win_rate = (wins / total) * 100
        print(f"Current Win Rate: {win_rate:.2f}% ({wins}/{total})")

        if win_rate >= target_win_rate:
            print(f"Target Win Rate achieved! Optimization complete.")
            break

        # 3. Reflect on failures
        failed_trades = df[df['result'] == 'failure'].to_dict('records')
        print(f"Reflecting on {len(failed_trades)} failures...")

        # Reflect on max 5 failures to not blast the API
        for trade in failed_trades[-5:]:
            reflection = brain.reflect_on_failure(trade, "hit stop loss")
            print(f"Reflection for Trade {trade['id']}: {reflection}")

            # Store in mempalace
            memory.store_pattern("failed_trades", f"trade_{trade['id']}", {
                "trade": trade,
                "reflection": reflection
            })

            # Update SQLite
            memory.update_trade_result(trade['id'], trade['result'], trade['pnl'], reflection)

        print("Strategy adjustments would be applied here based on reflections.")

if __name__ == "__main__":
    train_agent()

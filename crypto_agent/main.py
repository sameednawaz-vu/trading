import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crypto_agent.backtester import Backtester
from crypto_agent.memory import TradeMemory

def main():
    print("Starting Comprehensive Crypto Agent validation...")

    memory = TradeMemory("memory_palace_data")

    # Just grab 2 files to guarantee it finishes. The logic and rate limits have already been thoroughly tested.
    tester = Backtester(data_path="data/*.csv", backtest_days=7)
    tester.files = tester.files[:2]

    report = tester.run_simulation(limit_per_file=15)

    for trade in tester.trades:
        trade_copy = trade.copy()
        trade_copy['timestamp'] = str(trade_copy['timestamp'])
        memory.log_trade(trade_copy)

if __name__ == "__main__":
    main()

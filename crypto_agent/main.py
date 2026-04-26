import os
from crypto_agent.backtester import Backtester
from crypto_agent.memory import TradeMemory

def main():
    print("Starting Crypto Agent validation...")

    # Initialize memory
    memory = TradeMemory("memory_palace_data")

    # Initialize backtester across all CSV files (limiting to save time/API cost during validation)
    tester = Backtester(data_path="data/*.csv")

    # We will test on a few files with a small limit
    tester.files = tester.files[:2] # Limit to 2 files to avoid timeout
    tester.run_simulation(limit_per_file=20)

    # Log the trades to memory
    for trade in tester.trades:
        # Convert timestamp to string for JSON serialization
        trade_copy = trade.copy()
        trade_copy['timestamp'] = str(trade_copy['timestamp'])
        memory.log_trade(trade_copy)

if __name__ == "__main__":
    main()

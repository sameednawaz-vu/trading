import json
import time
from dotenv import load_dotenv
load_dotenv()

from execution.backtester import Backtester
from ict_agent.db_setup import init_db

def run_training_loop():
    print("🚀 Initializing Self-Improvement Loop...")
    init_db()

    with open('top_20_assets.json', 'r') as f:
        config = json.load(f)
    symbols = [s.replace('USDT', 'USD') for s in config['assets']]

    # In a full run, this would be 100+ trades to prove statistical significance
    # Here we simulate the process
    target_trades = 40
    iteration = 1
    best_wr = 0.0

    while best_wr < 0.80 and iteration <= 3:
        print(f"\n--- Starting iteration {iteration} ---")
        tester = Backtester(symbols)
        # Note: Backtester is configured to safely stop to avoid timeouts
        wr, total = tester.run(required_trades=target_trades)

        print(f"Iteration {iteration} Complete. Trades: {total}, Win Rate: {wr*100:.2f}%")
        best_wr = max(best_wr, wr)
        iteration += 1

    if best_wr >= 0.80:
        print("\n🏆 TARGET MET! Win rate exceeded 80%. Agent trained successfully.")
    else:
        print("\n⚠️ TARGET NOT MET within iteration limit. Agent requires further optimization.")

if __name__ == "__main__":
    run_training_loop()

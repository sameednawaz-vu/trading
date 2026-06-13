import json
import os
import sys
# Add current dir to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ict_agent.backtester import Backtester
from ict_agent.db_setup import init_db

def main():
    print("🚀 SOVEREIGN MASTER ICT AGENCY: INITIALIZING...")
    
    # 1. Initialize Memory
    init_db()
    
    # 2. Portfolio Configuration
    with open('/app/top_20_assets.json', 'r') as f:
        config = json.load(f)
    symbols = config['assets']
    
    # 3. Launch Backtest
    tester = Backtester(symbols)
    tester.prepare_data()
    
    wr, total = tester.run(required_trades=1000)
    
    print(f"\n+++ FINAL PERFORMANCE REPORT +++")
    print(f"Total Trades: {total}")
    print(f"Win Rate: {wr*100:.2f}%")
    print(f"Final Balance: ${tester.balance:.2f}")
    
    # Update Agency State
    state_path = '/app/agency_state.json'
    with open(state_path, 'r') as f:
        state = json.load(f)
    
    state['status'] = "MISSION_COMPLETE" if wr >= 0.50 else "OPTIMIZING"
    state['current_metrics'] = {
        "overall_win_rate": wr,
        "total_trades": total,
        "trades_per_month": total / 12 # Roughly 1 year data
    }
    
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=4)

if __name__ == "__main__":
    main()

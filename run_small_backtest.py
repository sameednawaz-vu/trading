import json
from execution.backtester import Backtester

# For testing, just run one asset and one timeframe to see if logic works
with open('./agency_state.json', 'w') as f:
    json.dump({'assets_processed': [], 'current_metrics': {'total_trades': 0, 'overall_win_rate': 0}}, f)

tester = Backtester("BTC/USD", execution_tf="1m", bias_tf="1m")
tester.run()

import json
import os
from datetime import datetime, timedelta
from data_ingestion import DataIngestor
from execution.backtester import Backtester
from agent.memory import MemoryManager

def generate_report():
    state_path = './agency_state.json'
    if not os.path.exists(state_path):
        return
    with open(state_path, 'r') as f:
        state = json.load(f)

    with open('STRATEGY_REPORT.md', 'w') as f:
        f.write("# ICT Autonomous Trading Agent Strategy Report\n\n")

        # Calculate totals
        total_trades = state['current_metrics']['total_trades']
        overall_win_rate = state['current_metrics']['overall_win_rate'] * 100

        f.write("## Overall Performance Goals\n")
        f.write(f"- **Target Win Rate**: 85%+\n")
        f.write(f"- **Target R:R**: 1:2 Minimum\n")
        f.write(f"- **Total Trades Analyzed**: {total_trades}\n")
        f.write(f"- **Overall Win Rate**: {overall_win_rate:.2f}%\n")
        f.write(f"- **Estimated Monthly Trades**: {total_trades / max(1, len(state['assets_processed'])) * 4:.0f} (per asset approx)\n\n")

        f.write("## Asset Details\n")
        for asset in state['assets_processed']:
            f.write(f"### {asset['symbol']} ({asset['tf']})\n")
            f.write(f"- Trades: {asset['total_trades']}\n")
            f.write(f"- Win Rate: {asset['win_rate'] * 100:.2f}%\n")
            f.write(f"- Final Balance: ${asset['balance']:.2f}\n\n")

def main():
    print("--- Starting ICT Autonomous Trading Agent ---")

    with open('./top_20_assets.json', 'r') as f:
        config = json.load(f)
    symbols = config['assets']

    symbols_to_run = ['BTC/USD']
    timeframes_to_run = ['15m']

    ingestor = DataIngestor(exchange_id='kraken')
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=15) # 15 days for sandbox testing
    start = start_dt.isoformat() + "Z"
    end = end_dt.isoformat() + "Z"

    for symbol in symbols_to_run:
        print(f"\n--- Ingesting {symbol} Data ---")
        ingestor.fetch_historical_data(symbol, '1h', start, end)
        for tf in timeframes_to_run:
            ingestor.fetch_historical_data(symbol, tf, start, end)
            print(f"\n--- ACEO Executing {symbol} on {tf} ---")
            tester = Backtester(symbol, execution_tf=tf, bias_tf='1h')
            tester.run()

    generate_report()
    print("\n--- Execution Complete, STRATEGY_REPORT.md Generated ---")

if __name__ == "__main__":
    main()

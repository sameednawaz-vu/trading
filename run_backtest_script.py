import json
import os
import sys
import argparse

sys.path.insert(0, '/app')

from ict_agent.robust_tester import RobustBacktester, generate_markdown_report

def main():
    parser = argparse.ArgumentParser(description="Run the ICT Autonomous Agent Backtester")
    parser.add_argument('--assets', nargs='+', default=["BTC/USD"], help='List of assets to backtest (e.g., BTC/USD ETH/USD)')
    parser.add_argument('--trades', type=int, default=500, help='Number of trades to simulate per strategy')
    args = parser.parse_args()

    print(f"Initializing Backtester for assets: {args.assets} with {args.trades} trades each.")
    tester = RobustBacktester(args.assets)

    strats_to_test = ["agentic_llm_strategy"]

    all_results = []
    for s in strats_to_test:
        try:
            res = tester.test_strategy(s, trades_per_strat=args.trades)
            if res:
                all_results.append(res)
        except Exception as e:
            print(f"Failed to test {s}: {e}")

    if not os.path.exists('reports'): os.makedirs('reports')
    if all_results:
        generate_markdown_report(all_results, 'reports/STRATEGY_PERFORMANCE_AUDIT.md')
        print("Audit Complete. Report saved to reports/STRATEGY_PERFORMANCE_AUDIT.md")
    else:
        print("Test executed but no valid trades returned in sample.")

if __name__ == "__main__":
    main()

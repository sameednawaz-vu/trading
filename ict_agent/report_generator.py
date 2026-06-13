import json
import os

def generate_report():
    leaderboard_path = '/app/strategy_leaderboard.json'
    report_path = '/app/STRATEGY_REPORT.md'
    
    if not os.path.exists(leaderboard_path):
        print("Leaderboard not found yet.")
        return

    with open(leaderboard_path, 'r') as f:
        data = json.load(f)

    successful = [s for s in data if s['win_rate'] >= 0.50]
    failed = [s for s in data if s['win_rate'] < 0.50]

    report = "# ICT Strategy Validation Report\n\n"
    report += f"Generated on: {os.popen('date /t').read().strip()} {os.popen('time /t').read().strip()}\n\n"

    report += "## Successful Strategies (>50% Win Rate)\n"
    if not successful:
        report += "_No strategies reached the 50% win rate threshold yet._\n\n"
    else:
        report += "| Strategy | Win Rate | Trades | Avg RR | Monthly Trades | Best Coin | PnL |\n"
        report += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for s in successful:
            report += f"| {s['name']} | {s['win_rate']:.2%} | {s['total_trades']} | {s['avg_rr']:.2f} | {s['avg_monthly_trades']:.2f} | {s['best_coin']} | ${s['profitability']:.2f} |\n"
        report += "\n"

    report += "## Failed Strategies (<50% Win Rate)\n"
    if not failed:
        report += "_No failed strategies recorded._\n\n"
    else:
        report += "| Strategy | Win Rate | Trades | Avg RR | Monthly Trades | Best Coin | PnL |\n"
        report += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for s in failed:
            report += f"| {s['name']} | {s['win_rate']:.2%} | {s['total_trades']} | {s['avg_rr']:.2f} | {s['avg_monthly_trades']:.2f} | {s['best_coin']} | ${s['profitability']:.2f} |\n"
        report += "\n"

    report += "## Architecture Audit Updates\n"
    report += "- **Fixed**: Short trade evaluation logic in backtester.\n"
    report += "- **Fixed**: Missing `get_recent_reflections` method in Memory module.\n"
    report += "- **Fixed**: Stage-1 filter logic (Bias/Direction alignment and SL/TP scope).\n"
    report += "- **Fixed**: Gemini CLI integration using robust piping and `--skip-trust`.\n"

    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"Report generated at {report_path}")

if __name__ == "__main__":
    generate_report()

import sqlite3
import pandas as pd
from datetime import datetime

class ReportGenerator:
    def __init__(self, db_path='./logs/trading_memory.db', report_path='./STRATEGY_REPORT.md'):
        self.db_path = db_path
        self.report_path = report_path

    def generate(self):
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM trades", conn)
            conn.close()

            if len(df) == 0:
                print("No trades found in database.")
                self._write_empty_report()
                return

            # Basic metrics
            total_trades = len(df)
            wins = df[df['outcome'] == 'Win']
            win_rate = len(wins) / total_trades

            # Risk/Reward
            losses = df[df['outcome'] == 'Loss']
            avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
            avg_loss = abs(losses['pnl'].mean()) if len(losses) > 0 else 1
            avg_rr = avg_win / avg_loss if avg_loss != 0 else 0

            # Estimated monthly trades
            # Find time range of trades
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            time_range_days = (df['timestamp'].max() - df['timestamp'].min()).days
            if time_range_days > 0:
                monthly_trades = (total_trades / time_range_days) * 30
            else:
                monthly_trades = total_trades # if all trades in same day

            report_content = f"""# Autonomous ICT Trading Agent - Final Strategy Report
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overall Performance Metrics
- **Total Trades**: {total_trades}
- **Successful Trades**: {len(wins)}
- **Overall Success Rate**: {win_rate:.2%}
- **Average Risk-to-Reward Ratio**: 1:{avg_rr:.2f}
- **Estimated Average Monthly Trades**: {monthly_trades:.1f}

## Strategy Summary
The agentic AI trader utilizes an Institutional Multi-Timeframe (MTF) model with the following core components:
1. **Kraken Data Ingestion**: Historical tracking bypassing geo-restrictions.
2. **Local Pre-Filtering**: Fast evaluation of Killzones, 1h HTF POI confluences, and FVG/OB detection to respect the 40 RPM NVIDIA API limit.
3. **NVIDIA LLaMa 3.3 70B Analysis**: Acts as the Sovereign Brain, applying "Evolved Student Agency" models to confirm Inducement sweeps, Market Structure Shifts, and precision FVG entries with a minimum 1:2 R/R target.
4. **Self-Reflection Memory**: Failed setups are analyzed post-mortem, and corrective mandates are injected iteratively into the `learnings.txt` memory node.

## Database Breakdown
"""
            # Group by symbol
            symbol_stats = df.groupby('symbol').apply(
                lambda x: pd.Series({
                    'Trades': len(x),
                    'Win Rate': f"{(len(x[x['outcome'] == 'Win']) / len(x)):.2%}",
                    'PnL': x['pnl'].sum()
                })
            ).reset_index()

            report_content += symbol_stats.to_markdown(index=False)

            with open(self.report_path, 'w') as f:
                f.write(report_content)

            print(f"Report generated successfully at {self.report_path}")

        except Exception as e:
            print(f"Failed to generate report: {e}")

    def _write_empty_report(self):
        content = f"""# Autonomous ICT Trading Agent - Final Strategy Report
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overall Performance Metrics
- **Total Trades**: 0
- **Successful Trades**: 0
- **Overall Success Rate**: 0.00%
- **Average Risk-to-Reward Ratio**: 0.00
- **Estimated Average Monthly Trades**: 0

*No trades were executed or recorded in the backtesting database.*
"""
        with open(self.report_path, 'w') as f:
            f.write(content)

if __name__ == "__main__":
    rg = ReportGenerator()
    rg.generate()

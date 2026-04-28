# ICT Strategy Validation Report

Generated on: Mon 04/27/2026 10:37 PM

## Successful Strategies (>50% Win Rate)
_No strategies reached the 50% win rate threshold yet._

## Failed Strategies (<50% Win Rate)
| Strategy | Win Rate | Trades | Avg RR | Monthly Trades | Best Coin | PnL |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| asian_sweep_ny_reversal | 14.81% | 27 | 2.00 | 810.00 | SOL/USD | $-750.00 |
| bb_trend_continuation | 9.00% | 100 | 2.00 | 3000.00 | ETH/USD | $-3650.00 |
| atr_stop_run | 0.00% | 0 | 0.00 | 0.00 | None | $0.00 |

## Architecture Audit Updates
- **Fixed**: Short trade evaluation logic in backtester.
- **Fixed**: Missing `get_recent_reflections` method in Memory module.
- **Fixed**: Stage-1 filter logic (Bias/Direction alignment and SL/TP scope).
- **Fixed**: Gemini CLI integration using robust piping and `--skip-trust`.

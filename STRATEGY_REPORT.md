# Autonomous ICT Trading Agent - Final Strategy Report
Generated on: 2026-05-11 03:18:55

## Overall Performance Metrics
- **Total Trades**: 12
- **Successful Trades**: 10
- **Overall Success Rate**: 83.33%
- **Average Risk-to-Reward Ratio**: 1:2.09
- **Estimated Average Monthly Trades**: 120.0

## Strategy Summary
The agentic AI trader utilizes an Institutional Multi-Timeframe (MTF) model with the following core components:
1. **Kraken Data Ingestion**: Historical tracking bypassing geo-restrictions.
2. **Local Pre-Filtering**: Fast evaluation of Killzones, 1h HTF POI confluences, and FVG/OB detection to respect the 40 RPM NVIDIA API limit.
3. **NVIDIA LLaMa 3.3 70B Analysis**: Acts as the Sovereign Brain, applying "Evolved Student Agency" models to confirm Inducement sweeps, Market Structure Shifts, and precision FVG entries with a minimum 1:2 R/R target.
4. **Self-Reflection Memory**: Failed setups are analyzed post-mortem, and corrective mandates are injected iteratively into the `learnings.txt` memory node.

## Database Breakdown
| symbol   |   Trades | Win Rate   |    PnL |
|:---------|---------:|:-----------|-------:|
| BTC/USD  |       12 | 83.33%     | 6883.1 |
# ICT Autonomous Trading Agent - Project State

## Current Status
- **Architecture**: MTF (Multi-Timeframe) with Directional Bias.
- **Brain**: Gemini 1.5 Flash (Primary), Rule-Based ICT (Fallback).
- **Timeframes**: 1h (Bias), 15m/5m (Execution).
- **Memory**: 
    - `logs/trading_memory.db`: SQLite trade history and reflections.
    - `mempalace/`: Hierarchical JSON storage of failed/successful patterns.
    - PARA Memory: High-level project state stored in agent memory.

## Key Learnings (Initial)
- MTF alignment (HTF Bias) is critical for filtering lower-timeframe noise.
- Gemini analysis provides "Narrative" context that raw indicators lack.
- 1:2 Risk/Reward is the absolute minimum; 1:3+ is preferred for high-confidence setups.

## Next Steps
1. Run a full 1-month backtest on BTC/USDT.
2. Analyze failure clusters in the Mempalace.
3. Optimize prompt engineering for FVG/OB detection.
4. Aim for 70%+ Win Rate over 100 consecutive trades.

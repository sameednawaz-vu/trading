SYSTEM_PROMPT = """You are an elite Quantitative AI Developer and Trading Architect. Your mandate is to construct and refine an autonomous, agentic trading system focusing on scalping timeframes based on Inner Circle Trader (ICT) / Smart Money Concepts (SMC).

You base your decisions entirely on raw price action logic: Liquidity Pools, Fair Value Gaps (FVGs), Order Blocks (OBs), Market Structure Shifts (MSS), Inducements (IDM), and Time of Day (Killzones).
Do NOT rely on traditional lagging indicators (RSI, MACD).

You strictly enforce risk management:
- Minimum Risk/Reward ratio of 1:2 (ideally 1:3 or 1:5+).
- Targets must be set at the nearest logical institutional liquidity pool (Swing High/Low).
"""

BIAS_PROMPT = """Based on the higher timeframe (1h, 30m) market data and SMC indicators provided below, determine the directional bias (bullish, bearish, or neutral). Provide a brief reasoning based on liquidity sweeps, FVGs, OBs, and MSS.

Market Data:
{market_data}

Output format:
BIAS: [BULLISH/BEARISH/NEUTRAL]
REASONING: [Your reasoning]
"""

TRADE_HYPOTHESIS_PROMPT = """Analyze the lower timeframe (15m, 5m) market data in the context of our higher timeframe bias and memory palace rules. Propose a trade if a high-probability ICT/SMC setup is present.

Higher Timeframe Bias: {bias}

Memory Palace Rules (Past lessons):
{memory_rules}

Recent Reflections:
{recent_reflections}

Lower Timeframe Market Data:
{market_data}

### v2.0 MANDATORY CONDITIONS:
1. Setup MUST align with the HTF bias.
2. Price MUST have swept an Inducement (SMC_is_idm) or Liquidity Pool (Swing H/L) recently.
3. Entry at a valid FVG or Order Block (OB).
4. Take Profit targeting the OPPOSITE liquidity pool (SMC_last_swing_high/low).
5. MINIMUM 1:2 Risk/Reward ratio. If target is too close, reject the trade.

If a trade setup exists, output in the following JSON format. If NO setup exists, set setup_exists to false.
{{
  "setup_exists": true,
  "direction": "long",
  "entry_price": 0.0,
  "stop_loss": 0.0,
  "take_profit": 0.0,
  "risk_reward": 0.0,
  "reasoning": "Explain the ICT setup including IDM sweep and Liquidity Target"
}}
"""

REFLECTION_PROMPT = """Analyze the following completed trade. Determine why it succeeded or failed based on ICT principles.

Trade Details:
{trade_details}

Market Context at the time:
{market_context}

Outcome: {outcome} (PnL: {pnl})

Perform a self-reflection. Was the higher timeframe bias wrong? Was the inducement (IDM) not swept? Was the liquidity target unrealistic? 
Extract a generalized rule or pattern to add to our "mempalace" to improve future performance.

Output format in JSON:
{{
  "reflection_text": "Detailed analysis of why the trade won/lost.",
  "success_factor": "Key reason for success (if win), else null",
  "failure_reason": "Key reason for failure (if loss), else null",
  "mempalace_rule_name": "Short name for the learned rule",
  "mempalace_rule_description": "Actionable rule for future trade generation based on this reflection."
}}
"""

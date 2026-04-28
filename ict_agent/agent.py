import json
import pandas as pd
from ict_agent.memory import MemPalace
from ict_agent.llm import LLMIntegration
from ict_agent.prompts import SYSTEM_PROMPT, BIAS_PROMPT, TRADE_HYPOTHESIS_PROMPT, REFLECTION_PROMPT
from ict_agent.smc_logic import get_killzone

class TradingAgent:
    def __init__(self, db_path=None, is_backtest=False):
        self.memory = MemPalace(db_path) if db_path else MemPalace()
        self.llm = LLMIntegration()
        self.is_backtest = is_backtest

    def _format_market_data(self, df_dict, timeframes, num_rows=5):
        formatted = ""
        for tf in timeframes:
            if tf in df_dict and df_dict[tf] is not None:
                df = df_dict[tf].tail(num_rows)
                formatted += f"\n--- {tf} Timeframe ---\n"
                cols = [c for c in df.columns if 'SMC_' in c]
                formatted += df[cols].to_string() + "\n"
        return formatted

    def analyze_bias(self, df_dict):
        market_data_str = self._format_market_data(df_dict, ['1h', '30m'])
        prompt = f"Determine the Higher Timeframe Institutional Bias based on structural displacement and liquidity sweeps. Reply BULLISH, BEARISH, or NEUTRAL.\n{market_data_str}"
        response = self.llm.generate_response(SYSTEM_PROMPT, prompt)
        bias = "NEUTRAL"
        if response:
            if "BULLISH" in response.upper(): bias = "BULLISH"
            elif "BEARISH" in response.upper(): bias = "BEARISH"
        return bias, response

    def _stage_1_filter(self, df_dict, bias):
        """High-Precision Institutional Filter v2.1 (Local)"""
        try:
            ltf = df_dict.get('5m')
            if ltf is None: return None
            
            last_bar = ltf.iloc[-1]
            price = last_bar['close']
            kz = get_killzone(last_bar['timestamp'])
            
            # 1. Killzone Filter
            if kz == "None": return None
            
            # 2. Confluence Check: Liquidity Sweep + FVG + Bias Match
            lookback = ltf.tail(15)
            has_sweep_low = lookback['SMC_sweep_low'].any()
            has_sweep_high = lookback['SMC_sweep_high'].any()
            
            # Entry on FVG tap
            active_top = last_bar.get('SMC_active_fvg_top')
            active_bottom = last_bar.get('SMC_active_fvg_bottom')
            
            is_in_fvg = False
            if not pd.isna(active_top) and not pd.isna(active_bottom):
                if active_bottom <= price <= active_top:
                    is_in_fvg = True
            
            if not is_in_fvg or bias == "NEUTRAL":
                return None

            direction = None
            if bias == "BULLISH" and has_sweep_low:
                direction = "long"
            elif bias == "BEARISH" and has_sweep_high:
                direction = "short"
            
            if direction:
                # Dynamic SL/TP
                sl = float(active_bottom if direction == "long" else active_top)
                # TP at opposite swing high/low
                tp = float(last_bar['SMC_last_swing_high'] if direction == "long" else last_bar['SMC_last_swing_low'])
                
                # Minimum 1:2 RR Check
                risk = abs(price - sl)
                reward = abs(tp - price)
                
                if risk <= 0 or reward <= 0 or (reward / risk) < 2.0:
                    return None
                    
                return {
                    "setup_exists": True,
                    "direction": direction,
                    "entry_price": float(price),
                    "sl": sl,
                    "tp": tp,
                    "thesis": f"v2.1: {kz} {direction.upper()} | Sweep + FVG + Bias Confluence",
                    "rr": reward / risk
                }
        except Exception as e:
            # print(f"Filter Error: {e}")
            pass
        return None

    def propose_trade(self, df_dict, bias):
        # STAGE 1: LOCAL HIGH-PRECISION FILTER
        local_setup = self._stage_1_filter(df_dict, bias)
        if not local_setup:
            return {"setup_exists": False, "reason": "No Institutional Confluence"}

        # STAGE 2: NEURAL BRAIN AUDIT
        market_data_str = self._format_market_data(df_dict, ['15m', '5m'])
        learnings = self.memory.get_recent_reflections(limit=5)
        # learnings are rows: (pair, result, reflection_text, failure_reason)
        learnings_str = "\n".join([f"- {l[2]} (Reason: {l[3]})" for l in learnings])
        
        prompt = f"""
### ACEO SOVEREIGN BRAIN MANDATE
Evaluate this high-probability setup.
Local Thesis: {local_setup['thesis']}

### DATA:
{market_data_str}

### RECENT FAILURES (DO NOT REPEAT):
{learnings_str}

FINAL DECISION (JSON ONLY):
{{
  "setup_exists": bool,
  "direction": "long" | "short",
  "entry_price": float,
  "stop_loss": float,
  "take_profit": float,
  "strategy": "string",
  "reasoning": "string"
}}
"""
        response_text = self.llm.generate_response(SYSTEM_PROMPT, prompt)
        parsed = self.llm.parse_json_response(response_text)
        if parsed:
            return parsed
        return local_setup

    def reflect_on_trade(self, trade_id, trade_data, market_context):
        prompt = f"RUTHLESS AUDIT: Trade {trade_id} failed. Details: {json.dumps(trade_data)}. Context: {json.dumps(market_context)}. Explain the mistake and provide a rule to prevent it."
        response = self.llm.generate_response(SYSTEM_PROMPT, prompt)
        if response:
            self.memory.log_reflection(trade_id, response, failure_reason="Market Structure Failure")
            self.memory.add_to_mempalace("FAILURE_RULE", response[:100])

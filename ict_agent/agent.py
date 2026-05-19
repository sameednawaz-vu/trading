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
        # Optimized: Use naive logic to avoid LLM rate limit for bias
        # This keeps the requests strictly for setups
        htf = df_dict.get('1h')
        if htf is None or htf.empty: return "NEUTRAL", "No HTF data"
        last_bar = htf.iloc[-1]

        # Simple structural bias: Price vs EMA 200 + recent sweeps
        price = last_bar['close']
        ema = last_bar.get('SMC_ema_200', price)

        if price > ema:
            bias = "BULLISH"
        elif price < ema:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        return bias, "Local EMA-based structural bias."

    def _stage_1_filter(self, df_dict, bias):
        """High-Precision Institutional Filter v2.1 (Local)"""
        try:
            # We determine the execution timeframe dynamically based on what's available
            # (excluding 1h which is bias)
            ltf_keys = [k for k in df_dict.keys() if k != '1h']
            if not ltf_keys: return None
            tf = ltf_keys[0]

            ltf = df_dict.get(tf)
            if ltf is None or ltf.empty: return None
            
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
            
            # Check Order Blocks as secondary POI
            ob_bull = last_bar.get('SMC_ob_bullish')
            ob_bear = last_bar.get('SMC_ob_bearish')

            if not is_in_fvg and not ob_bull and not ob_bear:
                return None

            if bias == "NEUTRAL":
                return None

            direction = None
            if bias == "BULLISH" and (has_sweep_low or ob_bull):
                direction = "long"
            elif bias == "BEARISH" and (has_sweep_high or ob_bear):
                direction = "short"
            
            if direction:
                sl = float(active_bottom if direction == "long" else active_top)

                # If OB logic triggered without FVG, fallback to price-based SL
                if pd.isna(sl):
                    sl = float(last_bar['low'] * 0.998 if direction == "long" else last_bar['high'] * 1.002)

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
                    "thesis": f"v2.1: {kz} {direction.upper()} | Sweep/OB + FVG + Bias Confluence",
                    "rr": reward / risk,
                    "tf": tf
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

        tf = local_setup["tf"]
        # STAGE 2: NEURAL BRAIN AUDIT
        market_data_str = self._format_market_data(df_dict, ['1h', tf])

        # Pull learnings from memory palace and DB
        learnings = self.memory.get_recent_reflections(limit=5)
        # learnings are rows: (pair, result, reflection_text, failure_reason)
        learnings_str = "\n".join([f"- {l[2]} (Reason: {l[3]})" for l in learnings])
        
        mempalace_rules = self.memory.get_mempalace_rules()
        rules_str = "\n".join([f"- {r['name']}: {r['description']}" for r in mempalace_rules[:3]])

        prompt = f"""
### ACEO SOVEREIGN BRAIN MANDATE
Evaluate this high-probability setup generated by local filters.
Local Thesis: {local_setup['thesis']}

### DATA:
{market_data_str}

### MEMPALACE RULES (OBEY THESE):
{rules_str}

### RECENT FAILURES (DO NOT REPEAT):
{learnings_str}

FINAL DECISION (JSON ONLY). If you reject, set setup_exists to false:
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
            # Ensure risk constraints are met even if LLM hallucinates
            if parsed.get('setup_exists'):
                risk = abs(parsed.get('entry_price', 0) - parsed.get('stop_loss', 0))
                reward = abs(parsed.get('take_profit', 0) - parsed.get('entry_price', 0))
                if risk > 0 and reward / risk >= 2.0:
                    return parsed
                else:
                    return {"setup_exists": False, "reason": "LLM proposed trade violated 1:2 RR minimum"}
            return parsed
        return local_setup

    def reflect_on_trade(self, trade_id, trade_data, market_context):
        prompt = f"RUTHLESS AUDIT: Trade {trade_id} failed. Details: {json.dumps(trade_data)}. Context: {json.dumps(market_context)}. Explain the mistake and provide a rule to prevent it. Output purely JSON:\n{{\n  \"reflection_text\": \"detailed analysis\",\n  \"failure_reason\": \"short reason\",\n  \"mempalace_rule_name\": \"RULE_NAME\",\n  \"mempalace_rule_description\": \"rule description\"\n}}"
        response_text = self.llm.generate_response(SYSTEM_PROMPT, prompt)
        parsed = self.llm.parse_json_response(response_text)

        if parsed:
            self.memory.log_reflection(trade_id, parsed.get("reflection_text", "Failed trade"), failure_reason=parsed.get("failure_reason", "Unknown"))
            if parsed.get("mempalace_rule_name") and parsed.get("mempalace_rule_description"):
                self.memory.add_to_mempalace(parsed["mempalace_rule_name"], parsed["mempalace_rule_description"])
        else:
            self.memory.log_reflection(trade_id, "Model failed to parse JSON reflection.", failure_reason="Market Structure Failure")
            self.memory.add_to_mempalace("FAILURE_RULE", "Always ensure proper SL placement above/below swing points.")

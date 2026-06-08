import json
import pandas as pd
import numpy as np
import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

class TradingBrain:
    def __init__(self, api_key=None):
        self.learnings_path = './learnings.txt'
        self.api_key = api_key or os.getenv("JULES_API_KEY_ACCOUNT_2") or os.getenv("JULES_API_KEY")
        self.api_url = "https://integrate.api.nvidia.com/v1/chat/completions"

    def _call_llm_api(self, prompt):
        if not self.api_key:
            print("Error: NVIDIA API Key not found.")
            return None
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "meta/llama-3.3-70b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "top_p": 0.7,
            "max_tokens": 1024,
            "stream": False
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                resp_json = response.json()
                content = resp_json['choices'][0]['message']['content']

                # Extract JSON from markdown or raw text
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    return content[start:end+1]
                return content
            else:
                os.makedirs('./logs', exist_ok=True)
                with open('./logs/cli_errors.log', 'a') as f:
                    f.write(f"\n--- {datetime.now(timezone.utc)} ---\nStatus Code: {response.status_code}\nError: {response.text}\n")
                print(f"API Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Request Error: {e}")
        return None

    def generate_hypothesis(self, market_data, context=""):
        try:
            data = json.loads(market_data) if isinstance(market_data, str) else market_data
            
            # --- STAGE 1: INSTITUTIONAL FILTER v18.0 (Local) ---
            # Mimicking Jules High-Win setups: Must have Killzone + HTF POI + Sweep
            hypothesis_json = self._institutional_filter_v18(data)
            hypothesis = json.loads(hypothesis_json)
            
            if hypothesis.get('side') == 'None':
                return hypothesis_json

            # --- STAGE 2: NEURAL BRAIN (Remote) ---
            # Fresh analysis, no cache, grounded in 'Evolved Student' research
            data_str = json.dumps(data, sort_keys=True)
            learnings = ""
            if os.path.exists(self.learnings_path):
                with open(self.learnings_path, 'r') as f:
                    learnings = f.read()

            prompt = f"""
### ACEO SOVEREIGN BRAIN MANDATE: EVOLVED STUDENT AGENCY
You are the Agentic CEO and Master ICT Architect. Your mandate is to reach 80%+ win rate by mimicking the 'Evolved Student Models' and 'MCP' (Market Context & Price) frameworks.
Review this trade hypothesis triggered by our local Institutional Filter.

### INTEGRATED STUDENT MODELS:
1. **Model 1 (BOS Model)**: HTF Bias + BOS (Break of Structure) + FVG.
2. **Model 2 (Inducement Model)**: Identify 'IDM' (Retail Trap). Price must sweep the 'Inducement' (last low/high before POI) before hitting the FVG/OB.
3. **Model 3 (OTE Model)**: Fibonacci 62%–79% retracement + FVG confluence.
4. **Model 4 (Silver Bullet)**: Strict Killzone (3-4AM, 10-11AM, 2-3PM NY). Liquidity Raid on 9:00 AM range -> MSS -> FVG.

### CURRENT MARKET DATA:
{data_str}

### PREVIOUS AUDITS & CORRECTED MANDATES:
{learnings}

### REQUIRED MULTI-PERSPECTIVE AUDIT:
- **CEO**: Strategic alignment with 80% Win Rate mandate.
- **CSO**: Technical audit of IDM sweep and BOS.
- **Eng**: Precision execution on FVG Consequent Encroachment.

FINAL DECISION (JSON):
{{
  "side": "Long" | "Short" | "None",
  "entry_price": float,
  "stop_loss": float,
  "take_profit": float,
  "model_used": "Model 1" | "Model 2" | "Model 3" | "Model 4",
  "reason": "Detailed institutional audit identifying IDM and BOS",
  "confidence": float
}}
"""
            response = self._call_llm_api(prompt)
            if response:
                try:
                    res_json = json.loads(response)
                    if res_json.get('side') != 'None':
                        print(f"Sovereign Brain [{res_json.get('model_used')}]: {res_json.get('reason')[:100]}...")
                    return response
                except:
                    pass

            return hypothesis_json # Fallback to high-prob local setup

        except Exception as e:
            print(f"Brain Error: {e}")
        return json.dumps({"side": "None", "reason": "Error"})

    def _institutional_filter_v18(self, data):
        try:
            price = data['price']
            bias = data.get('bias', 'Neutral')
            kz = data.get('killzone')
            features = data['features']
            
            # 1. Killzone Window (Silver Bullet Windows)
            if kz not in ['London', 'New York', 'Silver_Bullet']:
                return json.dumps({"side": "None", "reason": "Outside Institutional Windows"})

            # 2. HTF POI (1h FVG)
            htf_fvg = features.get('htf_fvg', {})
            in_poi = False

            # FVG data format is {"FVG": {"date": value}, "Top": {"date": value}, "Bottom": {"date": value}}
            for idx, val in htf_fvg.get('fvg_top', {}).items():
                if not pd.isna(val) and not pd.isna(htf_fvg.get('fvg_bottom', {}).get(idx, np.nan)):
                    top = val
                    bottom = htf_fvg['fvg_bottom'][idx]
                    if bottom * 0.9995 <= price <= top * 1.0005:
                        in_poi = True; break

            # Check active FVGs instead
            if not in_poi:
                for idx, val in htf_fvg.get('active_fvg_top', {}).items():
                    if not pd.isna(val) and not pd.isna(htf_fvg.get('active_fvg_bottom', {}).get(idx, np.nan)):
                        top = val
                        bottom = htf_fvg['active_fvg_bottom'][idx]
                        if bottom * 0.9995 <= price <= top * 1.0005:
                            in_poi = True; break

            if not in_poi: return json.dumps({"side": "None", "reason": "No HTF POI Confluence"})

            # 3. Liquidity Sweep
            recent_lows = [v for v in features.get('last_swing_low', {}).values() if not pd.isna(v)]
            recent_highs = [v for v in features.get('last_swing_high', {}).values() if not pd.isna(v)]
            last_low = min(recent_lows[-5:]) if recent_lows else None
            last_high = max(recent_highs[-5:]) if recent_highs else None
            
            bull_sweep = last_low and price > last_low
            bear_sweep = last_high and price < last_high

            # Risk/Reward enforcing 1:2 minimum, 1:3 target
            if bull_sweep and bias != 'Bearish':
                sl = last_low * 0.997
                dist = price - sl
                tp = price + dist * 3.0 # Target 1:3 RR for 80% precision
                return json.dumps({"side": "Long", "entry_price": price, "stop_loss": sl, "take_profit": tp, "model_used": "Model 1", "reason": "Institutional POI + Sweep Detected"})
            
            if bear_sweep and bias != 'Bullish':
                sl = last_high * 1.003
                dist = sl - price
                tp = price - dist * 3.0
                return json.dumps({"side": "Short", "entry_price": price, "stop_loss": sl, "take_profit": tp, "model_used": "Model 1", "reason": "Institutional POI + Sweep Detected"})

        except Exception as e:
            print(f"Filter Error: {e}")

        return json.dumps({"side": "None", "reason": "Insufficient Institutional Confluence"})

    def reflect_on_failure(self, trade_details, outcome):
        prompt = f"Analyze failed ICT trade: {json.dumps(trade_details)}. Outcome: {outcome}. Provide a concise 'Corrected Mandate' to prevent this."
        corrected = self._call_llm_api(prompt)
        if corrected:
            with open(self.learnings_path, 'a') as f:
                f.write(f"\n--- Post-Mortem ({datetime.now(timezone.utc)}) ---\n{corrected.strip()}\n")
        return f"Logged: {trade_details.get('id', 'unknown')}"

if __name__ == "__main__":
    brain = TradingBrain("test_key_dummy")
    # Just a small sanity check on methods existing and not erroring out on initial parsing
    print(brain._institutional_filter_v18({"price": 60000, "bias": "Neutral", "killzone": "None", "features": {}}))

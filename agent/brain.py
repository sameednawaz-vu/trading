import json
import pandas as pd
import numpy as np
import hashlib
import subprocess
import os

class TradingBrain:
    def __init__(self, api_key=None):
        self.learnings_path = r'./learnings.txt'
        # Use JULES_API_KEY_ACCOUNT_2 from .env if available
        self.api_key = api_key or os.getenv("JULES_API_KEY_ACCOUNT_2")

    def _call_nvidia_nim(self, prompt):
        import requests
        if not self.api_key:
            return None
            
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "meta/llama-3.3-70b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1024,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    return content[start:end+1]
                return content
        except Exception as e:
            print(f"API Error: {e}")
        return None
            
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "meta/llama-3.3-70b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1024,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    return content[start:end+1]
                return content
        except Exception as e:
            print(f"API Error: {e}")
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
            response = self._call_nvidia_nim(prompt)
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
            if kz not in ['London', 'New York']:
                return json.dumps({"side": "None", "reason": "Outside Institutional Windows"})

            # 2. HTF POI (1h FVG)
            htf_fvg = features.get('htf_fvg', {})
            in_poi = False
            for idx, val in htf_fvg.get('FVG', {}).items():
                if htf_fvg['Bottom'][idx] * 0.9995 <= price <= htf_fvg['Top'][idx] * 1.0005:
                    in_poi = True; break
            if not in_poi: return json.dumps({"side": "None", "reason": "No HTF POI Confluence"})

            # 3. Liquidity Sweep
            fvg_data = features.get('fvg', {})
            recent_lows = [v for v in fvg_data.get('Bottom', {}).values() if not pd.isna(v)]
            recent_highs = [v for v in fvg_data.get('Top', {}).values() if not pd.isna(v)]
            last_low = min(recent_lows[-5:]) if recent_lows else None
            last_high = max(recent_highs[-5:]) if recent_highs else None
            
            bull_sweep = last_low and price > last_low
            bear_sweep = last_high and price < last_high

            if bull_sweep and bias != 'Bearish':
                sl = last_low * 0.997
                tp = price + (price - sl) * 3.0 # Target 1:3 RR for 80% precision
                return json.dumps({"side": "Long", "entry_price": price, "stop_loss": sl, "take_profit": tp, "model_used": "Model 1", "reason": "Institutional POI + Sweep Detected"})
            
            if bear_sweep and bias != 'Bullish':
                sl = last_high * 1.003
                tp = price - (sl - price) * 3.0
                return json.dumps({"side": "Short", "entry_price": price, "stop_loss": sl, "take_profit": tp, "model_used": "Model 1", "reason": "Institutional POI + Sweep Detected"})

        except: pass
        return json.dumps({"side": "None", "reason": "Insufficient Institutional Confluence"})

    def reflect_on_failure(self, trade_details, outcome):
        prompt = f"Analyze failed ICT trade: {json.dumps(trade_details)}. Outcome: {outcome}. Provide a concise 'Corrected Mandate' to prevent this."
        corrected = self._call_nvidia_nim(prompt)
        if corrected:
            with open(self.learnings_path, 'a') as f:
                f.write(f"\n--- Post-Mortem ({pd.Timestamp.now()}) ---\n{corrected.strip()}\n")
        return f"Logged: {trade_details.get('id', 'unknown')}"

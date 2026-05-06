import json
import pandas as pd
import numpy as np
import os
import requests
from dotenv import load_dotenv

load_dotenv()

class TradingBrain:
    def __init__(self, api_key=None):
        self.learnings_path = './learnings.txt'
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.api_url = "https://integrate.api.nvidia.com/v1/chat/completions"

    def _call_nvidia_api(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta/llama-3.3-70b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "top_p": 0.7,
            "max_tokens": 1024,
            "stream": False
        }
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                # Extract JSON from response
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    return content[start:end+1]
                return content
            else:
                print(f"API Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Request Error: {e}")
        return None

    def generate_hypothesis(self, market_data, context=""):
        try:
            data = json.loads(market_data) if isinstance(market_data, str) else market_data
            
            # --- STAGE 1: INSTITUTIONAL FILTER (Local) ---
            hypothesis_json = self._institutional_filter(data)
            hypothesis = json.loads(hypothesis_json)
            
            if hypothesis.get('side') == 'None':
                return hypothesis_json

            # --- STAGE 2: NEURAL BRAIN (Remote NVIDIA API) ---
            data_str = json.dumps(data, sort_keys=True)
            learnings = ""
            if os.path.exists(self.learnings_path):
                with open(self.learnings_path, 'r') as f:
                    learnings = f.read()

            prompt = f"""
### ACEO SOVEREIGN BRAIN MANDATE: EVOLVED STUDENT AGENCY
You are the Agentic CEO and Master ICT Architect. Your mandate is to reach >85% win rate and a minimum 1:2 R:R by mimicking the 'Evolved Student Models' and 'MCP' (Market Context & Price) frameworks.
Review this trade hypothesis triggered by our local Institutional Filter.

### STRATEGY RULES (ICT):
1. **Trend Alignment**: Only trade in the direction of the HTF bias (1h).
2. **Liquidity Sweeps**: A valid setup requires price to have recently swept a swing high/low (Inducement).
3. **Displacement & FVG**: Look for strong displacement leaving a Fair Value Gap (FVG).
4. **Order Blocks**: Entries from a valid Order Block (OB) are high probability.
5. **Risk to Reward**: Must be at least 1:2.

### CURRENT MARKET DATA:
{data_str}

### PREVIOUS AUDITS & CORRECTED MANDATES:
{learnings}

### TASK:
Review the local filter's proposed entry and confirm or reject it. You MUST format your response as valid JSON ONLY.

FINAL DECISION (JSON):
{{
  "side": "Long" | "Short" | "None",
  "entry_price": float,
  "stop_loss": float,
  "take_profit": float,
  "model_used": "FVG/OB Confluence" | "Liquidity Raid",
  "reason": "Detailed institutional audit identifying liquidity sweeps and FVGs",
  "confidence": float
}}
"""
            response = self._call_nvidia_api(prompt)
            if response:
                try:
                    res_json = json.loads(response)
                    if res_json.get('side') != 'None':
                        print(f"Sovereign Brain [{res_json.get('model_used')}]: {res_json.get('reason')[:100]}...")
                    return response
                except:
                    pass

            return hypothesis_json # Fallback to local setup if API fails

        except Exception as e:
            print(f"Brain Error: {e}")
        return json.dumps({"side": "None", "reason": "Error"})

    def _institutional_filter(self, data):
        try:
            price = data['price']
            bias = data.get('bias', 'Neutral')
            features = data['features']

            # Simplify for higher volume: check for FVG and direction
            fvg_data = features.get('fvg', {})
            ob_data = features.get('ob', {})
            
            # Simple heuristic for long/short
            # Look for recent FVG
            fvg_bottoms = [v for v in fvg_data.get('Bottom', {}).values() if not pd.isna(v)]
            fvg_tops = [v for v in fvg_data.get('Top', {}).values() if not pd.isna(v)]
            
            # Very basic setup logic, the AI will refine it.
            if bias == "Bullish" and fvg_bottoms:
                entry = price
                sl = price * 0.99 # 1% stop
                tp = price * 1.02 # 2% tp (1:2 R:R)
                return json.dumps({"side": "Long", "entry_price": entry, "stop_loss": sl, "take_profit": tp, "model_used": "Filter", "reason": "Bullish Bias + Data"})
            elif bias == "Bearish" and fvg_tops:
                entry = price
                sl = price * 1.01
                tp = price * 0.98
                return json.dumps({"side": "Short", "entry_price": entry, "stop_loss": sl, "take_profit": tp, "model_used": "Filter", "reason": "Bearish Bias + Data"})

        except Exception as e:
            pass
        return json.dumps({"side": "None", "reason": "Insufficient Local Confluence"})

    def reflect_on_failure(self, trade_details, outcome):
        prompt = f"Analyze failed ICT trade: {json.dumps(trade_details)}. Outcome: {outcome}. Provide a concise 'Corrected Mandate' to prevent this. RETURN JSON: {{\"learning\": \"string\"}}"
        response = self._call_nvidia_api(prompt)
        if response:
            try:
                res_json = json.loads(response)
                corrected = res_json.get('learning', '')
                if corrected:
                    with open(self.learnings_path, 'a') as f:
                        f.write(f"\n--- Post-Mortem ({pd.Timestamp.now()}) ---\n{corrected.strip()}\n")
            except:
                pass
        return f"Logged: {trade_details.get('id', 'unknown')}"

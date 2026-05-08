import json
import pandas as pd
import numpy as np
import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

class TradingBrain:
    def __init__(self, api_key=None):
        self.learnings_path = r'./learnings.txt'
        self.api_key = api_key or os.getenv("JULES_API_KEY_ACCOUNT_2")
        self.api_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.last_api_call_time = 0
        self.api_call_interval = 60.0 / 40.0 # 40 requests per minute limit

        # ensure logs directory exists
        if not os.path.exists('./logs'):
            os.makedirs('./logs')

    def _call_llm(self, prompt):
        # Rate limit to respect 40 RPM
        current_time = time.time()
        elapsed = current_time - self.last_api_call_time
        if elapsed < self.api_call_interval:
            time.sleep(self.api_call_interval - elapsed)
            
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
            self.last_api_call_time = time.time()
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                res_json = response.json()
                content = res_json['choices'][0]['message']['content']
                # extract json if it's wrapped in markdown or other text
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    return content[start:end+1]
                return content
            else:
                with open(r'./logs/api_errors.log', 'a') as f:
                    f.write(f"\n--- {pd.Timestamp.now()} ---\nStatus Code: {response.status_code}\nError: {response.text}\n")
        except Exception as e:
            print(f"API Error: {e}")
            with open(r'./logs/api_errors.log', 'a') as f:
                f.write(f"\n--- {pd.Timestamp.now()} ---\nException: {e}\n")
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
You are the Agentic CEO and Master ICT Architect. Your mandate is to reach 80%+ win rate using ICT concepts (Fair Value Gaps, Order Blocks, Liquidity Sweeps).
Review this trade hypothesis triggered by our local Institutional Filter.

### REQUIRED ANALYSIS:
1. Identify if a Valid Fair Value Gap (FVG) or Order Block (OB) exists in the direction of the bias.
2. Ensure there has been a recent Liquidity Sweep before entering the POI.
3. Determine entry price at the consequent encroachment (50% level) of the FVG/OB.
4. Place Stop Loss safely behind the swept liquidity or the other side of the FVG/OB.
5. Target the opposing liquidity pool, ensuring at least a 1:2 Risk/Reward ratio.

### CURRENT MARKET DATA:
{data_str}

### PREVIOUS AUDITS & CORRECTED MANDATES:
{learnings}

### REQUIRED DECISION FORMAT (JSON ONLY):
{{
  "side": "Long" | "Short" | "None",
  "entry_price": float,
  "stop_loss": float,
  "take_profit": float,
  "model_used": "ICT FVG/OB Model",
  "reason": "Detailed explanation of ICT concepts used.",
  "confidence": float
}}
"""
            response = self._call_llm(prompt)
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
        prompt = f"Analyze failed ICT trade: {json.dumps(trade_details)}. Outcome: {outcome}. Provide a concise 'Corrected Mandate' to prevent this based on ICT principles."
        corrected = self._call_llm(prompt)
        if corrected:
            with open(self.learnings_path, 'a') as f:
                f.write(f"\n--- Post-Mortem ({pd.Timestamp.now()}) ---\n{corrected.strip()}\n")
        return f"Logged: {trade_details.get('id', 'unknown')}"

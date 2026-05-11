import json
import pandas as pd
import numpy as np
import requests
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

class TradingBrain:
    def __init__(self, api_key=None):
        self.learnings_path = './learnings.txt'
        self.db_path = './logs/trading_memory.db'
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        if not self.api_key:
             print("Warning: NVIDIA_API_KEY not found in environment.")

        os.makedirs('./logs', exist_ok=True)
        self._init_db()

    def _init_db(self):
        # Double check initialization, though backtester handles it too
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                timeframe TEXT,
                timestamp TEXT,
                side TEXT,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                outcome TEXT,
                pnl REAL,
                model_used TEXT,
                reason TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def _call_llm(self, prompt):
        """Calls the NVIDIA NIM Llama 3.3 70B Instruct API via requests."""
        if not self.api_key:
            return None

        url = "https://integrate.api.nvidia.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        data = {
            "model": "meta/llama-3.3-70b-instruct",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "top_p": 0.7,
            "max_tokens": 1024,
            "stream": False
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                # Try to extract JSON from the response
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    return content[start:end+1]
                return content
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                with open('./logs/api_errors.log', 'a') as f:
                    f.write(f"\n--- {pd.Timestamp.now()} ---\nStatus: {response.status_code}\nError: {response.text}\n")
        except Exception as e:
            print(f"Request Error: {e}")
            with open('./logs/api_errors.log', 'a') as f:
                f.write(f"\n--- {pd.Timestamp.now()} ---\nRequest Error: {e}\n")
        return None

    def generate_hypothesis(self, market_data, context=""):
        try:
            data = json.loads(market_data) if isinstance(market_data, str) else market_data
            
            # --- STAGE 1: INSTITUTIONAL FILTER v18.0 (Local) ---
            # Mimicking Jules High-Win setups: Must have Killzone + HTF POI + Sweep
            hypothesis_json = self._institutional_filter_v18(data)
            hypothesis = json.loads(hypothesis_json)
            
            # If the local filter doesn't even see a setup, don't query the LLM (saves rate limit)
            if hypothesis.get('side') == 'None':
                return hypothesis_json

            # --- STAGE 2: NEURAL BRAIN (Remote) ---
            data_str = json.dumps(data, sort_keys=True)
            learnings = ""
            if os.path.exists(self.learnings_path):
                with open(self.learnings_path, 'r') as f:
                    learnings = f.read()

            prompt = f"""
### ACEO SOVEREIGN BRAIN MANDATE: EVOLVED STUDENT AGENCY
You are the Agentic CEO and Master ICT Architect. Your mandate is to reach 85%+ win rate by mimicking the 'Evolved Student Models' and 'MCP' (Market Context & Price) frameworks.
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
- **CEO**: Strategic alignment with 85% Win Rate mandate. Minimum Risk/Reward is 1:2.
- **CSO**: Technical audit of IDM sweep and BOS.
- **Eng**: Precision execution on FVG Consequent Encroachment.

FINAL DECISION (JSON ONLY, NO MARKDOWN):
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
            response = self._call_llm(prompt)
            if response:
                try:
                    res_json = json.loads(response)
                    if res_json.get('side') != 'None':
                        print(f"Sovereign Brain [{res_json.get('model_used')}]: {res_json.get('reason')[:100]}...")
                    return response
                except json.JSONDecodeError:
                    print(f"Failed to parse LLM response as JSON: {response}")
                    pass

            return hypothesis_json # Fallback to high-prob local setup

        except Exception as e:
            print(f"Brain Error: {e}")
        return json.dumps({"side": "None", "reason": f"Error: {e}"})

    def _institutional_filter_v18(self, data):
        try:
            price = data['price']
            bias = data.get('bias', 'Neutral')
            kz = data.get('killzone')
            features = data.get('features', {})
            
            # 1. Killzone Window (Silver Bullet Windows)
            if kz not in ['London', 'New York']:
                return json.dumps({"side": "None", "reason": "Outside Institutional Windows"})

            # 2. HTF POI (1h FVG)
            htf_fvg = features.get('htf_fvg', {})
            in_poi = False
            for idx, val in htf_fvg.get('FVG', {}).items():
                if htf_fvg['Bottom'][idx] * 0.9995 <= price <= htf_fvg['Top'][idx] * 1.0005:
                    in_poi = True; break

            if not in_poi:
                return json.dumps({"side": "None", "reason": "No HTF POI Confluence"})

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
                tp = price + (price - sl) * 2.0 # Target 1:2 RR min
                return json.dumps({"side": "Long", "entry_price": price, "stop_loss": sl, "take_profit": tp, "model_used": "Model 1", "reason": "Institutional POI + Sweep Detected"})
            
            if bear_sweep and bias != 'Bullish':
                sl = last_high * 1.003
                tp = price - (sl - price) * 2.0
                return json.dumps({"side": "Short", "entry_price": price, "stop_loss": sl, "take_profit": tp, "model_used": "Model 1", "reason": "Institutional POI + Sweep Detected"})

        except Exception as e:
            pass
        return json.dumps({"side": "None", "reason": "Insufficient Institutional Confluence"})

    def reflect_on_failure(self, trade_details, outcome):
        # Basic failure reflection
        prompt = f"Analyze failed ICT trade: {json.dumps(trade_details)}. Outcome: {outcome}. Provide a concise 'Corrected Mandate' to prevent this. Do not format with markdown, just provide a single sentence rule."
        corrected = self._call_llm(prompt)
        if corrected:
            with open(self.learnings_path, 'a') as f:
                f.write(f"\n- Post-Mortem ({pd.Timestamp.now()}): {corrected.strip()}\n")

        # We can also add it to mempalace if needed, but since mempalace setup in skills is complex
        # and mainly for hierarchical storage, we focus on appending to learnings.txt which is
        # explicitly passed as context to the agent in generate_hypothesis.

        return f"Logged reflection for trade."

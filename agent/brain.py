import json
import pandas as pd
import numpy as np
import requests
import os
from dotenv import load_dotenv
import sqlite3

load_dotenv()

class TradingBrain:
    def __init__(self, api_key=None):
        self.learnings_path = './learnings.txt'
        self.db_path = './logs/trading_memory.db'
        self.api_key = api_key or os.getenv("NVIDIA_NIM_API_KEY")

        if not os.path.exists('./logs'):
            os.makedirs('./logs')

        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS trades
                     (id TEXT PRIMARY KEY, side TEXT, entry REAL, sl REAL, tp REAL,
                      outcome TEXT, model TEXT, reason TEXT, timestamp TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS reflections
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_id TEXT, analysis TEXT, timestamp TEXT)''')
        conn.commit()
        conn.close()

    def _call_llm(self, prompt):
        if not self.api_key:
            print("NVIDIA_NIM_API_KEY not found.")
            return None
            
        try:
            url = "https://integrate.api.nvidia.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "meta/llama-3.3-70b-instruct",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 1024,
            }
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Extract JSON block if surrounded by markdown
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                return content[start:end+1]
            return content
        except Exception as e:
            print(f"LLM API Error: {e}")
            with open('./logs/api_errors.log', 'a') as f:
                f.write(f"\n--- {pd.Timestamp.now(tz='UTC')} ---\nError: {e}\n")
        return None

    def query(self, prompt):
        return self._call_llm(prompt)

    def generate_hypothesis(self, market_data, context=""):
        try:
            data = json.loads(market_data) if isinstance(market_data, str) else market_data
            
            # STAGE 1: INSTITUTIONAL FILTER (Local) - pre-filters to save API calls
            hypothesis_json = self._institutional_filter_v18(data)
            hypothesis = json.loads(hypothesis_json)
            
            if hypothesis.get('side') == 'None':
                return hypothesis_json

            # STAGE 2: NEURAL BRAIN (Remote)
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

FINAL DECISION MUST BE A VALID JSON OBJECT ONLY:
{{
  "side": "Long", "Short" or "None",
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
                except:
                    pass

            return hypothesis_json

        except Exception as e:
            print(f"Brain Error: {e}")
        return json.dumps({"side": "None", "reason": "Error"})

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

            fvg_data_htf = htf_fvg.get('FVG', {})
            top_htf = htf_fvg.get('Top', {})
            bottom_htf = htf_fvg.get('Bottom', {})

            if isinstance(fvg_data_htf, dict):
                 for idx, val in fvg_data_htf.items():
                    # val == 1 means Bullish FVG, val == -1 means Bearish FVG, check proximity
                    top_val = top_htf.get(idx)
                    bottom_val = bottom_htf.get(idx)
                    if top_val and bottom_val and not pd.isna(top_val) and not pd.isna(bottom_val):
                        if bottom_val * 0.9995 <= price <= top_val * 1.0005:
                            in_poi = True; break
            elif isinstance(fvg_data_htf, list):
                 # Array format
                 for i, val in enumerate(fvg_data_htf):
                    if pd.isna(val) or val == 0: continue
                    top_val = top_htf[i] if i < len(top_htf) else None
                    bottom_val = bottom_htf[i] if i < len(bottom_htf) else None
                    if top_val and bottom_val and not pd.isna(top_val) and not pd.isna(bottom_val):
                         if bottom_val * 0.9995 <= price <= top_val * 1.0005:
                            in_poi = True; break

            if not in_poi: return json.dumps({"side": "None", "reason": "No HTF POI Confluence"})

            # 3. Liquidity Sweep
            fvg_data = features.get('fvg', {})
            bottom_ltf = fvg_data.get('Bottom', {})
            top_ltf = fvg_data.get('Top', {})

            recent_lows = []
            recent_highs = []
            if isinstance(bottom_ltf, dict):
                 recent_lows = [v for v in bottom_ltf.values() if not pd.isna(v)]
                 recent_highs = [v for v in top_ltf.values() if not pd.isna(v)]
            elif isinstance(bottom_ltf, list):
                 recent_lows = [v for v in bottom_ltf if not pd.isna(v)]
                 recent_highs = [v for v in top_ltf if not pd.isna(v)]

            last_low = min(recent_lows[-5:]) if recent_lows else None
            last_high = max(recent_highs[-5:]) if recent_highs else None
            
            bull_sweep = last_low and price > last_low
            bear_sweep = last_high and price < last_high

            if bull_sweep and bias != 'Bearish':
                sl = last_low * 0.997
                tp = price + (price - sl) * 3.0 # Target 1:3 RR
                return json.dumps({"side": "Long", "entry_price": price, "stop_loss": sl, "take_profit": tp, "model_used": "Model 1", "reason": "Institutional POI + Sweep Detected"})
            
            if bear_sweep and bias != 'Bullish':
                sl = last_high * 1.003
                tp = price - (sl - price) * 3.0
                return json.dumps({"side": "Short", "entry_price": price, "stop_loss": sl, "take_profit": tp, "model_used": "Model 1", "reason": "Institutional POI + Sweep Detected"})

        except Exception as e:
            pass
        return json.dumps({"side": "None", "reason": "Insufficient Institutional Confluence"})

    def log_trade(self, trade_id, side, entry, sl, tp, outcome, model, reason):
        try:
             conn = sqlite3.connect(self.db_path)
             c = conn.cursor()
             c.execute('''INSERT INTO trades (id, side, entry, sl, tp, outcome, model, reason, timestamp)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (trade_id, side, entry, sl, tp, outcome, model, reason, str(pd.Timestamp.now(tz='UTC'))))
             conn.commit()
             conn.close()
        except Exception as e:
             print(f"Failed to log trade: {e}")

    def reflect_on_failure(self, trade_details, outcome):
        prompt = f"Analyze failed ICT trade: {json.dumps(trade_details)}. Outcome: {outcome}. Provide a concise 'Corrected Mandate' to prevent this in JSON format with key 'mandate'."
        corrected = self._call_llm(prompt)
        if corrected:
            try:
                res_json = json.loads(corrected)
                mandate = res_json.get('mandate', corrected)
                with open(self.learnings_path, 'a') as f:
                    f.write(f"\n--- Post-Mortem ({pd.Timestamp.now(tz='UTC')}) ---\n{mandate}\n")

                trade_id = trade_details.get('id', 'unknown')
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute('''INSERT INTO reflections (trade_id, analysis, timestamp)
                             VALUES (?, ?, ?)''',
                          (trade_id, str(mandate), str(pd.Timestamp.now(tz='UTC'))))
                conn.commit()
                conn.close()
            except Exception as e:
                pass
        return f"Logged failure reflection: {trade_details.get('id', 'unknown')}"

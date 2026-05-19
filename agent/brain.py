import json
import os
import requests
import time

class TradingBrain:
    def __init__(self, api_key=None):
        self.learnings_path = './learnings.txt'
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.model = "meta/llama-3.3-70b-instruct"
        self.last_call_time = 0
        self.rate_limit_delay = 60.0 / 40.0

    def _call_api(self, prompt):
        if not self.api_key:
            print("Warning: NVIDIA_API_KEY not found in environment.")
            return None

        now = time.time()
        time_since_last = now - self.last_call_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1024
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=60)
            self.last_call_time = time.time()
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    return content[start:end+1]
                return content
            elif response.status_code == 429:
                print("Rate limited by NVIDIA API. Retrying in 5 seconds...")
                time.sleep(5)
                return self._call_api(prompt)
            else:
                with open('./logs/api_errors.log', 'a') as f:
                    f.write(f"\n--- {time.time()} ---\nCode: {response.status_code}\nError: {response.text}\n")
                return None
        except Exception as e:
            print(f"API Error: {e}")
            return None

    def generate_hypothesis(self, market_data, context=""):
        try:
            data = json.loads(market_data) if isinstance(market_data, str) else market_data
            
            hypothesis_json = self._institutional_filter_v18(data)
            hypothesis = json.loads(hypothesis_json)
            
            if hypothesis.get('side') == 'None':
                return hypothesis_json

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
            response = self._call_api(prompt)
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
            features = data['features']
            
            if kz not in ['London', 'New York']:
                return json.dumps({"side": "None", "reason": "Outside Institutional Windows"})

            htf_fvg = features.get('htf_fvg', {})
            in_poi = False
            for idx, val in htf_fvg.get('FVG', {}).items():
                if htf_fvg['Bottom'][idx] * 0.9995 <= price <= htf_fvg['Top'][idx] * 1.0005:
                    in_poi = True; break
            if not in_poi: return json.dumps({"side": "None", "reason": "No HTF POI Confluence"})

            fvg_data = features.get('fvg', {})
            recent_lows = [v for v in fvg_data.get('Bottom', {}).values() if not pd.isna(v)]
            recent_highs = [v for v in fvg_data.get('Top', {}).values() if not pd.isna(v)]
            last_low = min(recent_lows[-5:]) if recent_lows else None
            last_high = max(recent_highs[-5:]) if recent_highs else None
            
            bull_sweep = last_low and price > last_low
            bear_sweep = last_high and price < last_high

            if bull_sweep and bias != 'Bearish':
                sl = last_low * 0.997
                tp = price + (price - sl) * 3.0
                return json.dumps({"side": "Long", "entry_price": price, "stop_loss": sl, "take_profit": tp, "model_used": "Model 1", "reason": "Institutional POI + Sweep Detected"})
            
            if bear_sweep and bias != 'Bullish':
                sl = last_high * 1.003
                tp = price - (sl - price) * 3.0
                return json.dumps({"side": "Short", "entry_price": price, "stop_loss": sl, "take_profit": tp, "model_used": "Model 1", "reason": "Institutional POI + Sweep Detected"})

        except: pass
        return json.dumps({"side": "None", "reason": "Insufficient Institutional Confluence"})

    def reflect_on_failure(self, trade_details, outcome):
        prompt = f"Analyze failed ICT trade: {json.dumps(trade_details)}. Outcome: {outcome}. Provide a concise 'Corrected Mandate' to prevent this. output in JSON Format: {{\n  \"reflection\": \"detailed reflection string\"\n}}"
        corrected = self._call_api(prompt)
        if corrected:
            try:
                res = json.loads(corrected)
                with open(self.learnings_path, 'a') as f:
                    f.write(f"\n--- Post-Mortem ({time.time()}) ---\n{res.get('reflection', corrected).strip()}\n")
            except:
                with open(self.learnings_path, 'a') as f:
                    f.write(f"\n--- Post-Mortem ({time.time()}) ---\n{corrected.strip()}\n")
        return f"Logged: {trade_details.get('id', 'unknown')}"

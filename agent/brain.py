import json
import pandas as pd
import numpy as np
import requests

import os
from dotenv import load_dotenv

load_dotenv()

class TradingBrain:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def query(self, prompt, context_messages=None):
        messages = [{"role": "system", "content": "You are an expert ICT scalper. Output strictly valid JSON without markdown wrapping or extra text."}]
        if context_messages:
            messages.extend(context_messages)
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "meta/llama-3.1-405b-instruct",
            "messages": messages,
            "temperature": 0.2,
            "top_p": 0.7,
            "max_tokens": 1024,
            "stream": False
        }

        try:
            response = requests.post(self.url, headers=self.headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Request Error: {e}")
            return None

    def generate_hypothesis(self, market_data, rules_context=""):
        try:
            data = json.loads(market_data) if isinstance(market_data, str) else market_data
            price = data.get('price', 0)
            bias = data.get('bias', 'Neutral')
            killzone = data.get('killzone', 'None')
            features = data.get('features', {})
            
            prompt = f"""
Market Data:
- Current Price: {price}
- Directional Bias: {bias}
- Killzone: {killzone}
- Recent Features: {json.dumps(features, indent=2)}

Rules:
{rules_context}

Analyze the data and determine if there is a valid ICT trading setup (e.g., FVG, OB, liquidity sweep).
Requirements:
1. ONLY take trades aligning with the Directional Bias unless there is a hyper-clear reversal setup.
2. The Take Profit to Stop Loss distance (Risk/Reward ratio) MUST be at least 1:2. If a 1:2 RR is not viable given the current setup structure, do not take the trade.
3. You must output a JSON object with EXACTLY the following keys:
   - "side": "Long", "Short", or "None"
   - "entry_price": float
   - "stop_loss": float
   - "take_profit": float
   - "reason": "string explaining the logic"
   - "confidence": float (0.0 to 1.0)
If no trade is valid, output {{"side": "None", "reason": "Explanation"}}

Output JUST the raw JSON string. Do not use markdown blocks like ```json.
"""
            res = self.query(prompt)
            if res:
                # Attempt to parse json
                res = res.strip()
                if res.startswith("```json"):
                    res = res[7:]
                if res.startswith("```"):
                    res = res[3:]
                if res.endswith("```"):
                    res = res[:-3]
                res = res.strip()

                parsed = json.loads(res)
                return json.dumps(parsed)

        except Exception as e:
            print(f"Brain Error: {e}")
            pass
            
        return json.dumps({"side": "None", "reason": "No setup or error parsing"})

    def reflect_on_failure(self, failure_patterns):
        prompt = f"""
We had the following failed setups:
{json.dumps(failure_patterns, indent=2)}

Please reflect on these mistakes as an ICT scalper. What went wrong? Were the stops too tight? Did we trade against HTF bias?
Generate an updated, explicit list of string rules to add to our strategy to avoid these specific failures in the future.
Output valid JSON: {{"rules": ["rule 1", "rule 2", ...]}}
"""
        res = self.query(prompt)
        if res:
            try:
                res = res.strip()
                if res.startswith("```json"):
                    res = res[7:]
                if res.startswith("```"):
                    res = res[3:]
                if res.endswith("```"):
                    res = res[:-3]
                res = res.strip()
                parsed = json.loads(res)
                return parsed.get("rules", [])
            except Exception as e:
                print(f"Reflection Parsing Error: {e}")
        return []


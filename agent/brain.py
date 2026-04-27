import json
import pandas as pd
import numpy as np
import os
import requests
import time

class TradingBrain:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.last_api_call = 0
        self.rpm_limit = 40
        self.min_interval = 60.0 / self.rpm_limit

    def query_llm(self, prompt):
        # Enforce rate limit
        elapsed = time.time() - self.last_api_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "meta/llama-3.3-70b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 512
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            self.last_api_call = time.time()
            if response.status_code == 200:
                res_json = response.json()
                return res_json['choices'][0]['message']['content']
            else:
                return None
        except Exception as e:
            return None

    def query(self, prompt):
        return self.query_llm(prompt)

    def generate_hypothesis(self, market_data, context=""):
        try:
            data = json.loads(market_data) if isinstance(market_data, str) else market_data
            price = data['price']
            bias = data.get('bias', 'Neutral')
            features = data['features']
            
            fvg_data = features.get('fvg', {})
            ob_data = features.get('ob', {})
            
            # Pre-filter: Only query LLM if there's a strong recent FVG or OB
            has_active_setup = False
            relevant_levels = []

            for idx, val in fvg_data.get('FVG', {}).items():
                if val != 0.0:
                    top = fvg_data['Top'][idx]
                    bot = fvg_data['Bottom'][idx]
                    # Check if price is near FVG
                    if abs(price - top) / price < 0.02 or abs(price - bot) / price < 0.02:
                        has_active_setup = True
                        relevant_levels.append(f"FVG ({val}): Top {top}, Bot {bot}")

            for idx, val in ob_data.get('OB', {}).items():
                if val != 0.0:
                    top = ob_data['Top'][idx]
                    bot = ob_data['Bottom'][idx]
                    if abs(price - top) / price < 0.02 or abs(price - bot) / price < 0.02:
                        has_active_setup = True
                        relevant_levels.append(f"OB ({val}): Top {top}, Bot {bot}")

            if not has_active_setup:
                return json.dumps({"side": "None", "reason": "No active setup nearby"})

            # Prompt the Agent
            prompt = f"""
You are an autonomous ICT scalping agent.
Current Price: {price}
HTF Bias: {bias}
Nearby ICT Levels: {', '.join(relevant_levels)}

Your goal is an 85%+ win rate with a minimum 1:2 Risk/Reward ratio.
Analyze the setup. If valid, reply ONLY with a valid JSON in the exact following format:
{{
    "side": "Long" or "Short" or "None",
    "entry_price": float,
    "stop_loss": float,
    "take_profit": float,
    "reason": "Brief ICT narrative"
}}
Ensure the risk/reward ratio is strictly >= 2.0. If not a high-probability setup, return "side": "None".
"""

            response = self.query_llm(prompt)
            if response:
                # Find JSON bounds in case LLM wraps it
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end != 0:
                    json_str = response[start:end]
                    try:
                        setup = json.loads(json_str)
                        return json.dumps(setup)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            pass
            
        return json.dumps({"side": "None", "reason": "Error or no setup"})

    def reflect_on_failure(self, trade_details, outcome):
        # Use LLM to reflect and analyze failure
        prompt = f"Trade failed. Details: {json.dumps(trade_details)}. What went wrong in the ICT narrative?"
        return self.query_llm(prompt) or f"Fail: {trade_details['id']} - {outcome}"

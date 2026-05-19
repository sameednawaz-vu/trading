import os
import json
import requests
import time

class LLMIntegration:
    def __init__(self):
        self.api_key = os.getenv("NVIDIA_API_KEY")
        self.url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.model = "meta/llama-3.3-70b-instruct"
        self.last_call_time = 0
        self.rate_limit_delay = 60.0 / 40.0 # 40 RPM

    def _call_api(self, prompt):
        if not self.api_key:
            print("Warning: NVIDIA_API_KEY not found in environment.")
            return None

        # Respect 40 RPM rate limit
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
                return data['choices'][0]['message']['content']
            elif response.status_code == 429:
                print("Rate limited by NVIDIA API. Retrying in 5 seconds...")
                time.sleep(5)
                return self._call_api(prompt)
            else:
                print(f"API Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"Request Error: {e}")
            return None

    def generate_response(self, system_prompt, user_prompt):
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        return self._call_api(full_prompt)

    def parse_json_response(self, text):
        if not text: return None
        try:
            return json.loads(text)
        except:
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                try: return json.loads(text[start:end+1])
                except: pass
        return None

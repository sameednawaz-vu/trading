import os
import json
import requests
import time

class LLMIntegration:
    def __init__(self):
        self.api_key = os.getenv("NVIDIA_API_KEY")
        if not self.api_key:
            print("WARNING: NVIDIA_API_KEY is not set.")
        self.url = "https://integrate.api.nvidia.com/v1/chat/completions"

    def generate_response(self, system_prompt, user_prompt):
        if not self.api_key:
            return None
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "meta/llama-3.3-70b-instruct",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 1024,
            "temperature": 0.2
        }

        # Rate limit handling (40 RPM limit)
        retries = 3
        for attempt in range(retries):
            try:
                response = requests.post(self.url, headers=headers, json=payload, timeout=60)
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']
                elif response.status_code == 429:
                    print(f"Rate limited. Waiting {2**attempt} seconds...")
                    time.sleep(2**attempt)
                else:
                    print(f"NVIDIA API Error {response.status_code}: {response.text}")
                    break
            except Exception as e:
                print(f"Request Error: {e}")
                time.sleep(1)

        return None

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

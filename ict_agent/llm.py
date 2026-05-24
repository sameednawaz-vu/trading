import os
import json
import time
import subprocess
import tempfile
from dotenv import load_dotenv

load_dotenv()

class LLMIntegration:
    def __init__(self):
        # The audit mentioned JULES_API_KEY might be needed by the CLI
        self.api_key = os.getenv("JULES_API_KEY_ACCOUNT_2") or os.getenv("NVIDIA_API_KEY")

    def _call_nvidia_api(self, prompt):
        import requests
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
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
            # Enforce strict 40 RPM rate limit locally (sleep 1.5s per request)
            time.sleep(1.5)
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Try to extract JSON if wrapped in markdown
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    return content[start:end+1]
                return content
            else:
                print(f"API Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"Request Error: {e}")
            return None

    def generate_response(self, system_prompt, user_prompt):
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        return self._call_nvidia_api(full_prompt)

    def parse_json_response(self, text):
        if not text: return None
        try:
            return json.loads(text)
        except:
            # Naive cleanup
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                try: return json.loads(text[start:end+1])
                except: pass
        return None

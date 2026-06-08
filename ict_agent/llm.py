import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

class LLMIntegration:
    def __init__(self):
        self.api_key = os.getenv("JULES_API_KEY_ACCOUNT_2") or os.getenv("JULES_API_KEY")
        self.api_url = "https://integrate.api.nvidia.com/v1/chat/completions"

    def _call_llm_api(self, prompt):
        if not self.api_key:
            print("Error: NVIDIA API Key not found.")
            return None
            
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
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                resp_json = response.json()
                content = resp_json['choices'][0]['message']['content']
                
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    return content[start:end+1]
                return content
            else:
                os.makedirs('./logs', exist_ok=True)
                with open('./logs/cli_errors.log', 'a') as f:
                    f.write(f"\n--- {datetime.now(timezone.utc)} ---\nStatus Code: {response.status_code}\nError: {response.text}\n")
                print(f"API Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Request Error: {e}")
        return None

    def generate_response(self, system_prompt, user_prompt):
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        return self._call_llm_api(full_prompt)

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

if __name__ == "__main__":
    llm = LLMIntegration()
    # Simple syntax check, without full API key execution
    print("LLMIntegration class loaded successfully")

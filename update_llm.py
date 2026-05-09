import re
with open("ict_agent/llm.py", "r") as f:
    content = f.read()
nim_body = """    def _call_nvidia_nim(self, prompt):
        if not self.api_key:
            return None

        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "meta/llama-3.3-70b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1024,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]

                # Extract JSON if markdown wrapped
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    return content[start:end+1]
                return content
        except Exception as e:
            print(f"Nvidia NIM API Error: {e}")
        return None"""

content = re.sub(r'    def _call_nvidia_nim\(self, prompt\):.*?return None', nim_body, content, flags=re.DOTALL)
with open("ict_agent/llm.py", "w") as f:
    f.write(content)

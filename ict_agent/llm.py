import os
import json
import time
import subprocess
import tempfile

class LLMIntegration:
    def __init__(self):
        # The audit mentioned JULES_API_KEY might be needed by the CLI
        self.api_key = os.getenv("JULES_API_KEY_ACCOUNT_2")

    def _call_gemini_cli(self, prompt):
        try:
            env = os.environ.copy()
            if self.api_key:
                # Ensure the CLI gets the key it expects. 
                # If it's gemini-cli, it might need GEMINI_API_KEY
                env["GEMINI_API_KEY"] = self.api_key
                env["JULES_API_KEY"] = self.api_key
            
            # Use a temporary file to avoid shell escaping issues with large prompts
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tf:
                tf.write(prompt)
                temp_name = tf.name

            try:
                # Run gemini command using the file as input
                # -p - tells gemini to read from stdin, but we can also use -p <prompt>
                # However, for very large prompts, we'll pipe the file
                with open(temp_name, 'r', encoding='utf-8') as pf:
                    result = subprocess.run(
                        ['gemini', '--prompt', '-', '--output-format', 'json', '--skip-trust'],
                        stdin=pf,
                        capture_output=True, 
                        text=True, 
                        env=env, 
                        timeout=180
                    )
                
                if result.returncode == 0:
                    try:
                        full_json = json.loads(result.stdout.strip())
                        # Gemini CLI JSON output usually has a 'response' field
                        content = full_json.get('response', '')
                        
                        # Extract inner JSON if the model wrapped it in markdown
                        start = content.find('{')
                        end = content.rfind('}')
                        if start != -1 and end != -1:
                            return content[start:end+1]
                        return content
                    except json.JSONDecodeError:
                        # Fallback if stdout is not JSON but the raw response
                        return result.stdout.strip()
                else:
                    print(f"CLI Error {result.returncode}: {result.stderr}")
            finally:
                if os.path.exists(temp_name):
                    os.remove(temp_name)
                    
        except Exception as e:
            print(f"Subprocess Error: {e}")
        return None

    def generate_response(self, system_prompt, user_prompt):
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        return self._call_gemini_cli(full_prompt)

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

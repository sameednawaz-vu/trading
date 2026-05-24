from agent.brain import TradingBrain
import os

import os

key = os.getenv("NVIDIA_API_KEY", "YOUR_API_KEY")
brain = TradingBrain(api_key=key)
res = brain._call_nvidia_api("Test message. Reply with 'OK'.")
print(f"Brain Response: {res}")

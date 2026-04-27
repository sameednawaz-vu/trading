from agent.brain import TradingBrain
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("NVIDIA_API_KEY")
brain = TradingBrain(api_key=key)
res = brain.query("Test message. Reply with 'OK'.")
print(f"Brain Response: {res}")

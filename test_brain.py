from agent.brain import TradingBrain
import os

key = "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"
brain = TradingBrain(api_key=key)
res = brain.query("Test message. Reply with 'OK'.")
print(f"Brain Response: {res}")

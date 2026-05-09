import sys
sys.path.append('.')
from ict_agent.agent import TradingAgent
import json
agent = TradingAgent()
agent.llm.api_key = "test_key"
res = agent.llm.generate_response("You are an ICT trader", "Is BTC bullish?")
print("Result:", res)

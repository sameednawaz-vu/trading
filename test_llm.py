import sys
sys.path.append('.')
from ict_agent.agent import TradingAgent

agent = TradingAgent()
print(agent.llm.api_key)

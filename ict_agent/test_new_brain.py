
import json
import sys
import os
sys.path.append(r'..')

from ict_agent.agent import TradingAgent

def test_new_brain():
    agent = TradingAgent()
    mock_data = {
        "price": 60000,
        "bias": "BULLISH",
        "killzone": "London",
        "features": {
            "fvg": {"FVG": {"0": 1.0}, "Top": {"0": 61000}, "Bottom": {"0": 60500}},
            "htf_fvg": {"FVG": {"0": 1.0}, "Top": {"0": 62000}, "Bottom": {"0": 59000}}
        }
    }
    print("ACEO | Testing Evolved LLM Integration...")
    res = agent.propose_trade(mock_data, "BULLISH")
    print(f"RESULT: {res}")

if __name__ == "__main__":
    test_new_brain()

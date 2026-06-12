import json
import sys
import os

# Ensure current dir is in path
sys.path.append(os.path.abspath('.'))

from agent.brain import TradingBrain

def test_new_brain():
    brain = TradingBrain()
    mock_data = {
        "price": 60000,
        "bias": "Bullish",
        "killzone": "London",
        "features": {
            "fvg": {"FVG": {"0": 1.0}, "Top": {"0": 61000}, "Bottom": {"0": 60500}},
            "htf_fvg": {"FVG": {"0": 1.0}, "Top": {"0": 62000}, "Bottom": {"0": 59000}}
        }
    }
    res = brain.generate_hypothesis(mock_data)
    assert isinstance(res, str)
    assert 'side' in json.loads(res)

if __name__ == "__main__":
    test_new_brain()

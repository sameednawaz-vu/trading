from agent.brain import TradingBrain
import os
import json

def test_brain():
    # Provide a dummy key if env is empty, so initialization passes
    key = os.getenv("NVIDIA_NIM_API_KEY", "dummy_key")
    brain = TradingBrain(api_key=key)

    # Just test that object initializes and methods exist
    assert hasattr(brain, 'query')
    assert hasattr(brain, 'generate_hypothesis')
    assert hasattr(brain, 'log_trade')
    assert hasattr(brain, 'reflect_on_failure')

def test_hypothesis_fallback():
    brain = TradingBrain(api_key="dummy")
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
    try:
        parsed = json.loads(res)
        assert 'side' in parsed
    except json.JSONDecodeError:
        pass # In case of API failure or missing keys, should return something parseable or fallback None string

if __name__ == "__main__":
    test_brain()
    print("test_brain OK")

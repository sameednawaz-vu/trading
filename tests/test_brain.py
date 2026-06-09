import pytest
import json
from agent.brain import TradingBrain

@pytest.fixture
def brain():
    return TradingBrain(api_key="dummy") # doesn't matter, we test local filter

def test_institutional_filter(brain):
    # Test valid setup
    data = {
        "price": 100,
        "bias": "Bullish",
        "killzone": "New York",
        "features": {
            "htf_fvg": {"FVG": {0: 1}, "Top": {0: 105}, "Bottom": {0: 95}},
            "fvg": {"Top": {0: 110}, "Bottom": {0: 98}}
        }
    }

    res_json = brain._institutional_filter_v18(data)
    res = json.loads(res_json)

    # It swept 98, so it's a bull sweep, bias is bullish, in NY killzone, inside HTF FVG (95-105).
    assert res['side'] == "Long"
    assert res['entry_price'] == 100

def test_institutional_filter_fail(brain):
    # Test invalid setup (outside killzone)
    data = {
        "price": 100,
        "bias": "Bullish",
        "killzone": "None",
        "features": {
            "htf_fvg": {"FVG": {0: 1}, "Top": {0: 105}, "Bottom": {0: 95}},
            "fvg": {"Top": {0: 110}, "Bottom": {0: 98}}
        }
    }

    res_json = brain._institutional_filter_v18(data)
    res = json.loads(res_json)
    assert res['side'] == "None"

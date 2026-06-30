import pytest
from agent.brain import TradingBrain
import os

def test_nvidia_api_call():
    # Use environment variable; fail gracefully if not provided
    api_key = os.getenv("JULES_API_KEY_ACCOUNT_2")
    if not api_key:
        pytest.skip("No API key provided, skipping test.")

    brain = TradingBrain()
    prompt = "Reply strictly with the word 'PONG'."
    response = brain._call_nvidia_api(prompt)
    assert response is not None
    assert 'PONG' in response.upper()

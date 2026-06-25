import json
import pandas as pd
from agent.brain import TradingBrain
from unittest.mock import patch, MagicMock

@patch('requests.post')
def test_brain_call_nim_api(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'choices': [
            {'message': {'content': '```json\n{"side": "Long", "entry_price": 60000, "stop_loss": 59000, "take_profit": 63000, "model_used": "Model 1", "reason": "Test", "confidence": 0.9}\n```'}}
        ]
    }
    mock_post.return_value = mock_response

    brain = TradingBrain('dummy_key')
    response = brain._call_nim_api('test prompt')

    assert response is not None
    assert '{"side": "Long"' in response

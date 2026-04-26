from agent.brain import TradingBrain
import json

brain = TradingBrain()

# Test general query
res = brain.query("Test message. Reply with a json object containing 'status': 'OK'.")
print(f"Query Response: {res}")

# Test generate_hypothesis
mock_data = {
    "price": 60000,
    "bias": "Bullish",
    "killzone": "New York",
    "features": {
        "fvg": {
            "FVG": { "0": 1.0 },
            "Top": { "0": 60100 },
            "Bottom": { "0": 59900 }
        }
    }
}
res_hyp = brain.generate_hypothesis(mock_data)
print(f"Hypothesis: {res_hyp}")

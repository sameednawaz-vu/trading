from agent.brain import TradingBrain
import json

brain = TradingBrain()
market_data = {
    "price": 60000,
    "bias": "Bullish",
    "killzone": "New York",
    "features": {
        "fvg": {
            "FVG": {"0": 1},
            "Bottom": {"0": 59900},
            "Top": {"0": 59950}
        },
        "ob": {},
        "liquidity": {},
        "htf_fvg": {}
    }
}
print("Testing generation of hypothesis...")
hypothesis = brain.generate_hypothesis(market_data)
print(hypothesis)
print("Brain logic tested.")

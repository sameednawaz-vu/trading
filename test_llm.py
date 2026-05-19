from dotenv import load_dotenv
load_dotenv()
from ict_agent.llm import LLMIntegration
from agent.brain import TradingBrain

llm = LLMIntegration()
print("LLM API Key exists:", bool(llm.api_key))
resp = llm.generate_response("You are a helpful assistant.", "Reply with 'Hello'.")
print("LLM Response:", resp)

brain = TradingBrain()
print("Brain API Key exists:", bool(brain.api_key))
test_data = {
    "price": 60000,
    "bias": "Bullish",
    "killzone": "New York",
    "features": {
        "htf_fvg": {"FVG": {"1": True}, "Bottom": {"1": 59000}, "Top": {"1": 61000}},
        "fvg": {"Bottom": {"1": 59500}, "Top": {"1": 60500}}
    }
}
resp2 = brain.generate_hypothesis(test_data)
print("Brain Hypothesis:", resp2)

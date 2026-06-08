from agent.agent_brain import TradingBrain
import os

# Use an environment variable or dummy key for testing to prevent hardcoding secrets
key = os.getenv("JULES_API_KEY_ACCOUNT_2", "dummy_test_key")
brain = TradingBrain(api_key=key)

def test_brain_loads():
    assert brain is not None
    print("Brain loaded successfully.")

if __name__ == "__main__":
    test_brain_loads()

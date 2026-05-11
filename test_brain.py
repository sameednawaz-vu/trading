def test_brain():
    from agent.brain import TradingBrain
    import os

    brain = TradingBrain()
    # It requires an API key which isn't available, so we just check it instantiates
    assert brain is not None

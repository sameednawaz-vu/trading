import pytest
from agent.brain import TradingBrain
from ict_engine import ICTEngine
from agent.memory import MemoryManager
import pandas as pd
from datetime import datetime, timezone

def test_brain_initialization():
    brain = TradingBrain()
    assert brain.nim_url == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert brain.rpm_limit == 40

def test_engine_initialization():
    engine = ICTEngine()
    assert hasattr(engine, 'compute_smc_features')

def test_memory_manager():
    mem = MemoryManager(db_path='./logs/test_memory.db', mempalace_path='./test_mempalace')
    assert mem.db_path == './logs/test_memory.db'
    trade_id = mem.log_trade({
        'symbol': 'BTC/USD',
        'timeframe': '5m',
        'side': 'Long',
        'entry_price': 60000,
        'stop_loss': 59000,
        'take_profit': 62000,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    assert trade_id > 0

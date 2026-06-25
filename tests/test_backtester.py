import pytest
from execution.backtester import Backtester
import pandas as pd
from datetime import datetime, timezone

def test_backtester_init():
    bt = Backtester('BTC/USD', '5m', '1h')
    assert bt.symbol == 'BTC/USD'
    assert bt.execution_tf == '5m'
    assert bt.bias_tf == '1h'

def test_backtester_final_report():
    bt = Backtester('BTC/USD', '5m', '1h')
    bt.trades_history = [{'result': 'success', 'pnl': 100, 'timestamp': datetime.now(timezone.utc)}]
    bt.final_report()
    assert bt.balance == 10000 # Since we didn't add pnl in this test directly to balance

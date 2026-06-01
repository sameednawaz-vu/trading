import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta
from src.backtest import Backtester

def test_htf_context_lookahead_bias():
    b = Backtester()

    # Dummy HTF (1h) data
    htf_data = []
    base_time = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
    for i in range(5):
        htf_data.append({
            'timestamp': base_time + timedelta(hours=i),
            'open': 100, 'high': 105, 'low': 95, 'close': 102, 'volume': 1000
        })
    htf_df = pd.DataFrame(htf_data)

    # Current time is 12:30 (middle of the 12:00-13:00 candle)
    # The 12:00 candle hasn't closed yet. The last closed candle is 11:00 (closed at 12:00)
    current_time = datetime(2023, 1, 1, 12, 30, tzinfo=timezone.utc)

    past_htf = b.get_htf_context(htf_df, current_time)

    assert len(past_htf) == 2
    # The latest included should be the 11:00 candle
    assert past_htf.iloc[-1]['timestamp'] == base_time + timedelta(hours=1)

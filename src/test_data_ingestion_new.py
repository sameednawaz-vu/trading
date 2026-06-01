import pytest
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import MagicMock
from src.data_ingestion import DataIngestor

def test_kraken_initialization():
    ingestor = DataIngestor(exchange_id='kraken')
    assert ingestor.exchange.id == 'kraken'

def test_fetch_resample_3m():
    ingestor = DataIngestor()

    # Mock ccxt exchange fetch_ohlcv to return dummy 1m data
    ingestor.exchange.fetch_ohlcv = MagicMock(return_value=[
        [1672531200000, 100, 105, 95, 102, 1000], # 00:00
        [1672531260000, 102, 103, 101, 103, 500], # 00:01
        [1672531320000, 103, 110, 102, 108, 1500] # 00:02
    ])

    # Needs a smaller limit hack for testing to end loop
    ingestor.exchange.id = 'binance' # forces limit to 1000

    start = "2023-01-01T00:00:00Z"
    end = "2023-01-01T00:03:00Z"

    df = ingestor.fetch_historical_data("BTC/USD", "3m", start, end)

    assert len(df) == 1

    # Open of 1st, High of all, Low of all, Close of last, Sum of vol
    assert df.iloc[0]['open'] == 100
    assert df.iloc[0]['high'] == 110
    assert df.iloc[0]['low'] == 95
    assert df.iloc[0]['close'] == 108
    assert df.iloc[0]['volume'] == 3000

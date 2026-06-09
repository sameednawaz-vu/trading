import pytest
import pandas as pd
import json
import os
from data_ingestion import DataIngestor

@pytest.fixture
def ingestor():
    return DataIngestor()

def test_fetch_and_resample(ingestor, tmp_path):
    ingestor.data_path = str(tmp_path)

    # Very short timeframe just to test functionality
    df_1m = ingestor.fetch_historical_data("BTC/USD", "1m", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z")
    assert df_1m is not None
    assert not df_1m.empty
    assert 'timestamp' in df_1m.columns
    assert df_1m['timestamp'].dt.tz is not None # Should be timezone aware

    df_3m = ingestor.resample_1m_to_3m(df_1m, "BTC/USD")
    assert df_3m is not None
    assert not df_3m.empty
    assert len(df_3m) < len(df_1m)

def test_load_full_data(ingestor, tmp_path):
    ingestor.data_path = str(tmp_path)

    # Create fake data
    df = pd.DataFrame({'timestamp': ['2024-01-01 00:00:00'], 'close': [100]})
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC')
    path = os.path.join(tmp_path, "TEST_USD_1h_full.csv")
    df.to_csv(path, index=False)

    loaded = ingestor.load_full_data("TEST/USD", "1h")
    assert loaded is not None
    assert loaded['timestamp'].dt.tz is not None

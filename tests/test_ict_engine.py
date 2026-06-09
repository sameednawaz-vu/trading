import pytest
import pandas as pd
import numpy as np
from ict_engine import ICTEngine
from datetime import datetime

@pytest.fixture
def engine():
    return ICTEngine()

def test_compute_smc_features(engine):
    # Create a dummy dataframe that looks like OHLCV
    dates = pd.date_range("2024-01-01", periods=100, freq="1h")
    df = pd.DataFrame({
        'open': np.random.rand(100) * 100,
        'high': np.random.rand(100) * 100 + 10,
        'low': np.random.rand(100) * 100 - 10,
        'close': np.random.rand(100) * 100,
        'volume': np.random.rand(100) * 1000
    }, index=dates)

    # The library doesn't strictly need index, but it needs columns
    features = engine.compute_smc_features(df)

    assert 'fvg' in features
    assert 'swing_hl' in features
    assert 'ob' in features
    assert 'liquidity' in features

    # check that we didn't mutate df
    assert df.columns.tolist() == ['open', 'high', 'low', 'close', 'volume']

def test_killzone(engine):
    london_time = datetime(2024, 1, 1, 8, 30)
    ny_time = datetime(2024, 1, 1, 13, 30)
    other_time = datetime(2024, 1, 1, 18, 0)

    assert engine.is_killzone(london_time) == "London"
    assert engine.is_killzone(ny_time) == "New York"
    assert engine.is_killzone(other_time) is None

import pytest
import pandas as pd
from data_ingestion import DataIngestor
import os

def test_data_resampling():
    ingestor = DataIngestor('kraken')
    # Use existing 1m file to test resampling
    df_1m = pd.read_csv('./data/BTC_USD_1m_full.csv', parse_dates=['timestamp'])
    df_1m.set_index('timestamp', inplace=True)

    resample_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }

    df_3m = df_1m.resample('3min').agg(resample_dict).dropna()
    assert len(df_3m) > 0
    # Check frequency difference approx 3x
    assert (len(df_1m) / len(df_3m)) >= 2.5

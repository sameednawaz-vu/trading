import ccxt
import pandas as pd
from datetime import datetime, timezone, timedelta

exchange = ccxt.kraken()
symbol = 'BTC/USD'
timeframe = '1m'
since = exchange.parse8601('2023-01-01T00:00:00Z')

ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=720)
print(f"Fetched {len(ohlcv)} candles from {pd.to_datetime(ohlcv[0][0], unit='ms')} to {pd.to_datetime(ohlcv[-1][0], unit='ms')}")

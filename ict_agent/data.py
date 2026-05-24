import ccxt
import pandas as pd
import os
import json
import time

CACHE_DIR = r"./ict_agent/data_cache"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def fetch_ohlcv(symbol, timeframe, limit=4000, use_cache=True):
    # Adjust for kraken and USD
    safe_symbol = symbol.replace("/", "_").replace("USDT", "USD")
    cache_file = os.path.join(CACHE_DIR, f"{safe_symbol}_{timeframe}_{limit}.json")
    
    if use_cache and os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            data = json.load(f)
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df

    exchange = ccxt.kraken({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    fetch_symbol = symbol.replace("USDT", "USD")
    if "/" not in fetch_symbol:
        if fetch_symbol.endswith("USD"):
            fetch_symbol = fetch_symbol[:-3] + "/USD"
    try:
        all_ohlcv = []
        since = exchange.parse8601('2024-01-01T00:00:00Z')
        
        while len(all_ohlcv) < limit:
            ohlcv = None
            retries = 5

            # Fetch 1m data and resample if 3m is requested since Kraken doesn't support 3m
            kraken_tf = timeframe if timeframe != '3m' else '1m'

            for attempt in range(retries):
                try:
                    ohlcv = exchange.fetch_ohlcv(fetch_symbol, kraken_tf, limit=720, since=since)
                    break
                except Exception as e:
                    if "Too many requests" in str(e) or "EGeneral" in str(e):
                        wait_time = 2 ** attempt
                        print(f"Rate limited on {symbol} {kraken_tf}, waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise e
            
            if not ohlcv: 
                break
                
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            time.sleep(1.0)
            
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        if timeframe == '3m':
            df = df.set_index('timestamp').resample('3min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna().reset_index()

        df = df.head(limit)

        with open(cache_file, "w") as f:
            # Need to convert timestamp back to int ms for caching
            cache_df = df.copy()
            import numpy as np
            cache_df['timestamp'] = cache_df['timestamp'].astype(np.int64) // 10**6
            json.dump(cache_df.values.tolist(), f)
            
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol} {timeframe}: {e}")
        return None

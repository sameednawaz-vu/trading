import ccxt
import pandas as pd
import os
import json
import time
from datetime import datetime, timezone

CACHE_DIR = r"./data_cache"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def fetch_ohlcv(symbol, timeframe, limit=4000, use_cache=True):
    safe_symbol = symbol.replace("/", "_")
    cache_file = os.path.join(CACHE_DIR, f"{safe_symbol}_{timeframe}_{limit}.json")
    
    if use_cache and os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            data = json.load(f)
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df

    exchange = ccxt.kraken({
        'enableRateLimit': True,
    })
    
    # Ensure symbol ends with USD
    fetch_symbol = symbol
    if fetch_symbol.endswith("USDT"):
        fetch_symbol = fetch_symbol.replace("USDT", "USD")

    fetch_timeframe = '1m' if timeframe == '3m' else timeframe

    try:
        all_ohlcv = []
        since = exchange.parse8601('2023-01-01T00:00:00Z')
        
        while len(all_ohlcv) < (limit * 3 if timeframe == '3m' else limit):
            ohlcv = None
            retries = 5
            for attempt in range(retries):
                try:
                    ohlcv = exchange.fetch_ohlcv(fetch_symbol, fetch_timeframe, limit=720, since=since)
                    break
                except Exception as e:
                    if "Too many requests" in str(e) or "EGeneral" in str(e) or "Rate limit" in str(e):
                        wait_time = 2 ** attempt
                        print(f"Rate limited on {symbol} {timeframe}, waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise e
            
            if not ohlcv: 
                break
                
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            time.sleep(1.5)
            
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        if timeframe == '3m':
            df = df.set_index('timestamp')
            df = df.resample('3min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna().reset_index()

        df = df.tail(limit).reset_index(drop=True)

        # Save cache
        # Convert timestamp to ms for json
        cache_data = df.copy()
        cache_data['timestamp'] = cache_data['timestamp'].astype('int64') // 10**6
        with open(cache_file, "w") as f:
            json.dump(cache_data.values.tolist(), f)
            
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol} {timeframe}: {e}")
        return None

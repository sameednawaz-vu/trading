import ccxt
import pandas as pd
import os
import json
import time

CACHE_DIR = r"E:\TRADING\ict_agent\data_cache"

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

    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    fetch_symbol = symbol.replace("/", "") if "/" in symbol else symbol
    if not fetch_symbol.endswith("USDT") and not fetch_symbol.endswith("BUSD"):
        fetch_symbol = fetch_symbol.replace("USD", "USDT")
    try:
        all_ohlcv = []
        since = exchange.parse8601('2024-01-01T00:00:00Z')
        
        while len(all_ohlcv) < limit:
            ohlcv = None
            retries = 5
            for attempt in range(retries):
                try:
                    ohlcv = exchange.fetch_ohlcv(fetch_symbol, timeframe, limit=720, since=since)
                    break
                except Exception as e:
                    if "Too many requests" in str(e) or "EGeneral" in str(e):
                        wait_time = 2 ** attempt
                        print(f"Rate limited on {symbol} {timeframe}, waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise e
            
            if not ohlcv: 
                break
                
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            time.sleep(1.0)
            
        with open(cache_file, "w") as f:
            json.dump(all_ohlcv[:limit], f)
            
        df = pd.DataFrame(all_ohlcv[:limit], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol} {timeframe}: {e}")
        return None

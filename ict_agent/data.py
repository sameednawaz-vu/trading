import ccxt
import pandas as pd
import os
import json
import time

CACHE_DIR = "./data_cache"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def fetch_ohlcv(symbol, timeframe, limit=4000, use_cache=True):
    safe_symbol = symbol.replace("/", "_")
    cache_file = os.path.join(CACHE_DIR, f"{safe_symbol}_{timeframe}_{limit}.json")
    
    if use_cache and os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            data = json.load(f)
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            return df

    exchange = ccxt.kraken({
        'enableRateLimit': True,
    })
    
    # Clean symbol for Kraken (e.g. BTC/USD or XBT/USD is expected, let ccxt handle generic mapping usually, but ensure it ends in USD)
    fetch_symbol = symbol.replace("USDT", "USD")

    fetch_tf = '1m' if timeframe == '3m' else timeframe

    # Adjust limit for 1m fetch to have enough 3m candles
    fetch_limit = limit * 3 if timeframe == '3m' else limit

    try:
        all_ohlcv = []
        # Calculate 'since' timestamp to get roughly 'limit' candles
        # Note: Kraken max is 720 per call

        # A rough heuristic for 'since'
        now = int(time.time() * 1000)
        tf_ms = exchange.parse_timeframe(fetch_tf) * 1000
        since = now - (fetch_limit * tf_ms)
        
        while len(all_ohlcv) < fetch_limit:
            ohlcv = None
            retries = 5
            for attempt in range(retries):
                try:
                    # Request up to 720 candles
                    req_limit = min(720, fetch_limit - len(all_ohlcv))
                    ohlcv = exchange.fetch_ohlcv(fetch_symbol, fetch_tf, limit=req_limit, since=since)
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
            time.sleep(exchange.rateLimit / 1000)
            
        with open(cache_file, "w") as f:
            json.dump(all_ohlcv[:fetch_limit], f)

        df = pd.DataFrame(all_ohlcv[:fetch_limit], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)

        if timeframe == '3m':
            df.set_index('timestamp', inplace=True)
            df = df.resample('3min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna().reset_index()
            # truncate to requested limit
            df = df.tail(limit)
            
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol} {timeframe}: {e}")
        return None

if __name__ == "__main__":
    df = fetch_ohlcv("BTC/USD", "3m", limit=100, use_cache=False)
    print(df.tail())

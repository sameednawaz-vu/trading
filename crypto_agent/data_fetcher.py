import ccxt
import pandas as pd
import time
import os
from datetime import datetime, timedelta, timezone

def fetch_data(symbol, timeframe, days=30):
    print(f"Fetching {symbol} {timeframe} data for last {days} days...")
    # Use OKX instead of Binance to avoid geo-restriction in test environment
    exchange = ccxt.okx({
        'enableRateLimit': True,
    })

    since = exchange.parse8601((datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace('+00:00', 'Z'))
    all_ohlcvs = []

    while True:
        try:
            ohlcvs = exchange.fetch_ohlcv(symbol, timeframe, since, limit=100)
            if not len(ohlcvs):
                break
            all_ohlcvs += ohlcvs
            since = ohlcvs[-1][0] + 1
            if len(all_ohlcvs) > 2000:
                break
            time.sleep(0.1) # Respect rate limits
        except Exception as e:
            print(f"Error: {e}")
            break

    if all_ohlcvs:
        df = pd.DataFrame(all_ohlcvs, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Save
        os.makedirs('data', exist_ok=True)
        filename = f"data/{symbol.replace('/', '_')}_{timeframe}.csv"
        df.to_csv(filename, index=False)
        print(f"Saved {filename} with {len(df)} rows")
    else:
        print(f"No data returned for {symbol} {timeframe}")

if __name__ == "__main__":
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']
    timeframes = ['3m', '5m', '15m', '30m']

    for symbol in symbols:
        for tf in timeframes:
            # Note OKX has BNB but volume might be low, let's keep it and test
            # OKX timeframes: 3m might be supported, let's check
            try:
                fetch_data(symbol, tf, days=7)
            except Exception as e:
                print(f"Failed to fetch {symbol} {tf}: {e}")

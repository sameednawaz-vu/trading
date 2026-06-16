import ccxt
import pandas as pd
import time
import os
from datetime import datetime, timedelta, timezone

def fetch_data(symbol, timeframe, days=7):
    print(f"Fetching {symbol} {timeframe} data for last {days} days...")
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
            time.sleep(0.1)
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            break

    if all_ohlcvs:
        df = pd.DataFrame(all_ohlcvs, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        os.makedirs('data', exist_ok=True)
        filename = f"data/{symbol.replace('/', '_')}_{timeframe}.csv"
        df.to_csv(filename, index=False)
        print(f"Saved {filename} with {len(df)} rows")
    else:
        print(f"No data returned for {symbol} {timeframe}")

if __name__ == "__main__":
    symbols = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT',
        'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT',
        'MATIC/USDT', 'LTC/USDT', 'BCH/USDT', 'UNI/USDT', 'ATOM/USDT',
        'XLM/USDT', 'NEAR/USDT', 'APT/USDT', 'ARB/USDT', 'INJ/USDT'
    ]
    timeframes = ['15m', '30m'] # Reduced timeframes just for the backtest speed, 3m/5m would generate way too many LLM calls

    for symbol in symbols:
        for tf in timeframes:
            try:
                fetch_data(symbol, tf, days=7) # 7 days
            except Exception as e:
                print(f"Failed to fetch {symbol} {tf}: {e}")

import ccxt
import pandas as pd
import os
import time

def fetch_data():
    exchange = ccxt.binance()
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']
    timeframes = ['3m', '5m', '15m', '30m', '1h']

    os.makedirs('data', exist_ok=True)

    for symbol in symbols:
        for timeframe in timeframes:
            print(f"Fetching {symbol} at {timeframe}")
            try:
                # Binance rate limits are generous but it's good to pause
                time.sleep(0.5)
                data = exchange.fetch_ohlcv(symbol, timeframe, limit=1000)
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

                safe_symbol = symbol.replace('/', '_')
                filepath = f"data/{safe_symbol}_{timeframe}.csv"
                df.to_csv(filepath, index=False)
                print(f"Saved {filepath}")
            except Exception as e:
                print(f"Error fetching {symbol} {timeframe}: {e}")

if __name__ == "__main__":
    fetch_data()

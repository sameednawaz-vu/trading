import ccxt
import pandas as pd
import os
import time

def fetch_data():
    exchange = ccxt.kraken()
    symbols = [
        'ADA/USDT', 'AI16Z/USDT', 'ALEO/USDT', 'ALGO/USDT', 'APE/USDT',
        'ATOM/USDT', 'AVAX/USDT', 'BCH/USDT', 'BERA/USDT', 'BNB/USDT',
        'BTC/USDT', 'CC/USDT', 'CRO/USDT', 'DAI/USDT', 'DOGE/USDT',
        'DOT/USDT', 'ETH/USDT', 'EURR/USDT', 'FARTCOIN/USDT', 'FIDD/USDT'
    ]
    timeframes = ['3m', '5m', '15m', '30m', '1h']

    os.makedirs('data', exist_ok=True)

    for symbol in symbols:
        for timeframe in timeframes:
            print(f"Fetching {symbol} at {timeframe}")
            try:
                # Add delay to avoid rate limiting
                time.sleep(1.0)

                # Different exchanges handle timeframes differently. ccxt abstracts it but limits vary
                data = exchange.fetch_ohlcv(symbol, timeframe, limit=500)

                if not data:
                    print(f"No data returned for {symbol} {timeframe}")
                    continue

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

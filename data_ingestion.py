import ccxt
import pandas as pd
import os
import time
import json
import argparse
from datetime import datetime, timedelta, timezone
from tqdm import tqdm

class DataIngestor:
    def __init__(self, exchange_id='kraken'):
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,
        })
        self.data_path = './data'
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)

    def fetch_historical_data(self, symbol, timeframe, start_date_str, end_date_str):
        """Fetches a full year of historical data in chunks."""
        since = self.exchange.parse8601(start_date_str)
        end_timestamp = self.exchange.parse8601(end_date_str)
        
        all_ohlcv = []
        
        print(f"Syncing {symbol} {timeframe} from {start_date_str} to {end_date_str}...")
        
        pbar = tqdm(total=end_timestamp - since, unit='ms', desc=f"{symbol} {timeframe}")
        
        # Determine actual timeframe to fetch from exchange
        fetch_tf = '1m' if timeframe == '3m' else timeframe

        while since < end_timestamp:
            try:
                # Kraken returns up to 720 candles
                limit = 720
                ohlcv = self.exchange.fetch_ohlcv(symbol, fetch_tf, since=since, limit=limit)
                if not ohlcv:
                    break
                
                last_timestamp = ohlcv[-1][0]
                # Update progress
                pbar.update(last_timestamp - since)
                since = last_timestamp + 1
                
                all_ohlcv.extend(ohlcv)
                
                # Avoid rate limit
                time.sleep(self.exchange.rateLimit / 1000)
                
                if len(ohlcv) < limit:
                    break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)
                continue
        
        pbar.close()
        
        if not all_ohlcv:
            print(f"No data fetched for {symbol} {timeframe}")
            return None

        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        # Remove duplicates
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        df.set_index('timestamp', inplace=True)

        if timeframe == '3m':
            # Resample 1m data to 3m
            df = df.resample('3min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
        
        filename = f"{symbol.replace('/', '_')}_{timeframe}_full.csv"
        path = os.path.join(self.data_path, filename)
        df.to_csv(path)
        print(f"Saved {len(df)} rows to {path}")
        return df

    def load_full_data(self, symbol, timeframe):
        filename = f"{symbol.replace('/', '_')}_{timeframe}_full.csv"
        path = os.path.join(self.data_path, filename)
        if os.path.exists(path):
            return pd.read_csv(path, parse_dates=['timestamp'], index_col='timestamp')
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch historical data from Kraken")
    parser.add_argument('--assets', nargs='+', default=["BTC/USD"], help='List of assets to fetch (e.g., BTC/USD ETH/USD)')
    parser.add_argument('--days', type=int, default=365, help='Number of days of data to fetch')
    args = parser.parse_args()

    ingestor = DataIngestor()

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=args.days)

    start = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    symbols = args.assets
    timeframes = ['1h', '30m', '15m', '5m', '3m']

    for symbol in symbols:
        for tf in timeframes:
            ingestor.fetch_historical_data(symbol, tf, start, end)

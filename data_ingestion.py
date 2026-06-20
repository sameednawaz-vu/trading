import ccxt
import pandas as pd
import os
import time
import json
from datetime import datetime, timedelta
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
        # For kraken, 3m is not supported natively. We fetch 1m instead and resample later.
        fetch_tf = '1m' if timeframe == '3m' else timeframe

        since = self.exchange.parse8601(start_date_str)
        end_timestamp = self.exchange.parse8601(end_date_str)
        
        all_ohlcv = []
        print(f"Syncing {symbol} {fetch_tf} (for {timeframe}) from {start_date_str} to {end_date_str}...")
        
        pbar = tqdm(total=end_timestamp - since, unit='ms', desc=f"{symbol} {fetch_tf}")
        
        while since < end_timestamp:
            try:
                limit = 720 # Kraken safe limit
                ohlcv = self.exchange.fetch_ohlcv(symbol, fetch_tf, since=since, limit=limit)
                if not ohlcv:
                    break
                
                last_timestamp = ohlcv[-1][0]
                pbar.update(last_timestamp - since)
                since = last_timestamp + 1
                
                all_ohlcv.extend(ohlcv)
                time.sleep(self.exchange.rateLimit / 1000)
                
                if len(ohlcv) < limit:
                    break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)
                continue
        
        pbar.close()
        
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        if timeframe == '3m' and fetch_tf == '1m':
            df.set_index('timestamp', inplace=True)
            df = df.resample('3min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna().reset_index()

        filename = f"{symbol.replace('/', '_')}_{timeframe}_full.csv"
        path = os.path.join(self.data_path, filename)
        df.to_csv(path, index=False)
        print(f"Saved {len(df)} rows to {path}")
        return df

    def load_full_data(self, symbol, timeframe):
        filename = f"{symbol.replace('/', '_')}_{timeframe}_full.csv"
        path = os.path.join(self.data_path, filename)
        if os.path.exists(path):
            return pd.read_csv(path, parse_dates=['timestamp'])
        return None

if __name__ == "__main__":
    ingestor = DataIngestor()
    # Fetching over 1 year of data: Jan 2023 to Feb 2024
    start = "2023-01-01T00:00:00Z"
    end = "2024-02-01T00:00:00Z"

    with open('./top_20_assets.json', 'r') as f:
        config = json.load(f)

    symbols = config['assets']
    timeframes = ['1h', '30m', '15m', '5m', '3m']

    for symbol in symbols[:2]: # only test 2 for brevity in testing
        for tf in timeframes:
            ingestor.fetch_historical_data(symbol, tf, start, end)

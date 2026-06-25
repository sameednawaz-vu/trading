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
        since = self.exchange.parse8601(start_date_str)
        end_timestamp = self.exchange.parse8601(end_date_str)
        
        all_ohlcv = []
        
        # Calculate total estimated iterations for progress bar
        # (Approximate, depends on limit per call)
        print(f"Syncing {symbol} {timeframe} from {start_date_str} to {end_date_str}...")
        
        pbar = tqdm(total=end_timestamp - since, unit='ms', desc=f"{symbol} {timeframe}")
        
        while since < end_timestamp:
            try:
                limit = 1000
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
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
        
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        # Remove duplicates
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        filename = f"{symbol.replace('/', '_')}_{timeframe}_full.csv"
        path = os.path.join(self.data_path, filename)
        df.to_csv(path, index=False)
        print(f"Saved {len(df)} rows to {path}")

        # If we just fetched 1m data, we should also resample it to create 3m data
        if timeframe == '1m':
            df.set_index('timestamp', inplace=True)
            df_3m = df.resample('3min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'})
            df_3m.dropna(inplace=True)
            df_3m.reset_index(inplace=True)
            filename_3m = f"{symbol.replace('/', '_')}_3m_full.csv"
            path_3m = os.path.join(self.data_path, filename_3m)
            df_3m.to_csv(path_3m, index=False)
            print(f"Saved {len(df_3m)} rows to {path_3m} (Resampled from 1m)")

        return df

    def load_full_data(self, symbol, timeframe):
        filename = f"{symbol.replace('/', '_')}_{timeframe}_full.csv"
        path = os.path.join(self.data_path, filename)
        if os.path.exists(path):
            return pd.read_csv(path, parse_dates=['timestamp'])
        return None

if __name__ == "__main__":
    ingestor = DataIngestor()
    # Fetching 1 year of data: April 2025 back to April 2024
    start = "2025-04-01T00:00:00Z"
    end = "2026-04-25T00:00:00Z"

    with open('./top_20_assets.json', 'r') as f:
        config = json.load(f)

    symbols = config['assets']
    timeframes = ['1h', '30m', '15m', '5m', '1m']

    for symbol in symbols:
        for tf in timeframes:
            ingestor.fetch_historical_data(symbol, tf, start, end)

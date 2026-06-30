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
        return df

    def load_full_data(self, symbol, timeframe):
        filename = f"{symbol.replace('/', '_')}_{timeframe}_full.csv"
        path = os.path.join(self.data_path, filename)
        if os.path.exists(path):
            return pd.read_csv(path, parse_dates=['timestamp'])
        return None

if __name__ == "__main__":
    ingestor = DataIngestor(exchange_id='kraken')
    # Fetching smaller timeframe for testing to save time, adjust dates as needed for full run
    start = "2023-01-01T00:00:00Z"
    end = "2024-01-01T00:00:00Z"

    with open('./top_20_assets.json', 'r') as f:
        config = json.load(f)

    symbols = config['assets']
    timeframes = ['1m']

    for symbol in symbols:
        for tf in timeframes:
            df_1m = ingestor.fetch_historical_data(symbol, tf, start, end)
            if df_1m is None or df_1m.empty:
                print(f"Skipping resampling for {symbol} due to empty data.")
                continue

            # Resampling logic
            df_1m.set_index('timestamp', inplace=True)

            resample_dict = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }

            tfs = {'3m': '3min', '5m': '5min', '15m': '15min', '30m': '30min', '1h': '1h'}
            for tf_name, tf_freq in tfs.items():
                df_resampled = df_1m.resample(tf_freq).agg(resample_dict).dropna()
                df_resampled.reset_index(inplace=True)
                filename = f"{symbol.replace('/', '_')}_{tf_name}_full.csv"
                path = os.path.join(ingestor.data_path, filename)
                df_resampled.to_csv(path, index=False)
                print(f"Saved {len(df_resampled)} rows to {path}")

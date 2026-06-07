import ccxt
import pandas as pd
import os
import time
import json
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
        
        fetch_tf = '1m' if timeframe == '3m' else timeframe

        print(f"Syncing {symbol} {timeframe} from {start_date_str} to {end_date_str}...")
        
        pbar = tqdm(total=end_timestamp - since, unit='ms', desc=f"{symbol} {timeframe}")
        
        while since < end_timestamp:
            try:
                limit = 720 # Kraken has specific limits
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
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        if timeframe == '3m':
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
            df = pd.read_csv(path, parse_dates=['timestamp'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            return df
        return None

if __name__ == "__main__":
    ingestor = DataIngestor()

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=365)

    start = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    with open('./top_20_assets.json', 'r') as f:
        config = json.load(f)

    symbols = config['assets'] # Use first asset for test execution run
    timeframes = ['1h', '30m', '15m', '5m', '3m']

    for symbol in symbols:
        for tf in timeframes:
            # Shorten the fetch for dry-run verification
            ingestor.fetch_historical_data(symbol, tf, start, end)

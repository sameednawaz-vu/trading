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

    def fetch_historical_data(self, symbol, start_date_str, end_date_str):
        """Fetches a full year of historical data in chunks of 1m."""
        timeframe = '1m'
        since = self.exchange.parse8601(start_date_str)
        end_timestamp = self.exchange.parse8601(end_date_str)
        
        all_ohlcv = []
        
        print(f"Syncing {symbol} {timeframe} from {start_date_str} to {end_date_str}...")
        
        pbar = tqdm(total=end_timestamp - since, unit='ms', desc=f"{symbol} {timeframe}")
        
        while since < end_timestamp:
            try:
                limit = 1000
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
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
        
        if not all_ohlcv:
            print(f"No data fetched for {symbol}")
            return None

        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        df.set_index('timestamp', inplace=True)
        
        # Resample to needed timeframes
        timeframes = {'3m': '3min', '5m': '5min', '15m': '15min', '30m': '30min', '1h': '1h'}
        for tf_name, tf_alias in timeframes.items():
            resampled = df.resample(tf_alias).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            resampled = resampled.reset_index()

            filename = f"{symbol.replace('/', '_')}_{tf_name}_full.csv"
            path = os.path.join(self.data_path, filename)
            resampled.to_csv(path, index=False)
            print(f"Saved {len(resampled)} rows to {path}")

        # Save 1m just in case
        df = df.reset_index()
        filename = f"{symbol.replace('/', '_')}_1m_full.csv"
        path = os.path.join(self.data_path, filename)
        df.to_csv(path, index=False)

        return df

    def load_full_data(self, symbol, timeframe):
        filename = f"{symbol.replace('/', '_')}_{timeframe}_full.csv"
        path = os.path.join(self.data_path, filename)
        if os.path.exists(path):
            return pd.read_csv(path, parse_dates=['timestamp'])
        return None

if __name__ == "__main__":
    ingestor = DataIngestor()
    # Fetching 1 year of data: approx 1 year back from today
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=365)

    start = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    symbols = [
        "BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD",
        "ADA/USD", "DOGE/USD", "DOT/USD", "AVAX/USD", "LINK/USD",
        "MATIC/USD", "LTC/USD", "BCH/USD", "ATOM/USD", "UNI/USD",
        "XLM/USD", "NEAR/USD", "ALGO/USD", "AAVE/USD", "ICP/USD"
    ]

    for symbol in symbols:
        ingestor.fetch_historical_data(symbol, start, end)

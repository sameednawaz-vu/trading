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
        """Fetches historical data in chunks."""
        # For kraken 3m, fetch 1m and resample
        fetch_timeframe = '1m' if timeframe == '3m' else timeframe

        since = self.exchange.parse8601(start_date_str)
        end_timestamp = self.exchange.parse8601(end_date_str)
        
        all_ohlcv = []
        
        print(f"Syncing {symbol} {timeframe} from {start_date_str} to {end_date_str}...")
        
        # tqdm for total ms
        pbar = tqdm(total=end_timestamp - since, unit='ms', desc=f"{symbol} {timeframe}")
        
        while since < end_timestamp:
            try:
                limit = 720 if self.exchange.id == 'kraken' else 1000
                ohlcv = self.exchange.fetch_ohlcv(symbol, fetch_timeframe, since=since, limit=limit)
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
            print(f"No data fetched for {symbol} {timeframe}")
            return None

        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        if timeframe == '3m':
            df = df.set_index('timestamp')
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

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=365)

    start = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    end = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    symbols = [
        "BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD",
        "ADA/USD", "AI16Z/USD", "ALEO/USD", "ALGO/USD", "APE/USD",
        "ATOM/USD", "AVAX/USD", "BCH/USD", "BERA/USD", "CC/USD",
        "CRO/USD", "DAI/USD", "DOGE/USD", "DOT/USD", "EURR/USD",
        "FARTCOIN/USD", "FIDD/USD"
    ]
    timeframes = ['1h', '30m', '15m', '5m', '3m']

    for symbol in symbols:
        for tf in timeframes:
            ingestor.fetch_historical_data(symbol, tf, start, end)

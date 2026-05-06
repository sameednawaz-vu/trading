from execution.backtester import Backtester
import pandas as pd
# For testing we can use the 15m file we downloaded for BTC
# But since we need 1h for bias, let's fetch 2 days of 1h for BTC first
from data_ingestion import DataIngestor
from datetime import datetime, timedelta

ingestor = DataIngestor(exchange_id='kraken')
end_dt = datetime.now()
start_dt = end_dt - timedelta(days=5) # Ensure enough data for 500 periods on 15m
start = start_dt.isoformat() + "Z"
end = end_dt.isoformat() + "Z"

print("Fetching BTC/USD 1h for 5 days...")
ingestor.fetch_historical_data("BTC/USD", "1h", start, end)
print("Fetching BTC/USD 15m for 5 days...")
ingestor.fetch_historical_data("BTC/USD", "15m", start, end)

print("Running backtester on BTC/USD 15m...")
bt = Backtester("BTC/USD", execution_tf='15m', bias_tf='1h')
bt.run()

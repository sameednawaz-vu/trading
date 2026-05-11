from data_ingestion import DataIngestor
import os
from datetime import datetime, timedelta

ingestor = DataIngestor()
end_date = datetime.now()
start_date = end_date - timedelta(days=10) # Just 10 days for fast testing

start = start_date.strftime("%Y-%m-%dT00:00:00Z")
end = end_date.strftime("%Y-%m-%dT00:00:00Z")

ingestor.fetch_historical_data("BTC/USD", '1h', start, end)
ingestor.fetch_historical_data("BTC/USD", '15m', start, end)

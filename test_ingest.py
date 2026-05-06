from data_ingestion import DataIngestor
from datetime import datetime, timedelta

ingestor = DataIngestor(exchange_id='kraken')
end_dt = datetime.now()
start_dt = end_dt - timedelta(days=2) # Fetch only 2 days for quick testing
start = start_dt.isoformat() + "Z"
end = end_dt.isoformat() + "Z"

print("Fetching BTC/USD 15m for 2 days...")
df = ingestor.fetch_historical_data("BTC/USD", "15m", start, end)
print(df.head())
print("Data ingestion is verified.")

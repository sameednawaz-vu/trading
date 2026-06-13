from data_ingestion import DataIngestor
from datetime import datetime, timedelta, timezone

ingestor = DataIngestor()
end = datetime.now(timezone.utc)
start = end - timedelta(days=2) # Only 2 days for quick test
start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")

df_1h = ingestor.fetch_historical_data("BTC/USD", "1h", start_str, end_str)
print("1h shape:", df_1h.shape)

df_3m = ingestor.fetch_historical_data("BTC/USD", "1m", start_str, end_str)
print("3m resampled shape:", df_3m.shape)

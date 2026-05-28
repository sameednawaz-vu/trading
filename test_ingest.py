from data_ingestion import DataIngestor
from datetime import datetime, timedelta

ingestor = DataIngestor()
end = datetime.utcnow()
start = end - timedelta(days=1)
start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")

df = ingestor.fetch_historical_data("BTC/USD", "1m", start_str, end_str)
print(df.head() if df is not None else "No data")

import pandas as pd
from data_ingestion import DataIngestor
from datetime import datetime, timedelta, timezone

ingestor = DataIngestor()
end = datetime.now(timezone.utc)
start = end - timedelta(days=5)
start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")
ingestor.fetch_historical_data("BTC/USD", "5m", start_str, end_str)

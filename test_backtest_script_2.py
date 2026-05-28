from data_ingestion import DataIngestor
import os
import json
from datetime import datetime, timedelta

# Quick ingest of enough data for BTC/USD 1m and 5m to test trading logic
ingestor = DataIngestor(exchange_id='kraken')
end = datetime.utcnow()
start = end - timedelta(days=5) # 5 days to guarantee some setups
start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")

ingestor.fetch_historical_data("ETH/USD", "5m", start_str, end_str)
ingestor.fetch_historical_data("ETH/USD", "1h", start_str, end_str)

from execution.backtester import Backtester
tester = Backtester("ETH/USD", execution_tf="5m", bias_tf="1h")
tester.run()

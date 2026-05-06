from execution.backtester import Backtester
from data_ingestion import DataIngestor
from datetime import datetime, timedelta

ingestor = DataIngestor(exchange_id='kraken')
end_dt = datetime.now()
start_dt = end_dt - timedelta(days=10) # Enough for 500 * 15m (approx 5.2 days)
start = start_dt.isoformat() + "Z"
end = end_dt.isoformat() + "Z"

print("Fetching BTC/USD 1h for 10 days...")
ingestor.fetch_historical_data("BTC/USD", "1h", start, end)
print("Fetching BTC/USD 15m for 10 days...")
ingestor.fetch_historical_data("BTC/USD", "15m", start, end)

print("Running backtester on BTC/USD 15m...")
bt = Backtester("BTC/USD", execution_tf='15m', bias_tf='1h')
# override start_idx to test faster
bt.run()

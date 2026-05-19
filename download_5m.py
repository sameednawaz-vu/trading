from data_ingestion import DataIngestor
ingestor = DataIngestor()
ingestor.fetch_historical_data("BTC/USD", "5m", "2025-01-01T00:00:00Z", "2025-01-05T00:00:00Z")

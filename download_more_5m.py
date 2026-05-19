from data_ingestion import DataIngestor
ingestor = DataIngestor()
ingestor.fetch_historical_data("BTC/USD", "5m", "2024-01-01T00:00:00Z", "2024-01-15T00:00:00Z")

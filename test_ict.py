import pandas as pd
from ict_engine import ICTEngine
from data_ingestion import DataIngestor
from datetime import datetime, timedelta, timezone

engine = ICTEngine()
ingestor = DataIngestor()

end = datetime.now(timezone.utc)
start = end - timedelta(days=2)
start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")

df = ingestor.fetch_historical_data("BTC/USD", "15m", start_str, end_str)

features = engine.compute_smc_features(df)
print("Keys:", features.keys())
print("FVG shape:", features['fvg'].shape)
print("Swing HL shape:", features['swing_hl'].shape)

bias = engine.get_bias(df)
print("Bias:", bias)

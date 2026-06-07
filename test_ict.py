import pandas as pd
from ict_engine import ICTEngine

engine = ICTEngine()
df = pd.read_csv('data/BTC_USD_1h_full.csv', parse_dates=['timestamp'])
df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

feats = engine.compute_smc_features(df)
print("Keys computed:", feats.keys())
print("Bias:", engine.get_bias(df))

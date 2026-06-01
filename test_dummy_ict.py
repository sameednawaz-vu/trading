import pandas as pd
from src.ict_engine import ICTEngine

engine = ICTEngine()
df = pd.DataFrame({
    'timestamp': pd.date_range('2023-01-01', periods=100, freq='5min'),
    'open': [100]*100,
    'high': [105]*100,
    'low': [95]*100,
    'close': [102]*100,
    'volume': [1000]*100
})
res = engine.get_bias(df)
print(res)

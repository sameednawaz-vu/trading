import pandas as pd
df = pd.DataFrame({'high': [10, 15, 12, 18, 14], 'low': [5, 8, 7, 10, 9]})
df['rolling_max'] = df['high'].rolling(window=3, center=True).max()
print(df)

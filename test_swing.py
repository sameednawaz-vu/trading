import pandas as pd
from ict_engine import smc

def test_swing():
    df = pd.read_csv('./data/BTC_USD_15m_full.csv').tail(1000)
    df.columns = [col.lower() for col in df.columns]
    swing_hl = smc.swing_highs_lows(df, swing_length=20)
    print("Swing HL Columns:", swing_hl.columns.tolist())
    print("HighLow Counts:\n", swing_hl['HighLow'].value_counts())

if __name__ == "__main__":
    test_swing()

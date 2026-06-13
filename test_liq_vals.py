
import pandas as pd
from smartmoneyconcepts import smc

def test_liq():
    df = pd.read_csv('/app/data/BTC_USD_5m_full.csv').tail(1000)
    df.columns = [col.lower() for col in df.columns]
    swing_hl = smc.swing_highs_lows(df, swing_length=50)
    liquidity = smc.liquidity(df, swing_hl)
    print("Liquidity Columns:", liquidity.columns.tolist())
    print("Swept Value Counts:\n", liquidity['Swept'].value_counts())
    print("Sample rows where Swept != 0:\n", liquidity[liquidity['Swept'] != 0].tail(10))

if __name__ == "__main__":
    test_liq()

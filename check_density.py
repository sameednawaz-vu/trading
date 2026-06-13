
import pandas as pd
from smartmoneyconcepts import smc

def check_density():
    df = pd.read_csv('/app/data/BTC_USD_5m_full.csv').tail(1000)
    df.columns = [col.lower() for col in df.columns]
    fvg = smc.fvg(df)
    swing_hl = smc.swing_highs_lows(df, swing_length=20)
    ob = smc.ob(df, swing_hl)
    
    print("FVG Counts:\n", fvg['FVG'].value_counts())
    print("OB Counts:\n", ob['OB'].value_counts())
    print("OB Sample:\n", ob[ob['OB'] != 0].tail(5))

if __name__ == "__main__":
    check_density()

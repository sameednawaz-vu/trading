import pandas as pd
from smartmoneyconcepts import smc

def test_liq():
    df = pd.DataFrame({
        'open': [100, 102, 101, 103, 102],
        'high': [102, 104, 103, 105, 104],
        'low': [99, 101, 100, 102, 101],
        'close': [101, 103, 102, 104, 103],
        'volume': [10, 20, 15, 25, 20]
    })
    swing_hl = smc.swing_highs_lows(df, swing_length=2)
    liquidity = smc.liquidity(df, swing_hl)
    assert 'Liquidity' in liquidity.columns
    assert 'Level' in liquidity.columns
    assert 'Swept' in liquidity.columns

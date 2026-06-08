import pandas as pd
from smartmoneyconcepts import smc

def test_swing():
    # Make some dummy data since test depends on absolute non-existent paths
    df = pd.DataFrame({
        'open': [100, 102, 101, 103, 102],
        'high': [102, 104, 103, 105, 104],
        'low': [99, 101, 100, 102, 101],
        'close': [101, 103, 102, 104, 103],
        'volume': [10, 20, 15, 25, 20]
    })
    swing_hl = smc.swing_highs_lows(df, swing_length=2)
    # Testing that it returns the expected columns per our fix
    assert 'HighLow' in swing_hl.columns
    assert 'Level' in swing_hl.columns

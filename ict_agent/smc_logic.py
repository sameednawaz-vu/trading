import pandas as pd
import numpy as np
from smartmoneyconcepts import smc

def add_smc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a DataFrame and adds HIGH-PRECISION SMC indicators using the smartmoneyconcepts library.
    """
    df = df.copy() # Ensure we don't modify the original downstream
    df.columns = [c.lower() for c in df.columns]

    # Convert columns to expected names if necessary (smc expects specific naming if lowercased, usually title case, but we pass the df)
    # The smartmoneyconcepts library typically expects 'open', 'high', 'low', 'close', 'volume'
    
    # 1. Fair Value Gaps (FVG)
    # Returns FVG (1 for bullish, -1 for bearish), Top, Bottom, MitigatedIndex
    fvg_df = smc.fvg(df)
    df['fvg_bullish'] = fvg_df['FVG'] == 1
    df['fvg_bearish'] = fvg_df['FVG'] == -1
    df['fvg_top'] = fvg_df['Top']
    df['fvg_bottom'] = fvg_df['Bottom']
    df['active_fvg_top'] = df['fvg_top'].ffill()
    df['active_fvg_bottom'] = df['fvg_bottom'].ffill()
    
    # 2. Swing Highs and Lows
    # Returns HighLow (1 for high, -1 for low), Level
    swing_hl_df = smc.swing_highs_lows(df, swing_length=20)
    df['is_swing_high'] = swing_hl_df['HighLow'] == 1
    df['is_swing_low'] = swing_hl_df['HighLow'] == -1
    df['last_swing_high'] = swing_hl_df['Level'].where(df['is_swing_high']).ffill()
    df['last_swing_low'] = swing_hl_df['Level'].where(df['is_swing_low']).ffill()

    # 3. Order Blocks (OB)
    # Returns OB (1 for bullish, -1 for bearish), Top, Bottom, Volume, MitigatedIndex
    ob_df = smc.ob(df, swing_hl_df)
    df['ob_bullish'] = ob_df['OB'] == 1
    df['ob_bearish'] = ob_df['OB'] == -1
    df['ob_top'] = ob_df['Top']
    df['ob_bottom'] = ob_df['Bottom']

    # --- 6. Algorithmic Filters ---
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # ATR
    high_low = df['high'] - df['low']
    high_cp = abs(df['high'] - df['close'].shift())
    low_cp = abs(df['low'] - df['close'].shift())
    df['tr'] = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    df['atr'] = df['tr'].rolling(14).mean()
    
    # MFI
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    money_flow = typical_price * df['volume']
    positive_flow = np.where(typical_price > typical_price.shift(1), money_flow, 0)
    negative_flow = np.where(typical_price < typical_price.shift(1), money_flow, 0)
    pos_mf_14 = pd.Series(positive_flow).rolling(14).sum()
    neg_mf_14 = pd.Series(negative_flow).rolling(14).sum()
    mfr = pos_mf_14 / neg_mf_14
    df['mfi'] = 100 - (100 / (1 + mfr))

    # Clean up
    df.drop(columns=['tr'], inplace=True, errors='ignore')
    df = df.add_prefix('SMC_')
    for col in ['open', 'high', 'low', 'close', 'volume', 'timestamp']:
        if f'SMC_{col}' in df.columns:
            df[col] = df[f'SMC_{col}']

    return df

def get_killzone(timestamp):
    hour = timestamp.hour
    if 2 <= hour < 5: return "London"
    if 7 <= hour < 10: return "NY_AM"
    if 10 <= hour < 11: return "Silver_Bullet"
    if 14 <= hour < 16: return "NY_PM"
    return "None"

if __name__ == "__main__":
    # Test script to verify functionality
    test_data = {
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='5min'),
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 105,
        'low': np.random.randn(100).cumsum() + 95,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(100, 1000, 100)
    }
    df = pd.DataFrame(test_data)

    result = add_smc_indicators(df)
    print("Columns added successfully:")
    print([c for c in result.columns if 'SMC_' in c])
    print(f"Contains required swing columns: {'SMC_last_swing_high' in result.columns and 'SMC_last_swing_low' in result.columns}")

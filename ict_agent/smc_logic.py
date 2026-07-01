import pandas as pd
import numpy as np
from smartmoneyconcepts import smc

def add_smc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a DataFrame and adds HIGH-PRECISION manual SMC indicators.
    Uses the smartmoneyconcepts library as requested.
    """
    df = df.copy()

    # SMC expects lowercase columns
    df.columns = [c.lower() for c in df.columns]
    
    # 1. Fair Value Gaps (FVG)
    fvg = smc.fvg(df)
    df['fvg_bullish'] = fvg['FVG'] == 1
    df['fvg_bearish'] = fvg['FVG'] == -1
    df['fvg_top'] = fvg['Top']
    df['fvg_bottom'] = fvg['Bottom']

    # Forward fill FVGs
    df['active_fvg_top'] = df['fvg_top'].replace(0, np.nan).ffill()
    df['active_fvg_bottom'] = df['fvg_bottom'].replace(0, np.nan).ffill()

    # 2. Swing Points
    swings = smc.swing_highs_lows(df)
    df['is_swing_high'] = swings['HighLow'] == 1
    df['is_swing_low'] = swings['HighLow'] == -1
    df['last_swing_high'] = np.where(df['is_swing_high'], df['high'], np.nan)
    df['last_swing_high'] = pd.Series(df['last_swing_high']).ffill()
    df['last_swing_low'] = np.where(df['is_swing_low'], df['low'], np.nan)
    df['last_swing_low'] = pd.Series(df['last_swing_low']).ffill()

    # 3. Liquidity Sweeps
    df['sweep_high'] = (df['high'] > df['last_swing_high'].shift(1)) & (df['close'] < df['last_swing_high'].shift(1))
    df['sweep_low'] = (df['low'] < df['last_swing_low'].shift(1)) & (df['close'] > df['last_swing_low'].shift(1))

    # 4. Order Blocks (OB)
    ob = smc.ob(df, swings)
    df['ob_bullish'] = ob['OB'] == 1
    df['ob_bearish'] = ob['OB'] == -1

    # 5. Breaker Blocks (BB) (simplified approximation as not in SMC natively or complex)
    df['body_size'] = abs(df['close'] - df['open'])
    df['is_displacement'] = df['body_size'] > df['body_size'].rolling(20).mean() * 2.0
    df['is_idm'] = (df['fvg_bullish'] | df['fvg_bearish']) & df['is_displacement'].shift(1)
    df['bb_bullish'] = (df['high'] > df['high'].where(df['ob_bearish']).ffill()) & df['is_displacement']
    df['bb_bearish'] = (df['low'] < df['low'].where(df['ob_bullish']).ffill()) & df['is_displacement']

    # 6. Algorithmic Filters
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

    # 7. Range Statistics (Premium/Discount)
    df['range_100_high'] = df['high'].rolling(100).max()
    df['range_100_low'] = df['low'].rolling(100).min()
    df['mid_point'] = (df['range_100_high'] + df['range_100_low']) / 2
    df['is_discount'] = df['close'] < df['mid_point']
    df['is_premium'] = df['close'] > df['mid_point']

    # 8. Session Highs/Lows (Asian Session)
    df['hour'] = df['timestamp'].dt.hour
    df['is_asian'] = (df['hour'] >= 0) & (df['hour'] < 8)
    df['day'] = df['timestamp'].dt.date
    df['asian_high'] = df.groupby('day')['high'].transform(lambda x: x.where(df['is_asian']).max()).ffill()
    df['asian_low'] = df.groupby('day')['low'].transform(lambda x: x.where(df['is_asian']).min()).ffill()

    # Clean up
    df.drop(columns=['body_size', 'tr', 'hour', 'day', 'is_asian'], inplace=True, errors='ignore')
    df = df.add_prefix('SMC_')

    # Restore original columns
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

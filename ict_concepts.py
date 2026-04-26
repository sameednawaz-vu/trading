import pandas as pd
import numpy as np

def annotate_ict_features(df):
    """
    Annotate DataFrame with ICT concepts: Fair Value Gaps (FVG), Order Blocks (OB), and Liquidity Sweeps.
    Expects columns: timestamp, open, high, low, close, volume.
    """
    df = df.copy()

    # --- Fair Value Gaps (FVG) ---
    df['fvg_bullish'] = False
    df['fvg_bearish'] = False

    df['fvg_bullish'] = df['low'] > df['high'].shift(2)
    df['fvg_bullish'] = df['fvg_bullish'] & (df['close'].shift(1) > df['open'].shift(1))

    df['fvg_bearish'] = df['high'] < df['low'].shift(2)
    df['fvg_bearish'] = df['fvg_bearish'] & (df['close'].shift(1) < df['open'].shift(1))

    # --- Liquidity Sweeps ---
    window = 5
    df['rolling_max'] = df['high'].rolling(window=window, center=True).max()
    df['rolling_min'] = df['low'].rolling(window=window, center=True).min()

    df['is_swing_high'] = df['high'] == df['rolling_max']
    df['is_swing_low'] = df['low'] == df['rolling_min']

    df['last_swing_high'] = df['high'].where(df['is_swing_high']).ffill()
    df['last_swing_low'] = df['low'].where(df['is_swing_low']).ffill()

    prev_swing_high = df['last_swing_high'].shift(1)
    df['sweep_high'] = (df['high'] > prev_swing_high) & (df['close'] < prev_swing_high)

    prev_swing_low = df['last_swing_low'].shift(1)
    df['sweep_low'] = (df['low'] < prev_swing_low) & (df['close'] > prev_swing_low)

    df.drop(columns=['rolling_max', 'rolling_min'], inplace=True)

    # --- Order Blocks (OB) ---
    df['ob_bullish'] = False
    df['ob_bearish'] = False

    bullish_bos = (df['close'] > prev_swing_high) & (df['close'] > df['open'])
    df['ob_bullish_trigger'] = bullish_bos

    bearish_bos = (df['close'] < prev_swing_low) & (df['close'] < df['open'])
    df['ob_bearish_trigger'] = bearish_bos

    return df

if __name__ == "__main__":
    data = {
        'timestamp': pd.date_range(start='2023-01-01', periods=10, freq='5min'),
        'open':  [100, 102, 101, 105, 110, 108, 106, 115, 112, 110],
        'high':  [103, 104, 102, 112, 115, 110, 107, 118, 115, 112],
        'low':   [99,  101, 100, 104, 108, 105, 105, 110, 110, 108],
        'close': [102, 101, 102, 110, 108, 106, 107, 112, 110, 111],
        'volume':[10,  12,  8,   20,  15,  10,  8,   25,  18,  12]
    }
    df_mock = pd.DataFrame(data)
    annotated = annotate_ict_features(df_mock)
    print(annotated[['close', 'fvg_bullish', 'fvg_bearish', 'is_swing_high', 'sweep_high']])

import pandas as pd
import numpy as np

def calculate_fvg(df):
    """
    Calculate Fair Value Gaps (FVG).
    Bullish FVG: Low of candle 3 is higher than High of candle 1.
    Bearish FVG: High of candle 3 is lower than Low of candle 1.
    """
    df = df.copy()
    df['fvg_bullish'] = False
    df['fvg_bearish'] = False
    df['fvg_top'] = np.nan
    df['fvg_bottom'] = np.nan

    for i in range(2, len(df)):
        # Bullish FVG
        if df.iloc[i]['low'] > df.iloc[i-2]['high']:
            df.at[df.index[i-1], 'fvg_bullish'] = True
            df.at[df.index[i-1], 'fvg_top'] = df.iloc[i]['low']
            df.at[df.index[i-1], 'fvg_bottom'] = df.iloc[i-2]['high']

        # Bearish FVG
        elif df.iloc[i]['high'] < df.iloc[i-2]['low']:
            df.at[df.index[i-1], 'fvg_bearish'] = True
            df.at[df.index[i-1], 'fvg_top'] = df.iloc[i-2]['low']
            df.at[df.index[i-1], 'fvg_bottom'] = df.iloc[i]['high']

    return df

def calculate_order_blocks(df, period=10):
    """
    Calculate Order Blocks (OB).
    Bullish OB: The last down candle before an impulsive up move (that breaks structure or creates FVG).
    Bearish OB: The last up candle before an impulsive down move.
    Simple approximation: look for strong moves and mark the preceding opposite candle.
    """
    df = df.copy()
    df['ob_bullish'] = False
    df['ob_bearish'] = False
    df['ob_top'] = np.nan
    df['ob_bottom'] = np.nan

    # Calculate body size and ATR for "impulsive" move detection
    df['body'] = abs(df['close'] - df['open'])
    df['atr'] = df['high'] - df['low'] # Simple range for this example
    avg_range = df['atr'].rolling(period).mean()

    for i in range(1, len(df)):
        # Check for impulsive up move (body > 1.5 * avg_range)
        if df.iloc[i]['close'] > df.iloc[i]['open'] and df.iloc[i]['body'] > 1.5 * avg_range.iloc[i]:
            # Look back for the last down candle
            for j in range(i-1, max(-1, i-5), -1):
                if df.iloc[j]['close'] < df.iloc[j]['open']:
                    df.at[df.index[j], 'ob_bullish'] = True
                    df.at[df.index[j], 'ob_top'] = df.iloc[j]['high']
                    df.at[df.index[j], 'ob_bottom'] = df.iloc[j]['low']
                    break

        # Check for impulsive down move
        elif df.iloc[i]['close'] < df.iloc[i]['open'] and df.iloc[i]['body'] > 1.5 * avg_range.iloc[i]:
            # Look back for the last up candle
            for j in range(i-1, max(-1, i-5), -1):
                if df.iloc[j]['close'] > df.iloc[j]['open']:
                    df.at[df.index[j], 'ob_bearish'] = True
                    df.at[df.index[j], 'ob_top'] = df.iloc[j]['high']
                    df.at[df.index[j], 'ob_bottom'] = df.iloc[j]['low']
                    break

    return df

def apply_ict_concepts(df):
    """Apply all ICT concepts to the dataframe."""
    df = calculate_fvg(df)
    df = calculate_order_blocks(df)
    return df

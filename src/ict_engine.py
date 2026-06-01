import pandas as pd
from smartmoneyconcepts import smc

class ICTEngine:
    def __init__(self):
        pass

    def compute_smc_features(self, df):
        """
        Computes SMC features using the smartmoneyconcepts library.
        Expects columns: open, high, low, close, volume.
        """
        df_copy = df.copy()
        # Ensure column names are lowercase
        df_copy.columns = [col.lower() for col in df_copy.columns]

        # Format explicitly for smc since it requires string casing depending on version or lowercase
        
        # Fair Value Gaps
        fvg = smc.fvg(df_copy)
        
        # Swing Highs/Lows
        swing_hl = smc.swing_highs_lows(df_copy, swing_length=50)
        
        # Order Blocks
        ob = smc.ob(df_copy, swing_hl)
        
        # BOS and CHoCH
        bos_choch = smc.bos_choch(df_copy, swing_hl)
        
        # Liquidity
        liquidity = smc.liquidity(df_copy, swing_hl)
        
        return {
            'fvg': fvg,
            'swing_hl': swing_hl,
            'ob': ob,
            'bos_choch': bos_choch,
            'liquidity': liquidity
        }

    def get_bias(self, df):
        """
        Determines the directional bias (Bullish/Bearish/Neutral) 
        based on recent Market Structure (BOS/CHoCH).
        """
        df_copy = df.copy()
        df_copy.columns = [col.lower() for col in df_copy.columns]

        swing_hl = smc.swing_highs_lows(df_copy, swing_length=20)
        bos_choch = smc.bos_choch(df_copy, swing_hl)
        
        last_signals = bos_choch.tail(5)
        
        bullish_signals = last_signals[last_signals['BOS'] == 1.0].shape[0] + last_signals[last_signals['CHOCH'] == 1.0].shape[0]
        bearish_signals = last_signals[last_signals['BOS'] == -1.0].shape[0] + last_signals[last_signals['CHOCH'] == -1.0].shape[0]
        
        if bullish_signals > bearish_signals:
            return "Bullish"
        elif bearish_signals > bullish_signals:
            return "Bearish"
        return "Neutral"

    def is_killzone(self, timestamp):
        """
        Determines if a given timestamp falls within an ICT Killzone.
        Times in UTC.
        """
        hour = timestamp.hour
        if 7 <= hour < 10:
            return "London"
        elif 12 <= hour < 15:
            return "New York"
        elif 0 <= hour < 3:
            return "Asian"
        return None

if __name__ == "__main__":
    pass

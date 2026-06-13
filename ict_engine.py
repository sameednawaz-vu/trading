import pandas as pd
from smartmoneyconcepts import smc

class ICTEngine:
    def __init__(self):
        pass

    def compute_smc_features(self, df_in):
        """
        Computes SMC features using the smartmoneyconcepts library.
        Expects columns: open, high, low, close, volume.
        """
        df = df_in.copy()
        # Ensure column names are lowercase
        df.columns = [col.lower() if col.lower() in ['open', 'high', 'low', 'close', 'volume', 'timestamp'] else col for col in df.columns]
        
        # Fair Value Gaps
        fvg = smc.fvg(df)
        
        # Swing Highs/Lows
        swing_hl = smc.swing_highs_lows(df, swing_length=50)
        
        # Order Blocks
        ob = smc.ob(df, swing_hl)
        
        # BOS and CHoCH
        bos_choch = smc.bos_choch(df, swing_hl)
        
        # Liquidity
        liquidity = smc.liquidity(df, swing_hl)
        
        return {
            'fvg': fvg,
            'swing_hl': swing_hl,
            'ob': ob,
            'bos_choch': bos_choch,
            'liquidity': liquidity
        }

    def get_bias(self, df_in):
        """
        Determines the directional bias (Bullish/Bearish/Neutral) 
        based on recent Market Structure (BOS/CHoCH).
        """
        df = df_in.copy()
        df.columns = [col.lower() if col.lower() in ['open', 'high', 'low', 'close', 'volume', 'timestamp'] else col for col in df.columns]

        swing_hl = smc.swing_highs_lows(df, swing_length=20)
        bos_choch = smc.bos_choch(df, swing_hl)
        
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

    def validate_risk_reward(self, entry, stop_loss, take_profit, direction):
        """
        Validates that the trade meets the minimum 1:2 Risk/Reward ratio.
        """
        if direction == 'Long':
            risk = entry - stop_loss
            reward = take_profit - entry
        elif direction == 'Short':
            risk = stop_loss - entry
            reward = entry - take_profit
        else:
            return False

        if risk <= 0:
            return False

        rr = reward / risk
        return rr >= 2.0

if __name__ == "__main__":
    pass

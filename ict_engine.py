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

        # Ensure column names are exactly what smc expects
        df_copy.columns = [col.lower() for col in df_copy.columns]
        
        # Fair Value Gaps
        fvg = smc.fvg(df_copy)
        
        # Swing Highs/Lows
        swing_hl = smc.swing_highs_lows(df_copy, swing_length=20)
        
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
        
        bullish_signals = last_signals[last_signals['BOS'] == 1].shape[0] + last_signals[last_signals['CHOCH'] == 1].shape[0]
        bearish_signals = last_signals[last_signals['BOS'] == -1].shape[0] + last_signals[last_signals['CHOCH'] == -1].shape[0]
        
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
        # UTC Times based on rules:
        # London Open: 3-4AM EST -> 7-8AM or 8-9AM UTC (Approximate 7-10)
        # NY AM: 10-11AM EST -> 14-15 or 15-16 UTC (Approximate 12-16)
        # NY PM: 2-3PM EST -> 18-19 or 19-20 UTC (Approximate 18-20)
        # Will stick to original simplistic logic but return explicit times to avoid bias.

        hour = timestamp.hour
        if 7 <= hour < 10:
            return "London"
        elif 12 <= hour < 16:
            return "New York"
        return None

    def merge_htf_features(self, ltf_df, htf_df, htf_features):
        """
        Merges HTF features into LTF without lookahead bias.
        Matches the LTF row to the most recently closed HTF row.
        """
        ltf_timestamps = ltf_df['timestamp'] if 'timestamp' in ltf_df.columns else ltf_df.index
        htf_timestamps = htf_df['timestamp'] if 'timestamp' in htf_df.columns else htf_df.index

        # We find the index of the latest HTF candle that is strictly < LTF timestamp
        merged_features = []
        for ltf_time in ltf_timestamps:
            # Strictly less than to ensure the HTF candle has CLOSED
            closed_htf = htf_timestamps[htf_timestamps < ltf_time]
            if len(closed_htf) > 0:
                latest_closed_idx = closed_htf.index[-1]
                # Extract features for that specific HTF closed index
                # Currently simple structure, returning dictionary with latest known bounds

                fvg_data = htf_features['fvg']
                # Get the last 3 active FVGs
                active_fvgs = fvg_data.iloc[:latest_closed_idx+1]
                active_fvgs = active_fvgs[active_fvgs['FVG'] != 0].tail(3)

                fvg_dict = {
                    'FVG': active_fvgs['FVG'].to_dict(),
                    'Top': active_fvgs['Top'].to_dict(),
                    'Bottom': active_fvgs['Bottom'].to_dict()
                }
                merged_features.append({'htf_fvg': fvg_dict})
            else:
                merged_features.append({'htf_fvg': {}})

        return merged_features

if __name__ == "__main__":
    pass
import unittest
import pandas as pd
from ict_concepts import annotate_ict_features

class TestICTConcepts(unittest.TestCase):
    def test_fvg_calculation(self):
        # 5 rows. We want a Bullish FVG on row index 2 (from perspective of row 4)
        # So low of 4 > high of 2. And close of 3 > open of 3.
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=5, freq='5min'),
            'open':  [100, 100, 100, 105, 110],
            'high':  [101, 102, 102, 112, 115],  # index 2 high is 102
            'low':   [99,  99,  99,  104, 105],  # index 4 low is 105 (105 > 102, FVG gap = 3)
            'close': [100, 101, 101, 110, 108],  # index 3 close(110) > open(105), confirming bullish push
            'volume':[10,  10,  10,  10,  10]
        }
        df = pd.DataFrame(data)
        annotated = annotate_ict_features(df)

        # At index 4, fvg_bullish should be True because low(105) > high(102) from index 2
        # and previous candle (index 3) is bullish (close 110 > open 105)
        self.assertTrue(annotated['fvg_bullish'].iloc[4])

    def test_swing_high_calculation(self):
        # Peak at index 2
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=5, freq='5min'),
            'open':  [100]*5,
            'high':  [101, 102, 105, 103, 102],
            'low':   [99]*5,
            'close': [100]*5,
            'volume':[10]*5
        }
        df = pd.DataFrame(data)
        annotated = annotate_ict_features(df)
        self.assertTrue(annotated['is_swing_high'].iloc[2])
        self.assertFalse(annotated['is_swing_high'].iloc[1])

if __name__ == '__main__':
    unittest.main()

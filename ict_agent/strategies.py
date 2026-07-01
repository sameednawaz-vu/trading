import pandas as pd
import numpy as np
import pandas_ta as ta

class StrategyFactory:
    """
    A collection of Hybrid ICT trading strategies for empirical ranking.
    Focuses on combining SMC logic (FVG, OB, BB, Liquidity) with algo filters (EMA, MFI, ATR).
    """
    
    @staticmethod
    def _calc_rr(side, price, sl, rr=2.0):
        min_dist = price * 0.003
        dist = abs(price - sl)
        if dist < min_dist:
            dist = min_dist
            sl = price - dist if side == 'long' else price + dist
            
        tp = price + dist * rr if side == 'long' else price - dist * rr
        return sl, tp

    # 1. FVG + EMA 200 Trend Follower
    @staticmethod
    def fvg_ema200_trend(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        htf = df_dict.get('1h')
        if ltf is None or ltf.empty or htf is None or htf.empty: return None
        last_ltf = ltf.iloc[-1]
        last_htf = htf.iloc[-1]
        
        # Range for Discount/Premium
        lookback = htf.tail(50)
        range_max = lookback['high'].max()
        range_min = lookback['low'].min()
        mid = (range_max + range_min) / 2
        
        if last_htf['close'] > last_htf['SMC_ema_200']:
            # Long only in Discount
            if last_ltf['SMC_fvg_bullish'] and last_ltf['close'] < mid:
                sl, tp = StrategyFactory._calc_rr('long', last_ltf['close'], last_ltf['SMC_fvg_bottom'], 2.0)
                return {"side": "long", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        elif last_htf['close'] < last_htf['SMC_ema_200']:
            # Short only in Premium
            if last_ltf['SMC_fvg_bearish'] and last_ltf['close'] > mid:
                sl, tp = StrategyFactory._calc_rr('short', last_ltf['close'], last_ltf['SMC_fvg_top'], 2.0)
                return {"side": "short", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        return None

    # 2. Breaker Block + MFI Reversion
    @staticmethod
    def breaker_mfi_reversion(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        if last['SMC_bb_bullish'] and last['SMC_mfi'] < 30:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_bb_bearish'] and last['SMC_mfi'] > 70:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 3. Liquidity Sweep + EMA 50 Pullback
    @staticmethod
    def sweep_ema50_pullback(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        lookback = ltf.tail(10)
        if last['close'] > last['SMC_ema_50'] and lookback['SMC_sweep_low'].any():
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['close'] < last['SMC_ema_50'] and lookback['SMC_sweep_high'].any():
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 4. Order Block + ATR Volatility Filter
    @staticmethod
    def ob_atr_filtered(df_dict, symbol):
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        if last['SMC_atr'] > ltf['SMC_atr'].rolling(100).mean():
            if last['SMC_ob_bullish']:
                sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
                return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
            if last['SMC_ob_bearish']:
                sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
                return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 5. Silver Bullet + MFI Confluence
    @staticmethod
    def silver_bullet_mfi(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        hour = last['timestamp'].hour
        is_window = (3 <= hour < 4) or (10 <= hour < 11) or (14 <= hour < 15)
        if not is_window: return None
        if last['SMC_fvg_bullish'] and last['SMC_mfi'] < 40:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['SMC_fvg_bottom'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_fvg_bearish'] and last['SMC_mfi'] > 60:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['SMC_fvg_top'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 6. Unicorn Model (Breaker + FVG)
    @staticmethod
    def unicorn_model(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        if last['SMC_bb_bullish'] and last['SMC_fvg_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['SMC_fvg_bottom'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_bb_bearish'] and last['SMC_fvg_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['SMC_fvg_top'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 7. Turtle Soup + EMA 200 Rejection
    @staticmethod
    def turtle_soup_ema200(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        if last['SMC_sweep_low'] and last['close'] < last['SMC_ema_200']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_sweep_high'] and last['close'] > last['SMC_ema_200']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 8. London Killzone Judas Swing
    @staticmethod
    def london_judas_swing(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        hour = last['timestamp'].hour
        if not (2 <= hour < 5): return None
        if last['SMC_sweep_low'] and last['SMC_mfi'] < 30:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_sweep_high'] and last['SMC_mfi'] > 70:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 9. NY AM Continuity (9:30 AM Volatility)
    @staticmethod
    def ny_am_continuity(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        hour = last['timestamp'].hour
        minute = last['timestamp'].minute
        if not (hour == 13 and 30 <= minute <= 59): return None
        if last['close'] > last['SMC_ema_50'] and last['SMC_fvg_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['close'] < last['SMC_ema_50'] and last['SMC_fvg_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 10. MFI Exhaustion + Order Block
    @staticmethod
    def mfi_exhaustion_ob(df_dict, symbol):
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        if last['SMC_mfi'] < 15 and last['SMC_ob_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_mfi'] > 85 and last['SMC_ob_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 11. EMA 50/200 Golden Cross + FVG
    @staticmethod
    def golden_cross_fvg(df_dict, symbol):
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        if last['SMC_ema_50'] > last['SMC_ema_200'] and last['SMC_fvg_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['SMC_fvg_bottom'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_ema_50'] < last['SMC_ema_200'] and last['SMC_fvg_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['SMC_fvg_top'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 12. SMC Liquidity Void + ATR Stretch
    @staticmethod
    def liquidity_void_atr(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        if last['SMC_is_displacement'] and last['SMC_atr'] > ltf['SMC_atr'].rolling(50).mean() * 1.5:
            if last['close'] > last['open']:
                sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
                return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
            else:
                sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
                return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 13. High Timeframe Bias + Low Timeframe Entry
    @staticmethod
    def htf_bias_ltf_entry(df_dict, symbol):
        htf = df_dict.get('1h')
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if htf is None or ltf is None or htf.empty or ltf.empty: return None
        last_htf = htf.iloc[-1]
        last_ltf = ltf.iloc[-1]
        if last_htf['SMC_fvg_bullish'] and last_ltf['SMC_fvg_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last_ltf['close'], last_ltf['low'], 2.0)
            return {"side": "long", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        if last_htf['SMC_fvg_bearish'] and last_ltf['SMC_fvg_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last_ltf['close'], last_ltf['high'], 2.0)
            return {"side": "short", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        return None

    # 14. Breaker Block Trend Continuation
    @staticmethod
    def bb_trend_continuation(df_dict, symbol):
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        if last['close'] > last['SMC_ema_200'] and last['SMC_bb_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['close'] < last['SMC_ema_200'] and last['SMC_bb_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 15. Power of Three
    @staticmethod
    def power_of_three(df_dict, symbol):
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        hour = last['timestamp'].hour
        if 13 <= hour < 16:
            if last['SMC_sweep_low'] and last['SMC_fvg_bullish']:
                sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
                return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
            if last['SMC_sweep_high'] and last['SMC_fvg_bearish']:
                sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
                return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 16. MFI Divergence + SMC FVG
    @staticmethod
    def mfi_div_fvg(df_dict, symbol):
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        prev = ltf.iloc[-5]
        if last['close'] < prev['close'] and last['SMC_mfi'] > prev['SMC_mfi'] and last['SMC_fvg_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['close'] > prev['close'] and last['SMC_mfi'] < prev['SMC_mfi'] and last['SMC_fvg_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 17. Extreme MFI + Displacement
    @staticmethod
    def extreme_mfi_displacement(df_dict, symbol):
        htf = df_dict.get('1h')
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if htf is None or ltf is None or htf.empty or ltf.empty: return None
        last_htf = htf.iloc[-1]
        last_ltf = ltf.iloc[-1]
        
        if last_htf['close'] > last_htf['SMC_ema_200']:
            if last_ltf['SMC_mfi'] < 10 and last_ltf['SMC_is_displacement']:
                sl, tp = StrategyFactory._calc_rr('long', last_ltf['close'], last_ltf['low'], 2.0)
                return {"side": "long", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        elif last_htf['close'] < last_htf['SMC_ema_200']:
            if last_ltf['SMC_mfi'] > 90 and last_ltf['SMC_is_displacement']:
                sl, tp = StrategyFactory._calc_rr('short', last_ltf['close'], last_ltf['high'], 2.0)
                return {"side": "short", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        return None

    # 18. FVG Retest + EMA 50
    @staticmethod
    def fvg_retest_ema50(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        if last['close'] > last['SMC_ema_50'] and last['SMC_fvg_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['SMC_fvg_bottom'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['close'] < last['SMC_ema_50'] and last['SMC_fvg_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['SMC_fvg_top'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 19. ATR Stop Run
    @staticmethod
    def atr_stop_run(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        if last['SMC_sweep_low'] and last['SMC_atr'] > ltf['SMC_atr'].rolling(20).mean() * 1.1:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_sweep_high'] and last['SMC_atr'] > ltf['SMC_atr'].rolling(20).mean() * 1.1:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 20. FVG Trend Reversal
    @staticmethod
    def fvg_trend_reversal(df_dict, symbol):
        htf = df_dict.get('1h')
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if htf is None or ltf is None or htf.empty or ltf.empty: return None
        last_htf = htf.iloc[-1]
        last_ltf = ltf.iloc[-1]
        if last_htf['SMC_ob_bullish'] and last_ltf['SMC_fvg_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last_ltf['close'], last_ltf['low'], 2.0)
            return {"side": "long", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        if last_htf['SMC_ob_bearish'] and last_ltf['SMC_fvg_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last_ltf['close'], last_ltf['high'], 2.0)
            return {"side": "short", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        return None

    # 21. Reclaimed Breaker
    @staticmethod
    def reclaimed_breaker_mfi(df_dict, symbol):
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        if last['SMC_bb_bullish'] and last['SMC_mfi'] < 45:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_bb_bearish'] and last['SMC_mfi'] > 55:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 22. Asian Sweep NY Reversal
    @staticmethod
    def asian_sweep_ny_reversal(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        hour = last['timestamp'].hour
        if not (13 <= hour < 17): return None
        lookback = ltf.tail(100)
        asian_high = lookback[lookback['timestamp'].dt.hour < 8]['high'].max()
        asian_low = lookback[lookback['timestamp'].dt.hour < 8]['low'].min()
        if last['high'] > asian_high and last['close'] < asian_high:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        if last['low'] < asian_low and last['close'] > asian_low:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 23. Premium/Discount OB
    @staticmethod
    def premium_discount_ob(df_dict, symbol):
        htf = df_dict.get('1h')
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if htf is None or ltf is None: return None
        range_high = htf['high'].tail(50).max()
        range_low = htf['low'].tail(50).min()
        mid = (range_high + range_low) / 2
        last_ltf = ltf.iloc[-1]
        if last_ltf['close'] < mid and last_ltf['SMC_ob_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last_ltf['close'], last_ltf['low'], 2.0)
            return {"side": "long", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        if last_ltf['close'] > mid and last_ltf['SMC_ob_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last_ltf['close'], last_ltf['high'], 2.0)
            return {"side": "short", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        return None

    # 24. IOF Continuation
    @staticmethod
    def iof_continuation_fvg(df_dict, symbol):
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        if last['close'] > last['SMC_ema_50'] and last['SMC_fvg_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['SMC_fvg_bottom'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['close'] < last['SMC_ema_50'] and last['SMC_fvg_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['SMC_fvg_top'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 25. Double Bottom Sweep + MSS
    @staticmethod
    def double_bottom_sweep_mss(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        if last['SMC_sweep_low'] and last['SMC_is_displacement']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_sweep_high'] and last['SMC_is_displacement']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 26. London Open Killzone OB
    @staticmethod
    def london_open_ob(df_dict, symbol):
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        hour = last['timestamp'].hour
        if not (7 <= hour < 10): return None
        if last['SMC_ob_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_ob_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 27. MFI Reversal + HTF EMA
    @staticmethod
    def mfi_reversal_htf_ema(df_dict, symbol):
        htf = df_dict.get('1h')
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if htf is None or ltf is None: return None
        last_htf = htf.iloc[-1]
        last_ltf = ltf.iloc[-1]
        if last_htf['close'] > last_htf['SMC_ema_200']:
            if last_ltf['SMC_mfi'] < 25:
                sl, tp = StrategyFactory._calc_rr('long', last_ltf['close'], last_ltf['low'], 2.0)
                return {"side": "long", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        elif last_htf['close'] < last_htf['SMC_ema_200']:
            if last_ltf['SMC_mfi'] > 75:
                sl, tp = StrategyFactory._calc_rr('short', last_ltf['close'], last_ltf['high'], 2.0)
                return {"side": "short", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        return None

    # 28. SMT Divergence
    @staticmethod
    def smt_divergence_mfi(df_dict, symbol):
        htf = df_dict.get('1h')
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if htf is None or ltf is None or htf.empty or ltf.empty: return None
        last_htf = htf.iloc[-1]
        last_ltf = ltf.iloc[-1]
        prev_ltf = ltf.iloc[-10]
        
        # Trend alignment
        if last_htf['close'] > last_htf['SMC_ema_200']:
            if last_ltf['low'] < prev_ltf['low'] and last_ltf['SMC_mfi'] > prev_ltf['SMC_mfi']:
                sl, tp = StrategyFactory._calc_rr('long', last_ltf['close'], last_ltf['low'], 2.0)
                return {"side": "long", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        elif last_htf['close'] < last_htf['SMC_ema_200']:
            if last_ltf['high'] > prev_ltf['high'] and last_ltf['SMC_mfi'] < prev_ltf['SMC_mfi']:
                sl, tp = StrategyFactory._calc_rr('short', last_ltf['close'], last_ltf['high'], 2.0)
                return {"side": "short", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        return None

    # 29. NY Killzone FVG
    @staticmethod
    def ny_killzone_fvg(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        hour = last['timestamp'].hour
        if not (13 <= hour < 16): return None
        if last['SMC_fvg_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['SMC_fvg_bottom'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_fvg_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['SMC_fvg_top'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 31. ICT 2022 Mentorship Model (Strict)
    @staticmethod
    def ict_2022_model(df_dict, symbol):
        htf = df_dict.get('1h')
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if htf is None or ltf is None: return None
        last_htf = htf.iloc[-1]
        last_ltf = ltf.iloc[-1]
        
        # 1. HTF Context (POI)
        if last_htf['SMC_fvg_bullish'] or last_htf['SMC_ob_bullish']:
            # 2. LTF Liquidity Sweep + MSS + FVG
            if last_ltf['SMC_sweep_low'] and last_ltf['SMC_is_displacement'] and last_ltf['SMC_fvg_bullish']:
                sl, tp = StrategyFactory._calc_rr('long', last_ltf['close'], last_ltf['low'], 2.5)
                return {"side": "long", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        if last_htf['SMC_fvg_bearish'] or last_htf['SMC_ob_bearish']:
            if last_ltf['SMC_sweep_high'] and last_ltf['SMC_is_displacement'] and last_ltf['SMC_fvg_bearish']:
                sl, tp = StrategyFactory._calc_rr('short', last_ltf['close'], last_ltf['high'], 2.5)
                return {"side": "short", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        return None

    # 32. NY Silver Bullet (10 AM - 11 AM EST)
    @staticmethod
    def ny_silver_bullet(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        # 10:00 - 11:00 AM NY (approx 14:00 - 15:00 UTC)
        hour = last['timestamp'].hour
        if not (14 <= hour < 15): return None
        
        if last['SMC_fvg_bullish'] and last['SMC_is_discount']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_fvg_bearish'] and last['SMC_is_premium']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 33. Asian Range Sweep + Killzone Reversal
    @staticmethod
    def asian_sweep_kz_reversal(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None or ltf.empty: return None
        last = ltf.iloc[-1]
        hour = last['timestamp'].hour
        # London or NY Open
        if not ((2 <= hour < 5) or (12 <= hour < 15)): return None
        
        if last['low'] < last['SMC_asian_low'] and last['SMC_fvg_bullish']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['high'] > last['SMC_asian_high'] and last['SMC_fvg_bearish']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 34. SMC Breaker + Trend Alignment (60%+ Filter)
    @staticmethod
    def breaker_trend_pro(df_dict, symbol):
        htf = df_dict.get('1h')
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if htf is None or ltf is None: return None
        last_htf = htf.iloc[-1]
        last_ltf = ltf.iloc[-1]
        
        # Strict Trend + Breaker
        if last_htf['close'] > last_htf['SMC_ema_200'] and last_ltf['SMC_bb_bullish']:
            if last_ltf['SMC_mfi'] < 40:
                sl, tp = StrategyFactory._calc_rr('long', last_ltf['close'], last_ltf['low'], 2.0)
                return {"side": "long", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        if last_htf['close'] < last_htf['SMC_ema_200'] and last_ltf['SMC_bb_bearish']:
            if last_ltf['SMC_mfi'] > 60:
                sl, tp = StrategyFactory._calc_rr('short', last_ltf['close'], last_ltf['high'], 2.0)
                return {"side": "short", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        return None

    # 36. Premium/Discount MSS + FVG (High Conviction Reversal)
    @staticmethod
    def premium_discount_mss_fvg(df_dict, symbol):
        htf = df_dict.get('1h')
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if htf is None or ltf is None: return None
        last_htf = htf.iloc[-1]
        last_ltf = ltf.iloc[-1]
        
        # 1. HTF Premium/Discount
        if last_htf['SMC_is_premium']:
            # 2. LTF Shift + FVG + Displacement
            if last_ltf['SMC_sweep_high'] and last_ltf['SMC_fvg_bearish'] and last_ltf['SMC_is_displacement']:
                sl, tp = StrategyFactory._calc_rr('short', last_ltf['close'], last_ltf['high'], 3.0)
                return {"side": "short", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        if last_htf['SMC_is_discount']:
            if last_ltf['SMC_sweep_low'] and last_ltf['SMC_fvg_bullish'] and last_ltf['SMC_is_displacement']:
                sl, tp = StrategyFactory._calc_rr('long', last_ltf['close'], last_ltf['low'], 3.0)
                return {"side": "long", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        return None

    # 37. London/NY Overlap Sweep (The Power Hour)
    @staticmethod
    def overlap_sweep_reversal(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None: return None
        last = ltf.iloc[-1]
        hour = last['timestamp'].hour
        # 12:00 - 14:00 UTC (NY Open / London Close Overlap)
        if not (12 <= hour < 14): return None
        
        if last['SMC_sweep_low'] and last['SMC_mfi'] < 20:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.5)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_sweep_high'] and last['SMC_mfi'] > 80:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.5)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 38. Turtle Soup + MFI Divergence (Extreme Bottom/Top)
    @staticmethod
    def turtle_soup_mfi_div(df_dict, symbol):
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if ltf is None: return None
        last = ltf.iloc[-1]
        prev = ltf.iloc[-10]
        
        if last['SMC_sweep_low'] and last['low'] < prev['low'] and last['SMC_mfi'] > prev['SMC_mfi']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['low'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_sweep_high'] and last['high'] > prev['high'] and last['SMC_mfi'] < prev['SMC_mfi']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['high'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None

    # 39. Breaker Retest + Inducement (IOF Continuation)
    @staticmethod
    def breaker_retest_idm(df_dict, symbol):
        htf = df_dict.get('1h')
        ltf = df_dict.get('15m', df_dict.get('30m'))
        if htf is None or ltf is None: return None
        last_htf = htf.iloc[-1]
        last_ltf = ltf.iloc[-1]
        
        if last_htf['close'] > last_htf['SMC_ema_50']:
            if last_ltf['SMC_bb_bullish'] and last_ltf['SMC_is_idm']:
                sl, tp = StrategyFactory._calc_rr('long', last_ltf['close'], last_ltf['low'], 2.0)
                return {"side": "long", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        if last_htf['close'] < last_htf['SMC_ema_50']:
            if last_ltf['SMC_bb_bearish'] and last_ltf['SMC_is_idm']:
                sl, tp = StrategyFactory._calc_rr('short', last_ltf['close'], last_ltf['high'], 2.0)
                return {"side": "short", "entry": last_ltf['close'], "sl": sl, "tp": tp}
        return None

    # 40. ICT Macro 2.0 (Time + Price + Displacement)
    @staticmethod
    def ict_macro_strict(df_dict, symbol):
        ltf = df_dict.get('3m', df_dict.get('5m'))
        if ltf is None: return None
        last = ltf.iloc[-1]
        hour = last['timestamp'].hour
        minute = last['timestamp'].minute
        
        # Macro Windows (9:50-10:10, 10:50-11:10, 11:50-12:10, 13:50-14:10 UTC)
        is_macro = (hour == 9 and 50 <= minute) or (hour == 10 and minute <= 10) or \
                   (hour == 10 and 50 <= minute) or (hour == 11 and minute <= 10) or \
                   (hour == 11 and 50 <= minute) or (hour == 12 and minute <= 10) or \
                   (hour == 13 and 50 <= minute) or (hour == 14 and minute <= 10)
        
        if not is_macro: return None
        
        if last['SMC_fvg_bullish'] and last['SMC_is_displacement']:
            sl, tp = StrategyFactory._calc_rr('long', last['close'], last['SMC_fvg_bottom'], 2.0)
            return {"side": "long", "entry": last['close'], "sl": sl, "tp": tp}
        if last['SMC_fvg_bearish'] and last['SMC_is_displacement']:
            sl, tp = StrategyFactory._calc_rr('short', last['close'], last['SMC_fvg_top'], 2.0)
            return {"side": "short", "entry": last['close'], "sl": sl, "tp": tp}
        return None


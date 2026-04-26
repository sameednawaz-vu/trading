import pandas as pd
import numpy as np
import os
from agent import TradingAgent
from ict_concepts import annotate_ict_features

def load_and_prepare_data(symbol):
    timeframes = ['1h', '30m', '15m', '5m']
    dfs = {}

    for tf in timeframes:
        filepath = f"data/{symbol}_{tf}.csv"
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} missing")
            continue

        df = pd.read_csv(filepath)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        df = annotate_ict_features(df)

        # Shift higher timeframes to prevent lookahead bias!
        if tf != '5m':
            cols_to_shift = [c for c in df.columns if c != 'timestamp']
            df[cols_to_shift] = df[cols_to_shift].shift(1)
            df = df.dropna().reset_index(drop=True)

            rename_map = {col: f"{col}_{tf}" for col in df.columns if col != 'timestamp'}
            df = df.rename(columns=rename_map)

        dfs[tf] = df

    if '5m' not in dfs:
        return None

    master_df = dfs['5m']

    for tf in ['15m', '30m', '1h']:
        if tf in dfs:
            # Important: pd.merge_asof requires the 'on' column to be sorted
            # And it matches the nearest backward timestamp
            master_df = pd.merge_asof(master_df, dfs[tf], on='timestamp', direction='backward')

    # Drop rows with NaNs caused by the forward merge at the start
    # Note: Kraken fetch returned 500 rows. The 1h timeframe covers ~500 hours.
    # The 5m timeframe 500 rows only covers ~41 hours.
    # So we don't have overlapping 1h data for the early 5m candles.
    # To fix this so we don't drop all rows, we should forward fill or dropna with subset
    # Actually, if we merge backwards, if there is no previous 1h candle, it returns NaN.
    # Let's just dropna on the merged frame. If 5m window is strictly inside 1h window, this works.
    master_df = master_df.dropna().reset_index(drop=True)
    return master_df

def run_backtest(df, limit=None):
    agent = TradingAgent()
    trades = []
    active_trade = None

    if limit:
        df = df.head(limit)

    window_size = 10

    for i in range(window_size, len(df)):
        current_row = df.iloc[i]
        current_price = current_row['close']

        if active_trade:
            if active_trade['type'] == 'BUY':
                if current_row['low'] <= active_trade['sl']:
                    active_trade['exit_price'] = active_trade['sl']
                    active_trade['pnl'] = active_trade['sl'] - active_trade['entry_price']
                    active_trade['exit_time'] = current_row['timestamp']
                    trades.append(active_trade)
                    active_trade = None
                elif current_row['high'] >= active_trade['tp']:
                    active_trade['exit_price'] = active_trade['tp']
                    active_trade['pnl'] = active_trade['tp'] - active_trade['entry_price']
                    active_trade['exit_time'] = current_row['timestamp']
                    trades.append(active_trade)
                    active_trade = None
            elif active_trade['type'] == 'SELL':
                if current_row['high'] >= active_trade['sl']:
                    active_trade['exit_price'] = active_trade['sl']
                    active_trade['pnl'] = active_trade['entry_price'] - active_trade['sl']
                    active_trade['exit_time'] = current_row['timestamp']
                    trades.append(active_trade)
                    active_trade = None
                elif current_row['low'] <= active_trade['tp']:
                    active_trade['exit_price'] = active_trade['tp']
                    active_trade['pnl'] = active_trade['entry_price'] - active_trade['tp']
                    active_trade['exit_time'] = current_row['timestamp']
                    trades.append(active_trade)
                    active_trade = None
            continue

        window = df.iloc[i-window_size:i+1]

        context_str = f"Current Price: {current_price}\n"
        context_str += "Recent 5m ICT Signals:\n"
        context_str += window[['timestamp', 'close', 'fvg_bullish', 'fvg_bearish', 'sweep_high', 'sweep_low']].tail(3).to_string()

        if 'fvg_bullish_1h' in window.columns:
            context_str += f"\n1H Trend Context (Last values): FVG Bullish: {window['fvg_bullish_1h'].iloc[-1]}, OB Triggered: {window['ob_bullish_trigger_1h'].iloc[-1]}"

        decision = agent.predict(context_str)

        action = decision.get('action', 'HOLD')
        sl = decision.get('stop_loss')
        tp = decision.get('take_profit')

        if action in ['BUY', 'SELL'] and sl is not None and tp is not None:
            risk = abs(current_price - sl)
            reward = abs(tp - current_price)

            if risk > 0 and reward / risk >= 2.0:
                active_trade = {
                    'entry_time': current_row['timestamp'],
                    'type': action,
                    'entry_price': current_price,
                    'sl': float(sl),
                    'tp': float(tp)
                }
                print(f"[{current_row['timestamp']}] OPEN {action} @ {current_price}. SL: {sl}, TP: {tp}")

    return trades

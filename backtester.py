import pandas as pd
import json
import time
from data_ingestion import DataIngestor
from ict_engine import ICTEngine
from agent.brain import TradingBrain
from agent.memory import MemoryManager
import warnings

# Suppress pandas FutureWarnings and numba warnings from smc
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)

class Backtester:
    def __init__(self, start_date=None, rules_context=""):
        self.ingestor = DataIngestor()
        self.engine = ICTEngine()
        self.brain = TradingBrain()
        self.memory = MemoryManager()
        self.start_date = start_date
        self.rules_context = rules_context

    def run(self, symbols=['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT'], timeframes=['15m']):
        for symbol in symbols:
            for tf in timeframes:
                print(f"--- Running Backtest on {symbol} {tf} ---")
                import os
                filename = f"{symbol.replace('/', '_')}_{tf}.csv"
                path = os.path.join(self.ingestor.data_path, filename)
                if os.path.exists(path):
                    df = pd.read_csv(path, parse_dates=['timestamp'])
                else:
                    df = None
                if df is None or len(df) == 0:
                    print(f"No data for {symbol} {tf}")
                    continue

                # Filter start date if needed for optimizer iterations
                if self.start_date:
                    df = df[df['timestamp'] >= self.start_date].copy()

                df.reset_index(drop=True, inplace=True)

                # Minimum candles needed to compute SMC
                window_size = 100
                if len(df) < window_size:
                    print(f"Not enough data for {symbol} {tf}")
                    continue

                active_trade = None

                for i in range(window_size, len(df)):
                    # Simulating live data feed
                    current_row = df.iloc[i]
                    current_price = current_row['close']
                    current_time = current_row['timestamp']

                    if active_trade:
                        # Check if stop loss or take profit hit
                        side = active_trade['side']
                        sl = active_trade['stop_loss']
                        tp = active_trade['take_profit']

                        high = current_row['high']
                        low = current_row['low']

                        result = None
                        pnl = 0

                        if side == "Long":
                            if low <= sl:
                                result = "failure"
                                pnl = -1
                            elif high >= tp:
                                result = "success"
                                pnl = (tp - active_trade['entry_price']) / (active_trade['entry_price'] - sl) # RR based
                        elif side == "Short":
                            if high >= sl:
                                result = "failure"
                                pnl = -1
                            elif low <= tp:
                                result = "success"
                                pnl = (active_trade['entry_price'] - tp) / (sl - active_trade['entry_price'])

                        if result:
                            # Update trade result
                            self.memory.update_trade_result(active_trade['db_id'], result, pnl)
                            if result == "failure":
                                self.memory.store_pattern("failures", f"trade_{active_trade['db_id']}", active_trade)
                            print(f"[{current_time}] Trade closed: {result} | PnL: {pnl:.2f}R")
                            active_trade = None

                        # Wait for trade to close before opening a new one
                        continue

                    # If no active trade, look for a setup periodically (e.g. every new candle)
                    # We compute features on the window UP TO the current candle (exclusive) to avoid lookahead
                    window_df = df.iloc[i-window_size:i].copy()

                    try:
                        features = self.engine.compute_smc_features(window_df)
                        bias = self.engine.get_bias(window_df)
                        kz = self.engine.is_killzone(current_time)
                    except Exception as e:
                        # smc library might fail if not enough variation
                        continue

                    # Extract the very last known features (most recent signals)
                    recent_fvg = {}
                    if not features['fvg'].empty:
                        last_fvg = features['fvg'].iloc[-1]
                        recent_fvg = last_fvg.to_dict()

                    recent_ob = {}
                    if not features['ob'].empty:
                        last_ob = features['ob'].iloc[-1]
                        recent_ob = last_ob.to_dict()

                    market_data = {
                        "price": current_price,
                        "bias": bias,
                        "killzone": str(kz),
                        "features": {
                            "fvg": recent_fvg,
                            "ob": recent_ob
                        }
                    }

                    # Ask Brain
                    res_json = self.brain.generate_hypothesis(market_data, rules_context=self.rules_context)
                    try:
                        setup = json.loads(res_json)
                        if setup.get("side") in ["Long", "Short"]:
                            print(f"[{current_time}] Trade Setup Found: {setup['side']} @ {setup['entry_price']}")
                            # Log trade
                            trade_data = {
                                'symbol': symbol,
                                'timeframe': tf,
                                'side': setup['side'],
                                'entry_price': setup['entry_price'],
                                'stop_loss': setup['stop_loss'],
                                'take_profit': setup['take_profit'],
                                'setup_details': market_data
                            }
                            trade_id = self.memory.log_trade(trade_data)
                            setup['db_id'] = trade_id
                            active_trade = setup

                            # API Rate limits mitigation
                            # time.sleep(2)  # removed sleep to speed up backtest
                    except json.JSONDecodeError:
                        pass

if __name__ == "__main__":
    bt = Backtester()
    # Test on a single symbol/tf first to verify


    bt.run()

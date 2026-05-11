import pandas as pd
import os
import json
import sqlite3
from tqdm import tqdm
from ict_engine import ICTEngine
from agent.brain import TradingBrain

class Backtester:
    def __init__(self, data_dir='./data', db_path='./logs/trading_memory.db'):
        self.data_dir = data_dir
        self.db_path = db_path
        self.ict = ICTEngine()
        self.brain = TradingBrain()

        # Ensure logs directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                timeframe TEXT,
                timestamp TEXT,
                side TEXT,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                outcome TEXT,
                pnl REAL,
                model_used TEXT,
                reason TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def run_backtest(self, symbol, htf='1h', ltf='15m'):
        print(f"Running backtest for {symbol} ({htf} -> {ltf})")

        # Load Data
        htf_file = os.path.join(self.data_dir, f"{symbol.replace('/', '_')}_{htf}_full.csv")
        ltf_file = os.path.join(self.data_dir, f"{symbol.replace('/', '_')}_{ltf}_full.csv")

        if not os.path.exists(htf_file) or not os.path.exists(ltf_file):
            print(f"Data files missing for {symbol}. Skipping.")
            return []

        df_htf = pd.read_csv(htf_file, parse_dates=['timestamp'])
        df_ltf = pd.read_csv(ltf_file, parse_dates=['timestamp'])

        # Compute Features
        print(f"Computing SMC features for HTF ({htf})...")
        htf_features = self.ict.compute_smc_features(df_htf)

        print(f"Computing SMC features for LTF ({ltf})...")
        ltf_features = self.ict.compute_smc_features(df_ltf)

        # Shift HTF features by 1 to prevent lookahead bias!
        # Need to align the dataframes. Let's create a combined feature dataframe
        # for HTF and then merge_asof

        # For simplicity in this script, we'll iterate through LTF and look up the *previous* HTF candle
        trades = []
        active_trade = None

        # Optimization: pre-calculate bias
        bias_series = []
        # Calculate rolling bias (this is simplified, ideally you'd calculate it efficiently)
        # For backtesting, we can pre-calculate bias at each HTF step
        print("Pre-calculating HTF Bias...")
        # Since getting bias per row is slow, let's just use the last 20 rows of HTF at each step
        # Actually, let's just do it dynamically in the loop but optimize the lookup

        df_htf = df_htf.sort_values('timestamp').reset_index(drop=True)
        df_ltf = df_ltf.sort_values('timestamp').reset_index(drop=True)

        for i in tqdm(range(50, len(df_ltf)), desc=f"Backtesting {symbol}"):
            row = df_ltf.iloc[i]
            timestamp = row['timestamp']

            # 1. Check if we have an active trade to manage
            if active_trade:
                if active_trade['side'] == 'Long':
                    if row['low'] <= active_trade['stop_loss']:
                        active_trade['outcome'] = 'Loss'
                        active_trade['pnl'] = active_trade['stop_loss'] - active_trade['entry_price']
                        trades.append(active_trade)
                        active_trade = None
                    elif row['high'] >= active_trade['take_profit']:
                        active_trade['outcome'] = 'Win'
                        active_trade['pnl'] = active_trade['take_profit'] - active_trade['entry_price']
                        trades.append(active_trade)
                        active_trade = None
                elif active_trade['side'] == 'Short':
                    if row['high'] >= active_trade['stop_loss']:
                        active_trade['outcome'] = 'Loss'
                        active_trade['pnl'] = active_trade['entry_price'] - active_trade['stop_loss']
                        trades.append(active_trade)
                        active_trade = None
                    elif row['low'] <= active_trade['take_profit']:
                        active_trade['outcome'] = 'Win'
                        active_trade['pnl'] = active_trade['entry_price'] - active_trade['take_profit']
                        trades.append(active_trade)
                        active_trade = None
                continue # Don't take new trades while one is active

            # 2. Killzone Check
            kz = self.ict.is_killzone(timestamp)
            if not kz: continue

            # 3. Get HTF context (previous candle to avoid lookahead)
            htf_past = df_htf[df_htf['timestamp'] < timestamp]
            if len(htf_past) < 50: continue

            bias = self.ict.get_bias(htf_past.tail(50))

            # Slice LTF features up to current index
            # This is slightly inaccurate because smc features change retroactively,
            # but for a fast backtester approximation we use the latest computed value.

            market_data = {
                "timestamp": str(timestamp),
                "price": row['close'],
                "bias": bias,
                "killzone": kz,
                "features": {
                    "htf_fvg": {"FVG": {}, "Top": {}, "Bottom": {}},
                    "fvg": {"FVG": {}, "Top": {}, "Bottom": {}}
                }
            }

            # Grab recent HTF FVGs (from full computed array, filtering by past index)
            htf_idx = htf_past.index[-1]
            # Since SMC library outputs pd.Series aligned with df index:
            try:
                # We only want FVGs that are active at htf_idx.
                if htf_features['fvg']['FVG'].iloc[htf_idx] != 0:
                     market_data['features']['htf_fvg']['FVG']["0"] = htf_features['fvg']['FVG'].iloc[htf_idx]
                     market_data['features']['htf_fvg']['Top']["0"] = htf_features['fvg']['Top'].iloc[htf_idx]
                     market_data['features']['htf_fvg']['Bottom']["0"] = htf_features['fvg']['Bottom'].iloc[htf_idx]
            except: pass

            try:
                # LTF FVGs
                if ltf_features['fvg']['FVG'].iloc[i] != 0:
                     market_data['features']['fvg']['FVG']["0"] = ltf_features['fvg']['FVG'].iloc[i]
                     market_data['features']['fvg']['Top']["0"] = ltf_features['fvg']['Top'].iloc[i]
                     market_data['features']['fvg']['Bottom']["0"] = ltf_features['fvg']['Bottom'].iloc[i]
            except: pass

            # Query Brain
            decision_json = self.brain.generate_hypothesis(market_data)
            try:
                decision = json.loads(decision_json)
                if decision.get('side') in ['Long', 'Short']:
                    active_trade = {
                        'symbol': symbol,
                        'timeframe': ltf,
                        'timestamp': str(timestamp),
                        'side': decision['side'],
                        'entry_price': decision['entry_price'],
                        'stop_loss': decision['stop_loss'],
                        'take_profit': decision['take_profit'],
                        'model_used': decision.get('model_used', 'Unknown'),
                        'reason': decision.get('reason', '')
                    }
                    print(f"[{timestamp}] Entered {active_trade['side']} on {symbol} @ {active_trade['entry_price']}")
            except json.JSONDecodeError:
                pass

        # Save trades to DB
        if trades:
            self._save_trades(trades)

        return trades

    def _save_trades(self, trades):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for t in trades:
            c.execute('''
                INSERT INTO trades (symbol, timeframe, timestamp, side, entry_price, stop_loss, take_profit, outcome, pnl, model_used, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (t['symbol'], t['timeframe'], t['timestamp'], t['side'], t['entry_price'], t['stop_loss'], t['take_profit'], t['outcome'], t['pnl'], t['model_used'], t['reason']))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    bt = Backtester()
    symbols = [
        "BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD",
        "ADA/USD", "ALGO/USD", "APE/USD", "ATOM/USD", "AVAX/USD",
        "BCH/USD", "DOGE/USD", "DOT/USD", "LINK/USD", "LTC/USD",
        "MATIC/USD", "NEAR/USD", "SHIB/USD", "TRX/USD", "UNI/USD"
    ]
    for sym in symbols:
        bt.run_backtest(sym, htf='1h', ltf='15m')
        bt.run_backtest(sym, htf='30m', ltf='5m')

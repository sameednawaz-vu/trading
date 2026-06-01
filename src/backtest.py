import pandas as pd
import json
import sqlite3
import os
from datetime import timezone
from .data_ingestion import DataIngestor
from .ict_engine import ICTEngine
from agent.brain import TradingBrain

class Backtester:
    def __init__(self):
        self.data_ingestor = DataIngestor()
        self.engine = ICTEngine()
        self.brain = TradingBrain()
        self.db_path = './logs/trading_memory.db'
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                timeframe TEXT,
                entry_time TEXT,
                side TEXT,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                exit_price REAL,
                exit_time TEXT,
                pnl REAL,
                model_used TEXT,
                reason TEXT,
                outcome TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def get_htf_context(self, htf_df, current_time):
        """
        Slices HTF data rigorously to prevent lookahead bias.
        Only includes rows where the HTF candle has fully closed *before* the current time.
        """
        if htf_df is None or htf_df.empty:
            return None

        # Determine HTF interval delta to check for strict close
        # E.g., if HTF is 1h, a candle opening at 10:00 closes at 11:00
        # We only consider it fully closed if current_time >= 11:00.
        try:
            interval = htf_df['timestamp'].iloc[1] - htf_df['timestamp'].iloc[0]
        except:
            return None

        # The close time of a candle is its open timestamp + interval
        # Therefore, we filter where timestamp + interval <= current_time
        closed_mask = (htf_df['timestamp'] + interval) <= current_time
        past_htf = htf_df.loc[closed_mask]

        if past_htf.empty:
            return None

        return past_htf.iloc[-100:] # Return last 100 closed candles for context

    def run_backtest(self, symbol, timeframe, start_date, end_date):
        """Main backtesting loop."""
        print(f"Starting backtest for {symbol} on {timeframe}")

        # Load local data if available, else return
        ltf_df = self.data_ingestor.load_full_data(symbol, timeframe)
        htf_df = self.data_ingestor.load_full_data(symbol, '1h')

        if ltf_df is None or htf_df is None:
            print(f"Missing data for {symbol}. Skipping.")
            return []

        ltf_df = ltf_df[(ltf_df['timestamp'] >= start_date) & (ltf_df['timestamp'] <= end_date)].reset_index(drop=True)

        trades = []
        active_trade = None

        # Start looking after first 100 candles for indicator warmup
        for i in range(100, len(ltf_df)):
            current_row = ltf_df.iloc[i]
            current_time = current_row['timestamp']
            price = current_row['close']

            # 1. Manage Active Trade
            if active_trade:
                high = current_row['high']
                low = current_row['low']

                # Check for stop loss or take profit hits
                if active_trade['side'] == 'Long':
                    if low <= active_trade['stop_loss']:
                        active_trade['exit_price'] = active_trade['stop_loss']
                        active_trade['exit_time'] = current_time
                        active_trade['pnl'] = (active_trade['exit_price'] - active_trade['entry_price']) / active_trade['entry_price']
                        active_trade['outcome'] = 'Loss'
                        self.evaluate_trade_outcome(active_trade)
                        trades.append(active_trade)
                        active_trade = None
                    elif high >= active_trade['take_profit']:
                        active_trade['exit_price'] = active_trade['take_profit']
                        active_trade['exit_time'] = current_time
                        active_trade['pnl'] = (active_trade['exit_price'] - active_trade['entry_price']) / active_trade['entry_price']
                        active_trade['outcome'] = 'Win'
                        self.evaluate_trade_outcome(active_trade)
                        trades.append(active_trade)
                        active_trade = None
                elif active_trade['side'] == 'Short':
                    if high >= active_trade['stop_loss']:
                        active_trade['exit_price'] = active_trade['stop_loss']
                        active_trade['exit_time'] = current_time
                        active_trade['pnl'] = (active_trade['entry_price'] - active_trade['exit_price']) / active_trade['entry_price']
                        active_trade['outcome'] = 'Loss'
                        self.evaluate_trade_outcome(active_trade)
                        trades.append(active_trade)
                        active_trade = None
                    elif low <= active_trade['take_profit']:
                        active_trade['exit_price'] = active_trade['take_profit']
                        active_trade['exit_time'] = current_time
                        active_trade['pnl'] = (active_trade['entry_price'] - active_trade['exit_price']) / active_trade['entry_price']
                        active_trade['outcome'] = 'Win'
                        self.evaluate_trade_outcome(active_trade)
                        trades.append(active_trade)
                        active_trade = None
                continue

            # 2. Check Local Pre-conditions (Local Filter to save API calls)
            # Only trigger LLM if in killzone and local conditions look interesting
            kz = self.engine.is_killzone(current_time)
            if not kz:
                continue

            past_ltf = ltf_df.iloc[max(0, i-100):i+1].copy()
            past_htf = self.get_htf_context(htf_df, current_time)

            if past_htf is None or len(past_htf) < 20:
                continue

            if self.check_local_conditions(past_ltf, past_htf, current_time, price, kz):
                trade_decision = self.execute_trade(past_ltf, past_htf, symbol, timeframe, current_time, price, kz)
                if trade_decision and trade_decision.get('side') in ['Long', 'Short']:

                    # Validate RR is at least 1:2
                    entry = trade_decision.get('entry_price')
                    sl = trade_decision.get('stop_loss')
                    tp = trade_decision.get('take_profit')

                    if entry is None or sl is None or tp is None:
                        continue
                    if trade_decision['side'] == 'Long':
                        risk = entry - sl
                        reward = tp - entry
                    else:
                        risk = sl - entry
                        reward = entry - tp

                    if risk > 0 and (reward / risk) >= 2.0:
                        active_trade = {
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'entry_time': current_time,
                            'side': trade_decision['side'],
                            'entry_price': entry,
                            'stop_loss': sl,
                            'take_profit': tp,
                            'model_used': trade_decision.get('model_used', 'Unknown'),
                            'reason': trade_decision.get('reason', '')
                        }
                    else:
                        print(f"Trade rejected: Insufficient RR {reward/risk if risk > 0 else 0}")

        return trades

    def check_local_conditions(self, ltf_df, htf_df, current_time, price, kz):
        """
        Local filter to prevent spamming the LLM API (40 RPM limit).
        Returns True if we see a recent FVG or a sweep in the LTF data.
        """
        features = self.engine.compute_smc_features(ltf_df)
        fvg = features['fvg']

        # Check if there's any FVG in the last 5 candles
        recent_fvg = fvg.tail(5)
        has_fvg = not recent_fvg[recent_fvg['FVG'] != 0].empty

        return has_fvg

    def execute_trade(self, ltf_df, htf_df, symbol, timeframe, current_time, price, kz):
        """Queries Sovereign Brain for a trade decision."""
        htf_bias = self.engine.get_bias(htf_df)
        htf_features = self.engine.compute_smc_features(htf_df)
        ltf_features = self.engine.compute_smc_features(ltf_df)

        market_data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "time": str(current_time),
            "price": price,
            "bias": htf_bias,
            "killzone": kz,
            "features": {
                "fvg": {
                    "Top": ltf_features['fvg']['Top'].dropna().tail(3).to_dict(),
                    "Bottom": ltf_features['fvg']['Bottom'].dropna().tail(3).to_dict()
                },
                "htf_fvg": {
                    "FVG": htf_features['fvg']['FVG'].dropna().tail(3).to_dict(),
                    "Top": htf_features['fvg']['Top'].dropna().tail(3).to_dict(),
                    "Bottom": htf_features['fvg']['Bottom'].dropna().tail(3).to_dict()
                }
            }
        }

        response_json = self.brain.generate_hypothesis(market_data)
        try:
            return json.loads(response_json)
        except:
            return None

    def evaluate_trade_outcome(self, trade):
        """Logs trade to DB and reflections if it was a loss."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (symbol, timeframe, entry_time, side, entry_price, stop_loss, take_profit, exit_price, exit_time, pnl, model_used, reason, outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade['symbol'], trade['timeframe'], str(trade['entry_time']), trade['side'],
            trade['entry_price'], trade['stop_loss'], trade['take_profit'], trade['exit_price'],
            str(trade['exit_time']), trade['pnl'], trade['model_used'], trade['reason'], trade['outcome']
        ))
        conn.commit()
        conn.close()

        # If it was a loss, tell brain to reflect
        if trade['outcome'] == 'Loss':
            self.brain.reflect_on_failure(trade, "Stop loss hit")

if __name__ == "__main__":
    pass

def generate_report(db_path='./logs/trading_memory.db'):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM trades", conn)
    conn.close()

    if df.empty:
        print("No trades logged in the database.")
        return

    total_trades = len(df)
    wins = len(df[df['outcome'] == 'Win'])
    losses = len(df[df['outcome'] == 'Loss'])
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

    # Approx RR calculation (avg risk vs avg reward on realized trades)
    avg_pnl_win = df[df['outcome'] == 'Win']['pnl'].mean() if wins > 0 else 0
    avg_pnl_loss = abs(df[df['outcome'] == 'Loss']['pnl'].mean()) if losses > 0 else 0
    avg_rr = avg_pnl_win / avg_pnl_loss if avg_pnl_loss > 0 else 0

    # Monthly trades estimate
    try:
        first_trade = pd.to_datetime(df['entry_time'].min())
        last_trade = pd.to_datetime(df['exit_time'].max())
        days = (last_trade - first_trade).days
        months = max(1, days / 30.0)
        trades_per_month = total_trades / months
    except:
        trades_per_month = total_trades

    print("\n" + "="*40)
    print("BACKTESTING REPORT")
    print("="*40)
    print(f"Total Trades         : {total_trades}")
    print(f"Wins / Losses        : {wins} / {losses}")
    print(f"Win Rate             : {win_rate:.2f}%")
    print(f"Avg Realized RR      : 1 : {avg_rr:.2f}")
    print(f"Est. Trades / Month  : {trades_per_month:.1f}")
    print("="*40 + "\n")

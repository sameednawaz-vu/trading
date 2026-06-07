import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import json
import sqlite3
import time
from datetime import timezone
from ict_engine import ICTEngine
from agent.brain import TradingBrain
from tqdm import tqdm
from tabulate import tabulate

class Backtester:
    def __init__(self, db_path='./logs/trading_memory.db', mempalace_dir='./mempalace/'):
        self.engine = ICTEngine()
        self.brain = TradingBrain()
        self.db_path = db_path
        self.mempalace_dir = mempalace_dir

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.mempalace_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS trades
                     (id INTEGER PRIMARY KEY, symbol TEXT, side TEXT, entry_price REAL,
                      sl REAL, tp REAL, model TEXT, reason TEXT, entry_time TEXT,
                      exit_time TEXT, status TEXT, pnl REAL)''')
        conn.commit()
        conn.close()

    def log_trade(self, trade):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO trades
                     (symbol, side, entry_price, sl, tp, model, reason, entry_time, exit_time, status, pnl)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (trade['symbol'], trade['side'], trade['entry_price'], trade['sl'], trade['tp'],
                   trade['model'], trade['reason'], trade['entry_time'], trade['exit_time'], trade['status'], trade['pnl']))
        trade_id = c.lastrowid
        conn.commit()
        conn.close()

        if trade['status'] == 'Loss':
            # Save to mempalace
            filepath = os.path.join(self.mempalace_dir, f"failed_trade_{trade_id}.json")
            with open(filepath, 'w') as f:
                json.dump(trade, f, indent=4)
            # Self-improve
            self.brain.reflect_on_failure(trade, "Hit Stop Loss")

    def run_backtest(self, symbol, ltf_file, htf_file):
        print(f"Loading data for {symbol}...")
        ltf_df = pd.read_csv(ltf_file, parse_dates=['timestamp'])
        htf_df = pd.read_csv(htf_file, parse_dates=['timestamp'])

        ltf_df['timestamp'] = pd.to_datetime(ltf_df['timestamp'], utc=True)
        htf_df['timestamp'] = pd.to_datetime(htf_df['timestamp'], utc=True)
        
        # We process in chunks to simulate time flowing
        trades = []
        active_trade = None
        
        print("Computing SMC Features (Initial Chunk)...")
        # Optimization: Pre-compute large chunks
        chunk_size = 500
        total_rows = len(ltf_df)
        
        # Metrics
        api_calls = 0
        
        for i in tqdm(range(50, total_rows), desc="Backtesting"):
            current_time = ltf_df.iloc[i]['timestamp']
            current_price = ltf_df.iloc[i]['close']
            high = ltf_df.iloc[i]['high']
            low = ltf_df.iloc[i]['low']
            
            # Manage active trade
            if active_trade:
                if active_trade['side'] == 'Long':
                    if low <= active_trade['sl']:
                        active_trade['status'] = 'Loss'
                        active_trade['exit_time'] = str(current_time)
                        active_trade['pnl'] = active_trade['sl'] - active_trade['entry_price']
                        self.log_trade(active_trade)
                        trades.append(active_trade)
                        active_trade = None
                    elif high >= active_trade['tp']:
                        active_trade['status'] = 'Win'
                        active_trade['exit_time'] = str(current_time)
                        active_trade['pnl'] = active_trade['tp'] - active_trade['entry_price']
                        self.log_trade(active_trade)
                        trades.append(active_trade)
                        active_trade = None
                elif active_trade['side'] == 'Short':
                    if high >= active_trade['sl']:
                        active_trade['status'] = 'Loss'
                        active_trade['exit_time'] = str(current_time)
                        active_trade['pnl'] = active_trade['entry_price'] - active_trade['sl']
                        self.log_trade(active_trade)
                        trades.append(active_trade)
                        active_trade = None
                    elif low <= active_trade['tp']:
                        active_trade['status'] = 'Win'
                        active_trade['exit_time'] = str(current_time)
                        active_trade['pnl'] = active_trade['entry_price'] - active_trade['tp']
                        self.log_trade(active_trade)
                        trades.append(active_trade)
                        active_trade = None
                continue # Skip new setups if already in a trade

            # Pre-filter: Killzone
            kz = self.engine.is_killzone(current_time)
            if not kz:
                continue

            # Filter HTF (Strictly past closed)
            closed_htf = htf_df[htf_df['timestamp'] < current_time]
            if len(closed_htf) < 50:
                continue

            # Compute recent features
            recent_ltf = ltf_df.iloc[i-30:i+1].copy()
            recent_htf = closed_htf.tail(30).copy()

            ltf_features = self.engine.compute_smc_features(recent_ltf)
            htf_features = self.engine.compute_smc_features(recent_htf)

            bias = self.engine.get_bias(recent_htf)

            # Extract latest local FVG/OB locally to minimize API calls
            latest_fvg = ltf_features['fvg'].iloc[-1]
            latest_ob = ltf_features['ob'].iloc[-1]
            if latest_fvg['FVG'] == 0 and latest_ob['OB'] == 0:
                continue # No active local POI

            # Prepare data for brain
            fvg_dict = {
                'FVG': ltf_features['fvg']['FVG'].tail(5).to_dict(),
                'Top': ltf_features['fvg']['Top'].tail(5).to_dict(),
                'Bottom': ltf_features['fvg']['Bottom'].tail(5).to_dict()
            }
            htf_fvg_dict = {
                'FVG': htf_features['fvg']['FVG'].tail(3).to_dict(),
                'Top': htf_features['fvg']['Top'].tail(3).to_dict(),
                'Bottom': htf_features['fvg']['Bottom'].tail(3).to_dict()
            }
            
            market_data = {
                'symbol': symbol,
                'price': current_price,
                'time': str(current_time),
                'killzone': kz,
                'bias': bias,
                'features': {
                    'fvg': fvg_dict,
                    'htf_fvg': htf_fvg_dict
                }
            }
            
            # 40 RPM strict adherence
            if api_calls >= 40:
                print("Hit local 40 RPM limit, waiting 60s...")
                time.sleep(60)
                api_calls = 0
            
            decision_raw = self.brain.generate_hypothesis(market_data)
            api_calls += 1

            try:
                decision = json.loads(decision_raw)
                if decision.get('side') in ['Long', 'Short']:
                    # Force RR Validation
                    entry = float(decision['entry_price'])
                    sl = float(decision['stop_loss'])
                    tp = float(decision['take_profit'])

                    risk = abs(entry - sl)
                    reward = abs(tp - entry)

                    if risk > 0 and (reward / risk) >= 2.0:
                        active_trade = {
                            'symbol': symbol,
                            'side': decision['side'],
                            'entry_price': entry,
                            'sl': sl,
                            'tp': tp,
                            'model': decision.get('model_used', 'Unknown'),
                            'reason': decision.get('reason', ''),
                            'entry_time': str(current_time),
                            'status': 'Open',
                            'pnl': 0.0
                        }
            except:
                pass

        return trades

    def generate_report(self, trades, output_file='STRATEGY_REPORT.md'):
        if not trades:
            with open(output_file, 'w') as f:
                f.write("# Strategy Report\nNo trades executed.\n")
            return

        wins = [t for t in trades if t['status'] == 'Win']
        losses = [t for t in trades if t['status'] == 'Loss']
        win_rate = len(wins) / len(trades) if trades else 0
        
        # Calculate RR
        rrs = []
        for t in wins:
            risk = abs(t['entry_price'] - t['sl'])
            reward = abs(t['tp'] - t['entry_price'])
            if risk > 0: rrs.append(reward/risk)
        avg_rr = sum(rrs)/len(rrs) if rrs else 0
        
        # Estimated trades per month
        # Assuming the timeframe we passed was 1 year
        est_monthly = len(trades) / 12.0

        report = f"""# Autonomous ICT Trading Agent - Strategy Report

## Overall Performance Metrics
- **Total Executed Trades:** {len(trades)}
- **Successful Trades:** {len(wins)}
- **Failed Trades:** {len(losses)}
- **Success Rate (Win Rate):** {win_rate * 30:.2f}%
- **Average Risk/Reward Ratio:** 1:{avg_rr:.2f}
- **Estimated Average Monthly Trades:** {est_monthly:.2f}

## Targets Check
- Target Win Rate: >85% (Current: {win_rate * 30:.2f}%)
- Target R:R: >= 1:2 (Current: 1:{avg_rr:.2f})
- Target Monthly Volume: >= 40-60 (Current: {est_monthly:.2f})

"""
        with open(output_file, 'w') as f:
            f.write(report)
        print(report)

if __name__ == "__main__":
    tester = Backtester()
    # We use a short timeframe for test suite verification
    trades = tester.run_backtest("BTC/USD", "./data/BTC_USD_5m_full.csv", "./data/BTC_USD_1h_full.csv")
    tester.generate_report(trades)

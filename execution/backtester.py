import pandas as pd
import json
import os
import time
from tqdm import tqdm
from agent.brain import TradingBrain
from ict_engine import ICTEngine

class Backtester:
    def __init__(self, start_date_str, end_date_str):
        self.brain = TradingBrain()
        self.engine = ICTEngine()
        self.data_path = './data'
        self.state_path = './agency_state.json'
        
        self.start_dt = pd.to_datetime(start_date_str, utc=True)
        self.end_dt = pd.to_datetime(end_date_str, utc=True)
        
        self.symbols = [
            'BTC_USD', 'ETH_USD', 'SOL_USD', 'BNB_USD', 'XRP_USD',
            'ADA_USD', 'ALGO_USD', 'APE_USD', 'ATOM_USD', 'AVAX_USD',
            'BCH_USD', 'DOGE_USD', 'DOT_USD', 'DAI_USD', 'CRO_USD',
            'UNI_USD', 'LINK_USD', 'LTC_USD', 'MATIC_USD', 'NEAR_USD'
        ]
        
        self.timeframes = ['3m', '5m', '15m', '30m']
        
    def _load_state(self):
        if os.path.exists(self.state_path):
             with open(self.state_path, 'r') as f:
                  return json.load(f)
        return {"total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0, "avg_rr": 0, "monthly_trades": 0, "history": []}

    def _save_state(self, state):
        with open(self.state_path, 'w') as f:
             json.dump(state, f, indent=4)

    def _get_htf_data(self, htf_df, current_time):
         past_htf = htf_df[htf_df['timestamp'] < current_time]
         if past_htf.empty:
             return pd.DataFrame()
         return past_htf.tail(200).copy()

    def load_data(self, symbol, timeframe):
        path = os.path.join(self.data_path, f"{symbol}_{timeframe}_full.csv")
        if os.path.exists(path):
            df = pd.read_csv(path, parse_dates=['timestamp'])
            return df[(df['timestamp'] >= self.start_dt) & (df['timestamp'] <= self.end_dt)].copy()
        return None

    def run_backtest(self, max_runs=1000): # Allow extensive runs to achieve goal
        for run in range(max_runs):
            state = self._load_state()
            print(f"\n--- Backtest Run {run + 1} ---")
            print(f"Current Metrics - Win Rate: {state['win_rate']}%, Trades: {state['total_trades']}")

            if state['win_rate'] >= 85 and state['monthly_trades'] >= 40:
                 print("Goals met! Autonomous Backtesting complete.")
                 break

            trades = []
            wins = 0
            losses = 0
            sum_rr = 0

            for symbol in self.symbols:
                df_1h = self.load_data(symbol, '1h')
                if df_1h is None or df_1h.empty:
                     continue

                for tf in self.timeframes:
                    df_ltf = self.load_data(symbol, tf)
                    if df_ltf is None or df_ltf.empty:
                         continue

                    print(f"Testing {symbol} on {tf}...")

                    start_idx = 100
                    for i in tqdm(range(start_idx, len(df_ltf))):
                        current_time = df_ltf.iloc[i]['timestamp']
                        current_price = df_ltf.iloc[i]['close']

                        kz = self.engine.is_killzone(current_time)
                        if not kz or kz not in ['London', 'New York']:
                             continue

                        htf_past = self._get_htf_data(df_1h, current_time)
                        if htf_past.empty or len(htf_past) < 50:
                             continue

                        htf_bias = self.engine.get_bias(htf_past)
                        htf_features = self.engine.compute_smc_features(htf_past)

                        ltf_past = df_ltf.iloc[i-100:i+1].copy()
                        ltf_features = self.engine.compute_smc_features(ltf_past)

                        market_data = {
                             "symbol": symbol,
                             "timeframe": tf,
                             "time": current_time.isoformat(),
                             "price": current_price,
                             "bias": htf_bias,
                             "killzone": kz,
                             "features": {
                                  "htf_fvg": htf_features['fvg'].to_dict() if not htf_features['fvg'].empty else {},
                                  "fvg": ltf_features['fvg'].to_dict() if not ltf_features['fvg'].empty else {},
                             }
                        }

                        hypothesis = self.brain.generate_hypothesis(market_data)
                        try:
                             decision = json.loads(hypothesis)
                        except:
                             continue

                        if decision.get('side') in ['Long', 'Short']:
                             entry = decision['entry_price']
                             sl = decision['stop_loss']
                             tp = decision['take_profit']

                             rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
                             if rr < 2.0:
                                  continue

                             outcome = 'Pending'
                             future_data = df_ltf.iloc[i+1:i+100]

                             for _, row in future_data.iterrows():
                                  high = row['high']
                                  low = row['low']

                                  if decision['side'] == 'Long':
                                       if low <= sl: outcome = 'Loss'; break
                                       if high >= tp: outcome = 'Win'; break
                                  elif decision['side'] == 'Short':
                                       if high >= sl: outcome = 'Loss'; break
                                       if low <= tp: outcome = 'Win'; break

                             if outcome == 'Pending':
                                  outcome = 'Loss'

                             trade = {
                                  "id": f"{symbol}_{tf}_{current_time.timestamp()}",
                                  "side": decision['side'],
                                  "entry": entry,
                                  "sl": sl,
                                  "tp": tp,
                                  "outcome": outcome,
                                  "rr": rr,
                                  "time": current_time.isoformat()
                             }
                             trades.append(trade)
                             self.brain.log_trade(trade['id'], trade['side'], entry, sl, tp, outcome, decision.get('model_used', ''), decision.get('reason', ''))

                             if outcome == 'Win':
                                  wins += 1
                                  sum_rr += rr
                             else:
                                  losses += 1
                                  self.brain.reflect_on_failure(trade, outcome)
                                  time.sleep(2)

            total_trades = wins + losses
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            avg_rr = (sum_rr / wins) if wins > 0 else 0

            days = (self.end_dt - self.start_dt).days
            monthly_trades = (total_trades / days * 30) if days > 0 else 0

            new_state = {
                 "total_trades": total_trades,
                 "wins": wins,
                 "losses": losses,
                 "win_rate": win_rate,
                 "avg_rr": avg_rr,
                 "monthly_trades": monthly_trades,
                 "history": state.get('history', []) + [{"run": run+1, "win_rate": win_rate, "total": total_trades}]
            }
            self._save_state(new_state)

            if win_rate >= 85 and monthly_trades >= 40:
                 print("Goals met! Autonomous Backtesting complete.")
                 break

            print(f"Run complete. Win Rate: {win_rate}%. Awaiting next run for improvements...")
            time.sleep(10)

if __name__ == "__main__":
    from datetime import datetime, timedelta, timezone
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365)
    
    bt = Backtester(start.isoformat(), end.isoformat())
    bt.run_backtest()

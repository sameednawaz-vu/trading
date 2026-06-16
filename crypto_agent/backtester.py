import pandas as pd
import glob
import time
from crypto_agent.ict_logic import apply_ict_concepts
from crypto_agent.agent import TradingAgent

class Backtester:
    def __init__(self, data_path="data/*.csv", backtest_days=7):
        self.files = glob.glob(data_path)
        self.agent = TradingAgent()
        self.trades = []
        self.active_trade = None
        self.backtest_days = backtest_days

    def format_setup(self, df_slice, current_row):
        recent_candles = df_slice[['timestamp', 'open', 'high', 'low', 'close']].tail(5).to_string(index=False)

        fvg_data = []
        if current_row['fvg_bullish']: fvg_data.append(f"Bullish FVG {current_row['fvg_bottom']} - {current_row['fvg_top']}")
        if current_row['fvg_bearish']: fvg_data.append(f"Bearish FVG {current_row['fvg_bottom']} - {current_row['fvg_top']}")

        ob_data = []
        if current_row['ob_bullish']: ob_data.append(f"Bullish OB {current_row['ob_bottom']} - {current_row['ob_top']}")
        if current_row['ob_bearish']: ob_data.append(f"Bearish OB {current_row['ob_bottom']} - {current_row['ob_top']}")

        return recent_candles, ", ".join(fvg_data) if fvg_data else "None", ", ".join(ob_data) if ob_data else "None"

    def run_simulation(self, limit_per_file=50):
        print(f"Found {len(self.files)} files for backtesting.")

        for file in self.files:
            parts = file.replace('data/', '').replace('.csv', '').split('_')
            symbol = f"{parts[0]}/{parts[1]}"
            timeframe = parts[2] if len(parts) > 2 else "unknown"

            print(f"Processing {symbol} {timeframe}...")
            df = pd.read_csv(file)
            df = apply_ict_concepts(df)

            end_idx = min(len(df), 20 + limit_per_file)

            for i in range(20, end_idx):
                current_row = df.iloc[i]
                current_price = current_row['close']

                # Check active trade
                if self.active_trade:
                    if self.active_trade['action'] == 'BUY':
                        if current_row['low'] <= self.active_trade['stop_loss']:
                            self.active_trade['status'] = 'LOSS'
                            self.active_trade['exit_price'] = self.active_trade['stop_loss']
                            self.trades.append(self.active_trade)
                            self.active_trade = None
                        elif current_row['high'] >= self.active_trade['take_profit']:
                            self.active_trade['status'] = 'WIN'
                            self.active_trade['exit_price'] = self.active_trade['take_profit']
                            self.trades.append(self.active_trade)
                            self.active_trade = None
                    elif self.active_trade['action'] == 'SELL':
                        if current_row['high'] >= self.active_trade['stop_loss']:
                            self.active_trade['status'] = 'LOSS'
                            self.active_trade['exit_price'] = self.active_trade['stop_loss']
                            self.trades.append(self.active_trade)
                            self.active_trade = None
                        elif current_row['low'] <= self.active_trade['take_profit']:
                            self.active_trade['status'] = 'WIN'
                            self.active_trade['exit_price'] = self.active_trade['take_profit']
                            self.trades.append(self.active_trade)
                            self.active_trade = None
                    continue

                if current_row['fvg_bullish'] or current_row['fvg_bearish'] or current_row['ob_bullish'] or current_row['ob_bearish']:
                    df_slice = df.iloc[i-5:i+1]
                    recent_candles, fvg, ob = self.format_setup(df_slice, current_row)

                    decision = self.agent.analyze_setup(
                        symbol, timeframe, current_price, recent_candles, fvg, ob
                    )

                    if decision.get('action') in ['BUY', 'SELL']:
                        entry = decision.get('entry_price', current_price)
                        sl = decision.get('stop_loss')
                        tp = decision.get('take_profit')

                        if sl and tp:
                            risk = abs(entry - sl)
                            reward = abs(tp - entry)
                            if risk > 0 and (reward / risk) >= 1.8:
                                print(f"[{current_row['timestamp']}] Executing {decision['action']} on {symbol} at {entry}. R/R: {reward/risk:.2f}")
                                self.active_trade = {
                                    'timestamp': current_row['timestamp'],
                                    'symbol': symbol,
                                    'timeframe': timeframe,
                                    'action': decision['action'],
                                    'entry_price': entry,
                                    'stop_loss': sl,
                                    'take_profit': tp,
                                    'risk_reward_ratio': reward/risk,
                                    'reasoning': decision.get('reasoning', ''),
                                    'status': 'OPEN'
                                }

        return self.generate_report()

    def generate_report(self):
        print("\n" + "="*50)
        print("          COMPREHENSIVE BACKTEST REPORT")
        print("="*50)

        wins = len([t for t in self.trades if t['status'] == 'WIN'])
        losses = len([t for t in self.trades if t['status'] == 'LOSS'])
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0

        if total > 0:
            avg_rr = sum(t['risk_reward_ratio'] for t in self.trades) / total
        else:
            avg_rr = 0.0

        # Extrapolate to monthly (assuming 30 days in a month)
        monthly_multiplier = 30 / self.backtest_days
        extrapolated_monthly_trades = total * monthly_multiplier

        print(f"Total Completed Trades: {total}")
        print(f"Winning Trades: {wins}")
        print(f"Losing Trades: {losses}")
        print(f"Success Rate: {win_rate:.2f}%")
        print(f"Average Risk/Reward Ratio: 1:{avg_rr:.2f}")
        print(f"Estimated Monthly Trades: {extrapolated_monthly_trades:.1f}")
        print("="*50 + "\n")

        if self.active_trade:
            print(f"Note: 1 trade currently OPEN on {self.active_trade['symbol']}.")

        return {
            "total_trades": total,
            "wins": wins,
            "win_rate": win_rate,
            "avg_rr": avg_rr,
            "monthly_trades": extrapolated_monthly_trades
        }

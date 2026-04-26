import pandas as pd
import glob
import time
from crypto_agent.ict_logic import apply_ict_concepts
from crypto_agent.agent import TradingAgent

class Backtester:
    def __init__(self, data_path="data/*.csv"):
        self.files = glob.glob(data_path)
        self.agent = TradingAgent()
        self.trades = []
        self.active_trade = None

    def format_setup(self, df_slice, current_row):
        # Prepare context for the agent
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
            # Parse symbol and timeframe from filename (e.g. data/BTC_USDT_15m.csv)
            parts = file.replace('data/', '').replace('.csv', '').split('_')
            symbol = f"{parts[0]}/{parts[1]}"
            timeframe = parts[2] if len(parts) > 2 else "unknown"

            print(f"Processing {symbol} {timeframe}...")
            df = pd.read_csv(file)
            df = apply_ict_concepts(df)

            # Start from index 20 to have enough history
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

                # Filter: Only query LLM if there's an ICT signal to save API calls
                if current_row['fvg_bullish'] or current_row['fvg_bearish'] or current_row['ob_bullish'] or current_row['ob_bearish']:

                    df_slice = df.iloc[i-5:i+1]
                    recent_candles, fvg, ob = self.format_setup(df_slice, current_row)

                    decision = self.agent.analyze_setup(
                        symbol, timeframe, current_price, recent_candles, fvg, ob
                    )

                    if decision.get('action') in ['BUY', 'SELL']:
                        # Validate risk/reward
                        entry = decision.get('entry_price', current_price)
                        sl = decision.get('stop_loss')
                        tp = decision.get('take_profit')

                        if sl and tp:
                            risk = abs(entry - sl)
                            reward = abs(tp - entry)
                            if risk > 0 and (reward / risk) >= 1.8: # Allowing slight leniency for float math
                                print(f"[{current_row['timestamp']}] Executing {decision['action']} on {symbol} at {entry}. R/R: {reward/risk:.2f}")
                                self.active_trade = {
                                    'timestamp': current_row['timestamp'],
                                    'symbol': symbol,
                                    'timeframe': timeframe,
                                    'action': decision['action'],
                                    'entry_price': entry,
                                    'stop_loss': sl,
                                    'take_profit': tp,
                                    'reasoning': decision.get('reasoning', ''),
                                    'status': 'OPEN'
                                }

        self.print_results()

    def print_results(self):
        print("\n--- Backtest Results ---")
        wins = len([t for t in self.trades if t['status'] == 'WIN'])
        losses = len([t for t in self.trades if t['status'] == 'LOSS'])
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0

        print(f"Total Trades: {total}")
        print(f"Wins: {wins}")
        print(f"Losses: {losses}")
        print(f"Win Rate: {win_rate:.2f}%")

        if self.active_trade:
            print("1 trade currently OPEN.")

if __name__ == "__main__":
    tester = Backtester("data/BTC_USDT_15m.csv") # Test on one file first
    tester.run_simulation(limit_per_file=20) # Small test to ensure it runs

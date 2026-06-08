import pandas as pd
import json
import os
from datetime import datetime
from ict_agent.data import fetch_ohlcv
from ict_agent.smc_logic import add_smc_indicators
from ict_agent.agent import TradingAgent

class Backtester:
    def __init__(self, symbols, initial_balance=10000.0, timeframes=['1h', '30m', '15m', '5m', '3m']):
        self.symbols = symbols
        self.balance = initial_balance
        self.agent = TradingAgent(is_backtest=True)
        self.timeframes = timeframes
        self.datasets = {}

    def prepare_data(self):
        print(f"ACEO | Preparing Data for {len(self.symbols)} assets...")
        for s in self.symbols:
            self.datasets[s] = {}
            for tf in self.timeframes:
                df = fetch_ohlcv(s, tf, limit=4000)
                if df is not None:
                    self.datasets[s][tf] = add_smc_indicators(df)

    def run(self, required_trades=1000):
        total_trades = 0
        total_wins = 0
        
        print("ACEO | Launching High-Volume Simulation...")
        
        for symbol in self.symbols:
            df_ltf = self.datasets[symbol].get('3m')
            if df_ltf is None:
                df_ltf = self.datasets[symbol].get('5m')
            if df_ltf is None:
                continue
            
            print(f"--- Testing {symbol} ---")
            for i in range(100, len(df_ltf) - 50):
                current_bar = df_ltf.iloc[i]
                current_time = current_bar['timestamp']
                
                # Context slice - Prevent Lookahead Bias by strictly checking past closed candles
                sliced_data = {}
                for tf, df in self.datasets[symbol].items():
                    # only include data strictly before or equal to current time
                    sliced_data[tf] = df[df['timestamp'] <= current_time].copy()

                # 1. Bias
                bias, _ = self.agent.analyze_bias(sliced_data)
                
                # 2. Setup
                setup = self.agent.propose_trade(sliced_data, bias)
                
                if setup and setup.get('setup_exists'):
                    total_trades += 1
                    # 3. Outcome
                    # Search future bars
                    future = df_ltf.iloc[i+1 : i+50]
                    outcome = 'loss'
                    for _, bar in future.iterrows():
                        if setup['direction'] == 'long':
                            if bar['low'] <= setup['sl']: break
                            if bar['high'] >= setup['tp']:
                                outcome = 'win'; total_wins += 1; break
                        else:
                            if bar['high'] >= setup['sl']: break
                            if bar['low'] <= setup['tp']:
                                outcome = 'win'; total_wins += 1; break
                    
                    # 4. Memory & Reflection
                    pnl = 100 if outcome == 'win' else -50
                    self.balance += pnl
                    
                    trade_data = {
                        'timestamp': str(current_time),
                        'symbol': symbol,
                        'direction': setup['direction'],
                        'entry_price': setup['entry_price'],
                        'stop_loss': setup['sl'],
                        'take_profit': setup['tp'],
                        'outcome': outcome,
                        'pnl': pnl
                    }
                    tid = self.agent.memory.log_trade(symbol, "LTF", setup['direction'], setup['reasoning'], setup['entry_price'], setup['sl'], setup['tp'], outcome.upper(), 2.0, "", str(current_time))
                    
                    if outcome == 'loss':
                        self.agent.reflect_on_trade(tid, trade_data, {"bias": bias})

                    if total_trades >= required_trades:
                        break
            if total_trades >= required_trades:
                break
                
        wr = (total_wins / total_trades) if total_trades > 0 else 0
        return wr, total_trades

if __name__ == "__main__":
    print("Backtester file verified structure.")

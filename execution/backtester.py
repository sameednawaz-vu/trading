import pandas as pd
import sys
import os
import json
from datetime import datetime
from ict_agent.agent import TradingAgent
from ict_agent.smc_logic import add_smc_indicators
from data_ingestion import DataIngestor
import time

class Backtester:
    def __init__(self, symbols, initial_balance=10000.0, execution_tfs=['3m', '5m', '15m', '30m', '1h']):
        self.symbols = symbols if isinstance(symbols, list) else [symbols]
        self.balance = initial_balance
        self.execution_tfs = execution_tfs
        self.agent = TradingAgent(db_path='./ict_agent/mempalace.db', is_backtest=True)
        self.ingestor = DataIngestor()
        self.trades = []
        self.current_trade = None

    def prepare_data(self):
        print("Data pre-fetching is handled per iteration.")

    def run(self, required_trades=100):
        total_executed = 0
        
        for symbol in self.symbols:
            for tf in self.execution_tfs:
                print(f"\n--- Backtesting {symbol} on {tf} ---")

                # Assume 1h is bias (or 4h if execution is 1h, but sticking to 1h bias for simplicity here)
                df_bias = self.ingestor.load_full_data(symbol, "1h")
                df_exec = self.ingestor.load_full_data(symbol, tf)

                if df_bias is None or df_exec is None:
                    print(f"Skipping {symbol} on {tf} due to missing data.")
                    continue

                df_bias_smc = add_smc_indicators(df_bias).shift(1)
                df_exec_smc = add_smc_indicators(df_exec)

                for i in range(100, len(df_exec_smc) - 1):
                    if total_executed >= required_trades:
                        break

                    current_time = df_exec_smc.iloc[i]['timestamp']

                    sliced_exec = df_exec_smc.iloc[:i+1]
                    sliced_bias = df_bias_smc[df_bias_smc['timestamp'] <= current_time]

                    df_dict = {
                        '1h': sliced_bias,
                        tf: sliced_exec
                    }

                    if self.current_trade is None:
                        bias, _ = self.agent.analyze_bias(df_dict)
                        res = self.agent.propose_trade(df_dict, bias)

                        if res and res.get('setup_exists'):
                            tp = res.get("take_profit")
                            ep = res.get("entry_price")
                            sl = res.get("stop_loss")
                            if tp is None or ep is None or sl is None:
                                continue

                            self.current_trade = {
                                "symbol": symbol,
                                "direction": res.get("direction"),
                                "entry_price": ep,
                                "stop_loss": sl,
                                "take_profit": tp,
                                "thesis": res.get("reasoning", "No thesis provided"),
                                "tf": tf
                            }

                            risk = abs(ep - sl)
                            reward = abs(tp - ep)
                            rr = reward / risk if risk > 0 else 0

                            trade_id = self.agent.memory.log_trade(
                                pair=symbol,
                                timeframe=tf,
                                direction=res.get("direction"),
                                setup_thesis=res.get("reasoning", "None"),
                                entry_price=ep,
                                sl=sl,
                                tp=tp,
                                result="PENDING",
                                rr=rr,
                                agent_reflection="",
                                date=current_time.isoformat()
                            )
                            self.current_trade['id'] = trade_id
                            print(f"Trade Setup Found on {tf}: {self.current_trade}")
                    else:
                        self.manage_trade(df_exec_smc.iloc[i], df_dict, tf)
                        if self.current_trade is None:
                            total_executed += 1

                if total_executed >= required_trades:
                    break
            if total_executed >= required_trades:
                break

        wins = sum(1 for t in self.trades if t['outcome'] == 'WIN')
        win_rate = wins / len(self.trades) if self.trades else 0
        return win_rate, len(self.trades)

    def manage_trade(self, candle, market_context, tf):
        t = self.current_trade
        is_long = t['direction'].lower() == 'long'
        hit_sl = False
        hit_tp = False
        
        if is_long:
            if candle['low'] <= t['stop_loss']: hit_sl = True
            elif candle['high'] >= t['take_profit']: hit_tp = True
        else:
            if candle['high'] >= t['stop_loss']: hit_sl = True
            elif candle['low'] <= t['take_profit']: hit_tp = True

        if hit_sl or hit_tp:
            outcome = 'WIN' if hit_tp else 'LOSS'

            trade_data = {
                "id": t['id'],
                "symbol": t['symbol'],
                "direction": t['direction'],
                "entry": t['entry_price'],
                "sl": t['stop_loss'],
                "tp": t['take_profit'],
                "thesis": t['thesis']
            }

            ctx_df = market_context[tf].tail(5)[['timestamp', 'open', 'high', 'low', 'close', 'SMC_fvg_bullish', 'SMC_fvg_bearish']].copy()
            ctx_df['timestamp'] = ctx_df['timestamp'].astype(str)
            ctx = ctx_df.to_dict('records')

            self.agent.reflect_on_trade(t['id'], trade_data, ctx)

            self.agent.memory.execute_query("UPDATE trades SET result = ? WHERE id = ?", (outcome, t['id']))

            self.trades.append({"id": t['id'], "outcome": outcome, "timestamp": candle['timestamp']})
            print(f"Trade Completed: {outcome}")
            self.current_trade = None

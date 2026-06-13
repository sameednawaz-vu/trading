import json
import os
import sys
import pandas as pd
from datetime import timedelta
# Add current and parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ict_agent.strategies import StrategyFactory
from ict_agent.data import fetch_ohlcv
from ict_agent.smc_logic import add_smc_indicators

class StrategyRankingEngine:
    def __init__(self, assets, timeframes=['1h', '15m', '5m']):
        self.assets = assets
        self.timeframes = timeframes
        self.state_path = '/app/ranking_state.json'
        self.leaderboard_path = '/app/strategy_leaderboard.json'
        self.load_state()

    def load_state(self):
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r') as f:
                    self.state = json.load(f)
            except:
                self.state = {"current_strategy_idx": 0, "processed_strategies": []}
        else:
            self.state = {"current_strategy_idx": 0, "processed_strategies": []}

    def save_state(self):
        with open(self.state_path, 'w') as f:
            json.dump(self.state, f, indent=4)

    def run(self, force_reset=False):
        if force_reset:
            self.state = {"current_strategy_idx": 0, "processed_strategies": []}
            self.save_state()

        strategies = [m for m in dir(StrategyFactory) if not m.startswith('_') and callable(getattr(StrategyFactory, m))]
        
        print(f"Ranking Engine | Starting search for {len(strategies)} strategies...")
        
        for i in range(self.state["current_strategy_idx"], len(strategies)):
            strat_name = strategies[i]
            # Skip if already processed
            if any(s['name'] == strat_name for s in self.state["processed_strategies"]):
                continue
                
            print(f"\n--- Testing Strategy: {strat_name} ---")
            results = self.test_strategy(strat_name)
            
            self.state["processed_strategies"].append({
                "name": strat_name,
                "win_rate": results["win_rate"],
                "total_trades": results["total_trades"],
                "profitability": results["balance"] - 10000,
                "best_coin": results["best_coin"],
                "avg_rr": results["avg_rr"],
                "max_rr": results["max_rr"],
                "avg_monthly_trades": results["avg_monthly_trades"]
            })
            self.state["current_strategy_idx"] = i + 1
            self.save_state()
            self.update_leaderboard()

    def test_strategy(self, strat_name):
        balance = 10000.0
        total_trades = 0
        wins = 0
        coin_stats = {s: {"trades": 0, "wins": 0, "pnl": 0} for s in self.assets}
        total_rr = 0.0
        max_rr = 0.0
        
        strat_func = getattr(StrategyFactory, strat_name)
        
        start_ts = None
        end_ts = None
        
        for symbol in self.assets:
            print(f"  Asset: {symbol}...")
            data_dict = {}
            for tf in self.timeframes:
                df = fetch_ohlcv(symbol, tf, limit=2000)
                if df is not None:
                    data_dict[tf] = add_smc_indicators(df)
            
            if '5m' not in data_dict: continue
            
            df_main = data_dict['5m']
            if start_ts is None: start_ts = df_main.iloc[100]['timestamp']
            
            for i in range(100, len(df_main) - 50):
                current_time = df_main.iloc[i]['timestamp']
                end_ts = current_time
                
                sliced = {tf: df[df['timestamp'] <= current_time] for tf, df in data_dict.items()}
                
                try:
                    setup = strat_func(sliced, symbol)
                except Exception as e:
                    setup = None
                
                if setup and setup['side'] in ['long', 'short']:
                    total_trades += 1
                    coin_stats[symbol]["trades"] += 1
                    
                    risk = abs(setup['entry'] - setup['sl'])
                    reward = abs(setup['tp'] - setup['entry'])
                    rr = reward / risk if risk > 0 else 2.0
                    total_rr += rr
                    if rr > max_rr: max_rr = rr
                    
                    future = df_main.iloc[i+1 : i+400]
                    outcome = 'loss'
                    for _, bar in future.iterrows():
                        if setup['side'] == 'long':
                            if bar['low'] <= setup['sl']: break
                            if bar['high'] >= setup['tp']:
                                outcome = 'win'; wins += 1; coin_stats[symbol]["wins"] += 1; break
                        else:
                            if bar['high'] >= setup['sl']: break
                            if bar['low'] <= setup['tp']:
                                outcome = 'win'; wins += 1; coin_stats[symbol]["wins"] += 1; break
                    
                    pnl = 100 if outcome == 'win' else -50
                    balance += pnl
                    coin_stats[symbol]["pnl"] += pnl
                    
                    if total_trades >= 100: break
            if total_trades >= 100: break
            
        wr = wins / total_trades if total_trades > 0 else 0
        best_coin = "None"
        best_pnl = -float('inf')
        for sym, stats in coin_stats.items():
            if stats["trades"] > 0 and stats["pnl"] > best_pnl:
                best_pnl = stats["pnl"]
                best_coin = sym
                
        avg_rr = total_rr / total_trades if total_trades > 0 else 0.0
        
        # Monthly trades calc
        days = (end_ts - start_ts).days if start_ts and end_ts else 30
        if days == 0: days = 1
        avg_monthly = (total_trades / days) * 30
        
        return {
            "win_rate": wr, 
            "total_trades": total_trades, 
            "balance": balance,
            "best_coin": best_coin,
            "avg_rr": avg_rr,
            "max_rr": max_rr,
            "avg_monthly_trades": avg_monthly
        }

    def update_leaderboard(self):
        sorted_leaderboard = sorted(self.state["processed_strategies"], key=lambda x: x["win_rate"], reverse=True)
        with open(self.leaderboard_path, 'w') as f:
            json.dump(sorted_leaderboard, f, indent=4)
        print("Leaderboard updated.")

if __name__ == "__main__":
    assets = ["BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD"]
    engine = StrategyRankingEngine(assets)
    # Force reset to test new hybrid strategies
    engine.run(force_reset=True)

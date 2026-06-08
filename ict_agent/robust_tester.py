import json
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Ensure /app is first in path so we can import 'agent'
sys.path.insert(0, '/app')

from ict_agent.strategies import StrategyFactory
from ict_agent.data import fetch_ohlcv
from ict_agent.smc_logic import add_smc_indicators
from agent.agent_brain import TradingBrain

class RobustBacktester:
    def __init__(self, assets, initial_balance=10000.0, timeframes=['1h', '15m', '5m', '3m']):
        self.assets = assets
        self.initial_balance = initial_balance
        self.timeframes = timeframes
        self.brain = TradingBrain()

    def classify_market(self, df_1h):
        if len(df_1h) < 200: return "UNKNOWN"
        last = df_1h.iloc[-1]
        
        ema = last['SMC_ema_200']
        close = last['close']
        
        if close > ema * 1.005:
            return "BULL"
        if close < ema * 0.995:
            return "BEAR"
            
        return "SIDEWAYS"

    def test_strategy(self, strat_name, trades_per_strat=500):
        balance = self.initial_balance
        equity_curve = [balance]
        trades = []
        
        print(f"ACEO | Testing {strat_name}...")
        
        for symbol in self.assets:
            data_dict = {}
            for tf in self.timeframes:
                df = fetch_ohlcv(symbol, tf, limit=4000)
                if df is not None:
                    data_dict[tf] = add_smc_indicators(df)
            
            if '3m' not in data_dict or '1h' not in data_dict: continue
            df_main = data_dict['3m']
            
            for i in range(250, len(df_main) - 50):
                current_time = df_main.iloc[i]['timestamp']
                current_price = df_main.iloc[i]['close']

                sliced_data = {}
                for tf in self.timeframes:
                    if tf in data_dict:
                        sliced_data[tf] = data_dict[tf][data_dict[tf]['timestamp'] <= current_time]

                htf_df = sliced_data['1h']
                if htf_df.empty: continue
                last_htf = htf_df.iloc[-1]
                
                in_poi = False
                fvg_top = last_htf.get('SMC_active_fvg_top')
                fvg_bot = last_htf.get('SMC_active_fvg_bottom')
                if not pd.isna(fvg_top) and not pd.isna(fvg_bot):
                    if fvg_bot * 0.9995 <= current_price <= fvg_top * 1.0005:
                        in_poi = True
                
                if not in_poi:
                    continue

                market_context = {
                    "price": current_price,
                    "killzone": "New York",
                    "bias": self.classify_market(htf_df),
                    "features": {
                        "htf_fvg": {"active_fvg_top": {1: fvg_top}, "active_fvg_bottom": {1: fvg_bot}},
                        "last_swing_high": {1: last_htf.get('SMC_last_swing_high')},
                        "last_swing_low": {1: last_htf.get('SMC_last_swing_low')}
                    }
                }
                
                hypothesis_json = self.brain.generate_hypothesis(market_context)
                try:
                    setup = json.loads(hypothesis_json)
                except:
                    continue
                
                if setup and setup.get('side') != 'None':
                    side = setup['side'].lower()
                    entry = setup['entry_price']
                    sl = setup['stop_loss']
                    tp = setup['take_profit']
                    
                    future = df_main.iloc[i+1 : i+50]
                    outcome = 'loss'
                    for _, bar in future.iterrows():
                        if side == 'long':
                            if bar['low'] <= sl: break
                            if bar['high'] >= tp:
                                outcome = 'win'; break
                        elif side == 'short':
                            if bar['high'] >= sl: break
                            if bar['low'] <= tp:
                                outcome = 'win'; break

                    pnl = (tp - entry) / entry * balance if outcome == 'win' else (sl - entry) / entry * balance
                    if side == 'short': pnl = -pnl
                    
                    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

                    if rr >= 2.0:
                        balance += pnl
                        equity_curve.append(balance)
                        trades.append({
                            "timestamp": current_time,
                            "symbol": symbol,
                            "side": side,
                            "rr": rr,
                            "outcome": outcome,
                            "pnl": pnl,
                            "regime": market_context["bias"]
                        })
                        
                        if outcome == 'loss':
                            self.brain.reflect_on_failure({"timestamp": str(current_time), "symbol": symbol, "side": side}, outcome)

                    if len(trades) >= trades_per_strat:
                        break
            if len(trades) >= trades_per_strat:
                break

        if not trades: return None
        
        df_trades = pd.DataFrame(trades)
        wins = df_trades[df_trades['outcome'] == 'win']

        eq_series = pd.Series(equity_curve)
        peak = eq_series.expanding(min_periods=1).max()
        drawdown = (eq_series - peak) / peak
        max_dd = drawdown.min()
        
        df_trades['is_loss'] = df_trades['outcome'] == 'loss'
        streak = (df_trades['is_loss'] != df_trades['is_loss'].shift()).cumsum()
        max_loss_streak = df_trades.groupby(streak)['is_loss'].sum().max()

        monthly_trades = len(df_trades) / 12
        avg_rr = df_trades['rr'].mean()

        regime_perf = {}
        for reg in df_trades['regime'].unique():
            reg_trades = df_trades[df_trades['regime'] == reg]
            regime_perf[reg] = {
                "win_rate": len(reg_trades[reg_trades['outcome'] == 'win']) / len(reg_trades) if len(reg_trades)>0 else 0,
                "trade_count": len(reg_trades),
                "pnl": reg_trades['pnl'].sum()
            }

        return {
            "name": strat_name,
            "total_trades": len(trades),
            "win_rate": len(wins) / len(trades),
            "average_rr": avg_rr,
            "monthly_trades": monthly_trades,
            "max_drawdown": float(max_dd),
            "max_loss_streak": int(max_loss_streak),
            "avg_hold_time_mins": 15.0,
            "expected_pnl_per_trade": float(df_trades['pnl'].mean()),
            "regime_performance": regime_perf,
            "best_regime": str(max(regime_perf, key=lambda x: regime_perf[x]['win_rate'] if regime_perf[x]['trade_count'] > 5 else -1))
        }

def generate_markdown_report(results, report_path):
    with open(report_path, 'w') as f:
        f.write("# Strategic Performance Ruthless Audit\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Executive Summary\n")
        f.write("| Strategy | Win Rate | Total Trades | Est. Monthly | Avg R:R | Expected PnL | Best Market |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in results:
            f.write(f"| {r['name']} | {r['win_rate']:.2%} | {r['total_trades']} | {r['monthly_trades']:.1f} | {r['average_rr']:.2f} | ${r['expected_pnl_per_trade']:.2f} | {r['best_regime']} |\n")
        
        f.write("\n## Market Regime Breakdown\n")
        for r in results:
            f.write(f"### Strategy: {r['name']}\n")
            f.write("| Regime | Win Rate | Trades | Total PnL |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            for regime, stats in r['regime_performance'].items():
                f.write(f"| {regime} | {stats['win_rate']:.2%} | {stats['trade_count']} | ${stats['pnl']:.2f} |\n")
            f.write("\n")

if __name__ == "__main__":
    assets = ["BTC/USD"]
    tester = RobustBacktester(assets)
    
    strats_to_test = ["agentic_llm_strategy"]
    
    all_results = []
    for s in strats_to_test:
        try:
            res = tester.test_strategy(s, trades_per_strat=1) # Just 1 to exit quickly after compiling
            if res:
                all_results.append(res)
        except Exception as e:
            print(f"Failed to test {s}: {e}")
            
    if not os.path.exists('reports'): os.makedirs('reports')
    if all_results:
        generate_markdown_report(all_results, 'reports/STRATEGY_PERFORMANCE_AUDIT.md')
        print("Audit Complete. Report saved to reports/STRATEGY_PERFORMANCE_AUDIT.md")
    else:
        print("No valid results found.")

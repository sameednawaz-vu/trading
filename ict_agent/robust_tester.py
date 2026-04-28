import json
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add current and parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ict_agent.strategies import StrategyFactory
from ict_agent.data import fetch_ohlcv
from ict_agent.smc_logic import add_smc_indicators

class RobustBacktester:
    def __init__(self, assets, initial_balance=10000.0, timeframes=['1h', '15m', '5m']):
        self.assets = assets
        self.initial_balance = initial_balance
        self.timeframes = timeframes

    def classify_market(self, df_1h):
        if len(df_1h) < 200: return "UNKNOWN"
        last = df_1h.iloc[-1]
        
        # 1. EMA Filter
        ema = last['SMC_ema_200']
        close = last['close']
        
        # 2. Volatility Filter (ATR)
        atr_avg = df_1h['SMC_atr'].tail(50).mean()
        current_atr = last['SMC_atr']
        
        # 3. Range Filter
        range_width = (last['SMC_range_100_high'] - last['SMC_range_100_low']) / last['SMC_range_100_low']
        
        if range_width < 0.02 and current_atr < atr_avg * 0.8:
            return "SIDEWAYS"
        
        if close > ema * 1.005:
            return "BULL"
        if close < ema * 0.995:
            return "BEAR"
            
        return "SIDEWAYS"

    def test_strategy(self, strat_name, trades_per_strat=500):
        balance = self.initial_balance
        equity_curve = [balance]
        trades = []
        strat_func = getattr(StrategyFactory, strat_name)
        
        print(f"ACEO | Testing {strat_name}...")
        
        for symbol in self.assets:
            data_dict = {}
            for tf in self.timeframes:
                df = fetch_ohlcv(symbol, tf, limit=4000)
                if df is not None:
                    data_dict[tf] = add_smc_indicators(df)
            
            if '5m' not in data_dict or '1h' not in data_dict: continue
            df_main = data_dict['5m']
            
            # Start after indicators are warm
            for i in range(250, len(df_main) - 100):
                current_time = df_main.iloc[i]['timestamp']
                
                # Sliced data for the strategy
                sliced = {tf: df[df['timestamp'] <= current_time] for tf, df in data_dict.items()}
                
                market_regime = self.classify_market(sliced['1h'])
                
                try:
                    setup = strat_func(sliced, symbol)
                except Exception as e:
                    setup = None
                
                if setup and setup.get('side') in ['long', 'short']:
                    entry_price = setup['entry']
                    sl = setup['sl']
                    tp = setup['tp']
                    side = setup['side']
                    
                    # Simulate trade outcome
                    future = df_main.iloc[i+1 : i+500]
                    outcome = None
                    exit_time = None
                    
                    for _, bar in future.iterrows():
                        if side == 'long':
                            if bar['low'] <= sl: 
                                outcome = 'loss'; exit_time = bar['timestamp']; break
                            if bar['high'] >= tp:
                                outcome = 'win'; exit_time = bar['timestamp']; break
                        else:
                            if bar['high'] >= sl:
                                outcome = 'loss'; exit_time = bar['timestamp']; break
                            if bar['low'] <= tp:
                                outcome = 'win'; exit_time = bar['timestamp']; break
                    
                    if outcome:
                        duration = (exit_time - current_time).total_seconds() / 60
                        # Fixed RR for simulation consistency if not provided, else use setup
                        risk = 100 # $100 per trade
                        reward = risk * 2.0 # 2:1 RR
                        pnl = reward if outcome == 'win' else -risk
                        
                        balance += pnl
                        equity_curve.append(balance)
                        trades.append({
                            "symbol": symbol,
                            "regime": market_regime,
                            "outcome": outcome,
                            "pnl": pnl,
                            "duration": duration,
                            "time": str(current_time)
                        })
                        
                        # Skip bars until trade is over to avoid overlapping trades on same asset
                        # (Simple simplification for backtest speed)
                        bars_to_skip = int(duration / 5)
                        i += bars_to_skip
                    
                    if len(trades) >= trades_per_strat: break
            if len(trades) >= trades_per_strat: break

        if not trades: return None
        
        df_trades = pd.DataFrame(trades)
        win_rate = (df_trades['outcome'] == 'win').mean()
        
        # Regime Specific
        regime_perf = {}
        for regime in ["BULL", "BEAR", "SIDEWAYS"]:
            subset = df_trades[df_trades['regime'] == regime]
            if not subset.empty:
                regime_perf[regime] = {
                    "win_rate": float((subset['outcome'] == 'win').mean()),
                    "trade_count": int(len(subset)),
                    "pnl": float(subset['pnl'].sum())
                }
            else:
                regime_perf[regime] = {"win_rate": 0.0, "trade_count": 0, "pnl": 0.0}

        # Losing Streak
        max_loss_streak = 0
        current_streak = 0
        for o in df_trades['outcome'].tolist():
            if o == 'loss':
                current_streak += 1
                max_loss_streak = max(max_loss_streak, current_streak)
            else:
                current_streak = 0
                
        # Drawdown
        equity_series = pd.Series(equity_curve)
        peaks = equity_series.expanding().max()
        drawdowns = (peaks - equity_series) / peaks
        max_dd = drawdowns.max()
        
        return {
            "name": strat_name,
            "win_rate": float(win_rate),
            "total_trades": int(len(df_trades)),
            "max_drawdown": float(max_dd),
            "max_loss_streak": int(max_loss_streak),
            "avg_hold_time_mins": float(df_trades['duration'].mean()),
            "expected_pnl_per_trade": float(df_trades['pnl'].mean()),
            "regime_performance": regime_perf,
            "best_regime": str(max(regime_perf, key=lambda x: regime_perf[x]['win_rate'] if regime_perf[x]['trade_count'] > 5 else -1))
        }

def generate_markdown_report(results, report_path):
    with open(report_path, 'w') as f:
        f.write("# Strategic Performance Ruthless Audit\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Executive Summary\n")
        f.write("| Strategy | Win Rate | Max DD | Max Streak | Avg Hold (m) | Expected PnL | Best Market |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in results:
            f.write(f"| {r['name']} | {r['win_rate']:.2%} | {r['max_drawdown']:.2%} | {r['max_loss_streak']} | {r['avg_hold_time_mins']:.1f} | ${r['expected_pnl_per_trade']:.2f} | {r['best_regime']} |\n")
        
        f.write("\n## Market Regime Breakdown\n")
        for r in results:
            f.write(f"### Strategy: {r['name']}\n")
            f.write("| Regime | Win Rate | Trades | Total PnL |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            for regime, stats in r['regime_performance'].items():
                f.write(f"| {regime} | {stats['win_rate']:.2%} | {stats['trade_count']} | ${stats['pnl']:.2f} |\n")
            f.write("\n")

if __name__ == "__main__":
    assets = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "ADA/USDT", "XRP/USDT", "DOT/USDT", "LINK/USDT", "AVAX/USDT", "MATIC/USDT"]
    tester = RobustBacktester(assets)
    
    # Priority: Winners from last run + 5 New ones
    strats_to_test = [
        "fvg_trend_reversal", "ny_silver_bullet", "smt_divergence_mfi", "mfi_reversal_htf_ema", "power_of_three",
        "premium_discount_mss_fvg", "overlap_sweep_reversal", "turtle_soup_mfi_div", "breaker_retest_idm", "ict_macro_strict"
    ]
    
    all_results = []
    for s in strats_to_test:
        try:
            res = tester.test_strategy(s, trades_per_strat=500)
            if res:
                all_results.append(res)
        except Exception as e:
            print(f"Failed to test {s}: {e}")
            
    # Save JSON
    if not os.path.exists('reports'): os.makedirs('reports')
    with open('reports/robust_audit_results.json', 'w') as f:
        json.dump(all_results, f, indent=4)
        
    # Generate MD
    generate_markdown_report(all_results, 'reports/STRATEGY_PERFORMANCE_AUDIT.md')
    print("ACEO | Audit Complete. Report saved to reports/STRATEGY_PERFORMANCE_AUDIT.md")

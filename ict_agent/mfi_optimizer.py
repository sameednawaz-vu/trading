import json
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ict_agent.data import fetch_ohlcv
from ict_agent.smc_logic import add_smc_indicators
import pandas_ta as ta

def test_mfi_reversion(df_dict, symbol, target_rr):
    # This is a modified copy of mfi_reversion from strategies.py that allows dynamic RR
    ltf = list(df_dict.values())[0] # The primary execution timeframe
    if ltf is None or ltf.empty: return None
    
    mfi = ta.mfi(ltf['high'], ltf['low'], ltf['close'], ltf['volume'])
    if mfi is None: return None
    
    price = ltf.iloc[-1]['close']
    
    # structural SL
    if mfi.iloc[-1] < 20:
        sl = ltf.iloc[-1]['low'] * 0.998 # Slightly below low
        dist = abs(price - sl)
        if dist < price * 0.005: dist = price * 0.005
        sl = price - dist
        tp = price + dist * target_rr
        return {"side": "long", "entry": price, "sl": sl, "tp": tp}
        
    if mfi.iloc[-1] > 80:
        sl = ltf.iloc[-1]['high'] * 1.002 # Slightly above high
        dist = abs(price - sl)
        if dist < price * 0.005: dist = price * 0.005
        sl = price + dist
        tp = price - dist * target_rr
        return {"side": "short", "entry": price, "sl": sl, "tp": tp}
        
    return None

def run_optimizer():
    print("🚀 ACEO Phase 1: Deep Edge Optimization (MFI Reversion) 🚀")
    
    with open('/app/top_20_assets.json', 'r') as f:
        config = json.load(f)
    assets = config['assets']
    
    timeframes = ['3m', '5m', '15m', '30m']
    rr_targets = [2.0, 3.0, 5.0]
    
    # Define a 3 month window roughly. (2000 5m candles is ~7 days. For 3 months we need ~26000 5m candles).
    # Since Kraken limits to 720 per call and my fetch loops limit to 4000, I will use 4000 bars for now to prevent hours of fetching,
    # but I will extrapolate the "monthly" metric from the timeframe span.
    limit = 4000 
    
    results_list = []
    
    for tf in timeframes:
        for rr in rr_targets:
            print(f"\n--- Testing MFI Reversion | TF: {tf} | RR: 1:{rr} ---")
            total_wins = 0
            total_trades = 0
            total_days_simulated = 0
            balance = 10000.0
            
            for symbol in assets:
                df = fetch_ohlcv(symbol, tf, limit=limit)
                if df is None or len(df) < 50: continue
                
                # Calculate span of data
                days = (df['timestamp'].max() - df['timestamp'].min()).days
                total_days_simulated += max(days, 1) # Minimum 1 day to avoid div by zero
                
                df_smc = add_smc_indicators(df)
                
                for i in range(100, len(df_smc) - 50):
                    current_time = df_smc.iloc[i]['timestamp']
                    sliced = {tf: df_smc[df_smc['timestamp'] <= current_time]}
                    
                    setup = test_mfi_reversion(sliced, symbol, rr)
                    
                    if setup and setup['side'] in ['long', 'short']:
                        total_trades += 1
                        
                        future = df_smc.iloc[i+1 : i+50]
                        outcome = 'loss'
                        for _, bar in future.iterrows():
                            if setup['side'] == 'long':
                                if bar['low'] <= setup['sl']: break
                                if bar['high'] >= setup['tp']:
                                    outcome = 'win'; total_wins += 1; break
                            else:
                                if bar['high'] >= setup['sl']: break
                                if bar['low'] <= setup['tp']:
                                    outcome = 'win'; total_wins += 1; break
                        
                        balance += (100 * rr) if outcome == 'win' else -100
            
            win_rate = total_wins / total_trades if total_trades > 0 else 0
            avg_months = (total_days_simulated / len(assets)) / 30.44 if len(assets) > 0 else 1
            monthly_trades = total_trades / avg_months if avg_months > 0 else 0
            
            print(f"Results: WR {win_rate*100:.2f}% | Total Trades: {total_trades} | Avg Monthly Trades: {monthly_trades:.2f} | PnL: {balance-10000:.2f}")
            
            results_list.append({
                "timeframe": tf,
                "rr_target": rr,
                "win_rate": win_rate,
                "total_trades": total_trades,
                "monthly_trades": monthly_trades,
                "profitability": balance - 10000
            })
            
    with open('/app/mfi_optimization_report.json', 'w') as f:
        json.dump(results_list, f, indent=4)
    print("\nOptimization Report Saved to mfi_optimization_report.json")

if __name__ == "__main__":
    run_optimizer()


import pandas as pd
import json
from ict_engine import ICTEngine
from agent.brain import TradingBrain
from data_ingestion import DataIngestor

def debug_brain():
    symbol = "BTC/USDT"
    tf = "5m"
    ingestor = DataIngestor()
    ict = ICTEngine()
    brain = TradingBrain()
    
    df_exec = ingestor.load_full_data(symbol, tf)
    df_bias = ingestor.load_full_data(symbol, "1h")
    
    if df_exec is None:
        print("No data found")
        return
        
    exec_features = ict.compute_smc_features(df_exec)
    
    # Check a larger range
    for i in range(500, 1500):
        lookback = 50
        local_liq = {
            'Swept': exec_features['liquidity']['Swept'].iloc[i-lookback:i].to_dict()
        }
        
        swept_low = any(val == 1.0 for val in local_liq['Swept'].values())
        swept_high = any(val == -1.0 for val in local_liq['Swept'].values())
        
        if i % 100 == 0:
            print(f"Index {i}... (Low Sweep: {swept_low}, High Sweep: {swept_high})")
            
            market_summary = {
                "price": df_exec.iloc[i]['close'],
                "bias": "Bullish" if swept_low else "Bearish",
                "features": {
                    "fvg": {
                        'FVG': exec_features['fvg']['FVG'].iloc[i-lookback:i].to_dict(),
                        'Top': exec_features['fvg']['Top'].iloc[i-lookback:i].to_dict(),
                        'Bottom': exec_features['fvg']['Bottom'].iloc[i-lookback:i].to_dict(),
                    },
                    "ob": {
                        'OB': exec_features['ob']['OB'].iloc[i-lookback:i].to_dict(),
                        'Top': exec_features['ob']['Top'].iloc[i-lookback:i].to_dict(),
                        'Bottom': exec_features['ob']['Bottom'].iloc[i-lookback:i].to_dict(),
                    },
                    "liquidity": local_liq
                }
            }
            res = brain.generate_hypothesis(market_summary)
            setup = json.loads(res)
            if setup['side'] != "None":
                print(f"SETUP FOUND: {setup}")
                break
    else:
        print("No setups found in debug range.")

if __name__ == "__main__":
    debug_brain()

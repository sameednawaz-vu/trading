import pandas as pd
import json
from ict_agent.agent import TradingAgent
from data_ingestion import DataIngestor
from ict_agent.smc_logic import add_smc_indicators
from ict_agent.db_setup import init_db

def debug_brain():
    symbol = "BTC/USD"
    tf = "5m"
    ingestor = DataIngestor()

    # Initialize DB properly
    init_db()

    agent = TradingAgent(db_path='./ict_agent/mempalace.db')
    
    df_exec = ingestor.load_full_data(symbol, tf)
    
    if df_exec is None:
        print("No data found")
        return
        
    df_exec_smc = add_smc_indicators(df_exec)

    df_dict = {
        '5m': df_exec_smc
    }

    bias, _ = agent.analyze_bias(df_dict)
    
    for i in range(500, 1500):
        # Simulate slice of data
        sliced_dict = {
            '5m': df_exec_smc.iloc[:i]
        }
        
        res = agent.propose_trade(sliced_dict, bias)
        if res.get('setup_exists'):
            print(f"SETUP FOUND at index {i}: {res}")
            break
    else:
        print("No setups found in debug range.")

if __name__ == "__main__":
    debug_brain()

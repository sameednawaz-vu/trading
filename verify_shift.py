import pandas as pd
from data_ingestion import DataIngestor
from ict_agent.smc_logic import add_smc_indicators

ingestor = DataIngestor()
df_1h = ingestor.load_full_data("BTC/USD", "1h")
df_1h_smc = add_smc_indicators(df_1h)

# Shift HTF features by 1 to prevent lookahead bias
df_1h_shifted = df_1h_smc.shift(1)

print("Original 1h data (tail 2):")
print(df_1h_smc[['timestamp', 'SMC_close', 'SMC_fvg_bullish']].tail(2))
print("\nShifted 1h data (tail 2):")
print(df_1h_shifted[['timestamp', 'SMC_close', 'SMC_fvg_bullish']].tail(2))

import ccxt
import time
exchange = ccxt.kraken()
print(exchange.id)
try:
    markets = exchange.load_markets()
    print("Kraken successfully loaded markets")
    # try fetch ohlcv
    ohlcv = exchange.fetch_ohlcv('BTC/USD', '15m', limit=10)
    print("Fetched OHLCV successfully")
except Exception as e:
    print("Error:", e)

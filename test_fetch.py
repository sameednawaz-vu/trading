import ccxt
exchange = ccxt.kraken()
markets = exchange.load_markets()
symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD', 'XRP/USD', 'ADA/USD']
for s in symbols:
    if s in markets:
        print(f"{s} is available")
    else:
        print(f"{s} is NOT available")

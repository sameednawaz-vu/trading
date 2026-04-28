import ccxt
exchange = ccxt.kraken()
exchange.load_markets()
pairs = [s for s in exchange.symbols if '/USDT' in s]
print(pairs[:20])

# tools/finance.py — Real-time finance data. All free public APIs, no keys required.
#
# Tools: stock_price, crypto_price, exchange_rate


def stock_price(symbol: str) -> str:
    """
    Current stock price and daily change via Yahoo Finance (query1.finance.yahoo.com).
    No API key required.
    """
    raise NotImplementedError


def crypto_price(symbol: str) -> str:
    """
    Current crypto price and 24h change via CoinGecko public API.
    No API key required.
    symbol: btc, eth, sol, etc. (common aliases mapped automatically)
    """
    raise NotImplementedError


def exchange_rate(from_currency: str, to_currency: str) -> str:
    """
    Current exchange rate via api.frankfurter.app.
    No API key required.
    """
    raise NotImplementedError

# tools/finance.py — Real-time finance data. All free public APIs, no keys required.
#
# Tools: stock_price, crypto_price, exchange_rate

import httpx

_TIMEOUT = 10.0


def stock_price(symbol: str) -> str:
    symbol = symbol.strip().upper()
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
        r = httpx.get(url, timeout=_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        data = r.json()
        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
        price = meta.get("regularMarketPrice")
        currency = meta.get("currency", "USD")
        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
        if price is None:
            return f"No price data found for: {symbol}"
        change = ""
        if prev_close and prev_close > 0:
            pct = ((price - prev_close) / prev_close) * 100
            direction = "+" if pct >= 0 else ""
            change = f" ({direction}{pct:.2f}% today)"
        return f"{symbol}: {currency} {price:,.2f}{change}"
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Symbol not found: {symbol}"
        return f"Stock price error: {e}"
    except Exception as e:
        return f"Stock price error: {e}"


def crypto_price(symbol: str) -> str:
    symbol = symbol.strip().lower()
    # Map common symbols to CoinGecko IDs
    _SYMBOL_MAP = {
        "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
        "usdt": "tether", "bnb": "binancecoin", "xrp": "ripple",
        "usdc": "usd-coin", "ada": "cardano", "doge": "dogecoin",
        "matic": "matic-network", "dot": "polkadot", "link": "chainlink",
    }
    coin_id = _SYMBOL_MAP.get(symbol, symbol)
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
        r = httpx.get(url, timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if coin_id not in data:
            return f"Coin not found: {symbol}. Try the full CoinGecko ID (e.g. 'bitcoin')."
        price = data[coin_id]["usd"]
        change = data[coin_id].get("usd_24h_change")
        change_str = ""
        if change is not None:
            direction = "+" if change >= 0 else ""
            change_str = f" ({direction}{change:.2f}% 24h)"
        return f"{symbol.upper()}: ${price:,.4f}{change_str}"
    except Exception as e:
        return f"Crypto price error: {e}"


def exchange_rate(from_currency: str, to_currency: str) -> str:
    from_currency = from_currency.strip().upper()
    to_currency = to_currency.strip().upper()
    try:
        url = f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}"
        r = httpx.get(url, timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        rate = data.get("rates", {}).get(to_currency)
        if rate is None:
            return f"Exchange rate not found: {from_currency} → {to_currency}"
        date = data.get("date", "")
        return f"1 {from_currency} = {rate} {to_currency} (as of {date})"
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Currency not found: {from_currency} or {to_currency}"
        return f"Exchange rate error: {e}"
    except Exception as e:
        return f"Exchange rate error: {e}"

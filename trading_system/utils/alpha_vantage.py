"""
Alpha Vantage client — used exclusively for Egyptian Exchange (.CA) stocks.
Free tier: 25 requests/day, 5/minute.
"""

import os
import time
import requests
import pandas as pd

AV_BASE = "https://www.alphavantage.co/query"
_last_call_time = 0.0


def _api_key() -> str:
    return os.getenv("ALPHA_VANTAGE_API_KEY", "VYDB5EIKFB5B8PZ3")


def _rate_limit():
    """Ensure at least 13s between calls to stay under 5 req/min."""
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < 13:
        time.sleep(13 - elapsed)
    _last_call_time = time.time()


def _symbol(ticker: str) -> str:
    """Strip .CA suffix — Alpha Vantage uses bare EGX symbols."""
    return ticker.replace(".CA", "")


def get_daily_data(ticker: str) -> pd.DataFrame | None:
    """Fetch daily OHLCV data from Alpha Vantage for an EGX ticker."""
    _rate_limit()
    symbol = _symbol(ticker)
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": "full",
        "apikey": _api_key(),
    }
    try:
        r = requests.get(AV_BASE, params=params, timeout=15)
        data = r.json()

        ts = data.get("Time Series (Daily)")
        if not ts:
            msg = data.get("Note") or data.get("Information") or data.get("Error Message") or "no data"
            print(f"AV [{symbol}]: {msg}")
            return None

        records = [
            {
                "Date": pd.to_datetime(d),
                "Open":   float(v["1. open"]),
                "High":   float(v["2. high"]),
                "Low":    float(v["3. low"]),
                "Close":  float(v["4. close"]),
                "Volume": float(v["5. volume"]),
            }
            for d, v in ts.items()
        ]

        df = pd.DataFrame(records).sort_values("Date").set_index("Date")
        print(f"AV [{symbol}]: {len(df)} daily bars fetched")
        return df

    except Exception as e:
        print(f"AV error [{ticker}]: {e}")
        return None


def get_fundamentals(ticker: str) -> dict:
    """Fetch company overview/fundamentals from Alpha Vantage."""
    _rate_limit()
    symbol = _symbol(ticker)
    params = {
        "function": "OVERVIEW",
        "symbol": symbol,
        "apikey": _api_key(),
    }
    nulls = {k: None for k in [
        "earnings_growth", "revenue_growth", "trailing_pe", "forward_pe",
        "roe", "profit_margin", "debt_to_equity", "analyst_target", "recommendation",
    ]}
    try:
        r = requests.get(AV_BASE, params=params, timeout=15)
        d = r.json()
        if not d or "Symbol" not in d:
            return nulls

        def _f(key):
            val = d.get(key)
            try:
                return float(val) if val and val not in ("None", "-") else None
            except (TypeError, ValueError):
                return None

        return {
            "earnings_growth":  None,               # not in AV OVERVIEW
            "revenue_growth":   None,               # not in AV OVERVIEW
            "trailing_pe":      _f("TrailingPE"),
            "forward_pe":       _f("ForwardPE"),
            "roe":              _f("ReturnOnEquityTTM"),
            "profit_margin":    _f("ProfitMargin"),
            "debt_to_equity":   None,
            "analyst_target":   _f("AnalystTargetPrice"),
            "recommendation":   None,
        }

    except Exception as e:
        print(f"AV fundamentals error [{ticker}]: {e}")
        return nulls

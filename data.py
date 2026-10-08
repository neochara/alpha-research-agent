from __future__ import annotations

import pandas as pd
import yfinance as yf

from config import DATA_DIR, END_DATE, START_DATE, UNIVERSE

PRICE_FILE = DATA_DIR / "adjusted_close.csv"


def download_prices(force: bool = False) -> pd.DataFrame:
    """Download adjusted daily closes and cache them locally."""
    if PRICE_FILE.exists() and not force:
        return load_prices()

    raw = yf.download(
        UNIVERSE,
        start=START_DATE,
        end=END_DATE,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if raw.empty:
        raise RuntimeError("No market data was downloaded.")

    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"].copy()
    else:
        close = raw[["Close"]].copy()
        close.columns = UNIVERSE[:1]

    close = close.sort_index().reindex(columns=UNIVERSE).dropna(how="all")
    _validate_prices(close)
    close.to_csv(PRICE_FILE)
    return close


def load_prices() -> pd.DataFrame:
    """Load cached prices; download them on first use."""
    if not PRICE_FILE.exists():
        return download_prices()
    prices = pd.read_csv(PRICE_FILE, index_col=0, parse_dates=True)
    prices = prices.sort_index().reindex(columns=UNIVERSE)
    _validate_prices(prices)
    return prices


def _validate_prices(prices: pd.DataFrame) -> None:
    if prices.empty:
        raise ValueError("Price data is empty.")
    if prices.index.has_duplicates:
        raise ValueError("Price data contains duplicate dates.")
    if not prices.index.is_monotonic_increasing:
        raise ValueError("Price dates must be sorted.")
    if (prices <= 0).any().any():
        raise ValueError("Prices must be positive wherever observed.")
    if prices.notna().sum().max() < 300:
        raise ValueError("Insufficient price history for momentum research.")

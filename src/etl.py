"""Station 1 ETL helpers for the Part B build.

Part B starts from the same clean-data rules as Part A, but it must be
self-contained inside this folder. Raw data is always loaded through
``src.data_access`` and never committed to the repository.
"""
from __future__ import annotations

import pandas as pd

from src import data_access

PROJECT_END_DATE = pd.Timestamp("2023-12-31")


def naive_date(series: pd.Series) -> pd.Series:
    """Return timezone-naive midnight dates for joins and calendar alignment."""
    return pd.to_datetime(series, utc=True).dt.tz_convert(None).dt.normalize()


def load_clean_equities() -> pd.DataFrame:
    """Load equity prices, normalise dates, and enforce ticker-date uniqueness."""
    df = data_access.load_equity_prices().copy()
    df["date"] = naive_date(df["date"])
    df = df.sort_values(["ticker", "date"]).drop_duplicates(["ticker", "date"], keep="first")
    return df.reset_index(drop=True)


def load_clean_crypto() -> pd.DataFrame:
    """Load crypto prices, cap at 2023-12-31, and enforce ticker-date uniqueness."""
    df = data_access.load_crypto_prices().copy()
    df["date"] = naive_date(df["date"])
    df = df[df["date"] <= PROJECT_END_DATE].copy()
    df = df.sort_values(["ticker", "date"]).drop_duplicates(["ticker", "date"], keep="first")
    return df.reset_index(drop=True)


def load_clean_news() -> pd.DataFrame:
    """Load headlines, normalise dates, and drop exact ticker-date-title duplicates."""
    df = data_access.load_news_headlines().copy()
    df["date"] = naive_date(df["date"])
    df["title"] = df["title"].fillna("").astype(str).str.strip()
    df["publisher"] = df["publisher"].fillna("").astype(str).str.strip()
    df = df.drop_duplicates(["ticker", "date", "title"], keep="first")
    return df.sort_values(["ticker", "date", "title"]).reset_index(drop=True)

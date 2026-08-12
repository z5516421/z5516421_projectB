"""Station 2 features reused by the Part B models.

The functions here prepare return panels and trading-day-aligned headlines only.
Sentiment scoring and portfolio optimisation belong to Station 3.
"""
from __future__ import annotations

import pandas as pd


def daily_returns(prices: pd.DataFrame, asset_class: str, price_col: str = "adjClose") -> pd.DataFrame:
    """Compute simple daily returns within each ticker's own calendar."""
    df = prices.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    df = df.sort_values(["ticker", "date"])
    df["return"] = df.groupby("ticker", sort=False)[price_col].pct_change()
    df["asset_class"] = asset_class
    if "sector" not in df.columns:
        df["sector"] = "Crypto"
    return (
        df[["date", "ticker", "asset_class", "sector", "return"]]
        .dropna(subset=["return"])
        .reset_index(drop=True)
    )


def align_crypto_returns_to_equity_calendar(
    equity_returns: pd.DataFrame,
    crypto_returns: pd.DataFrame,
) -> pd.DataFrame:
    """Left-merge already-computed crypto returns onto equity trading dates."""
    eq = equity_returns.copy()
    cr = crypto_returns.copy()
    eq["date"] = pd.to_datetime(eq["date"]).dt.tz_localize(None).dt.normalize()
    cr["date"] = pd.to_datetime(cr["date"]).dt.tz_localize(None).dt.normalize()

    equity_calendar = eq[["date"]].drop_duplicates().sort_values("date")
    aligned = []
    for ticker in sorted(cr["ticker"].unique()):
        one = equity_calendar.merge(
            cr.loc[cr["ticker"] == ticker, ["date", "ticker", "asset_class", "sector", "return"]],
            on="date",
            how="left",
        )
        one["ticker"] = one["ticker"].fillna(ticker)
        one["asset_class"] = one["asset_class"].fillna("Crypto")
        one["sector"] = one["sector"].fillna("Crypto")
        aligned.append(one)
    return pd.concat(aligned, ignore_index=True)


def combined_returns_panel(equity_prices: pd.DataFrame, crypto_prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build equity, crypto, and combined long return panels for Part B."""
    equity_returns = daily_returns(equity_prices, "Equity")
    crypto_returns = daily_returns(crypto_prices, "Crypto")
    crypto_aligned = align_crypto_returns_to_equity_calendar(equity_returns, crypto_returns)
    combined = pd.concat([equity_returns, crypto_aligned], ignore_index=True)
    combined = combined.sort_values(["date", "asset_class", "ticker"]).reset_index(drop=True)
    return equity_returns, crypto_returns, combined


def returns_wide(returns: pd.DataFrame, tickers: list[str] | None = None) -> pd.DataFrame:
    """Convert a long return panel to a date x ticker matrix."""
    df = returns.copy()
    if tickers is not None:
        df = df[df["ticker"].isin(tickers)].copy()
    wide = df.pivot_table(index="date", columns="ticker", values="return", aggfunc="first")
    wide.index = pd.to_datetime(wide.index).tz_localize(None).normalize()
    return wide.sort_index()


def assemble_daily_text_panel(headlines: pd.DataFrame, trading_dates: pd.Series) -> pd.DataFrame:
    """Map each headline to the same or next equity trading day."""
    df = headlines.copy()
    df["headline_date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert(None).dt.normalize()
    df["headline_date"] = df["headline_date"].astype("datetime64[ns]")
    df["headline_text"] = df["title"].fillna("").astype(str).str.strip()
    df["publisher"] = df["publisher"].fillna("").astype(str).str.strip()
    df = df.drop_duplicates(["ticker", "headline_date", "headline_text"], keep="first")
    df = df.drop(columns=["date"])

    calendar = pd.DataFrame(
        {"date": pd.to_datetime(trading_dates).dt.tz_localize(None).dt.normalize().drop_duplicates().sort_values()}
    )
    calendar["date"] = calendar["date"].astype("datetime64[ns]")
    mapped = pd.merge_asof(
        df.sort_values("headline_date"),
        calendar.sort_values("date"),
        left_on="headline_date",
        right_on="date",
        direction="forward",
    )
    mapped["mapped_from_non_trading_day"] = mapped["headline_date"] != mapped["date"]
    mapped["mapping_status"] = mapped["date"].isna().map(
        {False: "mapped_to_equity_trading_day", True: "no_next_equity_trading_day_in_sample"}
    )
    keep = [
        "date",
        "headline_date",
        "ticker",
        "sector",
        "publisher",
        "headline_text",
        "url",
        "mapped_from_non_trading_day",
        "mapping_status",
    ]
    return mapped[keep].sort_values(["date", "sector", "ticker", "headline_date"], na_position="last").reset_index(drop=True)

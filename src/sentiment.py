"""Station 3 sentiment scoring and sector index construction."""
from __future__ import annotations

import numpy as np
import pandas as pd


FINANCE_VADER_LEXICON = {
    "beat": 2.4,
    "beats": 2.4,
    "earnings beat": 2.9,
    "record revenue": 3.0,
    "buyback": 2.0,
    "upgrade": 2.2,
    "upgraded": 2.2,
    "outperform": 1.8,
    "bullish": 2.0,
    "dovish": 1.0,
    "tailwind": 1.4,
    "guidance raise": 2.4,
    "raised guidance": 2.4,
    "downgrade": -2.2,
    "downgraded": -2.2,
    "miss": -1.8,
    "misses": -1.8,
    "earnings miss": -2.4,
    "guidance cut": -2.9,
    "profit warning": -2.6,
    "impairment": -1.8,
    "headwind": -1.8,
    "hawkish": -1.0,
    "going concern": -3.9,
    "insolvency": -3.9,
    "bankruptcy": -3.5,
    "plunge": -2.4,
    "plunges": -2.4,
    "slump": -2.1,
    "slumps": -2.1,
    "lawsuit": -1.8,
    "probe": -1.5,
}


def _get_vader_analyser(finance_adjusted: bool = False):
    """Build a VADER analyser, downloading the lexicon if needed."""
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer

    try:
        analyser = SentimentIntensityAnalyzer()
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)
        analyser = SentimentIntensityAnalyzer()
    if finance_adjusted:
        analyser.lexicon.update(FINANCE_VADER_LEXICON)
    return analyser


def to_score_100(compound: pd.Series) -> pd.Series:
    """Map a compound score from [-1, 1] to a 0-100 fear/greed score."""
    return ((compound.astype(float) + 1.0) / 2.0) * 100.0


def score_headlines(panel: pd.DataFrame) -> pd.DataFrame:
    """Score mapped headline rows with baseline VADER and finance-extended VADER."""
    df = panel.copy()
    df = df[df["date"].notna()].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    df["headline_text"] = df["headline_text"].fillna("").astype(str)

    vader = _get_vader_analyser(finance_adjusted=False)
    finance_vader = _get_vader_analyser(finance_adjusted=True)

    distinct = df[["headline_text"]].drop_duplicates().copy()
    distinct["vader_compound"] = distinct["headline_text"].map(lambda text: vader.polarity_scores(text)["compound"])
    distinct["finance_vader_compound"] = distinct["headline_text"].map(
        lambda text: finance_vader.polarity_scores(text)["compound"]
    )
    distinct["vader_score_100"] = to_score_100(distinct["vader_compound"])
    distinct["finance_vader_score_100"] = to_score_100(distinct["finance_vader_compound"])

    scored = df.merge(distinct, on="headline_text", how="left")
    return scored.sort_values(["date", "sector", "ticker", "headline_date"]).reset_index(drop=True)


def ticker_day_sentiment(scored_headlines: pd.DataFrame) -> pd.DataFrame:
    """Average headline scores into one ticker-day sentiment observation."""
    df = scored_headlines.copy()
    grouped = (
        df.groupby(["date", "ticker", "sector"], as_index=False)
        .agg(
            headline_count=("headline_text", "count"),
            vader_compound=("vader_compound", "mean"),
            finance_vader_compound=("finance_vader_compound", "mean"),
            vader_score_100=("vader_score_100", "mean"),
            finance_vader_score_100=("finance_vader_score_100", "mean"),
        )
        .sort_values(["date", "sector", "ticker"])
        .reset_index(drop=True)
    )
    return grouped


def _expanding_zscore_by_sector(index: pd.DataFrame, value_col: str, min_periods: int = 30) -> pd.Series:
    """Look-ahead-safe z-score using sector history up to t-1."""
    pieces = []
    for _, group in index.sort_values(["sector", "date"]).groupby("sector", sort=False):
        values = group[value_col].astype(float)
        past_mean = values.expanding(min_periods=min_periods).mean().shift(1)
        past_std = values.expanding(min_periods=min_periods).std(ddof=1).shift(1)
        z = (values - past_mean) / past_std.replace(0.0, np.nan)
        pieces.append(z)
    return pd.concat(pieces).sort_index()


def sector_sentiment_index(scores: pd.DataFrame, sector_universe: pd.DataFrame) -> pd.DataFrame:
    """Build equal-ticker-weight daily sector sentiment indices."""
    ticker_day = ticker_day_sentiment(scores)
    sector_counts = sector_universe.groupby("sector")["ticker"].nunique().rename("sector_ticker_count")

    index = (
        ticker_day.groupby(["date", "sector"], as_index=False)
        .agg(
            active_tickers=("ticker", "nunique"),
            headline_count=("headline_count", "sum"),
            vader_compound=("vader_compound", "mean"),
            finance_vader_compound=("finance_vader_compound", "mean"),
            vader_score_100=("vader_score_100", "mean"),
            finance_vader_score_100=("finance_vader_score_100", "mean"),
        )
        .sort_values(["sector", "date"])
        .reset_index(drop=True)
    )
    index = index.merge(sector_counts, on="sector", how="left")
    index["coverage_ratio"] = index["active_tickers"] / index["sector_ticker_count"]

    for prefix in ["vader", "finance_vader"]:
        score_col = f"{prefix}_score_100"
        z_col = f"{prefix}_expanding_z"
        index[f"{prefix}_rolling_21d"] = (
            index.groupby("sector", sort=False)[score_col]
            .transform(lambda s: s.rolling(21, min_periods=5).mean())
        )
        index[z_col] = _expanding_zscore_by_sector(index, score_col)
        index[f"{prefix}_signal_lag1"] = index.groupby("sector", sort=False)[z_col].shift(1)
        index[f"{prefix}_coverage_lag1"] = index.groupby("sector", sort=False)["coverage_ratio"].shift(1)
        index[f"{prefix}_coverage_adjusted_signal_lag1"] = (
            index[f"{prefix}_signal_lag1"] * index[f"{prefix}_coverage_lag1"]
        )

    return index.sort_values(["date", "sector"]).reset_index(drop=True)


def sentiment_model_comparison(sector_index: pd.DataFrame) -> pd.DataFrame:
    """Summarise how baseline VADER differs from the finance-extended model."""
    rows = []
    for sector, group in sector_index.groupby("sector"):
        diff = group["finance_vader_score_100"] - group["vader_score_100"]
        rows.append(
            {
                "sector": sector,
                "days": int(len(group)),
                "mean_vader_score_100": float(group["vader_score_100"].mean()),
                "mean_finance_vader_score_100": float(group["finance_vader_score_100"].mean()),
                "mean_finance_minus_vader": float(diff.mean()),
                "correlation": float(group["vader_score_100"].corr(group["finance_vader_score_100"])),
                "mean_coverage_ratio": float(group["coverage_ratio"].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("sector").reset_index(drop=True)

"""Station 3 fusion: sentiment-aware equity portfolio overlays."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.portfolios import build_metrics_table, realized_rebalance_turnover


def _latest_sector_signal(
    sector_sentiment: pd.DataFrame,
    rebalance_date: pd.Timestamp,
    signal_col: str,
) -> pd.DataFrame:
    """Return the latest strictly pre-rebalance signal for each sector."""
    history = sector_sentiment.loc[sector_sentiment["date"] < rebalance_date].copy()
    if history.empty:
        return pd.DataFrame(columns=["sector", signal_col, "coverage_ratio", "signal_date"])
    latest_idx = history.sort_values("date").groupby("sector")["date"].idxmax()
    latest = history.loc[latest_idx, ["sector", "date", signal_col, "coverage_ratio"]].copy()
    latest = latest.rename(columns={"date": "signal_date"})
    return latest


def apply_sentiment(
    base_weights: pd.DataFrame,
    sector_sentiment: pd.DataFrame,
    sector_map: pd.DataFrame,
    lambda_tilt: float = 0.15,
    signal_col: str = "finance_vader_coverage_adjusted_signal_lag1",
) -> pd.DataFrame:
    """Tilt base equity weights using lagged sector sentiment.

    Positive sector signals raise all stocks in that sector; negative signals
    lower them. The exponential tilt keeps weights non-negative, and the final
    normalisation keeps the portfolio fully invested.
    """
    weights = base_weights.copy()
    weights["rebalance_date"] = pd.to_datetime(weights["rebalance_date"]).dt.tz_localize(None).dt.normalize()
    sentiment = sector_sentiment.copy()
    sentiment["date"] = pd.to_datetime(sentiment["date"]).dt.tz_localize(None).dt.normalize()
    sectors = sector_map[["ticker", "sector"]].drop_duplicates()

    out = []
    for rebalance_date, group in weights.groupby("rebalance_date", sort=True):
        one = group.merge(sectors, on="ticker", how="left", suffixes=("", "_map"))
        if "sector_map" in one.columns:
            one["sector"] = one["sector_map"].fillna(one["sector"])
            one = one.drop(columns=["sector_map"])
        latest = _latest_sector_signal(sentiment, rebalance_date, signal_col)
        one = one.merge(latest, on="sector", how="left")
        one[signal_col] = one[signal_col].fillna(0.0)
        one["coverage_ratio"] = one["coverage_ratio"].fillna(0.0)
        one["signal_date"] = pd.to_datetime(one["signal_date"])
        one["lambda_tilt"] = lambda_tilt
        one["tilt_multiplier"] = np.exp(lambda_tilt * one[signal_col].clip(-3.0, 3.0))
        one["raw_sentiment_weight"] = one["weight"] * one["tilt_multiplier"]
        total = one["raw_sentiment_weight"].sum()
        one["sentiment_weight"] = one["raw_sentiment_weight"] / total if total > 0 else one["weight"]
        out.append(one)
    tilted = pd.concat(out, ignore_index=True)
    tilted["fund"] = tilted["fund"] + " + Sentiment Tilt"
    tilted["method"] = tilted["method"] + " + Sentiment Tilt"
    return tilted


def backtest_tilted_weights(
    tilted_weights: pd.DataFrame,
    equity_returns: pd.DataFrame,
    periods_per_year: int = 252,
) -> pd.DataFrame:
    """Apply monthly tilted weights to the next live return block."""
    returns = equity_returns.copy()
    returns.index = pd.to_datetime(returns.index).tz_localize(None).normalize()
    returns = returns.sort_index()
    weights = tilted_weights.copy()
    weights["rebalance_date"] = pd.to_datetime(weights["rebalance_date"]).dt.tz_localize(None).dt.normalize()
    rebalance_dates = sorted(weights["rebalance_date"].unique())

    rows = []
    for idx, rebalance_date in enumerate(rebalance_dates):
        one = weights.loc[weights["rebalance_date"] == rebalance_date]
        tickers = one["ticker"].tolist()
        w = one.set_index("ticker")["sentiment_weight"]
        if idx + 1 < len(rebalance_dates):
            next_rebalance = rebalance_dates[idx + 1]
            live = returns.loc[(returns.index >= rebalance_date) & (returns.index < next_rebalance), tickers]
        else:
            live = returns.loc[returns.index >= rebalance_date, tickers]
        live = live.fillna(0.0)
        daily = live @ w
        for date, value in daily.items():
            rows.append(
                {
                    "date": date,
                    "universe": "Equity",
                    "method": one["method"].iloc[0],
                    "fund": one["fund"].iloc[0],
                    "return": float(value),
                    "periods_per_year": periods_per_year,
                    "lambda_tilt": float(one["lambda_tilt"].iloc[0]),
                }
            )
    return pd.DataFrame(rows)


def build_fusion_experiment(
    fund_weights: pd.DataFrame,
    fund_returns: pd.DataFrame,
    equity_returns: pd.DataFrame,
    sector_sentiment: pd.DataFrame,
    sector_map: pd.DataFrame,
    base_funds: tuple[str, ...] = ("Equity Equal Weight", "Equity Risk Parity"),
    lambda_tilt: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run base-vs-sentiment overlay experiments for selected equity funds."""
    weights_all = []
    returns_all = []
    for base_fund in base_funds:
        base = fund_weights.loc[fund_weights["fund"] == base_fund].copy()
        tilted = apply_sentiment(base, sector_sentiment, sector_map, lambda_tilt=lambda_tilt)
        tilted_returns = backtest_tilted_weights(tilted, equity_returns)
        weights_all.append(tilted)
        returns_all.append(tilted_returns)

    fusion_weights = pd.concat(weights_all, ignore_index=True)
    fusion_returns = pd.concat(returns_all, ignore_index=True)
    comparison_input = pd.concat(
        [fund_returns.loc[fund_returns["fund"].isin(base_funds)].copy(), fusion_returns],
        ignore_index=True,
    )
    comparison_weights = pd.concat(
        [
            fund_weights.loc[fund_weights["fund"].isin(base_funds)].copy(),
            fusion_weights.assign(weight=fusion_weights["sentiment_weight"])[
                ["rebalance_date", "training_end_date", "universe", "method", "fund", "ticker", "weight"]
            ],
        ],
        ignore_index=True,
    )
    turnover_diagnostics = realized_rebalance_turnover(comparison_weights, equity_returns)
    comparison = build_metrics_table(comparison_input, comparison_weights, turnover_diagnostics)
    comparison["experiment"] = np.where(comparison["fund"].str.contains("Sentiment Tilt"), "sentiment_augmented", "base")
    comparison["lambda_tilt"] = np.where(comparison["experiment"] == "sentiment_augmented", lambda_tilt, 0.0)
    return fusion_returns, fusion_weights, comparison

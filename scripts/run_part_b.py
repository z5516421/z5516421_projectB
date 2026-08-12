"""Reproduce the Part B funds, sentiment artifacts, tables, and figures.

Run from the project root:

    python scripts/run_part_b.py
"""
from __future__ import annotations

import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import data_access  # noqa: E402
from src.etl import load_clean_crypto, load_clean_equities, load_clean_news  # noqa: E402
from src.features import assemble_daily_text_panel, combined_returns_panel, returns_wide  # noqa: E402
from src.figures import build_all_figures  # noqa: E402
from src.fusion import build_fusion_experiment  # noqa: E402
from src.portfolios import METHODS, build_backtest_audit, build_metrics_table, oos_backtest  # noqa: E402
from src.sentiment import score_headlines, sector_sentiment_index, sentiment_model_comparison, ticker_day_sentiment  # noqa: E402


def _write(df: pd.DataFrame, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print("saved:", path.relative_to(pathlib.Path.cwd()))


def _latest_holdings(weights: pd.DataFrame) -> pd.DataFrame:
    latest_dates = (
        weights.groupby("fund", as_index=False)["rebalance_date"]
        .max()
        .rename(columns={"rebalance_date": "latest_rebalance_date"})
    )
    holdings = weights.merge(
        latest_dates,
        left_on=["fund", "rebalance_date"],
        right_on=["fund", "latest_rebalance_date"],
        how="inner",
    )
    cols = ["fund", "universe", "method", "latest_rebalance_date", "ticker", "weight"]
    return holdings[cols].sort_values(["fund", "weight"], ascending=[True, False])


def build_oos_funds(root: pathlib.Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eq = load_clean_equities()
    cr = load_clean_crypto()
    news = load_clean_news()
    eq_returns, cr_returns, combined = combined_returns_panel(eq, cr)
    daily_text_panel = assemble_daily_text_panel(news, eq["date"])

    data_dir = root / "results" / "data"
    _write(eq_returns, data_dir / "equity_returns.csv")
    _write(cr_returns, data_dir / "crypto_returns.csv")
    _write(combined, data_dir / "combined_returns_panel.csv")
    _write(daily_text_panel, data_dir / "daily_text_panel.csv")

    universes = {
        "Equity": (returns_wide(eq_returns), 252),
        "Crypto": (returns_wide(cr_returns), 365),
        "Combined": (returns_wide(combined), 252),
    }

    all_returns = []
    all_weights = []
    all_diagnostics = []
    for universe, (matrix, periods_per_year) in universes.items():
        for method in METHODS:
            print(f"backtesting {universe} / {method}")
            result = oos_backtest(
                matrix,
                universe=universe,
                method=method,
                periods_per_year=periods_per_year,
                first_live_date="2021-01-01",
            )
            all_returns.append(result.returns)
            all_weights.append(result.weights)
            all_diagnostics.append(result.diagnostics)

    fund_returns = pd.concat(all_returns, ignore_index=True)
    fund_weights = pd.concat(all_weights, ignore_index=True)
    diagnostics = pd.concat(all_diagnostics, ignore_index=True)
    metrics = build_metrics_table(fund_returns, fund_weights, diagnostics)
    audit = build_backtest_audit(fund_returns, fund_weights, diagnostics)
    holdings = _latest_holdings(fund_weights)

    _write(fund_returns, data_dir / "fund_returns.csv")
    _write(fund_weights, data_dir / "fund_weights.csv")
    _write(diagnostics, data_dir / "backtest_diagnostics.csv")
    _write(holdings, data_dir / "current_holdings.csv")
    _write(metrics, root / "results" / "tables" / "performance_metrics.csv")
    _write(audit, root / "results" / "tables" / "backtest_audit.csv")
    return fund_returns, fund_weights, metrics


def build_sentiment(root: pathlib.Path) -> pd.DataFrame:
    eq = load_clean_equities()
    news = load_clean_news()
    daily_text_panel = assemble_daily_text_panel(news, eq["date"])
    sector_universe = data_access.load_sector_universe()

    print("scoring headlines with VADER and finance-extended VADER")
    scored = score_headlines(daily_text_panel)
    ticker_day = ticker_day_sentiment(scored)
    sector_index = sector_sentiment_index(scored, sector_universe)
    comparison = sentiment_model_comparison(sector_index)

    data_dir = root / "results" / "data"
    tables_dir = root / "results" / "tables"
    _write(scored, data_dir / "headline_sentiment_scores.csv")
    _write(ticker_day, data_dir / "ticker_day_sentiment.csv")
    _write(sector_index, data_dir / "sector_sentiment_index.csv")
    _write(comparison, tables_dir / "sentiment_model_comparison.csv")
    return sector_index


def build_fusion(root: pathlib.Path, fund_returns: pd.DataFrame, fund_weights: pd.DataFrame, sector_index: pd.DataFrame) -> pd.DataFrame:
    eq_returns = pd.read_csv(root / "results" / "data" / "equity_returns.csv", parse_dates=["date"])
    equity_matrix = returns_wide(eq_returns)
    sector_map = data_access.load_sector_universe()
    fusion_returns, fusion_weights, comparison = build_fusion_experiment(
        fund_weights=fund_weights,
        fund_returns=fund_returns,
        equity_returns=equity_matrix,
        sector_sentiment=sector_index,
        sector_map=sector_map,
        lambda_tilt=0.15,
    )
    _write(fusion_returns, root / "results" / "data" / "fusion_returns.csv")
    _write(fusion_weights, root / "results" / "data" / "fusion_weights.csv")
    _write(comparison, root / "results" / "tables" / "fusion_comparison.csv")
    return comparison


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    for folder in [root / "results" / "data", root / "results" / "tables", root / "results" / "figures"]:
        folder.mkdir(parents=True, exist_ok=True)
    fund_returns, fund_weights, metrics = build_oos_funds(root)
    sector_index = build_sentiment(root)
    fusion_comparison = build_fusion(root, fund_returns, fund_weights, sector_index)
    build_all_figures(root, fund_returns, fund_weights, metrics, sector_index, fusion_comparison)
    print("Part B fund backtests, sentiment index, and fusion experiment complete.")


if __name__ == "__main__":
    main()

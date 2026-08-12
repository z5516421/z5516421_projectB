"""Station 3 portfolio construction and out-of-sample backtesting."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

METHODS = ["equal_weight", "min_variance", "tangency", "risk_parity"]
METHOD_LABELS = {
    "equal_weight": "Equal Weight",
    "min_variance": "Minimum Variance",
    "tangency": "Tangency",
    "risk_parity": "Risk Parity",
}


@dataclass(frozen=True)
class BacktestResult:
    """Container for daily OOS returns and rebalance weights."""

    returns: pd.DataFrame
    weights: pd.DataFrame
    diagnostics: pd.DataFrame


@dataclass(frozen=True)
class WeightSolution:
    """Portfolio weights plus optimiser diagnostics for auditability."""

    weights: pd.Series
    status: str
    fallback: bool
    objective_value: float | None


def _clean_training_matrix(train: pd.DataFrame) -> pd.DataFrame:
    """Drop assets with insufficient history and fill small return gaps conservatively."""
    min_obs = max(60, int(len(train) * 0.75))
    clean = train.dropna(axis=1, thresh=min_obs)
    clean = clean.fillna(0.0)
    return clean.loc[:, clean.std() > 1e-10]


def _regularized_cov(train: pd.DataFrame) -> np.ndarray:
    cov = train.cov().to_numpy(dtype=float)
    diag_mean = float(np.nanmean(np.diag(cov))) if cov.size else 0.0
    ridge = max(diag_mean, 1e-8) * 1e-4
    return cov + np.eye(cov.shape[0]) * ridge


def _equal_weight(n_assets: int) -> np.ndarray:
    return np.repeat(1.0 / n_assets, n_assets)


def _min_variance_weights(cov: np.ndarray) -> tuple[np.ndarray, bool, float | None]:
    n = cov.shape[0]
    x0 = _equal_weight(n)
    bounds = [(0.0, 1.0)] * n
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    result = minimize(lambda w: float(w @ cov @ w), x0, method="SLSQP", bounds=bounds, constraints=constraints)
    weights = result.x if result.success else x0
    objective = float(result.fun) if result.success else None
    return weights, not result.success, objective


def _tangency_weights(mu: np.ndarray, cov: np.ndarray, risk_free_daily: float = 0.0) -> tuple[np.ndarray, bool, float | None]:
    """Long-only maximum-Sharpe weights using a robust direct Sharpe objective."""
    n = len(mu)
    x0 = _equal_weight(n)
    excess = mu - risk_free_daily
    if np.nanmax(excess) <= 0:
        weights, _, objective = _min_variance_weights(cov)
        return weights, True, objective

    bounds = [(0.0, 1.0)] * n
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    def objective(w: np.ndarray) -> float:
        ret = float(w @ excess)
        vol = float(np.sqrt(max(w @ cov @ w, 1e-12)))
        return -ret / vol

    result = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints, options={"maxiter": 1000})
    if not result.success or not np.isfinite(result.x).all():
        weights, _, minvar_objective = _min_variance_weights(cov)
        return weights, True, minvar_objective
    return result.x, False, float(result.fun)


def _risk_parity_weights(cov: np.ndarray) -> tuple[np.ndarray, bool, float | None]:
    """Long-only equal risk-contribution portfolio."""
    n = cov.shape[0]
    x0 = _equal_weight(n)
    bounds = [(1e-8, 1.0)] * n
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    def risk_contribution(w: np.ndarray) -> np.ndarray:
        port_var = max(float(w @ cov @ w), 1e-12)
        marginal = cov @ w
        return w * marginal / port_var

    target = np.repeat(1.0 / n, n)

    def objective(w: np.ndarray) -> float:
        diff = risk_contribution(w) - target
        return float(diff @ diff)

    result = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints, options={"maxiter": 1000})
    success = result.success and np.isfinite(result.x).all()
    return (result.x if success else x0), not success, (float(result.fun) if success else None)


def risk_contributions(weights: pd.Series, train: pd.DataFrame) -> pd.Series:
    """Return each asset's share of portfolio variance using the training covariance."""
    aligned = train.loc[:, weights.index].fillna(0.0)
    cov = _regularized_cov(aligned)
    w = weights.to_numpy(dtype=float)
    port_var = max(float(w @ cov @ w), 1e-12)
    contributions = w * (cov @ w) / port_var
    return pd.Series(contributions, index=weights.index, name="risk_contribution")


def solve_weights(train: pd.DataFrame, method: str, risk_free_daily: float = 0.0) -> WeightSolution:
    """Solve long-only fully invested weights from past returns only."""
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}; expected one of {METHODS}")
    clean = _clean_training_matrix(train)
    if clean.empty:
        raise ValueError("training window has no usable assets")

    n = clean.shape[1]
    fallback = False
    objective_value = None
    if method == "equal_weight":
        weights = _equal_weight(n)
    else:
        cov = _regularized_cov(clean)
        if method == "min_variance":
            weights, fallback, objective_value = _min_variance_weights(cov)
        elif method == "tangency":
            weights, fallback, objective_value = _tangency_weights(clean.mean().to_numpy(dtype=float), cov, risk_free_daily)
        else:
            weights, fallback, objective_value = _risk_parity_weights(cov)

    weights = np.clip(weights, 0.0, 1.0)
    weights = weights / weights.sum()
    status = "fallback" if fallback else "success"
    return WeightSolution(pd.Series(weights, index=clean.columns, name="weight"), status, fallback, objective_value)


def monthly_rebalance_dates(returns: pd.DataFrame, first_live_date: str | pd.Timestamp = "2021-01-01") -> list[pd.Timestamp]:
    """Return the first available trading date in each live month."""
    live = returns.loc[returns.index >= pd.Timestamp(first_live_date)]
    return [pd.Timestamp(group.index.min()) for _, group in live.groupby(live.index.to_period("M"))]


def oos_backtest(
    returns: pd.DataFrame,
    universe: str,
    method: str,
    periods_per_year: int,
    first_live_date: str | pd.Timestamp = "2021-01-01",
    risk_free_daily: float = 0.0,
) -> BacktestResult:
    """Run monthly expanding-window OOS backtest for one universe and method."""
    matrix = returns.copy()
    matrix.index = pd.to_datetime(matrix.index).tz_localize(None).normalize()
    matrix = matrix.sort_index()
    rebalance_dates = monthly_rebalance_dates(matrix, first_live_date)

    fund_returns = []
    weight_rows = []
    diagnostic_rows = []
    previous_weights: pd.Series | None = None
    previous_live: pd.DataFrame | None = None
    for idx, rebalance_date in enumerate(rebalance_dates):
        train = matrix.loc[matrix.index < rebalance_date]
        if train.empty:
            continue
        solution = solve_weights(train, method=method, risk_free_daily=risk_free_daily)
        weights = solution.weights
        rebalance_turnover = np.nan
        if previous_weights is not None and previous_live is not None:
            drifted = _drifted_weights(previous_weights, previous_live)
            aligned = pd.concat([drifted.rename("drifted"), weights.rename("target")], axis=1).fillna(0.0)
            rebalance_turnover = float((aligned["target"] - aligned["drifted"]).abs().sum() / 2.0)

        if idx + 1 < len(rebalance_dates):
            next_rebalance = rebalance_dates[idx + 1]
            live = matrix.loc[(matrix.index >= rebalance_date) & (matrix.index < next_rebalance), weights.index]
        else:
            live = matrix.loc[matrix.index >= rebalance_date, weights.index]
        live = live.fillna(0.0)
        daily = live @ weights

        for date, value in daily.items():
            fund_returns.append(
                {
                    "date": date,
                    "universe": universe,
                    "method": METHOD_LABELS[method],
                    "fund": f"{universe} {METHOD_LABELS[method]}",
                    "return": float(value),
                    "periods_per_year": periods_per_year,
                }
            )
        for ticker, weight in weights.items():
            weight_rows.append(
                {
                    "rebalance_date": rebalance_date,
                    "training_end_date": train.index.max(),
                    "universe": universe,
                    "method": METHOD_LABELS[method],
                    "fund": f"{universe} {METHOD_LABELS[method]}",
                    "ticker": ticker,
                    "weight": float(weight),
                }
            )
        diagnostic_rows.append(
            {
                "rebalance_date": rebalance_date,
                "training_end_date": train.index.max(),
                "max_training_observation_date": train.loc[:, weights.index].dropna(how="all").index.max(),
                "first_live_return_date": live.index.min(),
                "universe": universe,
                "method": METHOD_LABELS[method],
                "fund": f"{universe} {METHOD_LABELS[method]}",
                "assets_used": int(len(weights)),
                "solver_status": solution.status,
                "fallback_used": bool(solution.fallback),
                "objective_value": solution.objective_value,
                "weight_sum": float(weights.sum()),
                "min_weight": float(weights.min()),
                "max_weight": float(weights.max()),
                "rebalance_turnover": rebalance_turnover,
                "risk_contribution_dispersion": float(
                    risk_contributions(weights, train).max() - risk_contributions(weights, train).min()
                ),
            }
        )
        previous_weights = weights
        previous_live = live

    return BacktestResult(pd.DataFrame(fund_returns), pd.DataFrame(weight_rows), pd.DataFrame(diagnostic_rows))


def performance_metrics(daily_returns: pd.Series, periods_per_year: int = 252, risk_free_rate: float = 0.0) -> dict:
    """Compute fund fact-sheet metrics from daily OOS returns."""
    returns = pd.Series(daily_returns).dropna().astype(float)
    if returns.empty:
        return {
            "observations": 0,
            "annualised_return": np.nan,
            "annualised_volatility": np.nan,
            "sharpe_ratio": np.nan,
            "sortino_ratio": np.nan,
            "historical_var_95": np.nan,
            "expected_shortfall_95": np.nan,
            "maximum_drawdown": np.nan,
            "growth_of_1": np.nan,
        }

    growth = (1.0 + returns).cumprod()
    total_growth = float(growth.iloc[-1])
    annualised_return = total_growth ** (periods_per_year / len(returns)) - 1.0
    annualised_volatility = float(returns.std(ddof=1) * np.sqrt(periods_per_year))
    excess_returns = returns - (risk_free_rate / periods_per_year)
    excess_volatility = float(excess_returns.std(ddof=1))
    sharpe = (
        float(excess_returns.mean() / excess_volatility * np.sqrt(periods_per_year))
        if excess_volatility > 0
        else np.nan
    )

    downside = excess_returns.clip(upper=0.0)
    downside_vol = float(np.sqrt((downside.pow(2).mean())) * np.sqrt(periods_per_year))
    annualised_mean_excess = float(excess_returns.mean() * periods_per_year)
    sortino = annualised_mean_excess / downside_vol if downside_vol > 0 else np.nan

    q05 = float(returns.quantile(0.05))
    tail = returns[returns <= q05]
    drawdown = growth / growth.cummax() - 1.0
    return {
        "observations": int(len(returns)),
        "annualised_return": float(annualised_return),
        "annualised_volatility": annualised_volatility,
        "sharpe_ratio": float(sharpe),
        "sortino_ratio": float(sortino),
        "historical_var_95": float(-q05),
        "expected_shortfall_95": float(-tail.mean()) if not tail.empty else np.nan,
        "maximum_drawdown": float(drawdown.min()),
        "growth_of_1": total_growth,
    }


def weights_turnover(weights: pd.DataFrame) -> pd.DataFrame:
    """Compute target-weight changes from rebalance to rebalance."""
    if weights.empty:
        return pd.DataFrame(columns=["fund", "rebalance_date", "turnover"])
    pivot = weights.pivot_table(index=["fund", "rebalance_date"], columns="ticker", values="weight", fill_value=0.0)
    rows = []
    for fund, group in pivot.groupby(level=0):
        w = group.droplevel(0).sort_index()
        turnover = w.diff().abs().sum(axis=1) / 2.0
        turnover.iloc[0] = np.nan
        for date, value in turnover.items():
            rows.append({"fund": fund, "rebalance_date": date, "turnover": float(value) if pd.notna(value) else np.nan})
    return pd.DataFrame(rows)


def _drifted_weights(previous_weights: pd.Series, live_returns: pd.DataFrame) -> pd.Series:
    """Drift target weights through a live holding period before rebalancing."""
    live = live_returns.reindex(columns=previous_weights.index).fillna(0.0)
    if live.empty:
        return previous_weights.copy()
    drifted = previous_weights * (1.0 + live).prod(axis=0)
    total = float(drifted.sum())
    return drifted / total if total > 0 else previous_weights.copy()


def realized_rebalance_turnover(
    weights: pd.DataFrame,
    asset_returns: pd.DataFrame,
    weight_col: str = "weight",
) -> pd.DataFrame:
    """Compute implementable one-way turnover using pre-rebalance drifted weights."""
    if weights.empty:
        return pd.DataFrame(columns=["fund", "rebalance_date", "rebalance_turnover"])
    returns = asset_returns.copy()
    returns.index = pd.to_datetime(returns.index).tz_localize(None).normalize()
    returns = returns.sort_index()
    wdf = weights.copy()
    wdf["rebalance_date"] = pd.to_datetime(wdf["rebalance_date"]).dt.tz_localize(None).dt.normalize()

    rows = []
    for fund, group in wdf.groupby("fund", sort=False):
        group = group.sort_values(["rebalance_date", "ticker"])
        dates = sorted(group["rebalance_date"].unique())
        previous_weights = None
        previous_live = None
        for idx, rebalance_date in enumerate(dates):
            current = group[group["rebalance_date"] == rebalance_date].set_index("ticker")[weight_col].astype(float)
            turnover = np.nan
            if previous_weights is not None and previous_live is not None:
                drifted = _drifted_weights(previous_weights, previous_live)
                aligned = pd.concat([drifted.rename("drifted"), current.rename("target")], axis=1).fillna(0.0)
                turnover = float((aligned["target"] - aligned["drifted"]).abs().sum() / 2.0)

            if idx + 1 < len(dates):
                next_rebalance = dates[idx + 1]
                live = returns.loc[(returns.index >= rebalance_date) & (returns.index < next_rebalance), current.index]
            else:
                live = returns.loc[returns.index >= rebalance_date, current.index]
            rows.append({"fund": fund, "rebalance_date": rebalance_date, "rebalance_turnover": turnover})
            previous_weights = current
            previous_live = live
    return pd.DataFrame(rows)


def build_metrics_table(
    fund_returns: pd.DataFrame,
    fund_weights: pd.DataFrame | None = None,
    diagnostics: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build the required performance metrics table across all funds."""
    rows = []
    if diagnostics is not None and "rebalance_turnover" in diagnostics.columns:
        avg_turnover = diagnostics.groupby("fund")["rebalance_turnover"].mean()
    else:
        turnover = weights_turnover(fund_weights) if fund_weights is not None else pd.DataFrame()
        avg_turnover = turnover.groupby("fund")["turnover"].mean() if not turnover.empty else pd.Series(dtype=float)
    for fund, group in fund_returns.groupby("fund", sort=False):
        periods_per_year = int(group["periods_per_year"].iloc[0])
        metrics = performance_metrics(group.set_index("date")["return"], periods_per_year=periods_per_year)
        metrics.update(
            {
                "fund": fund,
                "universe": group["universe"].iloc[0],
                "method": group["method"].iloc[0],
                "periods_per_year": periods_per_year,
                "average_turnover": float(avg_turnover.get(fund, np.nan)),
            }
        )
        rows.append(metrics)
    columns = [
        "fund",
        "universe",
        "method",
        "observations",
        "periods_per_year",
        "annualised_return",
        "annualised_volatility",
        "sharpe_ratio",
        "sortino_ratio",
        "historical_var_95",
        "expected_shortfall_95",
        "maximum_drawdown",
        "growth_of_1",
        "average_turnover",
    ]
    return pd.DataFrame(rows)[columns].sort_values(["universe", "method"]).reset_index(drop=True)


def build_backtest_audit(
    fund_returns: pd.DataFrame,
    fund_weights: pd.DataFrame,
    diagnostics: pd.DataFrame,
) -> pd.DataFrame:
    """Summarise OOS date coverage, constraints, and optimiser diagnostics per fund."""
    rows = []
    grouped_returns = fund_returns.groupby("fund", sort=False)
    grouped_weights = fund_weights.groupby("fund", sort=False)
    grouped_diag = diagnostics.groupby("fund", sort=False)
    for fund, returns_group in grouped_returns:
        weights_group = grouped_weights.get_group(fund)
        diag_group = grouped_diag.get_group(fund)
        weight_sums = weights_group.groupby("rebalance_date")["weight"].sum()
        duplicate_returns = returns_group.duplicated(["fund", "date"]).sum()
        rows.append(
            {
                "fund_name": fund,
                "universe": returns_group["universe"].iloc[0],
                "method": returns_group["method"].iloc[0],
                "first_oos_date": returns_group["date"].min(),
                "last_oos_date": returns_group["date"].max(),
                "oos_observations": int(len(returns_group)),
                "rebalance_count": int(weights_group["rebalance_date"].nunique()),
                "annualisation_factor": int(returns_group["periods_per_year"].iloc[0]),
                "solver_failures": int((diag_group["solver_status"] != "success").sum()),
                "fallback_count": int(diag_group["fallback_used"].sum()),
                "max_weight_sum_error": float((weight_sums - 1.0).abs().max()),
                "min_weight": float(weights_group["weight"].min()),
                "max_weight": float(weights_group["weight"].max()),
                "duplicate_return_dates": int(duplicate_returns),
                "missing_fund_returns": int(returns_group["return"].isna().sum()),
                "training_dates_valid": bool((diag_group["training_end_date"] < diag_group["rebalance_date"]).all()),
                "strict_no_lookahead_valid": bool(
                    (diag_group["max_training_observation_date"] < diag_group["first_live_return_date"]).all()
                ),
                "mean_risk_contribution_dispersion": float(diag_group["risk_contribution_dispersion"].mean()),
                "max_risk_contribution_dispersion": float(diag_group["risk_contribution_dispersion"].max()),
            }
        )
    return pd.DataFrame(rows).sort_values(["universe", "method"]).reset_index(drop=True)

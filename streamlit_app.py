"""SignalHarbor Streamlit app for FINS3645 Part B.

The deployed app is intentionally light: it reads precomputed CSV artifacts from
results/ and does not recompute backtests or run headline sentiment scoring.
"""
from __future__ import annotations

import pathlib

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import streamlit as st


ROOT = pathlib.Path(__file__).resolve().parent
DATA_DIR = ROOT / "results" / "data"
TABLE_DIR = ROOT / "results" / "tables"

PALETTE = {
    "ink": "#172033",
    "muted": "#607086",
    "line": "#d8dee9",
    "paper": "#fbfaf7",
    "panel": "#ffffff",
    "navy": "#17324d",
    "teal": "#0f8b8d",
    "green": "#2f9e44",
    "gold": "#f2a900",
    "red": "#c44536",
}


st.set_page_config(page_title="SignalHarbor", page_icon="SH", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: #fbfaf7;
        color: #172033;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e1e6ef;
        border-radius: 8px;
        padding: 14px 16px;
    }
    div[data-testid="stMetric"] label {
        color: #607086;
    }
    .signal-small {
        color: #607086;
        font-size: 0.92rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading precomputed fund results...")
def load_results() -> dict[str, pd.DataFrame]:
    fund_returns = pd.read_csv(DATA_DIR / "fund_returns.csv", parse_dates=["date"])
    fund_weights = pd.read_csv(DATA_DIR / "fund_weights.csv", parse_dates=["rebalance_date", "training_end_date"])
    current_holdings = pd.read_csv(DATA_DIR / "current_holdings.csv", parse_dates=["latest_rebalance_date"])
    sector_index = pd.read_csv(DATA_DIR / "sector_sentiment_index.csv", parse_dates=["date"])
    fusion_returns = pd.read_csv(DATA_DIR / "fusion_returns.csv", parse_dates=["date"])
    metrics = pd.read_csv(TABLE_DIR / "performance_metrics.csv")
    audit = pd.read_csv(TABLE_DIR / "backtest_audit.csv")
    fusion = pd.read_csv(TABLE_DIR / "fusion_comparison.csv")
    sentiment_models = pd.read_csv(TABLE_DIR / "sentiment_model_comparison.csv")
    return {
        "fund_returns": fund_returns,
        "fund_weights": fund_weights,
        "current_holdings": current_holdings,
        "sector_index": sector_index,
        "fusion_returns": fusion_returns,
        "metrics": metrics,
        "audit": audit,
        "fusion": fusion,
        "sentiment_models": sentiment_models,
    }


def format_percent(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def growth_series(returns: pd.Series) -> pd.Series:
    return (1.0 + returns.fillna(0.0)).cumprod()


def drawdown_series(growth: pd.Series) -> pd.Series:
    return growth / growth.cummax() - 1.0


def metrics_from_returns(returns: pd.Series, periods_per_year: int) -> dict[str, float]:
    returns = returns.dropna()
    if returns.empty:
        return {"return": np.nan, "vol": np.nan, "sharpe": np.nan, "max_drawdown": np.nan, "growth": np.nan}
    growth = growth_series(returns)
    ann_return = growth.iloc[-1] ** (periods_per_year / len(returns)) - 1.0
    ann_vol = returns.std(ddof=1) * np.sqrt(periods_per_year)
    daily_vol = returns.std(ddof=1)
    sharpe = returns.mean() / daily_vol * np.sqrt(periods_per_year) if daily_vol > 0 else np.nan
    return {
        "return": ann_return,
        "vol": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": drawdown_series(growth).min(),
        "growth": growth.iloc[-1],
    }


def plot_growth(df: pd.DataFrame, funds: list[str]) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 4.8), facecolor=PALETTE["paper"])
    ax.set_facecolor(PALETTE["panel"])
    colors = [PALETTE["navy"], PALETTE["teal"], PALETTE["green"], PALETTE["gold"], PALETTE["red"]]
    end_points: list[tuple[pd.Timestamp, float, str, str]] = []
    path_lows: list[float] = []
    path_highs: list[float] = []
    for color, fund in zip(colors * 4, funds):
        group = df[df["fund"] == fund].sort_values("date")
        if group.empty:
            continue
        growth = growth_series(group["return"])
        ax.plot(group["date"], growth, label=fund, linewidth=2.2, color=color)
        end_points.append((group["date"].iloc[-1], float(growth.iloc[-1]), fund, color))
        path_lows.append(float(growth.min()))
        path_highs.append(float(growth.max()))

    if end_points:
        y_values = [point[1] for point in end_points]
        endpoint_min = min(y_values)
        endpoint_max = max(y_values)
        path_min = min(path_lows) if path_lows else endpoint_min
        path_max = max(path_highs) if path_highs else endpoint_max
        y_min = min(0.95, endpoint_min, path_min)
        y_max = max(endpoint_max, path_max)
        label_gap = max((endpoint_max - endpoint_min) * 0.075, 0.14)
        label_floor = y_min + label_gap * 0.45
        label_positions: dict[str, float] = {}
        previous_y = None
        for _, value, fund, _ in sorted(end_points, key=lambda item: item[1], reverse=True):
            label_y = value if previous_y is None else min(value, previous_y - label_gap)
            label_positions[fund] = label_y
            previous_y = label_y
        lowest_label = min(label_positions.values())
        if lowest_label < label_floor:
            lift = label_floor - lowest_label
            label_positions = {fund: y + lift for fund, y in label_positions.items()}

        last_date = max(point[0] for point in end_points)
        first_date = min(df[df["fund"].isin(funds)]["date"])
        right_pad = pd.Timedelta(days=max(35, int((last_date - first_date).days * 0.07)))
        ax.set_xlim(first_date, last_date + right_pad)
        label_max = max(label_positions.values())
        label_min = min(label_positions.values())
        y_range = max(y_max - y_min, 1e-9)
        bottom_pad = max(y_range * 0.02, 0.08)
        top_pad = max(y_range * 0.04, 0.25)
        lower_limit = min(y_min - bottom_pad, label_min - label_gap)
        upper_limit = max(y_max + top_pad, label_max + label_gap)
        if path_max > 3:
            upper_limit = max(upper_limit, float(np.ceil(path_max + 0.05)))
        ax.set_ylim(lower_limit, upper_limit)
        for date, value, fund, color in end_points:
            label_y = label_positions[fund]
            if abs(label_y - value) > 0.02:
                ax.plot(
                    [date, date + pd.Timedelta(days=7)],
                    [value, label_y],
                    color=color,
                    linewidth=0.8,
                    alpha=0.45,
                )
            ax.text(
                date + pd.Timedelta(days=9),
                label_y,
                f"{fund}  ${value:.2f}",
                color=color,
                va="center",
                fontsize=8.6,
            )

    ax.set_title("Growth of $1", loc="left", fontweight="bold")
    ax.set_ylabel("Growth of $1")
    ax.set_xlabel("OOS date")
    ax.axhline(1.0, color="#b9b2a5", linewidth=1.1)
    ax.grid(True, axis="y", color=PALETTE["line"], linewidth=0.8)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend().remove()
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout()
    return fig


def plot_drawdown(df: pd.DataFrame, fund: str) -> plt.Figure:
    group = df[df["fund"] == fund].sort_values("date")
    growth = growth_series(group["return"])
    fig, ax = plt.subplots(figsize=(9, 4.2), facecolor=PALETTE["paper"])
    ax.fill_between(group["date"], drawdown_series(growth) * 100.0, 0, color=PALETTE["red"], alpha=0.22)
    ax.plot(group["date"], drawdown_series(growth) * 100.0, color=PALETTE["red"], linewidth=1.8)
    ax.set_title("Drawdown path", loc="left", fontweight="bold")
    ax.set_ylabel("Drawdown (%)")
    ax.set_xlabel("OOS date")
    ax.grid(True, axis="y", color=PALETTE["line"])
    ax.spines[["top", "right"]].set_visible(False)
    return fig


def plot_single_growth(df: pd.DataFrame, fund: str) -> plt.Figure:
    group = df[df["fund"] == fund].sort_values("date")
    growth = growth_series(group["return"])
    fig, ax = plt.subplots(figsize=(9, 4.2), facecolor=PALETTE["paper"])
    ax.plot(group["date"], growth, color=PALETTE["navy"], linewidth=2.2)
    ax.axhline(1.0, color="#b9b2a5", linewidth=1.0)
    ax.set_title("Growth of $1", loc="left", fontweight="bold")
    ax.set_ylabel("Growth of $1")
    ax.set_xlabel("OOS date")
    ax.grid(True, axis="y", color=PALETTE["line"])
    ax.spines[["top", "right"]].set_visible(False)
    return fig


def plot_sector(df: pd.DataFrame, sectors: list[str], field: str) -> plt.Figure:
    axis_labels = {
        "finance_vader_coverage_adjusted_signal_lag1": "Coverage-aware lagged z-score, 21-day average",
        "vader_coverage_adjusted_signal_lag1": "Coverage-aware lagged z-score",
        "coverage_ratio": "Coverage ratio",
        "finance_vader_score_100": "Daily sentiment index, 0-100",
        "vader_score_100": "Sentiment index, 0-100",
        "finance_vader_expanding_z": "Expanding z-score",
        "vader_expanding_z": "Expanding z-score",
        "finance_vader_rolling_21d": "Sentiment index, 0-100",
        "vader_rolling_21d": "21-day sentiment average",
    }
    chart_titles = {
        "finance_vader_coverage_adjusted_signal_lag1": "Coverage-aware sector sentiment signal",
        "coverage_ratio": "News coverage ratio",
        "finance_vader_score_100": "Daily sector sentiment index",
        "finance_vader_expanding_z": "Sector sentiment z-score",
        "finance_vader_rolling_21d": "Sector sentiment index over time",
    }
    fig, ax = plt.subplots(figsize=(9, 4.6), facecolor=PALETTE["paper"])
    colors = [PALETTE["navy"], PALETTE["teal"], PALETTE["green"], PALETTE["gold"], PALETTE["red"]]
    for color, sector in zip(colors * 3, sectors):
        group = df[df["sector"] == sector].sort_values("date")
        values = group[field]
        if field == "finance_vader_coverage_adjusted_signal_lag1":
            values = values.rolling(21, min_periods=5).mean()
        ax.plot(group["date"], values, label=sector, linewidth=1.8, color=color)
    if "score_100" in field or "rolling" in field:
        ax.axhline(50, color="#aab3c2", linewidth=1, linestyle="--")
    ax.set_title(chart_titles.get(field, "Sector sentiment"), loc="left", fontweight="bold")
    ax.set_ylabel(axis_labels.get(field, field.replace("_", " ").title()))
    ax.set_xlabel("Date")
    ax.grid(True, axis="y", color=PALETTE["line"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=min(len(sectors), 5), fontsize=8)
    return fig


def plot_weights(weights: pd.DataFrame, fund: str) -> plt.Figure:
    group = weights[weights["fund"] == fund].copy()
    latest = group[group["rebalance_date"] == group["rebalance_date"].max()].nlargest(10, "weight")["ticker"]
    plot_df = group[group["ticker"].isin(latest)].pivot_table(
        index="rebalance_date", columns="ticker", values="weight", aggfunc="sum"
    ).sort_index()
    if not plot_df.empty:
        plot_df["Other"] = (1.0 - plot_df.sum(axis=1)).clip(lower=0.0)
    fig, ax = plt.subplots(figsize=(9, 4.6), facecolor=PALETTE["paper"])
    plot_df.plot.area(ax=ax, linewidth=0.2, alpha=0.86, cmap="tab20")
    ax.set_title("Top holdings plus Other over time", loc="left", fontweight="bold")
    ax.set_ylabel("Weight")
    ax.set_xlabel("Rebalance date")
    ax.grid(True, axis="y", color=PALETTE["line"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=5, fontsize=7)
    return fig


def display_metric_row(row: pd.Series) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Annual return", format_percent(row["annualised_return"]))
    c2.metric("Volatility", format_percent(row["annualised_volatility"]))
    c3.metric("Sharpe", f"{row['sharpe_ratio']:.2f}")
    c4.metric("Max drawdown", format_percent(row["maximum_drawdown"]))
    c5.metric("Growth of $1", f"${row['growth_of_1']:.2f}")


def as_percent_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column in out.columns:
            out[column] = out[column] * 100.0
    return out


def clean_audit_summary(audit: pd.DataFrame) -> pd.DataFrame:
    out = audit.copy()
    out["OOS period"] = out["first_oos_date"].astype(str) + " to " + out["last_oos_date"].astype(str)
    return out[
        [
            "fund_name",
            "universe",
            "method",
            "OOS period",
            "oos_observations",
            "rebalance_count",
            "annualisation_factor",
            "solver_failures",
            "strict_no_lookahead_valid",
        ]
    ].rename(
        columns={
            "fund_name": "Fund",
            "universe": "Universe",
            "method": "Method",
            "oos_observations": "OOS observations",
            "rebalance_count": "Rebalances",
            "annualisation_factor": "Annualisation factor",
            "solver_failures": "Solver failures",
            "strict_no_lookahead_valid": "No-lookahead valid",
        }
    )


def clean_sentiment_models(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(
        columns={
            "sector": "Sector",
            "days": "Days",
            "mean_vader_score_100": "VADER score",
            "mean_finance_vader_score_100": "Finance-adjusted VADER score",
            "mean_finance_minus_vader": "Finance uplift",
            "correlation": "Model correlation",
            "mean_coverage_ratio": "Average coverage",
        }
    ).copy()
    if "Average coverage" in out:
        out["Average coverage"] = out["Average coverage"] * 100.0
    return out


def main() -> None:
    data = load_results()
    fund_returns = data["fund_returns"]
    fund_weights = data["fund_weights"]
    current_holdings = data["current_holdings"]
    sector_index = data["sector_index"]
    metrics = data["metrics"]
    audit = data["audit"]
    fusion = data["fusion"]

    st.title("SignalHarbor")
    st.caption("Systematic multi-asset funds with equity-sector news sentiment analytics.")

    top = metrics.sort_values("sharpe_ratio", ascending=False).iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Funds", f"{metrics['fund'].nunique()}")
    c2.metric("Best OOS Sharpe", f"{top['sharpe_ratio']:.2f}", top["fund"])
    c3.metric("OOS window", "2021-2023")
    c4.metric("Sectors", f"{sector_index['sector'].nunique()}")

    tab_explorer, tab_fact, tab_builder, tab_sentiment, tab_method = st.tabs(
        ["Fund Explorer", "Fact Sheet", "Portfolio Builder", "Sentiment Analytics", "Methodology"]
    )

    with tab_explorer:
        left, right = st.columns([1, 3])
        with left:
            universe = st.multiselect(
                "Universe",
                sorted(metrics["universe"].unique()),
                default=sorted(metrics["universe"].unique()),
            )
            method = st.multiselect(
                "Method",
                sorted(metrics["method"].unique()),
                default=sorted(metrics["method"].unique()),
            )
        filtered = metrics[metrics["universe"].isin(universe) & metrics["method"].isin(method)].copy()
        with right:
            view = filtered[
                [
                    "fund",
                    "universe",
                    "method",
                    "annualised_return",
                    "annualised_volatility",
                    "sharpe_ratio",
                    "maximum_drawdown",
                    "growth_of_1",
                    "average_turnover",
                ]
            ].sort_values("sharpe_ratio", ascending=False)
            display_view = as_percent_columns(
                view,
                ["annualised_return", "annualised_volatility", "maximum_drawdown", "average_turnover"],
            )
            st.dataframe(
                display_view,
                width="stretch",
                hide_index=True,
                column_config={
                    "annualised_return": st.column_config.NumberColumn("Annual return", format="%.2f%%"),
                    "annualised_volatility": st.column_config.NumberColumn("Volatility", format="%.2f%%"),
                    "maximum_drawdown": st.column_config.NumberColumn("Max drawdown", format="%.2f%%"),
                    "average_turnover": st.column_config.NumberColumn("Average monthly turnover", format="%.2f%%"),
                    "sharpe_ratio": st.column_config.NumberColumn("Sharpe", format="%.2f"),
                    "growth_of_1": st.column_config.NumberColumn("Growth of $1", format="$%.2f"),
                },
            )
        chart_funds = view["fund"].head(5).tolist()
        st.caption("Growth chart shows the top five displayed funds after the current filters and sorting.")
        st.pyplot(plot_growth(fund_returns, chart_funds), width="stretch")

    with tab_fact:
        fund = st.selectbox("Fund", metrics.sort_values(["universe", "method"])["fund"].tolist())
        row = metrics[metrics["fund"] == fund].iloc[0]
        display_metric_row(row)
        st.caption("All figures use submitted out-of-sample results and are not return promises.")
        c_growth, c_drawdown = st.columns(2)
        with c_growth:
            st.pyplot(plot_single_growth(fund_returns, fund), width="stretch")
        with c_drawdown:
            st.pyplot(plot_drawdown(fund_returns, fund), width="stretch")
        c1, c2 = st.columns([1.15, 0.85])
        with c1:
            st.pyplot(plot_weights(fund_weights, fund), width="stretch")
            st.caption("Other represents holdings outside the displayed top names.")
        with c2:
            holdings = current_holdings[current_holdings["fund"] == fund].copy()
            st.markdown("#### Current holdings")
            holdings_display = holdings[["ticker", "weight"]].sort_values("weight", ascending=False)
            holdings_display = as_percent_columns(holdings_display, ["weight"])
            st.dataframe(
                holdings_display,
                width="stretch",
                hide_index=True,
                column_config={"weight": st.column_config.NumberColumn("Weight", format="%.2f%%")},
            )
            audit_row = audit[audit["fund_name"] == fund].iloc[0]
            st.markdown("#### Backtest audit")
            st.dataframe(
                pd.DataFrame(
                    {
                        "Check": [
                            "Rebalances",
                            "OOS observations",
                            "Annualisation factor",
                            "Solver failures",
                            "Fallback count",
                            "No-look-ahead valid",
                            "Minimum weight",
                            "Max weight-sum error",
                        ],
                        "Value": [
                            str(int(audit_row["rebalance_count"])),
                            str(int(audit_row["oos_observations"])),
                            str(int(audit_row["annualisation_factor"])),
                            str(int(audit_row["solver_failures"])),
                            str(int(audit_row["fallback_count"])),
                            str(bool(audit_row["strict_no_lookahead_valid"])),
                            f"{audit_row['min_weight']:.4f}",
                            f"{audit_row['max_weight_sum_error']:.2e}",
                        ],
                    }
                ),
                width="stretch",
                hide_index=True,
            )

    with tab_builder:
        available = metrics.sort_values("fund")["fund"].tolist()
        selected = st.multiselect(
            "Funds",
            available,
            default=["Equity Equal Weight", "Combined Risk Parity", "Crypto Equal Weight"],
        )
        if not selected:
            st.warning("Select at least one fund.")
        else:
            raw_weights = {}
            cols = st.columns(min(3, len(selected)))
            for idx, fund in enumerate(selected):
                raw_weights[fund] = cols[idx % len(cols)].number_input(fund, min_value=0.0, max_value=100.0, value=100.0 / len(selected), step=1.0)
            total = sum(raw_weights.values())
            if total <= 0:
                st.warning("Allocation must be positive.")
            else:
                weights = {fund: value / total for fund, value in raw_weights.items()}
                pivot = fund_returns[fund_returns["fund"].isin(selected)].pivot_table(
                    index="date", columns="fund", values="return", aggfunc="sum"
                ).sort_index()
                aligned = pivot.dropna(subset=selected)
                if aligned.empty:
                    st.warning("The selected funds do not have common available return dates.")
                else:
                    selected_universes = metrics.set_index("fund").loc[selected, "universe"]
                    periods = 365 if (selected_universes == "Crypto").all() else 252
                    portfolio_returns = aligned[selected].mul(pd.Series(weights), axis=1).sum(axis=1)
                    fee_bps = st.slider(
                        "Annual management fee (bps)",
                        min_value=0,
                        max_value=200,
                        value=0,
                        step=5,
                        help="Applied as a simple daily fee drag to show net growth sensitivity.",
                    )
                    daily_fee = (fee_bps / 10000.0) / periods
                    net_returns = portfolio_returns - daily_fee
                    portfolio_metrics = metrics_from_returns(net_returns, periods)
                    st.caption(
                        "Custom portfolio metrics use common available dates across selected funds. Pure Crypto allocations use 365 annualisation; allocations containing Equity or Combined funds use 252. Net results include the selected fee drag."
                    )
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Net annual return", format_percent(portfolio_metrics["return"]))
                    c2.metric("Net volatility", format_percent(portfolio_metrics["vol"]))
                    c3.metric("Net Sharpe", f"{portfolio_metrics['sharpe']:.2f}")
                    c4.metric("Max drawdown", format_percent(portfolio_metrics["max_drawdown"]))
                    fig, ax = plt.subplots(figsize=(9, 4.5), facecolor=PALETTE["paper"])
                    ax.plot(portfolio_returns.index, growth_series(portfolio_returns), color="#aab3c2", linewidth=1.5, label="Gross")
                    ax.plot(net_returns.index, growth_series(net_returns), color=PALETTE["teal"], linewidth=2.2, label="Net")
                    ax.set_title("User allocation growth of $1", loc="left", fontweight="bold")
                    ax.set_ylabel("Growth of $1")
                    ax.set_xlabel("Date")
                    ax.grid(True, axis="y", color=PALETTE["line"])
                    ax.spines[["top", "right"]].set_visible(False)
                    ax.legend(frameon=False)
                    st.pyplot(fig, width="stretch")
                    st.dataframe(
                        as_percent_columns(
                            pd.DataFrame({"fund": list(weights.keys()), "normalised_weight": list(weights.values())}),
                            ["normalised_weight"],
                        ),
                        width="stretch",
                        hide_index=True,
                        column_config={"normalised_weight": st.column_config.NumberColumn("Allocation", format="%.2f%%")},
                    )
                    st.caption("Displayed allocations are normalised from the inputs above and sum to 100%; small differences can appear from rounding.")

    with tab_sentiment:
        selected_sector = st.selectbox(
            "Sector",
            sorted(sector_index["sector"].unique()),
            index=sorted(sector_index["sector"].unique()).index("Tech") if "Tech" in sorted(sector_index["sector"].unique()) else 0,
        )
        series_options = {
            "Coverage-aware lagged trading signal": "finance_vader_coverage_adjusted_signal_lag1",
            "Sentiment display index, 0-100": "finance_vader_rolling_21d",
        }
        field = st.selectbox(
            "Sentiment series",
            list(series_options.keys()),
            index=0,
        )
        selected_field = series_options[field]
        st.pyplot(plot_sector(sector_index, [selected_sector], selected_field), width="stretch")
        st.caption(
            "The coverage-aware signal is lagged before trading and scaled by prior news coverage. The 0-100 index is for investor display only. Both views use a 21-day average for readability."
        )
        with st.expander("Compare sectors with the same selected view"):
            compare_sectors = st.multiselect(
                "Sectors to compare",
                sorted(sector_index["sector"].unique()),
                default=["Tech", "Financials", "Energy", "Healthcare", "Consumer"],
            )
            if compare_sectors:
                st.pyplot(plot_sector(sector_index, compare_sectors, selected_field), width="stretch")
                st.caption("Multiple sectors are shown with a 21-day average for readability.")
        c1, c2 = st.columns([1, 1])
        with c1:
            latest = sector_index.sort_values("date").groupby("sector").tail(1)
            latest_view = latest[["sector", "finance_vader_score_100", "finance_vader_expanding_z", "coverage_ratio", "active_tickers"]].sort_values(
                    "finance_vader_expanding_z", ascending=False
                )
            latest_view = as_percent_columns(latest_view, ["coverage_ratio"])
            latest_view = latest_view.rename(
                columns={
                    "sector": "Sector",
                    "finance_vader_score_100": "Score 0-100",
                    "finance_vader_expanding_z": "Expanding z",
                    "coverage_ratio": "Coverage",
                    "active_tickers": "Active tickers",
                }
            )
            st.dataframe(
                latest_view,
                width="stretch",
                hide_index=True,
                column_config={
                    "Score 0-100": st.column_config.NumberColumn("Score 0-100", format="%.1f"),
                    "Expanding z": st.column_config.NumberColumn("Expanding z", format="%.2f"),
                    "Coverage": st.column_config.NumberColumn("Coverage", format="%.0f%%"),
                },
            )
        with c2:
            st.dataframe(
                clean_sentiment_models(data["sentiment_models"]),
                width="stretch",
                hide_index=True,
                column_config={
                    "VADER score": st.column_config.NumberColumn("VADER score", format="%.2f"),
                    "Finance-adjusted VADER score": st.column_config.NumberColumn("Finance-adjusted VADER score", format="%.2f"),
                    "Finance uplift": st.column_config.NumberColumn("Finance uplift", format="%.2f"),
                    "Model correlation": st.column_config.NumberColumn("Model correlation", format="%.2f"),
                    "Average coverage": st.column_config.NumberColumn("Average coverage", format="%.1f%%"),
                },
            )
        st.markdown("#### Sentiment fusion")
        fusion_view = as_percent_columns(
            fusion[["fund", "experiment", "annualised_return", "annualised_volatility", "sharpe_ratio", "maximum_drawdown", "average_turnover"]],
            ["annualised_return", "annualised_volatility", "maximum_drawdown", "average_turnover"],
        )
        fusion_view["experiment"] = fusion_view["experiment"].replace(
            {"base": "Base", "sentiment_augmented": "Sentiment fusion"}
        )
        st.dataframe(
            fusion_view,
            width="stretch",
            hide_index=True,
            column_config={
                "annualised_return": st.column_config.NumberColumn("Annual return", format="%.2f%%"),
                "annualised_volatility": st.column_config.NumberColumn("Volatility", format="%.2f%%"),
                "maximum_drawdown": st.column_config.NumberColumn("Max drawdown", format="%.2f%%"),
                "average_turnover": st.column_config.NumberColumn("Average monthly turnover", format="%.2f%%"),
                "sharpe_ratio": st.column_config.NumberColumn("Sharpe", format="%.2f"),
                "experiment": st.column_config.TextColumn("Experiment"),
            },
        )

    with tab_method:
        st.markdown(
            """
            #### Funds and backtest design
            SignalHarbor evaluates 12 funds from three universes and four portfolio methods. The backtest uses an expanding estimation window,
            monthly rebalancing, long-only weights, full investment, zero risk-free rate, and zero baseline transaction costs.

            #### Calendar treatment
            Equity and Combined funds use the equity trading calendar and a 252 annualisation factor. Crypto funds trade on the crypto calendar
            and use a 365 annualisation factor. Combined funds first compute crypto returns on the crypto calendar, then align those returns to
            equity trading days.

            #### Sentiment model
            Headlines are scored with VADER and a finance-extended VADER dictionary. The 0-100 sector sentiment index is a display measure for
            investor interpretation. The coverage ratio records how many tickers in a sector have observed news on a given day. The trading signal
            is the one-day-lagged sector z-score scaled by the prior coverage ratio, so sparse-news signals have less influence. Sentiment is used
            only for equity funds.

            #### Investor warning
            Results are historical out-of-sample backtests, not return promises. The sentiment tilt is transparent and look-ahead safe, but in this
            sample it slightly reduces Sharpe versus the base equity funds.
            """
        )
        st.dataframe(clean_audit_summary(audit), width="stretch", hide_index=True)
        with st.expander("Show full technical audit table"):
            st.dataframe(audit, width="stretch", hide_index=True)


if __name__ == "__main__":
    main()

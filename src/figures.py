"""Reporting figures for the Part B evidence pack."""
from __future__ import annotations

import pathlib

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm
from matplotlib.patches import Patch, Rectangle
import numpy as np
import pandas as pd


PALETTE = {
    "navy": "#0f5499",
    "teal": "#00847e",
    "green": "#789a3d",
    "gold": "#f2a900",
    "red": "#c7533c",
    "purple": "#6c5ce7",
    "slate": "#6f6f6f",
    "ink": "#262a33",
    "grid": "#d8d0c3",
    "paper": "#fff1e5",
}


def _style_axes(ax: plt.Axes, title: str, ylabel: str | None = None) -> None:
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color=PALETTE["ink"], pad=12)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", color=PALETTE["grid"], linewidth=0.8, alpha=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#b8c0cc")
    ax.spines["bottom"].set_color("#b8c0cc")


def _save(fig: plt.Figure, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def _growth_index(returns: pd.Series) -> pd.Series:
    return (1.0 + returns.fillna(0.0)).cumprod()


def _drawdown(growth: pd.Series) -> pd.Series:
    return growth / growth.cummax() - 1.0


def _format_growth_tick(value: float, _pos: int) -> str:
    if value >= 10:
        return f"{value:.0f}"
    if value >= 1:
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{value:.1f}"


def _spread_endpoint_labels(values: pd.Series, min_gap: float = 0.09) -> dict[str, float]:
    """Return endpoint label y-positions with small vertical separation."""
    ordered = values.sort_values()
    adjusted: dict[str, float] = {}
    last_value = -np.inf
    for label, value in ordered.items():
        label_value = float(value)
        if label_value - last_value < min_gap:
            label_value = last_value + min_gap
        adjusted[label] = label_value
        last_value = label_value
    return adjusted


def plot_growth_comparison(fund_returns: pd.DataFrame, path: pathlib.Path) -> None:
    df = fund_returns.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["fund", "date"])
    df["growth_1"] = df.groupby("fund", sort=False)["return"].transform(lambda r: (1.0 + r.fillna(0.0)).cumprod())

    method_colors = {
        "Equal Weight": "#1f5f99",
        "Minimum Variance": "#7a9942",
        "Risk Parity": "#00847e",
        "Tangency": "#c7533c",
    }
    method_order = ["Equal Weight", "Minimum Variance", "Risk Parity", "Tangency"]
    # Keep the warm, restrained Financial Times-inspired report treatment used
    # across the evidence pack while leaving the plotting field uncluttered.
    fig_bg = PALETTE["paper"]
    ax_bg = "#fffdf9"
    grid = "#d8d0c3"
    spine = "#b8b0a4"
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.titleweight": "bold",
        "axes.labelcolor": PALETTE["ink"],
        "xtick.color": PALETTE["ink"],
        "ytick.color": PALETTE["ink"],
    })
    fig, axes = plt.subplots(3, 1, figsize=(11.2, 7.65), facecolor=fig_bg, sharex=False)
    fig.subplots_adjust(left=0.10, right=0.86, top=0.90, bottom=0.14, hspace=0.52)

    universes = ["Equity", "Combined", "Crypto"]
    panel_titles = {
        "Equity": "Equity funds",
        "Combined": "Combined funds",
        "Crypto": "Crypto funds",
    }
    for ax, universe in zip(axes, universes):
        panel = df[df["universe"] == universe].copy()
        last_date = panel["date"].max()
        terminal_values = {}
        for method in method_order:
            group = panel[panel["method"] == method].sort_values("date")
            if group.empty:
                continue
            color = method_colors.get(method, PALETTE["slate"])
            ax.plot(group["date"], group["growth_1"], color=color, linewidth=1.75, label=method)
            terminal_values[method] = group["growth_1"].iloc[-1]

        min_gap = 0.09 if universe != "Crypto" else 0.45
        label_y = _spread_endpoint_labels(pd.Series(terminal_values), min_gap=min_gap)
        for method in method_order:
            group = panel[panel["method"] == method].sort_values("date")
            if group.empty:
                continue
            color = method_colors.get(method, PALETTE["slate"])
            ax.annotate(
                f"{method}  {group['growth_1'].iloc[-1]:.2f}",
                xy=(group["date"].iloc[-1], group["growth_1"].iloc[-1]),
                # Keep the time axis at the actual last OOS observation while
                # placing readable endpoint labels in the right-hand margin.
                xytext=(8, label_y[method]),
                textcoords=("offset points", "data"),
                va="center",
                fontsize=8.0,
                color=color,
                arrowprops=dict(arrowstyle="-", color=color, linewidth=0.65, shrinkA=0, shrinkB=0),
                annotation_clip=False,
            )

        ax.axhline(1.0, color="#b6afa5", linewidth=0.85)
        ax.set_facecolor(ax_bg)
        ax.grid(True, axis="y", color=grid, linewidth=0.65, alpha=0.78)
        ax.grid(False, axis="x")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(spine)
        ax.spines["bottom"].set_color(spine)
        ax.tick_params(axis="both", labelsize=8.4, length=3)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_format_growth_tick))
        ax.set_ylabel("Growth of $1", fontsize=9.2)
        ax.set_xlim(panel["date"].min(), last_date)
        ymax = max(panel["growth_1"].max(), max(label_y.values())) * 1.10
        ymax = max(ymax, 1.35)
        ymin = min(0.88, panel["growth_1"].min() * 0.96)
        ax.set_ylim(ymin, ymax)
        # Include the actual first live observation as a labelled 2021-01 tick
        # for every panel, including Equity and Combined (which begin on 4 Jan).
        regular_ticks = pd.date_range("2021-01-01", "2023-12-31", freq="4MS")
        tick_dates = [panel["date"].min()]
        tick_dates.extend(
            tick for tick in regular_ticks
            if panel["date"].min() < tick <= last_date
        )
        ax.set_xticks(tick_dates)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.set_title(panel_titles[universe], loc="left", fontsize=10.8, fontweight="bold", color=PALETTE["ink"], pad=7)
        ax.set_xlabel("OOS date", fontsize=9.2, labelpad=4)

    fig.suptitle(
        "Growth of $1 by fund universe, 2021–2023",
        x=0.02,
        y=0.975,
        ha="left",
        fontsize=15.2,
        fontweight="bold",
        color=PALETTE["ink"],
    )
    fig.text(
        0.02,
        0.01,
        "Source: SignalHarbor analysis of results/data/fund_returns.csv.",
        fontsize=8.5,
        fontstyle="italic",
        color=PALETTE["slate"],
    )
    _save(fig, path)


def plot_drawdown_comparison(fund_returns: pd.DataFrame, path: pathlib.Path) -> None:
    selected = [
        "Equity Equal Weight",
        "Equity Tangency",
        "Combined Equal Weight",
        "Combined Tangency",
        "Combined Risk Parity",
    ]
    df = fund_returns[fund_returns["fund"].isin(selected)].copy()
    df["date"] = pd.to_datetime(df["date"])

    fund_colors = {
        "Equity Equal Weight": PALETTE["navy"],
        "Equity Tangency": PALETTE["red"],
        "Combined Equal Weight": PALETTE["teal"],
        "Combined Tangency": PALETTE["gold"],
        "Combined Risk Parity": PALETTE["green"],
    }
    fig, ax = plt.subplots(figsize=(10.8, 5.6), facecolor=PALETTE["paper"])
    fig.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.20)
    for fund in selected:
        group = df[df["fund"] == fund].sort_values("date")
        if group.empty:
            continue
        group = group.sort_values("date")
        dd = _drawdown(_growth_index(group["return"]))
        ax.plot(
            group["date"],
            dd * 100.0,
            label=fund,
            linewidth=1.8,
            color=fund_colors[fund],
            linestyle="-",
        )

    first_date = df["date"].min()
    last_date = df["date"].max()
    regular_ticks = pd.date_range("2021-01-01", "2023-12-31", freq="4MS")
    tick_dates = [first_date] + [tick for tick in regular_ticks if first_date < tick <= last_date]

    ax.set_facecolor("#fffdf9")
    ax.axhline(0, color="#9c968d", linewidth=0.95, zorder=2)
    ax.grid(True, axis="y", color=PALETTE["grid"], linewidth=0.65, alpha=0.78, zorder=0)
    ax.grid(False, axis="x")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#b8b0a4")
    ax.spines["bottom"].set_color("#b8b0a4")
    ax.tick_params(axis="both", labelsize=8.6, length=3, color="#67615a")
    ax.set_title(
        "Tangency experienced the deepest drawdowns in the Equity and Combined funds",
        loc="left",
        fontsize=12.4,
        fontweight="bold",
        color=PALETTE["ink"],
        pad=9,
    )
    ax.set_ylabel("Drawdown from prior peak (%)", fontsize=9.2)
    ax.set_xlabel("OOS date", fontsize=9.2, labelpad=4)
    ax.set_xlim(first_date, last_date)
    ax.set_xticks(tick_dates)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.legend(
        frameon=False,
        ncol=2,
        fontsize=8.1,
        loc="lower left",
        handlelength=2.0,
        columnspacing=1.5,
    )
    fig.text(
        0.10,
        0.055,
        "Source: results/data/fund_returns.csv.",
        fontsize=8.5,
        fontstyle="italic",
        color=PALETTE["slate"],
    )
    _save(fig, path)


def plot_return_risk(fund_metrics: pd.DataFrame, path: pathlib.Path) -> None:
    df = fund_metrics.copy()
    markers = {"Equity": "o", "Crypto": "s", "Combined": "^"}
    colors = {
        "Equal Weight": PALETTE["navy"],
        "Minimum Variance": PALETTE["green"],
        "Tangency": PALETTE["gold"],
        "Risk Parity": PALETTE["teal"],
    }

    fig, ax = plt.subplots(figsize=(10.5, 6), facecolor=PALETTE["paper"])
    for _, row in df.iterrows():
        ax.scatter(
            row["annualised_volatility"] * 100.0,
            row["annualised_return"] * 100.0,
            s=95,
            marker=markers.get(row["universe"], "o"),
            color=colors.get(row["method"], PALETTE["slate"]),
            edgecolor="white",
            linewidth=0.8,
            alpha=0.92,
        )
        ax.annotate(row["fund"].replace("Minimum Variance", "Min Var"), 
                    (row["annualised_volatility"] * 100.0, row["annualised_return"] * 100.0),
                    xytext=(5, 4), textcoords="offset points", fontsize=7.8, color=PALETTE["ink"])

    _style_axes(ax, "Return vs risk: 12 OOS funds", "Annualised return (%)")
    ax.set_xlabel("Annualised volatility (%)")
    ax.text(0, -0.16, "Source: results/tables/performance_metrics.csv.\nColour identifies method; marker shape identifies universe. Annualisation uses 252 for equity/combined and 365 for crypto.",
            transform=ax.transAxes, fontsize=9, color=PALETTE["slate"], linespacing=1.35)
    _save(fig, path)


def plot_sharpe_by_fund(fund_metrics: pd.DataFrame, path: pathlib.Path) -> None:
    df = fund_metrics.sort_values("sharpe_ratio", ascending=True).copy()
    universe_colors = {
        "Equity": PALETTE["navy"],
        "Crypto": PALETTE["gold"],
        "Combined": PALETTE["teal"],
    }
    colors = df["universe"].map(universe_colors).fillna(PALETTE["slate"])
    median_sharpe = df["sharpe_ratio"].median()

    fig, ax = plt.subplots(figsize=(10, 6.5), facecolor=PALETTE["paper"])
    ax.barh(df["fund"], df["sharpe_ratio"], color=colors, alpha=0.92, zorder=3)
    ax.axvline(
        median_sharpe,
        color="#5f6672",
        linewidth=1.2,
        linestyle=(0, (4, 4)),
        alpha=0.74,
        zorder=1,
    )
    ax.text(
        median_sharpe,
        0.985,
        f"Median {median_sharpe:.2f}",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        fontsize=8.5,
        color=PALETTE["slate"],
        bbox=dict(facecolor="#fffaf2", edgecolor="none", pad=1.5, alpha=0.9),
    )
    _style_axes(ax, "Equal Weight and Risk Parity led OOS Sharpe, while Tangency was weaker", "Sharpe ratio")
    ax.set_axisbelow(True)
    ax.grid(False, axis="y")
    ax.grid(True, axis="x", color=PALETTE["grid"], linewidth=0.7, alpha=0.45, zorder=0)
    ax.set_xlabel("Sharpe ratio")
    ax.set_ylabel("")
    for y, row in enumerate(df.itertuples(index=False)):
        value = row.sharpe_ratio
        if 0 < median_sharpe - value < 0.06:
            offset = -1 if row.fund == "Crypto Minimum Variance" else 1
            ax.annotate(
                f"{value:.2f}",
                xy=(value, y),
                xytext=(offset, 0),
                textcoords="offset points",
                ha="left",
                va="center",
                fontsize=8.5,
                color=PALETTE["ink"],
                zorder=4,
            )
            continue
        else:
            x_pos = value + 0.015
            ha = "left"
            label_color = PALETTE["ink"]
        ax.text(x_pos, y, f"{value:.2f}", ha=ha, va="center", fontsize=8.5, color=label_color, zorder=4)
    ax.set_xlim(0, max(0.9, df["sharpe_ratio"].max() + 0.12))
    legend_handles = [Patch(facecolor=color, label=universe) for universe, color in universe_colors.items()]
    ax.legend(handles=legend_handles, frameon=False, ncol=3, fontsize=8.5, loc="lower right")
    ax.text(0, -0.14, "Source: results/tables/performance_metrics.csv.\nFunds are ranked by OOS Sharpe; higher values indicate better return per unit of volatility. Dashed line shows the median fund.",
            transform=ax.transAxes, fontsize=9, color=PALETTE["slate"], linespacing=1.35)
    _save(fig, path)


def plot_combined_weights_over_time(fund_weights: pd.DataFrame, path: pathlib.Path) -> None:
    methods = ["Equal Weight", "Minimum Variance", "Tangency", "Risk Parity"]
    df = fund_weights[fund_weights["universe"] == "Combined"].copy()
    df["rebalance_date"] = pd.to_datetime(df["rebalance_date"])

    present = set(df["method"].unique())
    missing = set(methods) - present
    if missing:
        raise ValueError(f"Missing Combined methods in fund_weights.csv: {sorted(missing)}")

    date_sums = df.groupby(["method", "rebalance_date"])["weight"].sum()
    max_sum_error = float((date_sums - 1.0).abs().max())
    if max_sum_error > 1e-8:
        raise ValueError(f"Combined weights do not sum to one; maximum error: {max_sum_error:.3e}")

    # Map the 50 equity names to their course-provided sectors; crypto remains a single sleeve.
    sector_path = path.parents[2] / "results" / "data" / "equity_returns.csv"
    sector_map = (
        pd.read_csv(sector_path, usecols=["ticker", "sector"])
        .dropna(subset=["ticker", "sector"])
        .drop_duplicates(subset="ticker")
    )
    df = df.merge(sector_map, on="ticker", how="left", validate="many_to_one")
    crypto_mask = df["ticker"].astype(str).str.endswith("-USD")
    if df.loc[~crypto_mask, "sector"].isna().any():
        missing_tickers = sorted(df.loc[~crypto_mask & df["sector"].isna(), "ticker"].unique())
        raise ValueError(f"Missing sector mapping for Combined equity tickers: {missing_tickers}")
    df["category"] = np.where(crypto_mask, "Crypto", df["sector"])

    category_order = [
        "Consumer", "Comm", "Energy", "Financials", "Healthcare", "Industrials",
        "Materials", "RealEstate", "Tech", "Utilities", "Crypto",
    ]
    category_labels = {
        "Consumer": "Consumer", "Comm": "Communication", "Energy": "Energy",
        "Financials": "Financials", "Healthcare": "Healthcare", "Industrials": "Industrials",
        "Materials": "Materials", "RealEstate": "Real Estate", "Tech": "Technology",
        "Utilities": "Utilities", "Crypto": "Crypto",
    }
    # Week 10 presents Crypto as one distinct dark sleeve.  The other colours
    # identify the equity sectors consistently across all method panels.
    category_colors = {
        "Consumer": "#b21f52", "Comm": "#d6577d", "Energy": "#f2a900",
        "Financials": "#776f9a", "Healthcare": "#5c89b4", "Industrials": "#8b6a2c",
        "Materials": "#b8894b", "RealEstate": "#b9b5ad", "Tech": "#16867d",
        "Utilities": "#8a9845", "Crypto": PALETTE["ink"],
    }
    category_weights = (
        df.groupby(["method", "rebalance_date", "category"], as_index=False)["weight"]
        .sum()
    )
    category_sums = category_weights.groupby(["method", "rebalance_date"])["weight"].sum()
    if float((category_sums - 1.0).abs().max()) > 1e-8:
        raise ValueError("Sector and Crypto aggregation does not preserve the weight total.")

    fig, axes = plt.subplots(4, 1, figsize=(12.8, 10.4), sharex=True, sharey=True, facecolor=PALETTE["paper"])
    for ax, method in zip(axes, methods, strict=True):
        weights = (
            category_weights[category_weights["method"] == method]
            .pivot(index="rebalance_date", columns="category", values="weight")
            .reindex(columns=category_order, fill_value=0.0)
            .fillna(0.0)
            .sort_index()
        )
        ax.stackplot(
            weights.index,
            *(weights[category].to_numpy() * 100.0 for category in category_order),
            colors=[category_colors[category] for category in category_order],
            linewidth=0.35,
            edgecolor="#fffdf9",
        )
        ax.set_title(method, loc="left", fontsize=11.3, fontweight="bold", color=PALETTE["ink"], pad=5)
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100, decimals=0))
        ax.set_ylabel("Target weight", fontsize=8.8)
        ax.set_facecolor("#fffdf9")
        ax.set_axisbelow(True)
        ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.6, alpha=0.75)
        ax.grid(False, axis="x")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#b8c0cc")
        ax.spines["bottom"].set_color("#b8c0cc")
        ax.tick_params(axis="both", labelsize=8, length=3, color="#67615a")

    first_date = pd.Timestamp(category_weights["rebalance_date"].min())
    x_ticks = [first_date, *pd.date_range("2021-07-01", "2023-07-01", freq="6MS")]
    axes[-1].set_xticks(x_ticks)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    axes[-1].set_xlim(first_date, pd.Timestamp(category_weights["rebalance_date"].max()))
    axes[-1].set_xlabel("Rebalance date", fontsize=9.2, labelpad=6)

    legend_handles = [
        Patch(facecolor=category_colors[category], label=category_labels[category])
        for category in category_order
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.948),
        ncol=6,
        frameon=False,
        fontsize=8.0,
        handlelength=1.2,
        columnspacing=1.1,
    )
    fig.suptitle(
        "Combined fund sector weights by method, 2021–2023",
        x=0.02,
        y=0.99,
        ha="left",
        fontsize=16,
        fontweight="bold",
        color=PALETTE["ink"],
    )
    fig.text(
        0.02,
        0.012,
        "Source: SignalHarbor analysis of results/data/fund_weights.csv; monthly OOS target weights.",
        fontsize=8.8,
        fontstyle="italic",
        color=PALETTE["slate"],
    )
    fig.subplots_adjust(left=0.10, right=0.985, top=0.88, bottom=0.075, hspace=0.26)
    _save(fig, path)


def plot_sector_sentiment(sector_index: pd.DataFrame, path: pathlib.Path) -> None:
    df = sector_index.copy()
    df["date"] = pd.to_datetime(df["date"])
    signal_col = "finance_vader_coverage_adjusted_signal_lag1"
    df = df.dropna(subset=[signal_col]).sort_values(["sector", "date"])
    df["plot_signal"] = (
        df.groupby("sector", sort=False)[signal_col]
        .transform(lambda s: s.rolling(21, min_periods=5).mean())
    )
    df = df.dropna(subset=["plot_signal"])

    sector_order = [
        "Consumer", "Tech", "Financials", "Energy", "Healthcare",
        "Comm", "Industrials", "Utilities", "RealEstate", "Materials",
    ]
    sector_order = [sector for sector in sector_order if sector in set(df["sector"])]
    sector_labels = {"RealEstate": "Real Estate", "Comm": "Communication"}
    color = PALETTE["teal"]

    y_limit = float(np.nanmax(np.abs(df["plot_signal"])))
    y_limit = max(0.8, np.ceil(y_limit * 10) / 10)
    start_date = df["date"].min()
    end_date = df["date"].max()

    fig, axes = plt.subplots(2, 5, figsize=(12.6, 6.6), sharex=True, sharey=True, facecolor=PALETTE["paper"])
    axes_flat = axes.ravel()
    for ax, sector in zip(axes_flat, sector_order):
        group = df[df["sector"] == sector]
        ax.set_facecolor("#fffdf9")
        ax.plot(group["date"], group["plot_signal"], color=color, linewidth=1.35)
        ax.axhline(0, color="#9e9589", linewidth=0.8)
        ax.set_title(sector_labels.get(sector, sector), loc="left", fontsize=10, fontweight="bold", color=PALETTE["ink"], pad=5)
        ax.set_ylim(-y_limit, y_limit)
        ax.set_xlim(start_date, end_date)
        ax.grid(True, axis="y", color=PALETTE["grid"], linewidth=0.55, alpha=0.55)
        ax.grid(False, axis="x")
        ax.tick_params(axis="both", labelsize=7.8, length=3)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#b8b0a4")
        ax.spines["bottom"].set_color("#b8b0a4")

    for ax in axes_flat[len(sector_order):]:
        ax.axis("off")

    for ax in axes[:, 0]:
        ax.set_ylabel("Signal")
    for ax in axes[-1, :]:
        ax.set_xlabel("Date")

    fig.suptitle(
        "Coverage-aware sector sentiment signals, 2020–2023",
        x=0.02,
        y=0.985,
        ha="left",
        fontsize=16,
        fontweight="bold",
        color=PALETTE["ink"],
    )
    fig.text(
        0.02,
        0.016,
        "Source: results/data/sector_sentiment_index.csv.\n"
        "Signal equals one-day-lagged sector sentiment z-score scaled by prior news coverage ratio; 21-day averages shown for readability.",
        fontsize=8.8,
        color=PALETTE["slate"],
        linespacing=1.32,
    )
    fig.subplots_adjust(left=0.07, right=0.99, top=0.88, bottom=0.16, hspace=0.34, wspace=0.18)
    _save(fig, path)


def plot_sector_sentiment_index(sector_index: pd.DataFrame, path: pathlib.Path) -> None:
    """Plot the investor-facing 0-100 sector sentiment index."""
    df = sector_index.copy()
    df["date"] = pd.to_datetime(df["date"])
    score_col = "finance_vader_score_100"
    df = df.dropna(subset=[score_col]).sort_values(["sector", "date"])
    df["plot_score"] = df.groupby("sector", sort=False)[score_col].transform(
        lambda s: s.rolling(21, min_periods=5).mean()
    )
    df = df.dropna(subset=["plot_score"])

    sector_order = [
        "Consumer", "Tech", "Financials", "Energy", "Healthcare",
        "Comm", "Industrials", "Utilities", "RealEstate", "Materials",
    ]
    sector_order = [sector for sector in sector_order if sector in set(df["sector"])]
    sector_labels = {"RealEstate": "Real Estate", "Comm": "Communication"}
    start_date = df["date"].min()
    end_date = df["date"].max()

    fig, axes = plt.subplots(
        2, 5, figsize=(12.6, 6.6), sharex=True, sharey=True,
        facecolor=PALETTE["paper"],
    )
    axes_flat = axes.ravel()
    for ax, sector in zip(axes_flat, sector_order):
        group = df[df["sector"] == sector]
        ax.set_facecolor("#fffdf9")
        ax.plot(group["date"], group["plot_score"], color=PALETTE["navy"], linewidth=1.35)
        ax.axhline(50, color="#9e9589", linewidth=0.8, linestyle="--")
        ax.set_title(
            sector_labels.get(sector, sector), loc="left", fontsize=10,
            fontweight="bold", color=PALETTE["ink"], pad=5,
        )
        ax.set_ylim(0, 100)
        ax.set_xlim(start_date, end_date)
        ax.grid(True, axis="y", color=PALETTE["grid"], linewidth=0.55, alpha=0.55)
        ax.grid(False, axis="x")
        ax.tick_params(axis="both", labelsize=7.8, length=3)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#b8b0a4")
        ax.spines["bottom"].set_color("#b8b0a4")

    for ax in axes_flat[len(sector_order):]:
        ax.axis("off")
    for ax in axes[:, 0]:
        ax.set_ylabel("Sentiment index, 0–100")
    for ax in axes[-1, :]:
        ax.set_xlabel("Date")

    fig.suptitle(
        "Sector sentiment index over time",
        x=0.02, y=0.985, ha="left", fontsize=16,
        fontweight="bold", color=PALETTE["ink"],
    )
    fig.text(
        0.02, 0.016,
        "Source: results/data/sector_sentiment_index.csv.\n"
        "Finance-augmented VADER index; 21-day averages shown for readability. "
        "The index is for investor display, not the trading rule.",
        fontsize=8.8, color=PALETTE["slate"], linespacing=1.32,
    )
    fig.subplots_adjust(left=0.10, right=0.99, top=0.88, bottom=0.16, hspace=0.34, wspace=0.18)
    _save(fig, path)


def plot_fusion_before_after(fusion_comparison: pd.DataFrame, path: pathlib.Path) -> None:
    df = fusion_comparison.copy()
    df["pair"] = np.where(df["fund"].str.contains("Risk Parity"), "Risk Parity", "Equal Weight")
    df["label"] = np.where(df["experiment"] == "base", "Base", "Sentiment Fusion")
    order = ["Equal Weight", "Risk Parity"]
    base = df[df["label"] == "Base"].set_index("pair").loc[order]
    tilted = df[df["label"] == "Sentiment Fusion"].set_index("pair").loc[order]

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.labelcolor": PALETTE["ink"],
        "xtick.color": PALETTE["ink"],
        "ytick.color": PALETTE["ink"],
    })
    metric_specs = [
        ("annualised_return", "Annual return", True, "Higher is better"),
        ("annualised_volatility", "Annual volatility", True, "Lower is better"),
        ("sharpe_ratio", "Sharpe ratio", False, "Higher is better"),
        ("maximum_drawdown", "Max drawdown loss", True, "Lower is better"),
        ("average_turnover", "Average monthly turnover", True, "Lower is better"),
    ]
    plot_data: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for column, _, is_percent, _ in metric_specs:
        before = base[column].to_numpy(dtype=float)
        after = tilted[column].to_numpy(dtype=float)
        if column == "maximum_drawdown":
            before = np.abs(before)
            after = np.abs(after)
        if is_percent:
            before = before * 100.0
            after = after * 100.0
        plot_data[column] = before, after

    fig, axes = plt.subplots(1, 5, figsize=(13.4, 5.0), facecolor=PALETTE["paper"])
    fig.subplots_adjust(left=0.055, right=0.99, top=0.72, bottom=0.23, wspace=0.34)
    x = np.arange(len(order))
    width = 0.34
    base_color = PALETTE["navy"]
    fusion_color = PALETTE["gold"]

    for ax, (column, title, is_percent, note) in zip(axes, metric_specs):
        before, after = plot_data[column]
        ax.set_facecolor("#fffdf9")
        bars_base = ax.bar(x - width / 2, before, width=width, color=base_color, label="Base", zorder=3)
        bars_fusion = ax.bar(x + width / 2, after, width=width, color=fusion_color, label="Sentiment Fusion", zorder=3)
        ax.set_title(title, loc="left", fontsize=9.8, fontweight="bold", color=PALETTE["ink"], pad=20)
        ax.text(0, 1.015, note, transform=ax.transAxes, ha="left", va="bottom", fontsize=7.1, color=PALETTE["slate"])
        ax.set_xticks(x, order, rotation=0, ha="center")
        ymax = max(float(np.nanmax(before)), float(np.nanmax(after)))
        ax.set_ylim(0, ymax * 1.30 if ymax > 0 else 1)
        ax.grid(True, axis="y", color=PALETTE["grid"], linewidth=0.6, alpha=0.58, zorder=0)
        ax.grid(False, axis="x")
        ax.tick_params(axis="both", labelsize=7.6)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#b8b0a4")
        ax.spines["bottom"].set_color("#b8b0a4")

        for bars in (bars_base, bars_fusion):
            for bar in bars:
                value = bar.get_height()
                if column == "sharpe_ratio":
                    label = f"{value:.3f}"
                else:
                    label = f"{value:.1f}%"
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    value + ymax * 0.035,
                    label,
                    ha="center",
                    va="bottom",
                    fontsize=7.0,
                    color=PALETTE["ink"],
                    rotation=0,
                )

    handles = [
        Patch(facecolor=base_color, edgecolor="none", label="Base"),
        Patch(facecolor=fusion_color, edgecolor="none", label="Sentiment Fusion"),
    ]
    fig.legend(
        handles=handles,
        loc="upper right",
        bbox_to_anchor=(0.985, 0.875),
        frameon=False,
        fontsize=9,
        ncol=2,
        handlelength=1.6,
        columnspacing=1.1,
    )
    fig.suptitle(
        "Performance impact of the equity sentiment fusion overlay",
        x=0.02,
        y=0.955,
        ha="left",
        fontsize=15.0,
        fontweight="bold",
        color=PALETTE["ink"],
    )
    fig.text(
        0.02,
        0.055,
        "Source: SignalHarbor analysis of results/data/fusion_returns.csv. OOS period 2021-2023.",
        ha="left",
        va="center",
        fontsize=8.8,
        color=PALETTE["slate"],
    )
    _save(fig, path)


def build_all_figures(
    root: pathlib.Path,
    fund_returns: pd.DataFrame,
    fund_weights: pd.DataFrame,
    fund_metrics: pd.DataFrame,
    sector_index: pd.DataFrame,
    fusion_comparison: pd.DataFrame,
) -> None:
    figures_dir = root / "results" / "figures"
    plot_growth_comparison(fund_returns, figures_dir / "growth_of_1_comparison.png")
    plot_drawdown_comparison(fund_returns, figures_dir / "drawdown_comparison.png")
    plot_return_risk(fund_metrics, figures_dir / "return_vs_risk_funds.png")
    plot_sharpe_by_fund(fund_metrics, figures_dir / "sharpe_by_fund.png")
    plot_combined_weights_over_time(fund_weights, figures_dir / "combined_risk_parity_weights.png")
    plot_sector_sentiment_index(sector_index, figures_dir / "sector_sentiment_index_timeseries.png")
    plot_sector_sentiment(sector_index, figures_dir / "sector_sentiment_timeseries.png")
    plot_fusion_before_after(fusion_comparison, figures_dir / "fusion_before_after_sharpe.png")

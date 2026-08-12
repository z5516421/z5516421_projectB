# AGENTS.md - Agent Instructions for FINS3645 Part B

This file records the project-specific instructions I gave my AI coding assistant for
FINS3645 Part B. It replaces the starter template and explains how the assistant should
work inside this project folder.

## Project Context

This project is `z5516421_projectB` for FINS3645 Part B. The product is
SignalHarbor, a Streamlit investment app for finance-literate retail investors.
The app should let a user compare systematic funds, read fund fact sheets, build a
simple allocation across funds, and inspect equity-sector news sentiment analytics.

All work must stay inside this project folder. The folder is the local runnable
project, the Moodle ZIP root, the GitHub repository root, and the Streamlit deployment
root.

## Core Deliverables

- Build out-of-sample systematic funds across three universes: Equity-only,
  Crypto-only, and Combined.
- For each universe, compare four methods: Equal Weight, Minimum Variance, Tangency
  / Maximum Sharpe, and Risk Parity.
- Generate precomputed app artifacts under `results/`.
- Build a standalone equity-sector sentiment index from news headlines.
- Test a sentiment fusion / overlay against base equity portfolios.
- Produce a finance-facing written report with self-contained figures and tables.
- Keep AI workflow evidence in `ai/`.

## Data Rules

- Use the official starter data and the provided data-access helper.
- Load raw equity, crypto, and headline data only through `src/data_access.py`.
- Do not commit raw `.parquet` files or downloaded source data.
- Save only derived outputs needed by the report and app.
- Compute equity returns on the equity trading calendar.
- Compute crypto returns on the crypto calendar before any calendar alignment.
- Compute crypto returns on the natural crypto calendar first, then align them to
  the equity trading calendar when constructing the Combined panel. Explain this
  calendar treatment clearly in the report.
- Do not merge equity and crypto price levels and then calculate returns.
- Deduplicate headlines using `ticker`, `date`, and `title`.
- Keep raw headline text for VADER-style scoring. Do not remove punctuation, casing,
  stop words, or negation terms before scoring.
- Sentiment applies only to equities because crypto has no headline data.

## Portfolio and Backtest Rules

- Use walk-forward out-of-sample backtests.
- Use an expanding estimation window, with live OOS performance from 2021 to 2023.
- Rebalance monthly.
- Portfolio weights must be formed only from information available before the live
  return period.
- All submitted fund weights should be long-only and fully invested:
  `w_i >= 0` and `sum_i w_i = 1`.
- Use a zero risk-free rate unless a different proxy is explicitly introduced and
  documented.
- State transaction costs clearly. If they are zero in the baseline, do not describe
  turnover as an actual transaction cost.
- Annualise Equity and Combined funds with the equity trading calendar. Annualise
  Crypto funds with the crypto calendar.
- Treat Equal Weight as a serious benchmark, not as a trivial method.
- Risk Parity should be covariance-aware equal risk contribution, not simply inverse
  volatility.
- Save diagnostics for weight sums, negative weights, rebalance counts, date ranges,
  solver fallbacks, and no-look-ahead checks.

## Sentiment and Innovation Rules

- Score headlines with a VADER-style model and a finance-augmented extension.
- Aggregate headline scores to ticker-day sentiment, then to sector-day sentiment.
- Sector sentiment should equal-weight ticker-day observations so that firms with
  more headlines do not dominate the sector.
- Record news coverage, such as active ticker count and coverage ratio.
- Do not fill no-news observations as automatically neutral unless explicitly tested
  and justified.
- Any sentiment signal used for trading must be lagged by at least one trading day.
- Use past-only or expanding-window standardisation for live signals. Do not use the
  full sample mean or standard deviation for a live decision.
- The main innovation is the coverage-aware sector sentiment signal:
  `Coverage-aware signal_{s,t-1} = z_{s,t-1} * Coverage_{s,t-1}`.
- The purpose of the coverage adjustment is to reduce the influence of sector signals
  based on sparse headline coverage.
- Test the innovation honestly through a before-versus-after fusion comparison.
- Do not claim that the sentiment overlay improves performance unless OOS evidence
  supports that claim.

## Figure and Table Rules

- Every table and figure must use generated project outputs, not invented values.
- Every exhibit must have a clear title, labelled axes, units, sample period where
  relevant, and a source line.
- Figures should support the report argument rather than appear as decoration.
- Use clean finance-report styling. Avoid clutter, unexplained annotations, and
  duplicated messages.
- Preserve the underlying data when making presentation-only changes.
- If a figure is revised, record whether the change affected the data or only the
  visual presentation.
- Use figure text to make the investment insight clear for readers who understand
  finance but may not read code.

## Required Result Files

The app and marker checks expect these files:

- `results/data/fund_returns.csv`
- `results/data/fund_weights.csv`
- `results/data/sector_sentiment_index.csv`
- `results/tables/performance_metrics.csv`

Additional diagnostics and report support files may also be saved, including:

- `results/tables/backtest_audit.csv`
- `results/data/backtest_diagnostics.csv`
- `results/tables/fusion_comparison.csv`
- `results/data/fusion_returns.csv`

## Streamlit App Rules

- The deployed app entrypoint is `streamlit_app.py` at the project root.
- The deployed app must read precomputed CSV files from `results/`.
- The app must not recompute backtests or rerun sentiment models on Streamlit
  Community Cloud.
- The app must not depend on local laptop paths.
- Keep the app lightweight and reproducible.

## Verification Rules

After model or output changes, run:

```bash
python scripts/run_part_b.py
python scripts/check_handin.py
```

Before relying on any result, check:

- number of funds and methods;
- OOS date ranges;
- rebalance counts;
- duplicate fund-date rows;
- missing fund returns;
- annualisation factors;
- weight sums;
- negative weights;
- solver failures or fallbacks;
- no-look-ahead diagnostics;
- required filenames.

## Report Writing Rules

- Write for a finance-literate reader, not a programmer.
- Explain why the investment methods were chosen, not only how they are calculated.
- Interpret each figure and table in the text.
- Use numbers from the generated files and keep them consistent with the exhibits.
- Separate return, risk, drawdown, turnover, and implementation burden.
- Do not overstate Risk Parity: low risk-contribution dispersion supports the
  implementation, but does not prove the fund is always safer or better.
- Do not overstate sentiment: headline sentiment is a noisy proxy and may not improve
  OOS returns.
- Critical reflection and recommendations must be based on the final results.

## AI Workflow Rules

- Keep prompt logs in `ai/`.
- Record the goal, prompt, assistant output, risk or error, and final correction.
- Keep the recovered original workflow record. Do not delete original prompt logs.
- The curated AI workflow may consolidate repeated cosmetic revisions, but it should
  still explain major rejected designs and why the final design was better.
- Review AI code, formulas, report text, and figures before accepting them.
- The final written interpretation must be my own judgement based on audit evidence
  and financial reasoning.

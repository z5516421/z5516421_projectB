# Prompt Log - Part B Implementation and Report

## Task 1 - Understand the Brief and Rubric

### What I wanted
I wanted to identify all Part B requirements and the high-distinction rubric before
writing code.

### Prompt(s)
"Read the Project B brief, HD rubric and Week 10 revision guidance. Identify the
required exhibits, report structure, app requirements, innovation expectations and AI
workflow requirements. Build an evidence plan for a finance-literate reader who may not
understand code."

### What the assistant produced
The assistant summarised the required Part B deliverables: 12 OOS funds, performance
tables, growth of $1, drawdowns, portfolio weights over time, sector sentiment index,
fusion before-after evidence, Streamlit app, deployment evidence and AI workflow
documentation. It also suggested using the report sections from the brief as the main
structure.

### What was wrong or risky
The first checklist was useful but too mechanical. It risked becoming a list of outputs
rather than a coherent investment argument. The HD rubric requires interpretation,
evidence and innovation, not just compliance with file names.

### What I changed and why
I converted the checklist into an evidence chain. Table 1 explains design, Table 2
audits fund performance, Figure 1 shows wealth paths, Figure 2 tests downside risk,
Figure 3 ranks risk-adjusted performance, Figure 4 explains portfolio weights, Figure 5
presents the sentiment innovation, and Figure 6 tests whether the innovation adds
investment value. I treated the coverage-aware signal as the core innovation, rather
than treating finance-VADER or chart design as innovation by itself.


## Task 2 - Build the Part B Clean Data Layer

### What I wanted
I wanted Part B to start from clean reusable return and headline panels, instead of
repeatedly reading or re-cleaning raw files.

### Prompt(s)
"Before the OOS backtest, please set up the Part B data layer first. Use clean reusable
panels, not raw parquet files scattered through the project. Equity returns should use
the equity trading calendar. Crypto returns should be calculated on the natural calendar
first, then aligned to the equity calendar only for the combined panel. For news,
deduplicate headlines by ticker, date and title, map them to the same or next equity
trading day, and keep sentiment for equity only, not crypto. After that, run a quick
count check and tell me if anything looks wrong."

### What the assistant produced
The assistant created the first Part B data layer by modifying `src/etl.py` and
`src/features.py`. It loaded and cleaned equity prices, crypto prices and news
headlines, calculated equity returns on the equity trading calendar, calculated crypto
returns on the natural calendar, created the combined return panel by aligning crypto
returns to the equity calendar, and mapped headlines to the same or next valid equity
trading day.

The assistant reported 50 equity stocks from 2020-01-02 to 2023-12-29, 10 crypto coins
from 2020-01-01 to 2023-12-31, 146,836 clean news rows, 50,250 equity return rows,
14,600 crypto return rows, 60,300 combined return rows across 60 assets, and 146,830
mapped headlines with 6 sample-end boundary rows.

### What was wrong or risky
The risky part was the calendar handling. Crypto trades every day, while equities do
not, so crypto returns needed to be calculated before any equity-calendar alignment. It
was also risky to use news for crypto, because the headline and sector sentiment design
was equity-based.

### What I changed and why
I kept the workflow based on clean intermediate panels and made the equity-only
sentiment assumption explicit. This reduced the risk of changing data definitions later
in the backtest, figures, report or app.

### How I checked
I reviewed the output counts and date ranges for equities, crypto, combined returns and
mapped headlines before moving on to the OOS backtest.



## Task 3 - Run the Monthly Walk-Forward OOS Fund Backtest

### What I wanted
I wanted to generate the main OOS fund results required for Part B: 12 funds from three
universes and four portfolio methods.

### Prompt(s)
"Please build the actual OOS backtest for Part B. I need the 12 funds from the brief:
Equity, Crypto and Combined, each with Equal Weight, Minimum Variance, Tangency and Risk
Parity.

Please make it monthly walk-forward OOS, long-only and fully invested, with an expanding
training window. Make sure the training data always ends before the rebalance date so
there is no look-ahead.

After it runs, please check the fund count, OOS date range, rebalance dates, weight
sums, negative weights and training dates. If something looks wrong, stop and tell me."

### What the assistant produced
The assistant implemented the monthly walk-forward OOS backtest by editing
`src/portfolios.py` and `scripts/run_part_b.py`. It generated the 12 required funds
across the Equity, Crypto and Combined universes using Equal Weight, Minimum Variance,
Tangency and Risk Parity. It also saved the main result files:
`results/data/fund_returns.csv`, `results/data/fund_weights.csv` and
`results/tables/performance_metrics.csv`.

### What was wrong or risky
The risky parts were look-ahead bias, invalid weights and calendar handling. Portfolio
weights had to be estimated before each rebalance date, remain long-only and sum to one.
The Combined universe also needed consistent treatment because it mixes equity and
crypto assets.

### What I changed and why
I treated this as the core OOS backtest engine and required basic checks before using
the results in later figures and report writing. These precomputed outputs became the
fixed source for the performance table, charts, Streamlit app and final analysis.

### How I checked
I checked that the pipeline produced 12 funds, the expected OOS period, valid rebalance
dates, no negative weights, near-zero weight-sum error and training dates before
rebalance dates.

## Task 4 - Audit the OOS Backtest Calendar and Optimisation Checks

### What I wanted
I wanted to check whether the OOS backtest was actually correct after noticing that the
summary showed 46 rebalance dates, which sounded wrong for a 2021-2023 monthly backtest.

### Prompt(s)
"The backtest output says 46 rebalance dates, but that sounds confusing for a monthly
OOS backtest from 2021 to 2023. Please audit this carefully instead of assuming it is
fine.

Check whether each fund really has 36 monthly rebalances, and explain why the pooled
unique rebalance-date count across all universes is 46. Also check no-lookahead, weight
sums, negative weights, duplicate or missing fund returns, annualisation factors, solver
fallback, and whether Risk Parity is really equal risk contribution rather than just
inverse volatility.

If the backtest is correct but the summary is misleading, please explain that clearly
and save proper audit outputs."

### What the assistant produced
The assistant audited the backtest calendar and optimisation diagnostics. It confirmed
that each fund had 36 monthly rebalances. The earlier value of 46 was not a fund-level
rebalance count; it came from pooling unique rebalance dates across the Equity, Crypto
and Combined universes. Crypto can rebalance on 2021-01-01 because it uses a natural
calendar, while Equity and Combined begin on the first equity trading day, 2021-01-04.

The assistant added `results/tables/backtest_audit.csv` and
`results/data/backtest_diagnostics.csv`. The checks confirmed 12 funds, 36 rebalances
per fund, Equity/Combined OOS returns from 2021-01-04 to 2023-12-29, Crypto OOS returns
from 2021-01-01 to 2023-12-31, annualisation of 252 for Equity/Combined and 365 for
Crypto, zero negative weights, weight-sum error around 1e-16, zero duplicate return
dates, zero missing fund returns, `training_end_date < rebalance_date = True`, strict
no-lookahead violations = 0, and solver fallback count = 0.

It also checked Risk Parity risk-contribution dispersion: Equity Risk Parity max
dispersion was 0.000382, Crypto Risk Parity was 0.001042, and Combined Risk Parity was
0.000620. This supported that Risk Parity was implemented as equal risk contribution
using the covariance matrix.

### What was wrong or risky
The backtest itself was not wrong, but the earlier summary was misleading. Saying 46
rebalance dates could make it look like each fund had 46 monthly rebalances, when each
fund actually had 36. There was also a risk of mislabelling Risk Parity if it was only
inverse volatility, so the risk-contribution check mattered.

### What I changed and why
I kept the backtest results unchanged because the audit showed the OOS setup was valid.
I changed the interpretation of the summary so it clearly separates 36 rebalances per
fund from 46 pooled unique dates across universes. I also used the Risk Parity
diagnostics later in the report to explain that Tangency was more concentrated while
Risk Parity was closer to equalising risk contributions.

### How I checked
I reviewed the audit outputs for rebalance counts, OOS dates, annualisation factors,
weight constraints, missing or duplicate returns, no-lookahead violations, solver
fallback and Risk Parity dispersion before moving on to sentiment.



## Task 5 - Build the Sector Sentiment Index Pipeline

### What I wanted
I wanted to add the required sector sentiment index after the OOS fund backtest was
stable, using equity news only.

### Prompt(s)
"Please build the sector sentiment index and connect it to the Part B pipeline. Use the
cleaned headline panel, not raw scattered files. The sentiment should be for equity
sectors only, not crypto. I want the chain to go from headline text to VADER or
finance-adjusted VADER score, then ticker-day sentiment, sector-day sentiment, and
finally a sector sentiment index and trading signal. Please save it as a precomputed
result so the figures, report and app can load it later instead of rerunning sentiment
scoring."

### What the assistant produced
The assistant added the sentiment module by updating `src/sentiment.py` and connecting
it through `scripts/run_part_b.py`. It generated
`results/data/sector_sentiment_index.csv`. The sentiment workflow used the cleaned
equity headline panel and aggregated sentiment from headline level to ticker-day and
then sector-day outputs. It also produced fields for the investor-facing sentiment index
and the coverage-aware lagged trading signal.

### What was wrong or risky
The main risk was applying sentiment to the wrong universe. The headline data and sector
mapping were equity-based, so crypto sentiment would have been unsupported. It was also
risky to make the app rerun sentiment scoring, because the teacher required the app to
load precomputed results.

### What I changed and why
I kept sentiment as an equity-sector signal and made it a saved pipeline output. This
gave the later figures, report and Streamlit app a stable precomputed sentiment file to
use.

### How I checked
I checked that `sector_sentiment_index.csv` was generated from the pipeline and could be
used later for the sentiment figure and app.



## Task 6 - Add and Test the Sentiment Fusion Overlay

### What I wanted
I wanted to test whether the sector sentiment signal could add investment value when
used as a portfolio tilt.

### Prompt(s)
"Please build the sentiment fusion module and connect it to the Part B pipeline. Use the
precomputed sector sentiment signal and the existing OOS equity fund results to create
sentiment-tilted equity portfolios. Be very careful about look-ahead. The signal must be
lagged before trading. Please check weight sums, minimum sentiment weights and
signal-date violations. Do not overstate the result. If sentiment fusion does not
improve Sharpe, say that honestly."

### What the assistant produced
The assistant added `src/fusion.py` and connected the fusion step through
`scripts/run_part_b.py`. It generated `results/data/fusion_returns.csv`,
`results/data/fusion_weights.csv` and `results/tables/fusion_comparison.csv`. It also
updated `AGENTS.md` so future work would preserve the precomputed-results workflow.

The fusion checks passed: maximum weight-sum error was approximately 3e-15, minimum
sentiment weight was 0.0074, and signal-date violations were 0. The hand-in checker
reported 22 checks passed, with only a warning that `report/report.pdf` did not exist
yet.

### What was wrong or risky
The main risk was look-ahead bias, because a sentiment overlay would be invalid if it
used news signals that were not available before trading. There was also a risk of
overstating the innovation. The sentiment tilt did not improve Sharpe, so it should be
treated as an honest negative result rather than claimed as successful alpha.

### What I changed and why
I treated the fusion overlay as an empirical test, not a guaranteed improvement. The
signal was lagged before trading, the weights remained valid, and the result files were
saved for later analysis. Because the fusion result did not improve Sharpe and drawdown
changes were small, I planned to explain it in the report as a valid but cautious
innovation result.

### How I checked
I checked the fusion diagnostics for weight sums, minimum sentiment weights and
signal-date violations, then ran `python3 scripts/check_handin.py` to confirm the
required files were present.

## Task 7 - Draft the Initial Part B Report

### What I wanted
I wanted to start writing the Part B report after the main results, sentiment outputs
and fusion test were available.

### Prompt(s)
"Now that the main Part B results are ready, please help me draft the report. Use the
project brief, HD rubric and Week 10 guidance. The report should explain the OOS fund
results, the sentiment index, the sentiment fusion test and the Streamlit product idea.
Please write for a finance reader, not a coder. Use the actual result files and figures
from my project. Do not invent numbers, do not change the CSV data, and do not rerun the
backtest or sentiment scoring. If a result is weak or negative, explain it honestly
instead of trying to make it sound successful."

### What the assistant produced
The assistant drafted the first version of the Part B report using the generated OOS
results, sentiment outputs and fusion evidence. The draft covered the portfolio
construction methods, OOS performance comparison, drawdowns, sector sentiment signal,
fusion overlay result and the idea of turning the results into a Streamlit product.

### What was wrong or risky
The first draft was useful as a starting point, but it was still too close to a results
summary. It needed deeper financial interpretation, clearer links to the required
figures, and stronger explanation of why the Streamlit app counted as a product. It also
needed more careful wording around the negative sentiment fusion result.

### What I changed and why
I treated this draft as a first report skeleton rather than the final submission. I
planned to revise it later by adding stronger investment interpretation, clearer
innovation framing, better figure discussion, turnover analysis and final product
recommendations.

### How I checked
I checked that the draft used the generated Part B outputs and did not include AI
workflow in the report body.

## Task 8 - Correct the Sharpe Ratio Formula

### What I wanted
I wanted to check whether the reported Sharpe ratios were being calculated incorrectly
from CAGR divided by annualised volatility.

### Prompt(s)
"sharp ratio is wrong. Please check Annualised volatility / Annualised return and see
whether the Sharpe calculation is wrong."

### What the assistant produced
The assistant inspected `src/portfolios.py` and found that the original Sharpe
calculation used annualised CAGR divided by annualised volatility.

### What was wrong or risky
This was inconsistent with the Week 5 formula. Sharpe should use average daily excess
return divided by daily standard deviation, multiplied by the square root of the
annualisation factor. CAGR can be reported as annualised return, but it should not be
used as the numerator of the Sharpe ratio.

### What I changed and why
I changed `performance_metrics()` and the Streamlit Portfolio Builder so Sharpe is
computed from daily returns. Then I regenerated the metrics table, fusion table, figures
and report. This made the reported Sharpe ratios consistent with the course formula.

### How I checked
I reran the Part B pipeline, rebuilt the report and ran the hand-in checker. The final
checks passed.


## Task 9 - Fix Turnover, Figures, and Report Evidence Chain

### What I wanted
I wanted to respond to a detailed visual and technical critique of the report,
especially the turnover calculation, figure design, captions, appendix layout and
unsupported wording.

### Prompt(s)
"Please review the current report and figures carefully. I think several things may
still be wrong or misleading. The turnover measure looks too simple, because it may only
compare target weights from one rebalance to the next. A real rebalance should compare
the new target weights with the pre-rebalance drifted weights after the holding period,
so please check whether the turnover calculation is implementable. The Growth of $1
figure is hard to read because crypto dominates the scale and compresses the equity and
combined funds. Please redesign it so the universes can be compared more clearly. Please
also check whether the portfolio weights figure really explains the allocation evidence
required by the brief, and whether the sentiment figure matches the signal discussed in
the report. If the report discusses z-scores or the coverage-aware trading signal, the
figure should not just show raw sentiment scores. Finally, check the captions, appendix
layout and wording. If any claim is stronger than the evidence, soften it and explain
transaction costs more carefully. If you agree with these issues, please fix them using
the existing result files. Do not change the underlying data or invent new results."

### What the assistant produced
The assistant checked the critique against the generated CSV files, code and lecture
requirements. It updated the turnover calculation, regenerated the metrics and fusion
tables, revised the required figures, and rewrote parts of the report so the evidence
chain was clearer.

### What was wrong or risky
Several issues could mislead the marker. The growth figure made equity and combined
funds hard to compare, the weights figure was not yet clear enough as portfolio
evidence, the sentiment figure did not fully match the signal discussed in the text, and
the turnover column was based on target-weight changes rather than implementable
rebalance turnover. Some report wording also risked overstating results that were not
fully supported by the evidence.

### What I changed and why
I changed turnover to compare new target weights against pre-rebalance drifted weights,
then rebuilt the metrics table, fusion table, figures and report. I revised the figure
evidence so the Growth of $1 chart used clearer universe panels with terminal value
labels, the weights figure better explained portfolio exposure, the sentiment figure
focused on the coverage-aware sector signal, and the fusion figure made the OOS
before/after comparison clearer. I also softened unsupported claims and added clearer
transaction-cost wording, so the report did not overclaim the results.

### How I checked
I regenerated the pipeline outputs and report, then checked the rendered PDF layout to
make sure the revised figures, captions and report discussion were consistent.


## Task 10 - Rebuild Figure A1 in FT Style from OOS Fund Returns

### What I wanted
I wanted Figure A1 to follow the Week 2 FT-style chart requirements and to use the
correct Growth of $1 data source.

### Prompt(s)
"Please check whether Figure A1 is generated correctly. It should calculate Growth of $1
directly from the submitted OOS fund daily returns in results/data/fund_returns.csv,
grouped by fund and sorted by date, using the cumulative product of one plus daily
return. It should not use raw prices, combined_returns_panel.csv, or asset returns
unless the monthly OOS fund weights are fully reapplied. If this method is correct,
please redraw Figure A1 in a clearer FT-style format with a conclusion-style title,
light FT-style background, readable axes, source note, linear panels, and
non-overlapping terminal labels."

### What the assistant produced
The assistant checked the current plotting code and confirmed that Figure A1 already
used OOS fund returns, then rebuilt the figure with a stronger FT-style presentation.

### What was wrong or risky
The original figure used the correct broad data source, but the visual design was not
sufficiently FT-style. Endpoint labels overlapped, the default log-axis formatting was
hard to read, the source note was less precise, and the chart did not clearly state that
Growth of $1 came from the submitted OOS fund return series.

### What I changed and why
I changed the Figure A1 plotting function to compute `growth_1` directly from
`fund_returns.csv`, use an FT-like paper background and restrained gridlines, add a
conclusion title and subtitle, show terminal value labels on the right, use linear
panels after splitting the universes, and cite `results/data/fund_returns.csv` in the
source note. I then regenerated the figure and rebuilt the report so the updated chart
is embedded in both the DOCX and PDF.


## Task 11 - Separate Overlapping Crypto Endpoint Labels in Figure A1

### What I wanted
I wanted the Crypto panel in Figure A1 to be more readable because the Risk Parity and
Equal Weight terminal labels were too close together.

### Prompt(s)
"Please fix Figure A1 because the Crypto panel's Risk Parity and Equal Weight endpoint
labels overlap. Keep the same Growth of $1 data and only adjust the label placement so
the terminal labels are readable in the report PDF."

### What the assistant produced
The assistant adjusted the endpoint label spacing for the Crypto panel, then regenerated
Figure A1 and rebuilt the DOCX and PDF report.

### What was wrong or risky
The underlying growth calculation was correct, but the visual label overlap could make
the figure look unfinished and reduce clarity for the marker.

### What I changed and why
I increased the minimum vertical separation for Crypto endpoint labels while keeping
connector lines from the labels back to the true series endpoints. This keeps the
reported terminal values unchanged while improving readability.

## Task 12 - Correct Figure A1 Dates and Reporting Note

### What I wanted
I wanted Figure 1 to retain the three fund-universe panels, fund lines, endpoint labels,
baseline and Financial Times-style treatment, while showing only the true OOS date range
on every x-axis.

### Prompt(s)
"Please revise Figure 1. Keep the same three-panel layout (Equity, Combined, Crypto),
the same fund lines, and the endpoint labels. Fix the x-axis so all panels have clear
date labels and the displayed period matches the true OOS sample, without extending to
2024-02 if that date is outside the sample. Keep the y-axis label 'Growth of $1' on each
panel and keep the baseline at 1.0. Change the title to 'Growth of $1 by fund universe,
2021–2023'. Add this note under the figure: 'Source: results/data/fund_returns.csv.
Note: Growth of $1 is calculated from submitted OOS daily fund returns. Equity and
combined funds use equity trading days, while crypto funds use calendar days. Panels use
different y-axis scales for readability.' Keep the figure clean, professional, and
FT-style."

### What the assistant produced
The assistant kept the submitted OOS returns, three-panel layout, method lines, direct
endpoint labels, 1.0 baseline and warm FT-style visual treatment. It changed the title
and replaced the old source note with the requested source and calendar note.

### What was wrong or risky
The earlier chart expanded the x-axis past the final OOS observations solely to create
space for endpoint labels. This made a 2024-02 tick appear even though the OOS sample
ends in December 2023, which could be misleading.

### What I changed and why
I constrained each panel's x-axis to its actual final OOS date: 2023-12-29 for Equity
and Combined, and 2023-12-31 for Crypto. Endpoint labels are now positioned using a
small display-offset outside the final point, rather than extending the data axis. I
used January, May and September date ticks so every panel has readable date labels
without adding an out-of-sample date.

### How I checked
I regenerated the figure from `results/data/fund_returns.csv`, rebuilt the Word report,
and rendered the report for visual inspection. The change did not alter the submitted
return series or the growth calculation.

## Task 13 - Refine Figure A1 Footer and First-Date Ticks

### What I wanted
I wanted the Figure A1 source note to read more like an FT-style report footer, without
rebuilding the report. I also wanted the Equity and Combined panels to display their
January 2021 starting period clearly, rather than beginning with a later visible date
label.

### Prompt(s)
“Please the figure should FT-style format.  And figure1 first two x-axes also do not
show 2021-01."

### What the assistant produced
Added explicit first-observation date ticks to every panel.

### What was wrong or risky
Equity and Combined start on their first January trading date rather than 1 January, so
the generic quarterly tick locator did not display a visible `2021-01` label on those
panels.

### What I changed and why
I made the first real OOS observation in each panel a fixed tick, formatted as
`2021-01`, while retaining the true underlying OOS x-axis limits.

### How I checked
I regenerated only `results/figures/growth_of_1_comparison.png` from the submitted
`fund_returns.csv` and visually checked the rendered image. No report file or underlying
return data was changed.

## Task 14 - Remove Figure A2 Dashed Lines

### What I wanted
I wanted the Figure A2 paths to remain fully solid rather than using dashed lines for
Combined funds.

### Prompt(s)
"Do not use dashed lines."

### What the assistant produced
The assistant changed every Figure A2 path back to a solid line and retained the
selected fund names in the legend.

### What was wrong or risky
The dashed-line distinction added visual noise to a chart that is already dense with
five drawdown paths.

### What I changed and why
I retained the consistent method colours and removed the line-style encoding so the
drawdown paths are easier to follow.

### How I checked
I regenerated only the Figure A2 PNG. The data and drawdown calculations were unchanged.

## Task 15 - Restore the Figure A2 Comparison Treatment

### What I wanted
I wanted Figure A2 to retain the earlier single-chart comparison treatment, but with
only a concise source line rather than an explanatory in-figure note.

### Prompt(s)
"Keep this Figure A2 version, but remove the long note inside the chart. I only want a
clean source line at the bottom.

Please do not change the drawdown data or calculation. Keep the selected OOS drawdown
paths, the 0% baseline and the 2021-2023 date range. Make sure the chart stays readable
and that the displayed funds are still easy to identify."

### What the assistant produced
The assistant retained the selected five OOS drawdown paths, the 0% baseline, the
2021-2023 date range and solid lines. It restored distinct colours for each displayed
fund, used the broad equity-and-combined title, and kept only a concise source footer.

### What was wrong or risky
Using only method colours made the Equity and Combined Equal Weight and Tangency paths
difficult to distinguish when their lines overlapped. The previous explanatory note was
unnecessarily long inside the chart.

### What I changed and why
I assigned distinct, report-consistent colours to the five displayed funds, retained the
full legend, and replaced the footer with `Source: results/data/fund_returns.csv.` The
OOS range was not expanded beyond December 2023.

### How I checked
I regenerated only Figure A2 from the submitted fund-return file and visually inspected
the resulting PNG. The underlying returns and drawdown calculations were unchanged.

## Task 16 - Add Median Reference to Figure A3

### What I wanted
I wanted Figure A3 to make the Sharpe ranking easier to interpret by adding a median
reference while keeping the same Sharpe values and horizontal ranking format.

### Prompt(s)
"Please revise Figure A3 to make the investment insight clearer for a high-quality
report. Keep the same Sharpe values and horizontal ranking format. Add a subtle vertical
dashed line showing the median Sharpe across the 12 funds. Keep the value labels at the
end of each bar. Use universe colours consistently. Do not change the Sharpe calculation
or underlying data."

### What the assistant produced
The assistant added a subtle dashed median-Sharpe line, kept the value labels at the bar
endpoints, and added a small universe-colour legend.

### What was wrong or risky
The previous chart ranked the funds correctly, but readers had no visual reference point
for distinguishing above-median from below-median Sharpe outcomes.

### What I changed and why
I used the existing plotted `sharpe_ratio` values to compute the median across the 12
funds. The Sharpe calculation, metric table, ranking order, and underlying data were
unchanged.


## Task 17 - Compare Combined Portfolio Weights Across All Four Methods

### What I wanted
I wanted Figure 4 to satisfy the brief's portfolio-weights-over-time requirement for one
universe. It needed to compare Equal Weight, Minimum Variance, Tangency and Risk Parity
in the Combined universe without recomputing the backtest or modifying portfolio
weights.

### Prompt(s)
"Please create Figure 4 as a portfolio-weights-over-time figure for the Combined
universe, using the existing out-of-sample portfolio weights... How do Equal Weight,
Minimum Variance, Tangency and Risk Parity differ in portfolio concentration and
allocation stability over the OOS period?"

### What the assistant produced
The assistant produced four aligned heatmap panels for the Combined universe. Each panel
uses the same 60-ticker row order and the same 36 monthly rebalance dates. Colour
indicates target weight, with values above 10% shown at the maximum shade, allowing
substantial Tangency concentrations to remain visible without flattening the other
methods.

### What was wrong or risky
The former Figure A4 showed only the Combined Risk Parity crypto sleeve and a
latest-holdings snapshot. It did not compare all four methods or show portfolio weights
through the OOS period, so it did not fully satisfy the brief's weights-over-time
requirement.

### What I changed and why
I used the existing `fund_weights.csv` directly and created a common asset order: crypto
tickers first and equity tickers second, alphabetically within each group. Each panel
also reports its mean largest holding, a concise concentration diagnostic calculated
directly from the displayed weights. This lets a finance reader compare stability and
concentration while keeping the full asset universe visible.

### How I checked
Before plotting, I verified that all four Combined methods are present, each has 36
rebalances and 60 tickers, and each rebalance-date weight sum equals one within
floating-point tolerance (maximum absolute error below 4e-15). The backtest and
underlying weights were not recomputed or changed.

## Task 18 - Aggregate Combined Weights by Sector and Crypto

### What I wanted
I wanted Figure 4 to become a readable portfolio-weights-over-time comparison for the
Combined universe. It needed to show all four OOS portfolio methods while aggregating
the 60 underlying assets into the 10 equity sectors and one Crypto bucket.

### Prompt(s)
"Create Figure 4 as a portfolio weights over time figure for the Combined universe only.
Compare the four OOS portfolio methods: Equal Weight, Minimum Variance, Tangency, and
Risk Parity. Use the existing out-of-sample weights from results/data/fund_weights.csv.
Do not recompute the backtest. Aggregate the asset weights into 10 equity sectors plus 1
Crypto bucket... Plot the result as four aligned stacked-area panels, one panel per
method, with a shared time axis and y-axis from 0% to 100%."

### What the assistant produced
The assistant produced four aligned 100% stacked-area panels, one for each
Combined-universe method. Each panel uses the same sector and Crypto category order, the
same colour map, the same 0% to 100% scale and the same monthly OOS rebalance dates.

### What was wrong or risky
The prior heatmap showed individual ticker weights. It was auditable but too dense for a
report reader and did not make sector allocation or the aggregate Crypto sleeve easy to
compare across methods.

### What I changed and why
I mapped equity tickers to the course-provided sector field in
`results/data/equity_returns.csv` and assigned every `-USD` ticker to a single Crypto
bucket. This preserves the submitted portfolio weights while making the allocation logic
readable: the same stacked categories show sector concentration, Crypto exposure and
changes at each monthly rebalance for all four methods.

### How I checked
I verified that all four Combined methods are present. Before and after aggregation,
weights sum to one on every rebalance date within floating-point tolerance. The figure
reads `results/data/fund_weights.csv` and the existing equity-sector mapping only; it
does not recompute the backtest or alter weights.

## Task 19 - Rebuild Figure 4 Using the Week 10 Portfolio-Weights Framework

### What I wanted
I wanted Figure 4 reconsidered from the Project B brief and the Week 10 teaching
material, rather than treated as a generic data visualisation. The figure needed to
provide clear evidence for the required portfolio-weights-over-time exhibit.

### Prompt(s)
"Please carefully read the brief, the HD marking criteria and the Week 10 lecture. Week
10 explicitly explains the Project B approach. Make Figure 4 correctly."

### What the assistant produced
The assistant rebuilt the Combined-universe weights figure as four aligned 100%
stacked-area panels for Equal Weight, Minimum Variance, Tangency and Risk Parity. Equity
weights are aggregated to the ten course-provided sectors, while all crypto assets form
one dark Crypto band.

### What was wrong or risky
Earlier versions mixed a time-series allocation chart with a latest-holdings snapshot,
or used a dense ticker-level heatmap. Those designs obscured the question being tested:
how portfolio capital is allocated through time. They also did not follow the specific
Week 10 presentation convention that sector bands sum to 100% at each date and Crypto is
a separate single band.

### What I changed and why
I followed the Week 10 structure: every panel shows monthly target weights that stack to
100%, uses the same sector order and colours, and displays Crypto as a single dark band.
Keeping the four methods aligned satisfies the brief's across-method comparison while
allowing a finance reader to see concentration, sector tilts, crypto exposure and
changes after each rebalance without inspecting code.

### How I checked
I re-read the relevant Project B brief and Week 10 pages on portfolio weights over time.
The figure validates that all four Combined methods are present and that weights sum to
one before and after the sector/Crypto aggregation. It uses existing
`results/data/fund_weights.csv` data and the provided sector mapping only; no backtest
or weight was recomputed.

## Task 20 - Clarify the Investment Question Behind Figure 4

### What I wanted
I wanted Figure 4 to stop behaving like another performance chart. Its purpose should be
to explain why different portfolio-construction methods produced different returns,
drawdowns and Sharpe ratios by showing allocation stability, sector or asset
concentration, crypto exposure and rebalancing behaviour.

### Prompt(s)
"For Figure 4, the task is not to show which fund had the highest return again. It
should answer why different methods ended up with different return, drawdown and Sharpe
outcomes. It should show whether allocations were stable, whether they were concentrated
in a few sectors or assets, how high crypto exposure was, and whether weights changed
frequently. Ignore my previous Figure 4 prompt and combine the teacher's framework with
this investment question."

### What the assistant produced
The assistant confirmed that the appropriate Figure 4 design is a Combined-universe
portfolio-weights-over-time chart using four aligned 100% stacked-area panels: Equal
Weight, Minimum Variance, Tangency and Risk Parity. The chart aggregates equities into
the ten course sectors and treats crypto as one separate dark sleeve.

### What was wrong or risky
A latest-holdings chart, a single crypto-sleeve line or a performance chart would not
answer the required investment-design question. Those alternatives either show only one
date, only one fund or only return outcomes, rather than showing how the methods
allocated capital through time.

### What I changed and why
I retained the Week 10 sector-band design and revalidated the existing figure against
the finance question. This design lets the report connect performance outcomes to
allocation mechanisms: stable equal weights, defensive sector concentration under
Minimum Variance, unstable sector and crypto shifts under Tangency, and smoother
risk-balanced exposure under Risk Parity.

### How I checked
I regenerated Figure 4 from `results/data/fund_weights.csv`, verified that all four
Combined methods have 36 monthly rebalance dates and 60 assets, and checked that weights
sum to one at each rebalance date within floating-point tolerance.

## Task 21 - Rebuild Figure 5 Around the Coverage-Aware Sentiment Innovation

### What I wanted
I wanted Figure 5 to focus on one clear Project B innovation: a coverage-aware sector
sentiment signal. The figure should not be a generic VADER average, a heatmap-only
design or a collection of unrelated panels. It should show the sector signal that scales
lagged sentiment by observed news coverage.

### Prompt(s)
"Please complete Figure 5. The main innovation should be a coverage-aware sector
sentiment signal. The signal should follow this chain: headline text, finance-augmented
VADER score, ticker-day average, sector average, past-only expanding z-score, multiplied
by the news coverage ratio, then lagged by one trading day. Plot ten equity-sector
coverage-aware sentiment signal time series, with date on the x-axis, coverage-aware
sentiment signal on the y-axis, and a zero line. Do not use crypto. The figure should
explain that the signal scales the lagged sector sentiment z-score by the proportion of
constituent stocks with observed news coverage."

### What the assistant produced
The assistant replaced the previous sector sentiment heatmap with a single time-series
figure covering the ten equity sectors from 2020 to 2023. The chart plots the existing
`finance_vader_coverage_adjusted_signal_lag1` field from `sector_sentiment_index.csv`,
directly labels each sector at the end of the line and includes a zero line.

### What was wrong or risky
The earlier figure treated the visual heatmap as the main story. That was risky because
the actual innovation is the signal construction: sector sentiment is not treated as
equally reliable every day, but is scaled by headline coverage breadth before being used
as a trading signal.

### What I changed and why
I used the one-day-lagged, coverage-adjusted finance-VADER sector signal as the plotted
variable. To keep ten sector lines readable in a report figure, the displayed lines use
a 21-trading-day average, while the underlying signal calculation and submitted CSV data
remain unchanged. The source note states the signal definition so the innovation is
auditable.

### How I checked
I verified that `sector_sentiment_index.csv` contains the required lagged
coverage-adjusted finance-VADER signal, spans 2020-01-02 to 2023-12-29 and includes the
ten equity sectors. I regenerated only Figure 5 from the existing CSV; no backtest,
portfolio return or portfolio weight was recomputed.

## Task 22 - Redesign Figure 5 as Sector Small Multiples

### What I wanted
I wanted Figure 5 to keep the same coverage-aware sentiment data but avoid the crowded
ten-line chart. The revised figure needed to show one equity sector per panel so that
the signal dynamics are readable while still covering all sectors.

### Prompt(s)
"Revise Figure 5. Do not change the underlying sentiment data. The current 10-line chart
is too crowded. Replot Figure 5 as 2x5 small multiples, one panel per equity sector. Use
the same coverage-aware sentiment signal currently used in the chart. If the chart uses
a 21-day rolling average for readability, keep that, but clearly state it in the footer.
Requirements: one sector per panel; shared x-axis date range; shared y-axis range across
all panels; add a horizontal zero line in every panel; remove the crowded right-side
labels and legend; panel titles should be sector names; title: Coverage-aware sector
sentiment signals, 2020–2023; footer: Source: results/data/sector_sentiment_index.csv.
Signal equals one-day-lagged sector sentiment z-score scaled by prior news coverage
ratio; 21-day averages shown for readability. Do not include crypto. Do not rerun the
portfolio backtest."

### What the assistant produced
The assistant rebuilt Figure 5 as a 2x5 grid of small multiples, with one panel for each
equity sector. Each panel plots the same `finance_vader_coverage_adjusted_signal_lag1`
series displayed as a 21-day average, uses the same y-axis range, has a zero line and
removes the previous right-side labels and legend.

### What was wrong or risky
The prior single-panel line chart preserved all ten sectors but was visually crowded. A
reader could see that a coverage-aware signal existed, but it was harder to compare
sector histories or identify which sectors had persistent positive or negative regimes.

### What I changed and why
I kept the existing sentiment data and the same 21-day display average, but moved each
sector into its own aligned panel. This keeps the innovation auditable and makes the
figure easier to interpret for a finance report reader.

### How I checked
I regenerated only `sector_sentiment_timeseries.png` from the existing
`sector_sentiment_index.csv`, then visually checked that all ten equity sectors appear,
the panels share the same date and y-axis range, every panel includes a zero line and
the footer states the signal definition. The portfolio backtest was not rerun.

## Task 23 - Test Whether the Sentiment Fusion Overlay Added Investment Value

### What I wanted
I wanted Figure 6 to evaluate the coverage-aware sector sentiment overlay as an
investment experiment, not just as a text-processing output. The figure needed to
compare the base equity portfolios with their sentiment-fusion versions using existing
submitted results only.

### Prompt(s)
"Create Figure 6 for my FINS3645 Project B. Figure 6 should test whether the
coverage-aware sector sentiment signal adds investment value. Use existing results only.
Do not invent data and do not rerun the main portfolio backtest. Use
results/data/fusion_returns.csv and any existing fusion performance summary if
available. Compare the base equity portfolio with the sentiment-tilted / fusion
portfolio over the OOS period. The figure should show before vs after performance
clearly. Preferred design: a grouped bar chart comparing Base vs Sentiment Fusion on
annual return or CAGR, annual volatility, Sharpe ratio, maximum drawdown and turnover if
available. Use actual metric values from the project files, do not claim improvement if
the fusion result is worse, use positive drawdown magnitude, and report which portfolios
and metric values are being compared before saving the figure."

### What the assistant produced
The assistant created Figure 6 as five aligned grouped-bar panels comparing Base versus
Sentiment Fusion for Equity Equal Weight and Equity Risk Parity. The panels report
annual return, annual volatility, OOS Sharpe, maximum drawdown loss and average
turnover.

### What was wrong or risky
A Sharpe-only comparison would be too shallow because it would miss implementation cost.
The sentiment fusion slightly reduced Sharpe in both tested portfolios, while turnover
rose materially, so the figure needed to show both investment performance and trading
intensity.

### What I changed and why
I used the existing `fusion_comparison.csv` summary, based on the submitted fusion
returns, to keep the metric values auditable. The final design makes the key result
visible: the sentiment overlay did not improve OOS Sharpe or downside protection, but it
approximately doubled monthly turnover.

### How I checked
I read `results/data/fusion_returns.csv` and `results/tables/fusion_comparison.csv`,
confirmed that the available comparison is Equity Equal Weight versus Equity Equal
Weight + Sentiment Tilt and Equity Risk Parity versus Equity Risk Parity + Sentiment
Tilt, and verified the metric values before plotting. I regenerated only Figure 6 and
ran a Python syntax check; the main backtest was not rerun.

## Task 24 - Retitle Figure 6

### What I wanted
I wanted the Figure 6 title to specify that the fusion overlay is applied to equity
portfolios.

### Prompt(s)
"Change the title to \"Performance impact of the equity sentiment fusion overlay.\""

### What the assistant produced
The assistant changed the Figure 6 title to `Performance impact of the equity sentiment
fusion overlay`.

### What was wrong or risky
The previous title was slightly broader and could be read as referring to all universes,
while the tested fusion portfolios are equity funds.

### What I changed and why
I updated only the figure title in `src/figures.py` and regenerated Figure 6. No data,
metric, portfolio, or calculation was changed.

### How I checked
I regenerated `fusion_before_after_sharpe.png`, visually checked the title and layout,
and ran a Python syntax check.

## Task 25 - Make Figure 6 Value Labels Horizontal

### What I wanted
I wanted the numeric value labels in Figure 6 to read horizontally rather than
vertically.

### Prompt(s)
"The data labels here should be horizontal, not vertical."

### What the assistant produced
The assistant changed all Figure 6 value labels to horizontal text.

### What was wrong or risky
The previous vertical labels were harder to read in a report figure and made the chart
feel less polished.

### What I changed and why
I changed only the label rotation in `src/figures.py`, regenerated Figure 6 and kept all
data, metric values and chart structure unchanged.

### How I checked
I regenerated `fusion_before_after_sharpe.png`, visually checked that the labels no
longer overlap, and ran a Python syntax check.

## Task 26 - Make Figure 6 X-Axis Labels Horizontal

### What I wanted
I wanted the Figure 6 x-axis category labels to read as `Equal Weight` and `Risk Parity`
and to remain horizontal.

### Prompt(s)
"For Figure 6, change the x-axis category labels to \"Equal Weight\" and \"Risk Parity\"
and keep them horizontal."

### What the assistant produced
The assistant kept the two category labels as `Equal Weight` and `Risk Parity` and
changed their rotation to horizontal.

### What was wrong or risky
The previous angled labels were readable but less clean for a publication-style report
figure.

### What I changed and why
I changed only the x-axis tick label rotation and alignment in `src/figures.py`,
regenerated Figure 6 and left all metric values and calculations unchanged.

### How I checked
I regenerated `fusion_before_after_sharpe.png`, visually checked that the labels are
horizontal and not crowded, and ran a Python syntax check.

## Task 27 - Clarify Figure 6 Turnover Metric

### What I wanted
I wanted Figure 6 to label turnover more precisely as an average monthly metric.

### Prompt(s)
"Please change the chart label to Average monthly turnover."

### What the assistant produced
The assistant changed the fifth Figure 6 panel title from `Average turnover` to `Average
monthly turnover`.

### What was wrong or risky
The shorter title could be ambiguous because turnover is measured at the monthly
rebalance frequency, not as a daily or annual cost.

### What I changed and why
I updated only the panel title in `src/figures.py` and regenerated Figure 6. No metric
value or calculation was changed.

### How I checked
I regenerated `fusion_before_after_sharpe.png`, visually checked that the longer panel
title fits, and ran a Python syntax check.


## Task 28- Fix Streamlit OOS Window Card and Fund Explorer Growth Caption

### What I wanted
I wanted two small Streamlit presentation fixes without changing any submitted data or
report numbers. The app needed a readable OOS window card and a clearer explanation of
why the Fund Explorer growth chart shows fewer funds than the full table.

### Prompt(s)
"1. The OOS window card is truncated. Please display it as either '2021-2023' or the
full date range in a smaller readable font. 2. In Fund Explorer, the Growth of $1 chart
currently shows fewer funds than the full table. Please add a short caption explaining
whether the chart shows the selected funds, filtered funds, or top displayed funds. Do
not change the underlying fund_returns.csv data or any report numbers. 3. Do not rerun
the backtest, optimiser, VADER, or sentiment scoring."

### What the assistant produced
The assistant changed the top-level OOS window metric to display `2021-2023` and added a
Fund Explorer caption explaining that the Growth of $1 chart shows the top five
displayed funds after the current filters and sorting.

### What was wrong or risky
The previous full-date OOS metric could be visually truncated in the Streamlit metric
card. The Fund Explorer chart used only the first five displayed funds, but without a
caption a reader could incorrectly assume the chart covered every fund shown in the
table.

### What I changed and why
I made only display-level changes in `streamlit_app.py`. The underlying CSV files,
backtest, optimiser, VADER scoring, sentiment signal construction and report numbers
were not changed.

### How I checked
I ran a Python syntax check on `streamlit_app.py` and reviewed the code change to
confirm it only affects Streamlit labels and captions.

## Task 29 - Improve Streamlit Fund Explorer Growth Chart Readability

### What I wanted
I wanted the Fund Explorer Growth of $1 chart to be easier to read without changing any
submitted fund return data or report numbers.

### Prompt(s)
"This image looks like a great candidate for you to make some adjustments to."

### What the assistant produced
The assistant revised the Streamlit growth chart styling. It changed the y-axis label
from `Portfolio value` to `Growth of $1`, removed the large legend, added direct
endpoint labels with terminal values, added a baseline at 1.0, used cleaner gridlines,
and formatted the date ticks more clearly.

### What was wrong or risky
The previous chart used a large legend, an imprecise y-axis label, and did not label
terminal values directly. Because crypto growth dominated the scale, the chart was
harder for an investor to interpret quickly.

### What I changed and why
I made only presentation-level changes in `streamlit_app.py`. The chart still reads the
same precomputed fund return data and compounds the same OOS daily returns. No backtest,
optimiser, VADER model, sentiment scoring, CSV file, or report number was changed.

### How I checked
I ran a Python syntax check on `streamlit_app.py` and reviewed the chart code to confirm
the edits affect labels, tick formatting, the baseline and endpoint annotations only.

## Task 30 - Fix Streamlit Growth Chart Endpoint Label Overlap

### What I wanted
I wanted the Streamlit Fund Explorer Growth of $1 chart to remain readable after direct
endpoint labels were added. The main issue was that the right-side labels and terminal
values overlapped, especially for crypto funds and the lower-growth comparison funds.

### Prompt(s)
"The chart still has a problem. Please inspect it yourself and adjust what is wrong. The
main issue I want fixed is that labels and terminal values such as Crypto Equal Weight
overlap with other labels, which is not acceptable."

### What the assistant produced
The assistant revised only the endpoint-label placement logic in `streamlit_app.py`. It
increased the minimum vertical spacing between endpoint labels, expanded the y-axis
limits to leave room for shifted labels, and added subtle leader lines from each shifted
label back to its actual terminal endpoint.

### What was wrong or risky
The previous endpoint-label algorithm placed labels too close to their terminal values
when final fund values were similar. This made the chart difficult to read and could
confuse a marker about which terminal value belonged to which fund.

### What I changed and why
I changed only the chart presentation logic. Labels are now automatically spaced apart
while the underlying growth paths and terminal values remain unchanged. Leader lines
preserve the connection between each label and its true endpoint, so readability
improves without changing the data.

### How I checked
I ran `python3 -m py_compile streamlit_app.py` and confirmed the edit only affects label
positioning, y-axis padding and leader-line styling. No backtest, optimiser, VADER
scoring, sentiment signal construction, CSV file, or report number was changed.

## Task 31 - Restore Full Y-Axis Range in Streamlit Growth Chart

### What I wanted
I wanted only the y-axis of the Streamlit Fund Explorer Growth of $1 chart fixed so the
full crypto growth path is visible again. Fund selection, endpoint labels, return data
and calculations should not change.

### Prompt(s)
"Please fix only the y-axis of the Growth of $1 chart. Make it like the earlier
full-range version so the lines are not clipped, but do not change the Equal Weight
labels, endpoint labels, selected funds, or underlying data."

### What the assistant produced
The assistant revised the y-axis limit calculation so high-growth paths use the maximum
reached anywhere along the plotted growth series, not only the terminal values. This
restores a full y-axis range for crypto-dominated charts while keeping the
endpoint-label spacing logic.

### What was wrong or risky
After the endpoint-label overlap fix, the visible y-axis could become too tight around
terminal values and crop high interim crypto spikes. This was a presentation bug: the
underlying fund returns and terminal labels were correct, but the chart understated the
path risk.

### What I changed and why
I changed only the y-axis upper-limit logic in `streamlit_app.py`. The fund list,
endpoint labels, compounded growth calculation, CSV data and report numbers were
unchanged.

### How I checked
I ran `python3 -m py_compile streamlit_app.py` and confirmed the edit only affects
display-level chart logic.

## Task 32 - Upgrade SignalHarbor App Against Week 10 Product Requirements

### What I wanted
I wanted the Streamlit app to better match the Week 10 product requirements for a
high-mark Part B submission. The app already ran, but the teacher's example showed that
a fund fact sheet should include the same core numbers, a Growth of $1 line, drawdown
and holdings. I also wanted the sentiment and methodology pages to look less like raw
code output.

### Prompt(s)
"Please modify the app. Fix the issues you identified: add the selected-fund Growth of
$1 chart to the Fact Sheet, improve the sentiment analytics display, make Methodology
more investor-facing, and improve Portfolio Builder if needed. Do not change CSV data,
report numbers, or rerun the backtest, optimiser, VADER or sentiment scoring."

### What the assistant produced
The assistant revised `streamlit_app.py` only. It added a selected-fund Growth of $1
chart to the Fact Sheet tab, placed it next to the drawdown chart, and kept holdings and
weights below. It changed the sentiment page to default to one selected sector for the
lagged coverage-aware signal, added an explanatory note, and moved multi-sector
comparison into an expander using a 21-day rolling average. It renamed technical
sentiment table columns into investor-readable labels and renamed fusion experiments
from `base` and `sentiment_augmented` to `Base` and `Sentiment fusion`. It added a fee
slider and net growth line to Portfolio Builder, and replaced the visible full audit
table in Methodology with a clean audit summary plus a full technical table expander.

### What was wrong or risky
The Fact Sheet previously had a Growth of $1 metric card but no selected-fund Growth of
$1 time-series chart, which made it weaker than the Week 10 fund fact sheet example. The
sentiment page could look noisy if too many daily sector signals were displayed
together. The Methodology audit table was useful but too technical as the default
visible table. Portfolio Builder allowed custom allocations but did not show fee/net
growth sensitivity, which the lecture suggested as part of a product-style allocation
tool.

### What I changed and why
I changed only app presentation and display logic. The app still reads precomputed files
from `results/` and does not recompute fund returns, portfolio weights, sentiment scores
or fusion results. The changes make the app more clearly satisfy the product journey:
compare funds, read a fact sheet, inspect sentiment analytics, build an allocation, and
understand methodology and limitations.

### How I checked
I ran `python3 -m py_compile streamlit_app.py`, ran `python3 scripts/check_handin.py`,
and opened the app at `http://localhost:8501/`. All five tabs loaded without Streamlit
errors. `check_handin.py` reported 22 checks passed, with only the reminder to delete
`__pycache__/` and `*.pyc` before zipping.

## Task 33 - Make Sentiment Analytics Readable and Check Default Allocation Weights

### What I wanted
I noticed that the default Sentiment Analytics chart showed the lagged coverage-aware
z-score, which was too noisy for a reader and did not look like the teacher's
requirement for a sector sentiment index over time. I also wanted to confirm whether the
Portfolio Builder allocation table was correctly showing 33.33% for each of the three
default funds.

### Prompt(s)
"The first sentiment chart is not right. It does not fit the requirement and readers
cannot understand it. Also, are those allocation data really all 33.33%? Please check."

### What the assistant produced
The assistant checked the underlying `sector_sentiment_index.csv` and confirmed that the
raw lagged coverage-aware signal ranges roughly from negative to positive z-score
spikes, while the finance-adjusted 21-day sentiment series stays on a clearer 0-100
index. It changed the default Sentiment Analytics chart to use
`finance_vader_rolling_21d` with the displayed label "Finance-adjusted sentiment index,
21-day average". The raw lagged trading signal remains available from the dropdown, but
is no longer the default chart. The assistant also confirmed that the Portfolio Builder
defaults use three selected funds with equal input weights of `100 / 3`, so each
normalised allocation is exactly one third internally and appears as 33.33% after
rounding.

### What was wrong or risky
Showing the raw lagged z-score as the first chart made the sentiment page look like a
technical diagnostic rather than an investor-facing sector sentiment index. The repeated
33.33% allocation values could also confuse a reader because three rounded values
display as 99.99%, even though the internal weights sum to 100%.

### What I changed and why
I changed only the app display logic. The default sentiment plot now shows a smoothed
finance-adjusted 0-100 sector sentiment index, which is easier for a marker to
interpret. I added a caption explaining that values above 50 indicate more positive news
tone and the 21-day average smooths daily headline noise. I also added a Portfolio
Builder caption explaining that displayed allocations are normalised from user inputs
and sum to 100%, with small differences caused by rounding.

### How I checked
I ran `python3 -m py_compile streamlit_app.py`, ran `python3 scripts/check_handin.py`,
and refreshed the app at `http://localhost:8501/`. The Sentiment Analytics and Portfolio
Builder tabs loaded without errors.

## Task 34 - Restore Coverage-Aware Signal as the Default Sentiment View

### What I wanted
I wanted the Sentiment Analytics tab to keep the main innovation signal as the default
view while still being readable for a marker. The previous revision made the chart
cleaner by defaulting to the 0-100 display index, but that hid the coverage-aware
trading signal that is central to the project.

### Prompt(s)
"The new sentiment chart is cleaner, but it now shows the 0-100 display index rather
than the main coverage-aware trading signal. Please revise the Sentiment Analytics tab
so the user can choose between: 1. 'Sentiment display index, 0-100' and 2.
'Coverage-aware lagged trading signal'. Set the default to 'Coverage-aware lagged
trading signal', using `finance_vader_coverage_adjusted_signal_lag1`. For the
coverage-aware signal: chart title 'Coverage-aware sector sentiment signal', y-axis
label 'Coverage-aware lagged z-score, 21-day average'. For the 0-100 display index:
chart title 'Sector sentiment index over time', y-axis label 'Sentiment index, 0-100'.
Keep the 21-day average for readability. Add a note saying the coverage-aware signal is
lagged before trading and scaled by prior news coverage, while the 0-100 index is for
investor display only. Do not rerun VADER, sentiment scoring, backtest, or optimisation.
Do not change CSV data or report numbers."

### What the assistant produced
The assistant changed the Sentiment Analytics selector to two investor-readable options:
`Coverage-aware lagged trading signal` and `Sentiment display index, 0-100`. The default
is now the coverage-aware signal based on `finance_vader_coverage_adjusted_signal_lag1`.
The plotting function applies a 21-day rolling average to the coverage-aware signal for
readability, uses the requested chart title and y-axis label, and keeps the 0-100 index
as a selectable display view.

### What was wrong or risky
Defaulting to the 0-100 display index made the page easier to read but weakened the
connection to the project's main coverage-aware sentiment innovation. Showing the raw
daily signal without smoothing was also too noisy, so the fix needed to keep the signal
but smooth the displayed path.

### What I changed and why
I changed only Streamlit display logic. The app still reads the same precomputed
`sector_sentiment_index.csv`; it does not recompute VADER scores, sentiment signals,
backtests, optimiser outputs, CSV data or report numbers.

### How I checked
I ran `python3 -m py_compile streamlit_app.py`, ran `python3 scripts/check_handin.py`,
and refreshed `http://localhost:8501/`. The Sentiment Analytics tab loaded without
errors and defaulted to `Coverage-aware lagged trading signal`.











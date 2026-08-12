# AI Notes - FINS3645 Part B

## How I Used AI

I used AI as a coding, checking and drafting assistant for Project B. I first asked it
to read the project brief, rubric and Week 10 guidance so that the implementation
matched the required deliverables: OOS funds, performance metrics, figures, sentiment
evidence, Streamlit app and AI workflow records.

I did not treat the AI output as automatically correct. I used AI to speed up coding
and drafting, but I checked the important finance and data assumptions myself before
using the outputs in the report. The main checks were about calendar handling,
look-ahead bias, portfolio constraints, Sharpe ratio formula, turnover definition,
sentiment timing and whether the report overclaimed the results.

AI was used for drafting and editing support, but the final report interpretation,
wording and submission decisions were reviewed and finalised by me.

## What I Directed AI To Do

- Build a clean Part B data layer for equity returns, crypto returns, combined returns
  and mapped equity headlines.
- Run the monthly walk-forward OOS backtest for 12 funds across Equity, Crypto and
  Combined universes.
- Add audit outputs so the backtest could be checked rather than only trusted.
- Build the equity sector sentiment index and the coverage-aware lagged trading signal.
- Test the sentiment fusion overlay as an OOS investment experiment.
- Generate the required figures from saved result files.
- Build a lightweight Streamlit app that loads precomputed CSV files instead of
  rerunning backtests, optimisation or VADER at runtime.
- Help draft and polish the report, while keeping the final interpretation evidence
  based and finance focused.

## Human Decisions and Checks

- I required equity returns to follow the equity trading calendar.
- I required crypto returns to be calculated on the natural crypto calendar before any
  alignment to the equity calendar for the Combined universe.
- I kept news sentiment as an equity-sector signal only, not a crypto signal.
- I required 252 annualisation for Equity and Combined funds, and 365 for Crypto funds.
- I checked that each fund had 36 monthly rebalances over the OOS period.
- I checked that the reported `46` was only the pooled number of unique rebalance dates
  across all universes, not the rebalance count for each fund.
- I required long-only, fully invested weights with no negative weights and weight sums
  close to one.
- I required strict no-look-ahead checks for both the OOS backtest and the sentiment
  fusion overlay.
- I required Risk Parity to be covariance-based equal risk contribution, not just a
  simple inverse-volatility shortcut.
- I required the Streamlit app to read saved results from `results/` and not rerun slow
  modelling steps on user clicks.

## Important AI Risks I Caught

- **Misleading rebalance summary:** The AI initially described `46` as rebalance months.
  I checked the dates and clarified that each fund had 36 monthly rebalances, while 46
  was only the pooled unique-date count across universes.
- **Sharpe ratio formula:** The AI initially used CAGR divided by annualised volatility.
  I corrected this to the course formula: average daily excess return divided by daily
  standard deviation, multiplied by the square root of the annualisation factor.
- **Calendar risk:** I checked that Equity and Combined use equity trading days, while
  Crypto uses calendar days.
- **Risk Parity definition:** I did not accept Risk Parity as a label until the
  risk-contribution dispersion checks showed that the optimiser was close to equal risk
  contribution.
- **Sentiment look-ahead:** I required the sentiment signal to be lagged before trading
  and checked that signal-date violations were zero.
- **Turnover definition:** I changed turnover from simple target-weight differences to
  implementable rebalance turnover, comparing new target weights with pre-rebalance
  drifted weights.
- **Overclaiming innovation:** The sentiment overlay did not improve Sharpe in the OOS
  test, so I presented it as an honest negative result and an analytics feature, not as
  proven alpha.
- **Figure and report consistency:** I revised figures and wording when charts were too
  crowded, used the wrong visual emphasis, or did not match the evidence discussed in
  the report.

## Final Verification

Before finalising the submission, the AI helped generate and revise a report draft. I
then checked the draft against the brief, Week 10 guidance and the generated results,
rewrote the analysis in my own words, and finalised the submitted report. I also reran
the main pipeline and ran the hand-in checker:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_part_b.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_report.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_handin.py
```

The final checks passed. I also inspected the Streamlit app locally to confirm that it
loaded precomputed result files and did not rerun backtests, optimisation or sentiment
scoring.

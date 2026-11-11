# Episode data

`build_episodes.py` downloads daily series from FRED's public CSV endpoint and writes one file per window to `data/episodes/<id>.json`. `validate_episodes.py` checks each file's structure and reports gaps. Both use only the Python standard library.

## Series

| FRED id | Use in the game | Required |
| --- | --- | --- |
| `DGS3MO`, `DGS2`, `DGS5`, `DGS10`, `DGS30` | Treasury curve for pricing, cash, and repo | Yes |
| `VIXCLS` | Stress multiplier, agent biases, margin penalty | Yes |
| `SP500` | Equity futures and the balanced benchmark | Yes |
| `DFF` | Policy-rate context in briefings | No |
| `DFII10`, `T10YIE` | Real yield and breakeven context | No |
| `DTWEXBGS` (falls back to `DTWEXM`) | Dollar move for foreign-buyer agents | No |

Each episode file records the start, end, lowest, and highest value of every series inside the window, with dates, plus the daily path the engine uses for worst-point margin checks. It also records which series are missing, any fallback used, the trailing 1-year 10y average, and the 2s10s slope at both ends.

## Analyst panel

Each file's `derived.analyst_panel` holds the statistics players see at the briefing, computed only from observations before the window opens: realized daily volatility over 20 and 60 days and the 20-day change for the 2y and 10y (in bp), the 10y against its trailing 1-year average, the S&P 20-day return and daily volatility, the prior VIX close (rounded), and the number of trading days in the window. Every value is a change, spread, or volatility, so the engine's hidden curve offset leaves the panel unchanged and it cannot be matched to a date.

## Current build (2026-11-09)

All 14 files pass the schema check. Six windows lack a complete equity series, because FRED's `SP500` starts on 2016-11-07:

| Window | Gap |
| --- | --- |
| Bond rout 1994, flight to quality 2008, taper tantrum 2013 | No S&P 500 data |
| Practice 2004 and 2011 | No S&P 500 data |
| Practice 2016 | S&P 500 starts a week into the window |

`SP500` is also a price index, so dividends are missing even where it is available. A total-return source is still to be chosen; Baruch library access to CRSP or Bloomberg is the first thing to check. 1994 also lacks the TIPS series, which begin in 2003, and uses `DTWEXM` for the dollar.

Two findings from the build affect the spec:

- **1994:** over the window the 10y ran 5.81% to 7.91% (high 8.05%), not about 5.2% to 8% as first written. The 5.2% level was the late-1993 low.
- **2020 dash for cash:** start to end, the 10y fell from 1.46% to 0.76%. The selloff (0.54% on 2020-03-09 to roughly 1.2% by 2020-03-18) happens inside the window, so a single rebalance at the start sees a net rally. Starting the window on 2020-03-09 would make the round itself show the selloff.

## Licensing

Built files are not committed (see `.gitignore`). Treasury yields and the dollar indexes are Federal Reserve data. `SP500` (S&P Dow Jones Indices) and `VIXCLS` (Cboe) carry their own terms on FRED. The licensing check must be done before any built data is committed, published, or served to players.

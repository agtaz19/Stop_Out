# Roadmap

Ten weeks to a pilot is an estimate for one or two part-time developers. Each phase lists its exit criterion.

| # | Phase | Status | Exit criterion |
| --- | --- | --- | --- |
| 0 | Repository setup | Done | First CI run passes |
| 1 | Data pipeline | Built; equity source open | Every episode file passes the schema check |
| 2 | Engine core | Started (scoring) | The spec's worked examples pass as unit tests |
| 3 | Calibration | Not started | No passive strategy in the top quartile; bid-to-cover 2.3 to 2.6; under 1 false flag per session |
| 4 | Server | Not started | A full simulated session runs headless |
| 5 | Clients | Not started | Each screen matches its mockup |
| 6 | Content and prep kit | Not started | Every episode pack reviewed by a second person |
| 7 | Testing | Not started | No dropped locks with 100 bots plus spectators |
| 8 | Pilot | Not started | One 5-person remote session and one 50+ in-person session with no forced restarts |

## Phase 1: data pipeline

- [x] Window definitions for 9 game episodes and 5 practice windows (`data/episode_windows.json`)
- [x] FRED builder with caching, daily paths, window highs and lows, trailing 1-year 10y average
- [x] Schema validator with missing-series and partial-coverage reporting
- [ ] Choose an equity total-return source for 1994, 2008, 2013, 2004, and 2011 (FRED's S&P 500 starts 2016-11-07)
- [ ] Licensing check on FRED, S&P, and Cboe data before any built file is committed or published
- [ ] Decide on the 2020 window (see data/README.md)

## Phase 2: engine core

- [x] Interval score, percentile ranks with averaged ties, round points, shrunk information ratio
- [ ] Exact bond repricing with curve interpolation
- [ ] S&P futures, steepener with carry, repo, initial margin
- [ ] Trading cost with the VIX stress multiplier
- [ ] Variation margin at the worst point, buffer, shortfall, forced sales
- [ ] Drawdown stop on return indices; fund blow-up and relaunch
- [ ] Bank AFS/HTM accounting and deposit runs; pension liability and funded status
- [ ] Auction clearing (competitive, non-competitive, proration, 35% cap, tail impact)
- [ ] Market agents and house funds with seeded draws
- [ ] Full scoring: normalized excess with window-scaled tau, forecasts, penalties, tie-breaks
- [ ] Surveillance monitors
- [ ] Event log and replay

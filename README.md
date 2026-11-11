# Stop-Out

A facilitator-led Treasury and equity trading game for 5 to 100 players, run in person or remotely around one shared host monitor. Players join as a team or solo and are assigned a fund of $10M, $100M, or $500M. A team splits its fund among its members; a solo player runs the whole fund. Funds trade eight historical market episodes with the dates hidden, against hidden, rules-driven market agents. Funds are scored on risk-adjusted excess return against their mandate and on how well calibrated their yield forecasts are.

**Status:** phase 1 of 8. The repository, CI, the first scoring functions, and the episode data pipeline are in place; the game engine, server, and clients are not built yet. The full game design is in the shared design spec: [Stop-Out: Game Design Spec](https://claude.ai/artifact/2QjkGqc7zLxyutMdHuRNLQ), with engine mechanics in its [Engine spec tab](https://claude.ai/artifact/2QjkGqc7zLxyutMdHuRNLQ#2ae9412c-4394). Screen mockups are in [Stop-Out Screen Mockups](https://claude.ai/artifact/2TAvXw4j64N63stD9ECHpz). Both are private until shared by their owner; see [docs/README.md](docs/README.md).

## Getting started

Requirements: Node 22 or later, pnpm 10 (`corepack enable`), and Python 3.11 or later. The data pipeline uses only the Python standard library.

```bash
pnpm install
```

```bash
pnpm typecheck && pnpm test
```

```bash
pnpm test:data
```

Build the episode data from FRED, then check it:

```bash
python3 data/build_episodes.py
```

```bash
python3 data/validate_episodes.py
```

Built files land in `data/episodes/` and are not committed until the data licensing check is done. See [data/README.md](data/README.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Session at a glance

| Item | Default |
| --- | --- |
| Players | 5 to 100 |
| Entry | Team of 2 to 5 players, or solo |
| Fund sizes | Small $10M, Mid $100M, Large $500M (drawn by the server) |
| Desk roles | Macro fund, Bank treasury, Pension (LDI), Balanced 60/40 |
| Rounds | 8 (6 for groups under 13), drawn from 9 historical episodes, dates hidden |
| Round length | About 7 minutes in person, about 8 minutes remote |
| Formats | In person, remote, or hybrid, all around one shared host monitor |
| Market agents | About 25 hidden, rules-driven auction bidders, plus hidden house funds |

### Session formats

| Item | In person | Remote |
| --- | --- | --- |
| Shared monitor | Projector or TV running the host view | Facilitator screen-shares the host view in the group's own call (Zoom, Discord, or any room they choose); a read-only spectator link is the backup |
| Joining | QR code and room code on the monitor | Room code posted in the call chat |
| Team discussion | Teams sit together, apart from other teams | Everyone stays in one shared call, with no breakout rooms; teams talk however they prefer, such as a private chat |
| Timers | Default | Huddle and trading window each +30s |
| Copy-timing monitor | ≤ 15s, ≥ 3 rounds | ≤ 30s, ≥ 2 rounds |

### Scaling

| Players | Funds (typical) | Rounds | Roles in play | House funds | Auctions |
| --- | --- | --- | --- | --- | --- |
| 5–12 | 3–8, mostly solo | 6 | Macro fund, Balanced 60/40 | Added until there are 8 funds, hidden | 2 |
| 13–40 | 6–15 | 8 | 3–4 | Added until there are 8 funds, hidden | 3 |
| 41–100 | 12–30 | 8 | All 4 | 3, hidden | 3 |

### Round loop

1. **Briefing (60s):** the real release (FOMC redline, CPI table, payrolls, auction results), ending with 15 seconds in which every player privately submits their own 10y forecast.
2. **Desk huddle (60s):** teams discuss and solo players plan. On a team, the desk head (a role that rotates each round) may move up to 20% of fund capital between members. In auction rounds, a 60-second sealed bidding window follows, and the results are shown before trading opens.
3. **Trading window (120s):** each player sets weights for their capital. Positions are hidden from other funds.
4. **Forecast (30s):** the desk head submits the fund's 80% interval for the 10y yield, after the team has seen every member's locked forecast and their median. Solo players submit their own.
5. **Lock and resolve:** the server locks inputs, plays the curve move, and posts P&L.
6. **Debrief (90s):** aggregate positioning is shown first, then the debrief card; the facilitator leads the discussion.

---

## Funds and capital

Players choose to join a team or play solo. By default, the server draws each fund's **tier** and **role** at random against quotas when registration closes; the recommended tier mix is 40% small, 40% mid, and 20% large, and the facilitator may change it for any session. The facilitator can override the draw for any fund, setting its role and tier, and the draw fills the rest. Overrides are made only after registration closes and are written to the event log. A team divides its fund equally among its members. Capital persists across rounds, and a player who does not submit keeps the prior round's positions.

| Tier | Fund size | Per member, team of 5 | Repo spread over bills | Auction access | Trading impact |
| --- | --- | --- | --- | --- | --- |
| Small | $10M | $2M | +75bp | Competitive through a dealer (indirect), or non-competitive ≤ $10M | Lowest |
| Mid | $100M | $20M | +40bp | Competitive as a direct bidder, or non-competitive ≤ $10M | Moderate |
| Large | $500M | $100M | +15bp | Competitive only, as a primary dealer with a bidding obligation | Highest |

### Instruments

| Instrument | Funding | DV01 per $100M of position (approx.) | Half-spread h |
| --- | --- | --- | --- |
| Cash / T-bills | Residual | ~$0 | 0 |
| 2y Treasury | Funded | ~$19k | 0.5bp |
| 10y Treasury | Funded | ~$85k | 1.5bp |
| 30y Treasury | Funded | ~$165k | 3.0bp |
| S&P 500 futures | Margin | n.m. | 0.5bp |
| 2s10s steepener | Margin, DV01-matched | 10% weight = $5k per leg per $100M of capital | 1.0bp |

Negative cash is repo borrowing at the bill rate plus the tier's spread. Bonds are constant-maturity and rolled each round:

$$r \approx y_0\,\Delta t - D_{\text{mod}}\,\Delta y + \tfrac{1}{2}\,C\,(\Delta y)^2$$

Trading cost uses the square-root impact law, with $Q$ the notional traded this round, $V$ the liquidity per round ($2B default), and $\eta = 10$bp:

$$\text{cost}_{\text{bp}} = h\,m_r + \eta \sqrt{\frac{Q\,m_r}{V}}, \qquad m_r = \min\!\big(4,\; \max(1,\; \text{VIX}_r / 20)\big)$$

In calm markets ($m = 1$), a large fund buying $500M of 10s pays about 6.5bp, and a small fund buying $10M pays about 2.2bp. The stress multiplier $m$ makes trading realistically expensive in a panic, up to 4× at a VIX of 80.

**Initial margin:** S&P futures need 8% of notional and each steepener leg 2%, posted in cash. The phone blocks allocations with too little cash. No repo haircuts are applied; role gross limits and tier repo spreads stand in for them.

**Drawdown stop** (checked on round-end marks): a position that ends a round 10% below its peak can deploy only half its capital the next round, and the fund loses 20 points. The app calls this the drawdown stop so it is not confused with the auction stop-out yield. It is measured on each share's return index (like NAV per unit), so capital moves between members cannot reset or dodge it. That position is a team member's share, or a solo player's whole fund. On a team, the freed half goes to the desk head.

### Role limits (as a share of capital)

| Role | Share of funds | Benchmark | Limits | Role event | Risk budget τ |
| --- | --- | --- | --- | --- | --- |
| Macro fund | 30% | Cash | Gross ≤ 500%, DV01 ≤ $300k per $100M, equity ±200% | None | 6.0% |
| Bank treasury | 20% | 70% 2y / 30% 10y | Long-only bonds ≤ 100%, no equity, DV01 ≤ $100k per $100M; AFS or HTM accounting | Deposit run: chance rises with hidden HTM losses; 20% withdrawn | 2.0% |
| Pension (LDI) | 20% | Liability (30y-like) | Bonds ≤ 150% via repo, equity ≤ 50% | Collateral call at the window's worst point; shortfall beyond the cash and 2y buffer forces a sale | 3.0% |
| Balanced 60/40 | 30% | 60% S&P / 40% 10y | Long-only, ±20pp per weight | None | 1.5% |

The phone client enforces limits as the player types, and the server validates them again at lock.

---

## Scoring

Each fund's score is out of 1,000 points and built from percentile ranks rather than raw P&L, so an all-in bet cannot win the session on luck. Teams and solo players share one leaderboard. Hidden house funds count in every percentile rank but never appear on it; the leaderboard shows points and order among human funds only, and the rules tell players they are ranked against the whole market. Fund size does not enter the score.

The leaderboard is shown after rounds 3 and 6 (rounds 2 and 4 in a six-round session) and at the final reveal, not after every round, so trailing funds have less reason to swing for the fences late.

| Component | Points |
| --- | --- |
| Round performance (rank of normalized excess return, each round) | 500 |
| Risk-adjusted game return (rank of shrunk information ratio) | 300 |
| Forecast calibration (rank of 80% interval score, each round) | 200 |
| Penalties: drawdown stop −20 each; margin shortfall −20 to −60, scaled by the window's peak VIX; blow-up −100 | −20 to −100 |

Normalized excess return, its round-by-round percentile, and round points:

$$\tilde{e}_{i,r} = \frac{R_{i,r} - B_{\text{role},r}}{\tau_{\text{role}}\sqrt{\Delta t_r / 0.25}}, \qquad p_{i,r} = \frac{N - k_{i,r}}{N - 1}, \qquad A_i = 62.5 \sum_{r=1}^{8} p_{i,r}$$

Shrunk information ratio, with floor $s_0 = 0.25$:

$$\mathrm{IR}^{*}_i = \frac{\bar{\tilde{e}}_i}{\sqrt{s_i^{2} + s_0^{2}}}$$

Interval score for the 10y forecast, with $\alpha = 0.2$, in basis points (lower is better):

$$\mathrm{IS} = (u - l) + \frac{2}{\alpha}(l - x)\,\mathbf{1}\{x < l\} + \frac{2}{\alpha}(x - u)\,\mathbf{1}\{x > u\}$$

**Individual forecasts** are submitted privately in the last 15 seconds of the briefing and lock before the huddle, so members' views stay independent. When the huddle opens, the whole team sees every member's locked range and the median; the only honor rule is not saying a number aloud during the entry window. They do not enter the fund's score; they feed Top PM and Best Forecaster, and the debrief compares each desk head's call with the median of the team's members.

A six-round session scales round points to 500 / 6 per round and forecast points to 200 / 6 per round.

**Awards:** Fund of the Session, Best Fund per role, Best Fund per size tier, Best Solo, Top PM (team members, scored out of 1,000 on member-level A and B plus their individual forecasts, revealed at the end), and Best Forecaster (individual forecasts, all players). House funds are not eligible. A dollar P&L table is shown at the end for realism and is not scored. Prizes carry real value, so awards are confirmed only after the facilitator clears every open flag, and the event log is kept until prizes are paid.

---

## Auctions

Three rounds (two under 13 players) include a 10y auction: a 60-second sealed bidding window right after the huddle, with results shown before trading opens. Bids clear at a single price.

- The offering is 20% of total player fund capital, with a $500M minimum.
- Each fund bids **competitively or non-competitively** in an auction, never both (the actual Treasury rule).
- **Non-competitive:** size only, up to $10M, filled in full at the stop-out before any competitive bid. Open to small and mid funds; large funds must bid competitively.
- **Competitive:** up to 3 bids of yield (to 0.1bp) and size, open to every tier. Small funds bid through a dealer and count as indirect, mid funds bid directly, and large funds bid as primary dealers.
- Large funds must bid for at least their pro-rata share within 3bp of the when-issued (WI) yield. If no large human fund exists, a house dealer agent carries the obligation.
- Bid sizes are checked against limits as if fully filled.
- Market agents supply most of the demand.
- Non-competitive bids fill first. Competitive bids fill from the lowest yield up; everyone pays the stop-out, and bids at the stop-out are prorated.
- No bidder is awarded more than 35% of the offering.
- The secondary 10y moves by $\kappa \times \text{tail}$, with $\kappa = 0.5$.

The host shows only the aggregate results a real auction release shows: high yield, WI, tail, bid-to-cover, allotted at high, and the dealer, direct, indirect, and non-competitive shares.

---

## Market agents

Agents are rules-driven: each is a short set of fixed rules plus a seeded random draw. No AI is involved. Players never see agent counts, parameters, or individual bids.

| Agent | Auction class | Default count | Base behavior | Biases |
| --- | --- | --- | --- | --- |
| Foreign official | Indirect | 4 | Large, price-insensitive bids within ±0.5bp of WI | Size ×0.6 in tariff or sanctions episodes; ×1.2 in a flight to quality |
| Foreign private | Indirect | 6 | Bid more when the 10y is above its 1-year average | Falls when the dollar drops more than 3% in a round |
| Domestic real money | Direct | 7 | Value buyers after selloffs | ×1.3 after a selloff of 40bp or more; quarter-end boost |
| Hedge funds | Direct | 7 | Follow the trend | ×0.4 and 1–2bp wider when VIX > 35 |
| House dealer | Dealer | 1 | Bids WI +1 to +3bp to absorb the remainder | Widens with VIX |

Bid rules for agent $j$ of type $k$. Here $z_r$ is the market state: last round's 10y change, the 10y against its 1-year average, the 2s10s slope, VIX, and the dollar's change. $b_{k,r}$ is the scheduled bias for that episode's auction:

$$Q_j = \bar{Q}_k \exp\!\left(\beta_k^{\top} z_r + b_{k,r} + \sigma_k \varepsilon_j\right), \qquad y_j = y_{\text{WI}} + \mu_k + \gamma_k^{\top} z_r + \nu_k u_j$$

The agents are calibrated to cover about 1.6× the offering on average, so total bid-to-cover lands near 2.3–2.6.

**House funds** are a second kind of hidden agent. They trade the same instruments as players and count in the rankings, but never appear on the leaderboard, cannot win awards, and are left out of the crowd-positioning chart. Each follows one fixed strategy with noise: hugging its benchmark, following the trend in the 10y, or harvesting carry. Sessions under 41 players add them until there are 8 funds; larger sessions add 3.

Agent parameters and seeds stay on the server and are written to the event log, so every auction can be replayed exactly. The facilitator's end-of-session export shows who bought each auction.

---

## Analysis and fairness

Both fundamental and quantitative analysts can play with their own analysis:

- **Fundamental:** the full release in its real format, with consensus and the prior print, plus the window length and curve shape.
- **Quantitative:** an analyst panel at every briefing with trailing 20- and 60-day realized volatility and 20-day change for the 2y and 10y, the 10y against its 1-year average, the S&P 20-day return and volatility, the prior VIX close, and the trading days in the window. Players may bring their own models, backtested beforehand on the prep kit's unblinded practice windows.

**Blinding.** Every yield shown and priced is shifted by a hidden per-episode offset $o$ of 50 to 150bp in either direction, logged and revealed at the end:

$$o \sim \mathrm{Uniform}\big([-150, -50] \cup [50, 150]\big), \qquad o \ge 5 - \min y_{3m}, \qquad y' = y + o$$

Changes, spreads, curve shape, and durations are unchanged; only carry moves slightly. The analyst panel uses only changes and volatilities, so the offset leaves it unchanged and it cannot fingerprint a date. Own calculators, spreadsheets, and models are allowed on on-screen information; outside market data and news are not, and the attestation says so.

## Market integrity

Coordination within a fund is teamwork. Coordination between funds, including between a solo player and a team, is what the integrity rules address. The design makes collusion unprofitable first and detects it second.

**Design controls**

- Bounded rank-based scoring and split awards remove the payoff from mirror bets between funds.
- Tier and role are drawn, or set by the facilitator, only after registration closes, so no pact made before the game can rely on known mandates.
- Hidden, randomly biased agent demand makes coordinated auction bidding unreliable.
- Hidden house funds mean no group can work out from the leaderboard what rank a pact would secure.
- Positions, bids, and forecasts are hidden until lock. Only aggregate positioning is shown afterward.
- There are no trades between players or funds.
- Each device holds one player token and each roster name one token. The facilitator approves the roster and any device change.
- Resolution data is never sent to clients before lock.
- Every player confirms an attestation on joining.

**Surveillance monitors** (rule-based, run at every lock, flag to the facilitator):

| Monitor | v1 threshold | Action |
| --- | --- | --- |
| Mirror pair | Risk-vector cosine ≤ −0.8, both funds ≥ 70% of limits, in ≥ 3 rounds | Review; forfeit round points |
| Auction cluster | ≥ 3 human funds within 0.5bp of each other and ≥ 2bp above WI | Review; void awards |
| Copy timing | In person: ≤ 15s, cos ≥ 0.95, ≥ 3 rounds. Remote: ≤ 30s, ≥ 2 rounds | Warning |
| Account integrity | Token on two devices, device tied to two players, or one roster name on two funds | Block; review |

The risk vector is DV01 by tenor and equity exposure, measured per $100M of capital and divided by role limits, so funds of every size compare fairly. The enforcement ladder is flag, private warning, forfeit of round points, then disqualification from awards. A person makes every sanction decision.

---

## Architecture (planned)

```
 Phones (players)   Shared monitor (host)   Spectator links   Laptop (facilitator)
        \                   |                    |                 /
         \               WebSocket (read-only for spectators)     /
          +-------------------- Game server ---------------------+
              |            |            |            |
         Round engine   Agents      Scoring    Surveillance
              \            |            |            /
                 Append-only event log (SQLite)
                               |
                  Episode data (JSON, prebuilt)
```

- **Server:** Node 20, TypeScript, Fastify and Socket.IO. A single process with session state in memory. It is authoritative for prices, locks, limits, and agent bids.
- **Agents:** pure functions of (market state, scheduled bias, seeded draw). They run server-side only.
- **Event log:** every join, allocation, bid (human and agent), forecast, lock, flag, and sanction is appended to SQLite. Scores and flags are pure functions of the log, so any disputed result can be recomputed exactly.
- **Clients:** player (phone), host (shared monitor), spectator (read-only copy of the host view for remote viewers), and facilitator. They are built with Vite and plain CSS design tokens, and charts are hand-built SVG. No UI component kit.
- **Data:** a build-time Python script pulls FRED series into `data/episodes/*.json`. Nothing calls an external API during a session.
- **Hosting:** one small instance in a region near the players. Players join through a QR code or a 6-character room code.

### FRED series

`DGS3MO`, `DGS2`, `DGS5`, `DGS10`, `DGS30` (nominal curve), `DFII10` (10y real), `T10YIE` (10y breakeven), `DFF` (fed funds), `VIXCLS`, `DTWEXBGS` (broad dollar), `SP500`. FRED's `SP500` covers only about the last 10 years and has licensing limits. The 1994 and 2008 episodes need a separate equity total-return source.

---

## Repository layout

Folders marked *planned* arrive in later phases.

```
stop_out/
├── README.md
├── CONTRIBUTING.md
├── config/
│   └── session_default.yaml   # every tunable parameter
├── data/
│   ├── episode_windows.json   # 9 game episodes and 5 reserved practice windows
│   ├── build_episodes.py      # FRED -> data/episodes/<id>.json
│   ├── validate_episodes.py   # schema check and data-gap report
│   ├── tests/
│   └── episodes/              # built locally, not committed
├── packages/
│   └── engine/                # pure game logic (TypeScript)
│       ├── src/scoring/       # interval score, percentile ranks, round points, IR*
│       ├── src/pricing/       # planned: exact repricing, costs, margin
│       ├── src/auctions/      # planned: clearing and market agents
│       ├── src/surveillance/  # planned: the four monitors
│       └── test/
├── apps/                      # planned: server, player, host, spectator, facilitator
├── prep/                      # planned: desk prep kit and offline sandbox
└── docs/
    ├── README.md              # links to the spec and mockups
    └── ROADMAP.md             # phases and exit criteria
```

## Configuration

All tunable parameters live in one file so facilitators can adjust a session without touching code.

```yaml
session:
  format: in_person            # in_person | remote | hybrid
  rounds: auto                 # auto = 6 under 13 players, else 8
  episodes: shuffle
  hide_dates: true
  team_size: { min: 2, max: 5 }
  allow_solo: true

funds:
  assignment: draw             # draw | choose
  size_draw: log_uniform       # within the tier band, rounded to $1M
  facilitator_overrides: true  # set role and tier per fund after registration closes; logged
  tiers:
    small: { aum_band_usd: [5_000_000, 25_000_000],      repo_spread_bp: 75, auction: [competitive_indirect, noncompetitive] }
    mid:   { aum_band_usd: [50_000_000, 150_000_000],    repo_spread_bp: 40, auction: [competitive_direct, noncompetitive] }
    large: { aum_band_usd: [250_000_000, 1_000_000_000], repo_spread_bp: 15, auction: [competitive_dealer] }
  tier_mix: { small: 0.40, mid: 0.40, large: 0.20 }   # recommended; facilitator may change
  role_mix: { macro: 0.30, bank: 0.20, pension: 0.20, balanced: 0.30 }

timers_seconds:
  briefing: 45
  private_forecast: 15         # each player, before the huddle
  huddle: 60                   # +30 when remote
  trading: 120                 # +30 when remote
  forecast: 30                 # desk head enters the fund forecast
  debrief: 90

trading_costs:
  impact_eta_bp: 10
  liquidity_per_round_usd: 2_000_000_000
  half_spread_bp: { ust2y: 0.5, ust10y: 1.5, ust30y: 3.0, spx_fut: 0.5, steepener: 1.0 }
  stress_multiplier: { vix_base: 20, cap: 4 }
  forced_sale_cost_multiple: 3

risk:
  drawdown_stop: 0.10           # checked on round-end marks
  drawdown_stop_capital_cut: 0.50
  initial_margin: { spx_fut: 0.08, steepener_leg: 0.02 }
  repo_haircuts: none
  margin_check: worst_point     # daily path inside the window
  margin_shortfall_penalty: { base: 20, vix_base: 20, max_multiple: 3 }
  blow_up: { fund_drawdown: 0.35, penalty: 100, relaunch_seed: 0.25, retier: true }
  tau_window_scaling: sqrt      # tau * sqrt(dt / 0.25)
  desk_head_realloc_max: 0.20

scoring:
  weights: { rounds: 500, risk_adjusted: 300, forecast: 200 }
  penalty_per_drawdown_stop: 20
  ir_floor_s0: 0.25
  forecast_alpha: 0.20
  tau: { macro: 0.060, bank: 0.020, pension: 0.030, balanced: 0.015 }
  house_funds: { visible: false, min_entries: 8, large_session_count: 3 }
  leaderboard_after_rounds: auto   # auto = [3, 6] for 8 rounds, [2, 4] for 6; always shown at the end

auction:
  count: auto                  # auto = 2 under 13 players, else 3
  offering_share_of_aum: 0.20
  offering_min_usd: 500_000_000
  award_cap: 0.35
  dealer_obligation_bp: 3
  noncompetitive_max_usd: 10_000_000
  tail_impact_kappa: 0.5

agents:
  target_cover_multiple: 1.6
  counts: { foreign_official: 4, foreign_private: 6, real_money: 7, hedge_fund: 7, house_dealer: 1 }
  seed: random                 # stored in the event log, never sent to clients

blinding:
  curve_offset_bp: [50, 150]   # hidden per-episode shift, either sign; revealed at the end
  min_shifted_bill_bp: 5       # offsets that push the 3m bill below 0.05% are not drawn
  vix_rounding: 1              # VIX shown as a whole number
  sp500_indexed: true          # S&P shown as 100 at each window start

analyst_panel:
  show_window_length: true
  lookback_days: [20, 60]      # realized vol and changes from data before the window only

surveillance:
  mirror:  { cosine_max: -0.80, limit_use_min: 0.70, rounds_min: 3 }
  auction: { cluster_bp: 0.5, above_wi_bp: 2.0, funds_min: 3 }
  copy:
    in_person: { seconds_max: 15, cosine_min: 0.95, rounds_min: 3 }
    remote:    { seconds_max: 30, cosine_min: 0.95, rounds_min: 2 }
```

The values for τ, $s_0$, κ, η, the agent parameters, and the surveillance thresholds are starting points. Calibrate them with the simulation harness (phase 3) before the first live session. The targets:

- honest-fund false flags under 1 per session
- no passive strategy finishing in the top quartile
- total bid-to-cover between 2.3 and 2.6

---

## Roadmap

| Phase | Scope |
| --- | --- |
| v1 | Blind historical mode; in-person, remote, and hybrid; team (2–5) or solo entry; 3 fund tiers; 4 roles; auctions with agents; hidden house funds; scoring; 4 monitors; desk prep kit; CSV export |
| v2 | Round 0 practice round, mid-window headline interrupts, season table across sessions, scenario editor |
| v3 | Sandbox mode with an FOMC team and a factor-model market |

## Engine mechanics (summary)

The full specification, with every formula, is in the Engine spec tab.

**Returns.** Bonds are bought at par each round and repriced exactly at the end (remaining maturity $n - \Delta t$, yield interpolated linearly from the ending curve), which captures carry, roll-down, duration, and convexity together:

$$r_n = \frac{P\big(c,\; n - \Delta t,\; y_1(n - \Delta t)\big) + 100\,c\,\Delta t}{100} - 1, \qquad c = y_{n,0}$$

S&P futures earn total return minus the bill rate. The steepener (both legs financed in repo at $\rho$) pays the curve change plus carry:

$$\text{P\&L}_{\text{st}} = \text{DV01}_{\text{leg}} \times 10^{4} \left[ (\Delta y_{10} - \Delta y_{2}) + \Delta t \left( \frac{y_{2,0} - \rho}{D_2} - \frac{y_{10,0} - \rho}{D_{10}} \right) \right], \qquad \text{DV01}_{\text{leg}} = 5 \times 10^{-4}\, w\, K$$

Negative cash pays the bill rate plus the tier's repo spread. Trading cost is charged on the change from the drifted starting position.

**Risk budget by window length.** $\tau_{\text{role},r} = \tau_{\text{role}}\sqrt{\Delta t_r / 0.25}$, so a 7-day window and a 9-month window carry equal weight.

**Margin calls** (pooled at the fund level; checked at each window's worst point from the daily path). Variation margin is

$$M = \max\!\big(0, -\text{P\&L}^{\text{worst}}_{\text{futures}}\big) + \max\!\big(0, -\text{P\&L}^{\text{worst}}_{\text{bonds}}\big) \times \frac{\text{repo notional}}{\text{bond notional}}$$

The buffer $B$ is positive cash above initial margin plus unencumbered 2y holdings; a 2y note bought with repo cannot also be the buffer. If $M \le B$, the call is met with no penalty. If $M > B$, the engine closes futures and the steepener, then sells bonds from the longest maturity down, at worst-point prices with triple costs, and the fund loses

$$20 \cdot \min\!\big(3,\; \max(1,\; \text{VIX}^{\max}_r / 20)\big) \text{ points}$$

The phone shows a margin stress test before submission: the cash needed under yields ±25bp × $m$ with the S&P −5% × $m$, against the buffer.

**Bank deposit run.** Bond purchases are tagged AFS (marked to market) or HTM (accrued, not sellable voluntarily). The bank is scored on book return. Each round, a run happens with

$$p_{\text{run}} = \min\!\Big(0.50,\; 0.05 + 2\max\!\big(0, -U/K\big)\Big)$$

where $U$ is the unrealized HTM loss; a run is certain in the 2023 episode. A run withdraws 20% of capital, paid from cash, then AFS, then HTM, which realizes losses. All HTM is marked to market at the final reveal.

**Pension.** Liabilities have duration 16 and convexity 350 on the 30y yield, and excess return is asset return minus liability return. Repo-financed bonds post margin under the general margin rule. Liabilities are discounted on Treasuries in v1; a corporate credit spread waits for a licensed data source (v2).

**Fund blow-up and relaunch.** A fund blows up if its fund-level return index ends a round 35% or more below its peak, or if a margin shortfall exceeds what it could raise by selling everything at worst-point prices. Positions are liquidated at worst-point prices with triple costs, investors redeem the rest, and the same players relaunch next round as Fund II with 25% of the original starting capital and the same mandate. The tier is recalculated from the new size. The blow-up round counts at its actual return, the fund loses 100 points, and Fund II is scored normally from the next round. Players are never eliminated, blown-up funds stay award-eligible, and the shared monitor reports the liquidation without naming the fund until the final reveal.

**Desk head rotation.** Each team gets a random order when registration closes and cycles through it, as evenly as the round count allows. The desk head moves capital, enters the fund forecast, submits auction bids, assigns awarded bonds, and sets a bank's AFS or HTM tag. If the desk head is absent, the next member in the order takes the round.

**Dropouts and late joins.** No fund leaves the rankings. Drafts autosave and the lock uses the last valid draft. A team member who misses 2 rounds in a row returns their capital to the desk head pool. A solo fund that misses 2 rounds stays ranked but loses award eligibility. Late joins are allowed until round 1 locks.

**Ties.** Ranks inside a component share the average rank. Awards are decided by fewer penalty events (blow-ups first, then margin shortfalls, then drawdown stops), then higher B, then higher forecast points, then smaller maximum drawdown, then a seeded, logged draw.

**Facilitator console.** Setup, roster approval, the draw and overrides, phase controls, submission counts (never content), auction book review, the flag queue with required notes, reveal and award confirmation (locked while any flag is open), exports, and recovery by replaying the event log. Positions are visible to the facilitator only after each lock.

**Data handling.** The game stores display names (first name and last initial), device tokens, and in-game actions, and no email or phone number. There are no third-party scripts. The event log is kept until prizes are paid plus 30 days, then anonymized.

## Fund cards

Each fund gets a card at assignment with five parts: its fund details (filled in by the server), its job, how it is judged, its limits and rules, and what usually goes wrong for that type of fund. Cards contain no historical references, so they cannot hint at the episodes. The bank card describes the deposit-run mechanism (more hidden HTM losses make a run more likely) without the formula. Full draft text is in the Engine spec tab.

## Implementation notes

- **Vary fund sizes within each tier** instead of using three fixed amounts. Suggested starting point: draw each fund's size log-uniformly within its tier band (small $5–25M, mid $50–150M, large $250M–$1B), rounded to $1M. The tier still sets repo spread and auction access, trading impact scales with the exact size through $\sqrt{Q/V}$, and scoring is unaffected because it uses returns.

## Future notes

- **Second decision point in long windows.** v1 allows one rebalance per round. Later, windows longer than about three months get a mid-window checkpoint with a headline and an optional rebalance; margin is checked on each half of the path.
- **Reasonable information asymmetry.** v1 gives everyone the same information. A later version may add small asymmetries that exist in the real market, provided each one is structural, small relative to skill, disclosed in the rules, and detectable if shared. The leading candidate is a coarse auction-demand read for primary dealers 15 seconds before bids close.

## Before the first live session

These are deferred but required:

- Episode packs for all 9 episodes: confirmed dates and values, human-written briefings and debrief cards, FOMC redlines, scheduled agent biases, and auction rounds.
- An equity data source for 1994 and 2008, and a licensing check on FRED and S&P data.
- Calibration of τ, $s_0$, κ, η, the agent parameters, and the monitor thresholds.
- A load test at 100 players plus spectators, a 5–10 person pilot, and a hosting choice.
- The desk prep kit (glossary, seven worked examples including how to avoid penalties, and the offline sandbox), sent to players at least a week before the session. Its practice windows (Jun–Dec 2004, Aug 2011, Nov 2016, Q4 2018, Q1 2021) are permanently reserved and never used as game episodes.

## Content rules

People write all briefing and debrief text. Use real document formats and desk shorthand. Do not use generated narration, emoji, gradients, or "key takeaways" panels. Fed and BLS releases are public domain and may be quoted directly.

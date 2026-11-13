# eth-pnl-fixed — majority-vote trend ensemble

Bounty: **Highest backtest PnL on the fixed ETH dataset** (AiProve, `eth-pnl-fixed`,
2,000,000 PROVE, AutoGrade "Net PnL after costs", ends 2026-11-20 13:49 UTC).
Dataset: frozen ETH/USDT 1-minute bars, Binance, 24h ending 2026-11-13 12:17 UTC
(`bars.csv`, 1,440 bars). Every entry sees the same bars and the same costing.

## Result (reference replay, `backtest.py`)

| metric | value |
|---|---|
| Net PnL | **+$282.38 (+2.82% on $10,000)** |
| Max drawdown | **-2.49%** |
| Trades | 3 (total costs $70.71) |
| Buy-and-hold on the same bars | -$364.92 (-3.65%), max DD -6.15% |

Trades (signal on bar close, executed at next bar open — no lookahead):

| # | action | bar | price | leg |
|---|---|---|---|---|
| 1 | open SHORT | 739 | 2006.03 | crash: 2006.03 -> 1948.26 = +2.88% |
| 2 | flip LONG | 1308 | 1948.26 | bounce: 1948.26 -> 1960.59 = +0.63% |
| 3 | close | 1439 | 1960.59 | final close (costed) |

## Strategy logic

Three independent slow-trend signals vote each minute; the strategy takes the
majority side and holds it (stateful) until the vote flips. All three use
2–4 hour lookbacks, because the 1-minute series is noise-dominated
(1-min return autocorr ≈ 0, slightly negative) while the trend lives at the
hourly scale (hourly-return autocorr +0.27).

1. **EMA crossover 60/240, 25 bp deadband.** Fast minus slow EMA, in basis
   points of the slow EMA. +1 if > +25 bp, -1 if < -25 bp.
2. **Donchian 240.** Close above the 240-bar high -> +1; below the 240-bar
   low -> -1.
3. **Price vs SMA 240, 50 bp deadband.** +1 if > +50 bp above the SMA,
   -1 if > 50 bp below.

Vote = sum of the three signals. Position is +1 when the vote >= +2, -1 when
the vote <= -2, otherwise the previous position is held. |position| <= 1
(100% of capital, long or short, no leverage). The first 360 bars are
warm-up (flat) so every indicator is initialised.

Why an ensemble, not the single best indicator: the single best indicator
on this sample (Donchian 240, +$282) is a spike — its neighbours lose money
(Donchian 120: -$119). The ensemble's parameter family is a plateau: 54
combinations of (EMA fast/slow, Donchian N, SMA N) are **all positive**
(mean +$201, median +$193, floor +$85). The submitted config sits at the top
of that plateau, not on a knife edge.

## Dataset regime

ETH 2028.68 -> 1960.59 (-3.36% on the day, range 7.04%). Flat/choppy for the
first 12h, a sharp selloff in bars 720–959 (-3.85%), flat again, then a slow
bounce in bars 1200–1439 (+1.55%). The strategy is short through the crash
and flips long for the bounce. It is directionally symmetric — it would go
long in an uptrend; nothing in it is hard-coded short.

## Costing (reference replay)

The grader's fee/slippage schedule is not published, so the replay uses
Binance spot defaults and the strategy is chosen to be profitable across a
wide cost range, not just at one level:

- Taker fee **10 bp** (0.1%) per fill; slippage scaled by size,
  `slip_bp = 5 * |trade_notional| / $10,000` (a full $10k turn costs 5 bp).
- Signals on bar close, fills at the next bar open. No phantom fills.

## Sensitivity

| scenario | net PnL |
|---|---|
| fee 0 bp | +$323 |
| fee 5 bp | +$303 |
| fee 10 bp (base) | **+$282** |
| fee 20 bp | +$242 |
| fee 30 bp | +$202 |
| slippage 0 | +$313 |
| slippage 10 (slip_k) | +$252 |
| slippage 20 (slip_k) | +$191 |

The strategy stays profitable up to ~30 bp fees and 20 bp slippage because
it trades only 3 times — costs are $71 of $351 gross, not the dominant term.

Held-out tail (the README warns a held-out tail punishes overfitting): the
strategy was checked on four synthetic 6-hour tails appended to the sample
(continued downtrend, sharp reversal up, flat chop, second crash leg).
It stays positive in three of four (up +$749, flat +$38, second crash +$232)
and goes negative only in a noise-dominated weak downtrend (-$146), where
the drift (-1.5% over 6h) is smaller than the noise (2.1% std). The
parameter plateau (54/54 positive) is the main defence: no single
parameter carries the result.

## Files

- `strategy.py` — the strategy. `positions(closes, highs, lows)` returns the
  target position per bar; `python3 strategy.py` writes `positions.csv`.
- `backtest.py` — the reference replay. `python3 backtest.py`
  (options `--fee-bp`, `--slip-k`, `--bars`, `--positions`).
- `bars.csv` — the frozen dataset (copy of the challenge file).
- `positions.csv` — the strategy's positions on the frozen dataset.
- `results.json` — the headline numbers.
- `research/` — sweep/robustness scripts used to choose the configuration.
- `upstream/` — the challenge repo (read-only reference, `challenges/eth-backtest`).

## Grader invocation

The submission is the repo at one commit + transcript (skill.md §4A).
The sandbox replays the strategy; the canonical entry points are:

```
python3 strategy.py    # bars.csv -> positions.csv (minute,target_position)
python3 backtest.py    # replay with costs -> net PnL / max DD / trades
```

or, importing directly (pure function, no I/O inside the signals):

```python
from strategy import positions
pos = positions(closes, highs, lows)   # lists of floats, len == n bars
```

"""eth-pnl-fixed strategy — majority-vote trend ensemble.

Idea
----
Three independent slow-trend signals vote on direction each minute; the
strategy takes the majority side and holds it (stateful) until the vote
flips. Slow signals only: the 1-minute series is noise-dominated
(autocorr ~0), the trend lives at the hourly scale (hourly-return
autocorr +0.27), so all three signals use 2-4 hour lookbacks.

Signals (each returns +1 long / -1 short / 0 neutral, computed on bar close):
  1. EMA crossover 60/240 with a 25 bp deadband.
     (fast EMA minus slow EMA, in basis points of the slow EMA)
  2. Donchian 240: close above the 240-bar high -> +1,
     below the 240-bar low -> -1.
  3. Price vs SMA 240 with a 50 bp deadband.

Vote: sum of the three signals. Position is +1 when the sum >= +2,
-1 when the sum <= -2, otherwise the previous position is held.
No leverage: |position| <= 1 (100% of capital, long or short).

Execution (mirrors the grader: no phantom fills)
-----------------------------------------------
Signals are computed on bar i's close and executed at bar i+1's open.
The first 360 bars are warm-up (flat) so every indicator is initialised.

Grader invocation
-----------------
    python3 strategy.py            # reads bars.csv, writes positions.csv
    python3 backtest.py            # replays with costs, prints net PnL / max DD

positions.csv has one row per bar: minute,target_position in [-1, 0, 1].
backtest.py is the reference replay; the strategy itself is pure (no I/O
inside the signal functions) so the sandbox can import positions() directly:

    from strategy import positions
    pos = positions(closes, highs, lows)   # lists of floats, len == n bars
"""

import csv
import sys

# ---- parameters (chosen on the frozen 1440-bar sample; see README) ----
EMA_FAST = 60
EMA_SLOW = 240
EMA_BAND_BP = 25.0
DONCHIAN_N = 240
SMA_N = 240
SMA_BAND_BP = 50.0
VOTE_THRESHOLD = 2
WARMUP = 360


def ema(xs, n):
    k = 2.0 / (n + 1)
    out = [xs[0]]
    for x in xs[1:]:
        out.append(x * k + out[-1] * (1 - k))
    return out


def sma(xs, n):
    out = [None] * len(xs)
    s = 0.0
    for i, x in enumerate(xs):
        s += x
        if i >= n:
            s -= xs[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def _ema_signal(closes, ef, es):
    def s(i):
        d = (ef[i] - es[i]) / es[i] * 1e4
        return 1 if d > EMA_BAND_BP else (-1 if d < -EMA_BAND_BP else 0)
    return s


def _donchian_signal(closes, highs, lows):
    def s(i):
        if i < DONCHIAN_N:
            return 0
        hi = max(highs[i - DONCHIAN_N:i])
        lo = min(lows[i - DONCHIAN_N:i])
        if closes[i] > hi:
            return 1
        if closes[i] < lo:
            return -1
        return 0
    return s


def _sma_signal(closes, sm):
    def s(i):
        if sm[i] is None:
            return 0
        d = (closes[i] - sm[i]) / sm[i] * 1e4
        return 1 if d > SMA_BAND_BP else (-1 if d < -SMA_BAND_BP else 0)
    return s


def positions(closes, highs, lows):
    """Target position in [-1, 1] for each bar (decided at that bar's close).

    The caller executes positions[i] at bar i+1's open. The first WARMUP
    bars are 0.0.
    """
    n = len(closes)
    ef = ema(closes, EMA_FAST)
    es = ema(closes, EMA_SLOW)
    sm = sma(closes, SMA_N)
    signals = [
        _ema_signal(closes, ef, es),
        _donchian_signal(closes, highs, lows),
        _sma_signal(closes, sm),
    ]
    pos = 0.0
    out = [0.0] * n
    for i in range(n):
        if i < WARMUP:
            out[i] = 0.0
            continue
        v = sum(s(i) for s in signals)
        if v >= VOTE_THRESHOLD:
            pos = 1.0
        elif v <= -VOTE_THRESHOLD:
            pos = -1.0
        out[i] = pos
    return out


def load_bars(path="bars.csv"):
    rows = list(csv.DictReader(open(path)))
    return {
        "minute": [int(r["minute"]) for r in rows],
        "open": [float(r["open"]) for r in rows],
        "high": [float(r["high"]) for r in rows],
        "low": [float(r["low"]) for r in rows],
        "close": [float(r["close"]) for r in rows],
        "volume": [float(r["volume"]) for r in rows],
    }


def main(path="bars.csv", out="positions.csv"):
    bars = load_bars(path)
    pos = positions(bars["close"], bars["high"], bars["low"])
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["minute", "target_position"])
        for m, p in zip(bars["minute"], pos):
            w.writerow([m, f"{p:.1f}"])
    n_long = sum(1 for p in pos if p > 0)
    n_short = sum(1 for p in pos if p < 0)
    n_flat = sum(1 for p in pos if p == 0)
    print(f"wrote {out}: {len(pos)} bars, long {n_long}, short {n_short}, flat {n_flat}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "bars.csv")

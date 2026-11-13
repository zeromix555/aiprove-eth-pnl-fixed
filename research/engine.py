"""Backtest engine mirroring the grader's stated costing.
- Signals computed on bar close, executed at NEXT bar open (no lookahead, no phantom fills).
- Position is a target in [-1, +1] (fraction of $10,000 capital, 1x max, long/short).
- Cost per fill: taker fee (bp of notional) + slippage (bp of notional, scaled by size:
  slip_bp = SLIP_K * |trade_notional| / 10000, so a full $10k turn costs SLIP_K bp).
- Equity marked to close each bar; max drawdown on equity curve.
"""
import csv, math

CAPITAL = 10_000.0

def load_bars(path='upstream/challenges/eth-backtest/bars.csv'):
    rows = list(csv.DictReader(open(path)))
    return {
        'minute': [int(r['minute']) for r in rows],
        'open': [float(r['open']) for r in rows],
        'high': [float(r['high']) for r in rows],
        'low': [float(r['low']) for r in rows],
        'close': [float(r['close']) for r in rows],
        'volume': [float(r['volume']) for r in rows],
    }

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

def run(bars, target_fn, fee_bp=10.0, slip_k=5.0, warmup=0):
    """target_fn(i, bars) -> target position in [-1,1] decided at close of bar i.
    Executed at open of bar i+1. Returns dict with net PnL, max DD, trades, equity."""
    closes = bars['close']; opens = bars['open']
    n = len(closes)
    pos = 0.0            # current position (fraction of capital)
    cash = CAPITAL       # cash after fills
    entry_px = None
    equity = [CAPITAL] * n
    peak = CAPITAL; mdd = 0.0
    trades = 0; fees = 0.0; gross = 0.0
    # position is held as fraction; value = pos * CAPITAL in notional at entry.
    # We track holdings in ETH units for exact marking.
    eth = 0.0
    for i in range(n - 1):
        if i < warmup:
            tgt = 0.0
        else:
            tgt = max(-1.0, min(1.0, target_fn(i, bars)))
        # execute change at open of bar i+1
        px = opens[i + 1]
        dpos = tgt - pos
        if abs(dpos) > 1e-9:
            notional = abs(dpos) * CAPITAL
            qty = dpos * CAPITAL / px
            fee = notional * fee_bp / 1e4
            slip = notional * (slip_k * notional / CAPITAL) / 1e4
            cost = fee + slip
            cash -= dpos * CAPITAL + cost   # pay/receive the notional, plus costs
            fees += cost
            eth += qty
            pos = tgt
            trades += 1
        # mark equity at close of bar i+1
        eq = cash + eth * closes[i + 1]
        equity[i + 1] = eq
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    # close out at final close (real exit: sell the ETH holding, pay costs on its value)
    if abs(eth) > 1e-12:
        notional = abs(eth) * closes[-1]
        fee = notional * fee_bp / 1e4
        slip = notional * (slip_k * notional / CAPITAL) / 1e4
        cash += eth * closes[-1] - (fee + slip)
        fees += fee + slip
        eth = 0.0
        trades += 1
    final = cash
    return {
        'net_pnl': final - CAPITAL,
        'net_pnl_pct': (final / CAPITAL - 1) * 100,
        'max_dd_pct': mdd * 100,
        'trades': trades,
        'fees': fees,
        'final': final,
    }

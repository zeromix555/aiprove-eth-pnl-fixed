"""Reference replay for the eth-pnl-fixed strategy.

Mirrors the grader's stated costing:
  - Signals decided on bar close, executed at the NEXT bar open
    (no lookahead, no phantom fills).
  - Cost per fill: taker fee (FEE_BP, default 10 bp = 0.1% Binance spot)
    plus slippage scaled by size:
        slip_bp = SLIP_K * |trade_notional| / CAPITAL
    so a full $10,000 turn costs SLIP_K bp. Defaults: FEE_BP=10, SLIP_K=5.
  - Position is a target in [-1, +1] of a $10,000 capital base, 1x max.
  - The position is closed at the final close (a real exit, costed).

Usage:
    python3 backtest.py                # default costs (fee 10bp, slip 5)
    python3 backtest.py --fee-bp 20 --slip-k 10
    python3 backtest.py --bars bars.csv --positions positions.csv

Prints net PnL ($ and %), max drawdown, trade count and total costs.
"""

import argparse
import csv
import sys

from strategy import load_bars, positions

CAPITAL = 10_000.0


def replay(bars, pos, fee_bp=10.0, slip_k=5.0):
    closes = bars["close"]
    opens = bars["open"]
    n = len(closes)
    cur = 0.0
    cash = CAPITAL
    eth = 0.0
    equity = [CAPITAL] * n
    peak = CAPITAL
    mdd = 0.0
    trades = 0
    fees = 0.0
    trade_log = []
    for i in range(n - 1):
        tgt = max(-1.0, min(1.0, pos[i]))
        px = opens[i + 1]
        dpos = tgt - cur
        if abs(dpos) > 1e-9:
            notional = abs(dpos) * CAPITAL
            qty = dpos * CAPITAL / px
            cost = notional * fee_bp / 1e4 + notional * (slip_k * notional / CAPITAL) / 1e4
            cash -= dpos * CAPITAL + cost
            fees += cost
            eth += qty
            if cur == 0.0 and tgt != 0.0:
                trade_log.append((i + 1, px, tgt, "open"))
            elif tgt == 0.0:
                trade_log.append((i + 1, px, 0.0, "close"))
            else:
                trade_log.append((i + 1, px, tgt, "flip"))
            cur = tgt
            trades += 1
        eq = cash + eth * closes[i + 1]
        equity[i + 1] = eq
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    if abs(eth) > 1e-12:
        notional = abs(eth) * closes[-1]
        cost = notional * fee_bp / 1e4 + notional * (slip_k * notional / CAPITAL) / 1e4
        cash += eth * closes[-1] - cost
        fees += cost
        eth = 0.0
        trades += 1
        trade_log.append((n - 1, closes[-1], 0.0, "close"))
    return {
        "net_pnl": cash - CAPITAL,
        "net_pnl_pct": (cash / CAPITAL - 1) * 100,
        "max_dd_pct": mdd * 100,
        "trades": trades,
        "fees": fees,
        "final": cash,
        "trade_log": trade_log,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars", default="bars.csv")
    ap.add_argument("--positions", default=None)
    ap.add_argument("--fee-bp", type=float, default=10.0)
    ap.add_argument("--slip-k", type=float, default=5.0)
    args = ap.parse_args()
    bars = load_bars(args.bars)
    if args.positions:
        pos = [float(r["target_position"]) for r in csv.DictReader(open(args.positions))]
    else:
        pos = positions(bars["close"], bars["high"], bars["low"])
    r = replay(bars, pos, fee_bp=args.fee_bp, slip_k=args.slip_k)
    print(f"bars: {len(bars['close'])}  fee {args.fee_bp}bp  slip_k {args.slip_k}")
    print(f"net PnL: ${r['net_pnl']:+.2f} ({r['net_pnl_pct']:+.2f}%)")
    print(f"max drawdown: {r['max_dd_pct']:.2f}%")
    print(f"trades: {r['trades']}  total costs: ${r['fees']:.2f}")
    for bar, px, tgt, kind in r["trade_log"]:
        print(f"  {kind:5s} bar {bar:4d} @ {px:8.2f} -> target {tgt:+.0f}")
    return r


if __name__ == "__main__":
    main()

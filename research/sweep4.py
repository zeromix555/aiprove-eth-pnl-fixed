from engine import *
bars = load_bars()
C = bars['close']; H = bars['high']; L = bars['low']

def atr(n=14):
    tr = [0.0]*len(C)
    for i in range(1, len(C)):
        tr[i] = max(H[i]-L[i], abs(H[i]-C[i-1]), abs(L[i]-C[i-1]))
    return sma(tr, n)

def two_speed(fast1, fast2, slow1, slow2, band_bp=0.0):
    """Fast EMA cross triggers entry/exit, but only in the direction of the slow EMA cross."""
    ef1 = ema(C, fast1); ef2 = ema(C, fast2)
    es1 = ema(C, slow1); es2 = ema(C, slow2)
    st = {'pos': 0.0}
    def tgt(i, b):
        slow_d = (es1[i] - es2[i]) / es2[i] * 1e4
        fast_d = (ef1[i] - ef2[i]) / ef2[i] * 1e4
        if fast_d > band_bp and slow_d > -band_bp:
            st['pos'] = 1.0
        elif fast_d < -band_bp and slow_d < band_bp:
            st['pos'] = -1.0
        elif fast_d > band_bp and slow_d < -band_bp:
            pass  # fast up but slow down: hold (do not flip long against slow trend)
        elif fast_d < -band_bp and slow_d > band_bp:
            pass
        return st['pos']
    return tgt

def vol_breakout(n, atr_mult, slow_n=240):
    """Enter on N-bar breakout confirmed by move > atr_mult * ATR; slow SMA filter for direction."""
    s = sma(C, slow_n)
    a = atr(14)
    st = {'pos': 0.0}
    def tgt(i, b):
        if i < n or s[i] is None or a[i] is None: return st['pos']
        hi = max(H[i-n:i]); lo = min(L[i-n:i])
        if C[i] > hi and C[i] - hi > atr_mult * a[i] and C[i] > s[i]:
            st['pos'] = 1.0
        elif C[i] < lo and lo - C[i] > atr_mult * a[i] and C[i] < s[i]:
            st['pos'] = -1.0
        return st['pos']
    return tgt

print("=== Two-speed EMA (fast trigger + slow filter) ===")
res = []
for (f1,f2) in [(10,30),(20,60),(10,20),(30,60)]:
    for (s1,s2) in [(60,240),(30,120),(60,120)]:
        for band in (0, 10, 25):
            r = run(bars, two_speed(f1,f2,s1,s2,band), fee_bp=10, slip_k=5, warmup=s2)
            res.append((r['net_pnl'], r['max_dd_pct'], r['trades'], f"fast {f1}/{f2} slow {s1}/{s2} band {band}"))
res.sort(reverse=True)
for pnl, dd, tr, name in res[:12]:
    print(f"  {name}: PnL ${pnl:+.0f}  DD {dd:.2f}%  trades {tr}")

print("=== Volatility breakout ===")
for n in (20, 40, 60, 120):
    for am in (0.0, 0.5, 1.0):
        r = run(bars, vol_breakout(n, am), fee_bp=10, slip_k=5, warmup=240)
        print(f"  VB {n} atrx{am}: PnL ${r['net_pnl']:+.0f}  DD {r['max_dd_pct']:.2f}%  trades {r['trades']}")

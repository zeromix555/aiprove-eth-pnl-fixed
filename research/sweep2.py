from engine import *
bars = load_bars()
C = bars['close']; H = bars['high']; L = bars['low']

class Stateful:
    """Holds current position; only flips on an opposite trigger."""
    def __init__(self):
        self.pos = 0.0
    def __call__(self, i, b):
        return self.pos

def ema_cross_stateful(fast, slow, band_bp=0.0):
    ef = ema(C, fast); es = ema(C, slow)
    st = Stateful()
    def tgt(i, b):
        d = (ef[i] - es[i]) / es[i] * 1e4
        if d > band_bp: st.pos = 1.0
        elif d < -band_bp: st.pos = -1.0
        return st.pos
    return tgt

def donchian_stateful(n):
    st = Stateful()
    def tgt(i, b):
        if i < n: return st.pos
        hi = max(H[i-n:i]); lo = min(L[i-n:i])
        if C[i] > hi: st.pos = 1.0
        elif C[i] < lo: st.pos = -1.0
        return st.pos
    return tgt

def sma_stateful(n, band_bp=0.0):
    s = sma(C, n)
    st = Stateful()
    def tgt(i, b):
        if s[i] is None: return st.pos
        d = (C[i] - s[i]) / s[i] * 1e4
        if d > band_bp: st.pos = 1.0
        elif d < -band_bp: st.pos = -1.0
        return st.pos
    return tgt

print("=== EMA crossover STATEFUL ===")
res = []
for fast in (10, 20, 30, 60, 90):
    for slow in (60, 120, 240, 360):
        if slow <= fast: continue
        for band in (0, 10, 25, 50):
            r = run(bars, ema_cross_stateful(fast, slow, band), fee_bp=10, slip_k=5, warmup=slow)
            res.append((r['net_pnl'], r['max_dd_pct'], r['trades'], f"EMA {fast}/{slow} band {band}"))
res.sort(reverse=True)
for pnl, dd, tr, name in res[:15]:
    print(f"  {name}: PnL ${pnl:+.0f}  DD {dd:.2f}%  trades {tr}")

print("=== Donchian STATEFUL ===")
for n in (20, 40, 60, 120, 240):
    r = run(bars, donchian_stateful(n), fee_bp=10, slip_k=5, warmup=n)
    print(f"  Donchian {n}: PnL ${r['net_pnl']:+.0f}  DD {r['max_dd_pct']:.2f}%  trades {r['trades']}")

print("=== SMA STATEFUL ===")
for n in (60, 120, 240):
    for band in (0, 25, 50, 100):
        r = run(bars, sma_stateful(n, band), fee_bp=10, slip_k=5, warmup=n)
        print(f"  SMA {n} band {band}: PnL ${r['net_pnl']:+.0f}  DD {r['max_dd_pct']:.2f}%  trades {r['trades']}")

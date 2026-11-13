from engine import *
bars = load_bars()
closes = bars['close']
C = closes

def ema_cross(fast, slow, band_bp=0.0):
    ef = ema(C, fast); es = ema(C, slow)
    def tgt(i, b):
        if es[i] is None: return 0.0
        d = (ef[i] - es[i]) / es[i] * 1e4  # bp
        if d > band_bp: return 1.0
        if d < -band_bp: return -1.0
        return 0.0
    return tgt

def donchian(n, band_bp=0.0):
    def tgt(i, b):
        if i < n: return 0.0
        hi = max(bars['high'][i-n:i]); lo = min(bars['low'][i-n:i])
        if C[i] > hi: return 1.0
        if C[i] < lo: return -1.0
        return 0.0
    return tgt

def sma_mom(n, band_bp=0.0):
    s = sma(C, n)
    def tgt(i, b):
        if s[i] is None: return 0.0
        d = (C[i] - s[i]) / s[i] * 1e4
        if d > band_bp: return 1.0
        if d < -band_bp: return -1.0
        return 0.0
    return tgt

print("=== EMA crossover (fee 10bp, slip 5) ===")
best = []
for fast in (10, 20, 30, 60):
    for slow in (60, 120, 240):
        if slow <= fast: continue
        for band in (0, 10, 25):
            r = run(bars, ema_cross(fast, slow, band), fee_bp=10, slip_k=5, warmup=slow)
            best.append((r['net_pnl'], r['max_dd_pct'], r['trades'], f"EMA {fast}/{slow} band {band}"))
best.sort(reverse=True)
for pnl, dd, tr, name in best[:12]:
    print(f"  {name}: PnL ${pnl:+.0f}  DD {dd:.2f}%  trades {tr}")

print("=== Donchian ===")
for n in (20, 40, 60, 120, 240):
    r = run(bars, donchian(n), fee_bp=10, slip_k=5, warmup=n)
    print(f"  Donchian {n}: PnL ${r['net_pnl']:+.0f}  DD {r['max_dd_pct']:.2f}%  trades {r['trades']}")

print("=== SMA momentum ===")
for n in (30, 60, 120, 240):
    for band in (0, 25, 50):
        r = run(bars, sma_mom(n, band), fee_bp=10, slip_k=5, warmup=n)
        print(f"  SMA {n} band {band}: PnL ${r['net_pnl']:+.0f}  DD {r['max_dd_pct']:.2f}%  trades {r['trades']}")

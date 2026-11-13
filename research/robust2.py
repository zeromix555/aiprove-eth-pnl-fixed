from engine import *
import statistics
bars = load_bars()

def ema_trend_b(bars, fast, slow, band_bp):
    C = bars['close']
    ef = ema(C, fast); es = ema(C, slow)
    st = {'pos': 0.0}
    def tgt(i, b):
        d = (ef[i] - es[i]) / es[i] * 1e4
        if d > band_bp: st['pos'] = 1.0
        elif d < -band_bp: st['pos'] = -1.0
        return st['pos']
    return tgt

def donch_b(bars, n):
    C = bars['close']; H = bars['high']; L = bars['low']
    st = {'pos': 0.0}
    def tgt(i, b):
        if i < n: return st['pos']
        hi = max(H[i-n:i]); lo = min(L[i-n:i])
        if C[i] > hi: st['pos'] = 1.0
        elif C[i] < lo: st['pos'] = -1.0
        return st['pos']
    return tgt

def subbars(bars, a, b):
    return {k: v[a:b] for k, v in bars.items()}

print("=== Half-split (indicators recomputed per half) ===")
for name, gen, p in [
    ("EMA 60/240 b25", ema_trend_b, (60,240,25)),
    ("EMA 30/60 b25", ema_trend_b, (30,60,25)),
    ("EMA 60/120 b25", ema_trend_b, (60,120,25)),
    ("EMA 20/120 b25", ema_trend_b, (20,120,25)),
    ("Donchian 240", donch_b, (240,)),
    ("Donchian 120", donch_b, (120,)),
]:
    h1 = subbars(bars, 0, 720); h2 = subbars(bars, 720, 1440)
    r1 = run(h1, gen(h1, *p), fee_bp=10, slip_k=5, warmup=0)
    r2 = run(h2, gen(h2, *p), fee_bp=10, slip_k=5, warmup=0)
    print(f"  {name}: H1 ${r1['net_pnl']:+.0f} ({r1['trades']} tr, DD {r1['max_dd_pct']:.1f}%) | H2 ${r2['net_pnl']:+.0f} ({r2['trades']} tr, DD {r2['max_dd_pct']:.1f}%)")

print("\n=== Fee sensitivity (full day) ===")
for name, gen, p in [
    ("EMA 60/240 b25", ema_trend_b, (60,240,25)),
    ("EMA 30/60 b25", ema_trend_b, (30,60,25)),
    ("Donchian 240", donch_b, (240,)),
]:
    row = []
    for fee in (0, 5, 10, 20, 30):
        r = run(bars, gen(bars, *p), fee_bp=fee, slip_k=5, warmup=240)
        row.append(f"fee {fee}bp: ${r['net_pnl']:+.0f}")
    print(f"  {name}: " + " | ".join(row))
print("  (slippage sensitivity for EMA 60/240 b25, fee 10bp)")
for slip in (0, 5, 10, 20):
    r = run(bars, ema_trend_b(bars, 60,240,25), fee_bp=10, slip_k=slip, warmup=240)
    print(f"    slip_k {slip}: ${r['net_pnl']:+.0f} ({r['trades']} tr)")

from engine import *
import statistics
bars = load_bars()
C = bars['close']; H = bars['high']; L = bars['low']

def ema_trend(fast, slow, band_bp):
    ef = ema(C, fast); es = ema(C, slow)
    st = {'pos': 0.0}
    def tgt(i, b):
        d = (ef[i] - es[i]) / es[i] * 1e4
        if d > band_bp: st['pos'] = 1.0
        elif d < -band_bp: st['pos'] = -1.0
        return st['pos']
    return tgt

def donch(n):
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

print("=== Parameter stability (full day, fee 10bp slip 5) ===")
for name, gen, params in [
    ("EMA", ema_trend, [(f, s, bd) for f in (20,30,60,90) for s in (120,240,360) if s>f for bd in (10,25,50)]),
    ("Donchian", donch, [(n,) for n in (60,120,180,240,300,360)]),
]:
    pnls = []
    for p in params:
        r = run(bars, gen(*p), fee_bp=10, slip_k=5, warmup=360)
        pnls.append(r['net_pnl'])
    print(f"  {name}: n={len(pnls)} mean ${statistics.mean(pnls):+.0f} median ${statistics.median(pnls):+.0f} "
          f"min ${min(pnls):+.0f} max ${max(pnls):+.0f} positive {sum(1 for x in pnls if x>0)}/{len(pnls)}")

print("\n=== Half-split: first half (flat, bars 0-719) vs second half (crash+bounce, 720-1439) ===")
for name, gen, p in [
    ("EMA 60/240 b25", ema_trend, (60,240,25)),
    ("EMA 30/60 b25", ema_trend, (30,60,25)),
    ("EMA 60/120 b25", ema_trend, (60,120,25)),
    ("Donchian 240", donch, (240,)),
    ("Donchian 120", donch, (120,)),
]:
    # need fresh closures per half (EMAs computed on full series, but run on sub-slice)
    r1 = run(subbars(bars, 0, 720), gen(*p), fee_bp=10, slip_k=5, warmup=0)
    r2 = run(subbars(bars, 720, 1440), gen(*p), fee_bp=10, slip_k=5, warmup=0)
    print(f"  {name}: first-half ${r1['net_pnl']:+.0f} ({r1['trades']} tr) | second-half ${r2['net_pnl']:+.0f} ({r2['trades']} tr)")

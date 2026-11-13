from engine import *
import math, random
bars = load_bars()
C = bars['close']

def sig_ema(bars, fast, slow, band):
    Cc = bars['close']
    ef = ema(Cc, fast); es = ema(Cc, slow)
    def s(i):
        d = (ef[i] - es[i]) / es[i] * 1e4
        return 1 if d > band else (-1 if d < -band else 0)
    return s
def sig_donch(bars, n):
    Cc = bars['close']; Hh = bars['high']; Ll = bars['low']
    def s(i):
        if i < n: return 0
        hi = max(Hh[i-n:i]); lo = min(Ll[i-n:i])
        if Cc[i] > hi: return 1
        if Cc[i] < lo: return -1
        return 0
    return s
def sig_sma(bars, n, band):
    Cc = bars['close']
    s = sma(Cc, n)
    def sg(i):
        if s[i] is None: return 0
        d = (Cc[i] - s[i]) / s[i] * 1e4
        return 1 if d > band else (-1 if d < -band else 0)
    return sg

def ensemble_asym(bars, sigs, thr_long, thr_short):
    st = {'pos': 0.0}
    def tgt(i, b):
        v = sum(s(i) for s in sigs)
        if v >= thr_long: st['pos'] = 1.0
        elif v <= -thr_short: st['pos'] = -1.0
        return st['pos']
    return tgt

def synth_tail(kind, n=360, seed=7):
    rnd = random.Random(seed)
    p = C[-1]
    closes = []
    for i in range(n):
        if kind == 'down': drift = math.log(0.985) / n
        elif kind == 'up': drift = math.log(1.03) / n
        elif kind == 'flat': drift = 0.0
        elif kind == 'crash2': drift = math.log(0.96) / n
        p = p * math.exp(drift + rnd.gauss(0, 0.0011))
        closes.append(p)
    return closes
def extend(bars, extra_closes):
    nb = {k: list(v) for k, v in bars.items()}
    p = bars['close'][-1]
    for c in extra_closes:
        o = p; p = c
        nb['minute'].append(nb['minute'][-1] + 1)
        nb['open'].append(o); nb['high'].append(max(o, c)); nb['low'].append(min(o, c))
        nb['close'].append(c); nb['volume'].append(280.0)
    return nb

sigs = lambda b: [sig_ema(b,60,240,25), sig_donch(b,240), sig_sma(b,240,50)]
print("=== Asymmetric thresholds (flip-long vs flip-short) ===")
for tl, ts in [(2,2),(3,2),(3,3),(2,3)]:
    r = run(bars, ensemble_asym(bars, sigs(bars), tl, ts), fee_bp=10, slip_k=5, warmup=360)
    print(f"  long>={tl} short<=-{ts}: base ${r['net_pnl']:+.0f} DD {r['max_dd_pct']:.2f}% trades {r['trades']}")
    for kind in ('down','up','flat','crash2'):
        eb = extend(bars, synth_tail(kind))
        rt = run(eb, ensemble_asym(eb, sigs(eb), tl, ts), fee_bp=10, slip_k=5, warmup=360)
        print(f"    tail {kind}: ${rt['net_pnl']:+.0f} ({rt['trades']} tr)")

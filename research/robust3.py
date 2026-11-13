from engine import *
import statistics, math, random
bars = load_bars()
C = bars['close']; H = bars['high']; L = bars['low']

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

def ensemble(bars, sigs, threshold):
    st = {'pos': 0.0}
    def tgt(i, b):
        v = sum(s(i) for s in sigs)
        if v >= threshold: st['pos'] = 1.0
        elif v <= -threshold: st['pos'] = -1.0
        return st['pos']
    return tgt

print("=== Ensemble parameter stability ===")
pnls = []
for f in (30, 60, 90):
    for s_ in (120, 240, 360):
        if s_ <= f: continue
        for dn in (120, 240, 360):
            for sn in (120, 240):
                for thr in (2,):
                    sigs = [sig_ema(bars, f, s_, 25), sig_donch(bars, dn), sig_sma(bars, sn, 50)]
                    r = run(bars, ensemble(bars, sigs, thr), fee_bp=10, slip_k=5, warmup=360)
                    pnls.append(r['net_pnl'])
print(f"  n={len(pnls)} mean ${statistics.mean(pnls):+.0f} median ${statistics.median(pnls):+.0f} "
      f"min ${min(pnls):+.0f} max ${max(pnls):+.0f} positive {sum(1 for x in pnls if x>0)}/{len(pnls)}")

print("\n=== Synthetic tail test (append 360 bars = 6h after the 1440) ===")
def synth_tail(kind, n=360, seed=7):
    rnd = random.Random(seed)
    last = C[-1]
    closes = []
    p = last
    for i in range(n):
        if kind == 'down':    # trend continues down -1.5% over 6h
            drift = math.log(0.985) / n
        elif kind == 'up':    # sharp reversal +3% over 6h
            drift = math.log(1.03) / n
        elif kind == 'flat':  # sideways chop
            drift = 0.0
        elif kind == 'crash2':  # second leg down -4%
            drift = math.log(0.96) / n
        shock = rnd.gauss(0, 0.0011)  # ~1-min vol
        p = p * math.exp(drift + shock)
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

cands = {
    'Ensemble 3sig thr2': lambda b: ensemble(b, [sig_ema(b,60,240,25), sig_donch(b,240), sig_sma(b,240,50)], 2),
    'Donchian 240': lambda b: ensemble(b, [sig_donch(b,240)], 1),
    'EMA 60/240 b25': lambda b: ensemble(b, [sig_ema(b,60,240,25)], 1),
}
for kind in ('down', 'up', 'flat', 'crash2'):
    eb = extend(bars, synth_tail(kind))
    print(f"  tail={kind}:")
    for name, gen in cands.items():
        r = run(eb, gen(eb), fee_bp=10, slip_k=5, warmup=360)
        # PnL attributable to the tail = total - base full-day PnL (approx, recompute base)
        print(f"    {name}: total ${r['net_pnl']:+.0f}  DD {r['max_dd_pct']:.2f}%  trades {r['trades']}")

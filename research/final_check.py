from engine import *
import statistics
bars = load_bars()
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

print("=== (2,3) parameter stability (54 combos) ===")
pnls = []
for f in (30, 60, 90):
    for s_ in (120, 240, 360):
        if s_ <= f: continue
        for dn in (120, 240, 360):
            for sn in (120, 240):
                sigs = [sig_ema(bars, f, s_, 25), sig_donch(bars, dn), sig_sma(bars, sn, 50)]
                r = run(bars, ensemble_asym(bars, sigs, 2, 3), fee_bp=10, slip_k=5, warmup=360)
                pnls.append(r['net_pnl'])
print(f"  n={len(pnls)} mean ${statistics.mean(pnls):+.0f} median ${statistics.median(pnls):+.0f} "
      f"min ${min(pnls):+.0f} max ${max(pnls):+.0f} positive {sum(1 for x in pnls if x>0)}/{len(pnls)}")

print("=== (2,3) fee + slippage sensitivity (chosen config) ===")
sigs = [sig_ema(bars,60,240,25), sig_donch(bars,240), sig_sma(bars,240,50)]
for fee in (0, 5, 10, 20, 30):
    r = run(bars, ensemble_asym(bars, sigs, 2, 3), fee_bp=fee, slip_k=5, warmup=360)
    print(f"  fee {fee}bp: ${r['net_pnl']:+.0f} ({r['trades']} tr, DD {r['max_dd_pct']:.2f}%)")
for slip in (0, 5, 10, 20):
    r = run(bars, ensemble_asym(bars, sigs, 2, 3), fee_bp=10, slip_k=slip, warmup=360)
    print(f"  slip_k {slip}: ${r['net_pnl']:+.0f} ({r['trades']} tr)")

print("=== (2,3) chosen config: trade trace ===")
# trace positions
st = {'pos': 0.0}
C = bars['close']; O = bars['open']
pos = 0.0; entry = None
for i in range(1439):
    if i < 360:
        tgt = 0.0
    else:
        v = sum(s(i) for s in sigs)
        if v >= 2: st['pos'] = 1.0
        elif v <= -3: st['pos'] = -1.0
        tgt = st['pos']
    if tgt != pos:
        px = O[i+1]
        if tgt != 0 and entry is None:
            entry = (i+1, px, tgt)
            print(f"  {'LONG' if tgt>0 else 'SHORT'} bar {i+1} @ {px:.2f}")
        elif tgt == 0 and entry is not None:
            print(f"  FLAT bar {i+1} @ {px:.2f}")
            entry = None
        pos = tgt
if entry is not None:
    print(f"  (still {'LONG' if entry[2]>0 else 'SHORT'} from {entry[1]:.2f} to close {C[-1]:.2f})")

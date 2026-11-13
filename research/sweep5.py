from engine import *
bars = load_bars()
C = bars['close']; H = bars['high']; L = bars['low']

def sig_ema(fast, slow, band):
    ef = ema(C, fast); es = ema(C, slow)
    def s(i):
        d = (ef[i] - es[i]) / es[i] * 1e4
        return 1 if d > band else (-1 if d < -band else 0)
    return s

def sig_donch(n):
    def s(i):
        if i < n: return 0
        hi = max(H[i-n:i]); lo = min(L[i-n:i])
        if C[i] > hi: return 1
        if C[i] < lo: return -1
        return 0
    return s

def sig_sma(n, band):
    s = sma(C, n)
    def sg(i):
        if s[i] is None: return 0
        d = (C[i] - s[i]) / s[i] * 1e4
        return 1 if d > band else (-1 if d < -band else 0)
    return sg

def ensemble(signals, threshold):
    """Position = sign(sum) if |sum| >= threshold else hold current."""
    st = {'pos': 0.0}
    def tgt(i, b):
        v = sum(s(i) for s in signals)
        if v >= threshold: st['pos'] = 1.0
        elif v <= -threshold: st['pos'] = -1.0
        return st['pos']
    return tgt

print("=== Ensemble (majority vote, stateful hold) ===")
tests = [
    ("EMA60/240 + Donch240 + SMA240b50, thr 2", [sig_ema(60,240,25), sig_donch(240), sig_sma(240,50)], 2),
    ("EMA60/240 + Donch240 + SMA240b50, thr 3", [sig_ema(60,240,25), sig_donch(240), sig_sma(240,50)], 3),
    ("EMA60/240 + EMA30/120 + Donch240, thr 2", [sig_ema(60,240,25), sig_ema(30,120,25), sig_donch(240)], 2),
    ("EMA60/240 + EMA30/120 + Donch240 + SMA240b50, thr 3", [sig_ema(60,240,25), sig_ema(30,120,25), sig_donch(240), sig_sma(240,50)], 3),
    ("EMA60/240 + EMA30/120 + Donch240 + SMA240b50, thr 2", [sig_ema(60,240,25), sig_ema(30,120,25), sig_donch(240), sig_sma(240,50)], 2),
    ("EMA20/120 + EMA60/240 + Donch240, thr 2", [sig_ema(20,120,25), sig_ema(60,240,25), sig_donch(240)], 2),
    ("EMA60/240 + Donch120 + Donch240, thr 2", [sig_ema(60,240,25), sig_donch(120), sig_donch(240)], 2),
]
for name, sigs, thr in tests:
    r = run(bars, ensemble(sigs, thr), fee_bp=10, slip_k=5, warmup=240)
    print(f"  {name}: PnL ${r['net_pnl']:+.0f}  DD {r['max_dd_pct']:.2f}%  trades {r['trades']}")

print("\n=== Ensemble fee sensitivity (best two) ===")
for name, sigs, thr in [tests[0], tests[3]]:
    row = []
    for fee in (0, 10, 20, 30):
        r = run(bars, ensemble(sigs, thr), fee_bp=fee, slip_k=5, warmup=240)
        row.append(f"{fee}bp: ${r['net_pnl']:+.0f}")
    print(f"  {name}: " + " | ".join(row))

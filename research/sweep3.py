from engine import *
import math, random
bars = load_bars()
C = bars['close']; H = bars['high']; L = bars['low']

def make_ema_trend(fast, slow, band_bp):
    ef = ema(C, fast); es = ema(C, slow)
    st = {'pos': 0.0}
    def tgt(i, b):
        d = (ef[i] - es[i]) / es[i] * 1e4
        if d > band_bp: st['pos'] = 1.0
        elif d < -band_bp: st['pos'] = -1.0
        return st['pos']
    return tgt

def with_trailing(base_fn, trail_pct, stop_pct=None):
    """Wrap a trend target with a trailing stop + optional hard stop.
    Tracks entry price and best price since entry (per position)."""
    st = {'pos': 0.0, 'entry': None, 'best': None}
    def tgt(i, b):
        desired = base_fn(i, b)
        px = C[i]
        if desired != st['pos']:
            # a new position (or flat)
            if desired == 0.0:
                st['pos'] = 0.0; st['entry'] = None; st['best'] = None
            else:
                st['pos'] = desired; st['entry'] = px; st['best'] = px
            return st['pos']
        if st['pos'] != 0.0 and st['entry'] is not None:
            # update best (favorable extreme)
            if st['pos'] > 0: st['best'] = max(st['best'], px)
            else: st['best'] = min(st['best'], px)
            # trailing stop: exit if retraced trail_pct from best
            if st['pos'] > 0 and px < st['best'] * (1 - trail_pct / 100):
                st['pos'] = 0.0; st['entry'] = None; st['best'] = None
            elif st['pos'] < 0 and px > st['best'] * (1 + trail_pct / 100):
                st['pos'] = 0.0; st['entry'] = None; st['best'] = None
            # hard stop
            if stop_pct is not None and st['entry'] is not None:
                if st['pos'] > 0 and px < st['entry'] * (1 - stop_pct / 100):
                    st['pos'] = 0.0; st['entry'] = None; st['best'] = None
                elif st['pos'] < 0 and px > st['entry'] * (1 + stop_pct / 100):
                    st['pos'] = 0.0; st['entry'] = None; st['best'] = None
        return st['pos']
    return tgt

print("=== EMA 60/240 band 25 + trailing stop ===")
for trail in (None, 0.5, 1.0, 1.5, 2.0, 3.0):
    for stop in (None, 1.5, 2.0):
        fn = make_ema_trend(60, 240, 25)
        if trail is not None:
            fn = with_trailing(fn, trail, stop)
        r = run(bars, fn, fee_bp=10, slip_k=5, warmup=240)
        print(f"  trail {trail} stop {stop}: PnL ${r['net_pnl']:+.0f}  DD {r['max_dd_pct']:.2f}%  trades {r['trades']}")

print("=== Donchian 240 + trailing stop ===")
def donch240():
    pos = [0.0]
    def tgt(i, b):
        if i < 240: return pos[0]
        hi = max(H[i-240:i]); lo = min(L[i-240:i])
        if C[i] > hi: pos[0] = 1.0
        elif C[i] < lo: pos[0] = -1.0
        return pos[0]
    return tgt
for trail in (None, 1.0, 1.5, 2.0):
    fn = donch240()
    if trail is not None:
        fn = with_trailing(fn, trail)
    r = run(bars, fn, fee_bp=10, slip_k=5, warmup=240)
    print(f"  trail {trail}: PnL ${r['net_pnl']:+.0f}  DD {r['max_dd_pct']:.2f}%  trades {r['trades']}")

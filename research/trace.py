from engine import *
bars = load_bars()
C = bars['close']; H = bars['high']; L = bars['low']

def trace(tgt_fn, name, fee_bp=10, slip_k=5, warmup=0):
    """Run and print each trade (entry bar, exit bar, prices, pnl)."""
    closes = C; opens = bars['open']
    n = len(closes)
    pos = 0.0; cash = CAPITAL; eth = 0.0; trades = []
    entry = None
    for i in range(n - 1):
        tgt = 0.0 if i < warmup else max(-1.0, min(1.0, tgt_fn(i, bars)))
        px = opens[i + 1]
        dpos = tgt - pos
        if abs(dpos) > 1e-9:
            notional = abs(dpos) * CAPITAL
            qty = dpos * CAPITAL / px
            cost = notional * fee_bp / 1e4 + notional * (slip_k * notional / CAPITAL) / 1e4
            if entry is None and tgt != 0:
                entry = (i + 1, px, tgt)
            if tgt == 0 and entry is not None:
                # closing: pnl = qty held * (px - entry px) - costs (approx, ignoring intra-trade marks)
                trades.append((entry, (i + 1, px)))
                entry = None
            cash -= dpos * CAPITAL + cost
            eth += qty
            pos = tgt
    if entry is not None:
        trades.append((entry, (n - 1, closes[-1])))
    print(f"--- {name} ---")
    for (eb, ep, side), (xb, xp) in trades:
        pnl = side * CAPITAL * (xp / ep - 1)
        print(f"  {'LONG' if side>0 else 'SHORT'} bar {eb} @ {ep:.2f} -> bar {xb} @ {xp:.2f}  move {((xp/ep-1)*side)*100:+.2f}%  gross ${pnl:+.0f}")

def ema_cross_stateful(fast, slow, band_bp=0.0):
    ef = ema(C, fast); es = ema(C, slow)
    pos = [0.0]
    def tgt(i, b):
        d = (ef[i] - es[i]) / es[i] * 1e4
        if d > band_bp: pos[0] = 1.0
        elif d < -band_bp: pos[0] = -1.0
        return pos[0]
    return tgt

def donchian_stateful(n):
    pos = [0.0]
    def tgt(i, b):
        if i < n: return pos[0]
        hi = max(H[i-n:i]); lo = min(L[i-n:i])
        if C[i] > hi: pos[0] = 1.0
        elif C[i] < lo: pos[0] = -1.0
        return pos[0]
    return tgt

trace(ema_cross_stateful(60, 240, 25), "EMA 60/240 band 25", warmup=240)
trace(donchian_stateful(240), "Donchian 240", warmup=240)
trace(ema_cross_stateful(30, 60, 25), "EMA 30/60 band 25", warmup=60)

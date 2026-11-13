import csv, math, statistics
rows = list(csv.DictReader(open('upstream/challenges/eth-backtest/bars.csv')))
closes = [float(r['close']) for r in rows]
opens = [float(r['open']) for r in rows]
highs = [float(r['high']) for r in rows]
lows = [float(r['low']) for r in rows]
vols = [float(r['volume']) for r in rows]
n = len(closes)
print(f"bars: {n}")
print(f"start {closes[0]:.2f} -> end {closes[-1]:.2f}  total return {(closes[-1]/closes[0]-1)*100:.2f}%")
print(f"high {max(highs):.2f} low {min(lows):.2f} range {(max(highs)-min(lows)):.2f} ({(max(highs)/min(lows)-1)*100:.2f}%)")
rets = [math.log(closes[i]/closes[i-1]) for i in range(1, n)]
print(f"1m log-ret: mean {statistics.mean(rets)*1e4:.2f} bp, stdev {statistics.stdev(rets)*1e4:.2f} bp")
print(f"hourly vol (ann) approx: {statistics.stdev(rets)*math.sqrt(60)*100:.2f}%")
print(f"avg volume/bar: {statistics.mean(vols):.1f} ETH, min {min(vols):.1f}, max {max(vols):.1f}")
# buy-and-hold drawdown
peak = closes[0]; mdd = 0
for c in closes:
    peak = max(peak, c); mdd = min(mdd, c/peak - 1)
print(f"B&H max drawdown: {mdd*100:.2f}%")
# trend structure: split into 6 x 4h blocks
for k in range(6):
    a, b = k*240, min((k+1)*240, n)
    print(f"  block {k} bars {a}-{b-1}: {closes[a]:.0f} -> {closes[b-1]:.0f} ({(closes[b-1]/closes[a]-1)*100:+.2f}%)")
# autocorrelation of 1m returns (momentum vs mean-reversion)
def autocorr(x, lag):
    m = statistics.mean(x); num = sum((x[i]-m)*(x[i-lag]-m) for i in range(lag, len(x)))
    den = sum((v-m)**2 for v in x)
    return num/den
for lag in (1, 5, 10, 30, 60):
    print(f"  return autocorr lag {lag}: {autocorr(rets, lag):+.3f}")
# hourly returns autocorr (trend persistence at 1h)
hrets = [math.log(closes[i]/closes[i-60]) for i in range(60, n, 60)]
print(f"  hourly returns: {[f'{r*100:+.2f}%' for r in hrets]}")
print(f"  hourly autocorr lag1: {autocorr(hrets,1):+.3f}")

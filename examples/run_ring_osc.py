"""5-stage ring oscillator: schematic, waveforms, and measured period."""

import pathlib
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon

from minispice import parse, transient

here = pathlib.Path(__file__).parent
out = here / "out"
out.mkdir(exist_ok=True)

ckt, analyses = parse((here / "ring_osc.cir").read_text())
VDD = ckt.element("vdd").dc
t0 = time.perf_counter()
res = transient(ckt, *analyses[0][1])
elapsed = time.perf_counter() - t0
t = res.axis

# ---- measurements -----------------------------------------------------------
v1 = res["v(n1)"]
idx = np.where((v1[:-1] < VDD / 2) & (v1[1:] >= VDD / 2))[0]  # rising crossings
cross = t[idx] + (VDD / 2 - v1[idx]) / (v1[idx + 1] - v1[idx]) * (t[idx + 1] - t[idx])
cross = cross[cross > 1e-9]  # skip start-up
period = np.mean(np.diff(cross[-4:]))
n_stages = 5
tpd = period / (2 * n_stages)
i_dd = -res["i(vdd)"]
p_avg = VDD * np.mean(i_dd[t > cross[0]])
swing = (v1[t > 1e-9].min(), v1[t > 1e-9].max())

print(f"stages           : {n_stages}")
print(f"period           : {period * 1e12:.1f} ps  ({1 / period / 1e9:.3f} GHz)")
print(f"stage delay tpd  : {tpd * 1e12:.1f} ps  (T / 2N)")
print(f"swing on n1      : {swing[0]:.3f} .. {swing[1]:.3f} V")
print(f"avg supply power : {p_avg * 1e6:.1f} uW")
print(f"runtime          : {elapsed:.2f} s for {len(t)} points")

# ---- figure -----------------------------------------------------------------
fig = plt.figure(figsize=(12, 8.5), constrained_layout=True)
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.1])

# (a) ring schematic
ax = fig.add_subplot(gs[0, 0])
ax.set_aspect("equal"); ax.axis("off"); ax.set_title("(a) 5-stage ring (block level)")
ang = np.pi / 2 - 2 * np.pi * np.arange(n_stages) / n_stages
R = 1.0
pts = np.c_[R * np.cos(ang), R * np.sin(ang)]
for k, (x, y) in enumerate(pts):
    # inverter drawn pointing clockwise along the ring
    tang = np.array([np.sin(ang[k]), -np.cos(ang[k])])
    nrm = np.array([np.cos(ang[k]), np.sin(ang[k])])
    c = np.array([x, y])
    tri = [c - 0.16 * tang + 0.14 * nrm, c - 0.16 * tang - 0.14 * nrm, c + 0.14 * tang]
    ax.add_patch(Polygon(tri, closed=True, fc="#dbe9ff", ec="#1f3b73", lw=1.5))
    ax.add_patch(Circle(c + 0.18 * tang, 0.035, fc="white", ec="#1f3b73", lw=1.5))
    ax.text(*(c + 0.42 * nrm), f"INV{k + 1}", ha="center", va="center", fontsize=9)
for k in range(n_stages):
    a, b = np.array(pts[k]), np.array(pts[(k + 1) % n_stages])
    ta = np.array([np.sin(ang[k]), -np.cos(ang[k])])
    tb = np.array([np.sin(ang[(k + 1) % n_stages]), -np.cos(ang[(k + 1) % n_stages])])
    start, end = a + 0.215 * ta, b - 0.16 * tb
    ax.annotate("", xy=end, xytext=start,
                arrowprops=dict(arrowstyle="->", color="#444", lw=1.2, shrinkA=0, shrinkB=0))
    mid = (start + end) / 2
    ax.text(*(mid * 1.18), f"n{(k + 1) % n_stages + 1}", ha="center", va="center",
            fontsize=9, color="#b03a00", fontweight="bold")
ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1.4, 1.5)

# (b) one stage at transistor level
ax = fig.add_subplot(gs[0, 1])
ax.set_xlim(0, 10); ax.set_ylim(0, 9); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(b) one stage (transistor level)")
ink = "#1f3b73"
def line(xs, ys, **kw): ax.plot(xs, ys, color=kw.pop("color", ink), lw=kw.pop("lw", 1.6), solid_capstyle="round", **kw)
# rails
line([3, 8], [8.4, 8.4]); ax.text(8.15, 8.4, f"Vdd = {VDD:g} V", va="center", fontsize=9)
line([3, 8], [0.7, 0.7]); ax.text(8.15, 0.7, "GND", va="center", fontsize=9)
# PMOS (top) and NMOS (bottom), gates at x=4.4, channel at x=5
for ytop, name, label in ((6.2, "Mp", "PMOS  W/L = 3u/0.18u"), (2.2, "Mn", "NMOS  W/L = 1u/0.18u")):
    line([5, 5], [ytop - 0.9, ytop + 0.9], lw=2.4)           # channel
    line([4.4, 4.4], [ytop - 0.7, ytop + 0.7], lw=2.4)       # gate plate
    line([5, 6], [ytop + 0.7, ytop + 0.7]); line([5, 6], [ytop - 0.7, ytop - 0.7])
    line([5, 6], [ytop, ytop], lw=1.0)                       # body tie
    ax.text(6.4, ytop, f"{name}\n{label}", va="center", fontsize=8.5)
# PMOS gate bubble
ax.add_patch(Circle((4.25, 6.2), 0.14, fc="white", ec=ink, lw=1.4))
# connections
line([6, 6], [7.0, 8.4]); line([6, 6], [2.9, 0.7])
line([6, 6], [5.5, 2.9]); line([6, 7.5], [4.1, 4.1]); ax.plot([6], [4.1], "o", color=ink, ms=4)
line([2.2, 4.4], [4.2, 4.2]); line([4.4, 4.4], [2.9, 5.5])   # gate net
ax.plot([4.4], [4.2], "o", color=ink, ms=4)
ax.text(1.9, 4.2, "in\n(n_k)", ha="right", va="center", fontsize=9, color="#b03a00", fontweight="bold")
ax.text(7.7, 4.1, "out (n_k+1)", ha="left", va="center", fontsize=9, color="#b03a00", fontweight="bold")
line([7.0, 7.0], [4.1, 3.5], lw=1.2); line([6.6, 7.4], [3.5, 3.5], lw=1.2)
line([6.7, 7.3], [3.3, 3.3], lw=1.2); line([6.85, 7.15], [3.1, 3.1], lw=1.2)
ax.text(7.6, 3.5, "Cw = 5 fF", va="center", fontsize=8.5)
ax.text(3.0, 0.05, "body ties: PMOS to Vdd, NMOS to GND", fontsize=8, color="#555")

# (c) all node waveforms
ax = fig.add_subplot(gs[1, 0])
cols = plt.cm.viridis(np.linspace(0.05, 0.85, n_stages))
for k in range(n_stages):
    ax.plot(t * 1e9, res[f"v(n{k + 1})"], color=cols[k], lw=1.2, label=f"n{k + 1}")
ax.axvspan(0.1, 0.16, color="#b03a00", alpha=0.15, lw=0)
ax.text(0.17, 2.05, "kick (100 uA, 50 ps)", fontsize=8, color="#b03a00", va="bottom")
ax.set(xlabel="t [ns]", ylabel="V", xlim=(0, 1.0), ylim=(-0.15, 2.3),
       title="(c) start-up: DC midpoint -> oscillation")
ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.14), fontsize=8, frameon=False)
ax.grid(alpha=0.25)

# (d) zoom on the last two periods with measurements
ax = fig.add_subplot(gs[1, 1])
tz0 = cross[-3] - 0.15 * period
tz1 = cross[-1] + 0.15 * period
m = (t >= tz0) & (t <= tz1)
for k in range(n_stages):
    ax.plot(t[m] * 1e9, res[f"v(n{k + 1})"][m], color=cols[k], lw=1.2)
ax.axhline(VDD / 2, color="gray", ls=":", lw=1)
ax.annotate("", xy=(cross[-1] * 1e9, 1.95), xytext=(cross[-2] * 1e9, 1.95),
            arrowprops=dict(arrowstyle="<->", color="#b03a00"))
ax.text((cross[-1] + cross[-2]) / 2 * 1e9, 2.0, f"T = {period * 1e12:.0f} ps  ({1 / period / 1e9:.2f} GHz)",
        ha="center", va="bottom", color="#b03a00", fontsize=9, fontweight="bold")
ax.set(xlabel="t [ns]", ylabel="V", ylim=(-0.15, 2.3), title="(d) two periods, 50 % crossings")
ax.text(0.5, -0.2, f"stage delay tpd = T/2N = {tpd * 1e12:.1f} ps    |    avg supply power = {p_avg * 1e3:.2f} mW",
        transform=ax.transAxes, fontsize=9, ha="center", va="top")
ax.grid(alpha=0.25)

fig.suptitle("5-stage CMOS ring oscillator - minispice, Level 1, Vdd = 1.8 V", fontsize=13)
fig.savefig(out / "ring_osc.png", dpi=130)
print("saved", out / "ring_osc.png")

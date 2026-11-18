"""Lesson 9: FinFET - geometry, why 3 gated sides help, and how it maps onto compact-model parameters.

Facts used (see the textbook for sources): effective width per fin = 2*H_fin + W_fin; Intel 22 nm fin pitch 60 nm and
height 34 nm; design rules for DIBL = 100 mV/V from a Berkeley lecture (UTB: t_Si ~ L/5, FinFET: W_Si ~ L/2).
ILLUSTRATIVE (author's choices, not extracted from any process): fin width 8 nm, and the compact-model parameter sets.
"""

import json
import math
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import draw
import draw_multigate as dm
from minispice import EKV
from minispice.models import VT

out = pathlib.Path(__file__).parent / "out"
out.mkdir(exist_ok=True)
J = {}

# ---- 1. geometry --------------------------------------------------------------------------------
H, PITCH = 34.0, 60.0          # nm, Intel 22 nm (found in secondary sources)
WFIN = 8.0                     # nm, ASSUMED for illustration
weff_fin = 2 * H + WFIN
J["geom"] = dict(h=H, pitch=PITCH, wfin=WFIN, weff_fin=weff_fin, ratio_vs_planar=weff_fin / PITCH,
                 rows=[dict(n=n, weff=n * weff_fin, planar=n * PITCH) for n in range(1, 7)])

# ---- 2. body size needed for DIBL = 100 mV/V (Berkeley lecture, Yang & Fossum rule of thumb) -------------------
Ls = np.array([8, 10, 14, 20, 30], float)
J["rules"] = dict(L=Ls.tolist(), utb=(Ls / 5).tolist(), fin=(Ls / 2).tolist())

# ---- 3. compact-model mapping (ILLUSTRATIVE parameter sets) ----------------------------------------------------
VDD, VTO, KP, LAM = 0.8, 0.35, 300e-6, 0.05
SETS = {"planar": dict(n=1.45, eta=0.10), "FinFET": dict(n=1.15, eta=0.04)}
W, L = 1e-6, 20e-9
mdl = {k: EKV(1, dict(vto=VTO, kp=KP, lambda_=LAM, **v)) for k, v in SETS.items()}


def idr(m, vgs, vds):
    return m.evaluate(vds, vgs, 0.0, 0.0, W, L)[0]


vg = np.linspace(0, VDD, 321)
VLIN, VSAT = 0.10, VDD      # 'linear' bias: Vds = 100 mV (>> Vt, so the (1 - exp(-Vds/Vt)) factor is ~0.98)


def vt_cc(m, vds, icc):
    """constant-current threshold: the Vgs at which Id = icc"""
    i = np.array([idr(m, v, vds) for v in vg])
    return float(np.interp(math.log10(icc), np.log10(i), vg))


icc = 1e-7 * (W / L)
res = {}
for name, m in mdl.items():
    p = SETS[name]
    i_lin = np.array([idr(m, v, VLIN) for v in vg])
    i_sat = np.array([idr(m, v, VSAT) for v in vg])
    v1, v2 = 0.00, 0.10      # deep weak inversion, where Id ~ exp(Vgs / (n Vt))
    ss = (v2 - v1) / (math.log10(idr(m, v2, VLIN)) - math.log10(idr(m, v1, VLIN))) * 1e3
    dibl = (vt_cc(m, VLIN, icc) - vt_cc(m, VSAT, icc)) / (VSAT - VLIN) * 1e3
    res[name] = dict(n=p["n"], eta=p["eta"], ss_sim=ss, ss_hand=p["n"] * VT * math.log(10) * 1e3, dibl_sim=dibl, dibl_hand=p["eta"] * 1e3,
                     ioff=idr(m, 0.0, VSAT), ion=idr(m, VDD, VSAT), i_lin=i_lin, i_sat=i_sat)
for k in res:
    res[k]["onoff"] = res[k]["ion"] / res[k]["ioff"]
J["model"] = dict(vdd=VDD, vto=VTO, L=L, icc=icc, sets={k: {x: y for x, y in v.items() if not isinstance(y, np.ndarray)} for k, v in res.items()})
J["model"]["ioff_ratio"] = res["planar"]["ioff"] / res["FinFET"]["ioff"]

# ---- figure ---------------------------------------------------------------------------------------------------------
fig = plt.figure(figsize=(16.5, 9), constrained_layout=True)
gs_ = fig.add_gridspec(2, 3, width_ratios=[1.05, 1.0, 1.1])

ax = fig.add_subplot(gs_[0, 0], projection="3d"); dm.finfet_3d(ax, 2); ax.set_title("(a) FinFET: the gate wraps each fin on 3 sides", pad=-6)

ax = fig.add_subplot(gs_[1, 0]); ax.set_aspect("equal"); ax.axis("off"); ax.set_xlim(-2.0, 13.5); ax.set_ylim(-0.9, 6.3)
dm.planar_xsec(ax, 0.2, 3.6); dm.finfet_xsec(ax, 2, x0=6.3)
ax.text(2.0, 4.15, "planar", ha="center", fontsize=9.5, fontweight="bold", color=dm.INK)
ax.text(9.4, 5.95, f"FinFET, nfin = 2:  W_eff = 2·(2H + W)", ha="center", fontsize=9, fontweight="bold", color=dm.INK)
ax.set_title("(b) cross-section (dashed = gated surface)")

ax = fig.add_subplot(gs_[0, 1]); ax.set_xlim(0, 9); ax.set_ylim(0, 8); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(c) test bench: a FinFET is one MOS with W = nfin·W_eff")
d, s = draw.nmos(ax, 3.6, 4.6)
ax.text(3.2, 7.2, "M1  (FinFET, nfin = 2)", fontsize=9)
draw.vsource(ax, 1.4, 4.6, "Vgs"); draw.wire(ax, [1.85, 3.6], [4.6, 4.6]); draw.wire(ax, [1.4, 1.4], [4.15, 3.0]); draw.ground(ax, 1.4, 3.0)
draw.vsource(ax, 6.9, 4.5, "Vds", side="right"); draw.wire(ax, [6.9, 6.9], [4.95, 6.0]); draw.wire(ax, [6.9, d[0]], [6.0, 6.0])
draw.wire(ax, [6.9, 6.9], [4.05, 2.2]); draw.wire(ax, [s[0], 6.9], [2.2, 2.2]); draw.wire(ax, [s[0], s[0]], [s[1], 2.2]); draw.ground(ax, s[0], 2.2)
draw.dot(ax, d[0], 6.0); draw.dot(ax, s[0], 2.2)
ax.text(0.2, 1.1, f".model fin nmos level=ekv vto={VTO} kp=300u\n  n={SETS['FinFET']['n']} eta={SETS['FinFET']['eta']} lambda={LAM}\nM1 d g 0 0 fin W={2*weff_fin:.0f}n L=20n   * W = nfin*(2H+Wfin)",
        fontsize=7.6, family="monospace", va="center")

ax = fig.add_subplot(gs_[1, 1])
n_ = np.arange(1, 7)
ax.plot(n_, n_ * PITCH, "o--", color="#777", label=f"planar, same footprint (W = nfin × pitch {PITCH:.0f} nm)")
ax.step(n_, n_ * weff_fin, "o-", where="mid", color="#d95f02", lw=2, label=f"FinFET (W_eff = nfin × {weff_fin:.0f} nm)")
for k in (1, 3, 6):
    ax.annotate(f"{k*weff_fin:.0f} nm", (k, k * weff_fin), (0, 8), textcoords="offset points", ha="center", fontsize=8, color="#d95f02")
ax.set(xlabel="number of fins (footprint = nfin × pitch)", ylabel="effective channel width [nm]",
       title=f"(d) width per footprint: ×{weff_fin/PITCH:.2f}, but only in whole fins", xticks=n_, ylim=(30, 520))
ax.legend(loc="upper left", fontsize=8.5); ax.grid(alpha=0.25)
ax.text(0.97, 0.06, f"H = {H:.0f} nm, pitch = {PITCH:.0f} nm (Intel 22 nm, secondary source)\nWfin = {WFIN:.0f} nm is an assumption", transform=ax.transAxes, ha="right", fontsize=8, color="#555")

ax = fig.add_subplot(gs_[0, 2])
ax.plot(Ls, Ls / 5, "o-", color="#777", lw=2, label="ultra-thin-body planar: t_Si ≈ L/5")
ax.plot(Ls, Ls / 2, "o-", color="#d95f02", lw=2, label="FinFET: W_fin ≈ L/2")
for x, y in zip(Ls, Ls / 2):
    ax.annotate(f"{y:g}", (x, y), (0, 7), textcoords="offset points", ha="center", fontsize=8, color="#d95f02")
ax.set(xlabel="gate length L [nm]", ylabel="body size needed for DIBL = 100 mV/V [nm]", title="(e) more gated sides allow a thicker body")
ax.legend(loc="upper left", fontsize=8.5); ax.grid(alpha=0.25)
ax.text(0.97, 0.05, "Tox = 1.1 nm; rule of thumb from a Berkeley lecture\n(after Yang & Fossum, IEEE TED 2005)", transform=ax.transAxes, ha="right", fontsize=8, color="#555")

ax = fig.add_subplot(gs_[1, 2])
cols = {"planar": "#777", "FinFET": "#d95f02"}
for name, r in res.items():
    ax.semilogy(vg, r["i_sat"], color=cols[name], lw=2.2, label=f"{name}  Vds = {VSAT} V")
    ax.semilogy(vg, r["i_lin"], color=cols[name], lw=1.6, ls="--", label=f"{name}  Vds = {VLIN} V")
ax.set(xlabel="Vgs [V]", ylabel="Id [A]  (W/L = 50)", title="(f) Id–Vgs from the model (ILLUSTRATIVE n, η)", ylim=(1e-12, 3e-3))
ax.text(0.03, 0.97, "\n".join(f"{k}: SS {r['ss_sim']:.0f} mV/dec, DIBL {r['dibl_sim']:.0f} mV/V" for k, r in res.items()), transform=ax.transAxes,
        va="top", fontsize=8.5)
ax.legend(loc="lower right", fontsize=8); ax.grid(alpha=0.25, which="both")

fig.suptitle("Lesson 9 - FinFET: from structure to compact-model parameters (minispice EKV, illustrative parameters)", fontsize=13)
fig.savefig(out / "lesson9.png", dpi=130)
(out / "lesson9.json").write_text(json.dumps(J, indent=1, default=float))

print(f"W_eff per fin = 2*{H:.0f} + {WFIN:.0f} = {weff_fin:.0f} nm; per pitch {PITCH:.0f} nm: x{weff_fin/PITCH:.3f}")
for r in J["geom"]["rows"]: print("  nfin", r["n"], "W_eff", r["weff"], "planar", r["planar"])
print("rules:", J["rules"])
for k, r in res.items():
    print(f"{k:7s} n={r['n']} eta={r['eta']}: SS hand {r['ss_hand']:.2f} sim {r['ss_sim']:.2f} mV/dec | DIBL hand {r['dibl_hand']:.1f} sim {r['dibl_sim']:.1f} mV/V | Ioff {r['ioff']:.3e} Ion {r['ion']:.3e} on/off {r['onoff']:.2e}")
print("Ioff ratio planar/FinFET:", J["model"]["ioff_ratio"])

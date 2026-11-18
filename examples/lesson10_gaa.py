"""Lesson 10: gate-all-around (nanosheet) transistors - geometry and what better gate control does to circuits.

Verified facts used: BSIM-CMG GEOMOD 0/1/2/3 = double/triple/quadruple/cylindrical gate; cylindrical effective width = pi*D.
Geometry derivation (not a quoted formula): a gate that surrounds a rectangular sheet gates its whole perimeter, 2*(W+T).
ILLUSTRATIVE (author's choices, not from any process): nanosheet dimensions and the compact-model parameter sets.
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
from minispice import EKV, dc_sweep, parse
from minispice.models import VT

out = pathlib.Path(__file__).parent / "out"
out.mkdir(exist_ok=True)
J = {}

# ---- 1. geometry -----------------------------------------------------------------------------------------
H_FIN, W_FIN = 34.0, 8.0                      # nm (lesson 9)
weff_fin = 2 * H_FIN + W_FIN
T_NS, N_NS, W_NS = 5.0, 3, 30.0               # nm, ILLUSTRATIVE nanosheet
per_sheet = 2 * (W_NS + T_NS)
J["geom"] = dict(weff_fin=weff_fin, t=T_NS, n=N_NS, w=W_NS, per_sheet=per_sheet, weff_ns=N_NS * per_sheet,
                 cyl_d=6.0, cyl_weff=math.pi * 6.0, top_only=W_NS * N_NS)

# ---- 2. compact-model parameter sets (ILLUSTRATIVE) --------------------------------------------------------------
VDD, VTO0, KP, LAM = 0.8, 0.35, 300e-6, 0.05
SETS = {"planar": dict(n=1.45, eta=0.10), "FinFET": dict(n=1.15, eta=0.04), "GAA": dict(n=1.08, eta=0.02)}
COL = {"planar": "#777", "FinFET": "#d95f02", "GAA": "#1b5fb5"}
W, L = 1e-6, 20e-9


def model(name, vto=VTO0, kp=KP):
    return EKV(1, dict(vto=vto, kp=kp, lambda_=LAM, **SETS[name]))


def idr(m, vgs, vds):
    return m.evaluate(vds, vgs, 0.0, 0.0, W, L)[0]


VLIN = 0.10
sets = {}
for k, p in SETS.items():
    m = model(k)
    ss = 0.1 / (math.log10(idr(m, 0.1, VLIN)) - math.log10(idr(m, 0.0, VLIN))) * 1e3
    vg = np.linspace(0, VDD, 321)

    def vt_cc(vds, icc=1e-7 * W / L):
        i = np.array([idr(m, v, vds) for v in vg])
        return float(np.interp(math.log10(icc), np.log10(i), vg))
    dibl = (vt_cc(VLIN) - vt_cc(VDD)) / (VDD - VLIN) * 1e3
    sets[k] = dict(n=p["n"], eta=p["eta"], ss_hand=p["n"] * VT * math.log(10) * 1e3, ss_sim=ss, dibl_hand=p["eta"] * 1e3, dibl_sim=dibl)
J["sets"] = sets

# ---- 3. Ion at a fixed Ioff (VTO sweep) -----------------------------------------------------------------------------
IOFF_T = 1e-9
vtos = np.linspace(0.15, 0.60, 91)
curves = {}
for k in SETS:
    ioff = np.array([idr(model(k, v), 0.0, VDD) for v in vtos])
    ion = np.array([idr(model(k, v), VDD, VDD) for v in vtos])
    curves[k] = (ioff, ion)
    sets[k]["ion_at_target"] = float(np.exp(np.interp(math.log(IOFF_T), np.log(ioff)[::-1], np.log(ion)[::-1])))
    sets[k]["vto_at_target"] = float(np.interp(math.log(IOFF_T), np.log(ioff)[::-1], vtos[::-1]))
J["ioff_target"] = IOFF_T
J["ion_gain_vs_planar"] = {k: sets[k]["ion_at_target"] / sets["planar"]["ion_at_target"] for k in SETS}

# ---- 4. inverter: intrinsic gain (DIBL adds eta*gm to gds) -----------------------------------------------------------------
vtc = {}
for k, p in SETS.items():
    net = f"""inv
.model nch nmos level=ekv vto={VTO0} kp=300u lambda={LAM} n={p['n']} eta={p['eta']}
.model pch pmos level=ekv vto=-{VTO0} kp=100u lambda={LAM} n={p['n']} eta={p['eta']}
Vdd vdd 0 {VDD}
Vin in 0 0
M1 out in 0 0 nch W=1u L=20n
M2 out in vdd vdd pch W=3u L=20n
.end
"""
    c, _ = parse(net)
    r = dc_sweep(c, "vin", 0.0, VDD, 0.002)
    vin, vo = r.axis, r["v(out)"]
    gain = float(np.max(np.abs(np.gradient(vo, vin))))
    j = np.where(np.diff(np.sign(vo - vin)) != 0)[0][0]
    vm = float(vin[j] + (vin[j + 1] - vin[j]) * (vin[j] - vo[j]) / ((vo[j + 1] - vo[j]) - (vin[j + 1] - vin[j])))
    mn, mp = model(k), EKV(-1, dict(vto=-VTO0, kp=100e-6, lambda_=LAM, **p))
    _, gdn, gmn, *_ = mn.evaluate(vm, vm, 0.0, 0.0, 1e-6, 20e-9)
    _, gdp, gmp, *_ = mp.evaluate(vm, vm, VDD, VDD, 3e-6, 20e-9)
    sets[k].update(gain_num=gain, gain_hand=(gmn + gmp) / (gdn + gdp), vm=vm)
    vtc[k] = (vin, vo)

# ---- figure -----------------------------------------------------------------------------------------------------------------
fig = plt.figure(figsize=(16.5, 9), constrained_layout=True)
gs_ = fig.add_gridspec(2, 3, width_ratios=[1.05, 1.0, 1.1])

ax = fig.add_subplot(gs_[0, 0], projection="3d"); dm.gaa_3d(ax, 3); ax.set_title("(a) nanosheet GAA: the gate surrounds every sheet", pad=-6)

ax = fig.add_subplot(gs_[1, 0]); ax.set_aspect("equal"); ax.axis("off"); ax.set_xlim(-0.8, 10.2); ax.set_ylim(-0.9, 6.8)
dm.finfet_xsec(ax, 1, x0=0.0); dm.gaa_xsec(ax, 3, x0=4.6)
ax.text(1.6, 5.6, "FinFET (3 sides)\nW_eff = 2H + W", ha="center", fontsize=8.8, fontweight="bold", color=dm.INK)
ax.text(7.1, 6.05, f"nanosheet GAA (4 sides)\nW_eff = N·2(W + T)", ha="center", fontsize=8.8, fontweight="bold", color=dm.INK)
ax.set_title("(b) cross-section (dashed = gated surface)")

ax = fig.add_subplot(gs_[0, 1])
ws = np.linspace(8, 60, 100)
for n_, ls in ((2, ":"), (3, "-"), (4, "--")):
    ax.plot(ws, n_ * 2 * (ws + T_NS), ls, color=COL["GAA"], lw=2, label=f"nanosheet, N = {n_} sheets (T = {T_NS:g} nm)")
for k in (1, 2, 3):
    ax.axhline(k * weff_fin, color=COL["FinFET"], lw=1.4, alpha=0.7)
    ax.text(8.5, k * weff_fin + 6, f"{k} fin{'s' if k > 1 else ''}: {k*weff_fin:.0f} nm", color=COL["FinFET"], fontsize=8.5)
ax.set(xlabel="sheet width W [nm]", ylabel="effective channel width [nm]", title="(c) width: FinFET in steps, nanosheet continuously tunable", ylim=(0, 560))
ax.legend(loc="lower right", fontsize=8.5); ax.grid(alpha=0.25)
ax.text(0.03, 0.62, "nanosheet sizes are illustrative;\nfin: H = 34 nm (secondary source),\nW_fin = 8 nm (assumed)", transform=ax.transAxes, fontsize=8, color="#555")

ax = fig.add_subplot(gs_[1, 1])
for k, (ioff, ion) in curves.items():
    ax.loglog(ioff, ion * 1e3, color=COL[k], lw=2.2, label=f"{k}  (n = {SETS[k]['n']}, η = {SETS[k]['eta']})")
    ax.plot([IOFF_T], [sets[k]["ion_at_target"] * 1e3], "o", color=COL[k], ms=7)
ax.axvline(IOFF_T, color="gray", ls=":")
ax.text(IOFF_T * 1.3, ax.get_ylim()[0] * 1.15 if False else 0.9, f"Ioff = {IOFF_T*1e9:g} nA", fontsize=8.5, color="gray", rotation=90, va="bottom")
ax.set(xlabel="Ioff  (Vgs = 0, Vds = 0.8 V)  [A]", ylabel="Ion  (Vgs = Vds = 0.8 V)  [mA]", title="(d) Ion–Ioff trade-off (sweep of the threshold voltage)")
ax.legend(loc="lower right", fontsize=8.5); ax.grid(alpha=0.25, which="both")
ax.text(0.03, 0.96, "\n".join(f"{k}: Ion = {sets[k]['ion_at_target']*1e3:.2f} mA  (×{J['ion_gain_vs_planar'][k]:.2f})" for k in SETS),
        transform=ax.transAxes, va="top", fontsize=8.5)

ax = fig.add_subplot(gs_[0, 2])
for k, (vin, vo) in vtc.items():
    ax.plot(vin, vo, color=COL[k], lw=2.2, label=f"{k}: gain {sets[k]['gain_num']:.0f}")
ax.set(xlabel="Vin [V]", ylabel="Vout [V]", title="(e) inverter VTC: DIBL lowers the gain")
ax.legend(loc="upper right", fontsize=8.5); ax.grid(alpha=0.25)

ax = fig.add_subplot(gs_[1, 2])
x = np.arange(3); wd = 0.36
ax.bar(x - wd / 2, [sets[k]["ss_sim"] for k in SETS], wd, color="#8fb0e8", label="subthreshold swing [mV/dec]")
ax.bar(x + wd / 2, [sets[k]["dibl_sim"] for k in SETS], wd, color="#f0a96a", label="DIBL [mV/V]")
for i, k in enumerate(SETS):
    ax.text(i - wd / 2, sets[k]["ss_sim"] + 1.5, f"{sets[k]['ss_sim']:.0f}", ha="center", fontsize=8.5)
    ax.text(i + wd / 2, sets[k]["dibl_sim"] + 1.5, f"{sets[k]['dibl_sim']:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(x, [f"{k}\n({s})" for k, s in zip(SETS, ("1 gated side", "3 gated sides", "4 gated sides"))])
ax.set(title="(f) more gated sides → smaller n and η (ILLUSTRATIVE inputs)", ylim=(0, 125))
ax.legend(loc="upper right", fontsize=8.5); ax.grid(alpha=0.25, axis="y")

fig.suptitle("Lesson 10 - gate-all-around (nanosheet): geometry and the effect of better gate control (minispice EKV, illustrative parameters)", fontsize=12.5)
fig.savefig(out / "lesson10.png", dpi=130)
(out / "lesson10.json").write_text(json.dumps(J, indent=1, default=float))

g = J["geom"]
print(f"nanosheet: per sheet 2*({g['w']:.0f}+{g['t']:.0f}) = {g['per_sheet']:.0f} nm; x{g['n']} sheets = {g['weff_ns']:.0f} nm  (top face only would be {g['top_only']:.0f} nm); FinFET per fin {weff_fin:.0f} nm")
print(f"cylinder D={g['cyl_d']:.0f} nm: pi*D = {g['cyl_weff']:.1f} nm")
for k, v in sets.items():
    print(f"{k:7s} SS hand {v['ss_hand']:.1f} sim {v['ss_sim']:.1f} | DIBL hand {v['dibl_hand']:.0f} sim {v['dibl_sim']:.1f} | Ion@Ioff=1nA {v['ion_at_target']*1e3:.3f} mA (VTO {v['vto_at_target']:.3f}) x{J['ion_gain_vs_planar'][k]:.2f} | gain hand {v['gain_hand']:.1f} num {v['gain_num']:.1f} Vm {v['vm']:.3f}")

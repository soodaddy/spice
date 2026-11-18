"""Lesson 11: DRAM 1T1C cell - word line, bit line, storage capacitor; write, read (charge sharing + sense amplifier), retention.

Sourced facts (see the textbook): charge-sharing swing dV = (Vcell - Vblp) * Cs/(Cs + Cbl), the complementary bit line stays at the
precharge level, a boosted word line Vpp > Vdd + Vth is needed to write a full level, 64 ms refresh is the worst-case specification.
ILLUSTRATIVE (author's values, not any product): Cs = 25 fF, Cbl = 150 fF, Vdd = 1.2 V, Vth = 0.7 V, the device sizes.
"""

import json
import math
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle

import draw
from minispice import EKV, Level1, parse, transient
from minispice.models import VT
from dram_retention import is_hand, retention
from ngspice_util import run_ngspice

here = pathlib.Path(__file__).parent
out = here / "out"
out.mkdir(exist_ok=True)
work = out / "ngspice"
J = {}

VDD, VBLP, VPP, VTH = 1.2, 0.6, 2.0, 0.7
CS, CBL = 25e-15, 150e-15
KP_ACC, WL_ACC = 300e-6, 1.0                 # access transistor W/L = 0.1 um / 0.1 um
BETA = KP_ACC * WL_ACC
J["params"] = dict(vdd=VDD, vblp=VBLP, vpp=VPP, vth=VTH, cs=CS, cbl=CBL, beta=BETA)


def cross(t, v, lvl, rising, t0=0.0):
    for i in range(1, len(t)):
        if t[i] >= t0 and ((v[i - 1] < lvl <= v[i]) if rising else (v[i - 1] > lvl >= v[i])):
            return t[i - 1] + (lvl - v[i - 1]) / (v[i] - v[i - 1]) * (t[i] - t[i - 1])
    return float("nan")


# ---------------------------------------------------------------------------------------------- 1. write
def write_net(vpp):
    return f"""DRAM write 1 then write 0
.model nacc nmos level=1 vto={VTH} kp=300u lambda=0.05
Vbl bl 0 PULSE(0 {VDD} 0.5n 0.1n 0.1n 8n 40n)
Vwl wl 0 PULSE(0 {vpp} 1n 0.2n 0.2n 16n 40n)
M1 bl wl sn 0 nacc W=0.1u L=0.1u
Cs sn 0 25f
.end
"""


write = {}
for vpp in (1.2, 1.9, 2.0, 2.5):
    r = transient(parse(write_net(vpp))[0], 10e-12, 20e-9)
    t, sn = r.axis, r["v(sn)"]
    hand_level = min(VDD, vpp - VTH)
    tail = None
    if vpp > VDD + VTH:                                           # exponential tail of the write-1 transient
        m = (t > 1.5e-9) & (t < 8.5e-9) & (VDD - sn > 0.01) & (VDD - sn < 0.08)
        if m.sum() > 5:
            tail = -1 / np.polyfit(t[m], np.log(VDD - sn[m]), 1)[0]
    write[vpp] = dict(level_sim=float(sn[np.searchsorted(t, 8.5e-9)]), level_hand=hand_level, tau_tail_hand=(CS / (BETA * (vpp - VTH - VDD)) if vpp > VDD + VTH else float("inf")),
                      tau_tail_sim=tail, t90=cross(t, sn, 0.9 * hand_level, True, 1e-9) - 1e-9, zero_level=float(sn[np.searchsorted(t, 17e-9)]),
                      t_to_zero=cross(t, sn, 0.1 * VDD, False, 8.7e-9) - 8.7e-9, t=t, sn=sn, bl=r["v(bl)"], wl=r["v(wl)"])
J["write"] = {str(k): {kk: vv for kk, vv in v.items() if not isinstance(vv, np.ndarray)} for k, v in write.items()}


# ---------------------------------------------------------------------------------------------- 2. read: charge sharing
def share_net(vcell, vpp=VPP):
    return f"""DRAM read: charge sharing
.model nacc nmos level=1 vto={VTH} kp=300u lambda=0.05
.model nsw nmos level=1 vto=0.5 kp=300u lambda=0.05
Vblp vblp 0 {VBLP}
Vcell vcell 0 {vcell}
Veq eq 0 PULSE({vpp} 0 0.3n 0.1n 0.1n 100n 200n)
Vwl wl 0 PULSE(0 {vpp} 1n 0.2n 0.2n 20n 40n)
Meq bl eq vblp 0 nsw W=1u L=0.1u
Mwr sn eq vcell 0 nsw W=1u L=0.1u
Macc bl wl sn 0 nacc W=0.1u L=0.1u
Cbl bl 0 150f
Cs sn 0 25f
.end
"""


share = {}
for key, vc in (("1", VDD), ("0", 0.0), ("1_unboosted", min(VDD, 1.2 - VTH))):
    r = transient(parse(share_net(vc))[0], 5e-12, 6e-9)
    hand = VBLP + (vc - VBLP) * CS / (CS + CBL)
    share[key] = dict(vcell=vc, bl_sim=float(r["v(bl)"][-1]), sn_sim=float(r["v(sn)"][-1]), bl_hand=hand, dv_hand=hand - VBLP,
                      t_settle=cross(r.axis, r["v(bl)"], VBLP + 0.9 * (hand - VBLP), vc > VBLP, 1e-9) - 1e-9 if vc != VBLP else float("nan"))
J["share"] = share
net = share_net(VDD)
r = transient(parse(net)[0], 5e-12, 6e-9)
ng = run_ngspice(net, "dram_share1", "tran 5p 6n 0 5p", ["v(bl)", "v(sn)"], work)
J["share_ng"] = dict(bl=float(np.max(np.abs(np.interp(r.axis, ng[:, 0], ng[:, 1]) - r["v(bl)"]))), sn=float(np.max(np.abs(np.interp(r.axis, ng[:, 0], ng[:, 2]) - r["v(sn)"]))))
net = write_net(VPP)
r = transient(parse(net)[0], 10e-12, 20e-9)
ng = run_ngspice(net, "dram_write", "tran 10p 20n 0 10p", ["v(sn)"], work)
J["write_ng"] = dict(sn=float(np.max(np.abs(np.interp(r.axis, ng[:, 0], ng[:, 1]) - r["v(sn)"]))))
i_max = int(np.argmax(np.abs(np.interp(r.axis, ng[:, 0], ng[:, 1]) - r["v(sn)"])))
J["write_ng"]["t_at_max"] = float(r.axis[i_max])                               # the largest difference sits on the fast falling edge: a time-grid effect
r1 = transient(parse(net)[0], 1e-12, 20e-9)
ng1 = run_ngspice(net, "dram_write_1ps", "tran 1p 20n 0 1p", ["v(sn)"], work)
J["write_ng"]["sn_1ps"] = float(np.max(np.abs(np.interp(r1.axis, ng1[:, 0], ng1[:, 1]) - r1["v(sn)"])))

# sense margin from the charge-sharing formula
cbls = np.linspace(50e-15, 300e-15, 51)
J["margin"] = dict(cbl=(cbls * 1e15).tolist(), **{f"cs{int(c*1e15)}": ((VDD - VBLP) * c / (c + cbls) * 1e3).tolist() for c in (15e-15, 25e-15, 35e-15)})


# ---------------------------------------------------------------------------------------------- 3. sense amplifier: transistor-level read cycle
def cycle_net(vcell, vpp=VPP):
    return f"""DRAM read cycle with a latch sense amplifier
.model nacc nmos level=1 vto={VTH} kp=300u lambda=0.05
.model nsw nmos level=1 vto=0.5 kp=300u lambda=0.05
.model nsa nmos level=1 vto=0.4 kp=300u lambda=0.05
.model psa pmos level=1 vto=-0.4 kp=100u lambda=0.05
Vblp vblp 0 {VBLP}
Vcell vcell 0 {vcell}
Vdd vdd 0 {VDD}
Veq eq 0 PULSE({vpp} 0 0.3n 0.1n 0.1n 100n 200n)
Vwl wl 0 PULSE(0 {vpp} 1n 0.2n 0.2n 11n 40n)
Vsan san 0 PULSE({VBLP} 0 4n 0.5n 0.5n 100n 200n)
Vsap sap 0 PULSE({VBLP} {VDD} 4n 0.5n 0.5n 100n 200n)
Meq1 bl eq vblp 0 nsw W=1u L=0.1u
Meq2 blb eq vblp 0 nsw W=1u L=0.1u
Mwr sn eq vcell 0 nsw W=1u L=0.1u
Macc bl wl sn 0 nacc W=0.1u L=0.1u
Cbl bl 0 150f
Cblb blb 0 150f
Cs sn 0 25f
Mn1 bl blb san 0 nsa W=2u L=0.1u
Mn2 blb bl san 0 nsa W=2u L=0.1u
Mp1 bl blb sap vdd psa W=4u L=0.1u
Mp2 blb bl sap vdd psa W=4u L=0.1u
.end
"""


cycle = {}
for key, vc in (("1", VDD), ("0", 0.0)):
    net = cycle_net(vc)
    r = transient(parse(net)[0], 5e-12, 14e-9)
    ng = run_ngspice(net, f"dram_cycle{key}", "tran 5p 14n 0 5p", ["v(bl)", "v(blb)", "v(sn)"], work)
    t = r.axis
    diffs = {n: float(np.max(np.abs(np.interp(t, ng[:, 0], ng[:, k]) - r[f"v({n})"]))) for k, n in ((1, "bl"), (2, "blb"), (3, "sn"))}
    i39 = np.searchsorted(t, 3.9e-9)
    D = r["v(bl)"] - r["v(blb)"]
    m = (t > 4.5e-9) & (np.abs(D) > 0.3) & (np.abs(D) < 0.9)
    tau = 1 / np.polyfit(t[m], np.log(np.abs(D[m])), 1)[0] if m.sum() > 3 else float("nan")
    cycle[key] = dict(dv_before_sa=float(D[i39]), bl_end=float(r["v(bl)"][-1]), blb_end=float(r["v(blb)"][-1]), sn_restored=float(r["v(sn)"][np.searchsorted(t, 10.9e-9)]),
                      tau_fit=float(abs(tau)), ng=diffs, t=t, bl=r["v(bl)"], blb=r["v(blb)"], sn=r["v(sn)"], wl=r["v(wl)"])
nsa, psa = Level1(1, dict(vto=0.4, kp=300e-6, lambda_=0.05)), Level1(-1, dict(vto=-0.4, kp=100e-6, lambda_=0.05))
gmn, gmp = nsa.evaluate(0.6, 0.6, 0.0, 0, 2e-6, 0.1e-6)[2], abs(psa.evaluate(0.6, 0.6, VDD, VDD, 4e-6, 0.1e-6)[2])
J["sa"] = dict(gmn=gmn, gmp=gmp, tau_hand=CBL / (gmn + gmp))
# small-signal check of the hand time constant: enable the latch quickly (20 ps edges) so that D grows from 86 mV while gm is constant,
# then fit ln D in the small-signal window 0.12-0.30 V (the realistic 0.5 ns enable ramp above is fitted in the large-signal window 0.3-0.9 V)
fast = cycle_net(VDD).replace(f"PULSE({VBLP} 0 4n 0.5n 0.5n 100n 200n)", f"PULSE({VBLP} 0 4n 0.02n 0.02n 100n 200n)").replace(f"PULSE({VBLP} {VDD} 4n 0.5n 0.5n 100n 200n)", f"PULSE({VBLP} {VDD} 4n 0.02n 0.02n 100n 200n)")
rf = transient(parse(fast)[0], 1e-12, 6e-9)
Df, tf = rf["v(bl)"] - rf["v(blb)"], rf.axis
mf = (tf > 4.03e-9) & (Df > 0.12) & (Df < 0.30)
J["sa"]["tau_small"] = float(1 / np.polyfit(tf[mf], np.log(Df[mf]), 1)[0])
mf = (tf > 4.03e-9) & (Df > 0.30) & (Df < 0.90)
J["sa"]["tau_large"] = float(1 / np.polyfit(tf[mf], np.log(Df[mf]), 1)[0])
J["cycle"] = {k: {kk: vv for kk, vv in v.items() if not isinstance(vv, np.ndarray)} for k, v in cycle.items()}


# ---------------------------------------------------------------------------------------------- 4. retention (leakage of the off access transistor)
# retention() and is_hand() live in dram_retention.py (shared with the tests)
ret = {}
for vth, vwl in ((0.5, 0.0), (0.6, 0.0), (0.7, 0.0), (0.8, 0.0), (0.5, -0.2), (0.5, -0.4)):
    r1, r0 = retention(vth, vwl, True), retention(vth, vwl, False)
    i_hand = is_hand(vth, vwl) + 0.2e-15                                  # worst case: bit line at 0 V (source), Vds = Vdd, plus the junction
    ret[f"{vth}|{vwl}"] = dict(vth=vth, vwl=vwl, t1=r1["tret"], t0=r0["tret"], i1_hand=i_hand, t1_hand=CS * (r1["vh"] - r1["vlim"]) / i_hand, vlim1=r1["vlim"], vlim0=r0["vlim"], vh=r1["vh"],
                               t1_precharge=retention(vth, vwl, True, vbl="pre")["tret"], v0_end=r0["vs"][-1], t0_end=r0["ts"][-1])
J["retention"] = ret
J["ret_curves"] = {k: dict(t=retention(v["vth"], v["vwl"], True)["ts"], v=retention(v["vth"], v["vwl"], True)["vs"]) for k, v in ret.items() if v["vwl"] == 0.0 and v["vth"] in (0.5, 0.6, 0.7)}

# ---------------------------------------------------------------------------------------------- figure
fig = plt.figure(figsize=(16.5, 9.2), constrained_layout=True)
gs_ = fig.add_gridspec(2, 3, width_ratios=[1.05, 1.1, 1.05])

# (a) equivalent circuit
ax = fig.add_subplot(gs_[0, 0]); ax.set_xlim(0, 11.5); ax.set_ylim(0, 9.4); ax.set_aspect("equal"); ax.axis("off"); ax.set_title("(a) 1T1C cell: equivalent circuit")
draw.wire(ax, [0.6, 9.4], [7.9, 7.9], lw=3)
ax.text(0.6, 8.25, "BL (bit line)", color=draw.HOT, fontweight="bold", fontsize=10)
d, s = draw.nmos(ax, 3.8, 4.7)                                  # d = (5.4, 6.1), s = (5.4, 3.3)
draw.wire(ax, [5.4, 5.4], [6.1, 7.9]); draw.dot(ax, 5.4, 7.9)
draw.wire(ax, [0.4, 3.8], [4.7, 4.7], lw=2.4, color=draw.HOT); ax.text(0.4, 5.05, "WL (word line)", color=draw.HOT, fontweight="bold", fontsize=9)
ax.text(5.75, 4.7, "access\nNMOS", fontsize=8.5, color="#555")
draw.wire(ax, [5.4, 5.4], [3.3, 2.7]); draw.dot(ax, 5.4, 2.7); ax.text(5.7, 2.75, "SN (storage node)", color=draw.HOT, fontweight="bold", fontsize=9)
draw.capacitor(ax, 5.4, 2.7, 1.1); ax.text(5.95, 1.9, "Cs", fontsize=11, color=draw.HOT, fontweight="bold"); draw.ground(ax, 5.4, 1.1); ax.text(6.0, 0.55, "plate", fontsize=8.5, color="#555")
draw.capacitor(ax, 8.2, 7.9, 6.0); ax.text(8.75, 6.85, "Cbl", fontsize=11, color=draw.HOT, fontweight="bold"); draw.ground(ax, 8.2, 6.0)
ax.add_patch(Rectangle((9.4, 7.2), 1.9, 1.4, fc="#e8e0f5", ec=draw.INK, lw=1.6)); ax.text(10.35, 7.9, "sense\namp", ha="center", va="center", fontsize=9)
ax.text(10.35, 6.75, "(BLB reference\nat Vdd/2)", ha="center", va="top", fontsize=7.5, color="#555")

# (b) cell cross-section
ax = fig.add_subplot(gs_[1, 0]); ax.set_xlim(0, 15); ax.set_ylim(-0.6, 10.5); ax.set_aspect("equal"); ax.axis("off"); ax.set_title("(b) the same cell: cross-section (not to scale)")
ax.add_patch(Rectangle((0, 0), 15, 3, fc="#e6ecf5", ec=draw.INK, lw=1.2)); ax.text(0.3, 0.3, "p-type substrate", fontsize=8.5)
for x0 in (0, 13.2):
    ax.add_patch(Rectangle((x0, 2.2), 1.8, 0.8, fc="#d4d7dc", ec=draw.INK, lw=1, hatch="///"))
ax.add_patch(Rectangle((2.2, 2.2), 2.4, 0.8, fc="#f2b98f", ec=draw.INK, lw=1.2)); ax.text(3.4, 2.6, "n+", ha="center", va="center", fontsize=9, fontweight="bold")
ax.add_patch(Rectangle((8.2, 2.2), 2.4, 0.8, fc="#f2b98f", ec=draw.INK, lw=1.2)); ax.text(9.4, 2.6, "n+", ha="center", va="center", fontsize=9, fontweight="bold")
ax.add_patch(Rectangle((4.4, 3.0), 4.0, 0.2, fc="#f6e27a", ec=draw.INK, lw=1)); ax.add_patch(Rectangle((4.4, 3.2), 4.0, 0.9, fc="#7f8794", ec=draw.INK, lw=1.2))
ax.text(6.4, 3.65, "WL (gate)", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
ax.add_patch(Rectangle((4.2, 2.95), 4.4, 0.1, fc="#2f8cff", ec="none"))
draw.wire(ax, [3.4, 3.4], [3.0, 4.6], lw=3); ax.text(0.3, 3.9, "SN contact", fontsize=8, color=draw.HOT)                  # storage-node plug
ax.add_patch(Rectangle((1.6, 4.6), 3.6, 5.2, fc="#dcdfe4", ec=draw.INK, lw=1.2, hatch="..")); ax.text(1.75, 9.95, "plate electrode", fontsize=8, color="#555")
ax.add_patch(Rectangle((2.1, 4.6), 2.6, 4.7, fc="#f6e27a", ec=draw.INK, lw=1)); ax.add_patch(Rectangle((2.4, 4.6), 2.0, 4.4, fc="#f2b98f", ec=draw.INK, lw=1.2))
ax.text(3.4, 6.8, "Cs\n(stacked\ncapacitor)", ha="center", va="center", fontsize=8.5, fontweight="bold")
draw.wire(ax, [9.4, 9.4], [3.0, 7.4], lw=3); ax.text(9.7, 5.0, "BL contact", fontsize=8, color=draw.HOT)
draw.wire(ax, [6.5, 14.6], [7.6, 7.6], lw=5); ax.text(11.2, 8.0, "BL (bit line), runs ⊥ to the word line", fontsize=8.5, color=draw.HOT, fontweight="bold")
ax.text(5.2, 1.6, "channel (when WL is high)", fontsize=7.5, color="#1b5fb5", ha="center")

# (c) write
ax = fig.add_subplot(gs_[0, 1])
cols = {1.2: "#7570b3", 1.9: "#e6ab02", 2.0: "#1b9e77", 2.5: "#d95f02"}
for vpp, w in write.items():
    ax.plot(w["t"] * 1e9, w["sn"], color=cols[vpp], lw=2.2, label=f"Vpp = {vpp} V: write-1 level {w['level_sim']:.2f} V")
ax.plot(write[2.0]["t"] * 1e9, write[2.0]["bl"], color="#999", ls="--", lw=1.2, label="BL (data)")
ax.axhline(VDD, color="gray", ls=":", lw=1); ax.text(0.2, VDD + 0.03, "Vdd = 1.2 V", fontsize=8.5, color="gray")
ax.set(xlabel="t [ns]", ylabel="storage node V(SN) [V]", title="(c) write 1, then 0: Vpp sets the stored level", xlim=(0, 20), ylim=(-0.05, 1.5))
ax.legend(loc="upper right", fontsize=8); ax.grid(alpha=0.25)

# (d) read cycle
ax = fig.add_subplot(gs_[1, 1])
c1, c0 = cycle["1"], cycle["0"]
ax.plot(c1["t"] * 1e9, c1["wl"] / VPP * 0.4 + 1.3, color="#8a91a0", lw=1.4, label="WL (scaled)")
ax.plot(c1["t"] * 1e9, c1["bl"], color="#1f3b73", lw=2.2, label="BL, stored 1"); ax.plot(c1["t"] * 1e9, c1["blb"], color="#1f3b73", lw=1.4, ls="--", label="BLB")
ax.plot(c1["t"] * 1e9, c1["sn"], color="#d95f02", lw=2, label="SN, stored 1 (restored)")
ax.plot(c0["t"] * 1e9, c0["bl"], color="#1b9e77", lw=2, label="BL, stored 0")
ax.annotate(f"charge sharing\nΔV = ±{abs(share['1']['dv_hand'])*1e3:.0f} mV", (3.0, 0.6857), (1.6, 0.15), fontsize=8.5, arrowprops=dict(arrowstyle="->"))
ax.axvline(4.0, color="#bbb", ls=":", lw=1); ax.text(4.08, 1.0, "SA on", fontsize=8.5, color="#555"); ax.text(1.0, 1.72, "WL on", fontsize=8.5, color="#555"); ax.text(11.2, 1.72, "WL off", fontsize=8.5, color="#555")
ax.set(xlabel="t [ns]", ylabel="voltage [V]", title="(d) read cycle: share → sense → restore", xlim=(0, 14), ylim=(-0.1, 1.85))
ax.legend(loc="center right", fontsize=7.8); ax.grid(alpha=0.25)

# (e) retention
ax = fig.add_subplot(gs_[0, 2])
for k, c in zip(J["ret_curves"], ("#1b5fb5", "#d95f02", "#1b9e77")):
    cu = J["ret_curves"][k]; vth = float(k.split("|")[0]); ax.semilogx(np.maximum(cu["t"], 1e-4), cu["v"], color=c, lw=2.2, label=f"Vth = {vth} V: {ret[k]['t1']:.3g} s")
ax.axhline(ret["0.5|0.0"]["vlim1"], color="gray", ls=":"); ax.text(2e-4, ret["0.5|0.0"]["vlim1"] + 0.015, "sensing limit for a stored 1", fontsize=8.5, color="gray")
ax.set(xlabel="time after the write [s]", ylabel="V(SN) of a stored 1 [V]", title="(e) retention of a stored 1 (worst-case BL = 0 V)", xlim=(1e-4, 1e3), ylim=(0.5, 1.28))
ax.legend(loc="upper right", fontsize=8.5, title="time to the sensing limit", title_fontsize=8); ax.grid(alpha=0.25, which="both")

# (f) sense margin
ax = fig.add_subplot(gs_[1, 2])
for key, c in (("cs15", "#d95f02"), ("cs25", "#1f3b73"), ("cs35", "#1b9e77")):
    ax.plot(J["margin"]["cbl"], J["margin"][key], color=c, lw=2.2, label=f"Cs = {key[2:]} fF")
ax.plot([150], [abs(share["1"]["dv_hand"]) * 1e3], "o", color="#c00", ms=8); ax.annotate("this lesson:\nCs = 25 fF, Cbl = 150 fF", (150, abs(share["1"]["dv_hand"]) * 1e3), (170, 150), fontsize=8.5, arrowprops=dict(arrowstyle="->"))
ax.axhline(20, color="gray", ls=":"); ax.text(52, 24, "20 mV: assumed sense-amp offset", fontsize=8.5, color="gray")
ax.set(xlabel="bit-line capacitance Cbl [fF]", ylabel="read signal |ΔV| [mV]", title="(f) read signal vs. bit-line capacitance", ylim=(0, 260))
ax.legend(loc="upper right", fontsize=8.5); ax.grid(alpha=0.25)

fig.suptitle("Lesson 11 - DRAM 1T1C cell: word line, bit line, storage capacitor (minispice, illustrative values)", fontsize=13)
fig.savefig(out / "lesson11.png", dpi=130)
def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if (math.isinf(o) or math.isnan(o)) else float(o)
    return o


(out / "lesson11.json").write_text(json.dumps(clean(J), indent=1))

print("WRITE")
for k, w in write.items(): print(f"  Vpp={k}: level sim {w['level_sim']:.4f} hand {w['level_hand']:.3f} | tail tau sim {w['tau_tail_sim']} hand {w['tau_tail_hand']} | t90 {w['t90']*1e9:.3f} ns | write0 level {w['zero_level']:.4f}, t to 10% {w['t_to_zero']*1e9:.3f} ns")
print("SHARE", {k: (round(v['bl_sim'], 5), round(v['bl_hand'], 5)) for k, v in share.items()}, "| ngspice max diff (mV):", {k: round(v * 1e3, 3) for k, v in J["share_ng"].items()}, "| write ngspice (mV):", round(J["write_ng"]["sn"] * 1e3, 3))
print("CYCLE", {k: {kk: (round(vv, 4) if isinstance(vv, float) else {a: round(b * 1e3, 3) for a, b in vv.items()}) for kk, vv in v.items()} for k, v in J["cycle"].items()})
print("SA gm", J["sa"])
print("RETENTION")
for k, v in ret.items(): print(f"  Vth={v['vth']} Vwl={v['vwl']}: stored1 {v['t1']:.4g} s (hand {v['t1_hand']:.4g} s, I {v['i1_hand']:.3g} A) | with BL at Vdd/2: {v['t1_precharge']:.4g} s | stored0 {v['t0']:.4g} s")
print("SA tau: hand", round(J['sa']['tau_hand'] * 1e12, 1), "ps | small-signal fit", round(J['sa']['tau_small'] * 1e12, 1), "ps | large-signal fit", round(J['sa']['tau_large'] * 1e12, 1), "ps | realistic-ramp fit (ps):", {k: round(v['tau_fit'] * 1e12, 1) for k, v in J['cycle'].items()})

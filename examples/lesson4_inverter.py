"""Lesson 4: CMOS inverter (NMOS + PMOS). VTC, regions, gain, supply current, transient."""

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import draw
from minispice import Level1, dc_sweep, parse, transient

out = pathlib.Path(__file__).parent / "out"
out.mkdir(exist_ok=True)

VDD, CL = 1.8, 20e-15
WN, WP, L = 1e-6, 3e-6, 0.18e-6
NETLIST = f"""Lesson 4: CMOS inverter
.model nch nmos level=1 vto=0.5 kp=300u lambda=0.05
.model pch pmos level=1 vto=-0.5 kp=100u lambda=0.05
Vdd vdd 0 {VDD}
Vin in 0 PULSE(0 {VDD} 0.2n 0.1n 0.1n 0.8n 2n)
M1 out in 0 0 nch W=1u L=0.18u
M2 out in vdd vdd pch W=3u L=0.18u
CL out 0 20f
.dc Vin 0 {VDD} 0.001
.tran 5p 4n
.end
"""
nm = Level1(1, dict(vto=0.5, kp=300e-6, lambda_=0.05))
pm = Level1(-1, dict(vto=-0.5, kp=100e-6, lambda_=0.05))
J = {}

ckt, an = parse(NETLIST)
vtc = dc_sweep(ckt, *an[0][1])
vin, vout, idd = vtc.axis, vtc["v(out)"], -vtc["i(vdd)"]


def region(model, vd, vg, vs, vb=0.0):
    pol = model.polarity
    vgs, vds = pol * (vg - vs), pol * (vd - vs)
    vov = vgs - pol * model.p["vto"]
    return 0 if vov <= 0 else (1 if vds < vov else 2)   # 0 cutoff, 1 triode, 2 saturation


rn = np.array([region(nm, o, i, 0.0) for i, o in zip(vin, vout)])
rp = np.array([region(pm, o, i, VDD, VDD) for i, o in zip(vin, vout)])

# ---- numbers ----------------------------------------------------------------
bn, bp = 300e-6 * WN / L, 100e-6 * WP / L
J["beta_n"], J["beta_p"] = bn, bp
vm_ideal = (VDD - 0.5 + np.sqrt(bn / bp) * 0.5) / (1 + np.sqrt(bn / bp))
k = np.where(np.diff(np.sign(vout - vin)) != 0)[0][0]
vm = vin[k] + (vin[k + 1] - vin[k]) * (vin[k] - vout[k]) / ((vout[k + 1] - vout[k]) - (vin[k + 1] - vin[k]))
J["vm_ideal"], J["vm"] = vm_ideal, vm
gain_num = np.max(np.abs(np.gradient(vout, vin)))
i0, gdn, gmn, *_ = nm.evaluate(vm, vm, 0.0, 0.0, WN, L)
ip, gdp, gmp, *_ = pm.evaluate(vm, vm, VDD, VDD, WP, L)
gain_hand = (gmn + gmp) / (gdn + gdp)
J.update(gain_num=gain_num, gain_hand=gain_hand, gmn=gmn, gmp=gmp, gdsn=gdn, gdsp=gdp, i_sc_hand=i0)
J["i_sc_peak"] = idd.max()
J["i_static_0"], J["i_static_hi"] = idd[0], idd[-1]
J["vout_at_vm"] = float(np.interp(0.9, vin, vout))

# hand Newton at Vin = 0.6, starting from the previous sweep point (Vout ~ 1.8)
VIN_H = 0.6
newton = []
vo = VDD
for it in range(1, 7):
    idn, gn, *_ = nm.evaluate(vo, VIN_H, 0.0, 0.0, WN, L)
    idp, gp, *_ = pm.evaluate(vo, VIN_H, VDD, VDD, WP, L)
    f = idn + idp                      # KCL at out: current into both drains must cancel
    vn = vo - f / (gn + gp)
    newton.append(dict(it=it, vo=vo, idn=idn, isd=-idp, gdsn=gn, gdsp=gp, f=f, vnew=vn))
    if abs(vn - vo) < 1e-10:
        break
    vo = vn
J["newton"] = newton
J["newton_vin"] = VIN_H
J["newton_solver"] = float(np.interp(VIN_H, vin, vout))

# ---- transient ----------------------------------------------------------------
res = transient(parse(NETLIST)[0], *an[1][1])
t, tin, tout, tidd = res.axis, res["v(in)"], res["v(out)"], -res["i(vdd)"]


def cross(t, v, level, t0, rising):
    for i in range(1, len(t)):
        if t[i] < t0:
            continue
        a, b = v[i - 1], v[i]
        if (a < level <= b) if rising else (a > level >= b):
            return t[i - 1] + (level - a) / (b - a) * (t[i] - t[i - 1])


tin_r, tin_f = cross(t, tin, VDD / 2, 0.0, True), cross(t, tin, VDD / 2, 0.9e-9, False)
tout_f, tout_r = cross(t, tout, VDD / 2, 0.0, False), cross(t, tout, VDD / 2, 0.9e-9, True)
J["tphl"], J["tplh"] = tout_f - tin_r, tout_r - tin_f
J["fall_1090"] = cross(t, tout, 0.1 * VDD, 0.0, False) - cross(t, tout, 0.9 * VDD, 0.0, False)
J["rise_1090"] = cross(t, tout, 0.9 * VDD, 0.9e-9, True) - cross(t, tout, 0.1 * VDD, 0.9e-9, True)
m = (t >= 0.2e-9) & (t <= 2.2e-9)                    # exactly one input period
J["e_cycle"] = float(np.trapezoid(VDD * tidd[m], t[m]))
J["e_cv2"] = CL * VDD**2
J["i_sc_tran_peak"] = float(tidd.max())
J["tstep"] = float(t[1] - t[0])

# ---- figure -----------------------------------------------------------------
fig = plt.figure(figsize=(16, 8.4), constrained_layout=True)
gs_ = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.15, 1.15])

ax = fig.add_subplot(gs_[0, 0]); ax.set_xlim(0, 9); ax.set_ylim(0, 10); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(a) CMOS inverter")
ps, pd = draw.pmos(ax, 3.6, 6.3)      # source top (5.2, 7.7), drain bottom (5.2, 4.9)
ndr, nsr = draw.nmos(ax, 3.6, 2.7)    # drain top (5.2, 4.1), source bottom (5.2, 1.3)
draw.wire(ax, [4.2, 4.2, 3.0], [6.3, 6.3, 6.3]); draw.wire(ax, [3.0, 3.0], [6.3, 2.7]); draw.wire(ax, [3.0, 3.6], [2.7, 2.7])
draw.wire(ax, [1.7, 3.0], [4.5, 4.5]); draw.dot(ax, 3.0, 4.5)
ax.text(1.55, 4.5, "in", ha="right", va="center", color=draw.HOT, fontweight="bold", fontsize=10)
draw.wire(ax, [5.2, 5.2], [4.9, 4.1]); draw.dot(ax, 5.2, 4.5); draw.wire(ax, [5.2, 7.0], [4.5, 4.5])
ax.text(7.15, 4.5, "out", ha="left", va="center", color=draw.HOT, fontweight="bold", fontsize=10)
draw.wire(ax, [7.0, 7.0], [4.5, 3.4]); draw.capacitor(ax, 7.0, 4.5, 2.6); draw.ground(ax, 7.0, 2.6)
ax.text(7.5, 3.55, "CL", fontsize=9, va="center")
draw.wire(ax, [4.0, 6.4], [8.9, 8.9]); draw.wire(ax, [5.2, 5.2], [7.7, 8.9])
ax.text(5.2, 9.1, "Vdd = 1.8 V", ha="center", fontsize=9, color=draw.HOT, fontweight="bold")
draw.ground(ax, 5.2, 1.3)
ax.text(5.55, 7.15, "M2  3u/0.18u", fontsize=8.5); ax.text(5.55, 1.9, "M1  1u/0.18u", fontsize=8.5)

ax = fig.add_subplot(gs_[1, 0]); draw.cmos_section(ax); ax.set_title("(b) the same circuit: CMOS cross-section")

ax = fig.add_subplot(gs_[0, 1])
cols = {0: "#cfd3d9", 1: "#9ecae1", 2: "#fdd0a2"}
ax.plot(vin, vout, color="#1f3b73", lw=2.2, label="Vout")
ax.plot(vin, vin, color="gray", lw=0.9, ls=":")
ax.plot([vm], [vm], "o", color="#c00", ms=8)
ax.annotate(f"Vm = {vm:.3f} V\n(Vout = Vin)", (vm, vm), (1.15, 1.25), fontsize=9, color="#c00", arrowprops=dict(arrowstyle="->", color="#c00"))
for strip, (r, label, y0) in enumerate(((rp, "PMOS", -0.30), (rn, "NMOS", -0.18))):
    start = 0
    for i in range(1, len(vin) + 1):
        if i == len(vin) or r[i] != r[start]:
            ax.axvspan(vin[start], vin[min(i, len(vin) - 1)], ymin=0.0 + strip * 0.04, ymax=0.04 + strip * 0.04, color=cols[r[start]], lw=0)
            start = i
ax.text(1.83, 0.06, "PMOS", fontsize=7.5, ha="right", va="center"); ax.text(1.83, 0.14, "NMOS", fontsize=7.5, ha="right", va="center")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=cols[0], label="cutoff"), Patch(color=cols[1], label="triode"), Patch(color=cols[2], label="saturation")],
          loc="upper right", fontsize=8, title="strip colours", title_fontsize=8)
ax.set(xlabel="Vin [V]", ylabel="Vout [V]", title="(c) voltage transfer curve (VTC) + operating regions", xlim=(0, 1.8), ylim=(0, 1.9))
ax.grid(alpha=0.25)

ax = fig.add_subplot(gs_[1, 1])
ax.semilogy(vin, np.maximum(idd, 1e-13), color="#d95f02", lw=2)
ax.set(xlabel="Vin [V]", ylabel="supply current [A]", title="(d) supply current: flows only while switching", xlim=(0, 1.8))
ax.annotate(f"peak {idd.max()*1e6:.0f} uA at Vin ≈ Vm\n(both transistors on)", (vm, idd.max()), (1.0, 3e-7), fontsize=8.5, arrowprops=dict(arrowstyle="->"))
ax.text(0.02, 0.17, f"Vin = 0 or 1.8 V: ≈ {idd[0]:.1e} A\n(only gmin = 1e-12 S)", transform=ax.transAxes, fontsize=8.5)
ax.grid(alpha=0.25, which="both")

ax = fig.add_subplot(gs_[0, 2])
ax.plot(t * 1e9, tin, color="#777", ls="--", lw=1.5, label="Vin")
ax.plot(t * 1e9, tout, color="#1f3b73", lw=2.2, label="Vout (CL = 20 fF)")
ax.set(ylabel="voltage [V]", title="(e) transient: both edges are fast", xlim=(0, 4), ylim=(-0.1, 2.0))
ax.text(0.45, 0.55, f"tpHL = {J['tphl']*1e12:.0f} ps\ntpLH = {J['tplh']*1e12:.0f} ps", fontsize=9, color="#b03a00")
ax.legend(loc="upper right", fontsize=8.5, ncol=2); ax.grid(alpha=0.25)

ax = fig.add_subplot(gs_[1, 2], sharex=ax)
ax.plot(t * 1e9, tidd * 1e3, color="#d95f02", lw=1.8)
ax.axhline(0, color="k", lw=0.6)
ax.set(xlabel="t [ns]", ylabel="supply current [mA]", title="(f) supply current during switching")
ax.text(0.03, 0.95, f"E per cycle = {J['e_cycle']*1e15:.1f} fJ\nC·Vdd² = {J['e_cv2']*1e15:.1f} fJ", transform=ax.transAxes,
        ha="left", va="top", fontsize=9)
ax.grid(alpha=0.25)

fig.suptitle("Lesson 4 - the CMOS inverter (Level 1, minispice)", fontsize=13)
fig.savefig(out / "lesson4.png", dpi=130)
(out / "lesson4.json").write_text(json.dumps(J, indent=1, default=float))

print(f"beta_n = {bn*1e3:.4f} mA/V^2, beta_p = {bp*1e3:.4f} mA/V^2")
print(f"Vm: formula {vm_ideal:.4f} V, solver {vm:.4f} V")
print(f"gain: hand -(gmn+gmp)/(gdsn+gdsp) = {gain_hand:.1f}, numeric max|dVout/dVin| = {gain_num:.1f}")
print(f"static supply current: Vin=0 {idd[0]:.2e} A, Vin=1.8 {idd[-1]:.2e} A; peak {idd.max()*1e6:.1f} uA (hand at Vm: {i0*1e6:.1f} uA)")
print(f"hand Newton at Vin={VIN_H} (start Vout=1.8): solver {J['newton_solver']:.6f}")
for r in newton:
    print(f"  it {r['it']}: Vo={r['vo']:.6f} In={r['idn']*1e6:8.3f}uA Isd={r['isd']*1e6:8.3f}uA gdsN={r['gdsn']*1e6:.2f} gdsP={r['gdsp']*1e6:.1f} -> {r['vnew']:.6f}")
print(f"tpHL {J['tphl']*1e12:.1f} ps, tpLH {J['tplh']*1e12:.1f} ps, fall {J['fall_1090']*1e12:.0f} ps, rise {J['rise_1090']*1e12:.0f} ps")
print(f"energy/cycle {J['e_cycle']*1e15:.2f} fJ vs C*Vdd^2 {J['e_cv2']*1e15:.2f} fJ, peak transient supply current {J['i_sc_tran_peak']*1e3:.3f} mA")

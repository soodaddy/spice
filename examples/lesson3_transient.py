"""Lesson 3: NMOS + Rd + load capacitor, gate pulse. How SPICE steps through time."""

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import draw
from minispice import Level1, parse, transient

out = pathlib.Path(__file__).parent / "out"
out.mkdir(exist_ok=True)

VDD, VGH, RD, CL, W, L = 1.8, 1.4, 5e3, 100e-15, 1e-6, 0.18e-6
H = 20e-12
NETLIST = f"""Lesson 3: NMOS with resistor load and load capacitor
.model nch nmos level=1 vto=0.5 kp=300u lambda=0.05
Vdd vdd 0 {VDD}
Vg g 0 PULSE(0 {VGH} 1n 0.1n 0.1n 3n 8n)
Rd vdd d 5k
CL d 0 100f
M1 d g 0 0 nch W=1u L=0.18u
.tran 20p 8n
.end
"""
model = Level1(1, dict(vto=0.5, kp=300e-6, lambda_=0.05))
ckt, an = parse(NETLIST)
tstep, tstop = an[0][1]

res = transient(ckt, tstep, tstop, method="be")
t, vd, vg = res.axis, res["v(d)"], res["v(g)"]


def cross(t, v, level, start=0.0, rising=True):
    """First time after `start` where v crosses `level` (linear interpolation)."""
    for i in range(1, len(t)):
        if t[i] < start:
            continue
        a, b = v[i - 1], v[i]
        if (a < level <= b) if rising else (a > level >= b):
            return t[i - 1] + (level - a) / (b - a) * (t[i] - t[i - 1])
    return None


print("=== Step 3a: what changes versus lesson 2 ===========================")
print("a capacitor adds a term  i_C = C * dVd/dt  to the KCL at node d:")
print("   (Vd - Vdd)/Rd  +  Id(Vd, Vg)  +  C * dVd/dt  = 0        <- differential equation")
print("SPICE cuts time into small steps h and turns d/dt into a difference (Backward Euler):")
print("   dVd/dt  ~  (Vd_new - Vd_old) / h")
print(f"   i_C = C/h * Vd_new  -  C/h * Vd_old  =  Geq*Vd_new + Ieq,    Geq = C/h,  Ieq = -Geq*Vd_old")
print(f"with C = {CL*1e15:.0f} fF and h = {H*1e12:.0f} ps:  Geq = {CL/H*1e3:.1f} mS   (compare 1/Rd = {1/RD*1e3:.1f} mS)\n")

# ---- one time step by hand ---------------------------------------------------
t_a, t_b = 1.10e-9, 1.12e-9
kb = int(round(t_b / tstep)); ka = kb - 1
assert abs(t[kb] - t_b) < 1e-15
vd_old, vg_new = vd[ka], vg[kb]
geq = CL / H
print(f"=== Step 3b: ONE time step by hand, t = {t[ka]*1e9:.2f} ns -> {t[kb]*1e9:.2f} ns ==============")
print(f"known: Vd_old = {vd_old:.6f} V (from the previous step),  Vg(new) = {vg_new:.2f} V,  Geq = {geq*1e3:.1f} mS")
print("unknown: Vd_new. Same Newton as lesson 2, plus the capacitor's Geq and Ieq:")
print("   Vd = ( Vdd/Rd - Ieq_fet + Geq*Vd_old ) / ( 1/Rd + gds + Geq )\n")
print("iter |  Vd0 [V] | Id0 [uA] | gds [uS] | Ieq_fet [uA] | new Vd [V]")
v0 = vd_old
for it in range(1, 9):
    i0, gds, *_ = model.evaluate(v0, vg_new, 0.0, 0.0, W, L)
    ieq = i0 - gds * v0
    v1 = (VDD / RD - ieq + geq * vd_old) / (1 / RD + gds + geq)
    print(f"{it:4d} | {v0:8.5f} | {i0*1e6:8.2f} | {gds*1e6:8.1f} | {ieq*1e6:12.2f} | {v1:10.6f}")
    if abs(v1 - v0) < 1e-9:
        break
    v0 = v1
print(f"\nhand step : Vd_new = {v1:.6f} V")
print(f"minispice : Vd_new = {vd[kb]:.6f} V   (difference {abs(v1 - vd[kb]):.1e} V)")
i_c = geq * (v1 - vd_old)
i_r = (VDD - v1) / RD
i_d = model.evaluate(v1, vg_new, 0, 0, W, L)[0]
print(f"\ncurrents at the new point:  resistor {i_r*1e6:.1f} uA = transistor {i_d*1e6:.1f} uA + capacitor {i_c*1e6:.1f} uA"
      f"  (sum check {abs(i_r - i_d - i_c)*1e9:.2f} nA)")

# ---- results --------------------------------------------------------------
vlow = vd[np.searchsorted(t, 4.0e-9)]
swing = VDD - vlow
l90, l10, l50 = vlow + 0.9 * swing, vlow + 0.1 * swing, vlow + 0.5 * swing
t_f90, t_f10 = cross(t, vd, l90, 1e-9, rising=False), cross(t, vd, l10, 1e-9, rising=False)
t_r10, t_r90 = cross(t, vd, l10, 4.1e-9, rising=True), cross(t, vd, l90, 4.1e-9, rising=True)
t_g_up = cross(t, vg, VGH / 2, 0.0, rising=True)
t_g_dn = cross(t, vg, VGH / 2, 4.0e-9, rising=False)
t_d_dn = cross(t, vd, l50, 1e-9, rising=False)
t_d_up = cross(t, vd, l50, 4.1e-9, rising=True)
print("\n=== Step 3c: results ================================================")
print(f"Vd high = {VDD:.3f} V,  Vd low = {vlow:.4f} V   (low = the DC answer of lesson 2 for Vg = 1.4 V: 0.2372 V)")
print(f"fall time 90->10 % : {(t_f10 - t_f90)*1e12:7.0f} ps   (the transistor pulls the node down)")
print(f"rise time 10->90 % : {(t_r90 - t_r10)*1e12:7.0f} ps   (only Rd charges CL)")
print(f"   expected for a plain RC: 2.2*Rd*CL = {2.2*RD*CL*1e12:.0f} ps")
print(f"delay Vg 50% -> Vd 50%:  falling {(t_d_dn - t_g_up)*1e12:.0f} ps,  rising {(t_d_up - t_g_dn)*1e12:.0f} ps")

# accuracy vs. method / step
ref = transient(parse(NETLIST)[0], 1e-12, tstop, method="trap")
vd_ref = np.interp(t, ref.axis, ref["v(d)"])
tr20 = transient(parse(NETLIST)[0], tstep, tstop, method="trap")
print("\nmax |Vd error| against a 1 ps trapezoidal reference:")
print(f"  Backward Euler, h = 20 ps : {np.max(np.abs(vd - vd_ref))*1e3:6.1f} mV")
print(f"  trapezoidal,    h = 20 ps : {np.max(np.abs(tr20['v(d)'] - vd_ref))*1e3:6.1f} mV")

# branch currents (all from the node-d KCL)
i_r_t = (VDD - vd) / RD
i_d_t = np.array([model.evaluate(v, g, 0.0, 0.0, W, L)[0] for v, g in zip(vd, vg)])
i_c_t = np.zeros_like(vd)
i_c_t[1:] = CL * (vd[1:] - vd[:-1]) / tstep      # Backward-Euler capacitor current
print(f"\nKCL check over all steps: max |iR - iD - iC| = {np.max(np.abs(i_r_t - i_d_t - i_c_t))*1e9:.3f} nA")

# ---- figure -----------------------------------------------------------------
fig = plt.figure(figsize=(15, 8), constrained_layout=True)
gs_ = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.9], height_ratios=[1.0, 1.0])

ax = fig.add_subplot(gs_[0, 0]); ax.set_xlim(0, 9); ax.set_ylim(0, 8); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(a) circuit")
d, s = draw.nmos(ax, 3.6, 3.5)
ax.text(3.9, 0.9, "M1   W/L = 1u/0.18u", fontsize=8.5)
draw.vsource(ax, 1.4, 3.5, "Vg: pulse\n0 → 1.4 V"); draw.wire(ax, [1.85, 3.6], [3.5, 3.5]); draw.wire(ax, [1.4, 1.4], [3.05, 2.0])
draw.ground(ax, 1.4, 2.0)
draw.resistor(ax, d[0], d[1], 7.2)
ax.text(d[0] + 0.45, 6.05, "Rd = 5 kΩ", fontsize=8.5, va="center")
draw.wire(ax, [4.2, 6.2], [7.2, 7.2]); ax.text(d[0], 7.5, "Vdd = 1.8 V", fontsize=9, ha="center", color=draw.HOT, fontweight="bold")
draw.dot(ax, d[0], d[1]); ax.text(d[0] - 0.2, d[1] + 0.3, "d", color=draw.HOT, fontweight="bold", fontsize=10, ha="right")
draw.wire(ax, [d[0], 7.4], [d[1], d[1]])
draw.capacitor(ax, 7.4, d[1], 2.4); ax.text(7.85, 3.7, "CL\n100 fF", fontsize=8.5, va="center")
draw.ground(ax, 7.4, 2.4); draw.ground(ax, s[0], s[1])

ax = fig.add_subplot(gs_[1, 0]); ax.set_xlim(0, 9); ax.set_ylim(-1.0, 7.0); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(b) the capacitor in one time step (Backward Euler)")
draw.wire(ax, [1.4, 1.4], [5.8, 5.4]); draw.capacitor(ax, 1.4, 5.4, 2.2); draw.ground(ax, 1.4, 2.2)
ax.text(1.85, 3.8, "C", fontsize=10, va="center", color=draw.HOT, fontweight="bold")
ax.annotate("", xy=(3.9, 3.8), xytext=(2.6, 3.8), arrowprops=dict(arrowstyle="-|>", lw=2, color="#444"))
ax.text(3.25, 4.15, "every step", ha="center", fontsize=8.5, color="#444")
draw.wire(ax, [4.8, 4.8], [5.8, 5.4]); draw.wire(ax, [4.8, 7.4], [5.4, 5.4])
draw.resistor(ax, 4.8, 2.2, 5.4); ax.text(5.15, 3.8, "Geq", fontsize=9, va="center", color=draw.HOT, fontweight="bold")
draw.wire(ax, [7.4, 7.4], [5.4, 4.3]); draw.isource(ax, 7.4, 3.8, "Ieq", r=0.5, side="right"); draw.wire(ax, [7.4, 7.4], [3.3, 2.2])
draw.wire(ax, [4.8, 7.4], [2.2, 2.2]); draw.ground(ax, 6.1, 2.2)
ax.text(4.5, 1.0, "i = C·(v − v_prev)/h  =  Geq·v + Ieq", ha="center", fontsize=9)
ax.text(4.5, 0.2, "Geq = C/h,   Ieq = −Geq·v_prev", ha="center", fontsize=9)
ax.text(4.5, -0.6, f"C = 100 fF,  h = 20 ps  →  Geq = {geq*1e3:.0f} mS", ha="center", fontsize=8.5, color="#555")

axv = fig.add_subplot(gs_[0, 1])
axv.plot(t * 1e9, vg, color="#777", lw=1.6, ls="--", label="Vg (gate pulse)")
axv.plot(t * 1e9, vd, color="#1f3b73", lw=2.2, label="Vd (output)")
axv.axhline(vlow, color="#1f3b73", lw=0.8, ls=":")
axv.text(7.9, vlow + 0.04, f"{vlow:.3f} V (lesson 2's DC answer)", fontsize=8, ha="right", color="#1f3b73")
axv.plot([t[kb] * 1e9], [vd[kb]], "o", color="#d95f02", ms=9, zorder=5)
axv.annotate("the step computed by hand\n(1.10 → 1.12 ns)", (t[kb] * 1e9, vd[kb]), (1.6, 1.05), fontsize=8.5,
             color="#d95f02", arrowprops=dict(arrowstyle="->", color="#d95f02"))
axv.annotate("", xy=(t_f10 * 1e9, l10), xytext=(t_f90 * 1e9, l90), arrowprops=dict(arrowstyle="<->", color="#b03a00"))
axv.text(2.0, 1.62, f"fall 90→10%: {(t_f10-t_f90)*1e12:.0f} ps\\n(transistor pulls down)".replace("\\n", "\n"),
         fontsize=8.5, color="#b03a00")
axv.annotate("", xy=(t_r90 * 1e9, l90 - 0.0), xytext=(t_r10 * 1e9, l10), arrowprops=dict(arrowstyle="<->", color="#b03a00"))
axv.text(5.35, 0.75, f"rise 10→90%: {(t_r90-t_r10)*1e12:.0f} ps\n≈ 2.2·Rd·CL = {2.2*RD*CL*1e12:.0f} ps\n(only Rd charges CL)",
         fontsize=8.5, color="#b03a00")
axv.set(ylabel="voltage [V]", title="(c) output voltage follows the gate - falling is fast, rising is slow", xlim=(0, 8), ylim=(-0.1, 2.0))
axv.legend(loc="upper right", fontsize=8.5, ncol=2); axv.grid(alpha=0.25)

axi = fig.add_subplot(gs_[1, 1], sharex=axv)
axi.plot(t * 1e9, i_r_t * 1e3, color="#1b9e77", lw=1.8, label="iR  through Rd (from Vdd)")
axi.plot(t * 1e9, i_d_t * 1e3, color="#d95f02", lw=1.8, label="iD  through the transistor")
axi.plot(t * 1e9, i_c_t * 1e3, color="#7570b3", lw=1.8, label="iC  into CL  (= C·dVd/dt)")
axi.axhline(0, color="k", lw=0.6)
axi.set(xlabel="t [ns]", ylabel="current [mA]", title="(d) where the current goes:  iR = iD + iC  at every instant")
axi.legend(loc="lower right", fontsize=8.5); axi.grid(alpha=0.25)
axi.annotate("transistor turns on: iD jumps,\nCL discharges (iC < 0)", (1.12, -0.35), (1.7, -0.62), fontsize=8.5, color="#444",
             arrowprops=dict(arrowstyle="->", color="#444"))
axi.annotate("transistor off: iD = 0,\nRd charges CL (iC = iR)", (4.6, 0.12), (5.3, 0.55), fontsize=8.5, color="#444",
             arrowprops=dict(arrowstyle="->", color="#444"))

fig.suptitle("Lesson 3 - an NMOS with a load capacitor: stepping through time (transient)", fontsize=13)
fig.savefig(out / "lesson3.png", dpi=130)
print("\nsaved", out / "lesson3.png")

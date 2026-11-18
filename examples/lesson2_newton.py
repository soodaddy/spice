"""Lesson 2: NMOS + load resistor. How SPICE finds the operating point (Newton iteration)."""

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

import draw
from minispice import Level1, parse, solve_op

out = pathlib.Path(__file__).parent / "out"
out.mkdir(exist_ok=True)

VDD, VG, RD, W, L = 1.8, 1.4, 5e3, 1e-6, 0.18e-6
NETLIST = f"""Lesson 2: NMOS with resistor load
.model nch nmos level=1 vto=0.5 kp=300u lambda=0.05
Vdd vdd 0 {VDD}
Vg g 0 {VG}
Rd vdd d 5k
M1 d g 0 0 nch W=1u L=0.18u
.op
.end
"""
model = Level1(1, dict(vto=0.5, kp=300e-6, lambda_=0.05))


def fet(vd):
    """(Id, gds) of the transistor at Vgs = VG, Vs = 0."""
    i, gd, _, _, _ = model.evaluate(vd, VG, 0.0, 0.0, W, L)
    return i, gd


# ---- the answer from the real solver (to check our hand iteration against) ----
ckt, _ = parse(NETLIST)
names = ckt.node_names()
log = []
x = solve_op(ckt, trace=lambda it, xb, xa, damped: log.append((it, xb.copy(), xa.copy(), damped)))
vd_solver = x[names.index("d")]

print("=== Step 2a: the equation ===========================================")
print("Kirchhoff current law at node d:  (Vdd - Vd)/Rd = Id(Vd)")
print(f"  left : current the resistor delivers   (a straight line in Vd)")
print(f"  right: current the transistor can pass (the curved Level-1 formula)")
print("A line and a curve: no neat formula -> iterate.\n")

print("=== Step 2b: Newton iteration by hand (Vg fixed at 1.4 V, start Vd = 0) ==")
print("each step:  1) at the guess Vd0 get Id0 and slope gds from the model")
print("            2) replace the transistor by  Id = gds*Vd + Ieq,  Ieq = Id0 - gds*Vd0")
print("            3) solve the now-linear circuit:  Vd = (Vdd/Rd - Ieq) / (1/Rd + gds)\n")
print("step |  Vd0 [V] | Id0 [uA] | gds [uS] | Ieq [uA] | new Vd [V] | KCL error at Vd0 [uA]")
rows = []
vd0 = 0.0
for k in range(1, 9):
    id0, gds = fet(vd0)
    ieq = id0 - gds * vd0
    vd1 = (VDD / RD - ieq) / (1 / RD + gds)
    kcl = ((VDD - vd0) / RD - id0) * 1e6
    rows.append((k, vd0, id0, gds, ieq, vd1))
    print(f"{k:4d} | {vd0:8.5f} | {id0*1e6:8.2f} | {gds*1e6:8.1f} | {ieq*1e6:8.2f} | {vd1:10.6f} | {kcl:12.4f}")
    if abs(vd1 - vd0) < 1e-9:
        break
    vd0 = vd1
vd_star = rows[-1][5]
id_star = fet(vd_star)[0]
print(f"\nconverged: Vd* = {vd_star:.6f} V")
print(f"  resistor current (Vdd-Vd)/Rd = {(VDD-vd_star)/RD*1e6:.4f} uA")
print(f"  transistor current Id(Vd)    = {id_star*1e6:.4f} uA   -> equal, KCL satisfied")
print(f"  region: Vds = {vd_star:.3f} V < Vov = {VG-0.5:.2f} V  -> triode")

errs = [abs(r[1] - vd_star) for r in rows] + [abs(vd_star - vd_star)]
print("\nerror |Vd - Vd*| per step and  e(k+1)/e(k)^2  (a constant ratio means 'squares each step'):")
for k in range(len(rows) - 2):
    print(f"  step {k+1}: e = {errs[k]:.3e}   e_next/e^2 = {errs[k+1] / errs[k]**2:.2f}")

print("\n=== Step 2c: same answer from the real solver? ======================")
print(f"minispice solve_op: Vd = {vd_solver:.6f} V   | hand Newton: Vd = {vd_star:.6f} V   | difference {abs(vd_solver - vd_star):.1e} V")

print("\n=== Step 2d (reference): the real solver's own iteration log ========")
print("It solves ALL unknowns at once, including bringing the sources up from 0 V, and it limits")
print("every node-voltage step to 1 V. So its first iterations differ from our 1-variable picture.")
print("iter | Vd before -> after | Vg before -> after | step limited")
for it, xb, xa, damped in log:
    gi, di = names.index("g"), names.index("d")
    print(f"{it:4d} | {xb[di]:8.4f} -> {xa[di]:7.4f} | {xb[gi]:8.4f} -> {xa[gi]:7.4f} | {'yes' if damped else 'no'}")

# ---- figure -----------------------------------------------------------------
fig = plt.figure(figsize=(15, 7.4), constrained_layout=True)
gs_ = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.15, 0.95], height_ratios=[1.0, 1.0])

# (a) the circuit
ax = fig.add_subplot(gs_[0, 0]); ax.set_xlim(0, 8); ax.set_ylim(0, 8); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(a) circuit")
d, s = draw.nmos(ax, 3.6, 3.5)
ax.text(3.9, 1.0, "M1   W/L = 1u/0.18u", fontsize=8.5)
draw.vsource(ax, 1.4, 3.5, "Vg = 1.4 V"); draw.wire(ax, [1.85, 3.6], [3.5, 3.5]); draw.wire(ax, [1.4, 1.4], [3.05, 2.0])
draw.ground(ax, 1.4, 2.0)
draw.resistor(ax, d[0], d[1], 7.2)
ax.text(d[0] + 0.45, 6.05, "Rd = 5 kΩ", fontsize=8.5, va="center")
draw.wire(ax, [4.2, 6.2], [7.2, 7.2]); ax.text(d[0], 7.5, "Vdd = 1.8 V", fontsize=9, ha="center", color=draw.HOT, fontweight="bold")
draw.dot(ax, d[0], d[1]); ax.text(d[0] + 0.3, d[1] + 0.05, "d  (Vd = ?)", color=draw.HOT, fontweight="bold", fontsize=9, va="top")
draw.ground(ax, s[0], s[1])

# (b) one Newton step: the transistor becomes a resistor + a current source
ax = fig.add_subplot(gs_[1, 0]); ax.set_xlim(0, 8); ax.set_ylim(-1.2, 8); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(b) one Newton step: transistor → gds ∥ Ieq")
draw.resistor(ax, 2.4, 4.6, 7.0); ax.text(2.7, 5.8, "Rd", fontsize=9, va="center")
draw.wire(ax, [1.7, 3.1], [7.0, 7.0]); ax.text(2.4, 7.25, "Vdd", ha="center", fontsize=9, color=draw.HOT, fontweight="bold")
draw.wire(ax, [2.4, 6.6], [4.6, 4.6]); draw.dot(ax, 2.4, 4.6)
ax.text(2.1, 4.6, "d", ha="right", va="center", fontsize=10, color=draw.HOT, fontweight="bold")
draw.resistor(ax, 4.6, 1.9, 4.6); ax.text(4.3, 3.25, "gds", ha="right", va="center", fontsize=9, color=draw.HOT, fontweight="bold")
draw.wire(ax, [6.6, 6.6], [4.6, 3.75]); draw.isource(ax, 6.6, 3.25, "Ieq", r=0.5); draw.wire(ax, [6.6, 6.6], [2.75, 1.9])
draw.wire(ax, [4.6, 6.6], [1.9, 1.9]); draw.dot(ax, 4.6, 4.6); draw.ground(ax, 5.6, 1.9)
ax.add_patch(Rectangle((3.9, 1.35), 3.4, 4.0, fc="none", ec="#888", ls="--", lw=1.1))
ax.text(5.6, 5.55, "linearised transistor", ha="center", fontsize=8.5, color="#555")
ax.text(4.0, 0.3, "Id ≈ gds·Vd + Ieq,    Ieq = Id0 − gds·Vd0", ha="center", fontsize=9)
ax.text(4.0, -0.5, "now a linear circuit → solve directly", ha="center", fontsize=8.5, color="#555")

# (c) Newton steps on the I-V plane
ax = fig.add_subplot(gs_[:, 1])
pal = ["#d95f02", "#7570b3", "#1b9e77"]


def draw_iv(ax, xmax, labels=True):
    vd = np.linspace(0, xmax, 300)
    ax.plot(vd, [fet(v)[0] * 1e3 for v in vd], color="#1f3b73", lw=2.2,
            label="transistor  Id(Vd)  (Vg = 1.4 V)" if labels else None)
    ax.plot(vd, (VDD - vd) / RD * 1e3, color="#555", lw=2.2, label="resistor  (Vdd − Vd)/Rd" if labels else None)
    for c, (k, vd0, id0, gds, ieq, vd1) in zip(pal, rows[:3]):
        xs = np.array([0, xmax])
        ax.plot(xs, (gds * xs + ieq) * 1e3, "--", color=c, lw=1.3,
                label=f"step {k}: tangent at Vd = {vd0:.4f} V" if labels else None)
        ax.plot([vd0], [id0 * 1e3], "o", color=c, ms=8, zorder=4)
        y_load = (VDD - vd1) / RD * 1e3
        ax.plot([vd1], [y_load], "x", color=c, ms=10, mew=2.4, zorder=4)
        ax.annotate("", xy=(vd1, fet(vd1)[0] * 1e3), xytext=(vd1, y_load),
                    arrowprops=dict(arrowstyle="->", color=c, lw=1.2, ls=":"))
    ax.plot([vd_star], [id_star * 1e3], "*", color="#c00", ms=18 if labels else 14, zorder=5,
            label=f"solution  Vd* = {vd_star:.4f} V,  Id = {id_star*1e6:.0f} uA" if labels else None)


draw_iv(ax, 0.32)
ax.annotate("start: guess Vd = 0", (0, 0), (0.05, 0.035), fontsize=8.5, color=pal[0],
            arrowprops=dict(arrowstyle="->", color=pal[0]))
ax.annotate("×  tangent meets the load line = next guess\n●  next guess, read on the curve", (rows[0][5], (VDD - rows[0][5]) / RD * 1e3),
            (0.015, 0.40), fontsize=8.5, color="#444", arrowprops=dict(arrowstyle="->", color="#444"))
ax.set(xlabel="Vd [V]", ylabel="current [mA]", xlim=(0, 0.32), ylim=(0, 0.43),
       title="(c) each step: tangent → crossing with the load line")
ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, frameon=False)
ax.grid(alpha=0.25)
axin = ax.inset_axes([0.55, 0.07, 0.42, 0.36])
draw_iv(axin, 0.32, labels=False)
axin.set(xlim=(0.205, 0.245), ylim=(0.275, 0.325))
axin.tick_params(labelsize=7)
axin.set_title("zoom near the solution", fontsize=8)
axin.grid(alpha=0.25)
ax.indicate_inset_zoom(axin, edgecolor="gray")

# (d) convergence
ax = fig.add_subplot(gs_[:, 2])
n_show = next(i for i, e in enumerate(errs) if e < 1e-14)  # stop at machine precision
ks = list(range(n_show + 1))
vds = [0.0] + [r[5] for r in rows]
err = np.maximum(np.abs(np.array(vds) - vd_star), 1e-16)[: n_show + 1]
ax.semilogy(ks, err, "o-", color="#1f3b73")
for k, e, v in zip(ks, err, vds):
    ax.annotate(f"Vd = {v:.5f}", (k, e), (8, 4), textcoords="offset points", fontsize=8)
ax.set(xlabel="Newton step (0 = initial guess)", ylabel="|Vd − Vd*|  [V]", xticks=ks, xlim=(-0.3, n_show + 1.6),
       title="(d) the error vs. step", ylim=(1e-16, 2))
ax.grid(alpha=0.25, which="both")
chain = "  →  ".join(f"{e:.0e}" for e in err[:-1]) + "  →  ~1e-15"
ax.text(0.97, 0.97, "error roughly squares each step\n" + chain.replace("  →  ", " → "), transform=ax.transAxes,
        ha="right", va="top", fontsize=8.5)

fig.suptitle("Lesson 2 - how SPICE solves an NMOS with a load resistor (Newton iteration)", fontsize=13)
fig.savefig(out / "lesson2.png", dpi=130)
print("\nsaved", out / "lesson2.png")

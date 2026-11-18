"""Lesson 1: one planar NMOS. Hand calculation -> model code -> SPICE .op -> I-V curves."""

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import draw
from minispice import Level1, dc_sweep, op, parse

out = pathlib.Path(__file__).parent / "out"
out.mkdir(exist_ok=True)

NETLIST = """Lesson 1: single NMOS
.model nch nmos level=1 vto=0.5 kp=300u lambda=0.05
Vgs g 0 1.0
Vds d 0 1.8
M1 d g 0 0 nch W=1u L=0.18u
.op
.end
"""
VTO, KP, LAM, W, L = 0.5, 300e-6, 0.05, 1e-6, 0.18e-6
beta = KP * W / L

print("=== Step 1a: model parameters ===")
print(f"beta = KP*W/L = {KP*1e6:.0f}u * {W*1e6:.0f}u/{L*1e6:.2f}u = {beta*1e3:.4f} mA/V^2")
print(f"Vth  = VTO = {VTO} V   (Vsb = 0, so no body effect)\n")

model = Level1(1, dict(vto=VTO, kp=KP, lambda_=LAM))
print("=== Step 1b: hand calculation vs. model code ===")
print(f"{'bias':>22s} | {'region':>10s} | {'hand [uA]':>10s} | {'code [uA]':>10s}")
cases = [(1.0, 1.8), (1.0, 0.2), (1.8, 1.8), (0.4, 1.8)]
for vgs, vds in cases:
    vov = vgs - VTO
    if vov <= 0:
        region, hand = "cutoff", 0.0
    elif vds < vov:
        region, hand = "triode", beta * (vov - vds / 2) * vds * (1 + LAM * vds)
    else:
        region, hand = "saturation", 0.5 * beta * vov**2 * (1 + LAM * vds)
    code = model.evaluate(vds, vgs, 0.0, 0.0, W, L)[0]
    print(f"Vgs={vgs:.1f} V, Vds={vds:.1f} V | {region:>10s} | {hand*1e6:10.3f} | {code*1e6:10.3f}")

print("\n=== Step 1c: the same bias point through the SPICE solver (.op) ===")
ckt, _ = parse(NETLIST)
r = op(ckt)
print(f"v(d) = {r['v(d)'][0]:.4f} V   v(g) = {r['v(g)'][0]:.4f} V")
print(f"i(vds) = {r['i(vds)'][0]*1e6:.3f} uA   -> Id = -i(vds) = {-r['i(vds)'][0]*1e6:.3f} uA")

# conductances = slopes the solver will use in lesson 2
i0, gd, gg, gs, gb = model.evaluate(1.8, 1.0, 0.0, 0.0, W, L)
print("\n=== Step 1d: the slopes (small-signal conductances) at Vgs=1.0, Vds=1.8 ===")
print(f"gm  = dId/dVg = {gg*1e6:8.2f} uS   (= beta*Vov*(1+lam*Vds))")
print(f"gds = dId/dVd = {gd*1e6:8.2f} uS   (= lam * Id0, from channel-length modulation)")
print(f"dId/dVs       = {gs*1e6:8.2f} uS   (= -(gm+gds+gmb), so all four sum to 0)")

# ---- figure ----------------------------------------------------------------
fig = plt.figure(figsize=(15, 7.4), constrained_layout=True)
gs_ = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.15, 0.95], height_ratios=[1.0, 1.15])

ax = fig.add_subplot(gs_[0, 0]); ax.set_xlim(0, 8); ax.set_ylim(0, 8); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(a) circuit symbol and test bench (.op / .dc)")
d, s = draw.nmos(ax, 3.6, 4.0)                       # d = (5.2, 5.4), s = (5.2, 2.6)
ax.text(3.6, 6.7, "M1   W/L = 1u/0.18u", fontsize=8.5)
# gate: Vgs source from g to ground
draw.vsource(ax, 1.4, 4.0, "Vgs"); draw.wire(ax, [1.85, 3.6], [4.0, 4.0]); draw.wire(ax, [1.4, 1.4], [3.55, 2.2])
draw.ground(ax, 1.4, 2.2)
# drain: Vds source (+ on top) from drain to ground
draw.vsource(ax, 6.8, 3.9, "Vds", side="right")
draw.wire(ax, [6.8, 6.8], [4.35, 5.4]); draw.wire(ax, [6.8, d[0]], [5.4, 5.4])
draw.wire(ax, [6.8, 6.8], [3.45, 1.4]); draw.wire(ax, [s[0], 6.8], [1.4, 1.4])
draw.wire(ax, [s[0], s[0]], [s[1], 1.4]); draw.ground(ax, s[0], 1.4)
draw.dot(ax, d[0], 5.4); draw.dot(ax, s[0], 1.4)
ax.text(d[0] - 0.15, 5.65, "d", color=draw.HOT, fontweight="bold", ha="right")
ax.text(2.0, 4.15, "g", color=draw.HOT, fontweight="bold")
ax.text(s[0] - 0.15, 1.9, "s = b = 0 V", color=draw.HOT, fontweight="bold", fontsize=8.5, ha="right")

ax = fig.add_subplot(gs_[1, 0])
draw.planar_nmos_section(ax)
ax.set_title("(b) the same device: cross-section")

ax = fig.add_subplot(gs_[:, 1])
vds = np.arange(0, 1.8001, 0.01)
pal = plt.cm.viridis(np.linspace(0.1, 0.85, 5))
ckt, _ = parse(NETLIST)
vgs_src = ckt.element("vgs")
for color, vgs in zip(pal, (0.6, 0.8, 1.0, 1.2, 1.4)):
    vgs_src.dc = vgs
    rr = dc_sweep(ckt, "vds", 0.0, 1.8, 0.01)
    ax.plot(rr.axis, -rr["i(vds)"] * 1e3, color=color, label=f"Vgs = {vgs:.1f} V")
    vov = vgs - VTO
    ax.plot(vov, 0.5 * beta * vov**2 * (1 + LAM * vov) * 1e3, "o", color=color, ms=4, mfc="white")
vv = np.linspace(0, 0.9, 100)
ax.plot(vv, 0.5 * beta * vv**2 * (1 + LAM * vv) * 1e3, "k--", lw=1, label="Vds = Vgs − Vth")
vgs, vds_ = 1.0, 1.8
ax.plot([1.8], [model.evaluate(1.8, 1.0, 0, 0, W, L)[0] * 1e3], "s", color="#b03a00", ms=7)
ax.annotate("saturation\nId = 227 uA", (1.8, 0.2271), (1.15, 0.30), color="#b03a00", fontsize=8.5,
            arrowprops=dict(arrowstyle="->", color="#b03a00"))
ax.plot([0.2], [model.evaluate(0.2, 1.0, 0, 0, W, L)[0] * 1e3], "s", color="#b03a00", ms=7)
ax.annotate("triode\n135 uA", (0.2, 0.1347), (0.8, 0.10), color="#b03a00", fontsize=8.5,
            arrowprops=dict(arrowstyle="->", color="#b03a00"))
ax.set(xlabel="Vds [V]", ylabel="Id [mA]", title="(c) output characteristics (.dc Vds sweep)")
ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, frameon=False); ax.grid(alpha=0.25)

ax = fig.add_subplot(gs_[:, 2])
vg = np.linspace(0, 1.8, 400)
idv = np.array([model.evaluate(1.8, v, 0, 0, W, L)[0] for v in vg])
ax.plot(vg, np.sqrt(idv * 1e3), color="#1f3b73", lw=1.8)
ax.axvline(VTO, color="gray", ls=":"); ax.text(VTO - 0.03, 0.05, "Vth = 0.5 V", color="gray", fontsize=8.5, ha="right")
ax.set(xlabel="Vgs [V]", ylabel=r"$\sqrt{I_d}$  [$\sqrt{mA}$]", title="(d) Id-Vgs at Vds = 1.8 V (sqrt scale)")
ax.text(0.03, 0.97, "Level 1: Id ~ (Vgs-Vth)^2\nsqrt(Id) is a straight line;\nits x-intercept is Vth",
        transform=ax.transAxes, fontsize=8.5, va="top", bbox=dict(fc="white", ec="none", pad=2))
ax.grid(alpha=0.25)

fig.suptitle("Lesson 1 - a single planar NMOS (Level 1, minispice)", fontsize=13)
fig.savefig(out / "lesson1.png", dpi=130)
print("\nsaved", out / "lesson1.png")

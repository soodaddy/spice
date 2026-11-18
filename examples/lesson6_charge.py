"""Lesson 6: channel charge model - the MOSFET's own capacitances (Qg, Qd, Qs) and what they do to delay."""

import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import draw
from minispice import EKV, Circuit, Pulse, parse, transient

out = pathlib.Path(__file__).parent / "out"
out.mkdir(exist_ok=True)

D, G, S, B = range(4)
COX = 8.63e-3                        # F/m^2   (eps_ox / tox, tox = 4 nm)
W, L, WP = 1e-6, 0.18e-6, 3e-6
CGN, CGP = COX * W * L, COX * WP * L
VT0 = 0.5
n1 = EKV(1, dict(vto=VT0, kp=300e-6, n=1.0, cox=COX))      # n = 1: textbook values
n13 = EKV(1, dict(vto=VT0, kp=300e-6, n=1.3, cox=COX))
J = dict(cox=COX, cgn=CGN, cgp=CGP)


def cmat(m, vd, vg, vs, vb=0.0, w=W):
    q, c = m.charge_jac(vd, vg, vs, vb, w, L)
    return q, c / (COX * w * L)


# ---- 1. hand calculation vs. model ---------------------------------------------------
vov = 1.8 - VT0
q = np.array(n1.charges(1.8, 1.8, 0.0, 0.0, W, L))
qd, qg, qs, qb = q
hand_qi = (2 / 3) * CGN * vov
J["hand"] = dict(vov=vov, qi_hand=hand_qi, qg=qg, qd=qd, qs=qs, qd_hand=-0.4 * hand_qi, qs_hand=-0.6 * hand_qi,
                 split_d=-qd / qg, split_s=-qs / qg)

# ---- 2. capacitances vs Vds at Vgs = 1.8 V (n = 1) ---------------------------------------------
vds = np.linspace(0, 1.8, 181)
cv = np.array([[(lambda c: (c[G, G], -c[G, S], -c[G, D], -c[D, G], -c[S, G]))(cmat(n1, v, 1.8, 0.0)[1])] for v in vds])[:, 0, :]
J["cap_vds0"] = dict(cgg=cv[0, 0], cgs=cv[0, 1], cgd=cv[0, 2])
J["cap_sat"] = dict(cgg=cv[-1, 0], cgs=cv[-1, 1], cgd=cv[-1, 2], cdg=-cv[-1, 3], csg=-cv[-1, 4])   # dQd/dVg, dQs/dVg

# ---- 3. C-V: Cgg vs Vgs for Vds = 0 and 1.8 (n = 1.3) -------------------------------------------
vg = np.linspace(0, 1.8, 361)
cgg0 = np.array([cmat(n13, 0.0, v, 0.0)[1][G, G] for v in vg])
cgg1 = np.array([cmat(n13, 1.8, v, 0.0)[1][G, G] for v in vg])
J["cgg_vs_vgs"] = dict(at_1v8_vds0=cgg0[-1], at_1v8_sat=cgg1[-1], at_0v3_sat=float(np.interp(0.3, vg, cgg1)),
                       at_0v5_sat=float(np.interp(0.5, vg, cgg1)))
qv = np.array([n13.charges(1.8, v, 0.0, 0.0, W, L) for v in vg]) / CGN    # columns d, g, s, b (units of CG*V)

# ---- 4. charge conservation check: CMOS input, ideal source -------------------------------------
nm = EKV(1, dict(vto=0.5, kp=300e-6, n=1.3, cox=COX))
pm = EKV(-1, dict(vto=-0.5, kp=100e-6, n=1.3, cox=COX))
c = Circuit()
c.add_vsource("vdd", "vdd", "0", 1.8)
c.add_vsource("vin", "in", "0", 0.0, Pulse(0, 1.8, 0.1e-9, 0.2e-9, 0.2e-9, 1.0))
c.add_mosfet("mn", "out", "in", "0", "0", nm, w=W, l=L)
c.add_mosfet("mp", "out", "in", "vdd", "vdd", pm, w=WP, l=L)
c.add_capacitor("cl", "out", "0", 5e-15)
r = transient(c, 2e-12, 0.8e-9)
delivered = np.trapezoid(-r["i(vin)"], r.axis)
qgn = lambda k: nm.charges(r["v(out)"][k], r["v(in)"][k], 0.0, 0.0, W, L)[G]
qgp = lambda k: pm.charges(r["v(out)"][k], r["v(in)"][k], 1.8, 1.8, WP, L)[G]
J["conservation"] = dict(delivered=delivered, dq_n=qgn(-1) - qgn(0), dq_p=qgp(-1) - qgp(0))
J["conservation"]["expected"] = J["conservation"]["dq_n"] + J["conservation"]["dq_p"]

# ---- 5. delay effect: FO1 inverter chain and ring oscillator ------------------------------------------
def models(cox):
    return (f"level=ekv vto=0.5 kp=300u n=1.3 lambda=0.05 cgso=3e-10 cgdo=3e-10 cox={cox}",
            f"level=ekv vto=-0.5 kp=100u n=1.3 lambda=0.05 cgso=3e-10 cgdo=3e-10 cox={cox}")


def fo1(cox):
    m, mp = models(cox)
    return parse(f"""fo1
.model nch nmos {m}
.model pch pmos {mp}
Vdd vdd 0 1.8
Vin in 0 PULSE(0 1.8 50p 20p 20p 300p 700p)
M1 a in 0 0 nch W=1u L=0.18u
M2 a in vdd vdd pch W=3u L=0.18u
M3 b a 0 0 nch W=1u L=0.18u
M4 b a vdd vdd pch W=3u L=0.18u
.end
""")[0]


def cross(t, v, lvl, rising, t0=0.0):
    for i in range(1, len(t)):
        if t[i] >= t0 and ((v[i - 1] < lvl <= v[i]) if rising else (v[i - 1] > lvl >= v[i])):
            return t[i - 1] + (lvl - v[i - 1]) / (v[i] - v[i - 1]) * (t[i] - t[i - 1])


fo = {}
for cox in (0, COX):
    rr = transient(fo1(cox), 0.5e-12, 700e-12)
    t, a, vi = rr.axis, rr["v(a)"], rr["v(in)"]
    t_in_r, t_in_f = cross(t, vi, 0.9, True), cross(t, vi, 0.9, False, 300e-12)
    fo[cox] = dict(tphl=cross(t, a, 0.9, False) - t_in_r, tplh=cross(t, a, 0.9, True, 300e-12) - t_in_f)
J["fo1"] = dict(off=fo[0], on=fo[COX])


def ring(cox):
    m, mp = models(cox)
    L_ = ["ring", f".model nch nmos {m}", f".model pch pmos {mp}", "Vdd vdd 0 1.8",
          "Ikick 0 n1 PULSE(0 100u 0.1n 10p 10p 50p 100n)"]
    for k in range(1, 6):
        a, b = f"n{k}", f"n{k % 5 + 1}"
        L_ += [f"Mn{k} {b} {a} 0 0 nch W=1u L=0.18u", f"Mp{k} {b} {a} vdd vdd pch W=3u L=0.18u", f"C{k} {a} 0 5f"]
    return parse("\n".join(L_ + [".end"]))[0]


def period(res):
    v = res["v(n1)"]
    i = np.where((v[:-1] < 0.9) & (v[1:] >= 0.9))[0]
    cr = res.axis[i] + (0.9 - v[i]) / (v[i + 1] - v[i]) * (res.axis[i + 1] - res.axis[i])
    return float(np.mean(np.diff(cr[-3:])))


rg = {cox: transient(ring(cox), 2e-12, 3e-9) for cox in (0, COX)}
J["ring"] = dict(off=period(rg[0]), on=period(rg[COX]))
J["ring"]["ratio"] = J["ring"]["on"] / J["ring"]["off"]

# ---- figure -------------------------------------------------------------------------------------------
fig = plt.figure(figsize=(16.5, 8.8), constrained_layout=True)
gs_ = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.15, 1.1])

ax = fig.add_subplot(gs_[0, 0]); ax.set_xlim(0, 9); ax.set_ylim(0, 8); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(a) the MOSFET has capacitors of its own")
d, s = draw.nmos(ax, 4.4, 4.0)                              # d = (6.0, 5.4), s = (6.0, 2.6)
draw.wire(ax, [1.8, 4.4], [4.0, 4.0]); draw.dot(ax, 3.0, 4.0)
ax.text(1.7, 4.0, "g", ha="right", va="center", color=draw.HOT, fontweight="bold", fontsize=10)
draw.wire(ax, [6.0, 6.0], [5.4, 6.6]); draw.wire(ax, [3.0, 3.0], [4.0, 6.6], color=draw.HOT)
draw.capacitor_h(ax, 6.6, 3.0, 6.0, color=draw.HOT); ax.text(4.5, 7.15, "Cgd", ha="center", color=draw.HOT, fontweight="bold")
draw.wire(ax, [6.0, 6.0], [2.6, 1.4]); draw.wire(ax, [3.0, 3.0], [4.0, 1.4], color=draw.HOT)
draw.capacitor_h(ax, 1.4, 3.0, 6.0, color=draw.HOT); ax.text(4.5, 0.55, "Cgs", ha="center", color=draw.HOT, fontweight="bold")
draw.dot(ax, 6.0, 6.6); draw.dot(ax, 6.0, 1.4)
ax.text(6.25, 6.35, "d", color=draw.HOT, fontweight="bold", fontsize=10); ax.text(6.25, 1.65, "s", color=draw.HOT, fontweight="bold", fontsize=10)
ax.text(6.6, 4.0, "orange = intrinsic\ncapacitances (inside\nthe model, bias-dependent)", fontsize=8, color=draw.HOT, va="center")

ax = fig.add_subplot(gs_[1, 0]); draw.planar_nmos_section(ax)
ax.set_title("(b) channel charge splits to s and d")
ax.annotate("", xy=(3.0, 3.1), xytext=(5.1, 3.5), arrowprops=dict(arrowstyle="-|>", color="#1b5fb5", lw=2.2))
ax.annotate("", xy=(9.0, 3.1), xytext=(6.9, 3.5), arrowprops=dict(arrowstyle="-|>", color="#1b5fb5", lw=1.4))
ax.text(2.8, 4.85, f"Qs = {J['hand']['split_s']*100:.0f} % of Qi", fontsize=8.5, color="#1b5fb5", ha="right")
ax.text(9.2, 4.85, f"Qd = {J['hand']['split_d']*100:.0f} %", fontsize=8.5, color="#1b5fb5", ha="left")

ax = fig.add_subplot(gs_[0, 1])
ax.plot(vds, cv[:, 0], color="#1f3b73", lw=2.2, label="Cgg (total seen at the gate)")
ax.plot(vds, cv[:, 1], color="#d95f02", lw=2.2, label="Cgs = −dQg/dVs")
ax.plot(vds, cv[:, 2], color="#1b9e77", lw=2.2, label="Cgd = −dQg/dVd")
ax.axvline(vov, color="gray", ls=":"); ax.text(vov + 0.02, 0.9, "Vds = Vov\n(saturation →)", fontsize=8.5, color="gray")
for y, tx in ((1 / 2, "1/2"), (2 / 3, "2/3"), (1.0, "1")):
    ax.axhline(y, color="gray", lw=0.5, ls=":"); ax.text(0.02, y + 0.015, tx, fontsize=8, color="gray")
ax.set(xlabel="Vds [V]  (Vgs = 1.8 V, n = 1)", ylabel="capacitance / (Cox·W·L)", title="(c) intrinsic capacitances vs Vds", ylim=(-0.05, 1.1))
ax.legend(loc="center left", bbox_to_anchor=(0.0, 0.3), fontsize=8.5); ax.grid(alpha=0.25)

ax = fig.add_subplot(gs_[1, 1])
ax.plot(vg, cgg0, color="#1f3b73", lw=2.2, label="Vds = 0  (triode, all channel charge follows Vg)")
ax.plot(vg, cgg1, color="#d95f02", lw=2.2, label="Vds = 1.8 V  (saturation)")
ax.axvline(VT0, color="gray", ls=":"); ax.text(VT0 + 0.02, 0.05, "Vth", color="gray", fontsize=8.5)
ax.set(xlabel="Vgs [V]", ylabel="Cgg / (Cox·W·L)", title="(d) gate capacitance vs Vgs (a C-V curve)", ylim=(-0.03, 1.1))
ax.text(0.03, 0.8, "below Vth the model gives ≈ 0:\ndepletion charge is not modelled", fontsize=8.5, transform=ax.transAxes)
ax.legend(loc="lower right", fontsize=8.5); ax.grid(alpha=0.25)

ax = fig.add_subplot(gs_[0, 2])
ax.plot(vg, qv[:, 1], color="#1f3b73", lw=2.2, label="Qg (gate)")
ax.plot(vg, qv[:, 0], color="#1b9e77", lw=2.2, label="Qd (drain share)")
ax.plot(vg, qv[:, 2], color="#d95f02", lw=2.2, label="Qs (source share)")
ax.plot(vg, qv[:, 0] + qv[:, 1] + qv[:, 2], "k--", lw=1, label="Qg + Qd + Qs = 0")
ax.set(xlabel="Vgs [V]  (Vds = 1.8 V, n = 1.3)", ylabel="charge / (Cox·W·L)  [V]", title="(e) terminal charges: they always add up to 0")
ax.legend(loc="lower left", fontsize=8.5); ax.grid(alpha=0.25)

ax = fig.add_subplot(gs_[1, 2])
for cox, col, lab in ((0, "#7570b3", "no intrinsic charge (overlap caps only)"), (COX, "#d95f02", "with channel-charge model")):
    ax.plot(rg[cox].axis * 1e9, rg[cox]["v(n1)"], color=col, lw=1.8, label=f"{lab}:  T = {period(rg[cox])*1e12:.0f} ps")
ax.set(xlabel="t [ns]", ylabel="V(n1) [V]", title="(f) 5-stage ring oscillator: the cost of the gate charge", xlim=(1.8, 3.0))
ax.legend(loc="lower center", fontsize=8.5, bbox_to_anchor=(0.5, -0.32)); ax.grid(alpha=0.25)

fig.suptitle("Lesson 6 - channel charge model: the MOSFET's intrinsic capacitances (EKV charges, minispice)", fontsize=13)
fig.savefig(out / "lesson6.png", dpi=130)
(out / "lesson6.json").write_text(json.dumps(J, indent=1, default=float))

h = J["hand"]
print(f"Cox = {COX*1e3:.3f} mF/m^2;  Cox*W*L: NMOS {CGN*1e15:.3f} fF, PMOS {CGP*1e15:.3f} fF")
print(f"hand: Qi = -(2/3)*Cox*W*L*Vov = {-h['qi_hand']*1e15:.4f} fC ; code Qg = {h['qg']*1e15:.4f} fC (Qi = -Qg)")
print(f"      split drain/source: hand 40/60, code {h['split_d']*100:.1f}/{h['split_s']*100:.1f}")
print(f"caps at Vds=0   : Cgg {cv[0,0]:.3f}  Cgs {cv[0,1]:.3f}  Cgd {cv[0,2]:.3f}   (expect 1, 1/2, 1/2)")
print(f"caps saturation : Cgg {cv[-1,0]:.3f}  Cgs {cv[-1,1]:.3f}  Cgd {cv[-1,2]:.3f}   (expect 2/3, 2/3, 0)")
print(f"Cdg/Csg (saturation, transcapacitances): {cv[-1,3]:.3f}, {cv[-1,4]:.3f}   (Cdg = dQd/dVg = -0.4*2/3 = {-0.4*2/3:.3f}; Csg = -0.6*2/3 = {-0.6*2/3:.3f})")
cs = J["conservation"]
print(f"CMOS input charge: delivered {cs['delivered']*1e15:.3f} fC vs expected dQg(N)+dQg(P) = {cs['dq_n']*1e15:.3f} + {cs['dq_p']*1e15:.3f} = {cs['expected']*1e15:.3f} fC")
print(f"FO1 tpHL/tpLH: no charge {fo[0]['tphl']*1e12:.1f}/{fo[0]['tplh']*1e12:.1f} ps -> with charge {fo[COX]['tphl']*1e12:.1f}/{fo[COX]['tplh']*1e12:.1f} ps")
print(f"ring period: {J['ring']['off']*1e12:.1f} ps -> {J['ring']['on']*1e12:.1f} ps  (x{J['ring']['ratio']:.2f})")

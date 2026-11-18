"""Lesson 5: the EKV model - one formula from weak to strong inversion (subthreshold current)."""

import json
import math
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import draw
from minispice import EKV, Level1, op, parse
from minispice.models import VT

out = pathlib.Path(__file__).parent / "out"
out.mkdir(exist_ok=True)

W, L = 1e-6, 0.18e-6
KP, VTO, N, LAM = 300e-6, 0.5, 1.3, 0.05
beta = KP * W / L
IS = 2 * N * beta * VT**2                      # EKV specific current
lv1 = Level1(1, dict(vto=VTO, kp=KP, lambda_=LAM))
ekv = EKV(1, dict(vto=VTO, kp=KP, n=N, lambda_=LAM))
J = dict(beta=beta, Is=IS, Vt=VT, n=N)


VDS = 1.8   # every comparison uses saturation (i_r ~ 0), so Id = Is * i_f * (1 + lambda*Vds)


def idr(m, vgs, vds=VDS):
    return m.evaluate(vds, vgs, 0.0, 0.0, W, L)[0]


# ---- 1. hand calculation in weak inversion ------------------------------------
vgs_h, vds_h = 0.2, VDS
weak_hand = IS * math.exp((vgs_h - VTO) / (N * VT)) * (1 - math.exp(-vds_h / VT)) * (1 + LAM * vds_h)
J["weak_hand"], J["weak_code"] = weak_hand, idr(ekv, vgs_h, vds_h)
J["weak_exp"] = math.exp((vgs_h - VTO) / (N * VT))

# ---- 2. table: Level 1 vs EKV --------------------------------------------------
rows = []
for vgs in (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0, 1.4, 1.8):
    ie = idr(ekv, vgs)
    rows.append(dict(vgs=vgs, lv1=idr(lv1, vgs), ekv=ie, ic=ie / IS))
J["table"] = rows

# inversion-coefficient boundaries (IC = Id / Is, with Vds large so i_r ~ 0)
vg = np.linspace(0, 1.8, 3601)
id_e = np.array([idr(ekv, v) for v in vg])
ic = id_e / (IS * (1 + LAM * VDS))
v_ic01, v_ic10 = np.interp(0.1, ic, vg), np.interp(10, ic, vg)
J["vgs_ic01"], J["vgs_ic10"] = float(v_ic01), float(v_ic10)

# strong inversion: EKV gives beta/(2n) Vov^2 while Level 1 gives beta/2 Vov^2
J["strong_ekv"], J["strong_lv1"] = idr(ekv, 1.0), idr(lv1, 1.0)
J["strong_ratio"] = J["strong_ekv"] / J["strong_lv1"]


# ---- 3. subthreshold swing vs n ----------------------------------------------------
def swing(n):
    m = EKV(1, dict(vto=VTO, kp=KP, n=n))
    v1, v2 = 0.10, 0.20
    return (v2 - v1) / (math.log10(idr(m, v2)) - math.log10(idr(m, v1))) * 1e3


J["swing"] = [dict(n=n, sim=swing(n), theory=n * VT * math.log(10) * 1e3) for n in (1.0, 1.3, 1.5)]

# ---- 4. Vds dependence in weak inversion ----------------------------------------------
vds = np.linspace(0.0, 0.6, 241)
ii_w = np.array([idr(EKV(1, dict(vto=VTO, kp=KP, n=N)), 0.2, v) for v in vds])
ii_s = np.array([idr(EKV(1, dict(vto=VTO, kp=KP, n=N)), 1.0, v) for v in vds])
J["vds_95_weak"] = float(np.interp(0.95, ii_w / ii_w[-1], vds))
J["vds_95_theory"] = -VT * math.log(0.05)

# ---- 5. inverter leakage vs Vth (static current at Vin = 0) -------------------------
leak = []
for vt in (0.2, 0.3, 0.4, 0.5, 0.6):
    txt = f"""leak
.model nch nmos level=ekv vto={vt} kp=300u n=1.3
.model pch pmos level=ekv vto=-{vt} kp=100u n=1.3
Vdd vdd 0 1.8
Vin in 0 0
M1 out in 0 0 nch W=1u L=0.18u
M2 out in vdd vdd pch W=3u L=0.18u
.end
"""
    r = op(parse(txt)[0])
    nm = EKV(1, dict(vto=vt, kp=KP, n=1.3))
    ideal = nm.evaluate(r["v(out)"][0], 0.0, 0.0, 0.0, W, L)[0]
    leak.append(dict(vt=vt, i_supply=-r["i(vdd)"][0], i_model=ideal))
J["leak"] = leak
J["leak_ratio_per_100mV"] = leak[0]["i_model"] / leak[1]["i_model"]
J["leak_ratio_theory"] = math.exp(0.1 / (N * VT))

# ---- figure -------------------------------------------------------------------------------
fig = plt.figure(figsize=(16, 8.6), constrained_layout=True)
gs_ = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.15, 1.05])

ax = fig.add_subplot(gs_[0, 0]); ax.set_xlim(0, 8); ax.set_ylim(0, 8); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(a) test bench (same as lesson 1, model = EKV)")
d, s = draw.nmos(ax, 3.6, 4.0)
ax.text(3.6, 6.7, "M1  level=ekv  W/L = 1u/0.18u", fontsize=8.5)
draw.vsource(ax, 1.4, 4.0, "Vgs"); draw.wire(ax, [1.85, 3.6], [4.0, 4.0]); draw.wire(ax, [1.4, 1.4], [3.55, 2.2]); draw.ground(ax, 1.4, 2.2)
draw.vsource(ax, 6.8, 3.9, "Vds", side="right"); draw.wire(ax, [6.8, 6.8], [4.35, 5.4]); draw.wire(ax, [6.8, d[0]], [5.4, 5.4])
draw.wire(ax, [6.8, 6.8], [3.45, 1.4]); draw.wire(ax, [s[0], 6.8], [1.4, 1.4]); draw.wire(ax, [s[0], s[0]], [s[1], 1.4]); draw.ground(ax, s[0], 1.4)
draw.dot(ax, d[0], 5.4); draw.dot(ax, s[0], 1.4)

ax = fig.add_subplot(gs_[1, 0]); draw.planar_nmos_section(ax, inversion="weak")
ax.set_title("(b) cross-section in weak inversion (Vgs = 0.2 V)")

ax = fig.add_subplot(gs_[0, 1])
ax.semilogy(vg, np.maximum([idr(lv1, v) for v in vg], 1e-18), color="#1f3b73", lw=2, label="Level 1")
ax.semilogy(vg, id_e, color="#d95f02", lw=2, label="EKV (n = 1.3)")
ax.axvspan(0, v_ic01, color="#cfe8cf", alpha=0.6, lw=0); ax.axvspan(v_ic01, v_ic10, color="#fff3c4", alpha=0.7, lw=0)
ax.axvspan(v_ic10, 1.8, color="#f9d3d3", alpha=0.6, lw=0)
for x, txt in ((v_ic01 / 2, "weak\nIC < 0.1"), ((v_ic01 + v_ic10) / 2, "moderate"), ((v_ic10 + 1.8) / 2, "strong\nIC > 10")):
    ax.text(x, 3e-12, txt, ha="center", fontsize=8.5)
ax.plot([vgs_h], [J["weak_code"]], "o", color="#c00", ms=7)
ax.annotate(f"Vgs = 0.2 V:  code {J['weak_code']*1e9:.3f} nA\nhand formula {weak_hand*1e9:.3f} nA (+{(weak_hand/J['weak_code']-1)*100:.1f} %)", (vgs_h, J["weak_code"]), (0.55, 3e-9), fontsize=8.5,
            arrowprops=dict(arrowstyle="->"))
ax.set(xlabel="Vgs [V]", ylabel="Id [A]", title="(c) Id-Vgs at Vds = 1.8 V: Level 1 stops at Vth, EKV continues",
       ylim=(1e-13, 1e-2), xlim=(0, 1.8))
ax.legend(loc="lower right", fontsize=8.5); ax.grid(alpha=0.25, which="both")

ax = fig.add_subplot(gs_[1, 1])
ax.plot(vds, ii_w / ii_w[-1], color="#d95f02", lw=2, label="weak inversion (Vgs = 0.2 V)")
ax.plot(vds, ii_s / ii_s[-1], color="#1f3b73", lw=2, label="strong inversion (Vgs = 1.0 V)")
ax.axvline(J["vds_95_weak"], color="gray", ls=":")
ax.text(J["vds_95_weak"] + 0.01, 0.2, f"95 % at Vds = {J['vds_95_weak']*1e3:.0f} mV\n(= 3·Vt)", fontsize=8.5)
ax.set(xlabel="Vds [V]", ylabel="Id / Id(Vds = 0.6 V)", title="(d) in weak inversion Id saturates after only ~3 Vt")
ax.legend(loc="lower right", fontsize=8.5); ax.grid(alpha=0.25)

ax = fig.add_subplot(gs_[0, 2])
vv = np.linspace(0, 0.5, 200)
for n, c in zip((1.0, 1.3, 1.5), ("#1b9e77", "#d95f02", "#7570b3")):
    m = EKV(1, dict(vto=VTO, kp=KP, n=n))
    sw = next(x for x in J["swing"] if x["n"] == n)
    ax.semilogy(vv, [idr(m, v) for v in vv], color=c, lw=2, label=f"n = {n}:  {sw['sim']:.1f} mV/decade")
ax.set(xlabel="Vgs [V]", ylabel="Id [A]", title="(e) subthreshold swing S = n·Vt·ln10", ylim=(1e-14, 1e-4))
ax.legend(loc="lower right", fontsize=8.5); ax.grid(alpha=0.25, which="both")

ax = fig.add_subplot(gs_[1, 2])
ax.semilogy([x["vt"] for x in leak], [x["i_model"] for x in leak], "o-", color="#c00", lw=2)
for x in leak:
    ax.annotate(f"{x['i_model']:.1e} A", (x["vt"], x["i_model"]), (6, 6), textcoords="offset points", fontsize=8)
ax.set(xlabel="threshold voltage Vth [V]", ylabel="inverter leakage at Vin = 0 [A]",
       title="(f) lower Vth → exponentially more leakage")
ax.text(0.97, 0.95, f"each −100 mV of Vth:\n×{J['leak_ratio_per_100mV']:.1f}  (theory e^(0.1/nVt) = ×{J['leak_ratio_theory']:.1f})",
        transform=ax.transAxes, ha="right", va="top", fontsize=8.5)
ax.grid(alpha=0.25, which="both")

fig.suptitle("Lesson 5 - the EKV model: subthreshold current (minispice)", fontsize=13)
fig.savefig(out / "lesson5.png", dpi=130)
(out / "lesson5.json").write_text(json.dumps(J, indent=1, default=float))

print(f"beta = {beta*1e3:.4f} mA/V^2, Is = 2 n beta Vt^2 = {IS*1e6:.4f} uA")
print(f"weak hand: exp((0.2-0.5)/(n Vt)) = {J['weak_exp']:.4e};  Id hand {weak_hand*1e9:.4f} nA, code {J['weak_code']*1e9:.4f} nA")
for r in rows:
    print(f"  Vgs={r['vgs']:.1f}  Level1 {r['lv1']:.3e}  EKV {r['ekv']:.3e}  IC={r['ic']:.3g}")
print(f"IC=0.1 at Vgs={v_ic01:.3f} V, IC=10 at Vgs={v_ic10:.3f} V")
print(f"strong inversion Vgs=1.0, Vds=1.8: EKV/Level1 = {J['strong_ratio']:.3f} (1/n = {1/N:.3f})")
for x in J["swing"]:
    print(f"  swing n={x['n']}: sim {x['sim']:.2f}  theory {x['theory']:.2f} mV/dec")
print(f"Vds for 95% (weak): sim {J['vds_95_weak']*1e3:.1f} mV, theory {J['vds_95_theory']*1e3:.1f} mV")
for x in leak:
    print(f"  Vth={x['vt']}: leak model {x['i_model']:.3e}, supply current from solver {x['i_supply']:.3e}")
print(f"ratio per 100 mV: {J['leak_ratio_per_100mV']:.2f} vs theory {J['leak_ratio_theory']:.2f}")

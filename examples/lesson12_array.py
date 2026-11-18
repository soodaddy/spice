"""Lesson 12: several DRAM cells (access NMOS + storage node) on ONE bit line: N = 2 and N = 4.

FACT: only the word line that is raised connects its cell to the bit line; the other cells are isolated (open access transistor).
CALC: minispice (Level 1) transients, ngspice cross-check, hand charge-sharing formula, retention ODE (EKV) with neighbour activity.
ILLUSTRATIVE: Cs, wire capacitance, per-cell junction capacitance, the activity factor, all device values (see dram_array.py).
"""

import json
import math
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

import draw
from dram_array import CJ, CS, CW, VBLP, VDD, VH, VPP, VTH, cbl_total, hand_dv, seq_net, share_net
from dram_retention import retention
from minispice import parse, transient
from ngspice_util import run_ngspice

here = pathlib.Path(__file__).parent
out = here / "out"
out.mkdir(exist_ok=True)
work = out / "ngspice"
J = dict(params=dict(vdd=VDD, vpp=VPP, vth=VTH, vh=VH, cs=CS, cw=CW, cj=CJ, vblp=VBLP, offset=0.02))
lvl = lambda bits: [VH if b else 0.0 for b in bits]
Q = lambda s: [float(x) for x in s]

# ------------------------------------------------------------------------------ 1. charge sharing with N cells on the bit line (no sense amplifier)
cases = [([1], [0]), ([1, 0], [0]), ([1, 1], [0]), ([0, 1], [0]), ([1, 0, 0, 0], [0]), ([1, 1, 1, 1], [0]), ([1, 0, 1, 1], [1]), ([0, 0, 0, 0], [2]),
         ([1, 0], [0, 1]), ([1, 1], [0, 1]), ([1, 0, 0, 0], [0, 1]), ([1, 1, 0, 0], [0, 1, 2])]
rows = []
for bits, sel in cases:
    n = len(bits)
    net = share_net(bits, sel)
    r = transient(parse(net)[0], 10e-12, 3.9e-9)
    i = len(r.axis) - 1
    hand = hand_dv(lvl(bits), sel, n)
    i0 = int(np.searchsorted(r.axis, 0.9e-9))              # before the word line rises (the cells are set by the switches until 0.4 ns)
    rows.append(dict(n=n, bits=bits, sel=sel, cbl=cbl_total(n), hand=hand, bl=float(r["v(bl)"][i] - VBLP), sn_sel=[float(r[f"v(sn{k})"][i]) for k in sel],
                     unsel_shift=[float(r[f"v(sn{k})"][i] - r[f"v(sn{k})"][i0]) for k in range(n) if k not in sel]))
J["share"] = rows
# ngspice on two of them
ng = {}
for key, (bits, sel) in {"n4_single": ([1, 0, 1, 1], [1]), "n2_double": ([1, 1], [0, 1]), "n4_triple": ([1, 1, 0, 0], [0, 1, 2])}.items():
    n = len(bits)
    net = share_net(bits, sel)
    r = transient(parse(net)[0], 5e-12, 3.9e-9)
    vec = ["v(bl)"] + [f"v(sn{k})" for k in range(n)]
    d = run_ngspice(net, f"dram_arr_{key}", "tran 5p 3.9n 0 5p", vec, work)
    ng[key] = max(float(np.max(np.abs(np.interp(r.axis, d[:, 0], d[:, 1 + j]) - r[v]))) for j, v in enumerate(vec))
J["share_ng"] = ng

# hand-only extrapolation to long bit lines (NOT simulated)
scal = []
for n in (1, 2, 4, 8, 16, 64, 256):
    scal.append(dict(n=n, cbl=cbl_total(n), dv=hand_dv([VH], [0], n) if n else 0.0))
J["scaling"] = scal

# ------------------------------------------------------------------------------ 2. write N cells one after the other, then read each with the latch sense amplifier
seqs = {}
for bits in ([1, 0], [1, 0, 1, 1]):
    n = len(bits)
    net, info = seq_net(bits)
    r = transient(parse(net)[0], 10e-12, info["tstop"])
    t = r.axis
    vec = ["v(bl)", "v(blb)"] + [f"v(sn{k})" for k in range(n)]
    d = run_ngspice(net, f"dram_seq{n}", f"tran 10p {info['tstop']:.4e} 0 10p", vec, work)
    dd = {v: np.abs(np.interp(t, d[:, 0], d[:, 1 + j]) - r[v]) for j, v in enumerate(vec)}
    rd = t >= info["r0"]
    diffs = {v: float(x.max()) for v, x in dd.items()}                                  # whole run
    diffs_read = {v: float(x[rd].max()) for v, x in dd.items()}                         # read phase only (from the first equalize on)
    worst = max(dd, key=lambda v: dd[v].max())
    t_worst = float(t[int(np.argmax(dd[worst]))])
    cells = []
    for k in range(n):
        iw = np.searchsorted(t, 1e-9 + k * 8e-9 + 5e-9)
        isa = np.searchsorted(t, info["t_sa"][k] - 0.05e-9)
        i0 = np.searchsorted(t, info["t_wl_on"][k] - 0.2e-9)
        i1 = np.searchsorted(t, info["t_wl_on"][k] + 8.5e-9)
        others = [j for j in range(n) if j != k]
        cells.append(dict(k=k, bit=bits[k], written=float(r[f"v(sn{k})"][iw]), dv_sa=float(r["v(bl)"][isa] - r["v(blb)"][isa]), hand=hand_dv(lvl(bits), [k], n),
                          bl_end=float(r["v(bl)"][i1]), blb_end=float(r["v(blb)"][i1]), restored=float(r[f"v(sn{k})"][i1]),
                          others_shift=float(max(abs(r[f"v(sn{j})"][i1] - r[f"v(sn{j})"][i0]) for j in others))))
    seqs[str(n)] = dict(bits=bits, cells=cells, ng=diffs, ng_read=diffs_read, ng_worst=[worst, t_worst], tstop=info["tstop"], t_wl_on=info["t_wl_on"], t_sa=info["t_sa"], t=t[::5].tolist(),
                        bl=r["v(bl)"][::5].tolist(), sn=[r[f"v(sn{k})"][::5].tolist() for k in range(n)], r0=info["r0"])
J["seq"] = {k: {kk: vv for kk, vv in v.items() if kk not in ("t", "bl", "sn")} for k, v in seqs.items()}
net2, info2 = seq_net([1, 0])
J["seq_netlist_n2"] = net2
r2 = transient(parse(net2)[0], 2e-12, info2["tstop"])
vec2 = ["v(bl)", "v(blb)", "v(sn0)", "v(sn1)"]
d2 = run_ngspice(net2, "dram_seq2_2ps", f"tran 2p {info2['tstop']:.4e} 0 2p", vec2, work)
J["seq"]["2"]["ng_2ps"] = {v: float(np.max(np.abs(np.interp(r2.axis, d2[:, 0], d2[:, 1 + j]) - r2[v]))) for j, v in enumerate(vec2)}
J["seq"]["2"]["ng_2ps_read"] = {v: float(np.max(np.abs(np.interp(r2.axis, d2[:, 0], d2[:, 1 + j]) - r2[v])[r2.axis >= info2["r0"]])) for j, v in enumerate(vec2)}

# ------------------------------------------------------------------------------ 3. retention with neighbour activity (lesson 11 ODE + duty)
ACT = 0.5          # fraction of a neighbour's access slot during which its sense amplifier holds the bit line at its rail (illustrative)
ret = []
for n, nb in ((1, []), (2, [0]), (2, [1]), (4, [0, 0, 0]), (4, [1, 1, 0]), (4, [1, 1, 1])):
    f = ACT * sum(1 for b in nb if b == 0) / n          # stored 1 victim: only neighbours that store 0 pull the bit line to 0 V
    row = dict(n=n, neighbours=nb, duty=f)
    for vth in (0.5, 0.6, 0.7):
        row[f"t_{vth}"] = retention(vth, 0.0, True, duty=f, cbl=cbl_total(n))["tret"]
    ret.append(row)
J["ret"] = ret
J["act"] = ACT
duty_axis = np.linspace(0, 1, 21)
J["ret_curve"] = {str(n): [retention(0.6, 0.0, True, duty=float(f), cbl=cbl_total(n))["tret"] for f in duty_axis] for n in (2, 4)}
J["ret_curve_x"] = duty_axis.tolist()

# ------------------------------------------------------------------------------ figure
fig = plt.figure(figsize=(16, 15), constrained_layout=True)
gs = fig.add_gridspec(3, 2, width_ratios=[1.0, 1.0])


def cells_circuit(ax, n, title):
    pitch = 3.6
    W = 2.4 + pitch * n + 3.3
    ax.set_xlim(0, W); ax.set_ylim(0, 9.4); ax.set_aspect("equal"); ax.axis("off"); ax.set_title(title)
    yb = 7.9
    draw.wire(ax, [0.6, W - 3.4], [yb, yb], lw=3); ax.text(0.6, yb + 0.35, "BL (shared bit line)", color=draw.HOT, fontweight="bold", fontsize=9.5)
    for k in range(n):
        gx = 1.8 + pitch * k
        d, s = draw.nmos(ax, gx, 4.7)
        draw.wire(ax, [d[0], d[0]], [d[1], yb]); draw.dot(ax, d[0], yb)
        draw.wire(ax, [gx - 0.9, gx], [4.7, 4.7], lw=2.4, color=draw.HOT); ax.text(gx - 0.9, 5.15, f"WL{k}", color=draw.HOT, fontweight="bold", fontsize=9, ha="left")
        draw.wire(ax, [s[0], s[0]], [s[1], 2.7]); draw.dot(ax, s[0], 2.7); ax.text(s[0] + 0.25, 3.0, f"SN{k}", color=draw.HOT, fontsize=8.5, fontweight="bold")
        draw.capacitor(ax, s[0], 2.7, 1.1); ax.text(s[0] + 0.45, 1.9, "Cs", fontsize=8.5, color=draw.HOT); draw.ground(ax, s[0], 1.1)
    xc = W - 3.4
    draw.capacitor(ax, xc - 1.0, yb, 6.0); ax.text(xc - 0.55, 6.85, "Cbl = Cw + N*Cj", fontsize=8.5, color=draw.HOT, fontweight="bold"); draw.ground(ax, xc - 1.0, 6.0)
    ax.add_patch(Rectangle((xc, yb - 0.7), 2.7, 1.4, fc="#e8e0f5", ec=draw.INK, lw=1.6)); ax.text(xc + 1.35, yb, "sense\namp", ha="center", va="center", fontsize=9)


ax = fig.add_subplot(gs[0, 0]); cells_circuit(ax, 2, "(a) N = 2: two access transistors + storage nodes on one bit line")
ax = fig.add_subplot(gs[0, 1]); cells_circuit(ax, 4, "(b) N = 4")

# (c) cross-section (concept): two cells share a bit-line contact
ax = fig.add_subplot(gs[1, 0]); ax.set_xlim(0, 31.5); ax.set_ylim(-0.6, 11); ax.set_aspect("equal"); ax.axis("off"); ax.set_title("(c) N = 4 cross-section (concept): two cells share one bit-line contact; not to scale")
ax.add_patch(Rectangle((0, 0), 31.5, 3, fc="#e6ecf5", ec=draw.INK, lw=1.2)); ax.text(0.3, 0.3, "p-type substrate", fontsize=8)
for gi, x0 in enumerate((0.8, 15.8)):                                     # one pair: SN_a | WL_a | BL contact | WL_b | SN_b
    xs = [x0 + 0.0, x0 + 4.2, x0 + 8.4, x0 + 12.6]
    for j, xn in enumerate((xs[0], xs[2] - 0.9, xs[3] - 1.3)):
        pass
    sn_a, bl_c, sn_b = x0, x0 + 6.0, x0 + 12.0
    for xx, w, lab in ((sn_a, 2.2, "n+"), (bl_c, 2.2, "n+"), (sn_b, 2.2, "n+")):
        ax.add_patch(Rectangle((xx, 2.2), w, 0.8, fc="#f2b98f", ec=draw.INK, lw=1.2)); ax.text(xx + w / 2, 2.6, lab, ha="center", va="center", fontsize=8.5, fontweight="bold")
    for xx, name in ((sn_a + 2.2, f"WL{2*gi}"), (bl_c + 2.2, f"WL{2*gi+1}")):
        ax.add_patch(Rectangle((xx, 3.0), 3.8, 0.2, fc="#f6e27a", ec=draw.INK, lw=1)); ax.add_patch(Rectangle((xx, 3.2), 3.8, 0.9, fc="#7f8794", ec=draw.INK, lw=1.2))
        ax.text(xx + 1.9, 3.65, name, ha="center", va="center", color="white", fontsize=8.5, fontweight="bold")
    for xx, name in ((sn_a, f"Cs{2*gi}"), (sn_b, f"Cs{2*gi+1}")):
        draw.wire(ax, [xx + 1.1, xx + 1.1], [3.0, 4.6], lw=3)
        ax.add_patch(Rectangle((xx - 0.4, 4.6), 3.0, 4.6, fc="#dcdfe4", ec=draw.INK, lw=1.0, hatch=".."))
        ax.add_patch(Rectangle((xx + 0.1, 4.6), 2.0, 4.2, fc="#f2b98f", ec=draw.INK, lw=1.0)); ax.text(xx + 1.1, 6.6, name, ha="center", va="center", fontsize=8, fontweight="bold")
    draw.wire(ax, [bl_c + 1.1, bl_c + 1.1], [3.0, 9.6], lw=3)
draw.wire(ax, [7.9, 28.9], [9.8, 9.8], lw=5); ax.text(17.5, 10.2, "BL (shared by all cells, perpendicular to the WLs)", fontsize=9, color=draw.HOT, fontweight="bold", ha="center")

# (d) read signal vs N
ax = fig.add_subplot(gs[1, 1])
ns = np.array([1, 2, 4, 8, 16, 32, 64, 128, 256])
ax.semilogx(ns, [hand_dv([VH], [0], int(n)) * 1e3 for n in ns], "-o", color="#1f3b73", lw=2.2, label="hand formula (one cell read)")
sim_n = {1: [r for r in rows if r["n"] == 1][0], 2: [r for r in rows if r["n"] == 2][0], 4: [r for r in rows if r["n"] == 4][0]}
ax.plot(list(sim_n), [v["bl"] * 1e3 for v in sim_n.values()], "s", color="#d95f02", ms=9, mfc="none", mew=2, label="minispice (N = 1, 2, 4)")
ax.axhline(20, color="gray", ls=":"); ax.text(1.1, 23, "20 mV: assumed sense-amp offset", fontsize=8.5, color="gray")
ax.annotate("N >= 64: hand formula only\n(not simulated)", (64, hand_dv([VH], [0], 64) * 1e3), (6, 46), fontsize=8.5, arrowprops=dict(arrowstyle="->"))
ax.set(xlabel="cells on the bit line, N", ylabel="read signal dV [mV]", title="(d) more cells -> larger Cbl -> smaller signal", ylim=(0, 95)); ax.legend(fontsize=8.5); ax.grid(alpha=0.25, which="both")

# (e) the N = 4 sequence
ax = fig.add_subplot(gs[2, 0])
S4 = seqs["4"]; t = np.array(S4["t"]) * 1e9
cols = ["#1b9e77", "#d95f02", "#7570b3", "#e6ab02"]
ax.plot(t, S4["bl"], color="#1f3b73", lw=1.3, label="BL")
for k in range(4):
    ax.plot(t, S4["sn"][k], color=cols[k], lw=2.0, label=f"SN{k} (wrote {S4['bits'][k]})")
ax.axvline(S4["r0"] * 1e9, color="gray", ls=":"); ax.text(S4["r0"] * 1e9 + 0.6, -0.07, "write | read", fontsize=8.5, color="gray")
ax.set(xlabel="t [ns]", ylabel="voltage [V]", title="(e) write 1, 0, 1, 1 into 4 cells, then read each: only the selected cell moves", ylim=(-0.1, 1.45)); ax.legend(fontsize=8, ncol=5, loc="upper center"); ax.grid(alpha=0.25)

# (f) retention vs neighbour activity
ax = fig.add_subplot(gs[2, 1])
for n, c in ((2, "#1b5fb5"), (4, "#d95f02")):
    ax.semilogy(duty_axis, J["ret_curve"][str(n)], lw=2.2, color=c, label=f"N = {n}")
ax.axhline(64e-3, color="#7570b3", ls="--"); ax.text(0.02, 0.085, "64 ms", color="#7570b3", fontsize=8.5)
for f, lab in ((ACT * 1 / 2, "N=2, neighbour 0"), (ACT * 3 / 4, "N=4, neighbours 000")):
    ax.axvline(f, color="gray", ls=":"); ax.text(f + 0.01, 120, lab, rotation=90, fontsize=8, color="gray", va="top")
ax.set(xlabel="fraction f of time the BL sits at 0 V (neighbour accesses)", ylabel="t_ret of a stored 1 [s] (Vth = 0.6 V)", title="(f) busier neighbours -> a stored 1 is lost sooner (EKV leakage ODE)", xlim=(0, 1), ylim=(5e-3, 200)); ax.legend(fontsize=8.5, loc="upper right"); ax.grid(alpha=0.25, which="both")
fig.suptitle("Lesson 12 - 2 and 4 DRAM cells sharing one bit line (minispice, illustrative values)", fontsize=13)
fig.savefig(out / "lesson12.png", dpi=125)


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if (math.isinf(o) or math.isnan(o)) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


(out / "lesson12.json").write_text(json.dumps(clean(J), indent=1))
print("SHARE (hand | minispice, mV):")
for r in rows:
    print(f"  N={r['n']} bits={r['bits']} sel={r['sel']}: {r['hand']*1e3:8.3f} | {r['bl']*1e3:8.3f}   sn_sel={[round(x, 4) for x in r['sn_sel']]} unsel shift={[round(x, 6) for x in r['unsel_shift']]}")
print("ngspice max diff (mV):", {k: round(v * 1e3, 3) for k, v in ng.items()})
for n, S in seqs.items():
    print(f"SEQ N={n}: ngspice max diff mV (whole run)", {k: round(v * 1e3, 3) for k, v in S["ng"].items()}, "worst", S["ng_worst"], "| read phase", {k: round(v * 1e3, 3) for k, v in S["ng_read"].items()})
    for c in S["cells"]:
        print(f"   cell {c['k']} bit {c['bit']}: written {c['written']:.4f} dV {c['dv_sa']*1e3:7.2f} (hand {c['hand']*1e3:7.2f}) BL end {c['bl_end']:.3f} restored {c['restored']:.4f}  others shift {c['others_shift']*1e3:.4f} mV")
print("SEQ N=2 at 2 ps: whole", {k: round(v * 1e3, 3) for k, v in J["seq"]["2"]["ng_2ps"].items()}, "read phase", {k: round(v * 1e3, 3) for k, v in J["seq"]["2"]["ng_2ps_read"].items()})
print("RET:", [(r["n"], r["neighbours"], round(r["duty"], 3), {k: round(v, 3) for k, v in r.items() if k.startswith("t_")}) for r in ret])
print("SCALING:", [(s["n"], round(s["cbl"] * 1e15), round(s["dv"] * 1e3, 1)) for s in scal])

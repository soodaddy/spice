"""Lesson 7: cross-check minispice against ngspice with the SAME netlists (SPICE Level 1)."""

import json
import pathlib
import re
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import draw
from minispice import dc_sweep, op, parse, transient

here = pathlib.Path(__file__).parent
out = here / "out"
work = out / "ngspice"
work.mkdir(parents=True, exist_ok=True)

MODELS = """.model nch nmos level=1 vto=0.5 kp=300u lambda=0.05 cgso=3e-10 cgdo=3e-10
.model pch pmos level=1 vto=-0.5 kp=100u lambda=0.05 cgso=3e-10 cgdo=3e-10
"""
NET_BIAS = lambda vgs, vds: f"""NMOS with resistor load / test bench
{MODELS}Vdd vdd 0 1.8
Vg g 0 {vgs}
Rd vdd d 5k
M1 d g 0 0 nch W=1u L=0.18u
.end
"""
NET_NMOS = lambda vgs: f"""NMOS output curve
{MODELS}Vgs g 0 {vgs}
Vds d 0 1.0
M1 d g 0 0 nch W=1u L=0.18u
.end
"""
NET_INV = f"""CMOS inverter
{MODELS}Vdd vdd 0 1.8
Vin in 0 PULSE(0 1.8 0.2n 0.1n 0.1n 0.8n 2n)
M1 out in 0 0 nch W=1u L=0.18u
M2 out in vdd vdd pch W=3u L=0.18u
CL out 0 20f
.end
"""
NET_RING = (here / "ring_osc.cir").read_text()          # the very same file as in the ring-oscillator example


def run_ngspice(netlist, name, analysis, vectors):
    """Strip analysis cards, add one ngspice control block, run in batch mode, return columns."""
    keep = [l for l in netlist.splitlines() if not l.strip().lower().startswith((".dc", ".tran", ".op", ".end"))]
    data = work / f"{name}.dat"
    data.unlink(missing_ok=True)
    deck = "\n".join(keep + [
        ".options reltol=1e-6 abstol=1e-14 vntol=1e-9 gmin=1e-12 method=trap interp",
        ".control", "set wr_singlescale", "set wr_vecnames", analysis, f"wrdata {data.name} {' '.join(vectors)}", ".endc", ".end", ""])
    cir = work / f"{name}.cir"
    cir.write_text(deck)
    p = subprocess.run(["ngspice", "-b", "-o", f"{name}.log", cir.name], cwd=work, capture_output=True, text=True, timeout=300)
    log = (work / f"{name}.log").read_text()
    if p.returncode != 0 or not data.exists() or re.search(r"\berror\b", log, re.I):
        raise RuntimeError(f"ngspice failed for {name}:\n{log[-800:]}")
    return np.loadtxt(data, skiprows=1)


J = {}
ver = subprocess.run(["ngspice", "-v"], capture_output=True, text=True).stdout
J["ngspice_version"] = re.search(r"ngspice-(\d+)", ver).group(1)

# ---- A. operating point (lesson 2 circuit, Vg = 1.4 V) -----------------------------------------
vd_mini = op(parse(NET_BIAS(1.4, 0)[0:0] + NET_BIAS(1.4, 0))[0])["v(d)"][0]
vd_ng = run_ngspice(NET_BIAS(1.4, 0), "op", "dc Vg 1.4 1.4 1", ["v(d)"])[1]
J["op"] = dict(mini=vd_mini, ngspice=float(vd_ng), diff=float(abs(vd_mini - vd_ng)))

# ---- B. NMOS output curves (lesson 1 bench) ----------------------------------------------------
curves, worst, id_max = [], 0.0, 0.0
for vgs in (0.6, 0.8, 1.0, 1.2, 1.4):
    c, _ = parse(NET_NMOS(vgs))
    r = dc_sweep(c, "vds", 0.0, 1.8, 0.01)
    ng = run_ngspice(NET_NMOS(vgs), f"nmos_{vgs}", "dc Vds 0 1.8 0.01", ["i(vds)"])
    i_m, i_n = -r["i(vds)"], -ng[:, 1]
    worst = max(worst, float(np.max(np.abs(i_m - i_n))))
    id_max = max(id_max, float(i_m.max()))
    curves.append((vgs, r.axis, i_m, i_n))
J["curves"] = dict(max_abs_diff=worst, id_max=id_max, rel=worst / id_max)

# ---- C. inverter VTC ------------------------------------------------------------------------------
c, _ = parse(NET_INV)
vtc = dc_sweep(c, "vin", 0.0, 1.8, 0.001)
ng_vtc = run_ngspice(NET_INV, "vtc", "dc Vin 0 1.8 0.001", ["v(out)", "i(vdd)"])
dv = np.abs(vtc["v(out)"] - ng_vtc[:, 1])
slope = np.abs(np.gradient(vtc["v(out)"], vtc.axis))
# on the steep part a tiny Vin shift moves Vout a lot -> also report the shift in Vin needed to make them agree
steep = slope > 1.0                      # only where the curve is steep does a Vin shift make sense
shift = dv[steep] / slope[steep]
vm = lambda v, x: float(np.interp(0.0, (v - x)[::-1], x[::-1]))
J["vtc"] = dict(max_dv=float(dv.max()), max_dv_flat=float(dv[~steep].max()), max_equiv_vin_shift=float(shift.max()),
                vm_mini=vm(vtc["v(out)"], vtc.axis), vm_ng=vm(ng_vtc[:, 1], vtc.axis), idd_max_mini=float((-vtc["i(vdd)"]).max()),
                idd_max_ng=float((-ng_vtc[:, 2]).max()))

# ---- D. inverter transient -----------------------------------------------------------------------------
c, _ = parse(NET_INV)
tr = transient(c, 5e-12, 4e-9)
ng = run_ngspice(NET_INV, "tran", "tran 5p 4n 0 5p", ["v(out)", "i(vdd)"])
v_ng = np.interp(tr.axis, ng[:, 0], ng[:, 1])
i_ng = np.interp(tr.axis, ng[:, 0], -ng[:, 2])
dvt = np.abs(tr["v(out)"] - v_ng)


def cross(t, v, lvl, rising, t0=0.0):
    for i in range(1, len(t)):
        if t[i] >= t0 and ((v[i - 1] < lvl <= v[i]) if rising else (v[i - 1] > lvl >= v[i])):
            return t[i - 1] + (lvl - v[i - 1]) / (v[i] - v[i - 1]) * (t[i] - t[i - 1])


def delays(t, vin, vout):
    return (cross(t, vout, 0.9, False) - cross(t, vin, 0.9, True), cross(t, vout, 0.9, True, 0.9e-9) - cross(t, vin, 0.9, False, 0.9e-9))


vin_t = tr["v(in)"]
J["tran"] = dict(max_dv=float(dvt.max()), rms_dv=float(np.sqrt(np.mean(dvt**2))),
                 tphl_mini=delays(tr.axis, vin_t, tr["v(out)"])[0], tplh_mini=delays(tr.axis, vin_t, tr["v(out)"])[1],
                 tphl_ng=delays(tr.axis, vin_t, v_ng)[0], tplh_ng=delays(tr.axis, vin_t, v_ng)[1],
                 ipeak_mini=float((-tr["i(vdd)"]).max()), ipeak_ng=float(i_ng.max()))

# ---- E. ring oscillator -------------------------------------------------------------------------------------
c, an = parse(NET_RING)
rg = transient(c, 2e-12, 6e-9)
ngr = run_ngspice(NET_RING, "ring", "tran 2p 6n 0 2p", ["v(n1)", "v(n2)", "v(n3)", "v(n4)", "v(n5)"])


def per(t, v):
    i = np.where((v[:-1] < 0.9) & (v[1:] >= 0.9))[0]
    cr = t[i] + (0.9 - v[i]) / (v[i + 1] - v[i]) * (t[i + 1] - t[i])
    return cr[cr > 1e-9]


cm, cn = per(rg.axis, rg["v(n1)"]), per(ngr[:, 0], ngr[:, 1])
J["ring"] = dict(period_mini=float(np.mean(np.diff(cm[-4:]))), period_ng=float(np.mean(np.diff(cn[-4:]))),
                 first_cross_mini=float(cm[0]), first_cross_ng=float(cn[0]), n_cross=[len(cm), len(cn)])
J["ring"]["rel"] = abs(J["ring"]["period_mini"] - J["ring"]["period_ng"]) / J["ring"]["period_ng"]

# ---- figure ----------------------------------------------------------------------------------------------------
fig = plt.figure(figsize=(16.5, 9), constrained_layout=True)
gs_ = fig.add_gridspec(2, 3, width_ratios=[1.05, 1.1, 1.1])

ax = fig.add_subplot(gs_[0, 0]); ax.set_xlim(0, 10); ax.set_ylim(0, 8.6); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(a) one netlist, two simulators")


def box(x, y, w, h, txt, fc, ec=draw.INK, fs=9):
    from matplotlib.patches import FancyBboxPatch
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.15", fc=fc, ec=ec, lw=1.4))
    ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=fs)


box(3.0, 7.0, 4.0, 1.1, "inverter.cir / ring_osc.cir\n(SPICE netlist text)", "#fff6c9")
box(0.2, 4.4, 4.0, 1.5, "minispice\n(Python, our solver)\n.op .dc .tran", "#dbe9ff")
box(5.8, 4.4, 4.0, 1.5, "ngspice 47\n(reference simulator)\nbatch mode", "#e0f2e0")
box(0.2, 1.9, 4.0, 1.1, "Vout(t), Id(Vds) ... \n(numpy arrays)", "#f3f3f3")
box(5.8, 1.9, 4.0, 1.1, "wrdata file\n(text columns)", "#f3f3f3")
box(2.4, 0.2, 5.2, 1.0, "compare: max |Δ|, delays, period", "#ffe0d0", ec=draw.HOT)
for x0, y0, x1, y1 in ((4.0, 7.0, 2.2, 5.95), (6.0, 7.0, 7.8, 5.95), (2.2, 4.4, 2.2, 3.05), (7.8, 4.4, 7.8, 3.05), (2.2, 1.9, 4.0, 1.25), (7.8, 1.9, 6.0, 1.25)):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color="#444", lw=1.6))

ax = fig.add_subplot(gs_[1, 0]); ax.axis("off")
ax.set_title("(b) how close are they? (Level 1)", pad=10)
rows = [
    ("operating point  Vd", f"{J['op']['diff']:.1e} V", f"Vd = {J['op']['mini']:.6f} V"),
    ("NMOS Id–Vds (5 curves)", f"{J['curves']['max_abs_diff']:.1e} A", f"{J['curves']['rel']:.1e} of max Id"),
    ("inverter VTC, max |ΔVout|", f"{J['vtc']['max_dv']*1e6:.2f} µV", f"≙ ΔVin ≈ {J['vtc']['max_equiv_vin_shift']*1e6:.1f} µV (steep part)"),
    ("inverter transient, max |ΔVout|", f"{J['tran']['max_dv']*1e3:.2f} mV", f"rms {J['tran']['rms_dv']*1e3:.2f} mV"),
    ("ring oscillator period", f"{abs(J['ring']['period_mini']-J['ring']['period_ng'])*1e12:.2f} ps", f"{J['ring']['rel']*100:.2f} %"),
]
for k, (a, b, c_) in enumerate(rows):
    y = 0.88 - k * 0.17
    ax.text(0.0, y, a, fontsize=10, transform=ax.transAxes, va="center")
    ax.text(0.62, y, b, fontsize=10, fontweight="bold", color="#1b5fb5", transform=ax.transAxes, va="center")
    ax.text(0.80, y, c_, fontsize=8.5, color="#555", transform=ax.transAxes, va="center")
    ax.plot([0, 1], [y - 0.075] * 2, color="#ddd", lw=0.8, transform=ax.transAxes)

ax = fig.add_subplot(gs_[0, 1])
for (vgs, x, im, inn), col in zip(curves, plt.cm.viridis(np.linspace(0.1, 0.85, 5))):
    ax.plot(x, im * 1e3, color=col, lw=2.2, label=f"Vgs = {vgs:.1f} V")
    ax.plot(x[::12], inn[::12] * 1e3, "o", color="k", ms=4, mfc="none", mew=0.9)
ax.plot([], [], "o", color="k", mfc="none", label="ngspice")
ax.set(xlabel="Vds [V]", ylabel="Id [mA]", title="(c) NMOS output curves (line: minispice, ○: ngspice)")
ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.25)

ax = fig.add_subplot(gs_[1, 1])
ax.plot(vtc.axis, vtc["v(out)"], color="#1f3b73", lw=2.2, label="minispice")
ax.plot(vtc.axis[::40], ng_vtc[::40, 1], "o", color="#d95f02", ms=5, mfc="none", mew=1.2, label="ngspice")
ax.set(xlabel="Vin [V]", ylabel="Vout [V]", title="(d) inverter VTC")
ax.text(0.03, 0.55, f"Vm: {J['vtc']['vm_mini']:.4f} V (minispice) vs {J['vtc']['vm_ng']:.4f} V (ngspice)\npeak supply current: {J['vtc']['idd_max_mini']*1e6:.2f} vs {J['vtc']['idd_max_ng']*1e6:.2f} µA",
        transform=ax.transAxes, ha="left", va="top", fontsize=8.5)
ax.legend(loc="lower left", fontsize=8.5); ax.grid(alpha=0.25)

ax = fig.add_subplot(gs_[0, 2])
ax.plot(tr.axis * 1e9, tr["v(out)"], color="#1f3b73", lw=2.2, label="minispice")
ax.plot(tr.axis[::8] * 1e9, v_ng[::8], "o", color="#d95f02", ms=4, mfc="none", mew=1.1, label="ngspice")
ax.plot(tr.axis * 1e9, vin_t, color="#999", ls="--", lw=1.2, label="Vin")
ax.set(xlabel="t [ns]", ylabel="V", title="(e) inverter transient")
ax.text(0.40, 0.5, f"tpHL {J['tran']['tphl_mini']*1e12:.1f} vs {J['tran']['tphl_ng']*1e12:.1f} ps\ntpLH {J['tran']['tplh_mini']*1e12:.1f} vs {J['tran']['tplh_ng']*1e12:.1f} ps",
        transform=ax.transAxes, ha="center", fontsize=9)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), fontsize=8.5, ncol=3, frameon=False); ax.grid(alpha=0.25)

ax = fig.add_subplot(gs_[1, 2])
ax.plot(rg.axis * 1e9, rg["v(n1)"], color="#1f3b73", lw=2.2, label=f"minispice: T = {J['ring']['period_mini']*1e12:.2f} ps")
ax.plot(ngr[::3, 0] * 1e9, ngr[::3, 1], "o", color="#d95f02", ms=3.5, mfc="none", mew=1, label=f"ngspice: T = {J['ring']['period_ng']*1e12:.2f} ps")
ax.set(xlabel="t [ns]", ylabel="V(n1) [V]", title="(f) 5-stage ring oscillator (same netlist)", xlim=(4.6, 5.4))
ax.legend(loc="lower center", fontsize=8.5, bbox_to_anchor=(0.5, -0.32)); ax.grid(alpha=0.25)

# ---- data for the interactive widget of the textbook (downsampled, 10 significant digits)
def _r(a):
    return [float(f"{float(x):.10g}") for x in a]


win = (rg.axis >= 4.6e-9) & (rg.axis <= 5.4e-9)
wdata = dict(
    curves=dict(vgs=[0.6, 0.8, 1.0, 1.2, 1.4], vds=_r(curves[0][1]), mini=[_r(c[2]) for c in curves], ng=[_r(c[3]) for c in curves]),
    vtc=dict(vin=_r(vtc.axis[::2]), mini=_r(vtc["v(out)"][::2]), ng=_r(ng_vtc[::2, 1])),
    tran=dict(t=_r(tr.axis), vin=_r(vin_t), mini=_r(tr["v(out)"]), ng=_r(v_ng), idd_mini=_r(-tr["i(vdd)"]), idd_ng=_r(i_ng)),
    ring=dict(t=_r(rg.axis[win]), mini=[_r(rg[f"v(n{k})"][win]) for k in range(1, 6)],
              ng=[_r(np.interp(rg.axis[win], ngr[:, 0], ngr[:, k])) for k in range(1, 6)]),
)
(out / "lesson7_data.json").write_text(json.dumps(wdata, separators=(",", ":")))

fig.suptitle("Lesson 7 - cross-check against ngspice (SPICE Level 1, same netlists)", fontsize=13)
fig.savefig(out / "lesson7.png", dpi=130)
(out / "lesson7.json").write_text(json.dumps(J, indent=1, default=float))
for k, v in J.items():
    print(k, v)

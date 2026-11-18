"""Regression test of the interactive widgets: mount every widget in headless Chrome, read the values it computed
(defaults and a changed input) and compare them with independent minispice (Python) results.

test_js_parity.py checks the JavaScript models; this test checks the widget code on top of them (wrong monotonic
direction in a solver, a mistyped formula, a wrong unit ...), which the model test cannot see.
"""

import html
import json
import math
import pathlib
import re
import shutil
import subprocess

import numpy as np
import pytest

from minispice import EKV, Level1, dc_sweep, op, parse, transient
from minispice.models import VT

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHROME = next((c for c in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("google-chrome"), shutil.which("chromium"),
                           shutil.which("chromium-browser")) if c and pathlib.Path(c).exists()), None)
pytestmark = pytest.mark.skipif(CHROME is None, reason="no headless Chrome found")

JS_FILES = ["core.js", "ui.js", "scene3d.js", "schem.js", "ia_core.js", "ia_l1_4.js", "ia_l5_10.js", "ia_l7.js", "ia_l11.js"]
PROBE = r"""
const errs = [], R = {}; window.addEventListener('error', (e) => errs.push('uncaught: ' + e.message));
const IDS = ['l1','l2','l3','l4','l5','l6','l7','l9','l10','l11'];
function W(k) { return document.getElementById('ia-' + k).__ia; }
function setv(k, kv) { for (const id in kv) W(k).ctl[id].set(kv[id]); W(k).refresh(); return W(k).get(); }
try {
  for (const k of IDS) IA.W[k](document.getElementById('ia-' + k));
  let s = W('l1').get(); R.l1 = { id: s.ev.id, gm: s.ev.gg, gds: s.ev.gd };
  s = setv('l1', { vgs: 1.4, vds: 0.3, vth: 0.6, lam: 0.1 }); R.l1b = { id: s.ev.id, gm: s.ev.gg, gds: s.ev.gd, region: s.region };
  s = W('l2').get(); R.l2 = { star: s.star, first: s.trace[0].v1, n: s.trace.length };
  s = setv('l2', { vdd: 3.0, vg: 1.0, rd: 20000, vth: 0.7, W: 2 }); R.l2b = { star: s.star };
  s = W('l3').get(); R.l3 = { fall: s.c.fall, rise: s.c.rise, vlow: s.c.vlow };
  s = W('l4').get(); R.l4 = { vm: s.vm, gain: s.gainMax, hand: s.gainHand, tphl: s.tr.tphl, tplh: s.tr.tplh };
  s = setv('l4', { vdd: 1.2, ratio: 2, vtn: 0.4, vtp: 0.45, vin: 0.55 }); R.l4b = { vm: s.vm, vout: s.vout, gain: s.gainMax };
  s = W('l5').get(); R.l5 = { id: s.ev.id, v01: s.v01, v10: s.v10 };
  s = W('l6').get(); R.l6 = { gg: s.cn.gg, gs: s.cn.gs, gd: s.cn.gd };
  s = setv('l6', { vgs: 1.8, vds: 3, n: 1 }); s = setv('l6', { vgs: 1.8, vds: 2, n: 1 }); R.l6b = { gg: s.cn.gg, gs: s.cn.gs, gd: s.cn.gd };
  s = W('l9').get(); R.l9 = { weff: s.weff, id: s.id, ss: s.met.ss, dibl: s.met.dibl, ioff: s.met.ioff, ion: s.met.ion };
  s = setv('l9', { H: 50, Wf: 6, N: 3, L: 14, n: 1.3, eta: 0.08 }); R.l9b = { weff: s.weff, id: s.id, ioff: s.met.ioff };
  s = W('l10').get(); R.l10 = { weff: s.weff, gain: s.vt.cur.gain, planar: s.vt.planar.gain, fin: s.vt.fin.gain, gaa: s.vt.gaa.gain, vm: s.vt.cur.vm };
  s = setv('l10', { N: 4, W: 20, T: 4 }); R.l10b = { weff: s.weff };
  s = W('l7').get(); R.l7 = { dmax: s.dmax, n: s.n };
  // switching between a log-scale and a linear plot of the same widget used to throw (Plot options were sticky)
  for (const m of ['tran', 'dc', 'tran']) { W('l4').ctl.mode.set(m); W('l4').refresh(); }
  R.l4switch = W('l4').get().mode;
  // deterministic form of the same check: the axis scale of a Plot must not leak from one begin() to the next
  const pcv = document.createElement('canvas'); document.body.append(pcv); const pl = new UI.Plot(pcv, { height: 100 });
  pl.begin({ xlog: true, ylog: true, xlim: [1e-3, 1], ylim: [1e-3, 1] }).end(); pl.begin({ xlim: [0, 1], ylim: [0, 1] }).end();
  R.plotLog = [pl.o.xlog, pl.o.ylog];
  s = W('l11').get(); R.l11 = { dv: s.sim.dv, dvHand: s.dvHand, bl: s.vbl, sn: s.vsn, ok: s.sim.ok, tau: s.sim.tau, vh: s.vh };
  s = setv('l11', { mode: 'write1', vpp: 1.9, t: 8.5 }); R.l11w = { sn: s.vsn, vh: s.vh };
  s = setv('l11', { mode: 'write1', vpp: 2.0, t: 8.5 }); R.l11w2 = { sn: s.vsn, vh: s.vh };
  s = setv('l11', { mode: 'read0', vpp: 2.0, cs: 15e-15, cbl: 220e-15, voff: 0.03, t: 3.9 }); R.l11r0 = { dv: s.sim.dv, ok: s.sim.ok, bit: s.sim.bit, margin: s.dvHand };
  s = setv('l11', { mode: 'read1', cs: 10e-15, cbl: 300e-15, voff: 0.06, t: 3.9 }); R.l11weak = { dv: s.sim.dv, ok: s.sim.ok, bit: s.sim.bit };
  s = setv('l11', { mode: 'ret1', cs: 25e-15, cbl: 150e-15, voff: 0.02, vth: 0.6, vwl: 0, tr: 1, vpp: 2.0 }); R.l11ret = { tret: s.rt.r.tret, i0: s.i0, vsn: s.vsn, vlim: s.rt.r.vlim };
  s = setv('l11', { mode: 'ret1', vth: 0.5, vwl: -0.4, blhold: 'worst' }); R.l11ret2 = { tret: s.rt.r.tret, i0: s.i0 };
  s = setv('l11', { mode: 'ret1', vth: 0.6, vwl: 0, blhold: 'pre' }); R.l11ret3 = { tret: s.rt.r.tret };
  s = setv('l11', { mode: 'ret0', vth: 0.5, vwl: 0, blhold: 'worst' }); R.l11ret0 = { tret: s.rt.r.tret, vend: s.rt.r.vs[s.rt.r.vs.length - 1] };
  s = setv('l11', { mode: 'ret1', vth: 0.5, vpp: 1.2 }); R.l11low = { tret: s.rt.r.tret, vh: s.vh };
} catch (e) { errs.push('probe: ' + e.stack); }
document.getElementById('out').textContent = JSON.stringify({ errs, R });
"""


def _harness(tmp_path):
    js = "\n".join((ROOT / "textbook" / "js" / f).read_text(encoding="utf-8") for f in JS_FILES)
    css = (ROOT / "textbook" / "css" / "ia.css").read_text(encoding="utf-8")
    data = ROOT / "examples" / "out" / "lesson7_data.json"
    d7 = data.read_text(encoding="utf-8") if data.exists() else None
    boxes = "".join(f'<div id="ia-{k}"></div>' for k in ["l1", "l2", "l3", "l4", "l5", "l6", "l7", "l9", "l10", "l11"])
    page = (f"<!doctype html><meta charset=utf-8><style>:root{{--line:#ddd;--card:#fff;--acc:#123;--fg:#111;--mut:#555;--info:#eef}}body{{width:1200px}}{css}</style>"
            f"<body>{boxes}<pre id=out></pre>" + (f'<script type="application/json" id="ia-data-l7">{d7}</script>' if d7 else
                                                    '<script type="application/json" id="ia-data-l7">{"curves":{"vgs":[0.6,0.8,1.0,1.2,1.4],"vds":[0,1],"mini":[[0,1],[0,1],[0,1],[0,1],[0,1]],"ng":[[0,1],[0,1],[0,1],[0,1],[0,1]]},'
                                                    '"vtc":{"vin":[0,1],"mini":[0,1],"ng":[0,1]},"tran":{"t":[0,1],"vin":[0,1],"mini":[0,1],"ng":[0,1],"idd_mini":[0,1],"idd_ng":[0,1]},'
                                                    '"ring":{"t":[0,1],"mini":[[0,1],[0,1],[0,1],[0,1],[0,1]],"ng":[[0,1],[0,1],[0,1],[0,1],[0,1]]}}</script>')
            + f"<script>{js}\n{PROBE}</script>")
    f = tmp_path / "probe.html"
    f.write_text(page, encoding="utf-8")
    return f, d7


@pytest.fixture(scope="module")
def widgets(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("ia")
    f, d7 = _harness(tmp)
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=20000", "--dump-dom", f"file://{f}"], capture_output=True, text=True, timeout=240)
    m = re.search(r'<pre id="out">(.*?)</pre>', r.stdout, re.S)
    assert m, r.stdout[-500:] + r.stderr[-500:]
    out = json.loads(html.unescape(m.group(1)))
    assert out["errs"] == [], out["errs"]
    out["has_l7_data"] = d7 is not None
    return out


def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-300)


def test_lesson1(widgets):
    R = widgets["R"]
    m = Level1(1, dict(vto=0.5, kp=300e-6, lambda_=0.05))
    i, gd, gg, *_ = m.evaluate(1.8, 1.0, 0, 0, 1e-6, 0.18e-6)
    assert rel(R["l1"]["id"], i) < 1e-9 and rel(R["l1"]["gm"], gg) < 1e-9 and rel(R["l1"]["gds"], gd) < 1e-9
    m = Level1(1, dict(vto=0.6, kp=300e-6, lambda_=0.1))
    i, gd, gg, *_ = m.evaluate(0.3, 1.4, 0, 0, 1e-6, 0.18e-6)
    assert rel(R["l1b"]["id"], i) < 1e-9 and rel(R["l1b"]["gds"], gd) < 1e-9
    assert R["l1b"]["region"] == "triode"


def test_lesson2(widgets):
    R = widgets["R"]
    net = "t\n.model n nmos level=1 vto=0.5 kp=300u lambda=0.05\nVdd vdd 0 1.8\nVg g 0 1.4\nRd vdd d 5k\nM1 d g 0 0 n W=1u L=0.18u\n.end\n"
    assert abs(R["l2"]["star"] - op(parse(net)[0])["v(d)"][0]) < 1e-8
    assert abs(R["l2"]["first"] - 0.211765) < 1e-5 and R["l2"]["n"] in (4, 5, 6)        # the hand iteration of lesson 2
    net = "t\n.model n nmos level=1 vto=0.7 kp=300u lambda=0.05\nVdd vdd 0 3.0\nVg g 0 1.0\nRd vdd d 20000\nM1 d g 0 0 n W=2u L=0.18u\n.end\n"
    assert abs(R["l2b"]["star"] - op(parse(net)[0])["v(d)"][0]) < 1e-8


def _cross(t, v, lvl, rising, t0=0.0):
    for i in range(1, len(t)):
        if t[i] >= t0 and ((v[i - 1] < lvl <= v[i]) if rising else (v[i - 1] > lvl >= v[i])):
            return t[i - 1] + (lvl - v[i - 1]) / (v[i] - v[i - 1]) * (t[i] - t[i - 1])


def test_lesson3(widgets):
    R = widgets["R"]["l3"]
    net = ("t\n.model n nmos level=1 vto=0.5 kp=300u lambda=0.05\nVdd vdd 0 1.8\nVg g 0 PULSE(0 1.4 1n 0.1n 0.1n 3n 8n)\nRd vdd d 5k\nCL d 0 100f\nM1 d g 0 0 n W=1u L=0.18u\n.end\n")
    r = transient(parse(net)[0], 20e-12, 8e-9, method="be")
    t, v = r.axis, r["v(d)"]
    vlow = v[int(round(4e-9 / 20e-12))]
    sw = 1.8 - vlow
    fall = _cross(t, v, vlow + 0.1 * sw, False, 1e-9) - _cross(t, v, vlow + 0.9 * sw, False, 1e-9)
    rise = _cross(t, v, vlow + 0.9 * sw, True, 4.1e-9) - _cross(t, v, vlow + 0.1 * sw, True, 4.1e-9)
    assert abs(R["vlow"] - vlow) < 2e-4 and abs(R["fall"] - fall) < 2e-12 and abs(R["rise"] - rise) < 4e-12


def test_lesson4(widgets):
    R = widgets["R"]
    net = ("t\n.model nch nmos level=1 vto=0.5 kp=300u lambda=0.05\n.model pch pmos level=1 vto=-0.5 kp=100u lambda=0.05\nVdd vdd 0 1.8\nVin in 0 0\n"
           "M1 out in 0 0 nch W=1u L=0.18u\nM2 out in vdd vdd pch W=3u L=0.18u\n.end\n")
    c = parse(net)[0]
    r = dc_sweep(c, "vin", 0.8, 1.0, 0.0002)
    vm = float(np.interp(0.0, (r["v(out)"] - r.axis)[::-1], r.axis[::-1]))
    gain = float(np.max(np.abs(np.gradient(r["v(out)"], r.axis))))
    assert abs(R["l4"]["vm"] - vm) < 2e-4 and abs(R["l4"]["gain"] - gain) / gain < 0.02
    assert abs(R["l4"]["gain"] - R["l4"]["hand"]) / R["l4"]["hand"] < 1e-3         # numeric derivative = (gmn+gmp)/(gdsn+gdsp)
    tr = (net.replace("Vin in 0 0", "Vin in 0 PULSE(0 1.8 0.2n 0.1n 0.1n 0.8n 2n)").replace("\n.end", "\nCL out 0 20f\n.end"))
    rr = transient(parse(tr)[0], 5e-12, 4e-9)
    tphl = _cross(rr.axis, rr["v(out)"], 0.9, False) - _cross(rr.axis, rr["v(in)"], 0.9, True)
    assert abs(R["l4"]["tphl"] - tphl) < 0.5e-12
    # a changed configuration: Vdd 1.2 V, Wp/Wn = 2, Vtn 0.4, |Vtp| 0.45, Vin 0.55 V
    net2 = (f"t\n.model nch nmos level=1 vto=0.4 kp=300u lambda=0.05\n.model pch pmos level=1 vto=-0.45 kp=100u lambda=0.05\nVdd vdd 0 1.2\nVin in 0 0\n"
            "M1 out in 0 0 nch W=1u L=0.18u\nM2 out in vdd vdd pch W=2u L=0.18u\n.end\n")
    r2 = dc_sweep(parse(net2)[0], "vin", 0.0, 1.2, 0.0005)
    assert abs(R["l4b"]["vout"] - float(np.interp(0.55, r2.axis, r2["v(out)"]))) < 5e-4


def test_lesson5(widgets):
    R = widgets["R"]["l5"]
    m = EKV(1, dict(vto=0.5, kp=300e-6, n=1.3, lambda_=0.05))
    assert rel(R["id"], m.evaluate(1.8, 0.2, 0, 0, 1e-6, 0.18e-6)[0]) < 1e-9
    assert abs(R["v01"] - 0.433) < 0.002 and abs(R["v10"] - 0.710) < 0.002              # the IC boundaries quoted in lesson 5


def test_lesson6(widgets):
    R = widgets["R"]
    m = EKV(1, dict(vto=0.5, kp=300e-6, n=1.0, lambda_=0.0, cox=8.63e-3))
    w, l = 1e-6, 0.18e-6
    CG = 8.63e-3 * w * l
    for key, vds in (("l6", 0.0), ("l6b", 2.0)):                      # the widget against minispice at the same bias (strict) ...
        _, c = m.charge_jac(vds, 1.8, 0, 0, w, l)
        ref = dict(gg=c[1][1] / CG, gs=-(c[1][2] + c[1][3]) / CG, gd=-c[1][0] / CG)
        for k in ref:
            assert abs(R[key][k] - ref[k]) < 1e-9, (key, k, R[key][k], ref[k])
    # ... and against the textbook numbers (finite inversion makes them hold to ~1e-3, not exactly)
    assert abs(R["l6"]["gg"] - 1.0) < 1e-3 and abs(R["l6"]["gs"] - 0.5) < 1e-3 and abs(R["l6"]["gd"] - 0.5) < 1e-3
    assert abs(R["l6b"]["gg"] - 2 / 3) < 1e-3 and abs(R["l6b"]["gs"] - 2 / 3) < 1e-3 and abs(R["l6b"]["gd"]) < 1e-3


def _metrics(m, w, l, vdd=0.8):
    ev = lambda vd, vg: m.evaluate(vd, vg, 0, 0, w, l)[0]
    ss = 0.1 / (math.log10(ev(0.1, 0.1)) - math.log10(ev(0.1, 0.0))) * 1e3
    icc = 1e-7 * w / l

    def vt(vds):
        lo, hi = -0.5, 1.5
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if ev(vds, mid) < icc else (lo, mid)
        return 0.5 * (lo + hi)
    return dict(ss=ss, dibl=(vt(0.1) - vt(vdd)) / (vdd - 0.1) * 1e3, ioff=ev(vdd, 0.0), ion=ev(vdd, vdd))


def test_lesson9(widgets):
    R = widgets["R"]
    assert R["l9"]["weff"] == 2 * (2 * 34 + 8) and R["l9b"]["weff"] == 3 * (2 * 50 + 6)
    m = EKV(1, dict(vto=0.35, kp=300e-6, n=1.15, lambda_=0.05, eta=0.04))
    ref = _metrics(m, 152e-9, 20e-9)
    for k in ("ss", "dibl", "ioff", "ion"):
        assert rel(R["l9"][k], ref[k]) < 1e-6, (k, R["l9"][k], ref[k])
    m2 = EKV(1, dict(vto=0.35, kp=300e-6, n=1.3, lambda_=0.05, eta=0.08))
    assert rel(R["l9b"]["ioff"], _metrics(m2, 3 * (2 * 50 + 6) * 1e-9, 14e-9)["ioff"]) < 1e-6      # W_eff = N(2H + W_fin)
    assert abs(R["l9"]["ss"] - 1.15 * VT * math.log(10) * 1e3) < 1.0                      # the hand formula n*Vt*ln10


def _inverter_gain(n, eta, w, l, vdd=0.8, vto=0.35):
    net = (f"t\n.model nch nmos level=ekv vto={vto} kp=300u lambda=0.05 n={n} eta={eta}\n.model pch pmos level=ekv vto=-{vto} kp=100u lambda=0.05 n={n} eta={eta}\n"
           f"Vdd vdd 0 {vdd}\nVin in 0 0\nM1 out in 0 0 nch W={w} L={l}\nM2 out in vdd vdd pch W={3 * w} L={l}\n.end\n")
    c = parse(net)[0]
    r = dc_sweep(c, "vin", 0.3, 0.5, 2e-5)
    vm = float(np.interp(0.0, (r["v(out)"] - r.axis)[::-1], r.axis[::-1]))
    return float(np.max(np.abs(np.gradient(r["v(out)"], r.axis)))), vm


def test_lesson10(widgets):
    R = widgets["R"]
    assert R["l10"]["weff"] == 3 * 2 * (30 + 5) and R["l10b"]["weff"] == 4 * 2 * (20 + 4)
    for key, (n, eta) in {"planar": (1.45, 0.10), "fin": (1.15, 0.04), "gaa": (1.08, 0.02)}.items():
        gain, vm = _inverter_gain(n, eta, 210e-9, 20e-9)
        assert abs(R["l10"][key] - gain) / gain < 0.01, (key, R["l10"][key], gain)
    vm = R["l10"]["vm"]
    assert isinstance(vm, float) and 0.3 < vm < 0.5, vm                                       # a finite Vm (not a runaway bracket or NaN)
    # the lesson-10 text quotes gains 9.7 / 23.4 / 44.5
    assert abs(R["l10"]["planar"] - 9.7) < 0.1 and abs(R["l10"]["fin"] - 23.4) < 0.1 and abs(R["l10"]["gaa"] - 44.5) < 0.1


def test_lesson7_embedded_data(widgets):
    if not widgets["has_l7_data"]:
        pytest.skip("examples/out/lesson7_data.json not generated (needs ngspice; run the lesson 7 script)")
    d = json.loads((ROOT / "examples" / "out" / "lesson7_data.json").read_text())
    ref = max(abs(b - a) for a, b in zip(d["curves"]["mini"][4], d["curves"]["ng"][4]))
    assert abs(widgets["R"]["l7"]["dmax"] - ref) < 1e-15


def test_lesson11(widgets):
    import sys
    sys.path.insert(0, str(ROOT / "examples"))
    from dram_retention import retention
    R = widgets["R"]
    assert R["l4switch"] == "tran" and R["plotLog"] == [False, False]                  # a linear plot after a log plot must not inherit the log axis (it threw "Invalid array length" in lesson 4 DC -> transient)
    # default state: stored 1 read at 3.9 ns, just before the sense amplifier fires: charge sharing = the hand formula
    r = R["l11"]
    hand = (1.2 - 0.6) * 25e-15 / (25e-15 + 150e-15)
    assert abs(r["dv"] - hand) < 2e-6 and abs(r["dvHand"] - hand) < 1e-12 and abs(r["bl"] - (0.6 + hand)) < 2e-6 and abs(r["sn"] - (0.6 + hand)) < 2e-6   # BL and SN meet
    assert r["ok"] is True and abs(r["tau"] - 150e-15 / 2e-3) < 1e-15 and r["vh"] == 1.2
    # write level min(Vdd, Vpp - Vth) at 8.5 ns, against minispice
    for key, vpp in (("l11w", 1.9), ("l11w2", 2.0)):
        net = (f"t\n.model nacc nmos level=1 vto=0.7 kp=300u lambda=0.05\nVbl bl 0 PULSE(0 1.2 0.5n 0.1n 0.1n 8n 40n)\nVwl wl 0 PULSE(0 {vpp} 1n 0.2n 0.2n 16n 40n)\nM1 bl wl sn 0 nacc W=0.1u L=0.1u\nCs sn 0 25f\n.end\n")
        t = transient(parse(net)[0], 10e-12, 8.5e-9)
        assert abs(R[key]["sn"] - t["v(sn)"][-1]) < 2e-4, (key, R[key]["sn"], t["v(sn)"][-1])
    assert abs(R["l11w"]["vh"] - 1.2) < 1e-12 and R["l11w"]["sn"] < 1.2 - 0.01          # Vpp = 1.9 < Vdd + Vth = 1.9 + : still creeping towards Vdd (tail)
    # read 0 with a 30 mV offset against the data: margin 38.3 - 30 mV > 0 -> correct; weak cell (10 fF, 300 fF, 60 mV offset) -> wrong decision
    assert abs(R["l11r0"]["dv"] - (-0.6 * 15 / 235)) < 2e-6 and R["l11r0"]["ok"] is True and R["l11r0"]["bit"] == 0
    assert abs(R["l11weak"]["dv"] - 0.6 * 10 / 310) < 2e-6 and R["l11weak"]["ok"] is False and R["l11weak"]["bit"] == 0
    # retention against the Python ODE and an independent EKV evaluation of the leakage current
    py = retention(0.6, 0.0, True)
    assert abs(R["l11ret"]["tret"] - py["tret"]) / py["tret"] < 1e-9 and abs(R["l11ret"]["vlim"] - py["vlim"]) < 1e-12
    m = EKV(1, dict(vto=0.6, kp=300e-6, n=1.3, lambda_=0.05))
    i0 = abs(m.evaluate(0.0, 0.0, 1.2, 0.0, 1e-7, 1e-7)[0]) + 0.2e-15 * (1 - math.exp(-1.2 / VT))
    assert rel(R["l11ret"]["i0"], i0) < 1e-9
    ts, vs = np.array(py["ts"][1:]), np.array(py["vs"][1:])                          # V(SN) after 1 s: the decay accelerates towards t_ret = 1.157 s (0.80 V, not 1.2 V)
    assert abs(R["l11ret"]["vsn"] - float(np.interp(0.0, np.log10(ts), vs))) < 1e-9 and py["vlim"] < R["l11ret"]["vsn"] < 1.2 - 0.1
    assert abs(R["l11ret2"]["tret"] - retention(0.5, -0.4, True)["tret"]) / R["l11ret2"]["tret"] < 1e-9
    assert abs(R["l11ret3"]["tret"] - retention(0.6, 0.0, True, vbl="pre")["tret"]) / R["l11ret3"]["tret"] < 1e-9
    py0 = retention(0.5, 0.0, False)                                                  # a stored 0 does not reach its sensing limit (0.46 V) within the 1e6 s window: Vgs = -V(SN) throttles the leakage
    assert R["l11ret0"]["tret"] is None and py0["tret"] == float("inf") and abs(R["l11ret0"]["vend"] - py0["vs"][-1]) < 1e-12 and R["l11ret0"]["vend"] < py0["vlim"]
    assert R["l11low"]["tret"] == 0 and abs(R["l11low"]["vh"] - 0.7) < 1e-12            # Vpp = 1.2 V, Vth = 0.5 V -> level 0.7 V is already below the 0.74 V sensing limit

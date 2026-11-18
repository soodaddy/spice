"""The interactive widgets run the models in JavaScript (textbook/js/core.js). This test compares that port with minispice."""

import json
import pathlib
import shutil
import subprocess

import numpy as np
import pytest

from minispice import EKV, Level1, dc_sweep, parse, transient

ROOT = pathlib.Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def _models(rng):
    cases = []
    specs = [
        ("level1", 1, dict(vto=0.5, kp=300e-6, lambda_=0.05, gamma=0.4, phi=0.7), 1e-6, 0.18e-6),
        ("level1", -1, dict(vto=-0.5, kp=100e-6, lambda_=0.05, gamma=0.4, phi=0.7), 3e-6, 0.18e-6),
        ("ekv", 1, dict(vto=0.5, kp=300e-6, n=1.3, lambda_=0.05, eta=0.0, cox=8.63e-3), 1e-6, 0.18e-6),
        ("ekv", -1, dict(vto=-0.5, kp=100e-6, n=1.3, lambda_=0.05, eta=0.0, cox=8.63e-3), 3e-6, 0.18e-6),
        ("ekv", 1, dict(vto=0.35, kp=300e-6, n=1.15, lambda_=0.05, eta=0.04, cox=8.63e-3), 1e-6, 20e-9),
        ("ekv", -1, dict(vto=-0.35, kp=100e-6, n=1.08, lambda_=0.05, eta=0.02, cox=8.63e-3), 3e-6, 20e-9),
    ]
    for kind, pol, params, w, l in specs:
        py = {k: v for k, v in params.items()}
        cls = Level1 if kind == "level1" else EKV
        m = cls(pol, py)
        for _ in range(60):
            v = [float(x) for x in rng.uniform(-1.5, 1.5, 4)]
            i, gd, gg, gs, gb = m.evaluate(*v, w, l)
            case = dict(kind=kind, pol=pol, params={("lambda" if k == "lambda_" else k): x for k, x in params.items()}, v=v, w=w, l=l,
                        out=dict(id=i, gd=gd, gg=gg, gs=gs, gb=gb))
            if kind == "ekv":
                case["q"] = [float(x) for x in m.charges(*v, w, l)]
            cases.append(case)
    return cases


def _reference():
    rng = np.random.default_rng(7)
    ref = {"models": _models(rng), "rd": [], "inv": [], "tran_rd": [], "tran_inv": []}
    # NMOS + Rd (lesson 2)
    for vdd, vg, rd, vto, w, l in [(1.8, 1.4, 5e3, 0.5, 1e-6, 0.18e-6), (3.0, 1.0, 20e3, 0.7, 2e-6, 0.5e-6), (1.0, 0.45, 1e3, 0.3, 1e-6, 0.18e-6), (2.5, 2.0, 1e3, 0.5, 5e-6, 0.18e-6)]:
        net = f"t\n.model n nmos level=1 vto={vto} kp=300u lambda=0.05\nVdd vdd 0 {vdd}\nVg g 0 {vg}\nRd vdd d {rd}\nM1 d g 0 0 n W={w} L={l}\n.end\n"
        from minispice import op
        vd = float(op(parse(net)[0])["v(d)"][0])
        ref["rd"].append(dict(params=dict(vto=vto, kp=300e-6, lambda_=0.05), vdd=vdd, vg=vg, rd=rd, w=w, l=l, vd=vd))
    for c in ref["rd"]:
        c["params"] = {("lambda" if k == "lambda_" else k): v for k, v in c["params"].items()}
    # inverter VTC (lesson 4)
    for vdd, wn, wp, vtn, vtp in [(1.8, 1e-6, 3e-6, 0.5, 0.5), (1.2, 1e-6, 2e-6, 0.4, 0.45), (3.0, 2e-6, 3e-6, 0.7, 0.7)]:
        net = (f"t\n.model nch nmos level=1 vto={vtn} kp=300u lambda=0.05\n.model pch pmos level=1 vto=-{vtp} kp=100u lambda=0.05\n"
               f"Vdd vdd 0 {vdd}\nVin in 0 0\nM1 out in 0 0 nch W={wn} L=0.18u\nM2 out in vdd vdd pch W={wp} L=0.18u\n.end\n")
        r = dc_sweep(parse(net)[0], "vin", 0.0, vdd, vdd / 90)
        ref["inv"].append(dict(pn=dict(vto=vtn, kp=300e-6, **{"lambda": 0.05}), pp=dict(vto=-vtp, kp=100e-6, **{"lambda": 0.05}), vdd=vdd, wn=wn, wp=wp, l=0.18e-6,
                               vin=r.axis.tolist(), vout=r["v(out)"].tolist()))
    # lesson 3 transient (NMOS + Rd + CL)
    for method, rd, cl, vgh in [("be", 5e3, 100e-15, 1.4), ("trap", 5e3, 100e-15, 1.4), ("trap", 10e3, 50e-15, 1.0), ("be", 2e3, 200e-15, 1.8)]:
        net = f"t\n.model n nmos level=1 vto=0.5 kp=300u lambda=0.05\nVdd vdd 0 1.8\nVg g 0 PULSE(0 {vgh} 1n 0.1n 0.1n 3n 8n)\nRd vdd d {rd}\nCL d 0 {cl}\nM1 d g 0 0 n W=1u L=0.18u\n.end\n"
        r = transient(parse(net)[0], 20e-12, 8e-9, method=method)
        idx = list(range(0, len(r.axis), 7))
        ref["tran_rd"].append(dict(method=method, params=dict(vto=0.5, kp=300e-6, **{"lambda": 0.05}), vdd=1.8, rd=rd, cl=cl, w=1e-6, l=0.18e-6, tstep=20e-12, tstop=8e-9,
                                   pulse=dict(v1=0, v2=vgh, td=1e-9, tr=0.1e-9, tf=0.1e-9, pw=3e-9, per=8e-9), idx=idx, v=[float(r["v(d)"][i]) for i in idx]))
    # lesson 4 transient (inverter + CL)
    for method, wp, cl in [("trap", 3e-6, 20e-15), ("be", 2e-6, 50e-15)]:
        net = (f"t\n.model nch nmos level=1 vto=0.5 kp=300u lambda=0.05\n.model pch pmos level=1 vto=-0.5 kp=100u lambda=0.05\nVdd vdd 0 1.8\n"
               f"Vin in 0 PULSE(0 1.8 0.2n 0.1n 0.1n 0.8n 2n)\nM1 out in 0 0 nch W=1u L=0.18u\nM2 out in vdd vdd pch W={wp} L=0.18u\nCL out 0 {cl}\n.end\n")
        r = transient(parse(net)[0], 5e-12, 4e-9, method=method)
        idx = list(range(0, len(r.axis), 11))
        ref["tran_inv"].append(dict(method=method, pn=dict(vto=0.5, kp=300e-6, **{"lambda": 0.05}), pp=dict(vto=-0.5, kp=100e-6, **{"lambda": 0.05}), vdd=1.8, wn=1e-6, wp=wp, l=0.18e-6,
                                    cl=cl, tstep=5e-12, tstop=4e-9, pulse=dict(v1=0, v2=1.8, td=0.2e-9, tr=0.1e-9, tf=0.1e-9, pw=0.8e-9, per=2e-9), idx=idx, v=[float(r["v(out)"][i]) for i in idx]))
    return ref


def _dram_reference():
    """Lesson 11: write transient, charge sharing (minispice netlists with the same timing) and the retention ODE (examples/dram_retention.py)."""
    import sys
    sys.path.insert(0, str(ROOT / "examples"))
    from dram_retention import retention
    out = {"write": [], "share": [], "ret": []}
    for vpp, vth in ((2.0, 0.7), (1.9, 0.7), (1.2, 0.7), (2.5, 0.6)):
        net = (f"t\n.model nacc nmos level=1 vto={vth} kp=300u lambda=0.05\nVbl bl 0 PULSE(0 1.2 0.5n 0.1n 0.1n 8n 40n)\nVwl wl 0 PULSE(0 {vpp} 1n 0.2n 0.2n 16n 40n)\n"
               "M1 bl wl sn 0 nacc W=0.1u L=0.1u\nCs sn 0 25f\n.end\n")
        r = transient(parse(net)[0], 10e-12, 8.5e-9)
        idx = list(range(0, len(r.axis), 5))
        out["write"].append(dict(vpp=vpp, vth=vth, idx=idx, sn=[float(r["v(sn)"][i]) for i in idx]))
    for vcell, vpp, vth, cs, cbl in ((1.2, 2.0, 0.7, 25e-15, 150e-15), (0.0, 2.0, 0.7, 25e-15, 150e-15), (1.2, 2.0, 0.5, 15e-15, 220e-15)):
        net = (f"t\n.model nacc nmos level=1 vto={vth} kp=300u lambda=0.05\n.model nsw nmos level=1 vto=0.5 kp=300u lambda=0.05\nVblp vblp 0 0.6\nVcell vcell 0 {vcell}\n"
               f"Veq eq 0 PULSE({vpp} 0 0.3n 0.1n 0.1n 100n 200n)\nVwl wl 0 PULSE(0 {vpp} 1n 0.2n 0.2n 20n 40n)\nMeq bl eq vblp 0 nsw W=1u L=0.1u\nMwr sn eq vcell 0 nsw W=1u L=0.1u\n"
               f"Macc bl wl sn 0 nacc W=0.1u L=0.1u\nCbl bl 0 {cbl}\nCs sn 0 {cs}\n.end\n")
        r = transient(parse(net)[0], 10e-12, 3.9e-9)
        idx = list(range(110, len(r.axis), 10))
        out["share"].append(dict(vcell=vcell, vpp=vpp, vth=vth, cs=cs, cbl=cbl, idx=idx, bl=[float(r["v(bl)"][i]) for i in idx], sn=[float(r["v(sn)"][i]) for i in idx]))
    for vth, vwl, d1, vbl in ((0.5, 0.0, True, None), (0.7, 0.0, True, None), (0.5, -0.3, True, None), (0.6, 0.0, True, "pre"), (0.5, 0.0, False, None), (0.7, -0.2, True, None)):
        r = retention(vth, vwl, d1, vbl=vbl)
        out["ret"].append(dict(vth=vth, vwl=vwl, data1=d1, vbl=vbl, tret=None if r["tret"] == float("inf") else r["tret"], v_end=r["vs"][-1], n=len(r["ts"])))
    return out


def test_js_dram_matches_minispice(tmp_path):
    ref = _dram_reference()
    f = tmp_path / "dram.json"
    f.write_text(json.dumps(ref))
    r = subprocess.run([NODE, str(ROOT / "tests" / "js_parity.js"), str(f), "dram"], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["write"]["max_abs_dv"] < 2e-4, out["write"]                     # same equations, same time grid -> agreement far below the ~10 mV effects the lesson discusses
    assert out["share"]["max_abs_dv"] < 5e-4, out["share"]
    assert out["write"]["cases"] == 4 and out["share"]["cases"] == 3
    assert out["ret"]["max_rel_dt"] is not None and out["ret"]["max_rel_dt"] < 1e-9, out["ret"]                         # the JS retention ODE mirrors the Python one step by step
    assert out["ret"]["cases"] == 6 and out["ret"]["finite_cases"] == 5


def test_js_port_matches_minispice(tmp_path):
    ref = _reference()
    f = tmp_path / "ref.json"
    f.write_text(json.dumps(ref))
    r = subprocess.run([NODE, str(ROOT / "tests" / "js_parity.js"), str(f)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    m = out["models"]
    assert m["id"] < 1e-9 and max(m["gd"], m["gg"], m["gs"], m["gb"]) < 1e-9, m
    assert m["q"] < 1e-9, m
    assert out["rd"]["max_abs_dv"] < 1e-6, out["rd"]
    assert out["inv"]["max_abs_dv"] < 1e-6, out["inv"]
    assert out["tran_rd"]["max_abs_dv"] < 2e-4, out["tran_rd"]
    assert out["tran_inv"]["max_abs_dv"] < 2e-4, out["tran_inv"]
    assert out["profile"]["violations"] == 0, out["profile"]

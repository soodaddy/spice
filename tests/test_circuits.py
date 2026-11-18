import math

import numpy as np
import pytest

from minispice import Circuit, Pulse, dc_sweep, op, parse, transient

INVERTER = """CMOS inverter
.model nch nmos level=1 vto=0.5 kp=300u lambda=0.05
.model pch pmos level=1 vto=-0.5 kp=100u lambda=0.05
Vdd vdd 0 1.8
Vin in 0 PULSE(0 1.8 1n 0.1n 0.1n 2n 5n)
M1 out in 0 0 nch W=1u L=0.18u
M2 out in vdd vdd pch W=3u L=0.18u
CL out 0 10f
.dc Vin 0 1.8 0.01
.tran 10p 10n
.end
"""


def test_resistor_divider():
    c = Circuit()
    c.add_vsource("v1", "a", "0", 10.0)
    c.add_resistor("r1", "a", "b", 1e3)
    c.add_resistor("r2", "b", "0", 3e3)
    r = op(c)
    assert r["v(b)"][0] == pytest.approx(7.5)
    assert r["i(v1)"][0] == pytest.approx(-10 / 4e3)  # SPICE sign: supply current is negative


@pytest.mark.parametrize("method,tol", [("be", 2e-2), ("trap", 1e-4)])
def test_rc_step_response(method, tol):
    c = Circuit()
    c.add_vsource("v1", "in", "0", 0.0, Pulse(0, 1, 0, 1e-12, 1e-12, 1.0))
    c.add_resistor("r1", "in", "out", 1e3)
    c.add_capacitor("c1", "out", "0", 1e-9)
    tau = 1e-6
    r = transient(c, tau / 50, 5 * tau, method=method)
    expect = 1 - np.exp(-(r.axis - 1e-12) / tau)
    assert np.max(np.abs(r["v(out)"] - expect)) < tol


def test_nmos_resistor_load_matches_analytic():
    vdd, rl, vin = 5.0, 10e3, 3.0
    kp, w, l, vto = 100e-6, 10e-6, 1e-6, 1.0
    beta = kp * w / l
    c = Circuit()
    c.models["n"] = __import__("minispice").Level1(1, dict(vto=vto, kp=kp))
    c.add_vsource("vdd", "vdd", "0", vdd)
    c.add_vsource("vin", "g", "0", vin)
    c.add_resistor("rl", "vdd", "d", rl)
    c.add_mosfet("m1", "d", "g", "0", "0", "n", w=w, l=l)
    # triode: (vdd - vd)/rl = beta*((vin-vto) - vd/2)*vd  -> quadratic in vd
    vov = vin - vto
    a, b, cc = beta * 0.5, -(beta * vov + 1 / rl), vdd / rl
    vd = (-b - math.sqrt(b * b - 4 * a * cc)) / (2 * a)
    assert vd < vov  # really triode
    assert op(c)["v(d)"][0] == pytest.approx(vd, rel=1e-6)


@pytest.mark.parametrize("level", ["1", "ekv"])
def test_inverter_vtc(level):
    text = INVERTER.replace("level=1", f"level={level}")
    c, analyses = parse(text)
    (_, dc_args) = analyses[0]
    r = dc_sweep(c, *dc_args)
    vin, vout = r.axis, r["v(out)"]
    assert vout[0] == pytest.approx(1.8, abs=1e-3)
    assert vout[-1] == pytest.approx(0.0, abs=1e-3)
    assert np.all(np.diff(vout) <= 1e-9)  # monotonic
    vm = vin[np.argmin(np.abs(vout - vin))]  # switching threshold
    assert 0.6 < vm < 1.2


def test_inverter_transient_switches():
    c, analyses = parse(INVERTER)
    r = transient(c, *analyses[1][1])
    t, vout = r.axis, r["v(out)"]
    assert vout[0] == pytest.approx(1.8, abs=1e-3)
    assert vout[np.searchsorted(t, 2.5e-9)] < 0.05   # input high -> output low
    assert vout[np.searchsorted(t, 4.5e-9)] > 1.75   # input low again -> output high
    assert vout.min() > -0.05 and vout.max() < 1.85   # no big over/undershoot


def test_vdd_current_is_zero_when_output_settled():
    c, _ = parse(INVERTER)
    r = op(c)
    assert abs(r["i(vdd)"][0]) < 1e-9  # only leakage (gmin) in static CMOS

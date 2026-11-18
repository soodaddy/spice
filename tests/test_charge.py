"""Tests of the EKV channel-charge model.

Capacitances are ~1e-14 F, so every comparison is made on values normalised by CG = Cox*W*L.
(pytest.approx has a default absolute tolerance of 1e-12, which would make raw-farad checks vacuous.)
"""

import numpy as np
import pytest

from minispice import EKV, Circuit, Pulse, transient

D, G, S, B = range(4)                  # terminal order everywhere: charges rows and voltage columns
COX = 8.63e-3                          # F/m^2  (tox ~ 4 nm)
W, L = 10e-6, 1e-6                     # a long-ish device so the long-channel formulas apply
CG = COX * W * L                       # total gate capacitance
NEKV = EKV(1, dict(vto=0.5, kp=300e-6, n=1.3, cox=COX))
N1 = EKV(1, dict(vto=0.5, kp=300e-6, n=1.0, cox=COX))   # n = 1: no body effect -> textbook values
PEKV = EKV(-1, dict(vto=-0.5, kp=100e-6, n=1.3, cox=COX))


def cn(m, vd, vg, vs, vb):
    """Capacitance matrix in units of CG."""
    return m.charge_jac(vd, vg, vs, vb, W, L)[1] / CG


def test_charges_sum_to_zero():
    for m in (NEKV, PEKV):
        for v in ([1.0, 1.5, 0.0, 0.0], [0.0, 1.5, 1.0, 0.0], [0.3, 0.2, 0.0, 0.0], [-1.0, -1.5, 0.0, 0.0]):
            assert sum(m.charges(*v, W, L)) / (CG * 1.0) == pytest.approx(0.0, abs=1e-9)


def test_capacitance_rows_and_columns_sum_to_zero():
    c = cn(NEKV, 1.0, 1.5, 0.0, 0.0)
    assert np.abs(c.sum(axis=0)).max() < 1e-6   # charge conservation: the four charges always sum to 0
    assert np.abs(c.sum(axis=1)).max() < 1e-6   # only voltage differences matter


def test_strong_inversion_saturation_ward_dutton():
    # Vgs = 2.5 V, Vds = 3 V: long-channel saturation.
    c = cn(NEKV, 3.0, 2.5, 0.0, 0.0)
    cgg = c[G, G]
    cgs = -(c[G, S] + c[G, B])         # classical Cgs: source and bulk move together
    cgd = -c[G, D]
    assert cgg == pytest.approx(2 / 3, rel=0.01)
    assert cgs == pytest.approx(2 / 3, rel=0.01)
    assert cgd == pytest.approx(0.0, abs=0.01)
    qd, qg, qs, _ = NEKV.charges(3.0, 2.5, 0.0, 0.0, W, L)
    assert -qd / qg == pytest.approx(0.4, abs=0.005)    # Ward-Dutton 40/60 split
    assert -qs / qg == pytest.approx(0.6, abs=0.005)


def test_textbook_values_for_n_equal_one():
    sat = cn(N1, 3.0, 2.5, 0.0, 0.0)           # saturation: Cgs = 2/3, Cgd = 0, Cgb = 0
    assert -sat[G, S] == pytest.approx(2 / 3, rel=0.01)
    assert -sat[G, D] == pytest.approx(0.0, abs=0.01)
    assert sat[G, B] == pytest.approx(0.0, abs=1e-6)
    tri = cn(N1, 0.0, 2.5, 0.0, 0.0)           # Vds = 0: Cgs = Cgd = 1/2, Cgg = 1
    assert -tri[G, S] == pytest.approx(0.5, rel=0.01)
    assert -tri[G, D] == pytest.approx(0.5, rel=0.01)
    assert tri[G, G] == pytest.approx(1.0, rel=0.01)


def test_body_effect_scales_source_drain_derivatives_by_n():
    n = 1.3
    tri = cn(NEKV, 0.0, 2.5, 0.0, 0.0)
    assert tri[G, D] == pytest.approx(tri[G, S], rel=1e-6)        # symmetric at Vds = 0
    assert -tri[G, D] == pytest.approx(n * 0.5, rel=0.01)
    assert tri[G, B] == pytest.approx((n - 1) * tri[G, G], rel=0.01)  # no bulk charge modelled -> Cgb < 0


def test_weak_inversion_gate_sees_almost_no_inversion_charge():
    assert cn(NEKV, 1.0, 0.0, 0.0, 0.0)[G, G] < 1e-3


def test_source_drain_swap_symmetry():
    a = np.array(NEKV.charges(0.2, 1.5, 1.0, 0.0, W, L)) / CG
    b = np.array(NEKV.charges(1.0, 1.5, 0.2, 0.0, W, L)) / CG
    assert a[[G, D, S, B]] == pytest.approx(b[[G, S, D, B]], abs=1e-9)


def test_pmos_mirrors_nmos():
    n = np.array(NEKV.charges(0.4, 1.2, 0.0, 0.0, W, L)) / CG
    p = np.array(EKV(-1, dict(vto=-0.5, kp=300e-6, n=1.3, cox=COX)).charges(-0.4, -1.2, 0.0, 0.0, W, L)) / CG
    assert p == pytest.approx(-n, abs=1e-9)


@pytest.mark.parametrize("method", ["be", "trap"])
def test_transient_gate_charge_is_conserved(method):
    """Charge delivered by the gate source equals the change of the gate charge Qg."""
    c = Circuit()
    c.add_vsource("vd", "d", "0", 1.0)
    c.add_vsource("vg", "g", "0", 0.0, Pulse(0, 1.5, 0.1e-9, 0.1e-9, 0.1e-9, 1.0))
    c.add_mosfet("m1", "d", "g", "0", "0", NEKV, w=W, l=L)
    h = 5e-12
    r = transient(c, h, 1.0e-9, method=method)
    i_gate = -r["i(vg)"]                       # SPICE sign: a source that feeds the gate has negative i(v)
    delivered = np.trapezoid(i_gate, r.axis) if method == "trap" else np.sum(i_gate[1:]) * h
    qg = lambda k: NEKV.charges(r["v(d)"][k], r["v(g)"][k], 0.0, 0.0, W, L)[G]
    assert delivered / CG == pytest.approx((qg(-1) - qg(0)) / CG, rel=2e-3, abs=1e-4)
    assert abs(qg(-1) - qg(0)) / CG > 0.3      # make sure the comparison is not trivially about ~0


@pytest.mark.parametrize("method", ["be", "trap"])
def test_inverter_gate_charge_includes_both_devices(method):
    """CMOS input: delivered charge = dQg(NMOS) + dQg(PMOS). Catches terminal-order / sign mistakes."""
    n = EKV(1, dict(vto=0.5, kp=300e-6, n=1.3, cox=COX))
    p = EKV(-1, dict(vto=-0.5, kp=100e-6, n=1.3, cox=COX))
    c = Circuit()
    c.add_vsource("vdd", "vdd", "0", 1.8)
    c.add_vsource("vin", "in", "0", 0.0, Pulse(0, 1.8, 0.1e-9, 0.2e-9, 0.2e-9, 1.0))
    c.add_mosfet("mn", "out", "in", "0", "0", n, w=1e-6, l=0.18e-6)
    c.add_mosfet("mp", "out", "in", "vdd", "vdd", p, w=3e-6, l=0.18e-6)
    c.add_capacitor("cl", "out", "0", 5e-15)
    h = 2e-12
    r = transient(c, h, 0.8e-9, method=method)
    delivered = (np.trapezoid(-r["i(vin)"], r.axis) if method == "trap" else np.sum(-r["i(vin)"][1:]) * h)

    def qg(model, w, k, vs):
        return model.charges(r["v(out)"][k], r["v(in)"][k], vs, vs, w, 0.18e-6)[G]
    expect = (qg(n, 1e-6, -1, 0.0) - qg(n, 1e-6, 0, 0.0)) + (qg(p, 3e-6, -1, 1.8) - qg(p, 3e-6, 0, 1.8))
    assert expect > 5e-15                      # NMOS +2 fC, PMOS +6 fC
    assert delivered == pytest.approx(expect, rel=2e-2, abs=1e-17)

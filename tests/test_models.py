import random

import pytest

from minispice import EKV, Level1

NMOS1 = Level1(1, dict(vto=0.5, kp=300e-6, lambda_=0.05, gamma=0.4, phi=0.7))
PMOS1 = Level1(-1, dict(vto=-0.5, kp=100e-6, lambda_=0.05, gamma=0.4, phi=0.7))
NEKV = EKV(1, dict(vto=0.5, kp=300e-6, n=1.3, lambda_=0.05))
PEKV = EKV(-1, dict(vto=-0.5, kp=100e-6, n=1.3, lambda_=0.05))
MODELS = [NMOS1, PMOS1, NEKV, PEKV]
W, L = 2e-6, 0.18e-6


def _num_derivs(m, v, h=1e-6):
    out = []
    for k in range(4):
        hi, lo = list(v), list(v)
        hi[k] += h
        lo[k] -= h
        out.append((m.evaluate(*hi, W, L)[0] - m.evaluate(*lo, W, L)[0]) / (2 * h))
    return out


@pytest.mark.parametrize("model", MODELS)
def test_derivatives_match_finite_difference(model):
    rng = random.Random(1)
    for _ in range(300):
        v = [rng.uniform(-2, 2) for _ in range(4)]
        # keep Level 1 away from its (intentional) derivative kinks at cutoff/triode edge
        res = model.evaluate(*v, W, L)
        num = _num_derivs(model, v)
        scale = max(abs(x) for x in res[1:]) + 1e-12
        for a, b in zip(res[1:], num):
            assert a == pytest.approx(b, abs=2e-4 * scale + 1e-12)


@pytest.mark.parametrize("model", MODELS)
def test_derivatives_sum_to_zero(model):
    res = model.evaluate(1.1, 0.9, 0.2, 0.0, W, L)
    assert sum(res[1:]) == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("model", MODELS)
def test_source_drain_symmetry(model):
    # swapping D and S flips the sign of the current into the drain
    a = model.evaluate(0.3, 1.2, 1.0, 0.0, W, L)[0]
    b = model.evaluate(1.0, 1.2, 0.3, 0.0, W, L)[0]
    if model.p.get("lambda_"):
        pass  # CLM uses |vds| through the swap, so symmetry is exact
    assert a == pytest.approx(-b, rel=1e-12)


def test_level1_known_values():
    m = Level1(1, dict(vto=0.5, kp=200e-6))
    beta = 200e-6 * W / L
    # saturation: beta/2 * vov^2
    assert m.evaluate(1.8, 1.0, 0.0, 0.0, W, L)[0] == pytest.approx(0.5 * beta * 0.5**2)
    # triode: beta*(vov - vds/2)*vds
    assert m.evaluate(0.1, 1.0, 0.0, 0.0, W, L)[0] == pytest.approx(beta * (0.5 - 0.05) * 0.1)
    # cutoff
    assert m.evaluate(1.8, 0.3, 0.0, 0.0, W, L)[0] == 0.0


def test_pmos_mirrors_nmos():
    n = Level1(1, dict(vto=0.5, kp=1e-4, lambda_=0.02))
    p = Level1(-1, dict(vto=-0.5, kp=1e-4, lambda_=0.02))
    i_n = n.evaluate(0.8, 1.0, 0.0, 0.0, W, L)
    i_p = p.evaluate(-0.8, -1.0, 0.0, 0.0, W, L)
    assert i_p[0] == pytest.approx(-i_n[0])
    assert i_p[1:] == pytest.approx(i_n[1:])


def test_ekv_weak_inversion_slope():
    # below threshold: Id ~ exp(Vg / (n Vt)) -> one decade per n*Vt*ln(10) of Vg
    import math
    from minispice.models import VT
    m = EKV(1, dict(vto=0.5, kp=300e-6, n=1.3))
    i1 = m.evaluate(1.0, 0.10, 0.0, 0.0, W, L)[0]
    i2 = m.evaluate(1.0, 0.20, 0.0, 0.0, W, L)[0]
    swing = 0.10 / math.log10(i2 / i1)
    assert swing == pytest.approx(1.3 * VT * math.log(10), rel=0.01)


def test_ekv_strong_inversion_approaches_square_law():
    m = EKV(1, dict(vto=0.5, kp=300e-6, n=1.3))
    beta = 300e-6 * W / L
    vov = 1.0  # vgs - vto
    i = m.evaluate(2.0, 1.5, 0.0, 0.0, W, L)[0]  # saturated
    assert i == pytest.approx(beta / (2 * 1.3) * vov**2, rel=0.02)

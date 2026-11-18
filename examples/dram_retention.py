"""Retention of a DRAM cell (lesson 11): the stored charge leaks through the OFF access transistor (EKV, sub-threshold) and a junction.

Kept in its own module so that the lesson script and the tests (tests/test_js_parity.py compares the JavaScript mirror in
textbook/js/core.js: dramRetention) use the same function. ILLUSTRATIVE defaults: Cs 25 fF, Cbl 150 fF, Vdd 1.2 V, Vpp 2.0 V.
"""

import math

from minispice import EKV
from minispice.models import VT

VDD, VPP = 1.2, 2.0
CS, CBL = 25e-15, 150e-15
KP_ACC, WL_ACC = 300e-6, 1.0                 # access transistor W/L = 0.1 um / 0.1 um
BETA = KP_ACC * WL_ACC


def retention(vth, vwl, data1, *, vdd=VDD, vpp=VPP, n=1.3, cs=CS, cbl=CBL, voff=0.02, ij=0.2e-15, wl=WL_ACC, vbl=None, dv=1e-3, tmax=1e6, keep=400):
    """Charge decays through the off access transistor (EKV, sub-threshold) and a junction leakage ij. Fixed voltage step dv.

    vbl: bit-line level while the cell holds its data. None = worst case (0 V for a stored 1, Vdd for a stored 0: the bit line is
    driven there while other cells on it are accessed - a modelling assumption); "pre" = the idle precharge level Vdd/2.
    """
    m = EKV(1, dict(vto=vth, kp=300e-6, n=n, lambda_=0.05))
    w, l = wl * 1e-7, 1e-7
    vh = min(vdd, vpp - vth)
    v = vh if data1 else 0.0
    vb = (0.0 if data1 else vdd) if vbl is None else (vdd / 2 if vbl == "pre" else vbl)
    vlim = vdd / 2 + voff * (cs + cbl) / cs if data1 else vdd / 2 - voff * (cs + cbl) / cs
    t, ts, vs = 0.0, [0.0], [v]
    tret, step = float("inf"), 0
    if (v <= vlim) if data1 else (v >= vlim):                              # written level already beyond the sensing limit
        return dict(tret=0.0, ts=ts, vs=vs, vh=vh, vlim=vlim, vbl=vb)
    while t < tmax:
        ileave = -m.evaluate(vb, vwl, v, 0.0, w, l)[0]                      # current leaving the storage node through the access transistor
        itot = ileave + ij * (1 - math.exp(-v / VT)) if v > 0 else ileave   # plus the junction leakage to the substrate
        if abs(itot) < 1e-30:
            break
        dt = dv * cs / abs(itot)
        vn = v - math.copysign(dv, itot)
        crossed = (vn <= vlim) if data1 else (vn >= vlim)
        if crossed:
            tret = t + dt * abs(vlim - v) / dv
            ts.append(tret); vs.append(vlim)
            break
        t, v = t + dt, vn
        step += 1
        if step % 25 == 0:
            ts.append(t); vs.append(v)
    return dict(tret=tret, ts=ts, vs=vs, vh=vh, vlim=vlim, vbl=vb)


def is_hand(vth, vwl, n=1.3, vds=VDD):
    """Sub-threshold leakage with the gate-source voltage = vwl (the bit line is the source): Is*exp((Vgs-Vth)/(n Vt))*(1+lam*Vds)*(1-exp(-Vds/Vt))."""
    is_ = 2 * n * BETA * VT**2
    return is_ * math.exp((vwl - vth) / (n * VT)) * (1 + 0.05 * vds) * (1 - math.exp(-vds / VT))

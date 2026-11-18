"""MOSFET compact models.

Every model exposes the same interface so the solver never needs to know which
one it is talking to (and a Verilog-A/OSDI model can later be dropped in):

    evaluate(vd, vg, vs, vb, w, l) -> (id, did_dvd, did_dvg, did_dvs, did_dvb)

`id` is the current flowing *into* the drain terminal. Voltages are absolute
terminal voltages. Derivatives are with respect to the four terminal voltages,
so they always sum to zero.

Subclasses only implement `core(vgs, vds, vbs, w, l)` for an n-channel device
with vds >= 0 and return (ids, gm, gds, gmb). Polarity (NMOS/PMOS) and
source/drain swapping for vds < 0 are handled once here in `evaluate`.
"""

import math

import numpy as np

VT = 0.025865  # kT/q at 300.15 K (ngspice default temperature, 27 C)


class MosModel:
    defaults = {}

    def __init__(self, polarity, params=None):
        self.polarity = polarity  # +1 NMOS, -1 PMOS
        self.p = dict(self.defaults)
        for k, v in (params or {}).items():
            k = k.lower()
            if k in ("level", "type"):
                continue
            if k not in self.defaults:
                raise ValueError(f"unknown model parameter '{k}' for {type(self).__name__}")
            self.p[k] = v

    @property
    def vto(self):
        # Like SPICE, VTO is entered negative for PMOS; internally use |VTO|.
        return self.polarity * self.p["vto"]

    def core(self, vgs, vds, vbs, w, l):
        raise NotImplementedError

    def evaluate(self, vd, vg, vs, vb, w, l):
        pol = self.polarity
        vd, vg, vs, vb = pol * vd, pol * vg, pol * vs, pol * vb
        if vd >= vs:
            i, gm, gds, gmb = self.core(vg - vs, vd - vs, vb - vs, w, l)
            return pol * i, gds, gm, -(gm + gds + gmb), gmb
        # Reverse mode: the physical source is the drain terminal.
        i, gm, gds, gmb = self.core(vg - vd, vs - vd, vb - vd, w, l)
        return -pol * i, gm + gds + gmb, -gm, -gds, -gmb

    # ---- optional intrinsic charge model (Q = f(V)) ------------------------
    @property
    def has_charge(self):
        return self.p.get("cox", 0.0) > 0

    def charge_core(self, vgs, vds, vbs, w, l):
        """n-channel, vds >= 0: terminal charges (qg, qd, qs, qb) in coulombs."""
        raise NotImplementedError

    def charges(self, vd, vg, vs, vb, w, l):
        """Terminal charges (qd, qg, qs, qb) [same terminal order as the voltages d, g, s, b]."""
        pol = self.polarity
        vd, vg, vs, vb = pol * vd, pol * vg, pol * vs, pol * vb
        if vd >= vs:
            qg, qd, qs, qb = self.charge_core(vg - vs, vd - vs, vb - vs, w, l)
        else:  # reverse mode: the physical source is the drain terminal
            qg, qs, qd, qb = self.charge_core(vg - vd, vs - vd, vb - vd, w, l)
        return pol * qd, pol * qg, pol * qs, pol * qb

    def charge_jac(self, vd, vg, vs, vb, w, l, h=1e-6):
        """Charges (4,) and capacitance matrix C[k][j] = dQ_k/dV_j (4, 4); k and j both in order d, g, s, b."""
        v0 = [vd, vg, vs, vb]
        q0 = np.array(self.charges(*v0, w, l))
        c = np.zeros((4, 4))
        for j in range(4):
            hi, lo = list(v0), list(v0)
            hi[j] += h
            lo[j] -= h
            c[:, j] = (np.array(self.charges(*hi, w, l)) - np.array(self.charges(*lo, w, l))) / (2 * h)
        return q0, c

    def overlap_caps(self, w, l):
        """Constant gate capacitances (cgs, cgd, cgb) in farads."""
        p = self.p
        return p["cgso"] * w, p["cgdo"] * w, p["cgbo"] * l


class Level1(MosModel):
    """Shichman-Hodges (SPICE Level 1), same equations as ngspice MOS1."""

    defaults = dict(vto=0.0, kp=2e-5, gamma=0.0, phi=0.6, lambda_=0.0,
                    cgso=0.0, cgdo=0.0, cgbo=0.0)

    def __init__(self, polarity, params=None):
        params = dict(params or {})
        if "lambda" in params:
            params["lambda_"] = params.pop("lambda")
        super().__init__(polarity, params)

    def core(self, vgs, vds, vbs, w, l):
        p = self.p
        beta = p["kp"] * w / l
        phi, gamma, lam = p["phi"], p["gamma"], p["lambda_"]
        sphi = math.sqrt(phi)
        if vbs <= 0:
            sarg = math.sqrt(phi - vbs)
            dsarg = -0.5 / sarg
        else:  # smooth continuation for forward-biased bulk, as in ngspice
            d = 1 + 0.5 * vbs / phi
            sarg = sphi / d
            dsarg = -sphi * (0.5 / phi) / (d * d)
        vth = self.vto + gamma * (sarg - sphi)
        dvth = gamma * dsarg  # d(vth)/d(vbs)
        vov = vgs - vth
        if vov <= 0:
            return 0.0, 0.0, 0.0, 0.0
        clm = 1 + lam * vds
        if vds < vov:  # triode
            i0 = beta * (vov - 0.5 * vds) * vds
            gm = beta * vds * clm
            gds = beta * (vov - vds) * clm + lam * i0
        else:  # saturation
            i0 = 0.5 * beta * vov * vov
            gm = beta * vov * clm
            gds = lam * i0
        return i0 * clm, gm, gds, -gm * dvth


def _softplus(x):
    return x + math.log1p(math.exp(-x)) if x > 0 else math.log1p(math.exp(x))


def _sigmoid(x):
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def _ekv_f(x):
    """EKV interpolation function F(x) = ln^2(1 + exp(x/2)) and dF/dx."""
    h = 0.5 * x
    sp = _softplus(h)
    return sp * sp, sp * _sigmoid(h)


class EKV(MosModel):
    """Simplified long-channel EKV: one expression from weak to strong inversion.

    Id = Is * (F(Vp-Vs) - F(Vp-Vd)),  Vp = (Vg - VTO) / n,  Is = 2 n beta Vt^2
    All voltages are bulk-referenced, so source/drain are inherently symmetric.
    """

    defaults = dict(vto=0.5, kp=2e-4, n=1.3, lambda_=0.0, eta=0.0,
                    cgso=0.0, cgdo=0.0, cgbo=0.0, cox=0.0)  # cox: gate capacitance per area [F/m^2]
    # eta: DIBL coefficient [V/V]. The threshold drops by eta*Vds, i.e. the gate "sees" Vgs + eta*Vds.

    def __init__(self, polarity, params=None):
        params = dict(params or {})
        if "lambda" in params:
            params["lambda_"] = params.pop("lambda")
        super().__init__(polarity, params)

    def core(self, vgs, vds, vbs, w, l):
        p = self.p
        n, lam = p["n"], p["lambda_"]
        is_ = 2 * n * p["kp"] * (w / l) * VT * VT
        eta = self.p["eta"]
        vp = (vgs + eta * vds - vbs - self.vto) / n
        vsb, vdb = -vbs, vds - vbs
        f_f, df_f = _ekv_f((vp - vsb) / VT)
        f_r, df_r = _ekv_f((vp - vdb) / VT)
        i0 = is_ * (f_f - f_r)
        clm = 1 + lam * vds
        d_vp = is_ / VT * (df_f - df_r)
        d_vsb = -is_ / VT * df_f
        d_vdb = is_ / VT * df_r
        gm = clm * d_vp / n
        gds = clm * d_vdb + lam * i0 + eta * gm      # DIBL: vp also depends on vds through vgs + eta*vds
        gmb = clm * (-d_vp / n - d_vsb - d_vdb)
        return i0 * clm, gm, gds, gmb

    def charge_core(self, vgs, vds, vbs, w, l):
        """Channel (inversion) charge of the long-channel EKV model, Q_G = -(Q_D + Q_S), Q_B = 0.

        With q = (sqrt(1 + 4 i) - 1) / 2 at each channel end (i = i_f, i_r), the normalised
        charge density along the channel is q(y); integrating it gives the total inversion
        charge, and weighting by y/L gives the part attributed to the drain (Ward-Dutton).
        Depletion/accumulation charge is not modelled (documented limitation).
        """
        n = self.p["n"]
        vp = (vgs + self.p["eta"] * vds - vbs - self.vto) / n
        i_f, _ = _ekv_f((vp + vbs) / VT)          # vsb = -vbs
        i_r, _ = _ekv_f((vp - (vds - vbs)) / VT)  # vdb = vds - vbs
        qs = 2 * i_f / (math.sqrt(1 + 4 * i_f) + 1)
        qd = 2 * i_r / (math.sqrt(1 + 4 * i_r) + 1)
        big_s, delta = qs + qd + 1, qs - qd
        q_inv = d_frac = 0.0
        for t, wt in _GAUSS3:  # integrands are polynomials of degree <= 4 in t: exact
            q = qd + delta * t
            f = q * (2 * q + 1) / big_s
            q_inv += wt * f
            d_frac += wt * (1 - t * (q + qd + 1) / big_s) * f
        q0 = 2 * n * VT * self.p["cox"] * w * l
        qi_tot, qd_tot = -q0 * q_inv, -q0 * d_frac
        return -qi_tot, qd_tot, qi_tot - qd_tot, 0.0


_GAUSS3 = ((0.5 * (1 - math.sqrt(0.6)), 5 / 18), (0.5, 8 / 18), (0.5 * (1 + math.sqrt(0.6)), 5 / 18))

LEVELS = {1: Level1, "ekv": EKV}


def make_model(kind, params):
    """kind: 'nmos' or 'pmos'; params may contain level=1 or level='ekv'."""
    pol = {"nmos": 1, "pmos": -1}[kind.lower()]
    level = params.get("level", 1)
    if isinstance(level, float) and level.is_integer():
        level = int(level)
    if level not in LEVELS:
        raise ValueError(f"unsupported model level {level!r} (have {list(LEVELS)})")
    return LEVELS[level](pol, params)

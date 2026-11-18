"""Circuit container and elements. Each element knows how to stamp itself into
the MNA system  A x = z  where x = [node voltages..., voltage-source currents...].
"""

from dataclasses import dataclass

import numpy as np


def _add(A, r, c, v):
    """Add v at (r, c) where r, c are node numbers (0 = ground, not stored)."""
    if r and c:
        A[r - 1, c - 1] += v


def _addz(z, r, v):
    if r:
        z[r - 1] += v


@dataclass
class Pulse:
    v1: float
    v2: float
    td: float = 0.0
    tr: float = 0.0
    tf: float = 0.0
    pw: float = 1e30
    per: float = 0.0

    def breakpoints(self, tstop):
        """Times in (0, tstop] where the waveform has a corner."""
        corners = [0.0, self.tr, self.tr + self.pw, self.tr + self.pw + self.tf]
        pts, k = [], 0
        while True:
            base = self.td + k * self.per
            if base > tstop:
                break
            pts += [base + c for c in corners if 0 < base + c <= tstop]
            if self.per <= 0:
                break
            k += 1
        return pts

    def value(self, t):
        if t < self.td:
            return self.v1
        t -= self.td
        if self.per > 0:
            t %= self.per
        if t < self.tr:
            return self.v1 + (self.v2 - self.v1) * t / self.tr
        t -= self.tr
        if t < self.pw:
            return self.v2
        t -= self.pw
        if t < self.tf:
            return self.v2 + (self.v1 - self.v2) * t / self.tf
        return self.v1


class Context:
    """Per-solve settings shared by all stamps."""

    def __init__(self, t=None, scale=1.0, a=0.0, trap=False, state=None):
        self.t = t          # None -> DC value of sources
        self.scale = scale  # source stepping factor
        self.a = a          # companion coefficient: 1/h (BE) or 2/h (trap); 0 -> DC
        self.trap = trap
        self.state = state  # capacitor name -> (v_prev, i_prev)


@dataclass
class Resistor:
    name: str
    n1: int
    n2: int
    r: float

    def stamp(self, A, z, x, ctx):
        g = 1.0 / self.r
        _add(A, self.n1, self.n1, g)
        _add(A, self.n2, self.n2, g)
        _add(A, self.n1, self.n2, -g)
        _add(A, self.n2, self.n1, -g)


@dataclass
class Capacitor:
    name: str
    n1: int
    n2: int
    c: float

    def voltage(self, x):
        v1 = x[self.n1 - 1] if self.n1 else 0.0
        v2 = x[self.n2 - 1] if self.n2 else 0.0
        return v1 - v2

    def stamp(self, A, z, x, ctx):
        if ctx.a == 0.0:  # DC: open circuit
            return
        g = ctx.a * self.c
        v_prev, i_prev = ctx.state[self.name]
        ieq = g * v_prev + (i_prev if ctx.trap else 0.0)
        _add(A, self.n1, self.n1, g)
        _add(A, self.n2, self.n2, g)
        _add(A, self.n1, self.n2, -g)
        _add(A, self.n2, self.n1, -g)
        _addz(z, self.n1, ieq)
        _addz(z, self.n2, -ieq)

    def init_state(self, x):
        return (self.voltage(x), 0.0)  # capacitor current is 0 at DC

    def accept(self, x, ctx):
        v_prev, i_prev = ctx.state[self.name]
        v = self.voltage(x)
        i = ctx.a * self.c * (v - v_prev) - (i_prev if ctx.trap else 0.0)
        ctx.state[self.name] = (v, i)


@dataclass
class VSource:
    name: str
    np: int
    nn: int
    dc: float = 0.0
    wave: Pulse = None
    branch: int = -1  # row/column index in the MNA system, set by Circuit.prepare

    def value(self, ctx):
        v = self.wave.value(ctx.t) if (self.wave and ctx.t is not None) else self.dc
        return v * ctx.scale

    def stamp(self, A, z, x, ctx):
        k = self.branch
        if self.np:
            A[self.np - 1, k] += 1
            A[k, self.np - 1] += 1
        if self.nn:
            A[self.nn - 1, k] -= 1
            A[k, self.nn - 1] -= 1
        z[k] += self.value(ctx)


@dataclass
class ISource:
    name: str
    np: int
    nn: int
    dc: float = 0.0
    wave: Pulse = None

    def stamp(self, A, z, x, ctx):
        i = (self.wave.value(ctx.t) if (self.wave and ctx.t is not None) else self.dc) * ctx.scale
        _addz(z, self.np, -i)  # current flows np -> nn through the source
        _addz(z, self.nn, i)


@dataclass
class Mosfet:
    name: str
    d: int
    g: int
    s: int
    b: int
    model: object
    w: float
    l: float

    def _volts(self, x):
        return [x[n - 1] if n else 0.0 for n in (self.d, self.g, self.s, self.b)]

    def stamp(self, A, z, x, ctx):
        vd, vg, vs, vb = self._volts(x)
        i, gd, gg, gs, gb = self.model.evaluate(vd, vg, vs, vb, self.w, self.l)
        ieq = i - (gd * vd + gg * vg + gs * vs + gb * vb)
        for row, sign in ((self.d, 1.0), (self.s, -1.0)):
            _add(A, row, self.d, sign * gd)
            _add(A, row, self.g, sign * gg)
            _add(A, row, self.s, sign * gs)
            _add(A, row, self.b, sign * gb)
            _addz(z, row, -sign * ieq)
        if ctx.a and self.model.has_charge:
            # Terminal k draws i_k = dQ_k/dt. Linearise Q_k(V) ~ Q_k0 + sum_j C_kj (V_j - V_j0),
            # then discretise d/dt exactly like a capacitor (companion model).
            q0, cmat = self.model.charge_jac(vd, vg, vs, vb, self.w, self.l)
            q_prev, i_prev = ctx.state[self.name]
            v0 = np.array([vd, vg, vs, vb])
            nodes = (self.d, self.g, self.s, self.b)
            for k, nk in enumerate(nodes):
                for j, nj in enumerate(nodes):
                    _add(A, nk, nj, ctx.a * cmat[k, j])
                _addz(z, nk, ctx.a * (cmat[k] @ v0 - q0[k] + q_prev[k]) + (i_prev[k] if ctx.trap else 0.0))

    def init_state(self, x):
        if not self.model.has_charge:
            return None
        return (np.array(self.model.charges(*self._volts(x), self.w, self.l)), np.zeros(4))

    def accept(self, x, ctx):
        if not self.model.has_charge:
            return
        q = np.array(self.model.charges(*self._volts(x), self.w, self.l))
        q_prev, i_prev = ctx.state[self.name]
        ctx.state[self.name] = (q, ctx.a * (q - q_prev) - (i_prev if ctx.trap else 0.0))


class Circuit:
    def __init__(self, title=""):
        self.title = title
        self.elements = []
        self.models = {}
        self._nodes = {"0": 0}

    # ---- construction -------------------------------------------------
    def node(self, name):
        name = str(name).lower()
        if name == "gnd":
            name = "0"
        if name not in self._nodes:
            self._nodes[name] = len(self._nodes)
        return self._nodes[name]

    def _check_new(self, name):
        if any(e.name == name for e in self.elements):
            raise ValueError(f"duplicate element name '{name}'")

    def _add_element(self, e):
        self._check_new(e.name)
        self.elements.append(e)
        return e

    def add_resistor(self, name, n1, n2, r):
        return self._add_element(Resistor(name.lower(), self.node(n1), self.node(n2), r))

    def add_capacitor(self, name, n1, n2, c):
        return self._add_element(Capacitor(name.lower(), self.node(n1), self.node(n2), c))

    def add_vsource(self, name, np_, nn, dc=0.0, wave=None):
        return self._add_element(VSource(name.lower(), self.node(np_), self.node(nn), dc, wave))

    def add_isource(self, name, np_, nn, dc=0.0, wave=None):
        return self._add_element(ISource(name.lower(), self.node(np_), self.node(nn), dc, wave))

    def add_mosfet(self, name, d, g, s, b, model, w=1e-4, l=1e-4):
        """`model` is a MosModel instance or the name of a model in self.models."""
        if isinstance(model, str):
            model = self.models[model.lower()]
        name = name.lower()
        m = self._add_element(Mosfet(name, self.node(d), self.node(g), self.node(s),
                                     self.node(b), model, w, l))
        cgs, cgd, cgb = model.overlap_caps(w, l)
        for suffix, (a, c), val in (("cgs", (m.g, m.s), cgs), ("cgd", (m.g, m.d), cgd),
                                    ("cgb", (m.g, m.b), cgb)):
            if val > 0:
                self._add_element(Capacitor(f"{name}:{suffix}", a, c, val))
        return m

    # ---- queries ------------------------------------------------------
    @property
    def n_nodes(self):
        return len(self._nodes) - 1

    def node_names(self):
        return [n for n, _ in sorted(self._nodes.items(), key=lambda kv: kv[1]) if n != "0"]

    def prepare(self):
        """Assign branch rows to voltage sources; return the MNA system size."""
        k = self.n_nodes
        for e in self.elements:
            if isinstance(e, VSource):
                e.branch = k
                k += 1
        return k

    def element(self, name):
        name = name.lower()
        for e in self.elements:
            if e.name == name:
                return e
        raise KeyError(name)

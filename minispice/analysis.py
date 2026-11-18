"""Analyses: operating point, DC sweep, transient. Newton-Raphson on the MNA system."""

from dataclasses import dataclass, field

import numpy as np

from .circuit import Context, VSource

RELTOL = 1e-6
VABSTOL = 1e-9
IABSTOL = 1e-12
GMIN = 1e-12
VLIMIT = 1.0  # max node-voltage change per Newton iteration


class ConvergenceError(RuntimeError):
    pass


@dataclass
class Result:
    axis_name: str
    axis: np.ndarray
    signals: dict = field(default_factory=dict)

    def __getitem__(self, key):
        return self.signals[key.lower()]


def _assemble(ckt, x, ctx, gmin):
    n = len(x)
    A = np.zeros((n, n))
    z = np.zeros(n)
    A[np.arange(ckt.n_nodes), np.arange(ckt.n_nodes)] += gmin
    for e in ckt.elements:
        e.stamp(A, z, x, ctx)
    return A, z


def _newton(ckt, x0, ctx, gmin, maxit=150, trace=None):
    """Return the converged solution or None.

    `trace(iteration, x_before, x_after, damped)` is called after every iteration (for teaching/debugging).
    """
    nn = ckt.n_nodes
    abstol = np.full(len(x0), IABSTOL)
    abstol[:nn] = VABSTOL
    x = x0.copy()
    for it in range(1, maxit + 1):
        A, z = _assemble(ckt, x, ctx, gmin)
        try:
            x_new = np.linalg.solve(A, z)
        except np.linalg.LinAlgError:
            return None
        if not np.all(np.isfinite(x_new)):
            return None
        dx = x_new - x
        damped = False
        dv = np.max(np.abs(dx[:nn])) if nn else 0.0
        if dv > VLIMIT:
            dx *= VLIMIT / dv
            x_new = x + dx
            damped = True
        if trace:
            trace(it, x, x_new, damped)
        x = x_new
        if not damped and np.all(np.abs(dx) <= RELTOL * np.abs(x) + abstol):
            return x
    return None


def solve_op(ckt, x0=None, t=None, trace=None):
    """DC operating point. Tries plain Newton, then gmin stepping, then source stepping."""
    size = ckt.prepare()
    x0 = np.zeros(size) if x0 is None else x0

    def ctx(scale=1.0):
        return Context(t=t, scale=scale)

    x = _newton(ckt, x0, ctx(), GMIN, trace=trace)
    if x is not None:
        return x

    x = np.zeros(size)  # gmin stepping: start heavily damped, relax by decades
    for gmin in 10.0 ** np.arange(-2, -12 - 1, -1):
        x = _newton(ckt, x, ctx(), gmin)
        if x is None:
            break
    else:
        return x

    x = np.zeros(size)  # source stepping: ramp all sources 0 -> 100 %
    for scale in np.linspace(0.05, 1.0, 20):
        x = _newton(ckt, x, ctx(scale), GMIN)
        if x is None:
            raise ConvergenceError("operating point did not converge")
    return x


def _signals(ckt, xs):
    """xs: array (npoints, size) -> dict of 'v(node)' / 'i(vsrc)' arrays."""
    sig = {}
    for i, name in enumerate(ckt.node_names()):
        sig[f"v({name})"] = xs[:, i]
    for e in ckt.elements:
        if isinstance(e, VSource):
            sig[f"i({e.name})"] = xs[:, e.branch]
    return sig


def op(ckt):
    x = solve_op(ckt)
    return Result("op", np.array([0.0]), _signals(ckt, x[None, :]))


def dc_sweep(ckt, src_name, start, stop, step):
    src = ckt.element(src_name)
    size = ckt.prepare()
    n = int(round((stop - start) / step)) + 1
    values = start + step * np.arange(n)
    saved = src.dc
    xs = np.zeros((n, size))
    x = None
    try:
        for k, val in enumerate(values):
            src.dc = val
            try:
                if x is None:
                    raise ConvergenceError
                x_try = _newton(ckt, x, Context(), GMIN)
                if x_try is None:
                    raise ConvergenceError
                x = x_try
            except ConvergenceError:
                x = solve_op(ckt)
            xs[k] = x
    finally:
        src.dc = saved
    return Result(src.name, values, _signals(ckt, xs))


def transient(ckt, tstep, tstop, method="trap"):
    """Fixed output grid `tstep`; a step that fails to converge is split in two."""
    trap = method == "trap"
    size = ckt.prepare()
    x = solve_op(ckt)
    reactive = [e for e in ckt.elements if hasattr(e, "accept")]  # capacitors, charge-model MOSFETs
    state = {}
    for e in reactive:
        s = e.init_state(x)
        if s is not None:
            state[e.name] = s

    def advance(t0, t1, x, depth=0):
        h = t1 - t0
        ctx = Context(t=t1, a=(2.0 if trap else 1.0) / h, trap=trap, state=state)
        x_new = _newton(ckt, x, ctx, GMIN)
        if x_new is not None:
            for e in reactive:
                e.accept(x_new, ctx)
            return x_new
        if depth >= 12:
            raise ConvergenceError(f"transient failed near t={t1:g}s")
        mid = 0.5 * (t0 + t1)
        return advance(mid, t1, advance(t0, mid, x, depth + 1), depth + 1)

    # Land a time point on every source corner (a pulse edge inside a step would
    # otherwise be smeared, and trapezoidal integration is badly wrong across it).
    corners = sorted(t for e in ckt.elements if getattr(e, "wave", None)
                     for t in e.wave.breakpoints(tstop))

    n = int(round(tstop / tstep))
    times = tstep * np.arange(n + 1)
    xs = np.zeros((n + 1, size))
    xs[0] = x
    eps = 1e-6 * tstep
    for k in range(1, n + 1):
        t0, t1 = times[k - 1], times[k]
        inside = [t for t in corners if t0 + eps < t < t1 - eps]
        for a, b in zip([t0] + inside, inside + [t1]):
            x = advance(a, b, x)
        xs[k] = x
    return Result("time", times, _signals(ckt, xs))

"""Numbers quoted in lessons 1-3, computed here from the minispice code (nothing is typed in by hand)."""

import math

import numpy as np

from minispice import Level1, op, parse, solve_op, transient

KP, VTO, LAM, W, L = 300e-6, 0.5, 0.05, 1e-6, 0.18e-6
BETA = KP * W / L
MODEL = Level1(1, dict(vto=VTO, kp=KP, lambda_=LAM))


def lesson1():
    d = dict(beta=BETA, kp_phys=(3.9 * 8.854e-12 / 4e-9) * 0.035)
    rows = []
    for vgs, vds in ((1.0, 1.8), (1.0, 0.2), (1.8, 1.8), (0.4, 1.8)):
        vov = vgs - VTO
        if vov <= 0:
            region, hand = "차단(cutoff)", 0.0
        elif vds < vov:
            region, hand = "선형(triode)", BETA * (vov - vds / 2) * vds * (1 + LAM * vds)
        else:
            region, hand = "포화(saturation)", 0.5 * BETA * vov**2 * (1 + LAM * vds)
        rows.append((vgs, vds, region, hand, MODEL.evaluate(vds, vgs, 0.0, 0.0, W, L)[0]))
    d["rows"] = rows
    r = op(parse("""t
.model nch nmos level=1 vto=0.5 kp=300u lambda=0.05
Vgs g 0 1.0
Vds d 0 1.8
M1 d g 0 0 nch W=1u L=0.18u
.end
""")[0])
    d["op_i"] = r["i(vds)"][0]
    i0, gd, gg, gs, gb = MODEL.evaluate(1.8, 1.0, 0.0, 0.0, W, L)
    d.update(gm=gg, gds=gd, gs=gs, id0=i0)
    # lambda extraction from two saturation points
    i1, i2 = MODEL.evaluate(1.0, 1.0, 0, 0, W, L)[0], MODEL.evaluate(1.8, 1.0, 0, 0, W, L)[0]
    d.update(lam_i1=i1, lam_i2=i2, lam=(i2 - i1) / (i1 * 1.8 - i2 * 1.0))
    # beta from the sqrt(Id) slope
    m = (math.sqrt(MODEL.evaluate(1.8, 1.8, 0, 0, W, L)[0]) - math.sqrt(MODEL.evaluate(1.8, 1.0, 0, 0, W, L)[0])) / 0.8
    d.update(slope=m, beta_from_slope=2 * m * m / (1 + LAM * 1.8))
    # gds in two triode points (lesson 2 numbers: Vg = 1.4 V)
    d["gds_examples"] = []
    for vds in (0.0, 0.21176):
        vov = 1.4 - VTO
        t1 = BETA * (vov - vds) * (1 + LAM * vds)
        t2 = LAM * BETA * (vov - vds / 2) * vds
        d["gds_examples"].append((vds, t1, t2, t1 + t2))
    return d


VDD, RD = 1.8, 5e3


def lesson2():
    vg = 1.4
    fet = lambda vd: MODEL.evaluate(vd, vg, 0.0, 0.0, W, L)
    rows, vd0 = [], 0.0
    for k in range(1, 9):
        id0, gds = fet(vd0)[0], fet(vd0)[1]
        ieq = id0 - gds * vd0
        vd1 = (VDD / RD - ieq) / (1 / RD + gds)
        rows.append(dict(k=k, vd0=vd0, id0=id0, gds=gds, ieq=ieq, vd1=vd1))
        if abs(vd1 - vd0) < 1e-9:
            break
        vd0 = vd1
    star = rows[-1]["vd1"]
    ck, _ = parse(f"""t
.model nch nmos level=1 vto=0.5 kp=300u lambda=0.05
Vdd vdd 0 1.8
Vg g 0 {vg}
Rd vdd d 5k
M1 d g 0 0 nch W=1u L=0.18u
.end
""")
    log = []
    x = solve_op(ck, trace=lambda it, xb, xa, damped: log.append((it, xb.copy(), xa.copy(), damped)))
    names = ck.node_names()
    di, gi = names.index("d"), names.index("g")
    errs = [abs(r["vd0"] - star) for r in rows] + [abs(rows[-1]["vd1"] - star)]
    return dict(rows=rows, star=star, id_star=fet(star)[0], solver=x[di],
                log=[(it, xb[di], xa[di], xb[gi], xa[gi], dmp) for it, xb, xa, dmp in log], errs=errs, vg=vg)


def lesson3():
    NET = """t
.model nch nmos level=1 vto=0.5 kp=300u lambda=0.05
Vdd vdd 0 1.8
Vg g 0 PULSE(0 1.4 1n 0.1n 0.1n 3n 8n)
Rd vdd d 5k
CL d 0 100f
M1 d g 0 0 nch W=1u L=0.18u
.end
"""
    h, CL = 20e-12, 100e-15
    res = transient(parse(NET)[0], h, 8e-9, method="be")
    t, vd, vg = res.axis, res["v(d)"], res["v(g)"]
    kb = int(round(1.12e-9 / h)); ka = kb - 1
    vd_old, geq = vd[ka], CL / h
    fet = lambda v: MODEL.evaluate(v, vg[kb], 0.0, 0.0, W, L)
    rows, v0 = [], vd_old
    for it in range(1, 9):
        i0, gds = fet(v0)[0], fet(v0)[1]
        ieq = i0 - gds * v0
        v1 = (VDD / RD - ieq + geq * vd_old) / (1 / RD + gds + geq)
        rows.append(dict(it=it, v0=v0, i0=i0, gds=gds, ieq=ieq, v1=v1))
        if abs(v1 - v0) < 1e-9:
            break
        v0 = v1
    ic = geq * (v1 - vd_old)
    ir = (VDD - v1) / RD
    idn = fet(v1)[0]

    def cross(v, lvl, rising, t0=0.0):
        for i in range(1, len(t)):
            if t[i] >= t0 and ((v[i - 1] < lvl <= v[i]) if rising else (v[i - 1] > lvl >= v[i])):
                return t[i - 1] + (lvl - v[i - 1]) / (v[i] - v[i - 1]) * (t[i] - t[i - 1])
    vlow = vd[np.searchsorted(t, 4.0e-9)]
    sw = VDD - vlow
    l90, l10, l50 = vlow + 0.9 * sw, vlow + 0.1 * sw, vlow + 0.5 * sw
    out = dict(rows=rows, vd_old=vd_old, vg_new=vg[kb], geq=geq, t_a=t[ka], t_b=t[kb], vd_new_solver=vd[kb], vd_new_hand=v1,
               i_r=ir, i_d=idn, i_c=ic, vlow=vlow,
               fall=cross(vd, l10, False, 1e-9) - cross(vd, l90, False, 1e-9),
               rise=cross(vd, l90, True, 4.1e-9) - cross(vd, l10, True, 4.1e-9),
               rc22=2.2 * RD * CL,
               tp_fall=cross(vd, l50, False, 1e-9) - cross(vg, 0.7, True), tp_rise=cross(vd, l50, True, 4.1e-9) - cross(vg, 0.7, False, 4.0e-9))
    ref = transient(parse(NET)[0], 1e-12, 8e-9, method="trap")
    vref = np.interp(t, ref.axis, ref["v(d)"])
    tr = transient(parse(NET)[0], h, 8e-9, method="trap")
    out["err_be"] = float(np.max(np.abs(vd - vref)))
    out["err_trap"] = float(np.max(np.abs(tr["v(d)"] - vref)))
    return out

"""Id-Vgs of Level 1 vs EKV (Python API) and the CMOS inverter from a netlist."""

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from minispice import Circuit, EKV, Level1, dc_sweep, parse, transient

here = pathlib.Path(__file__).parent
out = here / "out"
out.mkdir(exist_ok=True)

# ---- 1. NMOS Id-Vgs: Level 1 has no subthreshold current, EKV does ---------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
for label, model in (("Level 1", Level1(1, dict(vto=0.5, kp=300e-6, lambda_=0.05))),
                     ("EKV", EKV(1, dict(vto=0.5, kp=300e-6, n=1.3, lambda_=0.05)))):
    c = Circuit()
    c.add_vsource("vd", "d", "0", 1.0)
    c.add_vsource("vg", "g", "0", 0.0)
    c.add_mosfet("m1", "d", "g", "0", "0", model, w=1e-6, l=0.18e-6)
    r = dc_sweep(c, "vg", 0.0, 1.8, 0.01)
    idrain = -r["i(vd)"]  # SPICE sign: current into the source's + terminal
    ax1.plot(r.axis, idrain * 1e3, label=label)
    ax2.semilogy(r.axis, idrain.clip(1e-18), label=label)
ax1.set(xlabel="Vgs [V]", ylabel="Id [mA]", title="linear (Vds = 1 V)")
ax2.set(xlabel="Vgs [V]", ylabel="Id [A]", title="log", ylim=(1e-12, 1e-2))
ax1.legend()
fig.tight_layout()
fig.savefig(out / "idvg.png", dpi=120)

# ---- 2. Inverter VTC and transient from the netlist --------------------------
ckt, analyses = parse((here / "inverter.cir").read_text())
vtc = dc_sweep(ckt, *analyses[0][1])
tr = transient(ckt, *analyses[1][1])
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
ax1.plot(vtc.axis, vtc["v(out)"])
ax1.set(xlabel="Vin [V]", ylabel="Vout [V]", title="inverter VTC")
ax2.plot(tr.axis * 1e9, tr["v(in)"], label="in")
ax2.plot(tr.axis * 1e9, tr["v(out)"], label="out")
ax2.set(xlabel="t [ns]", ylabel="V", title="inverter transient (CL = 10 fF)")
ax2.legend()
fig.tight_layout()
fig.savefig(out / "inverter.png", dpi=120)
print("saved", sorted(p.name for p in out.glob("*.png")))

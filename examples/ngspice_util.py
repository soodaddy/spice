"""Run ngspice in batch mode on a netlist (shared by the lesson scripts that cross-check against ngspice)."""

import pathlib
import re
import subprocess

import numpy as np

OPTIONS = ".options reltol=1e-6 abstol=1e-14 vntol=1e-9 gmin=1e-12 method=trap interp"


def run_ngspice(netlist, name, analysis, vectors, work, options=OPTIONS):
    """Strip the analysis cards of `netlist`, add one ngspice control block, run it and return the written columns.

    `analysis` is an ngspice command such as "tran 5p 4n 0 5p"; `vectors` are e.g. ["v(out)"]. Files go to `work`.
    """
    work = pathlib.Path(work)
    work.mkdir(parents=True, exist_ok=True)
    keep = [l for l in netlist.splitlines() if not l.strip().lower().startswith((".dc", ".tran", ".op", ".end"))]
    data = work / f"{name}.dat"
    data.unlink(missing_ok=True)
    deck = "\n".join(keep + [options, ".control", "set wr_singlescale", "set wr_vecnames", analysis, f"wrdata {data.name} {' '.join(vectors)}", ".endc", ".end", ""])
    cir = work / f"{name}.cir"
    cir.write_text(deck)
    p = subprocess.run(["ngspice", "-b", "-o", f"{name}.log", cir.name], cwd=work, capture_output=True, text=True, timeout=600)
    log = (work / f"{name}.log").read_text()
    if p.returncode != 0 or not data.exists() or re.search(r"\berror\b", log, re.I):
        raise RuntimeError(f"ngspice failed for {name}:\n{log[-800:]}")
    return np.loadtxt(data, skiprows=1)

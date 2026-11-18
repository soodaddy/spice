"""python -m minispice netlist.cir [-o outdir]  ->  one CSV per analysis."""

import argparse
import pathlib

import numpy as np

from . import dc_sweep, op, parse, transient


def main():
    ap = argparse.ArgumentParser(prog="minispice")
    ap.add_argument("netlist")
    ap.add_argument("-o", "--outdir", default=".")
    args = ap.parse_args()

    path = pathlib.Path(args.netlist)
    ckt, analyses = parse(path.read_text())
    out = pathlib.Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    for kind, a in analyses:
        res = {"op": lambda: op(ckt),
               "dc": lambda: dc_sweep(ckt, *a),
               "tran": lambda: transient(ckt, *a)}[kind]()
        names = list(res.signals)
        table = np.column_stack([res.axis] + [res.signals[n] for n in names])
        csv = out / f"{path.stem}.{kind}.csv"
        np.savetxt(csv, table, delimiter=",", header=",".join([res.axis_name] + names), comments="")
        print(f"{kind}: {len(res.axis)} points -> {csv}")
        if kind == "op":
            for n in names:
                print(f"  {n:12s} {res.signals[n][0]: .6g}")


if __name__ == "__main__":
    main()

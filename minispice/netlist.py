"""Minimal SPICE netlist parser (R C V I M, .model .op .dc .tran, PULSE sources).

Same syntax as ngspice for this subset, so a netlist can be fed to both.
The first line is the title, as in SPICE.
"""

import re

from .circuit import Circuit, Pulse
from .models import make_model

_SCALE = {"t": 1e12, "g": 1e9, "k": 1e3, "m": 1e-3, "u": 1e-6,
          "n": 1e-9, "p": 1e-12, "f": 1e-15, "a": 1e-18}
_NUM = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?)([a-z]*)$")


def parse_value(tok):
    m = _NUM.match(tok.lower())
    if not m:
        raise ValueError(f"bad number '{tok}'")
    num, suffix = float(m.group(1)), m.group(2)
    if suffix.startswith("meg"):
        return num * 1e6
    if suffix.startswith("mil"):
        return num * 25.4e-6
    return num * _SCALE[suffix[0]] if suffix and suffix[0] in _SCALE else num


def _logical_lines(text):
    lines = text.splitlines()
    out = []
    for raw in lines[1:]:  # first line is the title
        line = raw.split(";")[0].strip()
        if not line or line.startswith("*"):
            continue
        if line.startswith("+") and out:
            out[-1] += " " + line[1:]
        else:
            out.append(line)
    return lines[0].strip() if lines else "", out


def _tokens(line):
    return re.sub(r"[(),]", " ", line).lower().split()


def _split_kv(tokens):
    pos, kv = [], {}
    toks = " ".join(tokens).replace(" = ", "=").replace("= ", "=").replace(" =", "=").split()
    for t in toks:
        if "=" in t:
            k, v = t.split("=", 1)
            kv[k] = v
        else:
            pos.append(t)
    return pos, kv


def _num_or_str(s):
    try:
        return parse_value(s)
    except ValueError:
        return s


def _source_args(tok):
    """Parse '[DC] val' and/or 'PULSE v1 v2 ...' -> (dc, wave)."""
    dc, wave = 0.0, None
    i = 0
    while i < len(tok):
        t = tok[i]
        if t == "dc":
            dc = parse_value(tok[i + 1])
            i += 2
        elif t == "pulse":
            wave = Pulse(*[parse_value(v) for v in tok[i + 1:]])
            dc = wave.v1
            break
        else:
            dc = parse_value(t)
            i += 1
    return dc, wave


def parse(text):
    """Return (Circuit, analyses) where analyses is a list of (kind, args)."""
    title, lines = _logical_lines(text)
    ckt = Circuit(title)
    analyses = []
    elements = []
    for line in lines:
        tok = _tokens(line)
        if tok[0] == ".model":
            pos, kv = _split_kv(tok[1:])
            params = {k: _num_or_str(v) for k, v in kv.items()}
            ckt.models[pos[0]] = make_model(pos[1], params)
        elif tok[0] == ".op":
            analyses.append(("op", ()))
        elif tok[0] == ".dc":
            analyses.append(("dc", (tok[1], *map(parse_value, tok[2:5]))))
        elif tok[0] == ".tran":
            analyses.append(("tran", tuple(map(parse_value, tok[1:3]))))
        elif tok[0] == ".end":
            break
        elif tok[0].startswith("."):
            raise ValueError(f"unsupported control card '{tok[0]}'")
        else:
            elements.append(tok)  # defer so .model may appear after devices

    for tok in elements:
        name, kind = tok[0], tok[0][0]
        if kind == "r":
            ckt.add_resistor(name, tok[1], tok[2], parse_value(tok[3]))
        elif kind == "c":
            ckt.add_capacitor(name, tok[1], tok[2], parse_value(tok[3]))
        elif kind in "vi":
            dc, wave = _source_args(tok[3:])
            (ckt.add_vsource if kind == "v" else ckt.add_isource)(name, tok[1], tok[2], dc, wave)
        elif kind == "m":
            pos, kv = _split_kv(tok[1:])
            ckt.add_mosfet(name, pos[0], pos[1], pos[2], pos[3], pos[4],
                           w=parse_value(kv.get("w", "100u")), l=parse_value(kv.get("l", "100u")))
        else:
            raise ValueError(f"unsupported element '{name}'")
    return ckt, analyses

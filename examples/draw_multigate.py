"""Structure drawings for FinFET and gate-all-around (nanosheet) transistors: 3D views and cross-sections.

Not to scale. Colours: silicon = blue, source/drain = orange, gate = grey, gate dielectric = yellow, STI oxide = light grey.
"""

import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

INK = "#1f3b73"
HOT = "#b03a00"
SI, SD, GATE, OX, STI, SUB = "#7fa8e0", "#f2b98f", "#8a919c", "#f6e27a", "#dcdfe4", "#e6ecf5"


def _shade(color, f):
    c = np.array(matplotlib_rgb(color))
    return tuple(np.clip(c * f, 0, 1))


def matplotlib_rgb(color):
    from matplotlib.colors import to_rgb
    return to_rgb(color)


_ORDER = [0]


def box(ax, x0, x1, y0, y1, z0, z1, color, alpha=1.0, edge="#2a3550"):
    """Axis-aligned box with simple per-face shading (top light, sides darker).

    Boxes are drawn in the order they are added (the caller adds them back to front): matplotlib's own
    depth sorting of whole polygons mixes up touching boxes.
    """
    v = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]
    faces = {"bottom": [0, 1, 2, 3], "top": [4, 5, 6, 7], "front": [0, 1, 5, 4], "back": [2, 3, 7, 6], "right": [1, 2, 6, 5], "left": [0, 3, 7, 4]}
    shade = {"bottom": 0.7, "top": 1.05, "front": 0.92, "back": 0.8, "right": 0.82, "left": 0.86}
    polys = [[v[i] for i in idx] for idx in faces.values()]
    cols = [_shade(color, shade[k]) + (alpha,) for k in faces]
    coll = Poly3DCollection(polys, facecolors=cols, edgecolors=edge, linewidths=0.5)
    _ORDER[0] += 1
    coll.set_zorder(_ORDER[0])
    ax.add_collection3d(coll)


def _setup3d(ax, xlim, ylim, zlim, elev=27, azim=-58):
    ax.computed_zorder = False
    _ORDER[0] = 0
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_zlim(*zlim)
    ax.set_box_aspect((xlim[1] - xlim[0], ylim[1] - ylim[0], zlim[1] - zlim[0]), zoom=1.12)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


def finfet_3d(ax, nfin=2):
    """FinFET: fins stand on the substrate, the gate wraps over them (3 sides), raised source/drain at the fin ends."""
    ax.computed_zorder = False
    _ORDER[0] = 0
    pitch, wfin, hfin, sti_h = 3.0, 0.9, 3.0, 1.0
    wy = pitch * nfin + 0.8
    box(ax, 0, 10, 0, wy, -1.0, 0, SUB)
    box(ax, 0, 10, 0, wy, 0, sti_h, STI)
    box(ax, 0, 3.2, 0.2, wy - 0.2, sti_h, sti_h + 2.4, SD)                       # source (raised epitaxy)
    for k in reversed(range(nfin)):                                              # far fins first
        y0 = 0.9 + k * pitch
        box(ax, 3.2, 6.8, y0, y0 + wfin, sti_h, sti_h + hfin, SI)                # fin (channel)
    box(ax, 3.9, 6.1, 0.2, wy - 0.2, sti_h, sti_h + hfin + 0.7, GATE, alpha=0.38)  # gate wraps the fins
    box(ax, 6.8, 10, 0.2, wy - 0.2, sti_h, sti_h + 2.4, SD)                      # drain
    ax.text(1.6, 0.0, sti_h + 3.0, "source", color=HOT, fontsize=9, ha="center")
    ax.text(8.4, 0.0, sti_h + 3.0, "drain", color=HOT, fontsize=9, ha="center")
    ax.text(5.0, wy / 2, sti_h + hfin + 1.5, "gate", color=INK, fontsize=9, ha="center", fontweight="bold")
    ax.text(5.0, 0.0, -0.2, "fin", color="#1b5fb5", fontsize=8.5, ha="center")
    _setup3d(ax, (0, 10), (0, wy), (-1.0, sti_h + hfin + 1.8))


def gaa_3d(ax, nsheet=3):
    """Gate-all-around nanosheet: sheets stacked vertically, the gate surrounds every sheet on all four sides."""
    ax.computed_zorder = False
    _ORDER[0] = 0
    wy, ts, gap, z0 = 5.6, 0.45, 0.62, 1.0
    top = z0 + nsheet * ts + (nsheet - 1) * gap
    box(ax, 0, 10, 0, wy, -1.0, 0, SUB)
    box(ax, 0, 10, 0, wy, 0, 0.8, STI)
    box(ax, 0, 3.2, 0.5, wy - 0.5, 0.8, top + 0.35, SD)                          # source block
    for k in range(nsheet):                                                      # bottom sheet first
        zk = z0 + k * (ts + gap)
        box(ax, 3.2, 6.8, 0.9, wy - 0.9, zk, zk + ts, SI)                        # sheet through the channel region
    box(ax, 3.9, 6.1, 0.35, wy - 0.35, 0.8, top + 0.6, GATE, alpha=0.36)          # gate surrounds the stack
    box(ax, 6.8, 10, 0.5, wy - 0.5, 0.8, top + 0.35, SD)                         # drain block
    ax.text(1.6, 0.0, top + 1.1, "source", color=HOT, fontsize=9, ha="center")
    ax.text(8.4, 0.0, top + 1.1, "drain", color=HOT, fontsize=9, ha="center")
    ax.text(5.0, wy / 2, top + 1.4, "gate", color=INK, fontsize=9, ha="center", fontweight="bold")
    _setup3d(ax, (0, 10), (0, wy), (-1.0, top + 1.7))


# ------------------------------------------------------------------ 2D cross-sections (plane perpendicular to the channel)
def _dim(ax, p0, p1, txt, off=(0, 0), color=HOT, fs=8.5, ha="center"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="<->", mutation_scale=9, color=color, lw=1.2))
    ax.text((p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1], txt, color=color, fontsize=fs, ha=ha, va="center")


def planar_xsec(ax, x0=0.0, w=4.0):
    """Planar transistor seen across the channel width: the gate covers only the top of the active area."""
    ax.add_patch(Rectangle((x0 - 1.4, 0), w + 2.8, 2.2, fc=SUB, ec=INK, lw=1))
    ax.add_patch(Rectangle((x0 - 1.4, 1.5), 1.4, 0.7, fc=STI, ec=INK, lw=1, hatch="///"))
    ax.add_patch(Rectangle((x0 + w, 1.5), 1.4, 0.7, fc=STI, ec=INK, lw=1, hatch="///"))
    ax.add_patch(Rectangle((x0, 1.9), w, 0.3, fc=SI, ec=INK, lw=0.8))                 # active silicon / channel
    ax.add_patch(Rectangle((x0 - 0.2, 2.2), w + 0.4, 0.14, fc=OX, ec=INK, lw=0.8))   # gate dielectric (top only)
    ax.add_patch(Rectangle((x0 - 0.2, 2.34), w + 0.4, 1.1, fc=GATE, ec=INK, lw=1))
    ax.text(x0 + w / 2, 2.9, "gate", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
    ax.plot([x0, x0 + w], [2.27, 2.27], color=HOT, lw=2.4, ls=(0, (3, 1.6)))
    _dim(ax, (x0, 1.45), (x0 + w, 1.45), "W (top surface only)", off=(0, -0.38))


def finfet_xsec(ax, nfin=2, x0=0.0, show_dims=True):
    """FinFET across the channel: the gate wraps each fin on three sides, so W_eff = 2*H_fin + W_fin per fin."""
    pitch, wfin, hfin, sti = 2.6, 0.8, 3.0, 1.0
    total = pitch * nfin + 0.6
    ax.add_patch(Rectangle((x0, 0), total, sti + 0.3, fc=SUB, ec=INK, lw=1))
    ax.add_patch(Rectangle((x0, 0.3), total, sti, fc=STI, ec=INK, lw=1, hatch="///"))
    top = 0.3 + sti + hfin + 0.55
    ax.add_patch(Rectangle((x0, 0.3 + sti), total, top - 0.3 - sti, fc=GATE, ec=INK, lw=1))
    for k in range(nfin):
        fx = x0 + 0.9 + k * pitch
        ax.add_patch(Rectangle((fx - 0.12, 0.3 + sti), wfin + 0.24, hfin + 0.12, fc=OX, ec="none"))             # dielectric on 3 sides
        ax.add_patch(Rectangle((fx, 0.3), wfin, sti + hfin, fc=SI, ec=INK, lw=0.8))
        ax.plot([fx - 0.06, fx - 0.06, fx + wfin + 0.06, fx + wfin + 0.06], [0.3 + sti, 0.3 + sti + hfin + 0.06, 0.3 + sti + hfin + 0.06, 0.3 + sti],
                color=HOT, lw=2.4, ls=(0, (3, 1.6)))
    if nfin == 1:
        ax.text(x0 + total - 0.12, top - 0.35, "gate", ha="right", va="center", color="white", fontsize=9, fontweight="bold")
    else:
        ax.text(x0 + total / 2, top - 0.2, "gate", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
    if show_dims:
        fx = x0 + 0.9
        _dim(ax, (fx - 0.55, 0.3 + sti), (fx - 0.55, 0.3 + sti + hfin), "H", off=(-0.22, 0))
        _dim(ax, (fx, 0.3 + sti + hfin + 0.3), (fx + wfin, 0.3 + sti + hfin + 0.3), "W", off=(0, 0.28))
        if nfin > 1:
            _dim(ax, (fx + wfin / 2, 0.08), (fx + wfin / 2 + pitch, 0.08), "pitch", off=(0, -0.26))
    return total


def gaa_xsec(ax, nsheet=3, x0=0.0, show_dims=True):
    """Nanosheet GAA across the channel: the gate surrounds every sheet on four sides, so W_eff = 2*(W + T) per sheet."""
    w, t, gap = 3.0, 0.5, 0.75
    total = w + 2.0
    stack = nsheet * t + (nsheet - 1) * gap
    base = 0.9
    ax.add_patch(Rectangle((x0, 0), total, base, fc=SUB, ec=INK, lw=1))
    ax.add_patch(Rectangle((x0, base), total, stack + 1.3, fc=GATE, ec=INK, lw=1))
    for k in range(nsheet):
        zk = base + 0.65 + k * (t + gap)
        ax.add_patch(Rectangle((x0 + 1.0 - 0.12, zk - 0.12), w + 0.24, t + 0.24, fc=OX, ec="none"))       # dielectric on 4 sides
        ax.add_patch(Rectangle((x0 + 1.0, zk), w, t, fc=SI, ec=INK, lw=0.8))
        ax.add_patch(Rectangle((x0 + 1.0 - 0.17, zk - 0.17), w + 0.34, t + 0.34, fc="none", ec=HOT, lw=2.0, ls=(0, (3, 1.6))))
    ax.text(x0 + total - 0.05, base + stack + 0.95, "gate", ha="right", va="center", color="white", fontsize=9, fontweight="bold")
    if show_dims:
        zk = base + 0.65
        _dim(ax, (x0 + 1.0, zk - 0.45), (x0 + 1.0 + w, zk - 0.45), "W", off=(0, -0.22))
        _dim(ax, (x0 + 0.5, zk), (x0 + 0.5, zk + t), "T", off=(-0.2, 0))
    return total

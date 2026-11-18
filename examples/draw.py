"""Tiny schematic helpers shared by the lesson scripts."""

import numpy as np
from matplotlib.patches import Circle

INK = "#1f3b73"
HOT = "#b03a00"


def wire(ax, xs, ys, lw=1.6, color=INK):
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round")


def dot(ax, x, y):
    ax.plot([x], [y], "o", color=INK, ms=4)


def nmos(ax, x, y, label=None, size=1.0):
    """NMOS with gate on the left at (x, y); returns (drain, source) points."""
    s = size
    wire(ax, [x + 0.6 * s, x + 0.6 * s], [y - 0.9 * s, y + 0.9 * s], lw=2.4)   # channel
    wire(ax, [x, x], [y - 0.7 * s, y + 0.7 * s], lw=2.4)                         # gate plate
    wire(ax, [x + 0.6 * s, x + 1.6 * s], [y + 0.7 * s, y + 0.7 * s])
    wire(ax, [x + 0.6 * s, x + 1.6 * s], [y - 0.7 * s, y - 0.7 * s])
    wire(ax, [x + 0.6 * s, x + 1.6 * s], [y, y], lw=1.0)                         # body
    wire(ax, [x + 1.6 * s, x + 1.6 * s], [y + 0.7 * s, y + 1.4 * s])
    wire(ax, [x + 1.6 * s, x + 1.6 * s], [y - 0.7 * s, y - 1.4 * s])
    if label:
        ax.text(x + 1.9 * s, y, label, va="center", fontsize=8.5)
    return (x + 1.6 * s, y + 1.4 * s), (x + 1.6 * s, y - 1.4 * s)


def vsource(ax, x, y, label, r=0.45, side="left"):
    ax.add_patch(Circle((x, y), r, fc="white", ec=INK, lw=1.6))
    ax.text(x, y + 0.12, "+", ha="center", va="center", fontsize=9, color=INK)
    ax.text(x, y - 0.17, "−", ha="center", va="center", fontsize=9, color=INK)
    dx, ha = (-r - 0.2, "right") if side == "left" else (r + 0.2, "left")
    ax.text(x + dx, y, label, ha=ha, va="center", fontsize=9, color=HOT, fontweight="bold")


def resistor(ax, x, y0, y1):
    """Vertical zig-zag resistor from y0 (bottom) to y1 (top) at column x."""
    n = 6
    ys = np.linspace(y0 + 0.25 * (y1 - y0), y1 - 0.25 * (y1 - y0), n * 2 + 1)
    xs = x + 0.18 * np.array([0] + [(-1) ** k for k in range(n * 2 - 1)] + [0])
    wire(ax, [x, x], [y0, ys[0]])
    wire(ax, xs, ys)
    wire(ax, [x, x], [ys[-1], y1])


def ground(ax, x, y):
    wire(ax, [x, x], [y, y - 0.25])
    for k, w in enumerate((0.4, 0.26, 0.12)):
        wire(ax, [x - w, x + w], [y - 0.25 - 0.14 * k] * 2, lw=1.4)


def planar_nmos_section(ax, l_text="L = 0.18 µm", w_text="W = 1 µm", inversion="strong"):
    """Cross-section of a planar n-channel MOSFET (not to scale), biased in inversion."""
    from matplotlib.patches import Ellipse, FancyArrowPatch, Rectangle

    c_sub, c_n, c_ox, c_poly, c_dep, c_inv, c_sti = (
        "#e6ecf5", "#f2b98f", "#f6e27a", "#7f8794", "#fff6c9", "#2f8cff", "#d4d7dc")
    ax.set_xlim(0, 12)
    ax.set_ylim(-2.6, 7.4)
    ax.set_aspect("equal")
    ax.axis("off")

    sub = Rectangle((0, 0), 12, 3.6, fc=c_sub, ec=INK, lw=1.2)
    ax.add_patch(sub)
    # depletion region under the channel (clipped to the substrate)
    dep = Ellipse((6, 3.6), 6.4, 4.8, fc=c_dep, ec="#a08a00", ls="--", lw=1.1)
    ax.add_patch(dep)
    dep.set_clip_path(sub)
    # shallow trench isolation
    for x0 in (0, 10.6):
        ax.add_patch(Rectangle((x0, 2.4), 1.4, 1.2, fc=c_sti, ec=INK, lw=1.0, hatch="////"))
    # source / drain
    for x0 in (1.4, 7.4):
        ax.add_patch(Rectangle((x0, 2.6), 3.2, 1.0, fc=c_n, ec=INK, lw=1.2))
    ax.text(3.0, 3.1, "n+", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(9.0, 3.1, "n+", ha="center", va="center", fontsize=10, fontweight="bold")
    # inversion layer (channel), gate oxide, poly gate
    if inversion == "strong":
        ax.add_patch(Rectangle((4.6, 3.38), 2.8, 0.22, fc=c_inv, ec="none"))
    else:  # weak: almost no inversion layer, carriers diffuse through the barrier
        ax.add_patch(Rectangle((4.6, 3.38), 2.8, 0.22, fc="none", ec=c_inv, ls=":", lw=1.0))
    ax.add_patch(Rectangle((4.4, 3.6), 3.2, 0.22, fc=c_ox, ec=INK, lw=1.0))
    ax.add_patch(Rectangle((4.4, 3.82), 3.2, 0.95, fc=c_poly, ec=INK, lw=1.2))
    ax.text(6, 4.3, "poly-Si gate", ha="center", va="center", fontsize=8.5, color="white", fontweight="bold")
    # terminals
    top = 6.3
    for x, y0, name in ((3.0, 3.6, "s"), (6.0, 4.77, "g"), (9.0, 3.6, "d")):
        wire(ax, [x, x], [y0, top], lw=2.0)
        ax.plot([x], [y0], "s", color=INK, ms=5)
        ax.text(x, top + 0.25, name, ha="center", va="bottom", fontsize=11, color=HOT, fontweight="bold")
    wire(ax, [5.0, 7.0], [-0.55, -0.55], lw=2.0)
    wire(ax, [6.0, 6.0], [0, -0.55], lw=2.0)
    ax.text(6.0, -0.85, "b  (body / substrate)", ha="center", va="top", fontsize=9, color=HOT, fontweight="bold")
    # L dimension over the gate
    ax.add_patch(FancyArrowPatch((4.4, 5.35), (7.6, 5.35), arrowstyle="<->", mutation_scale=10, color=HOT, lw=1.3))
    ax.text(6.25, 5.5, l_text, ha="left", va="bottom", fontsize=8.5, color=HOT)
    # labels
    ax.text(0.2, 0.3, "p-type substrate", fontsize=8.5, va="bottom")
    ax.annotate("depletion region", (7.9, 1.55), (9.0, 0.45), fontsize=8, color="#7a6800",
                arrowprops=dict(arrowstyle="-", color="#7a6800"))
    if inversion == "strong":
        ax.annotate("inversion layer\n(channel, Vgs > Vth)", (5.0, 3.46), (0.1, 1.55), fontsize=8, color=c_inv,
                    va="center", arrowprops=dict(arrowstyle="->", color=c_inv))
    else:
        ax.annotate("", xy=(7.2, 2.95), xytext=(4.8, 2.95), arrowprops=dict(arrowstyle="-|>", color=c_inv, lw=1.6, ls="--"))
        ax.text(0.1, 1.55, "weak inversion (Vgs < Vth):\nno real channel; electrons\ndiffuse s → d over the barrier", fontsize=8, color="#1b5fb5", va="center")
    ax.annotate("gate oxide", (7.6, 3.71), (10.3, 4.55), fontsize=8, color="#7a6800",
                arrowprops=dict(arrowstyle="->", color="#7a6800"))
    ax.text(0.7, 3.8, "STI", fontsize=7.5, ha="center", color="#555")
    ax.text(11.3, 3.8, "STI", fontsize=7.5, ha="center", color="#555")
    ax.text(12.0, -1.7, f"{w_text}: into the page (⊙)", ha="right", va="top", fontsize=8.5)
    ax.text(0.0, -1.7, "electrons flow s → d,\nconventional Id flows d → s", ha="left", va="top", fontsize=8.5)


def isource(ax, x, y, label, r=0.5, side="right"):
    """Vertical current source (current flows downward), drawn with an arrow."""
    ax.add_patch(Circle((x, y), r, fc="white", ec=INK, lw=1.6))
    ax.annotate("", xy=(x, y - 0.3), xytext=(x, y + 0.3), arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.4))
    dx, ha = (r + 0.2, "left") if side == "right" else (-r - 0.2, "right")
    ax.text(x + dx, y, label, ha=ha, va="center", fontsize=9, color=HOT, fontweight="bold")


def capacitor(ax, x, y_top, y_bot, half=0.35, gap=0.12):
    """Vertical capacitor symbol between y_bot and y_top at column x."""
    mid = 0.5 * (y_top + y_bot)
    wire(ax, [x, x], [y_top, mid + gap])
    wire(ax, [x, x], [mid - gap, y_bot])
    wire(ax, [x - half, x + half], [mid + gap, mid + gap], lw=2.2)
    wire(ax, [x - half, x + half], [mid - gap, mid - gap], lw=2.2)


def pmos(ax, x, y, label=None, size=1.0):
    """PMOS: like nmos() with a bubble on the gate. Returns (source_top, drain_bottom) points."""
    top, bottom = nmos(ax, x, y, label, size)
    ax.add_patch(Circle((x - 0.17 * size, y), 0.14 * size, fc="white", ec=INK, lw=1.4))
    return top, bottom


def cmos_section(ax):
    """Cross-section of a CMOS inverter: NMOS in the p-substrate, PMOS in an n-well (not to scale)."""
    from matplotlib.patches import Rectangle

    c_sub, c_well, c_n, c_p, c_ox, c_poly, c_sti = (
        "#e6ecf5", "#dcefd9", "#f2b98f", "#f7a6c0", "#f6e27a", "#7f8794", "#d4d7dc")
    ax.set_xlim(-0.5, 21.5)
    ax.set_ylim(-2.2, 8.2)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 21, 3.6, fc=c_sub, ec=INK, lw=1.2))
    ax.add_patch(Rectangle((10.0, 1.2), 11, 2.4, fc=c_well, ec=INK, lw=1.2))
    ax.text(0.3, 0.3, "p-type substrate", fontsize=8.5)
    ax.text(10.3, 1.45, "n-well", fontsize=8.5)

    def region(x0, x1, color, txt):
        ax.add_patch(Rectangle((x0, 2.6), x1 - x0, 1.0, fc=color, ec=INK, lw=1.2))
        ax.text(0.5 * (x0 + x1), 3.1, txt, ha="center", va="center", fontsize=9, fontweight="bold")

    region(1.0, 3.6, c_n, "n+")      # NMOS source
    region(6.4, 9.0, c_n, "n+")      # NMOS drain
    region(11.0, 13.6, c_p, "p+")    # PMOS drain
    region(16.4, 19.0, c_p, "p+")    # PMOS source
    region(19.6, 20.6, c_n, "n+")    # n-well tie
    for gx0 in (3.4, 13.4):   # gates: oxide + poly (3.2 wide)
        ax.add_patch(Rectangle((gx0, 3.6), 3.2, 0.2, fc=c_ox, ec=INK, lw=1.0))
        ax.add_patch(Rectangle((gx0, 3.8), 3.2, 0.9, fc=c_poly, ec=INK, lw=1.2))
    ax.add_patch(Rectangle((4.0, 3.38), 2.0, 0.22, fc="#2f8cff", ec="none"))   # n channel (when on)
    ax.text(5.0, 4.25, "poly", ha="center", va="center", fontsize=8, color="white", fontweight="bold")
    ax.text(15.0, 4.25, "poly", ha="center", va="center", fontsize=8, color="white", fontweight="bold")

    def wire_up(x, y0, y1):
        wire(ax, [x, x], [y0, y1], lw=2.0)
        ax.plot([x], [y0], "s", color=INK, ms=4.5)

    top = 6.2
    wire_up(2.3, 3.6, top)            # NMOS source -> GND
    wire_up(7.7, 3.6, 5.5)            # NMOS drain -> out
    wire_up(12.3, 3.6, 5.5)           # PMOS drain -> out
    wire(ax, [7.7, 12.3], [5.5, 5.5], lw=2.0)
    wire(ax, [10.0, 10.0], [5.5, 5.9], lw=2.0)
    ax.text(10.0, 6.0, "out", ha="center", va="bottom", fontsize=11, color=HOT, fontweight="bold")
    wire_up(17.7, 3.6, top)           # PMOS source -> Vdd
    wire_up(20.1, 3.6, top)           # n-well tie -> Vdd
    wire(ax, [17.7, 20.1], [top, top], lw=2.0)
    ax.text(18.9, top + 0.2, "Vdd", ha="center", va="bottom", fontsize=11, color=HOT, fontweight="bold")
    ax.text(2.3, top + 0.2, "GND", ha="center", va="bottom", fontsize=11, color=HOT, fontweight="bold")
    # shared gate (input)
    wire_up(5.0, 4.7, 7.5)
    wire_up(15.0, 4.7, 7.5)
    wire(ax, [5.0, 15.0], [7.5, 7.5], lw=2.0)
    ax.text(10.0, 7.7, "in (shared gate)", ha="center", va="bottom", fontsize=11, color=HOT, fontweight="bold")
    # substrate contact
    wire(ax, [6.0, 8.0], [-0.55, -0.55], lw=2.0)
    wire(ax, [7.0, 7.0], [0, -0.55], lw=2.0)
    ax.text(7.0, -0.8, "p-substrate → GND", ha="center", va="top", fontsize=8.5, color=HOT)
    ax.text(5.0, 2.0, "NMOS", ha="center", fontsize=10, fontweight="bold", color="#1f3b73")
    ax.text(15.0, 2.0, "PMOS", ha="center", fontsize=10, fontweight="bold", color="#1f3b73")


def capacitor_h(ax, y, x0, x1, half=0.3, gap=0.12, color=INK, lw=1.6):
    """Horizontal capacitor symbol between x0 and x1 at height y."""
    mid = 0.5 * (x0 + x1)
    wire(ax, [x0, mid - gap], [y, y], lw=lw, color=color)
    wire(ax, [mid + gap, x1], [y, y], lw=lw, color=color)
    wire(ax, [mid - gap, mid - gap], [y - half, y + half], lw=2.2, color=color)
    wire(ax, [mid + gap, mid + gap], [y - half, y + half], lw=2.2, color=color)

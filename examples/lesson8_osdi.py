"""Lesson 8 figure: the Verilog-A -> OpenVAF -> OSDI -> ngspice pipeline (a diagram, no simulation results)."""

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

import draw

out = pathlib.Path(__file__).parent / "out"
out.mkdir(exist_ok=True)

fig = plt.figure(figsize=(15, 6.2), constrained_layout=True)
gs_ = fig.add_gridspec(1, 2, width_ratios=[1.55, 1.0])

ax = fig.add_subplot(gs_[0]); ax.set_xlim(0, 16); ax.set_ylim(0, 8.2); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(a) from equations to a simulator plug-in")


def box(x, y, w, h, title, sub, fc, badge=None, badge_fc="#fff"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.2", fc=fc, ec=draw.INK, lw=1.5))
    ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center", fontsize=8.2, color="#333")
    if badge:
        ax.text(x + w / 2, y - 0.32, badge, ha="center", va="top", fontsize=7.8, color="#9a3b00",
                bbox=dict(boxstyle="round,pad=0.25", fc=badge_fc, ec="#c98", lw=0.8))


box(0.2, 4.6, 3.6, 2.2, "ekv_simple.va", "Verilog-A source\n(equations only)", "#fff6c9", "written, not compiled yet", "#fff1e6")
box(4.9, 4.6, 3.6, 2.2, "OpenVAF", "compiler:\nVerilog-A → machine code", "#e8e0f5", "not run in this environment", "#fff1e6")
box(9.6, 4.6, 3.0, 2.2, "ekv_simple.osdi", "shared library\n(OSDI interface)", "#dbe9ff", "not built yet", "#fff1e6")
box(9.6, 0.5, 6.0, 2.4, "ngspice 47", "pre_osdi ekv_simple.osdi\n.model … ekv_simple …\nN1 d g s b model W=… L=…", "#e0f2e0", "OSDI support confirmed (pre_osdi exists)", "#eefaee")
for (x0, y0, x1, y1) in ((3.85, 5.7, 4.85, 5.7), (8.55, 5.7, 9.55, 5.7), (11.1, 4.55, 11.1, 2.98)):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color="#444", lw=2))
box(0.2, 0.5, 7.4, 2.4, "minispice (Python)", "models.py: class EKV  — the same equations,\nalready verified against its own tests", "#dbe9ff")
ax.annotate("", xy=(9.5, 1.7), xytext=(7.7, 1.7), arrowprops=dict(arrowstyle="<|-|>", color=draw.HOT, lw=2.2))
ax.text(8.6, 2.15, "compare", ha="center", fontsize=9, color=draw.HOT, fontweight="bold")
ax.text(8.6, 1.2, "Id–Vgs\nVTC", ha="center", fontsize=8.2, color=draw.HOT)

ax = fig.add_subplot(gs_[1]); ax.set_xlim(0, 9); ax.set_ylim(0, 8); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(b) test bench: an OSDI device is instantiated with 'N'")
d, s = draw.nmos(ax, 3.6, 4.0)
ax.text(3.0, 6.9, "N1 d g s b nmod W=1u L=0.18u", fontsize=8.5)
ax.text(3.0, 6.45, "(model: ekv_simple, from the .osdi file)", fontsize=8, color="#555")
draw.vsource(ax, 1.4, 4.0, "Vgs"); draw.wire(ax, [1.85, 3.6], [4.0, 4.0]); draw.wire(ax, [1.4, 1.4], [3.55, 2.2]); draw.ground(ax, 1.4, 2.2)
draw.vsource(ax, 6.8, 3.9, "Vds", side="right"); draw.wire(ax, [6.8, 6.8], [4.35, 5.4]); draw.wire(ax, [6.8, d[0]], [5.4, 5.4])
draw.wire(ax, [6.8, 6.8], [3.45, 1.4]); draw.wire(ax, [s[0], 6.8], [1.4, 1.4]); draw.wire(ax, [s[0], s[0]], [s[1], 1.4]); draw.ground(ax, s[0], 1.4)
draw.dot(ax, d[0], 5.4); draw.dot(ax, s[0], 1.4)

fig.suptitle("Lesson 8 - plugging a Verilog-A compact model into ngspice (OSDI)", fontsize=13)
fig.savefig(out / "lesson8.png", dpi=130)
print("saved", out / "lesson8.png")

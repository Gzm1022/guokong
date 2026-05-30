"""
Draw a presentation-style system block diagram for Method 3:
Conventional feedforward + cascade PID aeration DO control.

The style follows the existing Method 1/2 block-diagram reference:
colored blocks, explicit disturbance inputs, and clear feedback loops.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures" / "method3_system_diagram.png"


BLUE = "#1976D2"
GREEN = "#2E7D32"
LINE = "#2F3E46"
TITLE = "#1A237E"
FILL_SP = "#DDEFFB"
FILL_CTRL = "#FFF3DE"
FILL_PLANT = "#E7F4E9"
FILL_DO = "#FCE4EC"
FILL_FLOW = "#FFF8D8"
FILL_DIST = "#FDECEF"
FILL_FF = "#EDE7F6"


def add_box(ax, x, y, w, h, text, fc, fontsize=11):
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.018,rounding_size=0.012",
        fc=fc,
        ec=LINE,
        lw=1.8,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize)


def add_sum(ax, x, y, label="", signs=("-",), edge=LINE):
    c = Circle((x, y), 0.25, fc="white", ec=edge, lw=1.8)
    ax.add_patch(c)
    if "+" in signs:
        ax.text(x, y + 0.12, "+", ha="center", va="center", fontsize=11)
    if "-" in signs:
        ax.text(x, y - 0.12, "-", ha="center", va="center", fontsize=13)
    if label:
        ax.text(x, y - 0.42, label, ha="center", va="top", fontsize=9.5, color=LINE)


def arrow(ax, start, end, color=LINE, lw=1.8, text=None, text_offset=(0, 0.14), mutation=13):
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="->",
        mutation_scale=mutation,
        lw=lw,
        color=color,
        shrinkA=0,
        shrinkB=0,
    )
    ax.add_patch(patch)
    if text:
        ax.text(
            (start[0] + end[0]) / 2 + text_offset[0],
            (start[1] + end[1]) / 2 + text_offset[1],
            text,
            ha="center",
            va="bottom",
            fontsize=9.5,
            color=color,
        )


def polyline(ax, pts, color=LINE, lw=1.8, text=None, text_xy=None, mutation=13):
    for a, b in zip(pts[:-2], pts[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw, solid_capstyle="butt")
    arrow(ax, pts[-2], pts[-1], color=color, lw=lw, mutation=mutation)
    if text and text_xy:
        ax.text(text_xy[0], text_xy[1], text, ha="center", va="center", fontsize=10, color=color)


def dot(ax, x, y, color="black"):
    ax.plot(x, y, "o", color=color, markersize=5)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(18.5, 7.2), facecolor="white")
    ax.set_xlim(0, 18.5)
    ax.set_ylim(0, 7.2)
    ax.axis("off")

    ax.text(
        9.25,
        6.78,
        "方法3  普通前馈 + 串级 PID 控制结构（外环DO / 内环供气流量）",
        ha="center",
        va="center",
        fontsize=17,
        color=TITLE,
        fontweight="bold",
    )

    y = 3.45

    # Main cascade path.
    add_box(ax, 0.55, y - 0.38, 1.95, 0.78, "DO设定\nr", FILL_SP)
    add_sum(ax, 3.25, y, "Err1", signs=("-",))
    add_box(ax, 4.00, y - 0.42, 1.95, 0.84, "主控制器\nPI(DO)", FILL_CTRL)
    add_sum(ax, 6.45, y, "前馈叠加", signs=("+",))
    add_sum(ax, 7.55, y, "Err2", signs=("-",))
    add_box(ax, 8.15, y - 0.42, 2.05, 0.84, "副控制器\nPID(流量)", FILL_CTRL)
    add_box(ax, 10.95, y - 0.42, 1.80, 0.84, "鼓风机\nG2(s)", FILL_PLANT)
    add_box(ax, 13.35, y - 0.42, 1.85, 0.84, "供气流量\n(测量)", FILL_FLOW)
    add_box(ax, 15.65, y - 0.42, 1.95, 0.84, "水体DO\nFOPDT", FILL_DO)

    # Output and sensor mark.
    dot(ax, 17.95, y)
    arrow(ax, (17.60, y), (18.35, y), text="DO", text_offset=(0, 0.12))

    # Main path arrows.
    arrow(ax, (2.50, y), (3.00, y))
    arrow(ax, (3.50, y), (4.00, y))
    arrow(ax, (5.95, y), (6.20, y), text="反馈修正")
    arrow(ax, (6.70, y), (7.30, y), text="流量SP")
    arrow(ax, (7.80, y), (8.15, y))
    arrow(ax, (10.20, y), (10.95, y), text="u")
    arrow(ax, (12.75, y), (13.35, y))
    arrow(ax, (15.20, y), (15.65, y))
    arrow(ax, (17.60, y), (17.95, y))

    # Feedforward branch.
    add_box(ax, 1.05, 5.38, 1.50, 0.58, "进水流量\nQ", FILL_SP, fontsize=10.5)
    add_box(ax, 1.05, 4.55, 1.50, 0.58, "污染物浓度\nC", FILL_SP, fontsize=10.5)
    add_box(ax, 3.35, 4.76, 2.35, 0.95, "耗氧负荷\n前馈模型", FILL_FF)
    add_box(ax, 5.82, 4.92, 1.28, 0.64, "前馈供气量\nq_ff", FILL_FF, fontsize=10.5)

    arrow(ax, (2.55, 5.67), (3.35, 5.38))
    arrow(ax, (2.55, 4.84), (3.35, 5.02))
    arrow(ax, (5.70, 5.24), (5.82, 5.24))
    polyline(ax, [(6.46, 4.92), (6.46, 3.70)], color=LINE, lw=1.8)

    # Disturbance branches.
    add_box(ax, 11.05, 5.05, 1.70, 0.58, "二次扰动 d2", FILL_DIST, fontsize=10.5)
    arrow(ax, (11.90, 5.05), (11.90, 3.88))

    add_box(ax, 15.75, 5.05, 1.70, 0.58, "一次扰动 d1", FILL_DIST, fontsize=10.5)
    arrow(ax, (16.60, 5.05), (16.60, 3.88))

    # Secondary feedback: measured air flow to Err2.
    dot(ax, 15.20, y)
    polyline(
        ax,
        [(15.20, y), (15.20, 2.22), (7.55, 2.22), (7.55, 3.20)],
        color=GREEN,
        lw=2.0,
        text="副回路反馈（供气流量，快）",
        text_xy=(11.25, 2.02),
    )

    # Primary feedback: DO output to Err1.
    polyline(
        ax,
        [(17.95, y), (17.95, 1.05), (3.25, 1.05), (3.25, 3.20)],
        color=BLUE,
        lw=2.0,
        text="主回路反馈（溶解氧测量值，慢）",
        text_xy=(10.35, 0.82),
    )

    # A small sensor note at output, without adding another block to keep the diagram compact.
    ax.text(17.85, y + 0.38, "y", ha="left", va="bottom", fontsize=10, color=LINE)

    fig.tight_layout(pad=0.2)
    fig.savefig(OUT, dpi=200)
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()

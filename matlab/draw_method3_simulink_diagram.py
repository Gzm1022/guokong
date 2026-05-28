"""
Draw a Simulink-style block diagram for method 3:
conventional feedforward + cascade PID aeration DO control.

Run:
    python draw_method3_simulink_diagram.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle


def arrow(ax, start, end, **kwargs):
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(
            arrowstyle="-|>",
            mutation_scale=14,
            lw=1.2,
            color="black",
            shrinkA=0,
            shrinkB=0,
            **kwargs,
        ),
    )


def line(ax, xs, ys, **kwargs):
    ax.plot(xs, ys, color="black", lw=1.2, solid_capstyle="butt", **kwargs)


def block(ax, xy, wh, text, label=None, fontsize=12):
    x, y = xy
    w, h = wh
    ax.add_patch(Rectangle((x, y), w, h, fill=False, ec="black", lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize)
    if label:
        ax.text(x + w / 2, y - 0.20, label, ha="center", va="top", fontsize=10)


def step_block(ax, xy, label, label_pos="below"):
    x, y = xy
    w, h = 0.70, 0.70
    ax.add_patch(Rectangle((x, y), w, h, fill=False, ec="black", lw=1.2))
    sx = [x + 0.12, x + 0.36, x + 0.36, x + 0.58]
    sy = [y + 0.18, y + 0.18, y + 0.52, y + 0.52]
    ax.plot(sx, sy, color="black", lw=1.4)
    if not label:
        return
    if label_pos == "left":
        ax.text(x - 0.10, y + h / 2, label, ha="right", va="center", fontsize=10)
    elif label_pos == "right":
        ax.text(x + w + 0.10, y + h / 2, label, ha="left", va="center", fontsize=10)
    else:
        ax.text(x + w / 2, y - 0.16, label, ha="center", va="top", fontsize=10)


def sum_block(ax, center, signs, label):
    cx, cy = center
    r = 0.36
    ax.add_patch(Circle((cx, cy), r, fill=False, ec="black", lw=1.2))
    for sign, dx, dy in signs:
        ax.text(cx + dx, cy + dy, sign, ha="center", va="center", fontsize=11)
    ax.text(cx, cy - 0.52, label, ha="center", va="top", fontsize=10)


def gain_triangle(ax, xy, text, label):
    x, y = xy
    tri = Polygon([[x, y], [x, y + 0.70], [x + 0.80, y + 0.35]], fill=False, ec="black", lw=1.2)
    ax.add_patch(tri)
    ax.text(x + 0.34, y + 0.35, text, ha="center", va="center", fontsize=11)
    ax.text(x + 0.40, y - 0.16, label, ha="center", va="top", fontsize=10)


def dot(ax, xy):
    ax.add_patch(Circle(xy, 0.045, color="black"))


def main() -> None:
    here = Path(__file__).resolve().parent
    out = here / "figures" / "do_feedforward_cascade_diagram.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(19.0, 4.4), facecolor="white")
    ax.set_xlim(0, 18.8)
    ax.set_ylim(0, 4.8)
    ax.axis("off")

    y = 2.45

    # Main cascade path.
    step_block(ax, (0.15, y - 0.35), "DO设定")
    sum_block(ax, (1.75, y), [("+", 0.00, 0.20), ("-", 0.00, -0.22)], "Err1")
    block(ax, (2.45, y - 0.48), (1.25, 0.96), "PID(s)", "DO外环")
    sum_block(ax, (4.45, y), [("+", 0.00, 0.20), ("+", 0.00, -0.22)], "供气设定叠加")
    sum_block(ax, (5.65, y), [("+", 0.00, 0.20), ("-", 0.00, -0.22)], "Err2")
    block(ax, (6.35, y - 0.48), (1.25, 0.96), "PID(s)", "流量内环")
    sum_block(ax, (8.25, y), [("+", 0.00, 0.20), ("+", 0.00, -0.22)], "AddSec")
    block(ax, (9.00, y - 0.48), (1.45, 0.96), r"$\dfrac{1}{15s+1}$", "G2")
    block(ax, (11.00, y - 0.48), (1.15, 0.96), "Delay", "纯滞后")
    gain_triangle(ax, (12.65, y - 0.35), "4", "K1")
    sum_block(ax, (14.05, y), [("+", 0.00, 0.20), ("+", 0.00, -0.22)], "AddPri")
    block(ax, (14.75, y - 0.48), (1.45, 0.96), r"$\dfrac{1}{180s+1}$", "G1")
    block(ax, (16.85, y - 0.42), (0.75, 0.84), "", "示波器")
    block(ax, (16.85, 0.70), (1.25, 0.62), "out.DO", "DO输出")

    # Main arrows.
    arrow(ax, (0.85, y), (1.39, y))
    arrow(ax, (2.11, y), (2.45, y))
    arrow(ax, (3.70, y), (4.09, y))
    arrow(ax, (4.81, y), (5.29, y))
    arrow(ax, (6.01, y), (6.35, y))
    arrow(ax, (7.60, y), (7.89, y))
    arrow(ax, (8.61, y), (9.00, y))
    arrow(ax, (10.45, y), (11.00, y))
    arrow(ax, (12.15, y), (12.65, y))
    arrow(ax, (13.45, y), (13.69, y))
    arrow(ax, (14.41, y), (14.75, y))
    arrow(ax, (16.20, y), (16.85, y))
    line(ax, [16.20, 16.55, 16.55, 16.85], [y, y, 1.01, 1.01])
    arrow(ax, (16.55, 1.01), (16.85, 1.01))

    # Secondary and primary disturbances.
    step_block(ax, (8.00, 0.82), "供气扰动")
    line(ax, [8.35, 8.35], [1.52, 2.09])
    arrow(ax, (8.35, 2.09), (8.25, 2.09))

    step_block(ax, (13.80, 0.82), "耗氧扰动")
    line(ax, [14.15, 14.15], [1.52, 2.09])
    arrow(ax, (14.15, 2.09), (14.05, 2.09))

    # Feedforward branch.
    step_block(ax, (0.90, 4.00), "进水流量 Q", label_pos="left")
    step_block(ax, (0.90, 3.05), "污染物浓度 C", label_pos="left")
    block(ax, (2.25, 3.25), (1.85, 0.95), "耗氧负荷\n前馈模型", "q_ff")
    sum_block(ax, (4.45, 3.72), [("+", 0.00, 0.20), ("+", 0.00, -0.22)], "前馈叠加")

    arrow(ax, (1.60, 4.35), (2.25, 3.95))
    arrow(ax, (1.60, 3.40), (2.25, 3.50))
    arrow(ax, (4.10, 3.72), (4.09, 3.72))
    line(ax, [4.45, 4.45], [3.36, 2.81])
    arrow(ax, (4.45, 2.81), (4.45, 2.36))
    line(ax, [3.70, 4.45], [y, y])

    # Inner-loop flow feedback from G2 output to Err2 negative input.
    dot(ax, (10.45, y))
    line(ax, [10.45, 10.45, 5.65, 5.65], [y, 1.72, 1.72, 2.09])
    arrow(ax, (5.65, 1.72), (5.65, 2.09))

    # DO feedback to outer loop negative input.
    dot(ax, (16.20, y))
    line(ax, [16.20, 16.20, 1.75, 1.75], [y, 1.35, 1.35, 2.09])
    arrow(ax, (1.75, 1.35), (1.75, 2.09))

    ax.text(
        9.45,
        4.55,
        "方法3：普通前馈 + 串级 PID 曝气 DO 控制框图",
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
    )

    fig.tight_layout(pad=0.2)
    fig.savefig(out, dpi=180)
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()

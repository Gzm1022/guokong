"""
Draw a clean Simulink-style diagram for Method 3.

Output:
    figures/do_feedforward_cascade_diagram.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle


def line(ax, pts, lw=1.2):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(xs, ys, color="black", lw=lw, solid_capstyle="butt")


def arrow(ax, start, end, lw=1.2):
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(
            arrowstyle="-|>",
            mutation_scale=13,
            lw=lw,
            color="black",
            shrinkA=0,
            shrinkB=0,
        ),
    )


def routed_arrow(ax, pts, lw=1.2):
    if len(pts) < 2:
        return
    if len(pts) > 2:
        line(ax, pts[:-1], lw=lw)
    arrow(ax, pts[-2], pts[-1], lw=lw)


def block(ax, xy, wh, text, label=None, fontsize=11):
    x, y = xy
    w, h = wh
    ax.add_patch(Rectangle((x, y), w, h, fill=False, ec="black", lw=1.25))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize)
    if label:
        ax.text(x + w / 2, y - 0.16, label, ha="center", va="top", fontsize=9.5)


def step(ax, xy, label):
    x, y = xy
    w, h = 0.60, 0.56
    ax.add_patch(Rectangle((x, y), w, h, fill=False, ec="black", lw=1.25))
    ax.plot(
        [x + 0.10, x + 0.29, x + 0.29, x + 0.50],
        [y + 0.14, y + 0.14, y + 0.41, y + 0.41],
        color="black",
        lw=1.3,
    )
    ax.text(x + w / 2, y - 0.13, label, ha="center", va="top", fontsize=9.5)


def scope(ax, xy, label):
    x, y = xy
    w, h = 0.72, 0.68
    ax.add_patch(Rectangle((x, y), w, h, fill=False, ec="black", lw=1.25))
    screen = Rectangle((x + 0.12, y + 0.16), w - 0.24, h - 0.30, fill=False, ec="black", lw=1.10)
    ax.add_patch(screen)
    ax.plot(
        [x + 0.17, x + 0.27, x + 0.38, x + 0.50, x + 0.58],
        [y + 0.30, y + 0.42, y + 0.25, y + 0.40, y + 0.32],
        color="black",
        lw=1.05,
    )
    ax.text(x + w / 2, y - 0.16, label, ha="center", va="top", fontsize=9.5)


def sum_block(ax, center, label, signs=("+", "-")):
    cx, cy = center
    r = 0.30
    ax.add_patch(Circle((cx, cy), r, fill=False, ec="black", lw=1.25))
    if signs == ("+", "-"):
        ax.text(cx, cy + 0.15, "+", ha="center", va="center", fontsize=10)
        ax.text(cx, cy - 0.16, "-", ha="center", va="center", fontsize=10)
    elif signs == ("+", "+"):
        ax.text(cx, cy + 0.15, "+", ha="center", va="center", fontsize=10)
        ax.text(cx, cy - 0.16, "+", ha="center", va="center", fontsize=10)
    ax.text(cx, cy - 0.45, label, ha="center", va="top", fontsize=9.5)


def gain(ax, xy, text, label):
    x, y = xy
    tri = Polygon([[x, y], [x, y + 0.62], [x + 0.70, y + 0.31]], fill=False, ec="black", lw=1.25)
    ax.add_patch(tri)
    ax.text(x + 0.30, y + 0.31, text, ha="center", va="center", fontsize=11)
    ax.text(x + 0.35, y - 0.14, label, ha="center", va="top", fontsize=9.5)


def dot(ax, xy):
    ax.add_patch(Circle(xy, 0.045, color="black"))


def main() -> None:
    here = Path(__file__).resolve().parent
    out = here / "figures" / "do_feedforward_cascade_diagram.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(18.5, 5.2), facecolor="white")
    ax.set_xlim(0, 18.8)
    ax.set_ylim(0, 5.6)
    ax.axis("off")

    y = 2.55

    # Main cascade path.
    step(ax, (0.25, y - 0.28), "DO SP")
    sum_block(ax, (1.45, y), "Err1", ("+", "-"))
    block(ax, (2.15, y - 0.42), (1.20, 0.84), "PID(s)", "DO outer")
    sum_block(ax, (4.10, y), "Add FF", ("+", "+"))
    block(ax, (4.70, y - 0.34), (0.95, 0.68), "Sat\n0..1", "Air SP", fontsize=10)
    sum_block(ax, (6.25, y), "Err2", ("+", "-"))
    block(ax, (6.95, y - 0.42), (1.20, 0.84), "PID(s)", "Flow inner")
    sum_block(ax, (8.85, y), "AddSec", ("+", "+"))
    block(ax, (9.55, y - 0.42), (1.35, 0.84), r"$\dfrac{1}{15s+1}$", "G2")
    block(ax, (11.55, y - 0.42), (1.05, 0.84), "Delay", "30 s")
    gain(ax, (13.10, y - 0.31), "4", "K1")
    sum_block(ax, (14.35, y), "AddPri", ("+", "+"))
    block(ax, (15.05, y - 0.42), (1.35, 0.84), r"$\dfrac{1}{180s+1}$", "G1")
    scope(ax, (17.05, y - 0.34), "Scope")
    block(ax, (17.05, 0.75), (1.10, 0.55), "out.DO", "DO out")

    # Main signal arrows.
    arrow(ax, (0.85, y), (1.15, y))
    arrow(ax, (1.75, y), (2.15, y))
    arrow(ax, (3.35, y), (3.80, y))
    arrow(ax, (4.40, y), (4.70, y))
    arrow(ax, (5.65, y), (5.95, y))
    arrow(ax, (6.55, y), (6.95, y))
    arrow(ax, (8.15, y), (8.55, y))
    arrow(ax, (9.15, y), (9.55, y))
    arrow(ax, (10.90, y), (11.55, y))
    arrow(ax, (12.60, y), (13.10, y))
    arrow(ax, (13.80, y), (14.05, y))
    arrow(ax, (14.65, y), (15.05, y))
    arrow(ax, (16.40, y), (17.05, y))
    routed_arrow(ax, [(16.40, y), (16.72, y), (16.72, 1.02), (17.05, 1.02)])

    # Feedforward layer.
    step(ax, (0.55, 4.40), "Q")
    step(ax, (0.55, 3.62), "C")
    block(ax, (1.75, 3.75), (1.85, 0.95), "Oxygen Load\nFF Model", "q_ff")
    routed_arrow(ax, [(1.15, 4.68), (1.75, 4.38)])
    routed_arrow(ax, [(1.15, 3.90), (1.75, 4.05)])
    routed_arrow(ax, [(3.60, 4.23), (4.10, 4.23), (4.10, 2.85)])

    # Optional air-side disturbance, routed from above to avoid feedback lines.
    step(ax, (8.50, 3.75), "Dsec")
    routed_arrow(ax, [(8.80, 3.75), (8.80, 2.85)])

    # Primary oxygen-load disturbance, also routed from above.
    block(ax, (13.45, 3.65), (1.80, 0.70), "True Load\nDisturbance", "d_load")
    routed_arrow(ax, [(14.35, 3.65), (14.35, 2.85)])

    # Inner-loop flow feedback: separate level.
    dot(ax, (10.90, y))
    routed_arrow(ax, [(10.90, y), (10.90, 1.65), (6.25, 1.65), (6.25, 2.25)])
    ax.text(8.15, 1.46, "air-flow feedback", ha="center", va="top", fontsize=9, color="#333333")

    # DO feedback: lower separate level.
    dot(ax, (16.40, y))
    routed_arrow(ax, [(16.40, y), (16.40, 1.20), (1.45, 1.20), (1.45, 2.25)])
    ax.text(8.95, 1.02, "DO feedback", ha="center", va="top", fontsize=9, color="#333333")

    fig.tight_layout(pad=0.2)
    fig.savefig(out, dpi=180)
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()

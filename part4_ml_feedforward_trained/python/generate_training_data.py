"""
Generate simulated SCADA-like training data for the method 4 soft sensor.

The data source is not a real wastewater plant. It is generated from the same
engineering assumptions used by the DO control simulations, with random
operating conditions and measurement noise. This makes the ML part trainable
while keeping the coursework honest and reproducible.
"""

from __future__ import annotations

from pathlib import Path
import csv

import numpy as np


OUT = Path(__file__).resolve().parent / "training_dataset.csv"
RNG = np.random.default_rng(260528)


def build_row(t: float, q: float, cod: float, temp: float) -> dict[str, float]:
    phase_day = 2.0 * np.pi * t / 86400.0
    phase_short = 2.0 * np.pi * t / 7200.0

    q0 = 1.0
    cod0 = 1.0
    q_delta = q - q0
    cod_delta = cod - cod0
    temp_delta = temp - 20.0

    # Hidden "plant truth": a nonlinear oxygen-load relationship.
    oxygen_load = (
        1.18 * q_delta
        + 1.62 * cod_delta
        + 0.24 * q_delta * cod_delta
        + 0.018 * temp_delta
        + 0.05 * np.sin(phase_short)
        + RNG.normal(0.0, 0.018)
    )

    ph = (
        7.12
        - 0.16 * cod_delta
        - 0.025 * q_delta
        + 0.015 * np.sin(phase_day)
        + RNG.normal(0.0, 0.015)
    )
    conductivity = (
        1.00
        + 0.50 * cod_delta
        + 0.10 * q_delta
        + 0.010 * temp_delta
        + RNG.normal(0.0, 0.025)
    )
    orp = (
        1.00
        - 0.40 * cod_delta
        - 0.06 * q_delta
        + 0.010 * np.cos(phase_day)
        + RNG.normal(0.0, 0.020)
    )

    return {
        "q_in": q,
        "ph": ph,
        "conductivity": conductivity,
        "temperature": temp,
        "orp": orp,
        "time_sin": np.sin(phase_day),
        "time_cos": np.cos(phase_day),
        "oxygen_load": oxygen_load,
    }


def main() -> None:
    rows: list[dict[str, float]] = []
    n = 8000
    for _ in range(n):
        t = RNG.uniform(0.0, 7.0 * 86400.0)
        q = np.clip(RNG.normal(1.0, 0.16), 0.65, 1.45)
        cod = np.clip(RNG.normal(1.0 + 0.35 * (q - 1.0), 0.24), 0.55, 1.85)
        temp = RNG.uniform(16.0, 29.0)
        rows.append(build_row(t, q, cod, temp))

    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows({k: f"{v:.8f}" for k, v in row.items()} for row in rows)

    print(f"Training data saved: {OUT}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()

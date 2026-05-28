"""
Method 3 simulation: conventional feedforward + cascade PID for aeration DO control.

The model is intentionally compact for coursework use:
- outer loop: DO PID gives a trim value for target air flow
- feedforward: measured influent flow and pollutant concentration estimate oxygen load
- inner loop: air-flow PID drives the blower command
- plant: blower/valve dynamics + air-to-DO first-order lag with transport delay

Run:
    python sim_method3_feedforward_cascade.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv

import matplotlib.pyplot as plt
import numpy as np


@dataclass
class Plant:
    k_air: float = 4.0
    t_do: float = 180.0
    tau_delay: float = 30.0
    k_blower: float = 1.0
    t_flow: float = 15.0
    sp: float = 2.0
    u_min: float = 0.0
    u_max: float = 1.0
    dt: float = 0.5
    t_end: float = 2400.0
    t_dist: float = 1200.0
    q0: float = 1.0
    cod0: float = 1.0
    q_step: float = 0.20
    cod_step: float = 0.40
    k_q_true: float = 1.20
    k_cod_true: float = 1.60
    k_q_model: float = 1.05
    k_cod_model: float = 1.35
    tau_ff_measure: float = 35.0


@dataclass
class PIDParam:
    kp: float
    ki: float
    kd: float
    lo: float
    hi: float
    initial_integral: float = 0.0


class PID:
    def __init__(self, param: PIDParam) -> None:
        self.p = param
        self.integral = param.initial_integral
        self.prev_error: float | None = None

    def step(self, error: float, dt: float) -> float:
        derivative = 0.0 if self.prev_error is None else (error - self.prev_error) / dt
        self.prev_error = error

        trial_integral = self.integral + error * dt
        raw = self.p.kp * error + self.p.ki * trial_integral + self.p.kd * derivative
        clipped = clip(raw, self.p.lo, self.p.hi)

        # Conditional integration keeps the controller from winding up at actuator limits.
        if raw == clipped or (raw > self.p.hi and error < 0) or (raw < self.p.lo and error > 0):
            self.integral = trial_integral

        return clipped


def clip(value: float, lo: float, hi: float) -> float:
    return min(max(value, lo), hi)


def influent_profile(t: float, p: Plant) -> tuple[float, float]:
    if t >= p.t_dist:
        return p.q0 + p.q_step, p.cod0 + p.cod_step
    return p.q0, p.cod0


def simulate(p: Plant, use_feedforward: bool) -> dict[str, np.ndarray]:
    t = np.arange(0.0, p.t_end, p.dt)
    n = t.size

    do = np.zeros(n)
    air_flow = np.zeros(n)
    air_sp = np.zeros(n)
    blower_u = np.zeros(n)
    load_dist = np.zeros(n)
    ff_air = np.zeros(n)
    q_in = np.zeros(n)
    cod_in = np.zeros(n)

    base_air = p.sp / p.k_air
    y = p.sp
    x = base_air
    q_meas = p.q0
    cod_meas = p.cod0

    delay_len = int(round(p.tau_delay / p.dt)) + 1
    delay_buffer = np.full(delay_len, base_air)
    delay_idx = 0

    outer_no_ff = PID(PIDParam(0.52, 0.0034, 20.0, p.u_min, p.u_max, base_air / 0.0034))
    outer_ff = PID(PIDParam(0.26, 0.0015, 8.0, -0.25, 0.25, 0.0))
    inner = PID(PIDParam(4.0, 0.60, 0.0, p.u_min, p.u_max, base_air / 0.60))

    for i, now in enumerate(t):
        q, cod = influent_profile(now, p)
        q_in[i] = q
        cod_in[i] = cod

        q_meas += (q - q_meas) / p.tau_ff_measure * p.dt
        cod_meas += (cod - cod_meas) / p.tau_ff_measure * p.dt

        d_load = -(
            p.k_q_true * (q - p.q0)
            + p.k_cod_true * (cod - p.cod0)
        )
        load_dist[i] = d_load

        error_do = p.sp - y
        if use_feedforward:
            estimated_extra_load = (
                p.k_q_model * (q_meas - p.q0)
                + p.k_cod_model * (cod_meas - p.cod0)
            )
            ff = base_air + estimated_extra_load / p.k_air
            trim = outer_ff.step(error_do, p.dt)
            target_air = clip(ff + trim, p.u_min, p.u_max)
        else:
            ff = base_air
            target_air = outer_no_ff.step(error_do, p.dt)

        ff_air[i] = ff
        air_sp[i] = target_air

        error_flow = target_air - x
        u = inner.step(error_flow, p.dt)
        blower_u[i] = u

        x += (p.k_blower * u - x) / p.t_flow * p.dt
        air_flow[i] = x

        delay_buffer[delay_idx] = x
        delay_idx = (delay_idx + 1) % delay_len
        delayed_air = delay_buffer[delay_idx]

        y += (p.k_air * delayed_air - y + d_load) / p.t_do * p.dt
        do[i] = y

    return {
        "t": t,
        "do": do,
        "air_flow": air_flow,
        "air_sp": air_sp,
        "blower_u": blower_u,
        "load_dist": load_dist,
        "ff_air": ff_air,
        "q_in": q_in,
        "cod_in": cod_in,
    }


def disturbance_metrics(t: np.ndarray, y: np.ndarray, u: np.ndarray, p: Plant) -> dict[str, float]:
    mask = t >= p.t_dist
    tt = t[mask] - p.t_dist
    yy = y[mask]
    uu = u[mask]

    band = 0.02 * p.sp
    deviation = np.abs(yy - p.sp)
    outside = np.where(deviation > band)[0]
    recovery = float(tt[outside[-1]]) if outside.size else 0.0

    return {
        "min_do": float(np.min(yy)),
        "max_abs_error": float(np.max(deviation)),
        "recovery_time_s": recovery,
        "iae_after_dist": float(np.trapz(deviation, tt)),
        "air_command_integral": float(np.trapz(uu, tt)),
        "air_command_energy": float(np.trapz(uu * uu, tt)),
    }


def save_timeseries(path: Path, p: Plant, cascade: dict[str, np.ndarray], ff: dict[str, np.ndarray]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "time_s",
                "q_in_norm",
                "cod_in_norm",
                "load_disturbance_mgL",
                "do_cascade",
                "do_feedforward_cascade",
                "air_sp_cascade",
                "air_sp_feedforward_cascade",
                "air_flow_cascade",
                "air_flow_feedforward_cascade",
                "blower_u_cascade",
                "blower_u_feedforward_cascade",
                "feedforward_air_base",
            ]
        )
        for i, now in enumerate(cascade["t"]):
            writer.writerow(
                [
                    f"{now:.1f}",
                    f"{cascade['q_in'][i]:.6f}",
                    f"{cascade['cod_in'][i]:.6f}",
                    f"{cascade['load_dist'][i]:.6f}",
                    f"{cascade['do'][i]:.6f}",
                    f"{ff['do'][i]:.6f}",
                    f"{cascade['air_sp'][i]:.6f}",
                    f"{ff['air_sp'][i]:.6f}",
                    f"{cascade['air_flow'][i]:.6f}",
                    f"{ff['air_flow'][i]:.6f}",
                    f"{cascade['blower_u'][i]:.6f}",
                    f"{ff['blower_u'][i]:.6f}",
                    f"{ff['ff_air'][i]:.6f}",
                ]
            )


def save_metrics(path: Path, metrics: dict[str, dict[str, float]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["controller", "min_do", "max_abs_error", "recovery_time_s", "iae_after_dist", "air_command_integral", "air_command_energy"])
        for name, m in metrics.items():
            writer.writerow([name] + [f"{m[key]:.6f}" for key in ["min_do", "max_abs_error", "recovery_time_s", "iae_after_dist", "air_command_integral", "air_command_energy"]])


def make_plots(outdir: Path, p: Plant, cascade: dict[str, np.ndarray], ff: dict[str, np.ndarray], metrics: dict[str, dict[str, float]]) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    blue = "#1f77b4"
    red = "#d62728"
    green = "#2ca02c"
    orange = "#ff7f0e"
    gray = "#555555"

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(8.2, 4.6), facecolor="white")
    ax.plot(cascade["t"], cascade["do"], color=blue, lw=1.8, label="串级 PID")
    ax.plot(ff["t"], ff["do"], color=red, lw=1.8, ls="--", label="普通前馈 + 串级 PID")
    ax.axhline(p.sp, color=gray, lw=1.0, ls=":", label="DO 设定值")
    ax.axvline(p.t_dist, color=orange, lw=1.1, ls="-.", label="负荷阶跃扰动")
    ax.set_xlim(1050, 2100)
    ax.set_ylim(1.55, 2.08)
    ax.set_xlabel("时间 / s")
    ax.set_ylabel("溶解氧 DO / (mg/L)")
    ax.set_title("进水负荷阶跃扰动下的 DO 响应")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(outdir / "method3_do_response.png", dpi=180)
    fig.savefig(outdir / "method3_fig1_do_disturbance_response.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 4.6), facecolor="white")
    ax.plot(cascade["t"], cascade["air_sp"], color=blue, lw=1.5, label="串级 PID 目标供气量")
    ax.plot(ff["t"], ff["air_sp"], color=red, lw=1.5, ls="--", label="前馈串级 PID 目标供气量")
    ax.plot(ff["t"], ff["ff_air"], color=green, lw=1.4, ls=":", label="前馈计算供气量")
    ax.axvline(p.t_dist, color=orange, lw=1.1, ls="-.")
    ax.set_xlim(1050, 1800)
    ax.set_ylim(0.44, 0.82)
    ax.set_xlabel("时间 / s")
    ax.set_ylabel("目标供气量 / 归一化")
    ax.set_title("目标供气量信号对比")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(outdir / "method3_air_setpoint.png", dpi=180)
    fig.savefig(outdir / "method3_fig2_air_setpoint.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(8.2, 7.0), facecolor="white", sharex=True)
    axes[0].plot(ff["t"], ff["q_in"], color=blue, lw=1.5)
    axes[0].set_ylabel("进水流量")
    axes[0].set_title("可测扰动变量与前馈补偿作用")
    axes[1].plot(ff["t"], ff["cod_in"], color=red, lw=1.5)
    axes[1].set_ylabel("污染物浓度")
    axes[2].plot(ff["t"], ff["ff_air"], color=green, lw=1.5)
    axes[2].set_ylabel("前馈供气量")
    axes[2].set_xlabel("时间 / s")
    for ax in axes:
        ax.axvline(p.t_dist, color=orange, lw=1.0, ls="-.")
        ax.set_xlim(1050, 1800)
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / "method3_feedforward_signals.png", dpi=180)
    fig.savefig(outdir / "method3_fig3_feedforward_signals.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 4.6), facecolor="white")
    ax.plot(cascade["t"], cascade["blower_u"], color=blue, lw=1.5, label="串级 PID")
    ax.plot(ff["t"], ff["blower_u"], color=red, lw=1.5, ls="--", label="普通前馈 + 串级 PID")
    ax.axvline(p.t_dist, color=orange, lw=1.1, ls="-.")
    ax.set_xlim(1050, 1800)
    ax.set_ylim(0.45, 0.86)
    ax.set_xlabel("时间 / s")
    ax.set_ylabel("鼓风机控制指令 / 归一化")
    ax.set_title("控制量对比")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(outdir / "method3_fig4_control_signal.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 4.6), facecolor="white")
    ax.plot(cascade["t"], cascade["air_flow"], color=blue, lw=1.5, label="串级 PID 实际供气量")
    ax.plot(ff["t"], ff["air_flow"], color=red, lw=1.5, ls="--", label="前馈串级 PID 实际供气量")
    ax.plot(ff["t"], ff["air_sp"], color=green, lw=1.3, ls=":", label="前馈串级 PID 目标供气量")
    ax.axvline(p.t_dist, color=orange, lw=1.1, ls="-.")
    ax.set_xlim(1050, 1800)
    ax.set_ylim(0.46, 0.80)
    ax.set_xlabel("时间 / s")
    ax.set_ylabel("供气流量 / 归一化")
    ax.set_title("供气流量内环跟踪效果")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(outdir / "method3_fig5_cascade_inner_loop.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(8.2, 6.4), facecolor="white", sharex=True)
    axes[0].plot(cascade["t"], cascade["load_dist"], color=orange, lw=1.7)
    axes[0].axhline(0.0, color=gray, lw=1.0, ls=":")
    axes[0].set_ylabel("耗氧扰动 / mg/L")
    axes[0].set_title("进水耗氧负荷扰动")
    axes[1].plot(cascade["t"], cascade["q_in"], color=blue, lw=1.5, label="进水流量")
    axes[1].plot(cascade["t"], cascade["cod_in"], color=red, lw=1.5, ls="--", label="污染物浓度")
    axes[1].set_ylabel("归一化数值")
    axes[1].set_xlabel("时间 / s")
    axes[1].legend(loc="lower right")
    for ax in axes:
        ax.axvline(p.t_dist, color=orange, lw=1.0, ls="-.")
        ax.set_xlim(1050, 1700)
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / "method3_fig6_load_disturbance.png", dpi=180)
    plt.close(fig)

    labels = ["最大偏差", "恢复时间", "IAE", "控制能量"]
    keys = ["max_abs_error", "recovery_time_s", "iae_after_dist", "air_command_energy"]
    cascade_vals = [metrics["Cascade PID"][k] for k in keys]
    ff_vals = [metrics["Feedforward + Cascade PID"][k] for k in keys]
    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(9.2, 4.2), facecolor="white")
    ax.bar(x - width / 2, cascade_vals, width, color=blue, label="串级 PID")
    ax.bar(x + width / 2, ff_vals, width, color=red, label="普通前馈 + 串级 PID")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_title("抗扰动性能指标对比")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / "method3_performance_bar.png", dpi=180)
    fig.savefig(outdir / "method3_fig7_performance_bar.png", dpi=180)
    plt.close(fig)


def main() -> None:
    here = Path(__file__).resolve().parent
    outdir = here / "figures"
    p = Plant()

    cascade = simulate(p, use_feedforward=False)
    ff = simulate(p, use_feedforward=True)

    metrics = {
        "Cascade PID": disturbance_metrics(cascade["t"], cascade["do"], cascade["blower_u"], p),
        "Feedforward + Cascade PID": disturbance_metrics(ff["t"], ff["do"], ff["blower_u"], p),
    }

    save_timeseries(here / "method3_simulation_results.csv", p, cascade, ff)
    save_metrics(here / "method3_metrics.csv", metrics)
    make_plots(outdir, p, cascade, ff, metrics)

    print("Method 3 simulation complete.")
    print(f"Results CSV: {here / 'method3_simulation_results.csv'}")
    print(f"Metrics CSV: {here / 'method3_metrics.csv'}")
    print(f"Figures: {outdir}")
    for name, m in metrics.items():
        print(
            f"{name}: min DO={m['min_do']:.3f} mg/L, "
            f"max error={m['max_abs_error']:.3f} mg/L, "
            f"recovery={m['recovery_time_s']:.1f} s, "
            f"IAE={m['iae_after_dist']:.1f}, "
            f"air energy={m['air_command_energy']:.1f}"
        )


if __name__ == "__main__":
    main()

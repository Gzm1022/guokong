# -*- coding: utf-8 -*-
"""
污水处理曝气过程 —— 溶解氧(DO)控制仿真
====================================================
对应《过控提纲》中的控制方法：
    方法1：单回路 PID 控制
    方法2：串级 PID 控制（外环 DO，内环供气流量）

被控对象（工程常识取值，物理含义见报告 3.3 节）：
    主对象  供气流量 -> 溶解氧   FOPDT:  G1(s) = K1 * e^(-tau*s) / (T1*s + 1)
    副对象  鼓风机指令 -> 供气流量 一阶:  G2(s) = K2 / (T2*s + 1)

两类扰动：
    一次扰动 d_primary  ：进水耗氧负荷阶跃（COD/氨氮突增），作用在 DO 端（主对象）
    二次扰动 d_secondary：供气侧扰动（鼓风机母管压力波动/支路抢气），作用在供气流量端（副对象）
    —— 串级控制的核心优势在于：副回路能在二次扰动影响到 DO 之前将其快速抑制。

运行环境：PyCharm + conda(base)，依赖 numpy / matplotlib
作者：过程控制课程大作业
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")            # 仅出图保存，不弹窗；在 PyCharm 里想看图可改成 "TkAgg"
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# ----------------------------- 中文字体 -----------------------------
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 130

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)

# ============================================================
# 1. 被控对象数学模型参数
# ============================================================
# 主对象：供气流量 x(0~1, 归一化) -> 溶解氧 DO(mg/L)
K1   = 4.0      # 静态增益：满供气可把 DO 抬到约 4 mg/L 量级
T1   = 180.0    # 时间常数 s（约3min，水体大惯性）
tau  = 30.0     # 纯滞后 s（氧传质 + DO 膜电极测量滞后）
# 副对象：鼓风机变频指令 u(0~1) -> 实际供气流量 x(0~1)
K2   = 1.0
T2   = 15.0     # 副回路远快于主回路（15s vs 180s），是串级控制成立的前提

SP   = 2.0      # DO 设定值 mg/L（好氧池典型值）
U_MIN, U_MAX = 0.0, 1.0          # 执行器物理限幅

# 仿真时间设置
DT    = 0.5
T_END = 2400.0                   # 40 min
DIST_TIME = 1200.0               # t=1200s 施加扰动
D_PRIMARY   = -1.0               # 一次扰动：耗氧负荷，使主对象输入端等效失氧 1.0
D_SECONDARY = -0.18              # 二次扰动：供气流量被压低 0.18（约 0.7mg/L DO 当量）


# ============================================================
# 2. 通用仿真框架
#    物理被控对象对所有控制器相同：
#       u(鼓风机指令) -> 副对象G2 -> 供气流量x -> 纯滞后 -> 主对象G1 -> DO
#    dist_loc='secondary' 扰动加在供气流量端；'primary' 加在 DO 端
# ============================================================
def simulate(controller, setpoint=SP, t_end=T_END, dt=DT,
             dist_time=None, dist_mag=0.0, dist_loc="primary"):
    t = np.arange(0, t_end, dt)
    n = len(t)
    do = np.zeros(n)         # 溶解氧输出
    uq = np.zeros(n)         # 鼓风机指令（最终控制量）
    xq = np.zeros(n)         # 实际供气流量（副对象输出，含二次扰动）

    y_do = 0.0               # DO 初值（曝气前缺氧）
    x_air = 0.0              # 供气流量初值

    delay_steps = int(tau / dt) + 1
    delay_buf = np.zeros(delay_steps)
    di = 0
    state = None

    for i in range(n):
        active = (dist_time is not None and t[i] >= dist_time)
        d_sec = dist_mag if (active and dist_loc == "secondary") else 0.0
        d_pri = dist_mag if (active and dist_loc == "primary")   else 0.0

        # 控制器：输入当前 DO、供气流量测量，输出鼓风机指令 u
        u, state = controller(y_do, x_air, setpoint, state, dt)
        u = float(np.clip(u, U_MIN, U_MAX))
        uq[i] = u

        # 副对象：鼓风机指令 -> 供气流量（一阶惯性，快）；二次扰动作用在此
        x_air += (K2 * u - x_air + d_sec) / T2 * dt
        xq[i] = x_air

        # 纯滞后缓冲：进入主对象的有效供气流量被延迟 tau
        delay_buf[di] = x_air
        di = (di + 1) % delay_steps
        x_delayed = delay_buf[di]

        # 主对象：供气流量 -> 溶解氧（大惯性 FOPDT），叠加一次扰动 d_pri
        y_do += (K1 * x_delayed - y_do + d_pri) / T1 * dt
        do[i] = y_do

    return t, do, uq, xq


# ============================================================
# 3. 方法1：单回路 PID
#    DO 偏差 -> PID -> 直接给鼓风机变频指令（不测供气流量）
# ============================================================
PID_PARAMS = dict(Kp=0.70, Ki=0.0040, Kd=15.0)

def single_loop_pid(do, x_air, sp, state, dt):
    Kp, Ki, Kd = PID_PARAMS["Kp"], PID_PARAMS["Ki"], PID_PARAMS["Kd"]
    if state is None:
        state = {"integral": 0.0, "prev_e": None}
    e = sp - do
    state["integral"] += e * dt
    state["integral"] = np.clip(state["integral"], -400, 400)   # 抗积分饱和
    de = (e - state["prev_e"]) / dt if state["prev_e"] is not None else 0.0
    state["prev_e"] = e
    u = Kp * e + Ki * state["integral"] + Kd * de
    return u, state


# ============================================================
# 4. 方法2：串级 PID
#    外环(主)：DO 控制器，输出 = 目标供气流量（与单回路同一套 DO 整定，便于公平对比）
#    内环(副)：供气流量控制器，跟踪目标流量，输出 = 鼓风机指令
# ============================================================
# 加入副回路后主对象等效动态加快，主环按“先副后主”原则适当回调，
# 使设定值响应不差于单回路，同时把抗扰能力交给快速副环。
CASCADE_OUTER = dict(Kp=0.52, Ki=0.0034, Kd=20.0)  # 外环 DO 控制器
CASCADE_INNER = dict(Kp=4.0,  Ki=0.60,   Kd=0.0)   # 内环供气流量，快速随动

def cascade_pid(do, x_air, sp, state, dt):
    Kp1, Ki1, Kd1 = CASCADE_OUTER["Kp"], CASCADE_OUTER["Ki"], CASCADE_OUTER["Kd"]
    Kp2, Ki2, Kd2 = CASCADE_INNER["Kp"], CASCADE_INNER["Ki"], CASCADE_INNER["Kd"]
    if state is None:
        state = {"int1": 0.0, "pe1": None, "int2": 0.0, "pe2": None, "air_sp": 0.0}

    # ---- 外环：DO -> 目标供气流量 ----
    e1 = sp - do
    state["int1"] += e1 * dt
    state["int1"] = np.clip(state["int1"], -400, 400)
    d1 = (e1 - state["pe1"]) / dt if state["pe1"] is not None else 0.0
    state["pe1"] = e1
    air_sp = Kp1 * e1 + Ki1 * state["int1"] + Kd1 * d1
    air_sp = float(np.clip(air_sp, U_MIN, U_MAX))   # 目标流量限幅
    state["air_sp"] = air_sp

    # ---- 内环：目标供气流量 vs 实际供气流量 -> 鼓风机指令 ----
    e2 = air_sp - x_air
    state["int2"] += e2 * dt
    state["int2"] = np.clip(state["int2"], -400, 400)
    d2 = (e2 - state["pe2"]) / dt if state["pe2"] is not None else 0.0
    state["pe2"] = e2
    u = Kp2 * e2 + Ki2 * state["int2"] + Kd2 * d2
    return u, state


# ============================================================
# 5. 性能指标
# ============================================================
def step_metrics(t, y, sp=SP, settle_band=0.02):
    dt = t[1] - t[0]
    y_ss = np.mean(y[-int(60 / dt):])                 # 末段均值作为稳态
    sse = abs(sp - y_ss)
    overshoot = max(0.0, (np.max(y) - sp) / sp * 100)
    idx90 = np.argmax(y >= 0.9 * sp)
    rise = t[idx90] if idx90 > 0 else t[-1]
    band = settle_band * sp
    outside = np.where(np.abs(y - sp) > band)[0]
    settling = t[outside[-1]] if len(outside) else 0.0
    iae = np.trapz(np.abs(y - sp), t)
    itae = np.trapz(t * np.abs(y - sp), t)
    return dict(overshoot=overshoot, rise=rise, settling=settling,
                sse=sse, iae=iae, itae=itae)

def dist_metrics(t, y, sp=SP, dist_time=DIST_TIME, settle_band=0.02):
    dt = t[1] - t[0]
    i0 = int(dist_time / dt)
    max_dev = float(np.max(np.abs(y[i0:] - sp)))
    band = settle_band * sp
    outside = np.where(np.abs(y[i0:] - sp) > band)[0]
    recover = float(outside[-1] * dt) if len(outside) else 0.0
    # 扰动后误差积分（评估累计偏差）
    iae = float(np.trapz(np.abs(y[i0:] - sp), t[i0:]))
    return dict(max_dev=max_dev, recover=recover, iae=iae)


# ============================================================
# 6. 运行仿真
# ============================================================
if __name__ == "__main__":
    print("=" * 66)
    print("污水处理曝气溶解氧(DO)控制仿真：单回路PID vs 串级PID")
    print("=" * 66)

    # 6.1 设定值阶跃响应（无扰动）
    t, do_s, u_s, x_s = simulate(single_loop_pid)
    _, do_c, u_c, x_c = simulate(cascade_pid)

    # 6.2 二次扰动（供气侧，t=1200s）—— 串级核心优势
    t2, do_s2, u_s2, x_s2 = simulate(single_loop_pid, dist_time=DIST_TIME, dist_mag=D_SECONDARY, dist_loc="secondary")
    _,  do_c2, u_c2, x_c2 = simulate(cascade_pid,    dist_time=DIST_TIME, dist_mag=D_SECONDARY, dist_loc="secondary")

    # 6.3 一次扰动（耗氧负荷，DO侧，t=1200s）
    t1, do_s1, u_s1, _ = simulate(single_loop_pid, dist_time=DIST_TIME, dist_mag=D_PRIMARY, dist_loc="primary")
    _,  do_c1, u_c1, _ = simulate(cascade_pid,    dist_time=DIST_TIME, dist_mag=D_PRIMARY, dist_loc="primary")

    m_s, m_c = step_metrics(t, do_s), step_metrics(t, do_c)
    ds_s, ds_c = dist_metrics(t2, do_s2), dist_metrics(t2, do_c2)   # 二次扰动
    dp_s, dp_c = dist_metrics(t1, do_s1), dist_metrics(t1, do_c1)   # 一次扰动

    print("\n--- 阶跃响应性能指标 ---")
    for name, m in [("单回路PID", m_s), ("串级PID", m_c)]:
        print(f"  {name:8s}: 超调={m['overshoot']:6.2f}%  上升时间={m['rise']:6.1f}s  "
              f"调节时间={m['settling']:6.1f}s  稳态误差={m['sse']:.4f}  "
              f"IAE={m['iae']:7.1f}  ITAE={m['itae']:9.0f}")
    print("\n--- 二次扰动（供气侧母管压力波动）抑制 ---")
    for name, d in [("单回路PID", ds_s), ("串级PID", ds_c)]:
        print(f"  {name:8s}: 最大动态偏差={d['max_dev']:.4f} mg/L  恢复时间={d['recover']:6.1f}s  扰后IAE={d['iae']:6.1f}")
    print("\n--- 一次扰动（进水耗氧负荷）抑制 ---")
    for name, d in [("单回路PID", dp_s), ("串级PID", dp_c)]:
        print(f"  {name:8s}: 最大动态偏差={d['max_dev']:.4f} mg/L  恢复时间={d['recover']:6.1f}s  扰后IAE={d['iae']:6.1f}")

    # ============================================================
    # 7. 绘图
    # ============================================================
    C_S, C_C, C_REF, C_D = "#1f77b4", "#d62728", "#555555", "#ff7f0e"
    UNIT = "DO / (mg/L)"

    # 图1：设定值阶跃响应对比
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(t, do_s, color=C_S, lw=1.8, label="单回路PID")
    ax.plot(t, do_c, color=C_C, lw=1.8, ls="--", label="串级PID")
    ax.axhline(SP, color=C_REF, ls=":", lw=1.2, label=f"设定值 {SP} mg/L")
    ax.fill_between(t, SP * 0.98, SP * 1.02, color="green", alpha=0.07, label="±2% 误差带")
    ax.set_xlabel("时间 t / s"); ax.set_ylabel(UNIT)
    ax.set_title("溶解氧设定值阶跃响应对比", fontweight="bold")
    ax.set_xlim(0, 1200); ax.set_ylim(0, 2.6); ax.grid(alpha=0.3); ax.legend(loc="lower right")
    plt.tight_layout(); plt.savefig(f"{OUT}/fig1_step_response.png", dpi=200, bbox_inches="tight"); plt.close()

    # 图2：二次扰动（供气侧）抑制对比 —— 串级核心优势
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(t2, do_s2, color=C_S, lw=1.8, label="单回路PID")
    ax.plot(t2, do_c2, color=C_C, lw=1.8, ls="--", label="串级PID")
    ax.axhline(SP, color=C_REF, ls=":", lw=1.2, label=f"设定值 {SP} mg/L")
    ax.axvline(DIST_TIME, color=C_D, ls="-.", lw=1.2, label="供气扰动加入")
    ax.set_xlabel("时间 t / s"); ax.set_ylabel(UNIT)
    ax.set_title("二次扰动（供气母管压力波动）抑制对比", fontweight="bold")
    ax.set_xlim(1100, 2000); ax.set_ylim(1.4, 2.15); ax.grid(alpha=0.3); ax.legend(loc="lower right")
    plt.tight_layout(); plt.savefig(f"{OUT}/fig2_disturb_secondary.png", dpi=200, bbox_inches="tight"); plt.close()

    # 图3：一次扰动（耗氧负荷）抑制对比
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(t1, do_s1, color=C_S, lw=1.8, label="单回路PID")
    ax.plot(t1, do_c1, color=C_C, lw=1.8, ls="--", label="串级PID")
    ax.axhline(SP, color=C_REF, ls=":", lw=1.2, label=f"设定值 {SP} mg/L")
    ax.axvline(DIST_TIME, color=C_D, ls="-.", lw=1.2, label="耗氧负荷阶跃")
    ax.set_xlabel("时间 t / s"); ax.set_ylabel(UNIT)
    ax.set_title("一次扰动（进水耗氧负荷突增）抑制对比", fontweight="bold")
    ax.set_xlim(1100, 2100); ax.set_ylim(1.4, 2.1); ax.grid(alpha=0.3); ax.legend(loc="lower right")
    plt.tight_layout(); plt.savefig(f"{OUT}/fig3_disturb_primary.png", dpi=200, bbox_inches="tight"); plt.close()

    # 图4：控制量(鼓风机指令)对比（阶跃）
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(t, u_s, color=C_S, lw=1.6, label="单回路PID")
    ax.plot(t, u_c, color=C_C, lw=1.6, ls="--", label="串级PID")
    ax.set_xlabel("时间 t / s"); ax.set_ylabel("鼓风机变频指令 u (0~1)")
    ax.set_title("控制量（鼓风机/阀门指令）对比", fontweight="bold")
    ax.set_xlim(0, 800); ax.grid(alpha=0.3); ax.legend(loc="upper right")
    plt.tight_layout(); plt.savefig(f"{OUT}/fig4_control_signal.png", dpi=200, bbox_inches="tight"); plt.close()

    # 图5：串级内部信号（DO + 目标供气流量 vs 实际供气流量），二次扰动场景
    air_sp_hist = np.zeros(len(t2)); st = None; yy = 0.0; xx = 0.0
    db = np.zeros(int(tau / DT) + 1); k = 0
    for i in range(len(t2)):
        active = t2[i] >= DIST_TIME
        d_sec = D_SECONDARY if active else 0.0
        u, st = cascade_pid(yy, xx, SP, st, DT)
        air_sp_hist[i] = st["air_sp"]
        u = float(np.clip(u, U_MIN, U_MAX))
        xx += (K2 * u - xx + d_sec) / T2 * DT
        db[k] = xx; k = (k + 1) % len(db); xd = db[k]
        yy += (K1 * xd - yy) / T1 * DT
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    a1.plot(t2, do_c2, color=C_C, lw=1.8, label="主回路输出 DO")
    a1.axhline(SP, color=C_REF, ls=":", lw=1.2, label="DO 设定值")
    a1.axvline(DIST_TIME, color=C_D, ls="-.", lw=1.0)
    a1.set_ylabel(UNIT); a1.set_title("串级控制主/副回路信号（含二次扰动）", fontweight="bold")
    a1.set_ylim(1.5, 2.15); a1.grid(alpha=0.3); a1.legend(loc="lower right")
    a2.plot(t2, air_sp_hist, color="#2ca02c", lw=1.6, ls="--", label="副回路设定值（外环下发的目标供气流量）")
    a2.plot(t2, x_c2, color="#9467bd", lw=1.6, label="副回路输出（实际供气流量）")
    a2.axvline(DIST_TIME, color=C_D, ls="-.", lw=1.0, label="供气扰动加入")
    a2.set_xlabel("时间 t / s"); a2.set_ylabel("供气流量 (0~1)")
    a2.set_xlim(1100, 1700); a2.grid(alpha=0.3); a2.legend(loc="lower right")
    plt.tight_layout(); plt.savefig(f"{OUT}/fig5_cascade_signals.png", dpi=200, bbox_inches="tight"); plt.close()

    # 图6：性能指标柱状对比
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.2))
    items = [("超调量 / %", m_s["overshoot"], m_c["overshoot"]),
             ("阶跃调节时间 / s", m_s["settling"], m_c["settling"]),
             ("二次扰动最大偏差 / (mg/L)", ds_s["max_dev"], ds_c["max_dev"]),
             ("二次扰动恢复时间 / s", ds_s["recover"], ds_c["recover"])]
    labels = ["单回路PID", "串级PID"]; colors = [C_S, C_C]
    for ax, (title, vs, vc) in zip(axes, items):
        vals = [vs, vc]
        bars = ax.bar(labels, vals, color=colors, alpha=0.85, edgecolor="white")
        ax.set_title(title, fontweight="bold", fontsize=11); ax.grid(alpha=0.2, axis="y")
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:.2f}",
                    ha="center", va="bottom", fontsize=10)
    plt.suptitle("单回路PID 与 串级PID 性能指标对比", fontweight="bold", y=1.04)
    plt.tight_layout(); plt.savefig(f"{OUT}/fig6_performance_bar.png", dpi=200, bbox_inches="tight"); plt.close()

    # 图7：两种控制结构框图
    def draw_box(ax, x, y, w, h, text, fc):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                                    fc=fc, ec="#37474F", lw=1.4))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9.5)
    def arrow(ax, x1, y1, x2, y2, txt=""):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color="#37474F", lw=1.4))
        if txt: ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, txt, ha="center", fontsize=8, color="#555")

    fig, (axA, axB) = plt.subplots(2, 1, figsize=(11, 8))
    # —— 单回路 ——
    axA.set_xlim(0, 13); axA.set_ylim(0, 3); axA.axis("off")
    axA.text(6.5, 2.7, "方法1  单回路 PID 控制结构", ha="center", fontsize=13, fontweight="bold", color="#1A237E")
    draw_box(axA, 0.3, 1.2, 1.5, 0.8, "DO设定值\nr", "#E3F2FD")
    draw_box(axA, 2.8, 1.2, 1.6, 0.8, "PID\n控制器", "#FFF3E0")
    draw_box(axA, 5.2, 1.2, 1.7, 0.8, "鼓风机/\n变频阀门", "#E8F5E9")
    draw_box(axA, 7.6, 1.2, 1.9, 0.8, "曝气+水体\nFOPDT", "#FCE4EC")
    draw_box(axA, 10.4, 1.2, 1.5, 0.8, "DO\n传感器", "#E8F5E9")
    c1 = plt.Circle((2.55, 1.6), 0.18, fc="white", ec="#37474F", lw=1.4, zorder=5); axA.add_patch(c1)
    axA.text(2.55, 1.6, "−", ha="center", va="center", fontsize=12)
    arrow(axA, 1.8, 1.6, 2.37, 1.6); arrow(axA, 2.73, 1.6, 2.8, 1.6)
    arrow(axA, 4.4, 1.6, 5.2, 1.6, "u"); arrow(axA, 6.9, 1.6, 7.6, 1.6)
    arrow(axA, 9.5, 1.6, 10.4, 1.6, "DO")
    axA.annotate("", xy=(2.55, 1.42), xytext=(11.15, 1.2),
                 arrowprops=dict(arrowstyle="->", color="#1565C0", lw=1.6, connectionstyle="arc3,rad=0.25"))
    draw_box(axA, 7.6, 2.45, 1.9, 0.45, "扰动 d", "#FFEBEE")
    # —— 串级 ——
    axB.set_xlim(0, 13); axB.set_ylim(0, 3.4); axB.axis("off")
    axB.text(6.5, 3.15, "方法2  串级 PID 控制结构（外环DO / 内环供气流量）",
             ha="center", fontsize=13, fontweight="bold", color="#1A237E")
    draw_box(axB, 0.2, 1.5, 1.3, 0.7, "DO设定\nr", "#E3F2FD")
    draw_box(axB, 2.2, 1.5, 1.3, 0.7, "主控制器\nPI(DO)", "#FFF3E0")
    draw_box(axB, 4.3, 1.5, 1.3, 0.7, "副控制器\nPID(流量)", "#FFF3E0")
    draw_box(axB, 6.3, 1.5, 1.4, 0.7, "鼓风机\nG2(s)", "#E8F5E9")
    draw_box(axB, 8.1, 1.5, 1.5, 0.7, "供气流量\n(测量)", "#FFFDE7")
    draw_box(axB, 10.0, 1.5, 1.6, 0.7, "水体DO\nFOPDT", "#FCE4EC")
    for cx in (1.95, 4.05):
        c = plt.Circle((cx, 1.85), 0.16, fc="white", ec="#37474F", lw=1.3, zorder=5); axB.add_patch(c)
        axB.text(cx, 1.85, "−", ha="center", va="center", fontsize=11)
    arrow(axB, 1.5, 1.85, 1.79, 1.85); arrow(axB, 2.11, 1.85, 2.2, 1.85)
    arrow(axB, 3.5, 1.85, 3.89, 1.85, "流量SP"); arrow(axB, 4.21, 1.85, 4.3, 1.85)
    arrow(axB, 5.6, 1.85, 6.3, 1.85, "u"); arrow(axB, 7.7, 1.85, 8.1, 1.85)
    arrow(axB, 9.6, 1.85, 10.0, 1.85)
    arrow(axB, 11.6, 1.85, 12.3, 1.85, "DO")
    axB.annotate("", xy=(4.05, 1.69), xytext=(8.85, 1.5),
                 arrowprops=dict(arrowstyle="->", color="#2E7D32", lw=1.5, connectionstyle="arc3,rad=-0.35"))
    axB.text(6.4, 0.95, "副回路反馈（供气流量，快）", ha="center", fontsize=8, color="#2E7D32", style="italic")
    axB.annotate("", xy=(1.95, 1.65), xytext=(12.3, 1.4),
                 arrowprops=dict(arrowstyle="->", color="#1565C0", lw=1.6, connectionstyle="arc3,rad=0.25"))
    axB.text(6.4, 0.45, "主回路反馈（溶解氧，慢）", ha="center", fontsize=8, color="#1565C0", style="italic")
    draw_box(axB, 7.8, 2.65, 1.6, 0.45, "二次扰动 d2", "#FFEBEE")
    arrow(axB, 8.6, 2.65, 8.6, 2.2)
    plt.tight_layout(); plt.savefig(f"{OUT}/fig7_structure.png", dpi=200, bbox_inches="tight"); plt.close()

    print(f"\n图片已输出到: {OUT}")

    # ============================================================
    # 8. 保存结果到 JSON（供报告生成脚本读取）
    # ============================================================
    results = dict(
        model=dict(K1=K1, T1=T1, tau=tau, K2=K2, T2=T2, SP=SP,
                   G1="G1(s)=K1*exp(-tau*s)/(T1*s+1)", G2="G2(s)=K2/(T2*s+1)"),
        single_pid=PID_PARAMS,
        cascade=dict(outer=CASCADE_OUTER, inner=CASCADE_INNER),
        step_metrics=dict(single=m_s, cascade=m_c),
        dist_secondary=dict(single=ds_s, cascade=ds_c, mag=D_SECONDARY),
        dist_primary=dict(single=dp_s, cascade=dp_c, mag=D_PRIMARY),
        disturbance_time=DIST_TIME,
    )
    class E(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, (np.floating,)): return float(o)
            if isinstance(o, (np.integer,)): return int(o)
            if isinstance(o, np.ndarray): return o.tolist()
            return super().default(o)
    with open(os.path.join(os.path.dirname(OUT), "simulation_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, cls=E, ensure_ascii=False, indent=2)
    print("仿真数据已保存: simulation_results.json")
    print("=" * 66)

# 方法3：普通前馈 + 串级 PID 曝气 DO 控制仿真

## 1. 文件说明

本文件夹在原有方法1、方法2基础上，新增方法3“普通前馈 + 串级 PID”的 MATLAB 与 Python 双平台仿真。

新增文件如下：

| 文件 | 作用 |
|---|---|
| `python/sim_method3_feedforward_cascade.py` | 方法3 Python 仿真脚本，运行后生成数据和图片 |
| `matlab/sim_method3_feedforward_cascade.m` | 方法3 MATLAB 仿真脚本，运行后生成数据和图片 |
| `方法3_普通前馈串级PID_README.md` | 方法3仿真说明文件 |

Python 输出结果位于：

```text
python/figures/
```

MATLAB 输出结果位于：

```text
matlab/figures/
```

## 2. 控制目标

污水好氧池曝气控制的目标是维持水体溶解氧 DO 在设定值附近。本仿真中：

```text
DO 设定值 = 2.0 mg/L
```

当进水流量或污染物浓度升高时，水体耗氧量增大，DO 会下降。方法3引入进水侧可测扰动作为前馈信号，在 DO 明显下降前提前增加供气量，从而提升系统快速性。

## 3. 控制结构

方法3采用：

```text
普通前馈 + DO外环PID + 供气流量内环PID
```

结构为：

```text
进水流量 Q、污染物浓度 C
        |
        v
耗氧负荷前馈模型 ---> 前馈供气量 q_ff
        |                    |
        |                    v
DO设定值 ---> DO外环PID ---> + ---> 目标供气量 ---> 供气流量内环PID ---> 鼓风机/阀门
   ^                                                                           |
   |                                                                           v
   +------------------------------- 好氧池 DO 对象 <---------------------- 实际供气流量
```

各部分作用如下：

- 前馈模型：根据进水流量和污染物浓度估算当前耗氧负荷，提前给出供气补偿；
- DO 外环 PID：根据 DO 偏差进行反馈微调，消除前馈模型误差和不可测扰动；
- 供气流量内环 PID：快速调节鼓风机变频器或空气阀门，使实际供气量跟踪目标供气量。

## 4. 仿真模型

### 4.1 供气侧对象

鼓风机/阀门指令到实际供气流量采用一阶惯性模型：

```text
G2(s) = 1 / (15s + 1)
```

### 4.2 DO 主对象

供气流量到 DO 的过程采用一阶惯性加纯滞后模型：

```text
G1(s) = 4 * exp(-30s) / (180s + 1)
```

离散仿真中，DO 更新方程为：

```text
dDO/dt = [4 * q_delay - DO + d_load] / 180
```

其中：

- `q_delay` 为经过 30 s 纯滞后的实际供气量；
- `d_load` 为进水耗氧负荷扰动，负值表示耗氧增加导致 DO 下降。

### 4.3 进水负荷扰动

扰动在 `t = 1200 s` 加入：

```text
进水流量 Q:       1.00 -> 1.20
污染物浓度 C:     1.00 -> 1.40
```

真实耗氧负荷模型为：

```text
d_load = -[1.20 * (Q - Q0) + 1.60 * (C - C0)]
```

前馈模型采用工程近似：

```text
q_ff = q_base + [1.05 * (Q_meas - Q0) + 1.35 * (C_meas - C0)] / 4
```

这里故意使前馈模型与真实对象不完全一致，并加入 35 s 的测量滤波时间常数，用于体现普通前馈模型存在误差，仍需要 DO 反馈回路进行校正。

## 5. 运行方式

### 5.1 Python 运行

进入项目根目录后运行：

```powershell
cd python
python sim_method3_feedforward_cascade.py
```

运行后生成：

```text
python/method3_simulation_results.csv
python/method3_metrics.csv
python/figures/method3_fig1_do_disturbance_response.png
python/figures/method3_fig2_air_setpoint.png
python/figures/method3_fig3_feedforward_signals.png
python/figures/method3_fig4_control_signal.png
python/figures/method3_fig5_cascade_inner_loop.png
python/figures/method3_fig6_load_disturbance.png
python/figures/method3_fig7_performance_bar.png
```

### 5.2 MATLAB 运行

用 MATLAB 打开：

```text
matlab/sim_method3_feedforward_cascade.m
```

直接按 F5 运行。

运行后生成：

```text
matlab/method3_simulation_results.csv
matlab/method3_metrics.csv
matlab/figures/method3_fig1_do_disturbance_response.png
matlab/figures/method3_fig2_air_setpoint.png
matlab/figures/method3_fig3_feedforward_signals.png
matlab/figures/method3_fig4_control_signal.png
matlab/figures/method3_fig5_cascade_inner_loop.png
matlab/figures/method3_fig6_load_disturbance.png
matlab/figures/method3_fig7_performance_bar.png
```

## 6. 图片说明

### 6.1 `method3_fig1_do_disturbance_response.png`

该图比较串级 PID 和普通前馈 + 串级 PID 在进水负荷阶跃扰动下的 DO 响应。扰动发生后，普通串级 PID 需要等待 DO 下降后再通过反馈调节供气量，因此 DO 下跌较深、恢复较慢。加入前馈后，系统根据进水流量和污染物浓度提前提高供气量，DO 最低值更高，恢复更快。

### 6.2 `method3_fig2_air_setpoint.png`

该图展示目标供气量信号。普通串级 PID 的目标供气量由 DO 外环反馈产生，变化滞后于 DO 偏差；普通前馈 + 串级 PID 则在检测到进水负荷变化后，直接提高前馈供气量，使目标供气量提前上升。

### 6.3 `method3_fig3_feedforward_signals.png`

该图展示前馈通道的输入和输出。进水流量与污染物浓度在扰动时刻上升，前馈模型据此估算耗氧负荷增加，并输出更高的前馈供气量。它说明前馈补偿是由进水侧可测扰动计算得到的。

### 6.4 `method3_fig4_control_signal.png`

该图展示鼓风机变频指令或阀门开度。前馈 + 串级 PID 在扰动刚出现时控制指令更快上升，表示系统提前增加供气强度。该方法用短时间内略高的供气量换取更小的 DO 偏差。

### 6.5 `method3_fig5_cascade_inner_loop.png`

该图展示供气流量内环的跟踪效果。前馈通道给出新的目标供气量后，供气流量内环快速调节鼓风机或阀门，使实际供气量跟踪目标供气量。由于供气侧对象存在惯性，实际供气量会平滑上升。

### 6.6 `method3_fig6_load_disturbance.png`

该图展示仿真的扰动来源。进水流量和污染物浓度升高导致耗氧负荷增加，上半图中的负向扰动表示 DO 被额外消耗。该图用于说明方法3主要针对的是耗氧端扰动。

### 6.7 `method3_fig7_performance_bar.png`

该图比较最大偏差、恢复时间、IAE 和控制能量。普通前馈 + 串级 PID 的最大 DO 偏差更小，恢复时间更短，IAE 更低，说明抗扰动性能更好；同时控制能量略高，说明前馈提前补偿会带来一定能耗增加。

## 7. 仿真结论

普通前馈 + 串级 PID 相比单纯串级 PID 的主要优势是对进水耗氧负荷扰动响应更快。当前馈模型检测到进水流量和污染物浓度升高后，会提前提高目标供气量，使供气内环提前动作，从而减少 DO 的下跌幅度并缩短恢复时间。

由于前馈模型难以完全准确，且在线仪表存在测量滤波和滞后，因此前馈控制不能单独使用，仍需要 DO 外环反馈回路消除模型误差和不可测扰动。该方法适合用于进水流量、COD、氨氮等扰动变量能够在线测量或近似估算的污水处理曝气系统。

# 污水处理曝气溶解氧（DO）控制仿真

本仓库为过程控制课程大作业项目，研究污水处理好氧池曝气过程中的溶解氧（DO）控制问题。  
控制目标是在满足净水需要的前提下，使 DO 稳定在设定值附近，并尽量降低曝气能耗。

项目包含三种控制方法的仿真与报告：

1. 方法1：单回路 PID
2. 方法2：串级 PID
3. 方法3：普通前馈 + 串级 PID

其中方法1、方法2用于比较单回路与串级控制结构的差异；方法3进一步引入进水流量和污染物浓度前馈补偿，用于改善进水耗氧负荷突变时的快速性。

---

## 1. 项目目录结构

```text
过控_曝气溶解氧控制/
├─ README.md
├─ 污水曝气溶解氧控制仿真实验报告.docx
├─ 方法3_普通前馈串级PID仿真实验报告.docx
├─ 方法3_普通前馈串级PID_README.md
├─ create_method3_report.py
├─ python/
│  ├─ aeration_do_sim.py
│  ├─ sim_method3_feedforward_cascade.py
│  ├─ generate_report.py
│  ├─ simulation_results.json
│  ├─ method3_metrics.csv
│  ├─ method3_simulation_results.csv
│  └─ figures/
│     ├─ fig1_step_response.png
│     ├─ fig2_disturb_secondary.png
│     ├─ fig3_disturb_primary.png
│     ├─ fig4_control_signal.png
│     ├─ fig5_cascade_signals.png
│     ├─ fig6_performance_bar.png
│     ├─ fig7_structure.png
│     ├─ method3_fig1_do_disturbance_response.png
│     ├─ method3_fig2_air_setpoint.png
│     ├─ method3_fig3_feedforward_signals.png
│     ├─ method3_fig4_control_signal.png
│     ├─ method3_fig5_cascade_inner_loop.png
│     ├─ method3_fig6_load_disturbance.png
│     └─ method3_fig7_performance_bar.png
└─ matlab/
   ├─ aeration_do_sim.m
   ├─ sim_method3_feedforward_cascade.m
   ├─ build_simulink_models.m
   ├─ build_method3_simulink_model.m
   ├─ draw_method3_simulink_diagram.py
   ├─ do_single_loop.slx
   ├─ do_cascade.slx
   ├─ do_feedforward_cascade.slx
   ├─ Simulink搭建与使用说明.md
   ├─ 方法3_Simulink搭建与使用说明.md
   ├─ method3_metrics.csv
   ├─ method3_simulation_results.csv
   └─ figures/
      ├─ do_single_loop_diagram.png
      ├─ do_cascade_diagram.png
      ├─ do_feedforward_cascade_diagram.png
      ├─ fig1_step_response.png
      ├─ fig2_disturb_secondary.png
      ├─ fig3_disturb_primary.png
      ├─ fig4_control_signal.png
      ├─ fig5_cascade_signals.png
      ├─ fig6_performance_bar.png
      ├─ method3_fig1_do_disturbance_response.png
      ├─ method3_fig2_air_setpoint.png
      ├─ method3_fig3_feedforward_signals.png
      ├─ method3_fig4_control_signal.png
      ├─ method3_fig5_cascade_inner_loop.png
      ├─ method3_fig6_load_disturbance.png
      └─ method3_fig7_performance_bar.png
```

---

## 2. 被控对象模型

污水好氧池中 DO 的变化由供氧和耗氧共同决定：

- 供氧端：鼓风机或空气阀门调节供气量；
- 耗氧端：进水流量、污染物浓度变化引起耗氧负荷变化。

仿真中采用工程简化模型。

供气侧对象：

```text
G2(s) = 1 / (15s + 1)
```

DO 主对象：

```text
G1(s) = 4 * exp(-30s) / (180s + 1)
```

DO 设定值：

```text
SP = 2.0 mg/L
```

---

## 3. 控制方法

### 方法1：单回路 PID

DO 传感器将实时测量值反馈给 PID 控制器，PID 直接输出鼓风机变频指令或阀门开度。

```text
DO设定值 -> PID -> 鼓风机/阀门 -> 供气 -> 水体DO
      ^                                      |
      |______________________________________|
```

特点：

- 结构简单；
- 可以实现基本 DO 控制；
- 对供气侧扰动和进水负荷扰动响应较慢。

### 方法2：串级 PID

外环控制 DO，内环控制供气流量。

```text
DO外环PID -> 目标供气量 -> 供气流量内环PID -> 鼓风机/阀门
```

特点：

- 内环能快速抑制供气母管压力波动、支路抢气等供气侧扰动；
- 相比单回路 PID，串级 PID 对供气侧扰动的抑制效果明显更好；
- 对进水耗氧负荷突变仍然需要等待 DO 偏差出现后才反馈调节。

### 方法3：普通前馈 + 串级 PID

在串级 PID 基础上增加进水流量和污染物浓度前馈补偿。

```text
进水流量Q、污染物浓度C
        |
        v
耗氧负荷前馈模型 -> 前馈供气量
                         |
DO外环PID反馈修正 --------+
                         v
                    目标供气量 -> 供气流量内环PID -> 鼓风机/阀门
```

特点：

- 当前馈模型检测到进水耗氧负荷增加时，提前提高目标供气量；
- DO 外环反馈用于修正前馈模型误差；
- 相比单纯串级 PID，方法3对进水负荷扰动的快速性更好。

---

## 4. 如何运行

### 4.1 Python 仿真

进入 `python/` 目录：

```powershell
cd python
```

运行方法1、方法2仿真：

```powershell
python aeration_do_sim.py
```

运行方法3仿真：

```powershell
python sim_method3_feedforward_cascade.py
```

生成方法1、方法2报告：

```powershell
python generate_report.py
```

生成方法3 Word 报告：

```powershell
cd ..
python create_method3_report.py
```

### 4.2 MATLAB 仿真

进入 `matlab/` 目录。

运行方法1、方法2数值仿真：

```matlab
aeration_do_sim
```

运行方法3数值仿真：

```matlab
sim_method3_feedforward_cascade
```

一键生成方法1、方法2 Simulink 模型：

```matlab
build_simulink_models
```

一键生成方法3 Simulink 模型：

```matlab
build_method3_simulink_model
```

方法3模型生成后会得到：

```text
matlab/do_feedforward_cascade.slx
matlab/figures/do_feedforward_cascade_diagram.png
```

---

## 5. 方法3仿真结果

进水扰动设置：

```text
t = 1200 s
进水流量 Q:   1.00 -> 1.20
污染物浓度 C: 1.00 -> 1.40
```

方法3与普通串级 PID 的指标对比如下：

| 控制方法 | 最低 DO / mg/L | 最大偏差 / mg/L | 恢复时间 / s | IAE | 控制能量 |
|---|---:|---:|---:|---:|---:|
| 串级 PID | 1.783 | 0.217 | 448.5 | 66.79 | 613.42 |
| 普通前馈 + 串级 PID | 1.818 | 0.182 | 240.0 | 36.48 | 628.32 |

结论：

- 加入前馈后，DO 最低值由 1.783 mg/L 提高到 1.818 mg/L；
- 最大 DO 偏差由 0.217 mg/L 降低到 0.182 mg/L；
- 恢复时间由 448.5 s 缩短到 240.0 s；
- IAE 由 66.79 降低到 36.48；
- 控制能量略有增加，说明前馈通过提前供气换取了更好的 DO 稳定性。

---

## 6. 主要报告文件

| 文件 | 内容 |
|---|---|
| `污水曝气溶解氧控制仿真实验报告.docx` | 方法1、方法2综合仿真实验报告 |
| `方法3_普通前馈串级PID仿真实验报告.docx` | 方法3普通前馈 + 串级 PID 独立报告 |
| `方法3_普通前馈串级PID_README.md` | 方法3数值仿真说明 |
| `matlab/方法3_Simulink搭建与使用说明.md` | 方法3 Simulink 搭建与一键生成说明 |

---

## 7. 核心结论

单回路 PID 能实现基本 DO 控制，但对供气侧扰动和进水耗氧负荷扰动响应较慢。串级 PID 通过增加供气流量内环，显著提升了对供气侧扰动的抑制能力。普通前馈 + 串级 PID 进一步引入进水流量和污染物浓度信息，能够在 DO 明显下降之前提前补偿供气量，因此在进水负荷突变工况下具有更好的快速性和抗扰动能力。

总体来看：

- 方法1适合基础控制结构演示；
- 方法2适合解决供气侧扰动问题；
- 方法3适合解决进水耗氧负荷扰动响应滞后的问题。

# 污水处理曝气溶解氧（DO）控制仿真

过程控制大作业 —— 对应《过控提纲》**方法1：单回路PID**、**方法2：串级PID**。
被控对象为污水好氧池溶解氧控制（供气流量副对象 + 溶解氧主对象FOPDT），
在 **MATLAB 2024b** 与 **Python** 双平台仿真，结果一致。

## 目录结构

```
过控_曝气溶解氧控制/
├─ 污水曝气溶解氧控制仿真实验报告.docx   ← 最终实验报告（含全部图表）
├─ README.md
├─ python/                               ← Python 仿真（PyCharm + conda base）
│   ├─ aeration_do_sim.py                ← 主仿真：模型/两种PID/三组实验/出图/存JSON
│   ├─ generate_report.py                ← 读取结果与图片，生成 Word 报告
│   ├─ simulation_results.json           ← 仿真结果数据
│   └─ figures/                          ← 7 张结果图
└─ matlab/                               ← MATLAB 2024b
    ├─ aeration_do_sim.m                 ← 与 Python 等价的 .m 脚本（直接 F5 运行）
    ├─ build_simulink_models.m           ← 一键生成两个 Simulink 模型
    ├─ do_single_loop.slx                ← 方法1 单回路PID 模型
    ├─ do_cascade.slx                    ← 方法2 串级PID 模型
    ├─ Simulink搭建与使用说明.md
    └─ figures/                          ← MATLAB 出图 + Simulink 框图
```

## 如何运行

### Python（PyCharm）
1. 解释器选 conda `base` 环境（已装 numpy / matplotlib / python-docx）；
2. 运行 `python/aeration_do_sim.py` → 生成 `figures/` 和 `simulation_results.json`；
3. 运行 `python/generate_report.py` → 生成根目录的 Word 报告。

### MATLAB 2024b
- 运行 `matlab/aeration_do_sim.m`：打印性能指标并在 `matlab/figures/` 出图；
- 运行 `matlab/build_simulink_models.m`：生成两个 `.slx`，双击打开点运行看示波器。
  扰动复现见 `matlab/Simulink搭建与使用说明.md`。

## 核心结论
- 设定值跟踪：串级超调更小（9.4% vs 14.1%），不劣于单回路；
- **二次扰动（供气母管压力波动）：串级最大偏差 0.007 mg/L vs 单回路 0.176 mg/L —— 串级核心优势**；
- 一次扰动（进水耗氧负荷）：二者相近（该扰动在副回路之外），需前馈（方法3/4）进一步改善。

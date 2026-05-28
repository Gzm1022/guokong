%% 一键生成方法3 Simulink模型：普通前馈 + 串级 PID 曝气 DO 控制
%  生成文件：do_feedforward_cascade.slx
%
%  使用方法：
%    1. 用 MATLAB 打开本文件；
%    2. 按 F5 运行；
%    3. 当前 matlab 文件夹下会生成 do_feedforward_cascade.slx；
%    4. 双击模型，点击运行即可查看 Scope 和 To Workspace 输出。
%
%  模型结构：
%    Q、C -> 前馈模型 -> q_ff
%    DO设定 - DO反馈 -> DO外环PID -> feedback trim
%    q_ff + trim -> 目标供气量 -> 流量内环PID -> G2 -> Delay -> K1 -> G1 -> DO

clc;
here = fileparts(mfilename('fullpath'));

%% 公共参数，与 sim_method3_feedforward_cascade.m 保持一致
p.SP = 2.0;
p.Kair = 4.0;
p.Tflow = 15.0;
p.Tdo = 180.0;
p.delay = 30.0;
p.tStop = 2400;
p.tDist = 1200;

p.Q0 = 1.0;
p.C0 = 1.0;
p.QFinal = 1.20;
p.CFinal = 1.40;
p.tauFFMeasure = 35.0;

p.kQTrue = 1.20;
p.kCTrue = 1.60;
p.kQModel = 1.05;
p.kCModel = 1.35;
p.baseAir = p.SP / p.Kair;

% 方法3控制器参数
% DO外环输出为“反馈修正量”，限幅 [-0.25, 0.25]
p.KpOut = 0.26;
p.KiOut = 0.0015;
p.KdOut = 8.0;

% 供气流量内环输出为鼓风机/阀门指令，限幅 [0, 1]
p.KpIn = 4.0;
p.KiIn = 0.60;
p.KdIn = 0.0;

build_method3(fullfile(here, 'do_feedforward_cascade'), p, here);
disp('方法3 Simulink模型已生成：do_feedforward_cascade.slx');

%% ======================= 模型搭建函数 =======================
function build_method3(path, p, here)
    mdl = 'do_feedforward_cascade';
    close_all(mdl);
    new_system(mdl);

    % ---------------- 主反馈串级通道 ----------------
    add(mdl,'Sources/Step','SP',[30 240 60 270], ...
        'Time','0','Before','0','After',num2str(p.SP));
    add(mdl,'Math Operations/Sum','Err_DO',[120 235 150 275], 'Inputs','+-');
    add(mdl,'Continuous/PID Controller','PID_DO_outer',[200 220 290 290]);
    cfgPID(mdl,'PID_DO_outer',p.KpOut,p.KiOut,p.KdOut,-0.25,0.25);

    add(mdl,'Math Operations/Sum','Add_FF_Trim',[350 235 385 275], 'Inputs','++');
    add(mdl,'Discontinuities/Saturation','Sat_Air_SP',[425 230 485 280], ...
        'UpperLimit','1','LowerLimit','0');

    add(mdl,'Math Operations/Sum','Err_Flow',[535 235 565 275], 'Inputs','+-');
    add(mdl,'Continuous/PID Controller','PID_flow_inner',[620 220 710 290]);
    cfgPID(mdl,'PID_flow_inner',p.KpIn,p.KiIn,p.KdIn,0,1);

    add(mdl,'Math Operations/Sum','AddSec',[760 235 790 275], 'Inputs','++');
    add(mdl,'Continuous/Transfer Fcn','G2_air_flow',[850 230 950 280], ...
        'Numerator','[1]','Denominator',['[' num2str(p.Tflow) ' 1]']);
    add(mdl,'Continuous/Transport Delay','Delay',[1010 230 1090 280], ...
        'DelayTime',num2str(p.delay),'BufferSize','8192');
    add(mdl,'Math Operations/Gain','Kair',[1140 238 1190 272], ...
        'Gain',num2str(p.Kair));
    add(mdl,'Math Operations/Sum','AddPri',[1240 235 1270 275], 'Inputs','++');
    add(mdl,'Continuous/Transfer Fcn','G1_DO',[1325 230 1435 280], ...
        'Numerator','[1]','Denominator',['[' num2str(p.Tdo) ' 1]']);
    add(mdl,'Sinks/Scope','Scope_DO',[1500 230 1545 280]);

    add(mdl,'Sinks/To Workspace','DO_out',[1500 325 1585 355], ...
        'VariableName','DO_method3','SaveFormat','Structure With Time');
    add(mdl,'Sinks/To Workspace','AirSP_out',[500 330 600 360], ...
        'VariableName','AirSP_method3','SaveFormat','Structure With Time');
    add(mdl,'Sinks/To Workspace','AirFlow_out',[960 330 1070 360], ...
        'VariableName','AirFlow_method3','SaveFormat','Structure With Time');
    add(mdl,'Sinks/To Workspace','U_out',[720 330 805 360], ...
        'VariableName','U_method3','SaveFormat','Structure With Time');

    % ---------------- 进水扰动源 ----------------
    add(mdl,'Sources/Step','Q_in',[30 45 60 75], ...
        'Time',num2str(p.tDist),'Before',num2str(p.Q0),'After',num2str(p.QFinal));
    add(mdl,'Sources/Step','C_in',[30 130 60 160], ...
        'Time',num2str(p.tDist),'Before',num2str(p.C0),'After',num2str(p.CFinal));
    add(mdl,'Sinks/To Workspace','Q_out',[120 25 200 55], ...
        'VariableName','Q_method3','SaveFormat','Structure With Time');
    add(mdl,'Sinks/To Workspace','C_out',[120 110 200 140], ...
        'VariableName','C_method3','SaveFormat','Structure With Time');

    % ---------------- 前馈估算模型：q_ff = base + [(kQ*(Qm-Q0)+kC*(Cm-C0))/Kair] ----------------
    add(mdl,'Continuous/Transfer Fcn','Q_measure_filter',[110 45 205 75], ...
        'Numerator','[1]','Denominator',['[' num2str(p.tauFFMeasure) ' 1]']);
    add(mdl,'Continuous/Transfer Fcn','C_measure_filter',[110 130 205 160], ...
        'Numerator','[1]','Denominator',['[' num2str(p.tauFFMeasure) ' 1]']);
    add(mdl,'Sources/Constant','Q0_ff',[230 88 270 112], 'Value',num2str(p.Q0));
    add(mdl,'Sources/Constant','C0_ff',[230 173 270 197], 'Value',num2str(p.C0));
    add(mdl,'Math Operations/Sum','Q_dev_ff',[300 45 330 85], 'Inputs','+-');
    add(mdl,'Math Operations/Sum','C_dev_ff',[300 130 330 170], 'Inputs','+-');
    add(mdl,'Math Operations/Gain','KQ_model',[370 47 435 83], 'Gain',num2str(p.kQModel));
    add(mdl,'Math Operations/Gain','KC_model',[370 132 435 168], 'Gain',num2str(p.kCModel));
    add(mdl,'Math Operations/Sum','Load_model_sum',[480 85 515 125], 'Inputs','++');
    add(mdl,'Math Operations/Gain','Divide_Kair',[555 88 625 122], 'Gain',num2str(1/p.Kair));
    add(mdl,'Sources/Constant','Base_air',[555 145 625 175], 'Value',num2str(p.baseAir));
    add(mdl,'Math Operations/Sum','FF_air_sum',[665 100 700 140], 'Inputs','++');
    add(mdl,'Sinks/To Workspace','FF_out',[725 95 825 125], ...
        'VariableName','FFAir_method3','SaveFormat','Structure With Time');

    % ---------------- 真实耗氧扰动：d_load = -[(1.2*(Q-Q0)+1.6*(C-C0))] ----------------
    add(mdl,'Sources/Constant','Q0_true',[230 365 270 389], 'Value',num2str(p.Q0));
    add(mdl,'Sources/Constant','C0_true',[230 450 270 474], 'Value',num2str(p.C0));
    add(mdl,'Math Operations/Sum','Q_dev_true',[300 325 330 365], 'Inputs','+-');
    add(mdl,'Math Operations/Sum','C_dev_true',[300 410 330 450], 'Inputs','+-');
    add(mdl,'Math Operations/Gain','KQ_true',[370 327 435 363], 'Gain',num2str(p.kQTrue));
    add(mdl,'Math Operations/Gain','KC_true',[370 412 435 448], 'Gain',num2str(p.kCTrue));
    add(mdl,'Math Operations/Sum','Load_true_sum',[480 365 515 405], 'Inputs','++');
    add(mdl,'Math Operations/Gain','Neg_load',[555 368 625 402], 'Gain','-1');
    add(mdl,'Sinks/To Workspace','Load_out',[650 368 755 398], ...
        'VariableName','LoadDist_method3','SaveFormat','Structure With Time');

    % ---------------- 可选供气侧扰动，默认不启用 ----------------
    add(mdl,'Sources/Step','Dsec',[720 455 750 485], ...
        'Time',num2str(p.tDist),'Before','0','After','0');

    % ---------------- 连线：主通道 ----------------
    cn(mdl,'SP/1','Err_DO/1');
    cn(mdl,'Err_DO/1','PID_DO_outer/1');
    cn(mdl,'PID_DO_outer/1','Add_FF_Trim/2');
    cn(mdl,'Add_FF_Trim/1','Sat_Air_SP/1');
    cn(mdl,'Sat_Air_SP/1','Err_Flow/1');
    cn(mdl,'Sat_Air_SP/1','AirSP_out/1');
    cn(mdl,'Err_Flow/1','PID_flow_inner/1');
    cn(mdl,'PID_flow_inner/1','AddSec/1');
    cn(mdl,'PID_flow_inner/1','U_out/1');
    cn(mdl,'Dsec/1','AddSec/2');
    cn(mdl,'AddSec/1','G2_air_flow/1');
    cn(mdl,'G2_air_flow/1','Delay/1');
    cn(mdl,'G2_air_flow/1','AirFlow_out/1');
    cn(mdl,'Delay/1','Kair/1');
    cn(mdl,'Kair/1','AddPri/1');
    cn(mdl,'AddPri/1','G1_DO/1');
    cn(mdl,'G1_DO/1','Scope_DO/1');
    cn(mdl,'G1_DO/1','DO_out/1');
    cn(mdl,'G1_DO/1','Err_DO/2');        % DO主反馈
    cn(mdl,'G2_air_flow/1','Err_Flow/2');% 供气流量副反馈

    % ---------------- 连线：扰动源与前馈模型 ----------------
    cn(mdl,'Q_in/1','Q_measure_filter/1');
    cn(mdl,'C_in/1','C_measure_filter/1');
    cn(mdl,'Q_in/1','Q_out/1');
    cn(mdl,'C_in/1','C_out/1');

    cn(mdl,'Q_measure_filter/1','Q_dev_ff/1');
    cn(mdl,'Q0_ff/1','Q_dev_ff/2');
    cn(mdl,'C_measure_filter/1','C_dev_ff/1');
    cn(mdl,'C0_ff/1','C_dev_ff/2');
    cn(mdl,'Q_dev_ff/1','KQ_model/1');
    cn(mdl,'C_dev_ff/1','KC_model/1');
    cn(mdl,'KQ_model/1','Load_model_sum/1');
    cn(mdl,'KC_model/1','Load_model_sum/2');
    cn(mdl,'Load_model_sum/1','Divide_Kair/1');
    cn(mdl,'Divide_Kair/1','FF_air_sum/1');
    cn(mdl,'Base_air/1','FF_air_sum/2');
    cn(mdl,'FF_air_sum/1','Add_FF_Trim/1');
    cn(mdl,'FF_air_sum/1','FF_out/1');

    % ---------------- 连线：真实耗氧扰动 ----------------
    cn(mdl,'Q_in/1','Q_dev_true/1');
    cn(mdl,'Q0_true/1','Q_dev_true/2');
    cn(mdl,'C_in/1','C_dev_true/1');
    cn(mdl,'C0_true/1','C_dev_true/2');
    cn(mdl,'Q_dev_true/1','KQ_true/1');
    cn(mdl,'C_dev_true/1','KC_true/1');
    cn(mdl,'KQ_true/1','Load_true_sum/1');
    cn(mdl,'KC_true/1','Load_true_sum/2');
    cn(mdl,'Load_true_sum/1','Neg_load/1');
    cn(mdl,'Neg_load/1','AddPri/2');
    cn(mdl,'Neg_load/1','Load_out/1');

    % ---------------- 模型截图与保存 ----------------
    set_param(mdl, 'StopTime', num2str(p.tStop), 'Solver', 'ode45');
    figDir = fullfile(here, 'figures');
    if ~exist(figDir, 'dir')
        mkdir(figDir);
    end
    try
        set_param(mdl, 'ZoomFactor', 'FitSystem');
        print(['-s' mdl], '-dpng', '-r180', fullfile(figDir, 'do_feedforward_cascade_diagram.png'));
    catch ME
        warning('模型截图保存失败：%s', ME.message);
    end
    save_system(mdl, [path '.slx']);
    close_system(mdl, 0);
end

%% ======================= 工具函数 =======================
function add(mdl, libtail, name, pos, varargin)
    add_block(['simulink/' libtail], [mdl '/' name], 'Position', pos);
    for k = 1:2:numel(varargin)
        set_param([mdl '/' name], varargin{k}, varargin{k+1});
    end
end

function cfgPID(mdl, blk, Kp, Ki, Kd, lo, hi)
    full = [mdl, '/', blk];
    set_param(full, 'Controller','PID', ...
        'P',num2str(Kp), 'I',num2str(Ki), 'D',num2str(Kd), 'N','2');
    set_param(full, 'LimitOutput','on', ...
        'UpperSaturationLimit',num2str(hi), ...
        'LowerSaturationLimit',num2str(lo), ...
        'AntiWindupMode','clamping');
end

function cn(mdl, src, dst)
    add_line(mdl, src, dst, 'autorouting','on');
end

function close_all(mdl)
    if bdIsLoaded(mdl)
        close_system(mdl, 0);
    end
end

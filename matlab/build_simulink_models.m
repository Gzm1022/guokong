%% 自动搭建曝气溶解氧控制的两个 Simulink 模型 (MATLAB/Simulink 2024b)
%   do_single_loop.slx  —— 方法1 单回路PID
%   do_cascade.slx      —— 方法2 串级PID
%
%  运行本脚本(F5)即可在当前文件夹自动生成并保存这两个 .slx 模型，
%  随后双击 .slx 打开、点“运行”即可看到响应曲线（示波器）。
%  扰动 Step 默认幅值为 0（不起作用）；要复现扰动实验，按下方说明把
%  对应 Step 模块的 Final value 改成 -0.18(供气二次扰动) 或 -1.0(耗氧一次扰动)。
%
%  模型参数与 aeration_do_sim.m / .py 完全一致：
%     G2(供气流量) = 1/(15s+1)，纯滞后 30s，K1 增益=4，G1(DO)=1/(180s+1)
% =========================================================================
clc;
here = fileparts(mfilename('fullpath'));

% ---------- 公共参数 ----------
p.T2=15; p.tau=30; p.K1=4; p.T1=180; p.SP=2; p.tStop=2400; p.tDist=1200;
% 单回路 PID
p.Kp=0.70; p.Ki=0.0040; p.Kd=15.0;
% 串级 外环/内环
p.Kp1=0.52; p.Ki1=0.0034; p.Kd1=20.0;
p.Kp2=4.0;  p.Ki2=0.60;   p.Kd2=0.0;

build_single(fullfile(here,'do_single_loop'), p);
build_cascade(fullfile(here,'do_cascade'), p);
disp('两个 Simulink 模型已生成：do_single_loop.slx 与 do_cascade.slx');

% =========================================================================
function build_single(path, p)
    mdl = 'do_single_loop';
    close_all(mdl); new_system(mdl);
    add(mdl,'Sources/Step','SP',[20 100 50 130], 'Time','0','Before','0','After',num2str(p.SP));
    add(mdl,'Math Operations/Sum','Err',[100 100 130 130], 'Inputs','+-');
    add(mdl,'Continuous/PID Controller','PID',[170 90 240 140]);
    cfgPID(mdl,'PID', p.Kp, p.Ki, p.Kd);
    add(mdl,'Math Operations/Sum','AddSec',[290 100 320 130], 'Inputs','++');
    add(mdl,'Sources/Step','Dsec',[270 190 300 220], 'Time',num2str(p.tDist),'Before','0','After','0');
    add(mdl,'Continuous/Transfer Fcn','G2',[360 95 440 135], 'Numerator','[1]','Denominator',['[' num2str(p.T2) ' 1]']);
    add(mdl,'Continuous/Transport Delay','Delay',[470 95 540 135], 'DelayTime',num2str(p.tau),'BufferSize','8192');
    add(mdl,'Math Operations/Gain','K1',[570 100 600 130], 'Gain',num2str(p.K1));
    add(mdl,'Math Operations/Sum','AddPri',[630 100 660 130], 'Inputs','++');
    add(mdl,'Sources/Step','Dpri',[610 190 640 220], 'Time',num2str(p.tDist),'Before','0','After','0');
    add(mdl,'Continuous/Transfer Fcn','G1',[700 95 780 135], 'Numerator','[1]','Denominator',['[' num2str(p.T1) ' 1]']);
    add(mdl,'Sinks/Scope','Scope',[830 95 870 135]);
    add(mdl,'Sinks/To Workspace','DO',[830 180 900 210], 'VariableName','DO_single','SaveFormat','Structure With Time');
    % 连线
    cn(mdl,'SP/1','Err/1'); cn(mdl,'Err/1','PID/1'); cn(mdl,'PID/1','AddSec/1');
    cn(mdl,'Dsec/1','AddSec/2'); cn(mdl,'AddSec/1','G2/1'); cn(mdl,'G2/1','Delay/1');
    cn(mdl,'Delay/1','K1/1'); cn(mdl,'K1/1','AddPri/1'); cn(mdl,'Dpri/1','AddPri/2');
    cn(mdl,'AddPri/1','G1/1'); cn(mdl,'G1/1','Scope/1'); cn(mdl,'G1/1','DO/1');
    cn(mdl,'G1/1','Err/2');
    finalize(mdl, p.tStop, path);
end

function build_cascade(path, p)
    mdl = 'do_cascade';
    close_all(mdl); new_system(mdl);
    add(mdl,'Sources/Step','SP',[20 100 50 130], 'Time','0','Before','0','After',num2str(p.SP));
    add(mdl,'Math Operations/Sum','Err1',[100 100 130 130], 'Inputs','+-');     % 外环偏差
    add(mdl,'Continuous/PID Controller','PIDout',[170 90 240 140]);             % 主控制器(DO)
    cfgPID(mdl,'PIDout', p.Kp1, p.Ki1, p.Kd1);
    add(mdl,'Math Operations/Sum','Err2',[290 100 320 130], 'Inputs','+-');     % 内环偏差
    add(mdl,'Continuous/PID Controller','PIDin',[360 90 430 140]);             % 副控制器(流量)
    cfgPID(mdl,'PIDin', p.Kp2, p.Ki2, p.Kd2);
    add(mdl,'Math Operations/Sum','AddSec',[470 100 500 130], 'Inputs','++');
    add(mdl,'Sources/Step','Dsec',[450 200 480 230], 'Time',num2str(p.tDist),'Before','0','After','0');
    add(mdl,'Continuous/Transfer Fcn','G2',[540 95 620 135], 'Numerator','[1]','Denominator',['[' num2str(p.T2) ' 1]']);
    add(mdl,'Continuous/Transport Delay','Delay',[660 95 730 135], 'DelayTime',num2str(p.tau),'BufferSize','8192');
    add(mdl,'Math Operations/Gain','K1',[760 100 790 130], 'Gain',num2str(p.K1));
    add(mdl,'Math Operations/Sum','AddPri',[820 100 850 130], 'Inputs','++');
    add(mdl,'Sources/Step','Dpri',[800 200 830 230], 'Time',num2str(p.tDist),'Before','0','After','0');
    add(mdl,'Continuous/Transfer Fcn','G1',[890 95 970 135], 'Numerator','[1]','Denominator',['[' num2str(p.T1) ' 1]']);
    add(mdl,'Sinks/Scope','Scope',[1010 95 1050 135]);
    add(mdl,'Sinks/To Workspace','DO',[1010 180 1080 210], 'VariableName','DO_cascade','SaveFormat','Structure With Time');
    % 连线
    cn(mdl,'SP/1','Err1/1'); cn(mdl,'Err1/1','PIDout/1'); cn(mdl,'PIDout/1','Err2/1');
    cn(mdl,'Err2/1','PIDin/1'); cn(mdl,'PIDin/1','AddSec/1'); cn(mdl,'Dsec/1','AddSec/2');
    cn(mdl,'AddSec/1','G2/1');
    cn(mdl,'G2/1','Delay/1'); cn(mdl,'G2/1','Err2/2');          % 副回路反馈(供气流量)
    cn(mdl,'Delay/1','K1/1'); cn(mdl,'K1/1','AddPri/1'); cn(mdl,'Dpri/1','AddPri/2');
    cn(mdl,'AddPri/1','G1/1'); cn(mdl,'G1/1','Scope/1'); cn(mdl,'G1/1','DO/1');
    cn(mdl,'G1/1','Err1/2');                                     % 主回路反馈(DO)
    finalize(mdl, p.tStop, path);
end

% ---------- 工具函数 ----------
function add(mdl, libtail, name, pos, varargin)
    add_block(['simulink/' libtail], [mdl '/' name], 'Position', pos);
    for k=1:2:numel(varargin)
        set_param([mdl '/' name], varargin{k}, varargin{k+1});
    end
end

function cfgPID(mdl, blk, Kp, Ki, Kd)
    full = [mdl, '/', blk];
    % 连续 PID；微分滤波系数 N=2(滤波时间常数 0.5s)。
    % 说明：本 Simulink 模型用于直观演示两种控制“结构”，采用连续实时 PID 模块；
    % 报告中的定量指标以数值脚本 aeration_do_sim.m/.py 为准(同参数、同模型)。
    % N 取小值是为避免连续微分在 30s 纯滞后下引入高频增益而产生极限环。
    set_param(full, 'Controller','PID', 'P',num2str(Kp), 'I',num2str(Ki), 'D',num2str(Kd), 'N','2');
    set_param(full, 'LimitOutput','on', 'UpperSaturationLimit','1', 'LowerSaturationLimit','0', ...
              'AntiWindupMode','clamping');
end

function cn(mdl, src, dst)
    add_line(mdl, src, dst, 'autorouting','on');
end

function close_all(mdl)
    if bdIsLoaded(mdl); close_system(mdl,0); end
end

function finalize(mdl, tStop, path)
    set_param(mdl, 'StopTime', num2str(tStop), 'Solver','ode45');
    save_system(mdl, [path '.slx']);
    close_system(mdl, 0);
end

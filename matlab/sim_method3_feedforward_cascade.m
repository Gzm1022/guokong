%% 方法3：普通前馈 + 串级 PID 曝气 DO 控制仿真
%  与 python/sim_method3_feedforward_cascade.py 采用同一模型和参数。
%  运行方式：在 MATLAB 中打开本文件，直接按 F5。
%
%  对比对象：
%    1) 串级 PID：DO 外环 + 供气流量内环
%    2) 普通前馈 + 串级 PID：进水流量/污染物浓度前馈 + DO 反馈微调 + 流量内环

clear; clc; close all;

%% 1. 参数
P.Kair = 4.0;       % 供气流量 -> DO 增益
P.Tdo = 180.0;      % DO 主对象时间常数/s
P.delay = 30.0;     % 纯滞后/s
P.Kblower = 1.0;    % 鼓风机/阀门增益
P.Tflow = 15.0;     % 供气侧时间常数/s
P.SP = 2.0;         % DO 设定值/(mg/L)
P.uMin = 0.0; P.uMax = 1.0;
P.dt = 0.5; P.tEnd = 2400.0; P.tDist = 1200.0;

% 进水扰动：归一化进水流量 Q 和污染物浓度 C 在 tDist 时阶跃上升
P.Q0 = 1.0; P.C0 = 1.0;
P.Qstep = 0.20; P.Cstep = 0.40;

% 真实耗氧负荷模型与前馈估算模型故意不完全一致，体现普通前馈的模型误差
P.kQTrue = 1.20; P.kCTrue = 1.60;
P.kQModel = 1.05; P.kCModel = 1.35;
P.tauFFMeasure = 35.0;  % 前馈测量滤波时间常数/s

%% 2. 仿真
cascade = simulate_method3(P, false);
ff = simulate_method3(P, true);

mc = disturbance_metrics(cascade.t, cascade.DO, cascade.u, P);
mf = disturbance_metrics(ff.t, ff.DO, ff.u, P);

fprintf('================ 方法3 仿真结果 ================\n');
fprintf('%-24s  最低DO   最大偏差   恢复时间   IAE      控制能量\n', '');
fprintf('%-24s  %.3f    %.3f     %7.1f  %7.2f  %8.2f\n', ...
    '串级 PID', mc.minDO, mc.maxErr, mc.recovery, mc.IAE, mc.energy);
fprintf('%-24s  %.3f    %.3f     %7.1f  %7.2f  %8.2f\n', ...
    '普通前馈 + 串级 PID', mf.minDO, mf.maxErr, mf.recovery, mf.IAE, mf.energy);

%% 3. 输出数据
here = fileparts(mfilename('fullpath'));
outdir = fullfile(here, 'figures');
if ~exist(outdir, 'dir'); mkdir(outdir); end

resultTable = table(cascade.t, cascade.Q, cascade.C, cascade.loadDist, ...
    cascade.DO, ff.DO, cascade.airSP, ff.airSP, cascade.airFlow, ff.airFlow, ...
    cascade.u, ff.u, ff.ffAir, ...
    'VariableNames', {'time_s','q_in_norm','c_in_norm','load_disturbance_mgL', ...
    'do_cascade','do_feedforward_cascade','air_sp_cascade','air_sp_feedforward_cascade', ...
    'air_flow_cascade','air_flow_feedforward_cascade','blower_u_cascade', ...
    'blower_u_feedforward_cascade','feedforward_air_base'});
writetable(resultTable, fullfile(here, 'method3_simulation_results.csv'));

metricTable = table( ...
    ["串级 PID"; "普通前馈 + 串级 PID"], ...
    [mc.minDO; mf.minDO], [mc.maxErr; mf.maxErr], [mc.recovery; mf.recovery], ...
    [mc.IAE; mf.IAE], [mc.airIntegral; mf.airIntegral], [mc.energy; mf.energy], ...
    'VariableNames', {'controller','min_do','max_abs_error','recovery_time_s', ...
    'iae_after_dist','air_command_integral','air_command_energy'});
writetable(metricTable, fullfile(here, 'method3_metrics.csv'));

%% 4. 绘图
cB = [0.12 0.47 0.71];
cR = [0.84 0.15 0.16];
cG = [0.17 0.63 0.17];
cO = [1.00 0.50 0.05];
cGray = [0.35 0.35 0.35];

% 图1：DO 响应
f = figure('Color','w','Position',[100 100 920 520]);
plot(cascade.t, cascade.DO, 'Color', cB, 'LineWidth', 1.8); hold on;
plot(ff.t, ff.DO, '--', 'Color', cR, 'LineWidth', 1.8);
yline(P.SP, ':', 'Color', cGray, 'LineWidth', 1.2);
xline(P.tDist, '-.', 'Color', cO, 'LineWidth', 1.2);
xlim([1050 2100]); ylim([1.55 2.08]); grid on;
xlabel('时间 / s'); ylabel('溶解氧 DO / (mg/L)');
title('进水负荷阶跃扰动下的 DO 响应');
legend('串级 PID','普通前馈 + 串级 PID','DO 设定值','负荷阶跃扰动','Location','southeast');
saveas(f, fullfile(outdir, 'method3_fig1_do_disturbance_response.png'));

% 图2：目标供气量
f = figure('Color','w','Position',[100 100 920 520]);
plot(cascade.t, cascade.airSP, 'Color', cB, 'LineWidth', 1.6); hold on;
plot(ff.t, ff.airSP, '--', 'Color', cR, 'LineWidth', 1.6);
plot(ff.t, ff.ffAir, ':', 'Color', cG, 'LineWidth', 1.6);
xline(P.tDist, '-.', 'Color', cO, 'LineWidth', 1.1);
xlim([1050 1800]); ylim([0.44 0.82]); grid on;
xlabel('时间 / s'); ylabel('目标供气量 / 归一化');
title('目标供气量信号对比');
legend('串级 PID 目标供气量','前馈串级 PID 目标供气量','前馈计算供气量','Location','southeast');
saveas(f, fullfile(outdir, 'method3_fig2_air_setpoint.png'));

% 图3：前馈信号
f = figure('Color','w','Position',[100 100 920 760]);
subplot(3,1,1); plot(ff.t, ff.Q, 'Color', cB, 'LineWidth', 1.5); ylabel('进水流量'); title('可测扰动变量与前馈补偿作用'); grid on; xline(P.tDist,'-.','Color',cO);
subplot(3,1,2); plot(ff.t, ff.C, 'Color', cR, 'LineWidth', 1.5); ylabel('污染物浓度'); grid on; xline(P.tDist,'-.','Color',cO);
subplot(3,1,3); plot(ff.t, ff.ffAir, 'Color', cG, 'LineWidth', 1.5); ylabel('前馈供气量'); xlabel('时间 / s'); grid on; xline(P.tDist,'-.','Color',cO);
for ax = findall(f,'Type','axes')'; xlim(ax,[1050 1800]); end
saveas(f, fullfile(outdir, 'method3_fig3_feedforward_signals.png'));

% 图4：控制指令
f = figure('Color','w','Position',[100 100 920 520]);
plot(cascade.t, cascade.u, 'Color', cB, 'LineWidth', 1.5); hold on;
plot(ff.t, ff.u, '--', 'Color', cR, 'LineWidth', 1.5);
xline(P.tDist, '-.', 'Color', cO, 'LineWidth', 1.1);
xlim([1050 1800]); ylim([0.45 0.86]); grid on;
xlabel('时间 / s'); ylabel('鼓风机控制指令 / 归一化');
title('控制量对比');
legend('串级 PID','普通前馈 + 串级 PID','Location','southeast');
saveas(f, fullfile(outdir, 'method3_fig4_control_signal.png'));

% 图5：内环跟踪
f = figure('Color','w','Position',[100 100 920 520]);
plot(cascade.t, cascade.airFlow, 'Color', cB, 'LineWidth', 1.5); hold on;
plot(ff.t, ff.airFlow, '--', 'Color', cR, 'LineWidth', 1.5);
plot(ff.t, ff.airSP, ':', 'Color', cG, 'LineWidth', 1.5);
xline(P.tDist, '-.', 'Color', cO, 'LineWidth', 1.1);
xlim([1050 1800]); ylim([0.46 0.80]); grid on;
xlabel('时间 / s'); ylabel('供气流量 / 归一化');
title('供气流量内环跟踪效果');
legend('串级 PID 实际供气量','前馈串级 PID 实际供气量','前馈串级 PID 目标供气量','Location','southeast');
saveas(f, fullfile(outdir, 'method3_fig5_cascade_inner_loop.png'));

% 图6：扰动来源
f = figure('Color','w','Position',[100 100 920 680]);
subplot(2,1,1); plot(cascade.t, cascade.loadDist, 'Color', cO, 'LineWidth', 1.7); yline(0,':','Color',cGray); xline(P.tDist,'-.','Color',cO); ylabel('耗氧扰动 / mg/L'); title('进水耗氧负荷扰动'); grid on; xlim([1050 1700]);
subplot(2,1,2); plot(cascade.t, cascade.Q, 'Color', cB, 'LineWidth', 1.5); hold on; plot(cascade.t, cascade.C, '--', 'Color', cR, 'LineWidth', 1.5); xline(P.tDist,'-.','Color',cO); ylabel('归一化数值'); xlabel('时间 / s'); legend('进水流量','污染物浓度','Location','southeast'); grid on; xlim([1050 1700]);
saveas(f, fullfile(outdir, 'method3_fig6_load_disturbance.png'));

% 图7：指标柱状图
f = figure('Color','w','Position',[100 100 1100 520]);
labels = categorical({'最大偏差','恢复时间','IAE','控制能量'});
labels = reordercats(labels, {'最大偏差','恢复时间','IAE','控制能量'});
bar(labels, [mc.maxErr mf.maxErr; mc.recovery mf.recovery; mc.IAE mf.IAE; mc.energy mf.energy]);
title('抗扰动性能指标对比'); grid on;
legend('串级 PID','普通前馈 + 串级 PID','Location','northwest');
saveas(f, fullfile(outdir, 'method3_fig7_performance_bar.png'));

fprintf('\n方法3图片和数据已输出到：%s\n', here);

%% ========================== 局部函数 ==========================
function r = simulate_method3(P, useFF)
    t = (0:P.dt:P.tEnd-P.dt)';
    n = numel(t);
    DO = zeros(n,1); airFlow = zeros(n,1); airSP = zeros(n,1);
    u = zeros(n,1); loadDist = zeros(n,1); ffAir = zeros(n,1);
    Q = zeros(n,1); C = zeros(n,1);

    baseAir = P.SP / P.Kair;
    y = P.SP; x = baseAir;
    qMeas = P.Q0; cMeas = P.C0;
    delaySteps = round(P.delay / P.dt) + 1;
    delayBuf = baseAir * ones(delaySteps, 1); di = 1;

    outerNoFF = init_pid(0.52, 0.0034, 20.0, P.uMin, P.uMax, baseAir / 0.0034);
    outerFF = init_pid(0.26, 0.0015, 8.0, -0.25, 0.25, 0.0);
    inner = init_pid(4.0, 0.60, 0.0, P.uMin, P.uMax, baseAir / 0.60);

    for i = 1:n
        if t(i) >= P.tDist
            q = P.Q0 + P.Qstep; c = P.C0 + P.Cstep;
        else
            q = P.Q0; c = P.C0;
        end
        Q(i) = q; C(i) = c;
        qMeas = qMeas + (q - qMeas) / P.tauFFMeasure * P.dt;
        cMeas = cMeas + (c - cMeas) / P.tauFFMeasure * P.dt;

        dLoad = -(P.kQTrue * (q - P.Q0) + P.kCTrue * (c - P.C0));
        loadDist(i) = dLoad;

        eDO = P.SP - y;
        if useFF
            estimatedLoad = P.kQModel * (qMeas - P.Q0) + P.kCModel * (cMeas - P.C0);
            ff = baseAir + estimatedLoad / P.Kair;
            [trim, outerFF] = pid_step(outerFF, eDO, P.dt);
            targetAir = clip(ff + trim, P.uMin, P.uMax);
        else
            ff = baseAir;
            [targetAir, outerNoFF] = pid_step(outerNoFF, eDO, P.dt);
        end
        ffAir(i) = ff; airSP(i) = targetAir;

        eFlow = targetAir - x;
        [uu, inner] = pid_step(inner, eFlow, P.dt);
        u(i) = uu;

        x = x + (P.Kblower * uu - x) / P.Tflow * P.dt;
        airFlow(i) = x;

        delayBuf(di) = x;
        di = mod(di, delaySteps) + 1;
        delayedAir = delayBuf(di);
        y = y + (P.Kair * delayedAir - y + dLoad) / P.Tdo * P.dt;
        DO(i) = y;
    end

    r = struct('t',t,'DO',DO,'airFlow',airFlow,'airSP',airSP,'u',u, ...
        'loadDist',loadDist,'ffAir',ffAir,'Q',Q,'C',C);
end

function p = init_pid(kp, ki, kd, lo, hi, initialIntegral)
    p = struct('kp',kp,'ki',ki,'kd',kd,'lo',lo,'hi',hi, ...
        'integral',initialIntegral,'prevError',NaN);
end

function [out, p] = pid_step(p, err, dt)
    if isnan(p.prevError)
        der = 0.0;
    else
        der = (err - p.prevError) / dt;
    end
    p.prevError = err;

    trialIntegral = p.integral + err * dt;
    raw = p.kp * err + p.ki * trialIntegral + p.kd * der;
    out = clip(raw, p.lo, p.hi);
    if raw == out || (raw > p.hi && err < 0) || (raw < p.lo && err > 0)
        p.integral = trialIntegral;
    end
end

function v = clip(x, lo, hi)
    v = min(max(x, lo), hi);
end

function m = disturbance_metrics(t, y, u, P)
    idx = t >= P.tDist;
    tt = t(idx) - P.tDist;
    yy = y(idx);
    uu = u(idx);
    dev = abs(yy - P.SP);
    band = 0.02 * P.SP;
    outside = find(dev > band);
    if isempty(outside)
        recovery = 0.0;
    else
        recovery = tt(outside(end));
    end
    m.minDO = min(yy);
    m.maxErr = max(dev);
    m.recovery = recovery;
    m.IAE = trapz(tt, dev);
    m.airIntegral = trapz(tt, uu);
    m.energy = trapz(tt, uu .* uu);
end

%% 污水处理曝气过程 —— 溶解氧(DO)控制仿真  (MATLAB 2024b)
%  对应《过控提纲》方法1：单回路PID   方法2：串级PID(外环DO/内环供气流量)
%
%  被控对象：
%    主对象  供气流量 -> 溶解氧   FOPDT:  G1(s)=K1*exp(-tau*s)/(T1*s+1)
%    副对象  鼓风机指令 -> 供气流量 一阶:  G2(s)=K2/(T2*s+1)
%  两类扰动：
%    一次扰动 d_primary  ：进水耗氧负荷（作用在DO端/主对象）
%    二次扰动 d_secondary：供气母管压力波动（作用在供气流量端/副对象）—— 串级核心优势
%
%  自包含脚本：直接在 MATLAB 2024b 中运行(F5)即可，无需任何工具箱。
%  与 Python 版 aeration_do_sim.py 完全等价（同模型、同参数、同算法）。
% =========================================================================

clear; clc; close all;

%% 1. 被控对象参数（与 Python 版一致）
P.K1  = 4.0;   P.T1 = 180.0;  P.tau = 30.0;   % 主对象：供气流量->DO
P.K2  = 1.0;   P.T2 = 15.0;                    % 副对象：鼓风机->供气流量
P.SP  = 2.0;                                   % DO 设定值 mg/L
P.uMin = 0.0;  P.uMax = 1.0;                    % 执行器限幅
P.dt  = 0.5;   P.tEnd = 2400.0;                 % 仿真步长 / 总时长
P.distTime  = 1200.0;                           % 扰动施加时刻
P.dPrimary  = -1.0;                             % 一次扰动幅值（DO端）
P.dSecondary= -0.18;                            % 二次扰动幅值（供气端）

% 单回路 PID 参数
S.Kp = 0.70; S.Ki = 0.0040; S.Kd = 15.0;
% 串级：外环(主,PI on DO) / 内环(副,PID on flow)
C.Kp1 = 0.52; C.Ki1 = 0.0034; C.Kd1 = 20.0;
C.Kp2 = 4.0;  C.Ki2 = 0.60;   C.Kd2 = 0.0;

%% 2. 运行仿真
% 2.1 设定值阶跃（无扰动）
[t , doS , uS , xS ] = sim_single(P,S,[],0,'none');
[~ , doC , uC , xC ] = sim_cascade(P,C,[],0,'none');
% 2.2 二次扰动（供气侧）
[t2, doS2, uS2, xS2] = sim_single(P,S,P.distTime,P.dSecondary,'secondary');
[~ , doC2, uC2, xC2] = sim_cascade(P,C,P.distTime,P.dSecondary,'secondary');
% 2.3 一次扰动（耗氧负荷，DO侧）
[t1, doS1] = sim_single(P,S,P.distTime,P.dPrimary,'primary');
[~ , doC1] = sim_cascade(P,C,P.distTime,P.dPrimary,'primary');

%% 3. 性能指标
mS = step_metrics(t,doS,P.SP);   mC = step_metrics(t,doC,P.SP);
dsS= dist_metrics(t2,doS2,P.SP,P.distTime);  dsC= dist_metrics(t2,doC2,P.SP,P.distTime);
dpS= dist_metrics(t1,doS1,P.SP,P.distTime);  dpC= dist_metrics(t1,doC1,P.SP,P.distTime);

fprintf('================ 阶跃响应性能指标 ================\n');
fprintf('%-9s 超调%%   上升s   调节s    IAE     ITAE\n','');
fprintf('单回路PID  %5.2f  %6.1f  %6.1f  %7.1f  %9.0f\n',mS.os,mS.tr,mS.ts,mS.iae,mS.itae);
fprintf('串级PID    %5.2f  %6.1f  %6.1f  %7.1f  %9.0f\n',mC.os,mC.tr,mC.ts,mC.iae,mC.itae);
fprintf('\n========= 二次扰动(供气母管压力波动)抑制 =========\n');
fprintf('单回路PID  最大偏差=%.4f mg/L  恢复时间=%6.1fs\n',dsS.dev,dsS.rec);
fprintf('串级PID    最大偏差=%.4f mg/L  恢复时间=%6.1fs\n',dsC.dev,dsC.rec);
fprintf('\n=========== 一次扰动(进水耗氧负荷)抑制 ===========\n');
fprintf('单回路PID  最大偏差=%.4f mg/L  恢复时间=%6.1fs\n',dpS.dev,dpS.rec);
fprintf('串级PID    最大偏差=%.4f mg/L  恢复时间=%6.1fs\n',dpC.dev,dpC.rec);

%% 4. 绘图
outdir = fullfile(fileparts(mfilename('fullpath')),'figures');
if ~exist(outdir,'dir'); mkdir(outdir); end
cS=[0.12 0.47 0.71]; cC=[0.84 0.15 0.16]; cR=[0.33 0.33 0.33]; cD=[1 0.5 0.05];

% 图1 阶跃响应
f=figure('Color','w','Position',[100 100 820 460]);
plot(t,doS,'-','Color',cS,'LineWidth',1.8); hold on;
plot(t,doC,'--','Color',cC,'LineWidth',1.8);
yline(P.SP,':','Color',cR,'LineWidth',1.2);
xlabel('时间 t / s'); ylabel('溶解氧 DO / (mg/L)');
title('溶解氧设定值阶跃响应对比'); grid on; xlim([0 1200]); ylim([0 2.6]);
legend('单回路PID','串级PID','设定值','Location','southeast');
saveas(f,fullfile(outdir,'fig1_step_response.png'));

% 图2 二次扰动
f=figure('Color','w','Position',[100 100 820 460]);
plot(t2,doS2,'-','Color',cS,'LineWidth',1.8); hold on;
plot(t2,doC2,'--','Color',cC,'LineWidth',1.8);
yline(P.SP,':','Color',cR,'LineWidth',1.2);
xline(P.distTime,'-.','Color',cD,'LineWidth',1.2);
xlabel('时间 t / s'); ylabel('溶解氧 DO / (mg/L)');
title('二次扰动（供气母管压力波动）抑制对比'); grid on; xlim([1100 2000]); ylim([1.4 2.15]);
legend('单回路PID','串级PID','设定值','扰动加入','Location','southeast');
saveas(f,fullfile(outdir,'fig2_disturb_secondary.png'));

% 图3 一次扰动
f=figure('Color','w','Position',[100 100 820 460]);
plot(t1,doS1,'-','Color',cS,'LineWidth',1.8); hold on;
plot(t1,doC1,'--','Color',cC,'LineWidth',1.8);
yline(P.SP,':','Color',cR,'LineWidth',1.2);
xline(P.distTime,'-.','Color',cD,'LineWidth',1.2);
xlabel('时间 t / s'); ylabel('溶解氧 DO / (mg/L)');
title('一次扰动（进水耗氧负荷突增）抑制对比'); grid on; xlim([1100 2100]); ylim([1.4 2.1]);
legend('单回路PID','串级PID','设定值','扰动加入','Location','southeast');
saveas(f,fullfile(outdir,'fig3_disturb_primary.png'));

% 图4 控制量
f=figure('Color','w','Position',[100 100 820 460]);
plot(t,uS,'-','Color',cS,'LineWidth',1.6); hold on;
plot(t,uC,'--','Color',cC,'LineWidth',1.6);
xlabel('时间 t / s'); ylabel('鼓风机变频指令 u (0~1)');
title('控制量（鼓风机/阀门指令）对比'); grid on; xlim([0 800]);
legend('单回路PID','串级PID','Location','northeast');
saveas(f,fullfile(outdir,'fig4_control_signal.png'));

% 图5 串级内部信号（二次扰动场景下记录目标供气流量）
[~, doC2b, ~, xC2b, airSp] = sim_cascade(P,C,P.distTime,P.dSecondary,'secondary');
f=figure('Color','w','Position',[100 100 820 640]);
subplot(2,1,1);
plot(t2,doC2b,'-','Color',cC,'LineWidth',1.8); hold on; yline(P.SP,':','Color',cR,'LineWidth',1.2);
xline(P.distTime,'-.','Color',cD,'LineWidth',1.0);
ylabel('DO / (mg/L)'); title('串级控制主/副回路信号（含二次扰动）'); grid on; ylim([1.5 2.15]);
legend('主回路输出 DO','DO设定值','Location','southeast');
subplot(2,1,2);
plot(t2,airSp,'--','Color',[0.17 0.63 0.17],'LineWidth',1.6); hold on;
plot(t2,xC2b,'-','Color',[0.58 0.40 0.74],'LineWidth',1.6);
xline(P.distTime,'-.','Color',cD,'LineWidth',1.0);
xlabel('时间 t / s'); ylabel('供气流量 (0~1)'); grid on; xlim([1100 1700]);
legend('副回路设定值(目标供气流量)','副回路输出(实际供气流量)','供气扰动加入','Location','southeast');
saveas(f,fullfile(outdir,'fig5_cascade_signals.png'));

% 图6 性能指标柱状对比
f=figure('Color','w','Position',[100 100 1200 360]);
titles={'超调量 / %','阶跃调节时间 / s','二次扰动最大偏差 / (mg/L)','二次扰动恢复时间 / s'};
valsS=[mS.os, mS.ts, dsS.dev, dsS.rec];
valsC=[mC.os, mC.ts, dsC.dev, dsC.rec];
for k=1:4
    subplot(1,4,k);
    b=bar([valsS(k) valsC(k)]); b.FaceColor='flat'; b.CData(1,:)=cS; b.CData(2,:)=cC;
    set(gca,'XTickLabel',{'单回路','串级'}); title(titles{k}); grid on;
    text(1,valsS(k),sprintf('%.2f',valsS(k)),'HorizontalAlignment','center','VerticalAlignment','bottom');
    text(2,valsC(k),sprintf('%.2f',valsC(k)),'HorizontalAlignment','center','VerticalAlignment','bottom');
end
sgtitle('单回路PID 与 串级PID 性能指标对比');
saveas(f,fullfile(outdir,'fig6_performance_bar.png'));

fprintf('\n图片已保存到: %s\n', outdir);

%% ===================== 局部函数 =====================
function [t,do,u,x,airSpHist] = sim_cascade(P,C,distTime,distMag,distLoc)
% 串级PID仿真：外环DO->目标供气流量；内环供气流量->鼓风机指令
    t = (0:P.dt:P.tEnd-P.dt)';  n=numel(t);
    do=zeros(n,1); u=zeros(n,1); x=zeros(n,1); airSpHist=zeros(n,1);
    y=0; xa=0;
    ds=floor(P.tau/P.dt)+1; buf=zeros(ds,1); di=1;
    int1=0; pe1=NaN; int2=0; pe2=NaN;
    for i=1:n
        active = ~isempty(distTime) && t(i)>=distTime;
        dSec = (active && strcmp(distLoc,'secondary'))*distMag;
        dPri = (active && strcmp(distLoc,'primary'))  *distMag;
        % 外环
        e1=P.SP-y; int1=clip(int1+e1*P.dt,-400,400);
        d1=ternary(isnan(pe1),0,(e1-pe1)/P.dt); pe1=e1;
        airSp=clip(C.Kp1*e1+C.Ki1*int1+C.Kd1*d1, P.uMin,P.uMax);
        airSpHist(i)=airSp;
        % 内环
        e2=airSp-xa; int2=clip(int2+e2*P.dt,-400,400);
        d2=ternary(isnan(pe2),0,(e2-pe2)/P.dt); pe2=e2;
        uu=clip(C.Kp2*e2+C.Ki2*int2+C.Kd2*d2, P.uMin,P.uMax);
        u(i)=uu;
        % 副对象（含二次扰动）
        xa=xa+(P.K2*uu-xa+dSec)/P.T2*P.dt; x(i)=xa;
        % 纯滞后
        buf(di)=xa; di=mod(di,ds)+1; xd=buf(di);
        % 主对象（含一次扰动）
        y=y+(P.K1*xd-y+dPri)/P.T1*P.dt; do(i)=y;
    end
end

function [t,do,u,x] = sim_single(P,S,distTime,distMag,distLoc)
% 单回路PID仿真：DO偏差->PID->鼓风机指令
    t=(0:P.dt:P.tEnd-P.dt)'; n=numel(t);
    do=zeros(n,1); u=zeros(n,1); x=zeros(n,1);
    y=0; xa=0;
    ds=floor(P.tau/P.dt)+1; buf=zeros(ds,1); di=1;
    intg=0; pe=NaN;
    for i=1:n
        active = ~isempty(distTime) && t(i)>=distTime;
        dSec = (active && strcmp(distLoc,'secondary'))*distMag;
        dPri = (active && strcmp(distLoc,'primary'))  *distMag;
        e=P.SP-y; intg=clip(intg+e*P.dt,-400,400);
        de=ternary(isnan(pe),0,(e-pe)/P.dt); pe=e;
        uu=clip(S.Kp*e+S.Ki*intg+S.Kd*de, P.uMin,P.uMax); u(i)=uu;
        xa=xa+(P.K2*uu-xa+dSec)/P.T2*P.dt; x(i)=xa;
        buf(di)=xa; di=mod(di,ds)+1; xd=buf(di);
        y=y+(P.K1*xd-y+dPri)/P.T1*P.dt; do(i)=y;
    end
end

function m = step_metrics(t,y,sp)
    dt=t(2)-t(1);
    yss=mean(y(end-round(60/dt):end));
    m.sse=abs(sp-yss);
    m.os=max(0,(max(y)-sp)/sp*100);
    idx=find(y>=0.9*sp,1);
    if isempty(idx); m.tr=t(end); else; m.tr=t(idx); end
    band=0.02*sp; out=find(abs(y-sp)>band);
    if isempty(out); m.ts=0; else; m.ts=t(out(end)); end
    m.iae=trapz(t,abs(y-sp));
    m.itae=trapz(t,t.*abs(y-sp));
end

function d = dist_metrics(t,y,sp,distTime)
    dt=t(2)-t(1); i0=round(distTime/dt);
    seg=y(i0:end);
    d.dev=max(abs(seg-sp));
    band=0.02*sp; out=find(abs(seg-sp)>band);
    if isempty(out); d.rec=0; else; d.rec=(out(end)-1)*dt; end
end

function v=clip(x,lo,hi); v=min(max(x,lo),hi); end
function v=ternary(c,a,b); if c; v=a; else; v=b; end; end

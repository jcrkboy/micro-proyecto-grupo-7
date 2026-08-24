%% =========================================================
%  EEG + HIPNOGRAMA  —  ST7011J0
%  Solo canales EEG Fpz-Cz y EEG Pz-Oz
%% =========================================================

clear; clc; close all;

BASE = '/Users/juanvalera/Documents/Magister en Inteligencia Artificial/Cuarto Semestre/Cuarto Bimestre/Proyecto - Desarrollo de Soluciones/Proyecto de Grado/Tema 2/micro-proyecto-grupo-7/data/sleep-telemetry/'
PSG_FILE = [BASE, 'ST7011J0-PSG.edf'];
HYP_FILE = [BASE, 'ST7011JP-Hypnogram.edf'];
DECIMATE = 5;          % 1 = resolución completa (más lento)

%% ── 1. SEÑALES EEG ───────────────────────────────────────
psgInfo  = edfinfo(PSG_FILE);
psgTable = edfread(PSG_FILE);
vn = psgTable.Properties.VariableNames;

eeg1 = concatCol(psgTable.(vn{1}));    % EEG Fpz-Cz
eeg2 = concatCol(psgTable.(vn{2}));    % EEG Pz-Oz

fs = double(psgInfo.NumSamples(1)) / seconds(psgInfo.DataRecordDuration);
N  = numel(eeg1);
t  = (0:N-1).' / fs;

fprintf('EEG: %d muestras | fs = %g Hz | %.2f h\n', N, fs, t(end)/3600);

%% ── 2. ANOTACIONES ───────────────────────────────────────
[~, annTT] = edfread(HYP_FILE);
vnA = annTT.Properties.VariableNames;

if any(strcmpi(vnA,'Onset'))
    onsets = seconds(annTT.Onset);
else
    onsets = seconds(annTT.Properties.RowTimes);
end
if any(strcmpi(vnA,'Duration'))
    durs = seconds(annTT.Duration);
else
    durs = [diff(onsets); 30];
end
iLbl   = find(strcmpi(vnA,'Annotations') | strcmpi(vnA,'Value'), 1);
lbls   = strtrim(string(annTT.(vnA{iLbl})));

keep   = lbls ~= "" & ~contains(lbls,"?");
onsets = onsets(keep);  durs = durs(keep);  lbls = lbls(keep);
stg    = arrayfun(@stage2num, lbls);

fprintf('Hipnograma: %d anotaciones\n', numel(onsets));

COLORS = [0.05 0.15 0.50; 0.15 0.35 0.65; 0.30 0.60 0.85; ...
          0.55 0.80 0.70; 0.85 0.85 0.85; 0.95 0.45 0.40];
YTL = {'N4','N3','N2','N1','W','REM'};

%% ── 3. DIEZMADO PARA GRAFICAR ───────────────────────────
idx  = 1:DECIMATE:N;
th   = t(idx)/3600;
p1   = eeg1(idx);
p2   = eeg2(idx);
TEND = th(end);

%% ── 4. FIGURA (3 paneles) ───────────────────────────────
fig = figure('Name','EEG + Hipnograma','NumberTitle','off','Color','w', ...
             'Units','normalized','Position',[0.03 0.10 0.94 0.78]);

H = [0.22 0.30 0.30];
B = [0.70 0.38 0.06];
L = 0.07;  W = 0.85;
ax = gobjects(3,1);

% Hipnograma
ax(1) = axes('Position',[L B(1) W H(1)]); hold on;
for k = 1:numel(onsets)
    x1 = onsets(k)/3600;  x2 = (onsets(k)+durs(k))/3600;
    fill([x1 x2 x2 x1],[-0.5 -0.5 5.5 5.5], COLORS(stg(k)+1,:), ...
         'EdgeColor','none','FaceAlpha',0.5);
end
stairs([onsets; onsets(end)+durs(end)]/3600, [stg; stg(end)], ...
       'k-','LineWidth',1.6);
set(ax(1),'YTick',0:5,'YTickLabel',YTL,'YLim',[-0.5 5.5]);
ylabel('Etapa','FontWeight','bold');
title(sprintf('EEG + Hipnograma — ST7011J0  (%.1f h)', TEND), ...
      'FontSize',12,'FontWeight','bold');

hp = gobjects(6,1);
for s = 0:5
    hp(s+1) = patch(nan,nan,COLORS(s+1,:),'FaceAlpha',0.6,'EdgeColor','none');
end
legend(hp, YTL,'Location','eastoutside','FontSize',8,'Box','off');

% EEG Fpz-Cz
ax(2) = axes('Position',[L B(2) W H(2)]);
plot(th, p1, 'Color',[0.12 0.35 0.70],'LineWidth',0.25);
shadeBg(ax(2), onsets, durs, stg, COLORS, TEND);
ylabel('\muV');  title('EEG  Fpz-Cz','FontSize',10,'FontWeight','bold');

% EEG Pz-Oz
ax(3) = axes('Position',[L B(3) W H(3)]);
plot(th, p2, 'Color',[0.08 0.52 0.42],'LineWidth',0.25);
shadeBg(ax(3), onsets, durs, stg, COLORS, TEND);
ylabel('\muV');  title('EEG  Pz-Oz','FontSize',10,'FontWeight','bold');
xlabel('Tiempo (horas)','FontSize',11);

for k = 1:3
    set(ax(k),'Box','off','XGrid','on','GridAlpha',0.18, ...
        'TickDir','out','FontSize',8,'XLim',[0 TEND]);
    if k < 3, set(ax(k),'XTickLabel',{}); end
end
linkaxes(ax,'x');

exportgraphics(fig,'EEG_Hipnograma.png','Resolution',200);
fprintf('Guardado: EEG_Hipnograma.png\n');


%% ── FUNCIONES LOCALES ────────────────────────────────────
function y = concatCol(col)
    if iscell(col), y = vertcat(col{:}); else, y = col(:); end
    y = double(y);
end

function v = stage2num(lbl)
    s = char(strtrim(lbl));
    switch true
        case contains(s,'stage 4','IgnoreCase',true), v = 0;
        case contains(s,'stage 3','IgnoreCase',true), v = 1;
        case contains(s,'stage 2','IgnoreCase',true), v = 2;
        case contains(s,'stage 1','IgnoreCase',true), v = 3;
        case contains(s,'stage W','IgnoreCase',true), v = 4;
        case contains(s,'stage R','IgnoreCase',true), v = 5;
        otherwise,                                    v = 4;
    end
end

function shadeBg(axh, onsets, durs, stg, COLORS, TEND)
    hold(axh,'on');
    yl = ylim(axh);
    for k = 1:numel(onsets)
        x1 = onsets(k)/3600;  x2 = (onsets(k)+durs(k))/3600;
        fill(axh,[x1 x2 x2 x1],[yl(1) yl(1) yl(2) yl(2)], ...
             COLORS(stg(k)+1,:),'EdgeColor','none','FaceAlpha',0.10);
    end
    xlim(axh,[0 TEND]);  ylim(axh, yl);
    uistack(findobj(axh,'Type','patch'),'bottom');
end
import { EChartsCoreOption } from 'echarts/core';

import { EpochPrediction, SLEEP_STAGES } from '../models/sleep-api.models';

export const STAGE_COLORS: Record<string, string> = {
  W: '#20a37a',
  REM: '#6d5ce7',
  N1: '#ef9f27',
  N2: '#3687d8',
  N3: '#183d66',
};

export interface StageRun {
  startIndex: number;
  endIndex: number;
  stageIndex: number;
  previousStageIndex: number;
}

export function formatClock(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return [hours, minutes, seconds].map((part) => String(part).padStart(2, '0')).join(':');
}

export function groupConsecutiveStages(epochs: EpochPrediction[]): StageRun[] {
  return epochs.reduce<StageRun[]>((runs, epoch, index) => {
    const stageIndex = SLEEP_STAGES.indexOf(epoch.stage);
    const currentRun = runs.at(-1);

    if (currentRun?.stageIndex === stageIndex) {
      currentRun.endIndex = index;
      return runs;
    }

    runs.push({
      startIndex: index,
      endIndex: index,
      stageIndex,
      previousStageIndex: currentRun?.stageIndex ?? -1,
    });
    return runs;
  }, []);
}

export function createHypnogramOption(epochs: EpochPrediction[]): EChartsCoreOption {
  const labels = epochs.map((epoch) => formatClock(epoch.onset_seconds));
  const runs = groupConsecutiveStages(epochs);

  return {
    animationDuration: 350,
    grid: { left: 52, right: 24, top: 28, bottom: 76 },
    xAxis: {
      type: 'category',
      boundaryGap: true,
      data: labels,
      name: 'Tiempo desde el inicio',
      nameLocation: 'middle',
      nameGap: 34,
      axisLabel: { color: '#64748b', hideOverlap: true },
      axisLine: { lineStyle: { color: '#d7e0e5' } },
    },
    yAxis: {
      type: 'category',
      data: [...SLEEP_STAGES],
      inverse: true,
      axisLabel: { color: '#334155', fontWeight: 600 },
      axisTick: { show: false },
      axisLine: { show: false },
      splitLine: { show: true, lineStyle: { color: '#edf1f3' } },
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100, minValueSpan: 10, filterMode: 'weakFilter' },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 22,
        bottom: 8,
        borderColor: '#d7e0e5',
        fillerColor: 'rgba(32,163,122,.16)',
        filterMode: 'weakFilter',
      },
    ],
    series: [
      {
        name: 'Etapas del sueño',
        type: 'custom',
        silent: true,
        encode: { x: [0, 1], y: 2 },
        data: runs.map((run) => [
          run.startIndex,
          run.endIndex,
          run.stageIndex,
          run.previousStageIndex,
        ]),
        renderItem: (_params: unknown, api: any) => {
          const startIndex = Number(api.value(0));
          const endIndex = Number(api.value(1));
          const stageIndex = Number(api.value(2));
          const previousStageIndex = Number(api.value(3));
          const startPoint = api.coord([startIndex, stageIndex]) as [number, number];
          const endPoint = api.coord([endIndex, stageIndex]) as [number, number];
          const cellSize = api.size([1, 1]) as [number, number];
          const cellWidth = Math.abs(cellSize[0]);
          const rowHeight = Math.abs(cellSize[1]);
          const barHeight = Math.max(8, rowHeight * 0.58);
          const left = startPoint[0] - cellWidth / 2;
          const children: any[] = [];

          if (previousStageIndex >= 0 && previousStageIndex !== stageIndex) {
            const previousPoint = api.coord([startIndex, previousStageIndex]) as [number, number];
            const top = Math.min(previousPoint[1], startPoint[1]);
            const bottom = Math.max(previousPoint[1], startPoint[1]);

            for (
              let crossedStage = Math.min(previousStageIndex, stageIndex);
              crossedStage <= Math.max(previousStageIndex, stageIndex);
              crossedStage += 1
            ) {
              const stagePoint = api.coord([startIndex, crossedStage]) as [number, number];
              const regionTop = stagePoint[1] - rowHeight / 2;
              const regionBottom = stagePoint[1] + rowHeight / 2;
              const segmentTop = Math.max(top, regionTop);
              const segmentBottom = Math.min(bottom, regionBottom);

              if (segmentBottom > segmentTop) {
                children.push({
                  type: 'line',
                  shape: {
                    x1: left,
                    y1: segmentTop,
                    x2: left,
                    y2: segmentBottom,
                  },
                  style: {
                    stroke: STAGE_COLORS[SLEEP_STAGES[crossedStage]],
                    lineWidth: 2,
                  },
                });
              }
            }
          }

          children.push({
            type: 'rect',
            shape: {
              x: left,
              y: startPoint[1] - barHeight / 2,
              width: endPoint[0] - startPoint[0] + cellWidth,
              height: barHeight,
              r: Math.min(6, barHeight / 2),
            },
            style: { fill: STAGE_COLORS[SLEEP_STAGES[stageIndex]] },
          });

          return { type: 'group', children };
        },
      },
    ],
  };
}

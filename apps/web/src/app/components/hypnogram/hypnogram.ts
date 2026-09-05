import { Component, computed, input, signal } from '@angular/core';
import { CustomChart } from 'echarts/charts';
import { DataZoomComponent, GridComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import type { EChartsType } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { NgxEchartsDirective, provideEchartsCore } from 'ngx-echarts';

import { EpochPrediction, SLEEP_STAGES } from '../../core/models/sleep-api.models';
import { STAGE_COLORS, createHypnogramOption, formatClock } from '../../core/utils/hypnogram';

echarts.use([CustomChart, DataZoomComponent, GridComponent, CanvasRenderer]);

@Component({
  selector: 'app-hypnogram',
  imports: [NgxEchartsDirective],
  providers: [provideEchartsCore({ echarts })],
  templateUrl: './hypnogram.html',
  styleUrl: './hypnogram.css',
})
export class HypnogramComponent {
  readonly epochs = input.required<EpochPrediction[]>();
  protected readonly stageLegend = SLEEP_STAGES.map((stage) => ({
    stage,
    color: STAGE_COLORS[stage],
  }));
  protected readonly chartOption = computed(() => createHypnogramOption(this.epochs()));
  protected readonly hoveredEpoch = signal<EpochPrediction | null>(null);
  protected readonly pointerLeft = signal(0);
  protected readonly tooltipLeft = signal(0);
  protected readonly formattedOnset = computed(() =>
    this.hoveredEpoch() ? formatClock(this.hoveredEpoch()!.onset_seconds) : '',
  );
  protected readonly sortedProbabilities = computed(() =>
    Object.entries(this.hoveredEpoch()?.probabilities ?? {}).sort(
      ([, left], [, right]) => right - left,
    ),
  );

  private chart?: EChartsType;

  protected onChartInit(chart: EChartsType): void {
    this.chart = chart;
  }

  protected onPointerMove(event: MouseEvent): void {
    const container = event.currentTarget as HTMLElement;
    const bounds = container.getBoundingClientRect();
    const offsetX = event.clientX - bounds.left;
    const index = this.resolveEpochIndex(offsetX, bounds.width);
    if (index === null) {
      this.clearPointer();
      return;
    }

    this.pointerLeft.set(offsetX);
    this.tooltipLeft.set(
      offsetX > bounds.width * 0.72
        ? Math.max(8, offsetX - 266)
        : Math.min(bounds.width - 258, offsetX + 12),
    );
    this.hoveredEpoch.set(this.epochs()[index]);
  }

  protected clearPointer(): void {
    this.hoveredEpoch.set(null);
  }

  private resolveEpochIndex(offsetX: number, chartWidth: number): number | null {
    const epochCount = this.epochs().length;
    const gridLeft = 52;
    const gridRight = 24;
    const gridWidth = chartWidth - gridLeft - gridRight;
    if (
      epochCount === 0 ||
      gridWidth <= 0 ||
      offsetX < gridLeft ||
      offsetX > gridLeft + gridWidth
    ) {
      return null;
    }

    const option = this.chart?.getOption() as unknown as {
      dataZoom?: Array<{
        start?: number;
        end?: number;
        startValue?: number;
        endValue?: number;
      }>;
    };
    const zoom = option?.dataZoom?.[0];
    const firstVisible = Number(
      zoom?.startValue ?? Math.floor(((zoom?.start ?? 0) / 100) * (epochCount - 1)),
    );
    const lastVisible = Number(
      zoom?.endValue ?? Math.ceil(((zoom?.end ?? 100) / 100) * (epochCount - 1)),
    );
    const ratio = (offsetX - gridLeft) / gridWidth;
    return Math.max(
      0,
      Math.min(epochCount - 1, Math.round(firstVisible + ratio * (lastVisible - firstVisible))),
    );
  }
}

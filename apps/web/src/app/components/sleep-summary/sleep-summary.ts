import { Component, computed, input } from '@angular/core';

import { SLEEP_STAGES, SleepSummary } from '../../core/models/sleep-api.models';
import { STAGE_COLORS, formatClock } from '../../core/utils/hypnogram';

@Component({
  selector: 'app-sleep-summary',
  templateUrl: './sleep-summary.html',
  styleUrl: './sleep-summary.css',
})
export class SleepSummaryComponent {
  readonly summary = input.required<SleepSummary>();
  protected readonly duration = computed(() => formatClock(this.summary().total_duration_seconds));
  protected readonly stages = computed(() =>
    SLEEP_STAGES.map((stage) => ({
      stage,
      percentage: this.summary().percentage_by_stage[stage] ?? 0,
      minutes: (this.summary().duration_by_stage_seconds[stage] ?? 0) / 60,
      color: STAGE_COLORS[stage],
    })),
  );
}

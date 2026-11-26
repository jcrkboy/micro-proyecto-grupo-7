import { InferenceStage } from '../models/sleep-api.models';

export interface AnalysisDurations {
  upload: number;
  processing: number | null;
  inference: number | null;
  total: number;
}

/** Los hitos del servidor comparten un reloj monotónico, independiente del navegador. */
export class AnalysisTimer {
  private readonly started = performance.now();
  private serverOrigin?: number;
  private uploaded?: number;
  private processing?: number;
  private inference?: number;
  private processed?: number;

  uploadComplete(): void {
    this.uploaded = performance.now();
  }

  mark(stage: InferenceStage, serverMs?: number): void {
    const time = this.eventTime(performance.now(), serverMs);
    if (stage === 'processing') this.processing ??= time;
    if (stage === 'overlap' || stage === 'inferring') this.inference ??= time;
    if (stage === 'inferring') this.processed ??= time;
  }

  read(serverEndMs?: number): AnalysisDurations {
    const now = performance.now();
    const end = this.eventTime(now, serverEndMs);
    return {
      upload: (this.uploaded ?? now) - this.started,
      processing: this.processing === undefined ? null : Math.max(0, (this.processed ?? end) - this.processing),
      inference: this.inference === undefined ? null : Math.max(0, end - this.inference),
      total: now - this.started,
    };
  }

  private eventTime(now: number, serverMs?: number): number {
    if (serverMs === undefined) return now;
    this.serverOrigin ??= now - serverMs;
    return this.serverOrigin + serverMs;
  }
}

const secondsFormat = new Intl.NumberFormat('es', { maximumFractionDigits: 1 });

export function formatElapsed(ms: number | null): string {
  if (ms === null) return '—';
  if (ms > 0 && ms < 100) return '< 0,1 s';
  const seconds = Math.round(ms / 100) / 10;
  if (seconds < 60) return `${secondsFormat.format(seconds)} s`;
  return `${Math.floor(seconds / 60)} min ${secondsFormat.format(seconds % 60)} s`;
}

import { InferenceStage, ModelTimings } from '../models/sleep-api.models';

export interface AnalysisDurations {
  upload: number;
  processing: number | null;
  inference: number | null;
  overlap: number;
  total: number;
}

export class AnalysisTimer {
  private readonly started = performance.now();
  private uploaded?: number;
  private received = this.started;
  private stage?: InferenceStage;
  private timings?: ModelTimings;

  uploadComplete(): void {
    this.uploaded = performance.now();
  }

  mark(stage: InferenceStage, timings?: ModelTimings): void {
    this.stage = stage;
    this.timings = timings;
    this.received = performance.now();
  }

  read(): AnalysisDurations {
    const now = performance.now();
    // Entre avisos, avanza únicamente el contador que sigue activo en el modelo.
    const delta = now - this.received;
    const both = this.stage === 'overlap';
    const processing = this.timings?.processing_ms;
    const inference = this.timings?.inference_ms;
    return {
      upload: (this.uploaded ?? now) - this.started,
      processing: processing == null ? null : processing + (both || this.stage === 'processing' ? delta : 0),
      inference: inference == null ? null : inference + (both || this.stage === 'inferring' ? delta : 0),
      overlap: this.timings ? this.timings.overlap_ms + (both ? delta : 0) : 0,
      total: now - this.started,
    };
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

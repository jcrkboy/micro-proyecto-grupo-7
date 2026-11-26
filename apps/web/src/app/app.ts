import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subscription, finalize, switchMap } from 'rxjs';

import { AnalysisModalComponent } from './components/analysis-modal/analysis-modal';
import { HypnogramComponent } from './components/hypnogram/hypnogram';
import { SleepSummaryComponent } from './components/sleep-summary/sleep-summary';
import { AnalysisRequest, UploadFormComponent } from './components/upload-form/upload-form';
import { ModelInfo, PredictionResponse, WorkflowState, analysisInProgress } from './core/models/sleep-api.models';
import { SleepApiService } from './core/services/sleep-api.service';
import { AnalysisDurations, AnalysisTimer, formatElapsed } from './core/utils/analysis-timing';
import { predictionToCsv } from './core/utils/result-exporter';

@Component({
  selector: 'app-root',
  imports: [UploadFormComponent, AnalysisModalComponent, HypnogramComponent, SleepSummaryComponent],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App implements OnInit {
  private readonly api = inject(SleepApiService);
  private readonly destroyRef = inject(DestroyRef);
  private activeRequest?: Subscription;

  protected readonly state = signal<WorkflowState>('ready');
  protected readonly elapsed = signal<AnalysisDurations | null>(null);
  protected readonly resultDurations = signal<AnalysisDurations | null>(null);
  protected readonly formatElapsed = formatElapsed;
  protected readonly uploadPercent = signal<number | null>(null);
  protected readonly prediction = signal<PredictionResponse | null>(null);
  protected readonly model = signal<ModelInfo | null>(null);
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly analysisModalOpen = signal(false);

  ngOnInit(): void {
    this.api.getModelInfo().subscribe({
      next: (model) => this.model.set(model),
      error: () => this.model.set({ model_ready: false, classes: [], channels: [] }),
    });
  }

  protected analyze(request: AnalysisRequest): void {
    if (analysisInProgress(this.state())) return;
    const timer = new AnalysisTimer();
    const refresh = () => this.elapsed.set(timer.read());
    refresh();
    const ticker = window.setInterval(refresh, 250);
    this.errorMessage.set(null);
    this.uploadPercent.set(null);
    this.state.set('uploading');

    this.activeRequest = this.api
      .uploadEdf(request.patientName, request.file, (percent) => this.uploadPercent.set(percent))
      .pipe(
        switchMap((upload) => {
          timer.uploadComplete();
          refresh();
          this.state.set('queued');
          return this.api.streamInference(upload.upload_id, request.channels);
        }),
        takeUntilDestroyed(this.destroyRef),
        finalize(() => window.clearInterval(ticker)),
      )
      .subscribe({
        next: (event) => {
          if (event.type === 'progress') {
            timer.mark(event.stage, event.elapsed_ms);
            this.state.set(event.stage);
            refresh();
            return;
          }
          this.resultDurations.set(timer.read(event.elapsed_ms));
          this.prediction.set(event.prediction);
          this.state.set('result');
          this.analysisModalOpen.set(false);
        },
        error: (error: unknown) => {
          this.errorMessage.set(this.describeError(error));
          this.state.set('error');
        },
      });
  }

  protected cancelAnalysis(): void {
    if (!analysisInProgress(this.state())) return;
    this.activeRequest?.unsubscribe();
    this.elapsed.set(null);
    this.uploadPercent.set(null);
    this.state.set('ready');
  }

  protected openNewAnalysis(): void {
    this.errorMessage.set(null);
    this.state.set('ready');
    this.analysisModalOpen.set(true);
  }

  protected closeNewAnalysis(): void {
    if (analysisInProgress(this.state())) return;
    this.errorMessage.set(null);
    this.state.set(this.prediction() ? 'result' : 'ready');
    this.analysisModalOpen.set(false);
  }

  protected clearInitialError(): void {
    this.errorMessage.set(null);
    this.state.set('ready');
  }

  protected downloadJson(): void {
    const prediction = this.prediction();
    if (prediction) {
      this.download(
        JSON.stringify(prediction, null, 2),
        `sleep-edfx-${prediction.prediction_id}.json`,
        'application/json',
      );
    }
  }

  protected downloadCsv(): void {
    const prediction = this.prediction();
    if (prediction) {
      this.download(
        predictionToCsv(prediction),
        `sleep-edfx-${prediction.prediction_id}.csv`,
        'text/csv;charset=utf-8',
      );
    }
  }

  private download(content: string, filename: string, type: string): void {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  private describeError(error: unknown): string {
    if (!(error instanceof HttpErrorResponse)) {
      if (error instanceof Error && !(error instanceof SyntaxError)) return error.message;
      return 'No fue posible completar el análisis. Intenta nuevamente.';
    }
    const detail = error.error?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => item?.msg)
        .filter(Boolean)
        .join('. ');
    }
    if (error.status === 0) {
      return 'No hay conexión con la API. Verifica que el backend esté disponible.';
    }
    return `La API respondió con un error (${error.status}).`;
  }
}

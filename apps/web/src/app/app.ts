import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { switchMap } from 'rxjs';

import { HypnogramComponent } from './components/hypnogram/hypnogram';
import { SleepSummaryComponent } from './components/sleep-summary/sleep-summary';
import { AnalysisRequest, UploadFormComponent } from './components/upload-form/upload-form';
import { ModelInfo, PredictionResponse } from './core/models/sleep-api.models';
import { SleepApiService } from './core/services/sleep-api.service';
import { predictionToCsv } from './core/utils/result-exporter';

export type WorkflowState = 'ready' | 'uploading' | 'processing' | 'result' | 'error';

@Component({
  selector: 'app-root',
  imports: [UploadFormComponent, HypnogramComponent, SleepSummaryComponent],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App implements OnInit {
  private readonly api = inject(SleepApiService);

  protected readonly state = signal<WorkflowState>('ready');
  protected readonly prediction = signal<PredictionResponse | null>(null);
  protected readonly model = signal<ModelInfo | null>(null);
  protected readonly errorMessage = signal<string | null>(null);

  ngOnInit(): void {
    this.api.getModelInfo().subscribe({
      next: (model) => this.model.set(model),
      error: () => this.model.set({ model_ready: false, classes: [], channels: [] }),
    });
  }

  protected analyze(request: AnalysisRequest): void {
    this.prediction.set(null);
    this.errorMessage.set(null);
    this.state.set('uploading');

    this.api
      .uploadEdf(request.patientName, request.file)
      .pipe(
        switchMap((upload) => {
          this.state.set('processing');
          return this.api.runInference(upload.upload_id);
        }),
      )
      .subscribe({
        next: (prediction) => {
          this.prediction.set(prediction);
          this.state.set('result');
        },
        error: (error: unknown) => {
          this.errorMessage.set(this.describeError(error));
          this.state.set('error');
        },
      });
  }

  protected reset(): void {
    this.prediction.set(null);
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

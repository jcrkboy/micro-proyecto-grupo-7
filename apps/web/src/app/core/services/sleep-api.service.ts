import { HttpClient, HttpEventType } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, defer, filter, map, mergeMap, tap } from 'rxjs';

import { environment } from '../../../environments/environment';
import { InferenceStage, ModelInfo, ModelTimings, PredictionResponse, UploadResponse } from '../models/sleep-api.models';

type InferenceUpdate =
  | { type: 'progress'; stage: InferenceStage; timings?: ModelTimings }
  | { type: 'result'; prediction: PredictionResponse; timings?: ModelTimings };
type InferenceEvent = InferenceUpdate | { type: 'error'; detail: string };

@Injectable({ providedIn: 'root' })
export class SleepApiService {
  private readonly http = inject(HttpClient);
  private readonly apiRoot = environment.apiBaseUrl;

  getModelInfo(): Observable<ModelInfo> {
    return this.http.get<ModelInfo>(`${this.apiRoot}/model`);
  }

  uploadEdf(patientName: string, file: File, onProgress?: (percent: number) => void): Observable<UploadResponse> {
    const body = new FormData();
    body.append('patient_name', patientName);
    body.append('file', file, file.name);
    return this.http.post<UploadResponse>(`${this.apiRoot}/uploads`, body, {
      observe: 'events', reportProgress: true,
    }).pipe(
      tap((event) => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          onProgress?.(Math.floor(100 * event.loaded / event.total));
        }
      }),
      filter((event) => event.type === HttpEventType.Response),
      map((event) => event.body!),
    );
  }

  runInference(uploadId: string, channels: string[], onProgress?: (stage: InferenceStage) => void): Observable<PredictionResponse> {
    if (!onProgress) return this.http.post<PredictionResponse>(`${this.apiRoot}/inferencia`, { upload_id: uploadId, channels });
    return this.streamInference(uploadId, channels).pipe(
      tap((event) => { if (event.type === 'progress') onProgress(event.stage); }),
      filter((event) => event.type === 'result'),
      map((event) => event.prediction),
    );
  }

  streamInference(uploadId: string, channels: string[]): Observable<InferenceUpdate> {
    return defer(() => {
      let offset = 0;
      let receivedResult = false;
      return this.http.post(`${this.apiRoot}/inferencia/progreso`, { upload_id: uploadId, channels }, {
        observe: 'events', responseType: 'text', reportProgress: true,
      }).pipe(
        filter((event) => event.type === HttpEventType.DownloadProgress || event.type === HttpEventType.Response),
        mergeMap((event) => {
          // XHR entrega el texto acumulado y puede cortar una línea entre dos eventos.
          const final = event.type === HttpEventType.Response;
          const text = (final ? event.body : event.partialText) ?? '';
          const updates: InferenceUpdate[] = [];
          let end = text.indexOf('\n', offset);
          while (end !== -1) {
            const message: InferenceEvent = JSON.parse(text.slice(offset, end));
            offset = end + 1;
            if (message.type === 'error') throw new Error(message.detail);
            if (message.type === 'result') receivedResult = true;
            updates.push(message);
            end = text.indexOf('\n', offset);
          }
          if (final && !receivedResult) throw new Error('Se interrumpió la respuesta antes de recibir el hipnograma.');
          return updates;
        }),
      );
    });
  }
}

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ModelInfo, PredictionResponse, UploadResponse } from '../models/sleep-api.models';

@Injectable({ providedIn: 'root' })
export class SleepApiService {
  private readonly http = inject(HttpClient);
  private readonly apiRoot = environment.apiBaseUrl;

  getModelInfo(): Observable<ModelInfo> {
    return this.http.get<ModelInfo>(`${this.apiRoot}/model`);
  }

  uploadEdf(patientName: string, file: File): Observable<UploadResponse> {
    const body = new FormData();
    body.append('patient_name', patientName);
    body.append('file', file, file.name);
    return this.http.post<UploadResponse>(`${this.apiRoot}/uploads`, body);
  }

  runInference(uploadId: string): Observable<PredictionResponse> {
    return this.http.post<PredictionResponse>(`${this.apiRoot}/inferencia`, {
      upload_id: uploadId,
    });
  }
}

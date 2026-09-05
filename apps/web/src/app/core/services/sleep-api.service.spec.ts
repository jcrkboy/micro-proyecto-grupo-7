import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { SleepApiService } from './sleep-api.service';

describe('SleepApiService', () => {
  let service: SleepApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(SleepApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('envía la carga como multipart al endpoint versionado', () => {
    const file = new File(['0       test'], 'night.edf');
    service.uploadEdf('Paciente', file).subscribe();

    const request = http.expectOne('/api/v1/uploads');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toBeInstanceOf(FormData);
    expect(request.request.body.get('patient_name')).toBe('Paciente');
    const uploadedFile = request.request.body.get('file') as File;
    expect(uploadedFile.name).toBe(file.name);
    expect(uploadedFile.size).toBe(file.size);
    request.flush({
      upload_id: 'id',
      patient_name: 'Paciente',
      original_filename: 'night.edf',
      size_bytes: 12,
      created_at: '',
      status: 'uploaded',
    });
  });

  it('solicita inferencia usando el upload_id', () => {
    service.runInference('00000000-0000-0000-0000-000000000000').subscribe();

    const request = http.expectOne('/api/v1/inferencia');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ upload_id: '00000000-0000-0000-0000-000000000000' });
    request.flush({});
  });
});

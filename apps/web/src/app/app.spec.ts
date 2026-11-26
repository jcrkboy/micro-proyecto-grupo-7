import { HttpEventType, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { App } from './app';
import { UploadFormComponent } from './components/upload-form/upload-form';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
  });

  it('muestra el estado del modelo informado por la API', () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    TestBed.inject(HttpTestingController)
      .expectOne('/api/v1/model')
      .flush({
        model_ready: true,
        classes: ['W', 'N1', 'N2', 'N3', 'REM'],
        channels: ['EEG Fpz-Cz', 'EEG Pz-Oz', 'EOG horizontal'],
      });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Modelo disponible');
    expect(fixture.nativeElement.textContent).toContain('Convierte un estudio de sueño');
  });

  it('muestra carga antes de procesamiento según las respuestas HTTP', () => {
    const fixture = TestBed.createComponent(App);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/model').flush({ model_ready: true, classes: [], channels: [] });

    fixture.debugElement.query(By.directive(UploadFormComponent)).componentInstance.analyzeRequest.emit({
      patientName: 'Paciente de prueba',
      file: new File(['contenido'], 'registro.edf'),
      channels: ['EEG Pz-Oz'],
    });
    fixture.detectChanges();

    const stepStatus = () => Array.from(fixture.nativeElement.querySelectorAll('.analysis-steps li'),
      (step) => (step as HTMLElement).dataset['status']);
    expect(stepStatus()).toEqual(['active', 'pending', 'pending']);
    const upload = http.expectOne('/api/v1/uploads');
    expect(upload.request.method).toBe('POST');
    upload.event({ type: HttpEventType.UploadProgress, loaded: 65, total: 100 });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('progress').value).toBe(65);

    upload.flush({
      upload_id: '00000000-0000-0000-0000-000000000000',
      patient_name: 'Paciente de prueba',
      original_filename: 'registro.edf',
      size_bytes: 18,
      created_at: '2026-09-05T10:00:00',
      status: 'uploaded',
    });
    fixture.detectChanges();

    expect(stepStatus()).toEqual(['done', 'pending', 'pending']);
    const inference = http.expectOne('/api/v1/inferencia/progreso');
    let partialText = '{"type":"progress","stage":"processing"}\n{"type":"pro';
    inference.event({ type: HttpEventType.DownloadProgress, loaded: partialText.length, partialText });
    fixture.detectChanges();
    expect(stepStatus()).toEqual(['done', 'active', 'pending']);
    partialText += 'gress","stage":"overlap"}\n';
    inference.event({ type: HttpEventType.DownloadProgress, loaded: partialText.length, partialText });
    fixture.detectChanges();
    expect(stepStatus()).toEqual(['done', 'active', 'active']);
    partialText += '{"type":"progress","stage":"processing","timings":{"processing_ms":1500,"inference_ms":400,"overlap_ms":400}}\n';
    inference.event({ type: HttpEventType.DownloadProgress, loaded: partialText.length, partialText });
    fixture.detectChanges();
    expect(stepStatus()).toEqual(['done', 'active', 'paused']);
    expect(fixture.nativeElement.querySelector('[data-status="paused"] [role="timer"]').textContent.trim()).toBe('0,4 s');
    partialText += '{"type":"progress","stage":"inferring"}\n';
    inference.event({ type: HttpEventType.DownloadProgress, loaded: partialText.length, partialText });
    fixture.detectChanges();
    expect(stepStatus()).toEqual(['done', 'done', 'active']);
    inference.flush(partialText + '{"type":"error","detail":"Fin de la prueba"}\n');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="alert"]').textContent).toContain('Fin de la prueba');
  });

  it.each(['uploading', 'inferring'])('aborta la petición activa al cancelar en %s', (stage) => {
    const fixture = TestBed.createComponent(App);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/model').flush({ model_ready: true, channels: [], classes: [] });
    const form = fixture.debugElement.query(By.directive(UploadFormComponent)).componentInstance;
    form.analyzeRequest.emit({ patientName: 'Prueba', file: new File(['edf'], 'noche.edf'), channels: ['EEG Pz-Oz'] });
    let active = http.expectOne('/api/v1/uploads');
    if (stage === 'inferring') {
      active.flush({ upload_id: 'id' });
      active = http.expectOne('/api/v1/inferencia/progreso');
      active.event({ type: HttpEventType.DownloadProgress, loaded: 45, partialText: '{"type":"progress","stage":"inferring"}\n' });
    }
    fixture.detectChanges();
    form.cancelRequest.emit();
    fixture.detectChanges();
    expect(active.cancelled).toBe(true);
    expect(fixture.nativeElement.querySelector('.analysis-steps')).toBeNull();
    expect(fixture.nativeElement.querySelector('form')).toBeTruthy();
    http.verify();
  });
});

import { provideHttpClient } from '@angular/common/http';
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

    expect(fixture.nativeElement.textContent).toContain('Cargando archivo…');
    const upload = http.expectOne('/api/v1/uploads');
    expect(upload.request.method).toBe('POST');

    upload.flush({
      upload_id: '00000000-0000-0000-0000-000000000000',
      patient_name: 'Paciente de prueba',
      original_filename: 'registro.edf',
      size_bytes: 18,
      created_at: '2026-09-05T10:00:00',
      status: 'uploaded',
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Procesando señal…');
    http
      .expectOne('/api/v1/inferencia')
      .flush({ detail: 'Fin de la prueba' }, { status: 500, statusText: 'Test' });
  });
});

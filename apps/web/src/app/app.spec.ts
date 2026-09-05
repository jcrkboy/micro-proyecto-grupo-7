import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { App } from './app';

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
        channels: ['EEG Fpz-Cz', 'EEG Pz-Oz'],
      });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Modelo disponible');
    expect(fixture.nativeElement.textContent).toContain('Convierte un registro EEG');
  });

  it('muestra carga antes de procesamiento según las respuestas HTTP', () => {
    const fixture = TestBed.createComponent(App);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/model').flush({ model_ready: true, classes: [], channels: [] });

    const name = fixture.nativeElement.querySelector('#patient-name') as HTMLInputElement;
    name.value = 'Paciente de prueba';
    name.dispatchEvent(new Event('input'));
    const fileInput = fixture.nativeElement.querySelector('#edf-file') as HTMLInputElement;
    Object.defineProperty(fileInput, 'files', {
      configurable: true,
      value: [new File(['0       contenido'], 'registro.edf')],
    });
    fileInput.dispatchEvent(new Event('change'));
    (fixture.nativeElement.querySelector('form') as HTMLFormElement).dispatchEvent(
      new Event('submit'),
    );
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

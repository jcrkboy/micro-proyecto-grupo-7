import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UploadFormComponent } from './upload-form';

describe('UploadFormComponent', () => {
  let fixture: ComponentFixture<UploadFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [UploadFormComponent] }).compileComponents();
    fixture = TestBed.createComponent(UploadFormComponent);
    fixture.componentRef.setInput('state', 'ready');
    fixture.detectChanges();
  });

  it('rechaza extensiones diferentes de EDF antes de enviar', () => {
    selectFile(new File(['contenido'], 'registro.txt', { type: 'text/plain' }));
    expect(fixture.nativeElement.textContent).toContain('debe tener extensión .edf');
  });

  it('rechaza archivos que superan 50 MB antes de enviar', () => {
    const file = new File(['contenido'], 'registro.edf');
    Object.defineProperty(file, 'size', { value: 51 * 1024 * 1024 });
    selectFile(file);
    expect(fixture.nativeElement.textContent).toContain('supera el límite de 50 MB');
  });

  it('emite el EEG del archivo y el nombre normalizado', async () => {
    const emitted = vi.fn();
    fixture.componentInstance.analyzeRequest.subscribe(emitted);
    const name = fixture.nativeElement.querySelector('#patient-name') as HTMLInputElement;
    name.value = '  Paciente 024  ';
    name.dispatchEvent(new Event('input'));
    const header = '0'.padEnd(184) + '512'.padEnd(52) + '30'.padEnd(8) + '1'.padEnd(8) + '1'.padEnd(4);
    const signals = 'EEG Pz-Oz'.padEnd(216) + '100'.padEnd(40);
    const file = new File([header, signals, new Uint8Array(6000)], 'registro.edf');
    selectFile(file);
    await vi.waitFor(() => {
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector('input[type=checkbox]')?.checked).toBe(true);
    });
    (fixture.nativeElement.querySelector('form') as HTMLFormElement).dispatchEvent(
      new Event('submit'),
    );

    expect(emitted).toHaveBeenCalledWith({ patientName: 'Paciente 024', file, channels: ['EEG Pz-Oz'] });
  });

  it('bloquea un EDF con cabecera incompleta', async () => {
    selectFile(new File(['0       contenido'], 'registro.edf'));
    await vi.waitFor(() => {
      fixture.detectChanges();
      expect(fixture.nativeElement.textContent).toContain('cabecera EDF');
    });
    expect(fixture.nativeElement.querySelector('button[type=submit]').disabled).toBe(true);
  });

  function selectFile(file: File): void {
    const input = fixture.nativeElement.querySelector('#edf-file') as HTMLInputElement;
    Object.defineProperty(input, 'files', { configurable: true, value: [file] });
    input.dispatchEvent(new Event('change'));
    fixture.detectChanges();
  }
});

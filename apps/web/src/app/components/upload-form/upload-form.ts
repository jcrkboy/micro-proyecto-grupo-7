import { Component, computed, input, output, signal } from '@angular/core';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';

import type { WorkflowState } from '../../app';
import { EdfChannel, hasEeg, readEdfChannels } from '../../core/utils/edf-channels';

export const MAX_EDF_BYTES = 50 * 1024 * 1024;

export interface AnalysisRequest {
  patientName: string;
  file: File;
  channels: string[];
}

function validEdf(control: AbstractControl<File | null>): ValidationErrors | null {
  const file = control.value;
  if (!file) return null;
  if (!file.name.toLowerCase().endsWith('.edf')) return { edfExtension: true };
  if (file.size === 0) return { emptyFile: true };
  if (file.size > MAX_EDF_BYTES) return { maxSize: true };
  return null;
}

function nonBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { blank: true };
}

@Component({
  selector: 'app-upload-form',
  imports: [ReactiveFormsModule],
  templateUrl: './upload-form.html',
  styleUrl: './upload-form.css',
})
export class UploadFormComponent {
  readonly state = input.required<WorkflowState>();
  readonly modal = input(false);
  readonly analyzeRequest = output<AnalysisRequest>();

  protected readonly patientName = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.maxLength(120), nonBlank],
  });
  protected readonly file = new FormControl<File | null>(null, {
    validators: [Validators.required, validEdf],
  });
  protected readonly form = new FormGroup({ patientName: this.patientName, file: this.file });
  protected readonly busy = computed(() => ['uploading', 'processing'].includes(this.state()));
  protected readonly reading = signal(false);
  protected readonly readError = signal('');
  protected readonly available = signal<EdfChannel[] | null>(null);
  protected readonly selected = signal<string[]>([]);
  protected readonly hasSelectedEeg = computed(() => hasEeg(this.selected()));
  protected readonly hasAvailableEeg = computed(() =>
    hasEeg((this.available() ?? []).filter((ch) => ch.selectable).map((ch) => ch.name)),
  );
  protected readonly statusLabel = computed(() => {
    const labels: Partial<Record<WorkflowState, string>> = {
      uploading: 'Cargando archivo…',
      processing: 'Procesando señal…',
    };
    return labels[this.state()] ?? 'Analizar registro';
  });

  protected async onFileSelected(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.file.setValue(file);
    this.file.markAsTouched();
    this.available.set(null);
    this.selected.set([]);
    this.readError.set('');
    this.reading.set(!!file && this.file.valid);
    if (!file || this.file.invalid) return;
    try {
      const channels = await readEdfChannels(file);
      if (this.file.value !== file) return;
      this.available.set(channels);
      this.selected.set(channels.filter((ch) => ch.selectable).map((ch) => ch.name));
    } catch (error) {
      if (this.file.value === file) {
        this.readError.set(error instanceof Error ? error.message : 'No se pudo leer el EDF.');
      }
    } finally {
      if (this.file.value === file) this.reading.set(false);
    }
  }

  protected toggle(name: string, checked: boolean): void {
    this.selected.update((current) => checked ? [...current, name] : current.filter((ch) => ch !== name));
  }

  protected submit(): void {
    this.form.markAllAsTouched();
    const file = this.file.value;
    if (this.form.invalid || !file || this.busy() || !this.hasSelectedEeg()) return;
    this.analyzeRequest.emit({ patientName: this.patientName.value.trim(), file, channels: this.selected() });
  }

  protected formatSize(bytes: number): string {
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
}

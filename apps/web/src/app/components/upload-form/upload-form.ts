import { Component, computed, input, output } from '@angular/core';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';

import type { WorkflowState } from '../../app';

export const MAX_EDF_BYTES = 50 * 1024 * 1024;

export interface AnalysisRequest {
  patientName: string;
  file: File;
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
  protected readonly statusLabel = computed(() => {
    const labels: Partial<Record<WorkflowState, string>> = {
      uploading: 'Cargando archivo…',
      processing: 'Procesando señal…',
    };
    return labels[this.state()] ?? 'Analizar registro';
  });

  protected onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.file.setValue(input.files?.[0] ?? null);
    this.file.markAsTouched();
  }

  protected submit(): void {
    this.form.markAllAsTouched();
    const file = this.file.value;
    if (this.form.invalid || !file || this.busy()) return;
    this.analyzeRequest.emit({ patientName: this.patientName.value.trim(), file });
  }

  protected formatSize(bytes: number): string {
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
}

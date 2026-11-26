import { Component, ElementRef, Injector, afterNextRender, computed, inject, input, output, signal, viewChild } from '@angular/core';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';

import { WorkflowState, analysisInProgress } from '../../core/models/sleep-api.models';
import { EdfChannel, hasEeg, readEdfChannels } from '../../core/utils/edf-channels';
import { AnalysisDurations, formatElapsed } from '../../core/utils/analysis-timing';

export const MAX_EDF_BYTES = 70 * 1024 * 1024;

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
  protected readonly maxSizeMiB = MAX_EDF_BYTES / (1024 * 1024);
  readonly state = input.required<WorkflowState>();
  readonly uploadPercent = input<number | null>(null);
  readonly elapsed = input<AnalysisDurations | null>(null);
  readonly modal = input(false);
  readonly analyzeRequest = output<AnalysisRequest>();
  readonly cancelRequest = output<void>();
  private readonly card = viewChild.required<ElementRef<HTMLElement>>('card');
  private readonly injector = inject(Injector);
  protected readonly formatElapsed = formatElapsed;

  protected readonly patientName = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.maxLength(120), nonBlank],
  });
  protected readonly file = new FormControl<File | null>(null, {
    validators: [Validators.required, validEdf],
  });
  protected readonly form = new FormGroup({ patientName: this.patientName, file: this.file });
  protected readonly busy = computed(() => analysisInProgress(this.state()));
  protected readonly reading = signal(false);
  protected readonly readError = signal('');
  protected readonly available = signal<EdfChannel[] | null>(null);
  protected readonly selected = signal<string[]>([]);
  protected readonly hasSelectedEeg = computed(() => hasEeg(this.selected()));
  protected readonly hasAvailableEeg = computed(() =>
    hasEeg((this.available() ?? []).filter((ch) => ch.selectable).map((ch) => ch.name)),
  );
  protected readonly steps = computed(() => {
    const state = this.state();
    const inferencePaused = (state === 'processing' || state === 'waiting') && this.elapsed()?.inference != null;
    const waitingDetail = state === 'processing'
      ? 'Un modelo ya hizo su predicción. El otro sigue preparando sus señales.'
      : 'Esperando el siguiente cálculo.';
    return [
      {
        label: 'Subiendo archivo',
        duration: this.elapsed()?.upload ?? null,
        status: state === 'uploading' ? 'active' : 'done',
        detail: this.uploadPercent() === 100 ? 'Esperando confirmación de la carga.' : 'Enviando el EDF.',
      },
      {
        label: 'Procesando señales',
        duration: this.elapsed()?.processing ?? null,
        status: ['processing', 'overlap'].includes(state) ? 'active' : ['inferring', 'waiting', 'finalizing'].includes(state) ? 'done' : 'pending',
        detail: state === 'queued' ? 'Esperando al modelo.' : 'Filtrando las señales y extrayendo características.',
      },
      {
        label: 'Clasificando etapas del sueño',
        duration: this.elapsed()?.inference ?? null,
        status: ['overlap', 'inferring'].includes(state) ? 'active' : inferencePaused ? 'paused' : state === 'finalizing' ? 'done' : 'pending',
        detail: inferencePaused ? waitingDetail : 'Estimando el estadio de cada época de 30 segundos.',
      },
    ];
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
    const card = this.card().nativeElement;
    const previousHeight = card.getBoundingClientRect().height;
    this.analyzeRequest.emit({ patientName: this.patientName.value.trim(), file, channels: this.selected() });
    afterNextRender(() => {
      if (!this.busy()) return;
      card.querySelector('form.form-exit')?.setAttribute('inert', '');
      card.querySelector<HTMLElement>('h2')?.focus({ preventScroll: true });
      if (card.animate && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        const target = CSS.supports('interpolate-size', 'allow-keywords') ? 'auto' : card.getBoundingClientRect().height + 'px';
        card.animate(
          [{ height: previousHeight + 'px' }, { height: target }],
          { duration: 360, easing: 'cubic-bezier(.22,.68,.2,1)' },
        );
      }
    }, { injector: this.injector });
  }

  protected cancel(): void {
    this.card().nativeElement.getAnimations?.().forEach((animation) => animation.cancel());
    this.cancelRequest.emit();
    afterNextRender(() => {
      this.card().nativeElement.querySelector<HTMLButtonElement>('form:not(.form-exit) button[type=submit]')?.focus();
    }, { injector: this.injector });
  }

  protected formatSize(bytes: number): string {
    return `${(bytes / 1024 / 1024).toFixed(1)} MiB`;
  }
}

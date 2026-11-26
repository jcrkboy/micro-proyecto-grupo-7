import { Component, ElementRef, computed, effect, input, output, viewChild } from '@angular/core';

import { WorkflowState, analysisInProgress } from '../../core/models/sleep-api.models';
import { AnalysisDurations } from '../../core/utils/analysis-timing';
import { AnalysisRequest, UploadFormComponent } from '../upload-form/upload-form';

@Component({
  selector: 'app-analysis-modal',
  imports: [UploadFormComponent],
  templateUrl: './analysis-modal.html',
  styleUrl: './analysis-modal.css',
})
export class AnalysisModalComponent {
  readonly open = input.required<boolean>();
  readonly state = input.required<WorkflowState>();
  readonly uploadPercent = input<number | null>(null);
  readonly elapsed = input<AnalysisDurations | null>(null);
  readonly errorMessage = input<string | null>(null);
  readonly analyzeRequest = output<AnalysisRequest>();
  readonly cancelRequest = output<void>();
  readonly closeRequest = output<void>();

  protected readonly busy = computed(() => analysisInProgress(this.state()));
  private readonly dialog = viewChild<ElementRef<HTMLDialogElement>>('dialog');
  private readonly closeButton = viewChild<ElementRef<HTMLButtonElement>>('closeButton');

  constructor() {
    effect(() => {
      const shouldOpen = this.open();
      const dialog = this.dialog()?.nativeElement;
      if (!dialog) return;

      if (shouldOpen && !dialog.open) {
        dialog.showModal();
        queueMicrotask(() => this.closeButton()?.nativeElement.focus());
      } else if (!shouldOpen && dialog.open) {
        dialog.close();
      }
    });
  }

  protected requestClose(): void {
    if (!this.busy()) this.closeRequest.emit();
  }

  protected onCancel(event: Event): void {
    event.preventDefault();
    this.requestClose();
  }

  protected onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) this.requestClose();
  }
}

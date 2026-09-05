import { Component, ElementRef, computed, effect, input, output, viewChild } from '@angular/core';

import type { WorkflowState } from '../../app';
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
  readonly errorMessage = input<string | null>(null);
  readonly analyzeRequest = output<AnalysisRequest>();
  readonly closeRequest = output<void>();

  protected readonly busy = computed(() => ['uploading', 'processing'].includes(this.state()));
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

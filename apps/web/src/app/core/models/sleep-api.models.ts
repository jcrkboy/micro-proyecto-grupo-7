export const SLEEP_STAGES = ['W', 'REM', 'N1', 'N2', 'N3'] as const;
export type SleepStage = (typeof SLEEP_STAGES)[number];

export interface ModelInfo {
  model_ready: boolean;
  artifact_version?: number | null;
  model_type?: string | null;
  classes: string[];
  feature_count?: number | null;
  channels: string[];
  expected_sfreq?: number | null;
  epoch_seconds?: number | null;
}

export interface UploadResponse {
  upload_id: string;
  patient_name: string;
  original_filename: string;
  size_bytes: number;
  created_at: string;
  status: string;
}

export interface EpochPrediction {
  epoch_index: number;
  onset_seconds: number;
  duration_seconds: number;
  stage: SleepStage;
  confidence: number;
  probabilities: Record<string, number>;
}

export interface SleepSummary {
  total_epochs: number;
  total_duration_seconds: number;
  duration_by_stage_seconds: Record<string, number>;
  percentage_by_stage: Record<string, number>;
}

export interface PredictionResponse {
  prediction_id: string;
  upload_id: string;
  patient_name: string;
  model_version: string;
  preprocessing_version: string;
  channels: string[];
  sfreq: number;
  epoch_seconds: number;
  epochs: EpochPrediction[];
  summary: SleepSummary;
  disclaimer: string;
}

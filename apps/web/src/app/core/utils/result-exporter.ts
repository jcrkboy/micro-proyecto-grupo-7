import { PredictionResponse } from '../models/sleep-api.models';

export function predictionToCsv(prediction: PredictionResponse): string {
  const classes = Object.keys(prediction.epochs[0]?.probabilities ?? {}).sort();
  const header = [
    'epoch_index',
    'onset_seconds',
    'duration_seconds',
    'stage',
    'confidence',
    ...classes.map((stage) => `probability_${stage}`),
  ];
  const rows = prediction.epochs.map((epoch) => [
    epoch.epoch_index,
    epoch.onset_seconds,
    epoch.duration_seconds,
    epoch.stage,
    epoch.confidence,
    ...classes.map((stage) => epoch.probabilities[stage] ?? ''),
  ]);
  return [header, ...rows].map((row) => row.join(',')).join('\n');
}

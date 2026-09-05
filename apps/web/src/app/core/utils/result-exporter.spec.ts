import { PredictionResponse } from '../models/sleep-api.models';
import { predictionToCsv } from './result-exporter';

describe('exportación de resultados', () => {
  it('genera columnas de probabilidad estables', () => {
    const prediction = {
      epochs: [
        {
          epoch_index: 0,
          onset_seconds: 0,
          duration_seconds: 30,
          stage: 'W',
          confidence: 0.8,
          probabilities: { W: 0.8, N1: 0.2 },
        },
      ],
    } as unknown as PredictionResponse;

    expect(predictionToCsv(prediction)).toBe(
      'epoch_index,onset_seconds,duration_seconds,stage,confidence,probability_N1,probability_W\n0,0,30,W,0.8,0.2,0.8',
    );
  });
});

import { EpochPrediction } from '../models/sleep-api.models';
import { createHypnogramOption, formatClock, groupConsecutiveStages } from './hypnogram';

describe('transformación del hipnograma', () => {
  const epochs: EpochPrediction[] = [
    {
      epoch_index: 0,
      onset_seconds: 0,
      duration_seconds: 30,
      stage: 'W',
      confidence: 0.8,
      probabilities: { W: 0.8, N2: 0.2 },
    },
    {
      epoch_index: 1,
      onset_seconds: 30,
      duration_seconds: 30,
      stage: 'N2',
      confidence: 0.7,
      probabilities: { W: 0.3, N2: 0.7 },
    },
  ];

  it('convierte segundos a un reloj legible', () => {
    expect(formatClock(3661)).toBe('01:01:01');
  });

  it('agrupa únicamente las épocas vecinas del mismo estadio', () => {
    expect(groupConsecutiveStages([...epochs, epochs[1]])).toEqual([
      { startIndex: 0, endIndex: 0, stageIndex: 0, previousStageIndex: -1 },
      { startIndex: 1, endIndex: 2, stageIndex: 3, previousStageIndex: 0 },
    ]);
  });

  it('crea tramos continuos con conectores verticales personalizados', () => {
    const option = createHypnogramOption(epochs) as any;
    expect(option.xAxis.data).toEqual(['00:00:00', '00:00:30']);
    expect(option.series[0].data).toEqual([
      [0, 0, 0, -1],
      [1, 1, 3, 0],
    ]);
    expect(option.series[0].type).toBe('custom');
    expect(option.series[0].renderItem).toBeTypeOf('function');
    expect(option.series).toHaveLength(1);
    expect(option.yAxis.inverse).toBe(true);
    expect(option.visualMap).toBeUndefined();
    expect(option.tooltip).toBeUndefined();
    expect(option.dataZoom).toHaveLength(2);
  });
});

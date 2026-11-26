import { AnalysisTimer, formatElapsed } from './analysis-timing';

it('pausa la inferencia entre ramas y conserva el tiempo del servidor al recibir el resultado', () => {
  let now = 1000;
  const clock = vi.spyOn(performance, 'now').mockImplementation(() => now);
  try {
    const timer = new AnalysisTimer();
    now = 1400;
    timer.uploadComplete();
    now = 3400;
    expect(timer.read()).toEqual({ upload: 400, processing: null, inference: null, overlap: 0, total: 2400 });
    timer.mark('overlap', { processing_ms: 600, inference_ms: 0, overlap_ms: 0 });
    now += 500;
    expect(timer.read().inference).toBe(500);
    timer.mark('processing', { processing_ms: 1100, inference_ms: 500, overlap_ms: 500 });
    now += 3000;
    expect(timer.read()).toMatchObject({ processing: 4100, inference: 500, overlap: 500 });
    timer.mark('inferring', { processing_ms: 4100, inference_ms: 500, overlap_ms: 500 });
    now += 200;
    expect(timer.read()).toMatchObject({ processing: 4100, inference: 700, overlap: 500 });
    timer.mark('finalizing', { processing_ms: 4100, inference_ms: 700, overlap_ms: 500 });
    now = 9900;
    expect(timer.read()).toEqual({ upload: 400, processing: 4100, inference: 700, overlap: 500, total: 8900 });
    expect(formatElapsed(60_500)).toBe('1 min 0,5 s');
    expect(formatElapsed(63)).toBe('< 0,1 s');
  } finally {
    clock.mockRestore();
  }
});

it('omite los tiempos del modelo si la API no los mide', () => {
  const timer = new AnalysisTimer();
  timer.mark('overlap');
  expect(timer.read()).toMatchObject({ processing: null, inference: null, overlap: 0 });
});

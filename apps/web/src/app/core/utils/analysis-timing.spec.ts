import { AnalysisTimer, formatElapsed } from './analysis-timing';

it('mide el total de pared y usa los hitos del servidor aunque lleguen juntos', () => {
  let now = 1000;
  const clock = vi.spyOn(performance, 'now').mockImplementation(() => now);
  try {
    const timer = new AnalysisTimer();
    now = 1400;
    timer.uploadComplete();
    now = 3400;
    expect(timer.read()).toEqual({ upload: 400, processing: null, inference: null, total: 2400 });
    timer.mark('processing', 1000);
    timer.mark('overlap', 2000);
    timer.mark('inferring', 6000);
    now = 9900;
    expect(timer.read(8000)).toEqual({ upload: 400, processing: 5000, inference: 6000, total: 8900 });
    expect(formatElapsed(60_500)).toBe('1 min 0,5 s');
    expect(formatElapsed(63)).toBe('< 0,1 s');
  } finally {
    clock.mockRestore();
  }
});

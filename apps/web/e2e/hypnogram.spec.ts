import { expect, test } from '@playwright/test';

const STAGES = ['W', 'REM', 'N1', 'N2', 'N3'] as const;
const COLORS = [
  [32, 163, 122],
  [109, 92, 231],
  [239, 159, 39],
  [54, 135, 216],
  [24, 61, 102],
] as const;

test('muestra los estados en orden y dibuja los cinco colores del hipnograma', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });

  let releaseUpload!: () => void;
  let releaseInference!: () => void;
  let releaseSecondUpload!: () => void;
  let releaseSecondInference!: () => void;
  const uploadGate = new Promise<void>((resolve) => (releaseUpload = resolve));
  const inferenceGate = new Promise<void>((resolve) => (releaseInference = resolve));
  const secondUploadGate = new Promise<void>((resolve) => (releaseSecondUpload = resolve));
  const secondInferenceGate = new Promise<void>((resolve) => (releaseSecondInference = resolve));
  const prediction = createPrediction();
  const secondPrediction = createPrediction('Segundo paciente');
  let uploadRequestCount = 0;
  let inferenceRequestCount = 0;

  await page.route('**/api/v1/model', (route) =>
    route.fulfill({
      json: {
        model_ready: true,
        classes: STAGES,
        channels: ['EEG Fpz-Cz', 'EEG Pz-Oz'],
      },
    }),
  );
  await page.route('**/api/v1/uploads', async (route) => {
    uploadRequestCount += 1;
    await (uploadRequestCount === 1 ? uploadGate : secondUploadGate);
    await route.fulfill({
      status: 201,
      json: {
        upload_id: prediction.upload_id,
        patient_name: prediction.patient_name,
        original_filename: 'registro.edf',
        size_bytes: 1024,
        created_at: '2026-09-05T10:00:00',
        status: 'uploaded',
      },
    });
  });
  await page.route('**/api/v1/inferencia', async (route) => {
    inferenceRequestCount += 1;
    await (inferenceRequestCount === 1 ? inferenceGate : secondInferenceGate);
    await route.fulfill({ json: inferenceRequestCount === 1 ? prediction : secondPrediction });
  });

  await page.goto('/');
  await expect(page.locator('link[rel="icon"]')).toHaveAttribute('href', 'favicon.svg');
  const faviconResponse = await page.request.get('/favicon.svg');
  expect(faviconResponse.ok()).toBe(true);
  expect(faviconResponse.headers()['content-type']).toContain('image/svg+xml');
  await page.getByLabel('Nombre o identificador del paciente').fill('Paciente Playwright');
  await page.locator('#edf-file').setInputFiles({
    name: 'registro.edf',
    mimeType: 'application/octet-stream',
    buffer: Buffer.from('0       contenido de prueba'),
  });
  await page.getByRole('button', { name: 'Analizar registro' }).click();

  await expect(page.getByRole('button', { name: 'Cargando archivo…' })).toBeVisible();
  releaseUpload();
  await expect(page.getByRole('button', { name: 'Procesando señal…' })).toBeVisible();
  releaseInference();

  await expect(page.getByRole('heading', { name: 'Resumen de Paciente Playwright' })).toBeVisible();
  await expect(page.getByText('Convierte un registro EEG')).toBeHidden();
  await expect(page.getByRole('heading', { name: 'Hipnograma' })).toBeVisible();
  await expect(page.locator('app-hypnogram canvas').first()).toBeVisible();
  await page.waitForTimeout(500);

  const colorPixelCounts = await page
    .locator('app-hypnogram canvas')
    .evaluateAll((canvases, colors) => {
      const counts = colors.map(() => 0);
      for (const element of canvases) {
        const canvas = element as HTMLCanvasElement;
        const context = canvas.getContext('2d');
        if (!context) continue;
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
        for (let offset = 0; offset < pixels.length; offset += 4) {
          colors.forEach(([red, green, blue], index) => {
            if (
              Math.abs(pixels[offset] - red) <= 3 &&
              Math.abs(pixels[offset + 1] - green) <= 3 &&
              Math.abs(pixels[offset + 2] - blue) <= 3 &&
              pixels[offset + 3] > 200
            ) {
              counts[index] += 1;
            }
          });
        }
      }
      return counts;
    }, COLORS);

  colorPixelCounts.forEach((count) => expect(count).toBeGreaterThan(100));

  const connectorHasStageColors = await page
    .locator('app-hypnogram canvas')
    .first()
    .evaluate((element, colors) => {
      const canvas = element as HTMLCanvasElement;
      const context = canvas.getContext('2d');
      if (!context) return colors.map(() => false);

      const scaleX = canvas.width / canvas.clientWidth;
      const scaleY = canvas.height / canvas.clientHeight;
      const gridWidth = canvas.clientWidth - 52 - 24;
      const gridHeight = canvas.clientHeight - 28 - 76;
      // La época 100 inicia W justo después de N3: el conector atraviesa las cinco filas.
      const connectorX = (52 + (100 / 400) * gridWidth) * scaleX;

      return colors.map(([red, green, blue], stageIndex) => {
        const stageY = (28 + ((stageIndex + 0.5) / 5) * gridHeight) * scaleY;
        const pixels = context.getImageData(connectorX - 2, stageY - 2, 5, 5).data;
        for (let offset = 0; offset < pixels.length; offset += 4) {
          if (
            Math.abs(pixels[offset] - red) <= 6 &&
            Math.abs(pixels[offset + 1] - green) <= 6 &&
            Math.abs(pixels[offset + 2] - blue) <= 6 &&
            pixels[offset + 3] > 200
          ) {
            return true;
          }
        }
        return false;
      });
    }, COLORS);
  expect(connectorHasStageColors).toEqual([true, true, true, true, true]);

  const chart = page.locator('app-hypnogram [echarts]');
  await chart.scrollIntoViewIfNeeded();
  const chartBox = await chart.boundingBox();
  expect(chartBox).not.toBeNull();
  await page.mouse.move(chartBox!.x + chartBox!.width / 2, chartBox!.y + chartBox!.height * 0.78);
  await expect(page.getByTestId('epoch-pointer')).toBeVisible();
  await expect(page.getByTestId('epoch-tooltip')).toContainText('84.0%');

  await page.screenshot({ path: 'test-results/hypnogram-colored.png', fullPage: true });

  await page.getByRole('button', { name: 'Nuevo análisis' }).click();
  const modal = page.getByRole('dialog', { name: 'Iniciar un nuevo análisis' });
  await expect(modal).toBeVisible();
  await expect(modal.getByRole('heading', { name: 'Carga del registro' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Resumen de Paciente Playwright' })).toBeVisible();
  await expect(modal.getByRole('button', { name: 'Cerrar nuevo análisis' })).toBeFocused();
  await page.waitForTimeout(250);
  await page.screenshot({ path: 'test-results/new-analysis-modal.png' });

  await page.keyboard.press('Escape');
  await expect(modal).toBeHidden();
  await expect(page.getByRole('heading', { name: 'Resumen de Paciente Playwright' })).toBeVisible();

  await page.getByRole('button', { name: 'Nuevo análisis' }).click();
  await modal.getByLabel('Nombre o identificador del paciente').fill('Segundo paciente');
  await modal.locator('#edf-file').setInputFiles({
    name: 'segundo-registro.edf',
    mimeType: 'application/octet-stream',
    buffer: Buffer.from('0       segundo contenido de prueba'),
  });
  await modal.getByRole('button', { name: 'Analizar registro' }).click();

  await expect(modal.getByRole('button', { name: 'Cargando archivo…' })).toBeVisible();
  await expect(modal.getByRole('button', { name: 'Cerrar nuevo análisis' })).toBeDisabled();
  await expect(page.getByRole('heading', { name: 'Resumen de Paciente Playwright' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(modal).toBeVisible();

  releaseSecondUpload();
  await expect(modal.getByRole('button', { name: 'Procesando señal…' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Resumen de Paciente Playwright' })).toBeVisible();
  releaseSecondInference();

  await expect(modal).toBeHidden();
  await expect(page.getByRole('heading', { name: 'Resumen de Segundo paciente' })).toBeVisible();
  expect(consoleErrors).toEqual([]);
});

function createPrediction(patientName = 'Paciente Playwright') {
  const epochs = Array.from({ length: 400 }, (_, epochIndex) => {
    const block = Math.floor(epochIndex / 20);
    const stage = STAGES[block % STAGES.length];
    return {
      epoch_index: epochIndex,
      onset_seconds: epochIndex * 30,
      duration_seconds: 30,
      stage,
      confidence: 0.84,
      probabilities: Object.fromEntries(
        STAGES.map((candidate) => [candidate, candidate === stage ? 0.84 : 0.04]),
      ),
    };
  });
  const durationByStage = Object.fromEntries(
    STAGES.map((stage) => [stage, epochs.filter((epoch) => epoch.stage === stage).length * 30]),
  );
  return {
    prediction_id: '10000000-0000-0000-0000-000000000000',
    upload_id: '20000000-0000-0000-0000-000000000000',
    patient_name: patientName,
    model_version: 'test-v1',
    preprocessing_version: 'test-v1',
    channels: ['EEG Fpz-Cz', 'EEG Pz-Oz'],
    sfreq: 100,
    epoch_seconds: 30,
    epochs,
    summary: {
      total_epochs: epochs.length,
      total_duration_seconds: epochs.length * 30,
      duration_by_stage_seconds: durationByStage,
      percentage_by_stage: Object.fromEntries(
        STAGES.map((stage) => [stage, (durationByStage[stage] / (epochs.length * 30)) * 100]),
      ),
    },
    disclaimer: 'Resultado preliminar para revisión profesional.',
  };
}

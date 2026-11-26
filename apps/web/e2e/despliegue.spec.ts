import { expect, test } from '@playwright/test';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

test.skip(!process.env['PLAYWRIGHT_BASE_URL'], 'Requiere el despliegue local en ejecución.');

const estudios = [
  { archivo: 'apps/api/tests/fixtures/sample_eeg_60s.edf', epocas: 2 },
  { archivo: 'datos/example.edf', epocas: 1196 },
];

test('lee la cabecera localmente y reinicia la selección al reemplazar el EDF', async ({ page }) => {
  const ruta = resolve(__dirname, '../../..', estudios[0].archivo);
  const archivo = readFileSync(ruta);
  for (const nombre of ['EEG Fpz-Cz', 'EEG Pz-Oz']) {
    archivo.write('AUX', archivo.indexOf(nombre), 'ascii');
  }
  const cargas: string[] = [];
  page.on('request', (request) => {
    if (request.url().endsWith('/uploads')) cargas.push(request.url());
  });
  await page.goto('/');
  const input = page.locator('#edf-file');
  await input.setInputFiles({ name: 'sin-eeg.edf', mimeType: 'application/octet-stream', buffer: archivo });
  await expect(page.getByRole('alert')).toContainText('necesita un EEG');
  await expect(page.getByRole('checkbox', { name: /AUX Pz-Oz/ })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Analizar registro' })).toBeDisabled();
  await input.setInputFiles(ruta);
  await expect(page.getByRole('checkbox', { name: /EEG Pz-Oz/ })).toBeChecked();
  await expect(page.getByRole('checkbox', { name: /AUX/ })).toHaveCount(0);
  expect(cargas).toHaveLength(0);
});

test('cancela una inferencia en curso y permite reutilizar la selección', async ({ page }) => {
  const ruta = resolve(__dirname, '../../..', estudios[1].archivo);
  test.skip(!existsSync(ruta), 'El EDF nocturno se obtiene con DVC.');
  test.setTimeout(120_000);
  await page.goto('/');
  await page.getByLabel('Nombre o identificador del paciente').fill('Prueba de cancelación');
  await page.locator('#edf-file').setInputFiles(ruta);
  await page.getByRole('checkbox', { name: /EEG Fpz-Cz/ }).uncheck();
  const button = page.getByRole('button', { name: 'Analizar registro' });
  await button.click();
  const signals = page.getByRole('list', { name: 'Señales elegidas' });
  await expect(signals.getByRole('listitem')).toHaveText(['EEG Pz-Oz', 'EOG horizontal', 'EMG submental']);
  await expect(page.locator('li[data-status="active"]').filter({ hasText: 'Procesando señales' })).toBeVisible({ timeout: 60_000 });
  await expect(page.locator('.analysis-steps li').nth(1).getByRole('timer')).toContainText(/\d.*s/);
  const aborted = page.waitForEvent('requestfailed', (request) => request.url().endsWith('/inferencia/progreso'));
  await page.getByRole('button', { name: 'Cancelar' }).click();
  await aborted;
  await expect(button).toBeFocused();
  await expect(page.getByLabel('Nombre o identificador del paciente')).toHaveValue('Prueba de cancelación');
  await expect(page.getByText('example.edf', { exact: true })).toBeVisible();
  await expect(page.getByRole('checkbox', { name: /EEG Fpz-Cz/ })).not.toBeChecked();
  await expect(page.getByRole('checkbox', { name: /EEG Pz-Oz/ })).toBeChecked();
  await expect(page.getByRole('alert')).toHaveCount(0);
});

for (const { archivo, epocas } of estudios) {
  test(`procesa ${archivo} con el modelo desplegado`, async ({ page }, testInfo) => {
    const ruta = resolve(__dirname, '../../..', archivo);
    test.skip(archivo.startsWith('datos/') && !existsSync(ruta), 'El EDF nocturno se obtiene con DVC.');
    test.setTimeout(360_000);

    await page.goto('/');
    await expect(page.getByText('Modelo disponible', { exact: true })).toBeVisible();
    await page.getByLabel('Nombre o identificador del paciente').fill('Prueba de despliegue');
    await page.locator('#edf-file').setInputFiles(ruta);
    const eeg1 = page.getByRole('checkbox', { name: /EEG Fpz-Cz/ });
    const eeg2 = page.getByRole('checkbox', { name: /EEG Pz-Oz/ });
    const eog = page.getByRole('checkbox', { name: /EOG horizontal/ });
    await expect(eeg1).toBeChecked();
    await expect(eeg2).toBeChecked();
    await expect(eog).toBeChecked();
    let canales = ['EEG Fpz-Cz', 'EEG Pz-Oz', 'EOG horizontal', 'EMG submental'];
    if (epocas === 2) {
      await expect(page.getByRole('checkbox', { name: /EMG/ })).toHaveCount(0);
      await eeg1.uncheck();
      await eeg2.uncheck();
      await expect(page.getByRole('button', { name: 'Analizar registro' })).toBeDisabled();
      await eeg2.check();
      await eog.uncheck();
      canales = ['EEG Pz-Oz'];
    } else {
      await page.setViewportSize({ width: 1280, height: 640 });
      await expect(page.getByRole('checkbox', { name: /EMG submental/ })).toBeChecked();
      await expect(page.getByRole('checkbox', { name: /Marker/ })).toBeDisabled();
      expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBeLessThanOrEqual(640);
    }
    await page.locator('app-upload-form').screenshot({ path: testInfo.outputPath('seleccion-canales.png') });
    const [carga, inferencia] = await Promise.all([
      page.waitForResponse('**/api/v1/uploads'),
      page.waitForResponse('**/api/v1/inferencia/progreso', { timeout: 310_000 }),
      page.getByRole('button', { name: 'Analizar registro' }).click(),
    ]);
    expect(carga.status()).toBe(201);
    expect(inferencia.status()).toBe(200);
    if (epocas > 2) {
      await expect(page.locator('.analysis-steps li[data-status="active"]').filter({ hasText: 'Procesando señales' }))
        .toBeVisible({ timeout: 60_000 });
      await expect(page.getByRole('list', { name: 'Señales elegidas' }).getByRole('listitem')).toHaveText(canales);
    }
    const eventos = (await inferencia.text()).trim().split('\n').map((linea) => JSON.parse(linea));
    const etapas = eventos.filter((evento) => evento.type === 'progress').map((evento) => evento.stage);
    expect(etapas[0]).toBe('processing');
    expect(etapas).toContain('inferring');
    expect(etapas.at(-1)).toBe('finalizing');
    expect(eventos.at(-1).type).toBe('result');
    const hitos = eventos.map((evento) => evento.elapsed_ms);
    expect(hitos.every(Number.isFinite)).toBe(true);
    expect(hitos).toEqual([...hitos].sort((a, b) => a - b));
    const tiempos = eventos.at(-1).timings;
    expect(tiempos).toEqual(eventos.at(-2).timings);
    expect(tiempos.processing_ms).toBeGreaterThan(0);
    expect(tiempos.inference_ms).toBeGreaterThan(0);
    expect(tiempos.overlap_ms).toBeLessThanOrEqual(Math.min(tiempos.processing_ms, tiempos.inference_ms));
    expect(tiempos.processing_ms + tiempos.inference_ms - tiempos.overlap_ms).toBeLessThanOrEqual(hitos.at(-1));
    const resultado = eventos.at(-1).prediction;
    expect(inferencia.request().postDataJSON().channels).toEqual(canales);
    expect(resultado.channels).toEqual(canales);
    expect(resultado.upload_id).toBe((await carga.json()).upload_id);
    expect(resultado.epochs).toHaveLength(epocas);
    expect(resultado.summary.total_duration_seconds).toBe(epocas * 30);

    await expect(page.getByRole('heading', { name: 'Resumen de Prueba de despliegue' })).toBeVisible();
    await expect(page.locator('.result-timings dd')).toHaveText([/\d.*s/, /\d.*s/, /\d.*s/, /\d.*s/]);
    await expect(page.getByText(`${epocas} épocas ·`, { exact: false })).toBeVisible();
    await expect(page.locator('app-hypnogram canvas').first()).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath('hipnograma.png'),
      fullPage: true,
      animations: 'disabled',
    });

    for (const formato of ['CSV', 'JSON']) {
      const [descarga] = await Promise.all([
        page.waitForEvent('download'),
        page.getByRole('button', { name: `Descargar ${formato}` }).click(),
      ]);
      const contenido = readFileSync((await descarga.path())!, 'utf8');
      if (formato === 'JSON') {
        expect(JSON.parse(contenido)).toEqual(resultado);
      } else {
        expect(contenido.trim().split('\n')).toHaveLength(epocas + 1);
      }
    }
  });
}

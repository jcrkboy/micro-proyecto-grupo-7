import { expect, test } from '@playwright/test';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

test.skip(!process.env['PLAYWRIGHT_BASE_URL'], 'Requiere el despliegue local en ejecución.');

const estudios = [
  { archivo: 'apps/api/tests/fixtures/sample_eeg_60s.edf', epocas: 2 },
  { archivo: 'datos/example.edf', epocas: 1196 },
];

for (const { archivo, epocas } of estudios) {
  test(`procesa ${archivo} con el modelo desplegado`, async ({ page }, testInfo) => {
    const ruta = resolve(__dirname, '../../..', archivo);
    test.skip(archivo.startsWith('datos/') && !existsSync(ruta), 'El EDF nocturno se obtiene con DVC.');
    test.setTimeout(360_000);

    await page.goto('/');
    await expect(page.getByText('Modelo disponible', { exact: true })).toBeVisible();
    await page.getByLabel('Nombre o identificador del paciente').fill('Prueba de despliegue');
    await page.locator('#edf-file').setInputFiles(ruta);
    const [carga, inferencia] = await Promise.all([
      page.waitForResponse('**/api/v1/uploads'),
      page.waitForResponse('**/api/v1/inferencia', { timeout: 310_000 }),
      page.getByRole('button', { name: 'Analizar registro' }).click(),
    ]);
    expect(carga.status()).toBe(201);
    expect(inferencia.status()).toBe(200);
    const resultado = await inferencia.json();
    expect(resultado.upload_id).toBe((await carga.json()).upload_id);
    expect(resultado.epochs).toHaveLength(epocas);
    expect(resultado.summary.total_duration_seconds).toBe(epocas * 30);

    await expect(page.getByRole('heading', { name: 'Resumen de Prueba de despliegue' })).toBeVisible();
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

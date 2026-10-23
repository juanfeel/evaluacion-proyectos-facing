import { defineConfig, devices } from '@playwright/test';

/**
 * Pruebas de humo contra un despliegue real (por defecto, producción).
 * Credenciales SOLO por variables de entorno: E2E_ADMIN_EMAIL y E2E_ADMIN_PASSWORD.
 *   E2E_URL=https://... E2E_ADMIN_EMAIL=... E2E_ADMIN_PASSWORD=... npx playwright test
 */
export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  reporter: [['list']],
  use: {
    baseURL: process.env['E2E_URL'] ?? 'http://localhost:4200',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    locale: 'es-CO',
    timezoneId: 'America/Bogota',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});

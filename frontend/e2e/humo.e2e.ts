import { expect, Page, test } from '@playwright/test';

/**
 * Humo de producción (CLAUDE.md, fase 9):
 *  1. Login de admin y creación de un proyecto de prueba (con sus dos jurados).
 *  2. Login de jurado con la cédula, cambio de contraseña y envío de una evaluación.
 * Crea datos marcados con HUMO-<sello>; se borran después (ver README, «Pruebas de humo»).
 */
const ADMIN_EMAIL = process.env['E2E_ADMIN_EMAIL'] ?? '';
const ADMIN_PASSWORD = process.env['E2E_ADMIN_PASSWORD'] ?? '';
const SELLO = Date.now().toString().slice(-7);
const CODIGO = `HUMO-${SELLO}`;
const JURADOS = [1, 2].map((i) => ({
  nombre: `Jurado Humo ${i} ${SELLO}`,
  cedula: `77${SELLO}${i}`,
  email: `humo${i}.${SELLO}@udenar.edu.co`,
}));
const NUEVA = `Humo-Facing-${SELLO}`;

test.describe.configure({ mode: 'serial' });
test.skip(!ADMIN_EMAIL || !ADMIN_PASSWORD, 'Defina E2E_ADMIN_EMAIL y E2E_ADMIN_PASSWORD');

async function entrar(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.getByLabel('Correo institucional').fill(email);
  await page.getByLabel('Contraseña', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Ingresar' }).click();
}

async function elegir(page: Page, combo: string, opcion: string | RegExp, raiz = page.locator('body')) {
  await raiz.getByRole('combobox', { name: combo }).click();
  await page.getByRole('option', { name: opcion }).first().click();
}

test('1. admin: login, registra docentes y un proyecto de prueba con sus dos jurados', async ({ page }) => {
  await entrar(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await expect(page).toHaveURL(/\/admin\/inicio/);
  await expect(page.getByText('Proyectos que faltan por evaluar')).toBeVisible();

  await page.goto('/admin/docentes');
  for (const j of JURADOS) {
    await page.getByRole('button', { name: 'Registrar docente' }).click();
    const d = page.locator('mat-dialog-container');
    await d.getByLabel('Nombre completo').fill(j.nombre);
    await d.getByLabel('Cédula').fill(j.cedula);
    await d.getByLabel('Correo institucional').fill(j.email);
    await elegir(page, 'Departamento académico', 'Sistemas', d);
    await d.getByRole('button', { name: 'Guardar' }).click();
    await expect(page.getByText(`${j.nombre} registrado`)).toBeVisible();
  }

  await page.goto('/admin/proyectos/nuevo');
  await page.getByLabel('Código').fill(CODIGO);
  await page.getByLabel('Título del proyecto').fill('Proyecto de prueba de humo (borrar)');
  await elegir(page, 'Área de conocimiento', 'Ingeniería de software');
  await elegir(page, 'Origen', 'Semillero de investigación');
  await elegir(page, 'Estado del proyecto', 'En curso');
  await page.getByRole('radio', { name: 'Investigación (INV)' }).check();
  await page.locator('.autor').first().getByLabel('Nombre completo').fill('Autor Humo');
  await page.locator('.autor').first().getByLabel('Cédula').fill(`88${SELLO}`);
  await page.getByRole('button', { name: 'Guardar proyecto' }).click();
  await expect(page.getByText(`Proyecto ${CODIGO} registrado.`)).toBeVisible();

  await page.goto('/admin/asignaciones');
  const fila = page.locator('article.asignacion', { hasText: CODIGO });
  await elegir(page, 'Jurado 1', JURADOS[0].nombre, fila);
  await elegir(page, 'Jurado 2', JURADOS[1].nombre, fila);
  await fila.getByRole('button', { name: 'Asignar los dos' }).click();
  await expect(page.getByText(`Jurados asignados a ${CODIGO}.`)).toBeVisible();
});

test('2. jurado (celular): login con cédula, cambio de contraseña y envío de evaluación', async ({ browser }) => {
  const contexto = await browser.newContext({ viewport: { width: 360, height: 740 }, isMobile: true, hasTouch: true });
  const page = await contexto.newPage();
  const j = JURADOS[0];
  await entrar(page, j.email, j.cedula);
  await expect(page).toHaveURL(/\/cambiar-password/);
  await page.getByLabel('Contraseña actual').fill(j.cedula);
  await page.getByLabel('Nueva contraseña', { exact: true }).fill(NUEVA);
  await page.getByLabel('Confirme la nueva contraseña').fill(NUEVA);
  await page.getByRole('button', { name: 'Guardar contraseña' }).click();
  await expect(page).toHaveURL(/\/jurado$/);

  await page.locator('.proyecto', { hasText: CODIGO }).click();
  await expect(page.getByRole('heading', { name: 'Identificación del proyecto' })).toBeVisible();
  await page.locator('.asistencia__fila').first().getByRole('radio', { name: 'Asistió', exact: true }).click();
  const criterios = page.locator('.criterio');
  await expect(criterios).toHaveCount(7);
  for (let i = 0; i < 7; i++) await criterios.nth(i).locator('.opcion').nth(2).click(); // Bueno
  await expect(page.locator('.barra-total__puntaje strong')).toHaveText('67');
  await page.getByLabel('Fortalezas del proyecto').fill('Prueba de humo.');
  await page.getByRole('button', { name: 'Enviar evaluación' }).click();
  await page.locator('mat-dialog-container').getByRole('button', { name: 'Confirmar envío' }).click();
  await expect(page.getByRole('heading', { name: 'Evaluación enviada' })).toBeVisible();
  await expect(page.locator('.exito__total strong')).toHaveText('67.00');
  await contexto.close();
});

test('3. admin: el resultado del proyecto de prueba aparece como Parcial 1/2', async ({ page }) => {
  await entrar(page, ADMIN_EMAIL, ADMIN_PASSWORD);
  await expect(page).toHaveURL(/\/admin\/inicio/);
  await page.goto('/admin/resultados');
  await page.getByRole('tab', { name: /Semillero · INV/ }).click();
  const fila = page.locator('tr.mat-mdc-row', { hasText: CODIGO });
  await expect(fila).toContainText('67.00');
  await expect(fila).toContainText('Pendiente 1/2');
});

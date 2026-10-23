import { HttpErrorResponse } from '@angular/common/http';

import { erroresDeCampos, mensajeDeError } from './notificador';

describe('Mensajes de error', () => {
  it('usa el detalle de la API', () => {
    const e = new HttpErrorResponse({ status: 409, error: { detalle: 'Ya existe.', codigo: 'X', campos: {} } });
    expect(mensajeDeError(e)).toBe('Ya existe.');
  });

  it('sin conexión explica el problema en vez de mostrar un código', () => {
    expect(mensajeDeError(new HttpErrorResponse({ status: 0 }))).toContain('No se pudo conectar con el servidor');
  });

  it('nunca muestra JSON crudo ni HTML', () => {
    const e = new HttpErrorResponse({ status: 502, error: '<html>Bad gateway</html>' });
    expect(mensajeDeError(e)).toBe('Ocurrió un error en el servidor. Intente de nuevo en un momento.');
    expect(mensajeDeError(new Error('x'))).toBe('Ocurrió un error inesperado. Intente de nuevo.');
  });

  it('convierte los errores por campo en texto', () => {
    const e = new HttpErrorResponse({
      status: 400,
      error: { detalle: 'Revise', codigo: 'DATOS_INVALIDOS', campos: { password_nueva: ['Muy corta.', 'Común.'] } },
    });
    expect(erroresDeCampos(e)).toEqual({ password_nueva: 'Muy corta. Común.' });
  });
});

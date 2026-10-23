import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';

import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';
import { sinNotificacion } from './contexto-http';
import { erroresInterceptor } from './errores.interceptor';
import { Notificador } from './notificador';
import { ADMIN, iniciarSesionComo } from './pruebas';

const error = (status: number, codigo = 'X', detalle = 'Mensaje de la API') => ({
  status,
  statusText: 'error',
  body: { detalle, codigo, campos: {} },
});

describe('Interceptores', () => {
  let http: HttpTestingController;
  let cliente: HttpClient;
  let auth: AuthService;
  let notificar: ReturnType<typeof vi.fn>;
  let navegar: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    sessionStorage.clear();
    notificar = vi.fn();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([erroresInterceptor, authInterceptor])),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: Notificador, useValue: { errorHttp: notificar, error: vi.fn(), exito: vi.fn() } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    cliente = TestBed.inject(HttpClient);
    auth = TestBed.inject(AuthService);
    navegar = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    iniciarSesionComo(ADMIN, 'a1', 'r1');
  });

  afterEach(() => http.verify());

  function responder(req: ReturnType<HttpTestingController['expectOne']>, e: ReturnType<typeof error>) {
    req.flush(e.body, { status: e.status, statusText: e.statusText });
  }

  it('agrega Authorization: Bearer a las rutas de la API', () => {
    cliente.get('/api/admin/eventos/').subscribe();
    const req = http.expectOne('/api/admin/eventos/');
    expect(req.request.headers.get('Authorization')).toBe('Bearer a1');
    req.flush([]);
  });

  it('no agrega el token al login ni al refresh', () => {
    cliente.post('/api/auth/login/', {}).subscribe();
    expect(http.expectOne('/api/auth/login/').request.headers.has('Authorization')).toBe(false);
  });

  it('ante un 401 renueva el token una vez y reintenta sin que el usuario lo note', () => {
    let respuesta: unknown;
    cliente.get('/api/admin/eventos/').subscribe((r) => (respuesta = r));
    responder(http.expectOne('/api/admin/eventos/'), error(401, 'TOKEN_INVALIDO'));
    http.expectOne('/api/auth/refresh/').flush({ access: 'a2', refresh: 'r2' });
    const reintento = http.expectOne('/api/admin/eventos/');
    expect(reintento.request.headers.get('Authorization')).toBe('Bearer a2');
    reintento.flush([{ id: 1 }]);
    expect(respuesta).toEqual([{ id: 1 }]);
    expect(notificar).not.toHaveBeenCalled();
    expect(auth.autenticado()).toBe(true);
  });

  it('varias peticiones vencidas a la vez comparten una sola renovación', () => {
    cliente.get('/api/a/').subscribe();
    cliente.get('/api/b/').subscribe();
    responder(http.expectOne('/api/a/'), error(401));
    responder(http.expectOne('/api/b/'), error(401));
    http.expectOne('/api/auth/refresh/').flush({ access: 'a2', refresh: 'r2' });
    http.expectOne('/api/a/').flush({});
    http.expectOne('/api/b/').flush({});
  });

  it('si la renovación falla cierra la sesión y muestra un solo mensaje', () => {
    let fallo = false;
    cliente.get('/api/admin/eventos/').subscribe({ error: () => (fallo = true) });
    responder(http.expectOne('/api/admin/eventos/'), error(401, 'TOKEN_INVALIDO'));
    responder(http.expectOne('/api/auth/refresh/'), error(401, 'TOKEN_INVALIDO'));
    expect(fallo).toBe(true);
    expect(auth.autenticado()).toBe(false);
    expect(auth.accessToken()).toBeNull();
    expect(navegar).toHaveBeenCalledWith('/login');
    expect(notificar).toHaveBeenCalledTimes(1);
  });

  it('no reintenta dos veces: si el reintento también da 401, cierra la sesión', () => {
    cliente.get('/api/x/').subscribe({ error: () => undefined });
    responder(http.expectOne('/api/x/'), error(401));
    http.expectOne('/api/auth/refresh/').flush({ access: 'a2', refresh: 'r2' });
    responder(http.expectOne('/api/x/'), error(401));
    http.expectNone('/api/auth/refresh/');
    expect(auth.autenticado()).toBe(false);
  });

  it('un error de negocio después del reintento no cierra la sesión', () => {
    cliente.post('/api/x/', {}).subscribe({ error: () => undefined });
    responder(http.expectOne('/api/x/'), error(401));
    http.expectOne('/api/auth/refresh/').flush({ access: 'a2', refresh: 'r2' });
    responder(http.expectOne('/api/x/'), error(409, 'DOCENTE_SIN_CUPO'));
    expect(auth.autenticado()).toBe(true);
    expect(notificar).toHaveBeenCalledTimes(1);
  });

  it('403 CAMBIO_PASSWORD_REQUERIDO lleva a /cambiar-password sin snackbar', () => {
    cliente.get('/api/jurado/asignaciones/').subscribe({ error: () => undefined });
    responder(http.expectOne('/api/jurado/asignaciones/'), error(403, 'CAMBIO_PASSWORD_REQUERIDO'));
    expect(navegar).toHaveBeenCalledWith('/cambiar-password');
    expect(auth.rutaInicio()).toBe('/cambiar-password');
    expect(notificar).not.toHaveBeenCalled();
  });

  it('los errores de negocio se notifican con el mensaje de la API', () => {
    cliente.post('/api/x/', {}).subscribe({ error: () => undefined });
    responder(http.expectOne('/api/x/'), error(409, 'DOCENTE_SIN_CUPO', 'Ana ya tiene 3 proyectos.'));
    expect(notificar).toHaveBeenCalledTimes(1);
    expect(notificar.mock.calls[0][0].error.detalle).toBe('Ana ya tiene 3 proyectos.');
    expect(auth.autenticado()).toBe(true);
  });

  it('una petición con SIN_NOTIFICACION maneja su error sin snackbar', () => {
    cliente.get('/api/x/', { context: sinNotificacion() }).subscribe({ error: () => undefined });
    responder(http.expectOne('/api/x/'), error(409));
    expect(notificar).not.toHaveBeenCalled();
  });
});

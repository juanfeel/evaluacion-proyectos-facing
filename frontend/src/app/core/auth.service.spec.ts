import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';

import { AuthService } from './auth.service';
import { ADMIN, iniciarSesionComo, JURADO, JURADO_NUEVO } from './pruebas';

describe('AuthService', () => {
  let auth: AuthService;
  let http: HttpTestingController;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])] });
    auth = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('login guarda los tokens en sessionStorage y el usuario en el signal', () => {
    iniciarSesionComo(ADMIN, 'a1', 'r1');
    expect(auth.accessToken()).toBe('a1');
    expect(auth.refreshToken()).toBe('r1');
    expect(sessionStorage.getItem('evaluacion.access')).toBe('a1');
    expect(auth.usuario()).toEqual(ADMIN);
    expect(auth.autenticado()).toBe(true);
  });

  it('envía correo y contraseña al login', () => {
    auth.login('ana@udenar.edu.co', 'secreta').subscribe();
    const req = http.expectOne('/api/auth/login/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ email: 'ana@udenar.edu.co', password: 'secreta' });
    req.flush({ access: 'a', refresh: 'r', usuario: JURADO });
  });

  it('ruta de inicio según el rol y el cambio de contraseña pendiente', () => {
    expect(auth.rutaInicio()).toBe('/login');
    iniciarSesionComo(ADMIN);
    expect(auth.rutaInicio()).toBe('/admin');
    iniciarSesionComo(JURADO);
    expect(auth.rutaInicio()).toBe('/jurado');
    iniciarSesionComo(JURADO_NUEVO);
    expect(auth.rutaInicio()).toBe('/cambiar-password');
  });

  it('cerrar sesión borra los tokens y vuelve al login', () => {
    const navegar = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    iniciarSesionComo(ADMIN);
    auth.cerrarSesion();
    expect(auth.accessToken()).toBeNull();
    expect(auth.refreshToken()).toBeNull();
    expect(auth.usuario()).toBeNull();
    expect(navegar).toHaveBeenCalledWith('/login');
  });

  it('refrescar comparte una sola petición entre llamadas simultáneas y rota los tokens', () => {
    iniciarSesionComo(ADMIN, 'a1', 'r1');
    const recibidos: string[] = [];
    auth.refrescar().subscribe((t) => recibidos.push(t));
    auth.refrescar().subscribe((t) => recibidos.push(t));
    const req = http.expectOne('/api/auth/refresh/');
    expect(req.request.body).toEqual({ refresh: 'r1' });
    req.flush({ access: 'a2', refresh: 'r2' });
    expect(recibidos).toEqual(['a2', 'a2']);
    expect(auth.accessToken()).toBe('a2');
    expect(auth.refreshToken()).toBe('r2');
  });

  it('asegurarUsuario sin sesión responde false sin llamar a la API', () => {
    let resultado: boolean | undefined;
    auth.asegurarUsuario().subscribe((r) => (resultado = r));
    expect(resultado).toBe(false);
    http.expectNone('/api/auth/me/');
  });

  it('asegurarUsuario con tokens guardados recarga el usuario con /me', () => {
    sessionStorage.setItem('evaluacion.access', 'a1');
    sessionStorage.setItem('evaluacion.refresh', 'r1');
    let resultado: boolean | undefined;
    auth.asegurarUsuario().subscribe((r) => (resultado = r));
    auth.asegurarUsuario().subscribe(); // comparte la misma petición
    http.expectOne('/api/auth/me/').flush(JURADO);
    expect(resultado).toBe(true);
    expect(auth.usuario()).toEqual(JURADO);
  });

  it('asegurarUsuario limpia la sesión si /me falla', () => {
    sessionStorage.setItem('evaluacion.access', 'a1');
    let resultado: boolean | undefined;
    auth.asegurarUsuario().subscribe((r) => (resultado = r));
    http.expectOne('/api/auth/me/').flush({ detalle: 'x', codigo: 'TOKEN_INVALIDO', campos: {} }, { status: 401, statusText: 'x' });
    expect(resultado).toBe(false);
    expect(auth.accessToken()).toBeNull();
  });

  it('cambiar la contraseña actualiza el usuario', () => {
    iniciarSesionComo(JURADO_NUEVO);
    auth.cambiarPassword('1085', 'Nueva-Clave-2026', 'Nueva-Clave-2026').subscribe();
    const req = http.expectOne('/api/auth/cambiar-password/');
    expect(req.request.body).toEqual({
      password_actual: '1085', password_nueva: 'Nueva-Clave-2026', confirmacion: 'Nueva-Clave-2026',
    });
    req.flush({ ...JURADO_NUEVO, debe_cambiar_password: false });
    expect(auth.usuario()?.debe_cambiar_password).toBe(false);
    expect(auth.rutaInicio()).toBe('/jurado');
  });

  it('marcarCambioRequerido activa el cambio obligatorio', () => {
    iniciarSesionComo(JURADO);
    auth.marcarCambioRequerido();
    expect(auth.rutaInicio()).toBe('/cambiar-password');
  });
});

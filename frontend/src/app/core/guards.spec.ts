import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, provideRouter, Router, RouterStateSnapshot, UrlTree } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { firstValueFrom, isObservable, Observable, of } from 'rxjs';

import { routes } from '../app.routes';
import { authGuard, cambioPasswordGuard, invitadoGuard, rolGuard } from './guards';
import { ADMIN, iniciarSesionComo, JURADO, JURADO_NUEVO } from './pruebas';

type Resultado = boolean | UrlTree;

describe('Guards', () => {
  let router: Router;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter(routes)] });
    router = TestBed.inject(Router);
  });

  async function ejecutar(guard: (r: ActivatedRouteSnapshot, s: RouterStateSnapshot) => unknown, url = '/admin') {
    const salida = TestBed.runInInjectionContext(() =>
      guard({} as ActivatedRouteSnapshot, { url } as RouterStateSnapshot),
    ) as Resultado | Observable<Resultado>;
    const valor = await firstValueFrom(isObservable(salida) ? salida : of(salida));
    return valor instanceof UrlTree ? router.serializeUrl(valor) : valor;
  }

  it('authGuard sin sesión lleva al login recordando la ruta', async () => {
    expect(await ejecutar(authGuard, '/admin/docentes')).toBe('/login?volver=%2Fadmin%2Fdocentes');
  });

  it('authGuard con sesión deja pasar', async () => {
    iniciarSesionComo(ADMIN);
    expect(await ejecutar(authGuard)).toBe(true);
  });

  it('cambioPasswordGuard obliga a cambiar la contraseña', async () => {
    iniciarSesionComo(JURADO_NUEVO);
    expect(await ejecutar(cambioPasswordGuard)).toBe('/cambiar-password');
  });

  it('cambioPasswordGuard deja pasar si ya la cambió', async () => {
    iniciarSesionComo(JURADO);
    expect(await ejecutar(cambioPasswordGuard)).toBe(true);
  });

  it('rolGuard devuelve al jurado a su inicio si intenta entrar a /admin', async () => {
    iniciarSesionComo(JURADO);
    expect(await ejecutar(rolGuard('ADMIN'))).toBe('/jurado');
    expect(await ejecutar(rolGuard('JURADO'))).toBe(true);
  });

  it('rolGuard devuelve al admin a /admin si intenta entrar a /jurado', async () => {
    iniciarSesionComo(ADMIN);
    expect(await ejecutar(rolGuard('JURADO'))).toBe('/admin');
  });

  it('invitadoGuard: con sesión, /login lleva al inicio del rol', async () => {
    expect(await ejecutar(invitadoGuard)).toBe(true);
    iniciarSesionComo(ADMIN);
    expect(await ejecutar(invitadoGuard)).toBe('/admin');
  });

  describe('navegación completa', () => {
    it('un jurado que escribe /admin termina en /jurado', async () => {
      iniciarSesionComo(JURADO);
      const harness = await RouterTestingHarness.create();
      await harness.navigateByUrl('/admin/docentes');
      expect(router.url).toBe('/jurado');
    });

    it('un docente nuevo es llevado a /cambiar-password', async () => {
      iniciarSesionComo(JURADO_NUEVO);
      const harness = await RouterTestingHarness.create();
      await harness.navigateByUrl('/jurado');
      expect(router.url).toBe('/cambiar-password');
    });

    it('el admin llega a /admin/inicio desde la raíz', async () => {
      iniciarSesionComo(ADMIN);
      const harness = await RouterTestingHarness.create();
      await harness.navigateByUrl('/');
      expect(router.url).toBe('/admin/inicio');
    });

    it('/salir borra la sesión y lleva al login', async () => {
      iniciarSesionComo(ADMIN);
      const harness = await RouterTestingHarness.create();
      await harness.navigateByUrl('/salir');
      expect(router.url).toBe('/login');
      expect(sessionStorage.getItem('evaluacion.access')).toBeNull();
    });

    it('sin sesión, cualquier ruta protegida lleva al login', async () => {
      const harness = await RouterTestingHarness.create();
      await harness.navigateByUrl('/jurado');
      expect(router.url).toBe('/login?volver=%2Fjurado');
      TestBed.inject(HttpTestingController).verify();
    });
  });
});

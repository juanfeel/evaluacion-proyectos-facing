import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, Observable, switchMap, throwError } from 'rxjs';

import { AuthService } from './auth.service';
import { REINTENTADA } from './contexto-http';

const RUTAS_PUBLICAS = ['/api/auth/login/', '/api/auth/refresh/', '/api/health/'];

/**
 * Agrega `Authorization: Bearer`, renueva el token una vez ante un 401 y reintenta la petición.
 * Si la renovación falla (o el reintento vuelve a dar 401), cierra la sesión.
 * Ante CAMBIO_PASSWORD_REQUERIDO lleva a /cambiar-password.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  if (!req.url.startsWith('/api/') || RUTAS_PUBLICAS.some((r) => req.url.startsWith(r))) {
    return next(req);
  }
  const auth = inject(AuthService);
  const router = inject(Router);

  const manejar = (error: unknown): Observable<never> => {
    if (error instanceof HttpErrorResponse) {
      if (error.status === 401) {
        auth.cerrarSesion();
      } else if (error.status === 403 && error.error?.codigo === 'CAMBIO_PASSWORD_REQUERIDO') {
        auth.marcarCambioRequerido();
        void router.navigateByUrl('/cambiar-password');
      }
    }
    return throwError(() => error);
  };

  return next(conToken(req, auth.accessToken())).pipe(
    catchError((error: unknown) => {
      const renovar =
        error instanceof HttpErrorResponse && error.status === 401 && !req.context.get(REINTENTADA) && auth.refreshToken();
      if (!renovar) {
        return manejar(error);
      }
      return auth.refrescar().pipe(
        catchError(() => manejar(error)),
        switchMap((access) =>
          next(conToken(req.clone({ context: req.context.set(REINTENTADA, true) }), access)).pipe(catchError(manejar)),
        ),
      );
    }),
  );
};

function conToken(req: HttpRequest<unknown>, token: string | null): HttpRequest<unknown> {
  return token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;
}

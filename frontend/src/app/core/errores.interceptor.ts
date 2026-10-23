import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { SIN_NOTIFICACION } from './contexto-http';
import { Notificador } from './notificador';

/**
 * Muestra en un snackbar el mensaje de error de la API (`detalle`), salvo que la petición
 * pida manejarlo por su cuenta. No muestra el 403 de cambio de contraseña (hay redirección).
 * Va ANTES de authInterceptor: solo ve el error final, después de un posible reintento.
 */
export const erroresInterceptor: HttpInterceptorFn = (req, next) => {
  const notificador = inject(Notificador);
  return next(req).pipe(
    catchError((error: unknown) => {
      const silenciar =
        req.context.get(SIN_NOTIFICACION) ||
        (error instanceof HttpErrorResponse &&
          error.status === 403 &&
          error.error?.codigo === 'CAMBIO_PASSWORD_REQUERIDO');
      if (!silenciar) {
        notificador.errorHttp(error);
      }
      return throwError(() => error);
    }),
  );
};

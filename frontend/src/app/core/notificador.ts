import { HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ErrorApi } from './modelos';

/** Mensajes al usuario en snackbar. Nunca muestra JSON crudo. */
@Injectable({ providedIn: 'root' })
export class Notificador {
  private readonly snack = inject(MatSnackBar);

  exito(mensaje: string): void {
    this.snack.open(mensaje, 'Cerrar', { panelClass: 'snack-exito', duration: 4000 });
  }

  error(mensaje: string): void {
    this.snack.open(mensaje, 'Cerrar', { panelClass: 'snack-error', duration: 7000 });
  }

  errorHttp(error: unknown): void {
    this.error(mensajeDeError(error));
  }
}

export function mensajeDeError(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (error.status === 0) {
      return 'No se pudo conectar con el servidor. Revise su conexión e intente de nuevo.';
    }
    const cuerpo = error.error as Partial<ErrorApi> | null;
    if (cuerpo && typeof cuerpo.detalle === 'string' && cuerpo.detalle) {
      return cuerpo.detalle;
    }
    if (error.status >= 500) {
      return 'Ocurrió un error en el servidor. Intente de nuevo en un momento.';
    }
  }
  return 'Ocurrió un error inesperado. Intente de nuevo.';
}

/** Errores por campo de la API ({campos: {email: ["…"]}}) como texto por campo. */
export function erroresDeCampos(error: unknown): Record<string, string> {
  const campos = error instanceof HttpErrorResponse ? (error.error as Partial<ErrorApi> | null)?.campos : null;
  const resultado: Record<string, string> = {};
  for (const [campo, mensajes] of Object.entries(campos ?? {})) {
    if (Array.isArray(mensajes) && mensajes.length) {
      resultado[campo] = mensajes.filter((m) => typeof m === 'string').join(' ');
    }
  }
  return resultado;
}

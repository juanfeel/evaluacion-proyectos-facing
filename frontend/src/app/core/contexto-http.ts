import { HttpContext, HttpContextToken } from '@angular/common/http';

/** La petición maneja sus errores por su cuenta: no se muestra snackbar automático. */
export const SIN_NOTIFICACION = new HttpContextToken<boolean>(() => false);

/** Marca interna: la petición ya se reintentó tras renovar el token. */
export const REINTENTADA = new HttpContextToken<boolean>(() => false);

export const sinNotificacion = () => new HttpContext().set(SIN_NOTIFICACION, true);

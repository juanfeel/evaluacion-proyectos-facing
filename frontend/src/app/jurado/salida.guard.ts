import { CanDeactivateFn } from '@angular/router';
import { Observable } from 'rxjs';

export interface ConSalidaControlada {
  puedeSalir(): Observable<boolean> | boolean;
}

/** Pide confirmación antes de abandonar un formulario a medio llenar. */
export const salidaGuard: CanDeactivateFn<ConSalidaControlada> = (componente) => componente.puedeSalir();

import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';

import { AuthService, rutaDeRol } from './auth.service';
import { Rol } from './modelos';

/** Exige una sesión; si no la hay, lleva a /login recordando a dónde iba. */
export const authGuard: CanActivateFn = (_ruta, estado) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth
    .asegurarUsuario()
    .pipe(map((ok) => ok || router.createUrlTree(['/login'], { queryParams: { volver: estado.url } })));
};

/** RN-07: con el cambio de contraseña pendiente solo se permite /cambiar-password. */
export const cambioPasswordGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth
    .asegurarUsuario()
    .pipe(map((ok) => !ok || !auth.usuario()?.debe_cambiar_password || router.createUrlTree(['/cambiar-password'])));
};

/** Solo el rol indicado; cualquier otro vuelve a su propio inicio. */
export const rolGuard =
  (rol: Rol): CanActivateFn =>
  () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    return auth.asegurarUsuario().pipe(
      map((ok) => {
        const usuario = auth.usuario();
        if (!ok || !usuario) return router.createUrlTree(['/login']);
        return usuario.rol === rol || router.createUrlTree([rutaDeRol(usuario.rol)]);
      }),
    );
  };

/** /login: si ya hay sesión, va directo a su inicio. */
export const invitadoGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.asegurarUsuario().pipe(map((ok) => !ok || router.createUrlTree([auth.rutaInicio()])));
};

/** Raíz de la aplicación: decide a dónde ir según la sesión. */
export const inicioGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.asegurarUsuario().pipe(map(() => router.createUrlTree([auth.rutaInicio()])));
};

/** /salir: se activa solo si la pantalla anterior permitió salir; entonces borra la sesión. */
export const salirGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  auth.limpiarSesion();
  return inject(Router).createUrlTree(['/login']);
};

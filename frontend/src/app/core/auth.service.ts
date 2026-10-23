import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, finalize, map, Observable, of, shareReplay, tap, throwError } from 'rxjs';

import { sinNotificacion } from './contexto-http';
import { RespuestaLogin, RespuestaRefresh, Rol, Usuario } from './modelos';

const CLAVE_ACCESS = 'evaluacion.access';
const CLAVE_REFRESH = 'evaluacion.refresh';

/**
 * Sesión del usuario. Los tokens viven en sessionStorage (se borran al cerrar la pestaña).
 * El usuario se mantiene en un signal y se recarga con /me al abrir la aplicación.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  private readonly _usuario = signal<Usuario | null>(null);
  readonly usuario = this._usuario.asReadonly();
  readonly autenticado = computed(() => this._usuario() !== null);

  private refresco$: Observable<string> | null = null;
  private carga$: Observable<boolean> | null = null;

  accessToken(): string | null {
    return leer(CLAVE_ACCESS);
  }

  refreshToken(): string | null {
    return leer(CLAVE_REFRESH);
  }

  login(email: string, password: string): Observable<Usuario> {
    return this.http.post<RespuestaLogin>('/api/auth/login/', { email, password }).pipe(
      tap((r) => {
        this.guardarTokens(r.access, r.refresh);
        this._usuario.set(r.usuario);
      }),
      map((r) => r.usuario),
    );
  }

  /** Renueva el access token. Varias peticiones que vencen a la vez comparten una sola renovación. */
  refrescar(): Observable<string> {
    const refresh = this.refreshToken();
    if (!refresh) {
      return throwError(() => new Error('Sin refresh token'));
    }
    if (!this.refresco$) {
      this.refresco$ = this.http
        .post<RespuestaRefresh>('/api/auth/refresh/', { refresh }, { context: sinNotificacion() })
        .pipe(
          tap((r) => this.guardarTokens(r.access, r.refresh)),
          map((r) => r.access),
          finalize(() => (this.refresco$ = null)),
          shareReplay(1),
        );
    }
    return this.refresco$;
  }

  /** Garantiza que el usuario esté cargado si hay una sesión guardada. */
  asegurarUsuario(): Observable<boolean> {
    if (this._usuario()) {
      return of(true);
    }
    if (!this.accessToken() && !this.refreshToken()) {
      return of(false);
    }
    if (!this.carga$) {
      this.carga$ = this.http.get<Usuario>('/api/auth/me/', { context: sinNotificacion() }).pipe(
        tap((u) => this._usuario.set(u)),
        map(() => true),
        catchError(() => {
          this.limpiar();
          return of(false);
        }),
        finalize(() => (this.carga$ = null)),
        shareReplay(1),
      );
    }
    return this.carga$;
  }

  cambiarPassword(passwordActual: string, passwordNueva: string, confirmacion: string): Observable<Usuario> {
    return this.http
      .post<Usuario>('/api/auth/cambiar-password/', {
        password_actual: passwordActual,
        password_nueva: passwordNueva,
        confirmacion,
      })
      .pipe(tap((u) => this._usuario.set(u)));
  }

  /** La API respondió CAMBIO_PASSWORD_REQUERIDO (p. ej., el admin restableció la contraseña). */
  marcarCambioRequerido(): void {
    const u = this._usuario();
    if (u && !u.debe_cambiar_password) {
      this._usuario.set({ ...u, debe_cambiar_password: true });
    }
  }

  /**
   * Salida pedida por el usuario: pasa por la navegación, así una pantalla con cambios sin guardar
   * (p. ej. una evaluación a medio llenar) puede pedir confirmación ANTES de borrar la sesión.
   */
  salir(): void {
    void this.router.navigateByUrl('/salir');
  }

  /** Cierre forzado (sesión vencida o inválida): borra la sesión de inmediato. */
  cerrarSesion(): void {
    this.limpiar();
    void this.router.navigateByUrl('/login');
  }

  /** Lo usa la ruta /salir una vez que la navegación fue confirmada. */
  limpiarSesion(): void {
    this.limpiar();
  }

  /** Ruta de inicio según el estado de la sesión. */
  rutaInicio(): string {
    const u = this._usuario();
    if (!u) return '/login';
    if (u.debe_cambiar_password) return '/cambiar-password';
    return rutaDeRol(u.rol);
  }

  private guardarTokens(access: string, refresh: string): void {
    escribir(CLAVE_ACCESS, access);
    escribir(CLAVE_REFRESH, refresh);
  }

  private limpiar(): void {
    borrar(CLAVE_ACCESS);
    borrar(CLAVE_REFRESH);
    this._usuario.set(null);
  }
}

export function rutaDeRol(rol: Rol): string {
  return rol === 'ADMIN' ? '/admin' : '/jurado';
}

function leer(clave: string): string | null {
  try {
    return sessionStorage.getItem(clave);
  } catch {
    return null;
  }
}

function escribir(clave: string, valor: string): void {
  try {
    sessionStorage.setItem(clave, valor);
  } catch {
    /* almacenamiento no disponible: la sesión dura solo en memoria de la petición */
  }
}

function borrar(clave: string): void {
  try {
    sessionStorage.removeItem(clave);
  } catch {
    /* sin almacenamiento */
  }
}

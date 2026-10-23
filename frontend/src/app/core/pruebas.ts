import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthService } from './auth.service';
import { Usuario } from './modelos';

export const ADMIN: Usuario = {
  id: 1, email: 'admin@udenar.edu.co', nombre_completo: 'Coordinación', departamento: '', rol: 'ADMIN',
  debe_cambiar_password: false,
};
export const JURADO: Usuario = { ...ADMIN, id: 2, email: 'j@udenar.edu.co', nombre_completo: 'Jurado', rol: 'JURADO' };
export const JURADO_NUEVO: Usuario = { ...JURADO, debe_cambiar_password: true };

/** Inicia sesión respondiendo la petición de login con el usuario dado. */
export function iniciarSesionComo(usuario: Usuario, access = 'access-1', refresh = 'refresh-1'): void {
  const auth = TestBed.inject(AuthService);
  const http = TestBed.inject(HttpTestingController);
  auth.login(usuario.email, 'x').subscribe();
  http.expectOne('/api/auth/login/').flush({ access, refresh, usuario });
}

export type Rol = 'ADMIN' | 'JURADO';

export interface Usuario {
  id: number;
  email: string;
  nombre_completo: string;
  departamento: string;
  rol: Rol;
  debe_cambiar_password: boolean;
}

export interface RespuestaLogin {
  access: string;
  refresh: string;
  usuario: Usuario;
}

export interface RespuestaRefresh {
  access: string;
  refresh: string;
}

/** Forma de todos los errores de la API: {detalle, codigo, campos}. */
export interface ErrorApi {
  detalle: string;
  codigo: string;
  campos: Record<string, unknown>;
}

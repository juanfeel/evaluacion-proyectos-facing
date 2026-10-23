import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import {
  Docente, DocenteEntrada, EvaluacionCompleta, Evento, FiltrosProyectos, GrupoAreas, Proyecto, ProyectoEntrada,
  Resultados, Resumen,
} from './modelos';

/** Endpoints de administración (CLAUDE.md, sección 7). Los errores los muestra el interceptor. */
@Injectable({ providedIn: 'root' })
export class AdminApi {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/admin';

  // Eventos
  eventos(): Observable<Evento[]> {
    return this.http.get<Evento[]>(`${this.base}/eventos/`);
  }
  crearEvento(datos: { nombre: string; fecha: string; activo: boolean }): Observable<Evento> {
    return this.http.post<Evento>(`${this.base}/eventos/`, datos);
  }
  editarEvento(id: number, datos: { nombre: string; fecha: string }): Observable<Evento> {
    return this.http.patch<Evento>(`${this.base}/eventos/${id}/`, datos);
  }
  eliminarEvento(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/eventos/${id}/`);
  }
  activarEvento(id: number): Observable<Evento> {
    return this.http.post<Evento>(`${this.base}/eventos/${id}/activar/`, {});
  }

  // Áreas
  areas(): Observable<GrupoAreas[]> {
    return this.http.get<GrupoAreas[]>(`${this.base}/areas/`);
  }

  // Docentes
  docentes(): Observable<Docente[]> {
    return this.http.get<Docente[]>(`${this.base}/docentes/`);
  }
  crearDocente(datos: DocenteEntrada): Observable<Docente> {
    return this.http.post<Docente>(`${this.base}/docentes/`, datos);
  }
  editarDocente(id: number, datos: Partial<DocenteEntrada>): Observable<Docente> {
    return this.http.patch<Docente>(`${this.base}/docentes/${id}/`, datos);
  }
  eliminarDocente(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/docentes/${id}/`);
  }
  restablecerPassword(id: number): Observable<{ detalle: string }> {
    return this.http.post<{ detalle: string }>(`${this.base}/docentes/${id}/restablecer-password/`, {});
  }

  // Proyectos
  proyectos(filtros: FiltrosProyectos = {}): Observable<Proyecto[]> {
    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor !== '' && valor !== null && valor !== undefined) params = params.set(clave, String(valor));
    }
    return this.http.get<Proyecto[]>(`${this.base}/proyectos/`, { params });
  }
  proyecto(id: number): Observable<Proyecto> {
    return this.http.get<Proyecto>(`${this.base}/proyectos/${id}/`);
  }
  crearProyecto(datos: ProyectoEntrada): Observable<Proyecto> {
    return this.http.post<Proyecto>(`${this.base}/proyectos/`, datos);
  }
  editarProyecto(id: number, datos: Partial<ProyectoEntrada>): Observable<Proyecto> {
    return this.http.patch<Proyecto>(`${this.base}/proyectos/${id}/`, datos);
  }
  eliminarProyecto(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/proyectos/${id}/`);
  }

  // Jurados (siempre en pareja)
  asignarJurados(proyectoId: number, docentes: [number, number]): Observable<unknown> {
    return this.http.post(`${this.base}/proyectos/${proyectoId}/jurados/`, { docentes });
  }
  quitarJurados(proyectoId: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/proyectos/${proyectoId}/jurados/`);
  }
  reemplazarJurado(asignacionId: number, docente: number): Observable<unknown> {
    return this.http.patch(`${this.base}/asignaciones/${asignacionId}/`, { docente });
  }

  // Resultados
  resumen(evento?: number | null): Observable<Resumen> {
    return this.http.get<Resumen>(`${this.base}/resumen/`, { params: conEvento(evento) });
  }
  resultados(evento?: number | null): Observable<Resultados> {
    return this.http.get<Resultados>(`${this.base}/resultados/`, { params: conEvento(evento) });
  }
  evaluacionesDeProyecto(id: number): Observable<{ proyecto: Proyecto; evaluaciones: EvaluacionCompleta[] }> {
    return this.http.get<{ proyecto: Proyecto; evaluaciones: EvaluacionCompleta[] }>(
      `${this.base}/proyectos/${id}/evaluaciones/`,
    );
  }
}

function conEvento(evento?: number | null): HttpParams {
  return evento ? new HttpParams().set('evento', evento) : new HttpParams();
}

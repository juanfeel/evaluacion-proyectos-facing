import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { sinNotificacion } from '../core/contexto-http';
import { AsignacionJurado, EnvioEvaluacion, EvaluacionPropia, Formulario } from './modelos';

@Injectable({ providedIn: 'root' })
export class JuradoApi {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/jurado/asignaciones';

  misAsignaciones(): Observable<AsignacionJurado[]> {
    return this.http.get<AsignacionJurado[]>(`${this.base}/`);
  }

  formulario(id: number): Observable<Formulario> {
    return this.http.get<Formulario>(`${this.base}/${id}/formulario/`);
  }

  /** El componente maneja los errores (409 = ya enviada) por su cuenta. */
  enviar(id: number, envio: EnvioEvaluacion): Observable<EvaluacionPropia> {
    return this.http.post<EvaluacionPropia>(`${this.base}/${id}/evaluacion/`, envio, { context: sinNotificacion() });
  }

  evaluacion(id: number): Observable<EvaluacionPropia> {
    return this.http.get<EvaluacionPropia>(`${this.base}/${id}/evaluacion/`);
  }
}

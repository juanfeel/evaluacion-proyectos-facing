import { computed, inject, Injectable, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { AdminApi } from './admin-api';
import { Evento } from './modelos';

const CLAVE = 'evaluacion.admin.evento';

/**
 * Evento que el admin está consultando (Inicio, Proyectos, Resultados). Por defecto, el activo.
 * Se recuerda en el navegador solo como comodidad; si falla el almacenamiento, se usa el activo.
 */
@Injectable({ providedIn: 'root' })
export class EventoSeleccionado {
  private readonly api = inject(AdminApi);

  readonly eventos = signal<Evento[]>([]);
  readonly cargados = signal(false);
  private readonly elegido = signal<number | null>(leerGuardado());

  readonly activo = computed(() => this.eventos().find((e) => e.activo) ?? null);
  readonly evento = computed(() => {
    const lista = this.eventos();
    return lista.find((e) => e.id === this.elegido()) ?? this.activo() ?? lista[0] ?? null;
  });
  readonly id = computed(() => this.evento()?.id ?? null);

  cargar(): Observable<Evento[]> {
    return this.api.eventos().pipe(
      tap((lista) => {
        this.eventos.set(lista);
        this.cargados.set(true);
      }),
    );
  }

  elegir(id: number): void {
    this.elegido.set(id);
    try {
      localStorage.setItem(CLAVE, String(id));
    } catch {
      /* sin almacenamiento: no pasa nada */
    }
  }
}

function leerGuardado(): number | null {
  try {
    const valor = Number(localStorage.getItem(CLAVE));
    return Number.isInteger(valor) && valor > 0 ? valor : null;
  } catch {
    return null;
  }
}

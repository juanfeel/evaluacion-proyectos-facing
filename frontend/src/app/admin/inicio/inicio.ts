import { DecimalPipe } from '@angular/common';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { filter, switchMap, tap } from 'rxjs';

import { SelectorEvento } from '../../shared/selector-evento/selector-evento';
import { AdminApi } from '../admin-api';
import { EventoSeleccionado } from '../evento-seleccionado';

@Component({
  selector: 'app-inicio',
  imports: [DecimalPipe, MatButtonModule, MatIconModule, MatProgressBarModule, RouterLink, SelectorEvento],
  templateUrl: './inicio.html',
  styleUrl: './inicio.scss',
})
export class Inicio implements OnInit {
  private readonly api = inject(AdminApi);
  protected readonly sel = inject(EventoSeleccionado);
  protected readonly cargando = signal(true);

  protected readonly resumen = toSignal(
    toObservable(this.sel.id).pipe(
      filter((id): id is number => id !== null),
      tap(() => this.cargando.set(true)),
      switchMap((id) => this.api.resumen(id)),
      tap(() => this.cargando.set(false)),
    ),
  );

  protected readonly faltan = computed(() => {
    const r = this.resumen();
    return r ? r.total_proyectos - r.evaluados : 0;
  });
  protected readonly porcentaje = computed(() => {
    const r = this.resumen();
    return r && r.evaluaciones_total ? (100 * r.evaluaciones_enviadas) / r.evaluaciones_total : 0;
  });
  protected readonly tarjetas = computed(() => {
    const r = this.resumen();
    if (!r) return [];
    return [
      { estado: 'SIN_JURADOS', texto: 'Sin jurados', valor: r.sin_jurados, icono: 'person_off', clase: 'sin-jurados', ayuda: 'Asigne los dos jurados' },
      { estado: 'PENDIENTE', texto: 'Pendientes', valor: r.pendientes, icono: 'schedule', clase: 'pendiente', ayuda: 'Ningún jurado ha evaluado' },
      { estado: 'PARCIAL', texto: 'Parciales', valor: r.parciales, icono: 'timelapse', clase: 'parcial', ayuda: 'Falta un jurado' },
      { estado: 'EVALUADO', texto: 'Evaluados', valor: r.evaluados, icono: 'check_circle', clase: 'evaluado', ayuda: 'Con las dos evaluaciones' },
    ];
  });

  ngOnInit(): void {
    this.sel.cargar().subscribe({
      next: (lista) => this.cargando.set(lista.length > 0),
      error: () => this.cargando.set(false),
    });
  }
}

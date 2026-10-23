import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { filter, Subject, switchMap, tap, merge, map } from 'rxjs';

import { Notificador } from '../../core/notificador';
import { confirmar } from '../../shared/confirmar/confirmar';
import { EstadoChip } from '../../shared/estado-chip/estado-chip';
import { SelectorEvento } from '../../shared/selector-evento/selector-evento';
import { AdminApi } from '../admin-api';
import { EventoSeleccionado } from '../evento-seleccionado';
import { ESTADOS_EVALUACION, ORIGENES, Proyecto } from '../modelos';

/** "FALTAN" = todo lo que no está EVALUADO (filtro solo del frontend). */
type FiltroEstado = Proyecto['estado_evaluacion'] | 'FALTAN' | '';

function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

@Component({
  selector: 'app-proyectos',
  imports: [
    EstadoChip, MatButtonModule, MatFormFieldModule, MatIconModule, MatInputModule, MatProgressBarModule,
    MatSelectModule, MatTableModule, MatTooltipModule, RouterLink, SelectorEvento,
  ],
  templateUrl: './proyectos.html',
})
export class Proyectos implements OnInit {
  private readonly api = inject(AdminApi);
  private readonly dialog = inject(MatDialog);
  private readonly notificador = inject(Notificador);
  protected readonly sel = inject(EventoSeleccionado);
  private readonly recarga$ = new Subject<void>();

  protected readonly origenes = ORIGENES;
  protected readonly estadosEvaluacion = ESTADOS_EVALUACION;
  protected readonly origen = signal<'' | Proyecto['origen']>('');
  protected readonly tipo = signal<'' | Proyecto['tipo']>('');
  protected readonly estado = signal<FiltroEstado>(
    (inject(ActivatedRoute).snapshot.queryParamMap.get('estado_evaluacion') as FiltroEstado) ?? '',
  );
  protected readonly busqueda = signal('');
  protected readonly cargando = signal(true);

  private readonly todos = toSignal(
    merge(toObservable(this.sel.id), this.recarga$.pipe(map(() => this.sel.id()))).pipe(
      filter((id): id is number => id !== null),
      tap(() => this.cargando.set(true)),
      switchMap((id) => this.api.proyectos({ evento: id })),
      tap(() => this.cargando.set(false)),
    ),
    { initialValue: [] as Proyecto[] },
  );

  protected readonly proyectos = computed(() => {
    const q = normalizar(this.busqueda().trim());
    return this.todos().filter(
      (p) =>
        (!this.origen() || p.origen === this.origen()) &&
        (!this.tipo() || p.tipo === this.tipo()) &&
        (!this.estado() ||
          (this.estado() === 'FALTAN' ? p.estado_evaluacion !== 'EVALUADO' : p.estado_evaluacion === this.estado())) &&
        (!q || normalizar(`${p.codigo} ${p.titulo}`).includes(q)),
    );
  });
  protected readonly hayFiltros = computed(() => !!(this.origen() || this.tipo() || this.estado() || this.busqueda()));
  protected readonly columnas = ['codigo', 'titulo', 'origen', 'tipo', 'estado', 'jurados', 'evaluacion', 'acciones'];

  ngOnInit(): void {
    this.sel.cargar().subscribe((lista) => this.cargando.set(lista.length > 0));
  }

  protected limpiar(): void {
    this.origen.set('');
    this.tipo.set('');
    this.estado.set('');
    this.busqueda.set('');
  }

  protected eliminar(p: Proyecto): void {
    confirmar(this.dialog, {
      titulo: 'Eliminar proyecto',
      mensaje: `¿Eliminar «${p.codigo} · ${p.titulo}»? Se quitan también sus autores y jurados.`,
      confirmar: 'Eliminar',
      icono: 'delete',
      peligro: true,
    })
      .pipe(filter(Boolean), switchMap(() => this.api.eliminarProyecto(p.id)))
      .subscribe(() => {
        this.notificador.exito('Proyecto eliminado.');
        this.recarga$.next();
      });
  }
}

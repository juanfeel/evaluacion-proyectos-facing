import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { filter, switchMap, tap } from 'rxjs';

import { EstadoChip } from '../../shared/estado-chip/estado-chip';
import { SelectorEvento } from '../../shared/selector-evento/selector-evento';
import { AdminApi } from '../admin-api';
import { EventoSeleccionado } from '../evento-seleccionado';
import { FilaResultado } from '../modelos';
import { DetalleDialogo } from './detalle-dialogo';

const NOMBRES_TABLA: Record<string, string> = {
  'SEMILLERO-INV': 'Semillero · INV',
  'SEMILLERO-DTI': 'Semillero · DTI',
  'TRABAJO_GRADO-INV': 'Trabajo de grado · INV',
  'TRABAJO_GRADO-DTI': 'Trabajo de grado · DTI',
};

/** RN-41 a RN-47: cuatro tablas, de mayor a menor; los empates comparten puesto. */
@Component({
  selector: 'app-resultados',
  imports: [EstadoChip, MatIconModule, MatProgressBarModule, MatTableModule, MatTabsModule, SelectorEvento],
  templateUrl: './resultados.html',
  styleUrl: './resultados.scss',
})
export class Resultados implements OnInit {
  private readonly api = inject(AdminApi);
  private readonly dialog = inject(MatDialog);
  protected readonly sel = inject(EventoSeleccionado);
  protected readonly cargando = signal(true);
  protected readonly columnas = ['puesto', 'codigo', 'titulo', 'nota1', 'nota2', 'promedio', 'indicadores'];

  protected readonly resultados = toSignal(
    toObservable(this.sel.id).pipe(
      filter((id): id is number => id !== null),
      tap(() => this.cargando.set(true)),
      switchMap((id) => this.api.resultados(id)),
      tap(() => this.cargando.set(false)),
    ),
  );
  protected readonly tablas = computed(() =>
    (this.resultados()?.tablas ?? []).map((t) => ({
      ...t,
      nombre: NOMBRES_TABLA[`${t.origen}-${t.tipo}`] ?? t.titulo,
      evaluados: t.proyectos.filter((p) => !p.pendiente).length,
    })),
  );

  ngOnInit(): void {
    this.sel.cargar().subscribe((lista) => this.cargando.set(lista.length > 0));
  }

  protected verDetalle(fila: FilaResultado): void {
    this.dialog.open(DetalleDialogo, { data: fila.proyecto_id, width: '980px', maxWidth: '96vw', autoFocus: false });
  }
}

import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { filter, forkJoin, switchMap } from 'rxjs';

import { Notificador } from '../../core/notificador';
import { confirmar } from '../../shared/confirmar/confirmar';
import { EstadoChip } from '../../shared/estado-chip/estado-chip';
import { AdminApi } from '../admin-api';
import { EventoSeleccionado } from '../evento-seleccionado';
import { Docente, JuradoAsignado, Proyecto } from '../modelos';
import { ReemplazoDialogo } from './reemplazo-dialogo';

type Vista = 'SIN_JURADOS' | 'CON_JURADOS' | 'TODOS';

function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

/** Asignación de jurados del evento activo: siempre de a dos (un proyecto tiene 0 o 2 jurados). */
@Component({
  selector: 'app-asignaciones',
  imports: [
    EstadoChip, MatButtonModule, MatButtonToggleModule, MatFormFieldModule, MatIconModule, MatInputModule,
    MatProgressBarModule, MatSelectModule, MatTooltipModule, RouterLink,
  ],
  templateUrl: './asignaciones.html',
  styleUrl: './asignaciones.scss',
})
export class Asignaciones implements OnInit {
  private readonly api = inject(AdminApi);
  private readonly dialog = inject(MatDialog);
  private readonly notificador = inject(Notificador);
  protected readonly sel = inject(EventoSeleccionado);

  protected readonly proyectos = signal<Proyecto[]>([]);
  protected readonly docentes = signal<Docente[]>([]);
  protected readonly cargando = signal(true);
  protected readonly guardando = signal<number | null>(null);
  protected readonly vista = signal<Vista>('TODOS');
  protected readonly busqueda = signal('');
  /** Selección en curso por proyecto: [jurado 1, jurado 2]. */
  protected readonly seleccion = signal<Record<number, [number | null, number | null]>>({});

  protected readonly docentesOrdenados = computed(() =>
    [...this.docentes()].sort((a, b) => a.asignados - b.asignados || a.nombre_completo.localeCompare(b.nombre_completo)),
  );
  protected readonly visibles = computed(() => {
    const q = normalizar(this.busqueda().trim());
    return this.proyectos().filter(
      (p) =>
        (this.vista() === 'TODOS' || (this.vista() === 'SIN_JURADOS') === (p.jurados.length === 0)) &&
        (!q || normalizar(`${p.codigo} ${p.titulo} ${p.jurados.map((j) => j.nombre_completo).join(' ')}`).includes(q)),
    );
  });
  protected readonly sinJurados = computed(() => this.proyectos().filter((p) => p.jurados.length === 0).length);
  protected readonly cupoLibre = computed(() =>
    this.docentes().reduce((total, d) => total + Math.max(0, d.max_asignaciones - d.asignados), 0),
  );

  ngOnInit(): void {
    this.sel.cargar().subscribe({
      next: () => this.recargar(),
      error: () => this.cargando.set(false),
    });
  }

  private recargar(): void {
    const activo = this.sel.activo();
    if (!activo) {
      this.cargando.set(false);
      return;
    }
    forkJoin({ proyectos: this.api.proyectos({ evento: activo.id }), docentes: this.api.docentes() }).subscribe({
      next: ({ proyectos, docentes }) => {
        this.proyectos.set(proyectos);
        this.docentes.set(docentes);
        this.cargando.set(false);
      },
      error: () => this.cargando.set(false),
    });
  }

  protected elegido(proyecto: number, posicion: 0 | 1): number | null {
    return this.seleccion()[proyecto]?.[posicion] ?? null;
  }

  protected elegir(proyecto: number, posicion: 0 | 1, docente: number | null): void {
    this.seleccion.update((s) => {
      const par: [number | null, number | null] = [...(s[proyecto] ?? [null, null])];
      par[posicion] = docente;
      return { ...s, [proyecto]: par };
    });
  }

  protected listo(proyecto: number): boolean {
    const [a, b] = this.seleccion()[proyecto] ?? [null, null];
    return a !== null && b !== null && a !== b;
  }

  protected asignar(p: Proyecto): void {
    const [a, b] = this.seleccion()[p.id] ?? [null, null];
    if (a === null || b === null) return;
    this.guardando.set(p.id);
    this.api.asignarJurados(p.id, [a, b]).subscribe({
      next: () => {
        this.notificador.exito(`Jurados asignados a ${p.codigo}.`);
        this.seleccion.update((s) => ({ ...s, [p.id]: [null, null] }));
        this.guardando.set(null);
        this.recargar();
      },
      error: () => {
        this.guardando.set(null);
        this.recargar(); // la carga de algún docente pudo cambiar
      },
    });
  }

  protected cambiar(p: Proyecto, jurado: JuradoAsignado): void {
    this.dialog
      .open(ReemplazoDialogo, { data: { proyecto: p, jurado, docentes: this.docentesOrdenados() }, width: '520px', maxWidth: '94vw' })
      .afterClosed()
      .pipe(filter(Boolean))
      .subscribe(() => {
        this.notificador.exito(`Jurado de ${p.codigo} cambiado.`);
        this.recargar();
      });
  }

  protected quitar(p: Proyecto): void {
    confirmar(this.dialog, {
      titulo: 'Quitar jurados',
      mensaje: `Se quitan los dos jurados de ${p.codigo}. El proyecto quedará «Sin jurados».`,
      confirmar: 'Quitar ambos',
      icono: 'person_remove',
      peligro: true,
    })
      .pipe(filter(Boolean), switchMap(() => this.api.quitarJurados(p.id)))
      .subscribe(() => {
        this.notificador.exito(`Se quitaron los jurados de ${p.codigo}.`);
        this.recargar();
      });
  }

  protected algunoEvaluo(p: Proyecto): boolean {
    return p.jurados.some((j) => j.evaluada);
  }
}

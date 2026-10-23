import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { filter, switchMap } from 'rxjs';

import { Notificador } from '../../core/notificador';
import { confirmar } from '../../shared/confirmar/confirmar';
import { EstadoChip } from '../../shared/estado-chip/estado-chip';
import { AdminApi } from '../admin-api';
import { Docente } from '../modelos';
import { DocenteDialogo } from './docente-dialogo';

function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

@Component({
  selector: 'app-docentes',
  imports: [
    EstadoChip, MatButtonModule, MatFormFieldModule, MatIconModule, MatInputModule, MatProgressBarModule,
    MatTableModule, MatTooltipModule,
  ],
  templateUrl: './docentes.html',
})
export class Docentes implements OnInit {
  private readonly api = inject(AdminApi);
  private readonly dialog = inject(MatDialog);
  private readonly notificador = inject(Notificador);

  protected readonly docentes = signal<Docente[]>([]);
  protected readonly cargando = signal(true);
  protected readonly busqueda = signal('');
  protected readonly filtrados = computed(() => {
    const q = normalizar(this.busqueda().trim());
    if (!q) return this.docentes();
    return this.docentes().filter((d) =>
      normalizar(`${d.nombre_completo} ${d.cedula} ${d.email} ${d.departamento}`).includes(q),
    );
  });
  protected readonly columnas = ['nombre', 'cedula', 'email', 'departamento', 'carga', 'acceso', 'acciones'];

  ngOnInit(): void {
    this.recargar();
  }

  private recargar(): void {
    this.api.docentes().subscribe({
      next: (lista) => {
        this.docentes.set(lista);
        this.cargando.set(false);
      },
      error: () => this.cargando.set(false),
    });
  }

  protected abrir(docente: Docente | null = null): void {
    this.dialog
      .open(DocenteDialogo, { data: docente, width: '560px', maxWidth: '94vw' })
      .afterClosed()
      .pipe(filter(Boolean))
      .subscribe((d: Docente) => {
        this.notificador.exito(
          docente ? 'Docente actualizado.' : `${d.nombre_completo} registrado. Su contraseña inicial es su cédula.`,
        );
        this.recargar();
      });
  }

  protected restablecer(docente: Docente): void {
    confirmar(this.dialog, {
      titulo: 'Restablecer contraseña',
      mensaje:
        `La contraseña de ${docente.nombre_completo} volverá a ser su cédula y deberá cambiarla al ingresar.\n` +
        'Si estaba bloqueado por intentos fallidos, también se desbloquea.',
      confirmar: 'Restablecer',
      icono: 'lock_reset',
    })
      .pipe(filter(Boolean), switchMap(() => this.api.restablecerPassword(docente.id)))
      .subscribe((r) => {
        this.notificador.exito(r.detalle);
        this.recargar();
      });
  }

  protected eliminar(docente: Docente): void {
    confirmar(this.dialog, {
      titulo: 'Eliminar docente',
      mensaje: `¿Eliminar a ${docente.nombre_completo}? Esta acción no se puede deshacer.`,
      confirmar: 'Eliminar',
      icono: 'delete',
      peligro: true,
    })
      .pipe(filter(Boolean), switchMap(() => this.api.eliminarDocente(docente.id)))
      .subscribe(() => {
        this.notificador.exito('Docente eliminado.');
        this.recargar();
      });
  }

  protected motivoNoEliminar(d: Docente): string {
    if (d.tiene_evaluaciones) return 'No se puede eliminar: ya envió evaluaciones';
    if (d.asignados > 0) return 'Es jurado de algún proyecto: reemplácelo primero en Asignaciones';
    return 'Eliminar';
  }
}

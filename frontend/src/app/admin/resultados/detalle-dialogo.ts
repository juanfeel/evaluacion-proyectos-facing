import { DatePipe } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { EstadoChip } from '../../shared/estado-chip/estado-chip';
import { AdminApi } from '../admin-api';
import { EvaluacionCompleta, Proyecto } from '../modelos';

/** RN-47: las dos evaluaciones completas de un proyecto. */
@Component({
  selector: 'app-detalle-dialogo',
  imports: [DatePipe, EstadoChip, MatButtonModule, MatDialogModule, MatIconModule, MatProgressBarModule],
  templateUrl: './detalle-dialogo.html',
  styleUrl: './detalle-dialogo.scss',
})
export class DetalleDialogo implements OnInit {
  private readonly api = inject(AdminApi);
  protected readonly proyectoId = inject<number>(MAT_DIALOG_DATA);
  protected readonly proyecto = signal<Proyecto | null>(null);
  protected readonly evaluaciones = signal<EvaluacionCompleta[]>([]);
  protected readonly cargando = signal(true);

  ngOnInit(): void {
    this.api.evaluacionesDeProyecto(this.proyectoId).subscribe({
      next: (r) => {
        this.proyecto.set(r.proyecto);
        this.evaluaciones.set(r.evaluaciones);
        this.cargando.set(false);
      },
      error: () => this.cargando.set(false),
    });
  }
}

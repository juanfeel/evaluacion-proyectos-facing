import { Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';

import { AdminApi } from '../admin-api';
import { Docente, JuradoAsignado, Proyecto } from '../modelos';

export interface DatosReemplazo {
  proyecto: Proyecto;
  jurado: JuradoAsignado;
  docentes: Docente[];
}

/** Cambia un jurado por otro en un solo paso: el proyecto nunca queda con un solo jurado. */
@Component({
  selector: 'app-reemplazo-dialogo',
  imports: [MatButtonModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatSelectModule],
  template: `
    <h2 mat-dialog-title>Cambiar jurado</h2>
    <mat-dialog-content class="dialogo-formulario">
      <p>Proyecto <strong>{{ datos.proyecto.codigo }}</strong>: se reemplaza a <strong>{{ datos.jurado.nombre_completo }}</strong>.</p>
      <mat-form-field>
        <mat-label>Nuevo jurado</mat-label>
        <mat-select [value]="elegido()" (valueChange)="elegido.set($event)">
          @for (d of opciones(); track d.id) {
            <mat-option [value]="d.id" [disabled]="d.asignados >= d.max_asignaciones">
              {{ d.nombre_completo }} ({{ d.asignados }}/{{ d.max_asignaciones }})
            </mat-option>
          }
        </mat-select>
        <mat-hint>Los docentes con 3 proyectos aparecen deshabilitados.</mat-hint>
      </mat-form-field>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-stroked-button mat-dialog-close><mat-icon>close</mat-icon> Cancelar</button>
      <button mat-flat-button (click)="guardar()" [disabled]="!elegido() || enviando()"><mat-icon>swap_horiz</mat-icon> Cambiar</button>
    </mat-dialog-actions>
  `,
})
export class ReemplazoDialogo {
  private readonly api = inject(AdminApi);
  private readonly ref = inject(MatDialogRef<ReemplazoDialogo>);
  protected readonly datos = inject<DatosReemplazo>(MAT_DIALOG_DATA);
  protected readonly elegido = signal<number | null>(null);
  protected readonly enviando = signal(false);
  protected readonly opciones = computed(() => {
    const actuales = new Set(this.datos.proyecto.jurados.map((j) => j.docente_id));
    return this.datos.docentes.filter((d) => !actuales.has(d.id));
  });

  protected guardar(): void {
    const id = this.elegido();
    if (!id) return;
    this.enviando.set(true);
    this.api.reemplazarJurado(this.datos.jurado.asignacion_id, id).subscribe({
      next: () => this.ref.close(true),
      error: () => this.enviando.set(false),
    });
  }
}

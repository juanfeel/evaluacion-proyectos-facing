import { Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';

import { erroresDeCampos } from '../../core/notificador';
import { AdminApi } from '../admin-api';
import { Evento } from '../modelos';

@Component({
  selector: 'app-evento-dialogo',
  imports: [MatButtonModule, MatCheckboxModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatInputModule, ReactiveFormsModule],
  template: `
    <h2 mat-dialog-title>{{ evento ? 'Editar evento' : 'Nuevo evento' }}</h2>
    <form [formGroup]="form" (ngSubmit)="guardar()" novalidate>
      <mat-dialog-content class="dialogo-formulario">
        <mat-form-field>
          <mat-label>Nombre del evento</mat-label>
          <input matInput formControlName="nombre" cdkFocusInitial />
          @if (errores()['nombre']) { <mat-error>{{ errores()['nombre'] }}</mat-error> }
          @else { <mat-error>Escriba el nombre del evento.</mat-error> }
        </mat-form-field>
        <mat-form-field>
          <mat-label>Fecha</mat-label>
          <input matInput type="date" formControlName="fecha" />
          <mat-error>Indique la fecha del evento.</mat-error>
        </mat-form-field>
        @if (!evento) {
          <mat-checkbox formControlName="activo">Activar este evento (desactiva el que esté activo)</mat-checkbox>
        }
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        <button mat-stroked-button type="button" mat-dialog-close><mat-icon>close</mat-icon> Cancelar</button>
        <button mat-flat-button type="submit" [disabled]="enviando()"><mat-icon>save</mat-icon> Guardar</button>
      </mat-dialog-actions>
    </form>
  `,
})
export class EventoDialogo {
  private readonly api = inject(AdminApi);
  private readonly ref = inject(MatDialogRef<EventoDialogo>);
  protected readonly evento = inject<Evento | null>(MAT_DIALOG_DATA);
  protected readonly enviando = signal(false);
  protected readonly errores = signal<Record<string, string>>({});
  protected readonly form = inject(NonNullableFormBuilder).group({
    nombre: [this.evento?.nombre ?? 'I Encuentro de Semilleros de Investigación y Trabajos de Grado', Validators.required],
    fecha: [this.evento?.fecha ?? '2026-10-09', Validators.required],
    activo: [!this.evento],
  });

  protected guardar(): void {
    if (this.form.invalid || this.enviando()) {
      this.form.markAllAsTouched();
      return;
    }
    this.enviando.set(true);
    const { nombre, fecha, activo } = this.form.getRawValue();
    const peticion = this.evento
      ? this.api.editarEvento(this.evento.id, { nombre: nombre.trim(), fecha })
      : this.api.crearEvento({ nombre: nombre.trim(), fecha, activo });
    peticion.subscribe({
      next: (e) => this.ref.close(e),
      error: (e) => {
        this.enviando.set(false);
        this.errores.set(erroresDeCampos(e));
      },
    });
  }
}

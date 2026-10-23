import { Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

import { erroresDeCampos } from '../../core/notificador';
import { AdminApi } from '../admin-api';
import { DEPARTAMENTOS, Docente } from '../modelos';

const CEDULA = /^[0-9A-Za-z]{4,20}$/;

@Component({
  selector: 'app-docente-dialogo',
  imports: [
    MatButtonModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule, ReactiveFormsModule,
  ],
  template: `
    <h2 mat-dialog-title>{{ docente ? 'Editar docente' : 'Registrar docente' }}</h2>
    <form [formGroup]="form" (ngSubmit)="guardar()" novalidate>
      <mat-dialog-content class="dialogo-formulario">
        @if (!docente) {
          <p class="aviso aviso--info"><mat-icon>key</mat-icon>
            <span>La contraseña inicial es la <strong>cédula del docente</strong>. Deberá cambiarla en su primer ingreso.</span></p>
        } @else {
          <p class="aviso aviso--info"><mat-icon>info</mat-icon>
            <span>Cambiar la cédula <strong>no</strong> cambia la contraseña del docente.</span></p>
        }
        <mat-form-field>
          <mat-label>Nombre completo</mat-label>
          <input matInput formControlName="nombre_completo" cdkFocusInitial />
          <mat-error>{{ errores()['nombre_completo'] || 'Escriba el nombre completo.' }}</mat-error>
        </mat-form-field>
        <mat-form-field>
          <mat-label>Cédula</mat-label>
          <input matInput formControlName="cedula" inputmode="numeric" />
          <mat-hint>Solo números, sin puntos ni espacios.</mat-hint>
          <mat-error>{{ errores()['cedula'] || 'Escriba la cédula: solo números o letras, sin puntos.' }}</mat-error>
        </mat-form-field>
        <mat-form-field>
          <mat-label>Correo institucional</mat-label>
          <input matInput type="email" formControlName="email" />
          <mat-hint>Es el usuario con el que ingresa.</mat-hint>
          <mat-error>{{ errores()['email'] || 'Escriba un correo válido.' }}</mat-error>
        </mat-form-field>
        <mat-form-field>
          <mat-label>Departamento académico</mat-label>
          <mat-select formControlName="departamento">
            @for (d of departamentos; track d) { <mat-option [value]="d">{{ d }}</mat-option> }
          </mat-select>
          <mat-error>{{ errores()['departamento'] || 'Elija el departamento.' }}</mat-error>
        </mat-form-field>
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        <button mat-stroked-button type="button" mat-dialog-close><mat-icon>close</mat-icon> Cancelar</button>
        <button mat-flat-button type="submit" [disabled]="enviando()"><mat-icon>save</mat-icon> Guardar</button>
      </mat-dialog-actions>
    </form>
  `,
})
export class DocenteDialogo {
  private readonly api = inject(AdminApi);
  private readonly ref = inject(MatDialogRef<DocenteDialogo>);
  protected readonly docente = inject<Docente | null>(MAT_DIALOG_DATA);
  protected readonly departamentos = DEPARTAMENTOS;
  protected readonly enviando = signal(false);
  protected readonly errores = signal<Record<string, string>>({});
  protected readonly form = inject(NonNullableFormBuilder).group({
    nombre_completo: [this.docente?.nombre_completo ?? '', Validators.required],
    cedula: [this.docente?.cedula ?? '', [Validators.required, Validators.pattern(CEDULA)]],
    email: [this.docente?.email ?? '', [Validators.required, Validators.email]],
    departamento: [
      (DEPARTAMENTOS as readonly string[]).includes(this.docente?.departamento ?? '') ? this.docente!.departamento : '',
      Validators.required,
    ],
  });

  protected guardar(): void {
    this.form.controls.cedula.setValue(this.form.controls.cedula.value.replace(/[.\s]/g, ''));
    if (this.form.invalid || this.enviando()) {
      this.form.markAllAsTouched();
      return;
    }
    this.enviando.set(true);
    const datos = this.form.getRawValue();
    const peticion = this.docente ? this.api.editarDocente(this.docente.id, datos) : this.api.crearDocente(datos);
    peticion.subscribe({
      next: (d) => this.ref.close(d),
      error: (e) => {
        this.enviando.set(false);
        const errores = erroresDeCampos(e);
        this.errores.set(errores);
        for (const campo of Object.keys(errores)) {
          this.form.get(campo)?.setErrors({ servidor: true });
          this.form.get(campo)?.markAsTouched();
        }
      },
    });
  }
}

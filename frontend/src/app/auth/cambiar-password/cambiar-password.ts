import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { AbstractControl, NonNullableFormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { erroresDeCampos, Notificador } from '../../core/notificador';
import { Encabezado } from '../../shared/encabezado/encabezado';

function coinciden(grupo: AbstractControl): ValidationErrors | null {
  const nueva = grupo.get('password_nueva')?.value;
  const confirmacion = grupo.get('confirmacion')?.value;
  return confirmacion && nueva !== confirmacion ? { noCoinciden: true } : null;
}

/** RN-07 y RN-08. Las reglas se muestran en vivo; la validación definitiva la hace el backend. */
@Component({
  selector: 'app-cambiar-password',
  imports: [
    Encabezado, MatButtonModule, MatFormFieldModule, MatIconModule, MatInputModule, MatProgressSpinnerModule,
    ReactiveFormsModule,
  ],
  templateUrl: './cambiar-password.html',
})
export class CambiarPassword {
  protected readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly notificador = inject(Notificador);

  protected readonly obligatorio = computed(() => this.auth.usuario()?.debe_cambiar_password ?? false);
  protected readonly form = inject(NonNullableFormBuilder).group(
    {
      password_actual: ['', Validators.required],
      password_nueva: ['', [Validators.required, Validators.minLength(8)]],
      confirmacion: ['', Validators.required],
    },
    { validators: coinciden },
  );
  protected readonly enviando = signal(false);
  protected readonly erroresServidor = signal<Record<string, string>>({});

  private readonly nueva = toSignal(this.form.controls.password_nueva.valueChanges, { initialValue: '' });
  protected readonly reglas = computed(() => {
    const valor = this.nueva();
    return [
      { texto: 'Al menos 8 caracteres', cumple: valor.length >= 8 },
      { texto: 'No puede ser solo números', cumple: valor.length > 0 && !/^\d+$/.test(valor) },
      { texto: 'No puede ser su cédula ni parecerse a su correo o nombre', cumple: null },
      { texto: 'No puede ser una contraseña común (p. ej. «12345678» o «password»)', cumple: null },
    ];
  });

  protected guardar(): void {
    if (this.form.invalid || this.enviando()) {
      this.form.markAllAsTouched();
      return;
    }
    this.enviando.set(true);
    this.erroresServidor.set({});
    const v = this.form.getRawValue();
    this.auth.cambiarPassword(v.password_actual, v.password_nueva, v.confirmacion).subscribe({
      next: () => {
        this.notificador.exito('Contraseña actualizada.');
        void this.router.navigateByUrl(this.auth.rutaInicio());
      },
      error: (error) => {
        this.enviando.set(false);
        this.erroresServidor.set(erroresDeCampos(error));
      },
    });
  }

  protected volver(): void {
    void this.router.navigateByUrl(this.auth.rutaInicio());
  }
}

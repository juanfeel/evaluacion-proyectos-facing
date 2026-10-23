import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { map, Observable } from 'rxjs';

export interface DatosConfirmacion {
  titulo: string;
  mensaje: string;
  confirmar: string;
  icono?: string;
  peligro?: boolean;
  cancelar?: string;
}

/** Diálogo de confirmación reutilizable. Devuelve true solo si el usuario confirma. */
@Component({
  selector: 'app-confirmar',
  imports: [MatButtonModule, MatDialogModule, MatIconModule],
  template: `
    <h2 mat-dialog-title>{{ datos.titulo }}</h2>
    <mat-dialog-content><p class="confirmar__mensaje">{{ datos.mensaje }}</p></mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-stroked-button [mat-dialog-close]="false"><mat-icon>close</mat-icon> {{ datos.cancelar ?? 'Cancelar' }}</button>
      <button mat-flat-button [class.boton-peligro]="datos.peligro" [mat-dialog-close]="true" cdkFocusInitial>
        <mat-icon>{{ datos.icono ?? 'check' }}</mat-icon> {{ datos.confirmar }}
      </button>
    </mat-dialog-actions>
  `,
  styles: '.confirmar__mensaje { margin: 0; white-space: pre-line; }',
})
export class Confirmar {
  protected readonly datos = inject<DatosConfirmacion>(MAT_DIALOG_DATA);
}

export function confirmar(dialog: MatDialog, datos: DatosConfirmacion): Observable<boolean> {
  return dialog
    .open(Confirmar, { data: datos, width: '440px', maxWidth: '94vw', autoFocus: 'dialog' })
    .afterClosed()
    .pipe(map((r) => r === true));
}

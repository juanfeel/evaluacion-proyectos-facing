import { Component, inject } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

import { EventoSeleccionado } from '../../admin/evento-seleccionado';

@Component({
  selector: 'app-selector-evento',
  imports: [MatFormFieldModule, MatSelectModule],
  template: `
    @if (sel.eventos().length > 1) {
      <mat-form-field class="selector-evento" subscriptSizing="dynamic">
        <mat-label>Evento</mat-label>
        <mat-select [value]="sel.id()" (valueChange)="sel.elegir($event)">
          @for (e of sel.eventos(); track e.id) {
            <mat-option [value]="e.id">{{ e.nombre }}{{ e.activo ? ' (activo)' : '' }}</mat-option>
          }
        </mat-select>
      </mat-form-field>
    }
  `,
})
export class SelectorEvento {
  protected readonly sel = inject(EventoSeleccionado);
}

import { BreakpointObserver } from '@angular/cdk/layout';
import { Component, inject, input, output } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTabsModule } from '@angular/material/tabs';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { map } from 'rxjs';

export interface ItemNavegacion {
  ruta: string;
  etiqueta: string;
  icono: string;
}

/** Header SAPIENS (degradado + pestañas) y franja diagonal con el título de la sección. */
@Component({
  selector: 'app-encabezado',
  imports: [MatButtonModule, MatIconModule, MatMenuModule, MatTabsModule, RouterLink, RouterLinkActive],
  templateUrl: './encabezado.html',
})
export class Encabezado {
  readonly contexto = input.required<string>();
  readonly titulo = input.required<string>();
  readonly usuario = input<string>('');
  readonly navegacion = input<ItemNavegacion[]>([]);
  readonly seccion = input<string>('');
  readonly mostrarSalir = input(true);
  readonly salir = output<void>();

  protected readonly esCelular = toSignal(
    inject(BreakpointObserver).observe('(max-width: 720px)').pipe(map((r) => r.matches)),
    { initialValue: false },
  );
}

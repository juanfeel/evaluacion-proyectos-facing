import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { Encabezado } from '../../shared/encabezado/encabezado';
import { tituloDeRuta } from '../../shared/titulo-ruta';

/** Layout del jurado: mobile-first, sin navegación (una sola tarea). */
@Component({
  selector: 'app-jurado-layout',
  imports: [Encabezado, RouterOutlet],
  template: `
    <app-encabezado
      contexto="FACING · Jurado"
      [titulo]="auth.usuario()?.nombre_completo ?? 'Jurado'"
      [seccion]="seccion()"
      (salir)="auth.salir()"
    />
    <main class="pagina pagina--angosta"><router-outlet /></main>
  `,
})
export class JuradoLayout {
  protected readonly auth = inject(AuthService);
  protected readonly seccion = tituloDeRuta();
}

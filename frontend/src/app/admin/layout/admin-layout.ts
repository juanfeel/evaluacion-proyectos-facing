import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { Encabezado, ItemNavegacion } from '../../shared/encabezado/encabezado';
import { tituloDeRuta } from '../../shared/titulo-ruta';

@Component({
  selector: 'app-admin-layout',
  imports: [Encabezado, RouterOutlet],
  template: `
    <app-encabezado
      contexto="Universidad de Nariño · Facultad de Ingeniería"
      titulo="Evaluación de Proyectos"
      [usuario]="auth.usuario()?.nombre_completo ?? ''"
      [navegacion]="navegacion"
      [seccion]="seccion()"
      (salir)="auth.salir()"
    />
    <main class="pagina"><router-outlet /></main>
  `,
})
export class AdminLayout {
  protected readonly auth = inject(AuthService);
  protected readonly seccion = tituloDeRuta();
  protected readonly navegacion: ItemNavegacion[] = [
    { ruta: '/admin/inicio', etiqueta: 'Inicio', icono: 'dashboard' },
    { ruta: '/admin/eventos', etiqueta: 'Eventos', icono: 'event' },
    { ruta: '/admin/docentes', etiqueta: 'Docentes', icono: 'groups' },
    { ruta: '/admin/proyectos', etiqueta: 'Proyectos', icono: 'list_alt' },
    { ruta: '/admin/asignaciones', etiqueta: 'Asignaciones', icono: 'assignment_ind' },
    { ruta: '/admin/resultados', etiqueta: 'Resultados', icono: 'emoji_events' },
  ];
}

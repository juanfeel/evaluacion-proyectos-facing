import { DatePipe } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { filter, switchMap } from 'rxjs';

import { Notificador } from '../../core/notificador';
import { confirmar } from '../../shared/confirmar/confirmar';
import { EstadoChip } from '../../shared/estado-chip/estado-chip';
import { AdminApi } from '../admin-api';
import { EventoSeleccionado } from '../evento-seleccionado';
import { Evento } from '../modelos';
import { EventoDialogo } from './evento-dialogo';

@Component({
  selector: 'app-eventos',
  imports: [DatePipe, EstadoChip, MatButtonModule, MatIconModule, MatTableModule, MatTooltipModule],
  templateUrl: './eventos.html',
})
export class Eventos implements OnInit {
  private readonly api = inject(AdminApi);
  private readonly dialog = inject(MatDialog);
  private readonly notificador = inject(Notificador);
  protected readonly sel = inject(EventoSeleccionado);
  protected readonly columnas = ['nombre', 'fecha', 'proyectos', 'estado', 'acciones'];

  ngOnInit(): void {
    this.recargar();
  }

  private recargar(): void {
    this.sel.cargar().subscribe();
  }

  protected abrir(evento: Evento | null = null): void {
    this.dialog
      .open(EventoDialogo, { data: evento, width: '520px', maxWidth: '94vw' })
      .afterClosed()
      .pipe(filter(Boolean))
      .subscribe(() => {
        this.notificador.exito(evento ? 'Evento actualizado.' : 'Evento creado.');
        this.recargar();
      });
  }

  protected activar(evento: Evento): void {
    const actual = this.sel.activo();
    confirmar(this.dialog, {
      titulo: 'Activar evento',
      mensaje: `Los jurados solo ven las asignaciones del evento activo.` +
        (actual ? `\n«${actual.nombre}» dejará de estar activo.` : ''),
      confirmar: 'Activar',
      icono: 'radio_button_checked',
    })
      .pipe(filter(Boolean), switchMap(() => this.api.activarEvento(evento.id)))
      .subscribe(() => {
        this.notificador.exito(`«${evento.nombre}» es ahora el evento activo.`);
        this.sel.elegir(evento.id);
        this.recargar();
      });
  }

  protected eliminar(evento: Evento): void {
    confirmar(this.dialog, {
      titulo: 'Eliminar evento',
      mensaje: `¿Eliminar «${evento.nombre}»? Esta acción no se puede deshacer.`,
      confirmar: 'Eliminar',
      icono: 'delete',
      peligro: true,
    })
      .pipe(filter(Boolean), switchMap(() => this.api.eliminarEvento(evento.id)))
      .subscribe(() => {
        this.notificador.exito('Evento eliminado.');
        this.recargar();
      });
  }
}

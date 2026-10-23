import { Component, computed, input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

const ESTADOS: Record<string, { texto: string; clase: string; icono: string }> = {
  SIN_JURADOS: { texto: 'Sin jurados', clase: 'estado--sin-jurados', icono: 'person_off' },
  PENDIENTE: { texto: 'Pendiente', clase: 'estado--pendiente', icono: 'schedule' },
  PARCIAL: { texto: 'Parcial 1/2', clase: 'estado--parcial', icono: 'timelapse' },
  EVALUADO: { texto: 'Evaluado', clase: 'estado--evaluado', icono: 'check_circle' },
  ENVIADA: { texto: 'Enviada', clase: 'estado--enviada', icono: 'check_circle' },
  RECONOCIMIENTO: { texto: 'Reconocimiento', clase: 'estado--enviada', icono: 'emoji_events' },
  MENCION: { texto: 'Mención meritoria', clase: 'estado--mencion', icono: 'workspace_premium' },
  SIN_SUSTENTACION: { texto: 'Sin sustentación', clase: 'estado--peligro', icono: 'voice_over_off' },
  ACTIVO: { texto: 'Activo', clase: 'estado--enviada', icono: 'radio_button_checked' },
  PRIMER_INGRESO: { texto: 'Sin primer ingreso', clase: 'estado--pendiente', icono: 'key' },
};

/** Estado con color, ícono y texto (nunca solo color). */
@Component({
  selector: 'app-estado-chip',
  imports: [MatIconModule],
  template: `<span class="estado" [class]="'estado ' + info().clase"><mat-icon>{{ info().icono }}</mat-icon>{{ texto() || info().texto }}</span>`,
})
export class EstadoChip {
  readonly estado = input.required<string>();
  readonly texto = input<string>('');
  protected readonly info = computed(() => ESTADOS[this.estado()] ?? { texto: this.estado(), clase: '', icono: 'info' });
}

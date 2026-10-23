import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, HostListener, inject, input, OnInit, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router, RouterLink } from '@angular/router';
import { filter, Observable, of } from 'rxjs';

import { AuthService } from '../../core/auth.service';
import { Notificador } from '../../core/notificador';
import { confirmar } from '../../shared/confirmar/confirmar';
import {
  Asistencia, nadieAsistio, Niveles, nivelesEfectivos, ORDEN_SUSTENTACION, pendientes, puntajeMaximo, totalEnVivo,
} from '../calificacion';
import { JuradoApi } from '../jurado-api';
import { CriterioFormulario, EvaluacionPropia, Formulario } from '../modelos';

type Etapa = 'cargando' | 'llenando' | 'enviando' | 'enviada';

/** Formulario de evaluación del jurado (RN-30 a RN-38). Mobile-first. */
@Component({
  selector: 'app-evaluar',
  imports: [
    DatePipe, MatButtonModule, MatButtonToggleModule, MatFormFieldModule, MatIconModule, MatInputModule, MatProgressBarModule,
    MatProgressSpinnerModule, RouterLink,
  ],
  templateUrl: './evaluar.html',
  styleUrl: './evaluar.scss',
})
export class Evaluar implements OnInit {
  /** Parámetro de ruta `:id` (id de la asignación). */
  readonly id = input.required<string>();

  private readonly api = inject(JuradoApi);
  private readonly router = inject(Router);
  private readonly dialog = inject(MatDialog);
  private readonly notificador = inject(Notificador);
  protected readonly auth = inject(AuthService);

  protected readonly etapa = signal<Etapa>('cargando');
  protected readonly formulario = signal<Formulario | null>(null);
  protected readonly niveles = signal<Niveles>({});
  protected readonly asistencia = signal<Asistencia>({});
  protected readonly fortalezas = signal('');
  protected readonly aspectos = signal('');
  protected readonly resultado = signal<EvaluacionPropia | null>(null);

  private readonly criterios = computed(() => this.formulario()?.criterios ?? []);
  private readonly autores = computed(() => this.formulario()?.autores ?? []);
  protected readonly sinSustentacion = computed(() => nadieAsistio(this.autores(), this.asistencia()));
  protected readonly efectivos = computed(() => nivelesEfectivos(this.criterios(), this.niveles(), this.sinSustentacion()));
  protected readonly total = computed(() => totalEnVivo(this.criterios(), this.efectivos()));
  protected readonly maximo = computed(() => puntajeMaximo(this.criterios()));
  protected readonly faltan = computed(() => pendientes(this.criterios(), this.autores(), this.efectivos(), this.asistencia()));
  protected readonly completo = computed(() => !this.faltan().criterios.length && !this.faltan().autores);
  protected readonly textoFaltan = computed(() => {
    const f = this.faltan();
    const partes = [];
    if (f.autores) partes.push(`asistencia de ${f.autores} ${f.autores === 1 ? 'autor' : 'autores'}`);
    if (f.criterios.length) partes.push(`${f.criterios.length === 1 ? 'criterio' : 'criterios'} ${f.criterios.join(', ')}`);
    return partes.length ? 'Falta: ' + partes.join(' y ') : 'Listo para enviar';
  });
  /** Hay algo marcado o escrito que se perdería al salir. */
  private readonly sucio = computed(
    () =>
      Object.keys(this.niveles()).length > 0 ||
      Object.keys(this.asistencia()).length > 0 ||
      !!this.fortalezas().trim() ||
      !!this.aspectos().trim(),
  );

  ngOnInit(): void {
    const id = Number(this.id());
    this.api.formulario(id).subscribe({
      next: (f) => {
        if (f.evaluada) {
          void this.router.navigate(['/jurado/evaluacion', id], { replaceUrl: true });
          return;
        }
        this.formulario.set(f);
        this.etapa.set('llenando');
      },
      error: () => void this.router.navigateByUrl('/jurado'),
    });
  }

  protected elegirNivel(criterio: CriterioFormulario, nivel: number): void {
    if (this.etapa() !== 'llenando' || this.bloqueado(criterio)) return;
    this.niveles.update((n) => ({ ...n, [criterio.id]: nivel }));
  }

  protected marcarAsistencia(autorId: number, asistio: boolean): void {
    this.asistencia.update((a) => ({ ...a, [autorId]: asistio }));
  }

  /** RN-33: si nadie asistió, la sustentación queda fija en Insuficiente. */
  protected bloqueado(criterio: CriterioFormulario): boolean {
    return criterio.orden === ORDEN_SUSTENTACION && this.sinSustentacion();
  }

  protected irAPendiente(): void {
    const f = this.faltan();
    const destino = f.autores ? 'asistencia' : f.criterios.length ? `criterio-${f.criterios[0]}` : 'observaciones';
    document.getElementById(destino)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  protected enviar(): void {
    if (this.etapa() !== 'llenando') return;
    if (!this.completo()) {
      this.irAPendiente();
      return;
    }
    confirmar(this.dialog, {
      titulo: '¿Enviar la evaluación?',
      mensaje:
        `Total: ${this.total()} / ${this.maximo()}.\n` +
        'Una vez enviada, la calificación NO se puede editar. Revise los niveles, la asistencia y las observaciones.',
      confirmar: 'Confirmar envío',
      cancelar: 'Cancelar',
      icono: 'send',
    })
      .pipe(filter(Boolean))
      .subscribe(() => this.confirmarEnvio());
  }

  private confirmarEnvio(): void {
    if (this.etapa() !== 'llenando') return; // doble toque
    const f = this.formulario()!;
    this.etapa.set('enviando');
    const niveles = Object.fromEntries(Object.entries(this.efectivos()).map(([k, v]) => [k, v as number]));
    const asistencia = Object.fromEntries(Object.entries(this.asistencia()).map(([k, v]) => [k, v as boolean]));
    this.api
      .enviar(f.asignacion_id, {
        niveles, asistencia, fortalezas: this.fortalezas().trim(), aspectos_mejorar: this.aspectos().trim(),
      })
      .subscribe({
        next: (evaluacion) => {
          this.resultado.set(evaluacion);
          this.etapa.set('enviada');
          window.scrollTo({ top: 0 });
        },
        error: (e: unknown) => {
          if (e instanceof HttpErrorResponse && e.status === 409) {
            // RN-38: ya estaba registrada (doble envío o reintento de red): se muestra la registrada.
            this.etapa.set('enviada');
            this.notificador.exito('Esta evaluación ya estaba registrada.');
            void this.router.navigate(['/jurado/evaluacion', f.asignacion_id], { replaceUrl: true });
            return;
          }
          this.etapa.set('llenando');
          this.notificador.errorHttp(e);
        },
      });
  }

  /** Para el guard de salida: confirma antes de descartar un formulario a medio llenar. */
  puedeSalir(): Observable<boolean> {
    if (this.etapa() === 'enviando') return of(false);
    if (this.etapa() !== 'llenando' || !this.sucio()) return of(true);
    return confirmar(this.dialog, {
      titulo: '¿Salir sin enviar?',
      mensaje: 'Perderá los niveles, la asistencia y las observaciones que ha marcado en esta evaluación.',
      confirmar: 'Salir y descartar',
      cancelar: 'Seguir evaluando',
      icono: 'logout',
      peligro: true,
    });
  }

  @HostListener('window:beforeunload', ['$event'])
  protected antesDeCerrar(evento: BeforeUnloadEvent): void {
    if ((this.etapa() === 'llenando' && this.sucio()) || this.etapa() === 'enviando') {
      evento.preventDefault();
    }
  }
}

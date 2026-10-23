import { DatePipe } from '@angular/common';
import { Component, inject, input, OnInit, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { Router, RouterLink } from '@angular/router';

import { EstadoChip } from '../../shared/estado-chip/estado-chip';
import { JuradoApi } from '../jurado-api';
import { EvaluacionPropia } from '../modelos';

/** Evaluación propia ya enviada, solo lectura (RN-36). */
@Component({
  selector: 'app-evaluacion-enviada',
  imports: [DatePipe, EstadoChip, MatButtonModule, MatIconModule, MatProgressBarModule, RouterLink],
  templateUrl: './evaluacion-enviada.html',
  styleUrl: './evaluacion-enviada.scss',
})
export class EvaluacionEnviada implements OnInit {
  readonly id = input.required<string>();
  private readonly api = inject(JuradoApi);
  private readonly router = inject(Router);
  protected readonly evaluacion = signal<EvaluacionPropia | null>(null);

  ngOnInit(): void {
    this.api.evaluacion(Number(this.id())).subscribe({
      next: (e) => this.evaluacion.set(e),
      error: () => void this.router.navigateByUrl('/jurado'),
    });
  }
}

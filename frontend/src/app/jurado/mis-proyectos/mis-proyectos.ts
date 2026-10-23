import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { EstadoChip } from '../../shared/estado-chip/estado-chip';
import { JuradoApi } from '../jurado-api';
import { AsignacionJurado } from '../modelos';

@Component({
  selector: 'app-mis-proyectos',
  imports: [EstadoChip, MatIconModule, MatProgressBarModule, RouterLink],
  templateUrl: './mis-proyectos.html',
  styleUrl: './mis-proyectos.scss',
})
export class MisProyectos implements OnInit {
  private readonly api = inject(JuradoApi);
  protected readonly auth = inject(AuthService);
  protected readonly asignaciones = signal<AsignacionJurado[]>([]);
  protected readonly cargando = signal(true);
  protected readonly enviadas = computed(() => this.asignaciones().filter((a) => a.evaluada).length);
  /** Pendientes primero; las enviadas al final. */
  protected readonly ordenadas = computed(() =>
    [...this.asignaciones()].sort((a, b) => Number(a.evaluada) - Number(b.evaluada)),
  );

  ngOnInit(): void {
    this.api.misAsignaciones().subscribe({
      next: (lista) => {
        this.asignaciones.set(lista);
        this.cargando.set(false);
      },
      error: () => this.cargando.set(false),
    });
  }
}

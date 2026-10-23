import { Component, inject, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';

interface Health {
  ok: boolean;
  db: boolean;
}

@Component({
  selector: 'app-estado',
  styleUrl: './estado.scss',
  templateUrl: './estado.html',
})
export class Estado implements OnInit {
  private readonly http = inject(HttpClient);

  protected readonly health = signal<Health | null>(null);
  protected readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.http.get<Health>('/api/health/').subscribe({
      next: (r) => this.health.set(r),
      error: (e) => {
        // Un 503 del backend trae {ok, db:false}: se muestra igual.
        if (typeof e?.error?.db === 'boolean') {
          this.health.set(e.error);
        } else {
          this.error.set('No se pudo contactar al servidor.');
        }
      },
    });
  }
}

import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, input, OnInit, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormArray, FormControl, FormGroup, NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatRadioModule } from '@angular/material/radio';
import { MatSelectModule } from '@angular/material/select';
import { Router, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';

import { ErrorApi } from '../../core/modelos';
import { erroresDeCampos, Notificador } from '../../core/notificador';
import { AdminApi } from '../admin-api';
import { EventoSeleccionado } from '../evento-seleccionado';
import {
  Autor, ESTADOS_PROYECTO, EstadoProyecto, GrupoAreas, MAX_AUTORES, Origen, ORIGENES, Proyecto, ProyectoEntrada,
  Tipo, TIPOS,
} from '../modelos';

const CEDULA = /^[0-9A-Za-z]{4,20}$/;

type AutorForm = FormGroup<{
  id: FormControl<number | null>;
  nombre_completo: FormControl<string>;
  cedula: FormControl<string>;
}>;

/** Registrar o editar un proyecto (RN-12 a RN-20). */
@Component({
  selector: 'app-proyecto-form',
  imports: [
    MatButtonModule, MatFormFieldModule, MatIconModule, MatInputModule, MatProgressBarModule, MatRadioModule,
    MatSelectModule, ReactiveFormsModule, RouterLink,
  ],
  templateUrl: './proyecto-form.html',
  styleUrl: './proyecto-form.scss',
})
export class ProyectoForm implements OnInit {
  /** Parámetro de ruta `:id` (ausente al registrar). */
  readonly id = input<string>();

  private readonly api = inject(AdminApi);
  private readonly router = inject(Router);
  private readonly notificador = inject(Notificador);
  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly sel = inject(EventoSeleccionado);

  protected readonly origenes = ORIGENES;
  protected readonly tipos = TIPOS;
  protected readonly estados = ESTADOS_PROYECTO;
  protected readonly maxAutores = MAX_AUTORES;

  protected readonly areas = signal<GrupoAreas[]>([]);
  protected readonly proyecto = signal<Proyecto | null>(null);
  protected readonly cargando = signal(true);
  protected readonly enviando = signal(false);
  protected readonly errores = signal<Record<string, string>>({});
  protected readonly erroresAutores = signal<Record<string, Record<string, string>>>({});

  protected readonly form = this.fb.group({
    evento: this.fb.control<number | null>(null, Validators.required),
    codigo: ['', Validators.required],
    titulo: ['', Validators.required],
    area: this.fb.control<number | null>(null, Validators.required),
    origen: this.fb.control<Origen | null>(null, Validators.required),
    estado: this.fb.control<EstadoProyecto | null>(null, Validators.required),
    tipo: this.fb.control<Tipo | null>(null, Validators.required),
    autores: this.fb.array<AutorForm>([]),
  });

  /** RN-20: con evaluaciones enviadas solo se corrigen código, título, área y datos de autores. */
  protected readonly bloqueado = computed(() => this.proyecto()?.tiene_evaluaciones ?? false);
  private readonly origen = toSignal(this.form.controls.origen.valueChanges, { initialValue: null });
  private readonly area = toSignal(this.form.controls.area.valueChanges, { initialValue: null });
  protected readonly esTrabajoGrado = computed(() => this.origen() === 'TRABAJO_GRADO');
  protected readonly programa = computed(() => {
    for (const g of this.areas()) if (g.areas.some((a) => a.id === this.area())) return g.programa_nombre;
    return '';
  });

  get autores(): FormArray<AutorForm> {
    return this.form.controls.autores;
  }

  ngOnInit(): void {
    const id = Number(this.id());
    forkJoin({
      areas: this.api.areas(),
      eventos: this.sel.cargar(),
      proyecto: id ? this.api.proyecto(id) : of(null),
    }).subscribe({
      next: ({ areas, proyecto }) => {
        this.areas.set(areas);
        if (proyecto) {
          this.proyecto.set(proyecto);
          this.cargarProyecto(proyecto);
        } else {
          this.form.controls.evento.setValue(this.sel.activo()?.id ?? this.sel.id());
          this.agregarAutor();
        }
        this.cargando.set(false);
      },
      error: () => void this.router.navigateByUrl('/admin/proyectos'),
    });

    // RN-17 en vivo: un trabajo de grado no puede estar en Propuesta.
    this.form.controls.origen.valueChanges.subscribe((origen) => {
      if (origen === 'TRABAJO_GRADO' && this.form.controls.estado.value === 'PROPUESTA') {
        this.form.controls.estado.setValue(null);
        this.form.controls.estado.markAsTouched();
      }
    });
  }

  private cargarProyecto(p: Proyecto): void {
    this.form.patchValue({
      evento: p.evento, codigo: p.codigo, titulo: p.titulo, area: p.area.id, origen: p.origen, estado: p.estado, tipo: p.tipo,
    });
    for (const a of p.autores) this.agregarAutor(a);
    if (p.tiene_evaluaciones) {
      for (const campo of ['evento', 'origen', 'estado', 'tipo'] as const) this.form.controls[campo].disable();
    }
  }

  protected agregarAutor(autor?: Autor): void {
    if (this.autores.length >= MAX_AUTORES) return;
    this.autores.push(
      this.fb.group({
        id: this.fb.control<number | null>(autor?.id ?? null),
        nombre_completo: [autor?.nombre_completo ?? '', Validators.required],
        cedula: [autor?.cedula ?? '', [Validators.required, Validators.pattern(CEDULA)]],
      }),
    );
  }

  protected quitarAutor(indice: number): void {
    if (this.autores.length > 1) this.autores.removeAt(indice);
  }

  protected guardar(otro = false): void {
    for (const a of this.autores.controls) {
      a.controls.cedula.setValue(a.controls.cedula.value.replace(/[.\s]/g, ''));
    }
    if (this.form.invalid || this.enviando()) {
      this.form.markAllAsTouched();
      this.notificador.error('Revise los campos marcados en rojo.');
      return;
    }
    this.enviando.set(true);
    this.errores.set({});
    this.erroresAutores.set({});
    const v = this.form.getRawValue();
    const datos: ProyectoEntrada = {
      evento: v.evento!, codigo: v.codigo.trim(), titulo: v.titulo.trim(), area: v.area!, origen: v.origen!,
      estado: v.estado!, tipo: v.tipo!,
      autores: v.autores.map((a) => ({
        ...(a.id ? { id: a.id } : {}), nombre_completo: a.nombre_completo.trim(), cedula: a.cedula.trim(),
      })),
    };
    const actual = this.proyecto();
    const peticion = actual ? this.api.editarProyecto(actual.id, datos) : this.api.crearProyecto(datos);
    peticion.subscribe({
      next: (p) => {
        this.notificador.exito(actual ? `Proyecto ${p.codigo} actualizado.` : `Proyecto ${p.codigo} registrado.`);
        if (otro) {
          this.enviando.set(false);
          this.form.reset({ evento: v.evento, area: v.area, origen: v.origen, estado: v.estado, tipo: v.tipo });
          this.autores.clear();
          this.agregarAutor();
          window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
          void this.router.navigateByUrl('/admin/proyectos');
        }
      },
      error: (e: unknown) => {
        this.enviando.set(false);
        this.mostrarErrores(e);
      },
    });
  }

  private mostrarErrores(e: unknown): void {
    this.errores.set(erroresDeCampos(e));
    const autores = e instanceof HttpErrorResponse ? (e.error as ErrorApi | null)?.campos?.['autores'] : null;
    if (autores && !Array.isArray(autores) && typeof autores === 'object') {
      const porFila: Record<string, Record<string, string>> = {};
      for (const [fila, campos] of Object.entries(autores as Record<string, Record<string, string[]>>)) {
        porFila[fila] = Object.fromEntries(Object.entries(campos).map(([c, m]) => [c, m.join(' ')]));
      }
      this.erroresAutores.set(porFila);
    }
  }
}

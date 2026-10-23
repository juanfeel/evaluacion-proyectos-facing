import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { EventoSeleccionado } from './evento-seleccionado';
import { Evento } from './modelos';

const evento = (id: number, activo = false): Evento => ({ id, nombre: `E${id}`, fecha: '2026-10-09', activo, num_proyectos: 0 });

describe('EventoSeleccionado', () => {
  let sel: EventoSeleccionado;
  let http: HttpTestingController;

  function cargar(lista: Evento[]) {
    sel.cargar().subscribe();
    http.expectOne('/api/admin/eventos/').flush(lista);
  }

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    sel = TestBed.inject(EventoSeleccionado);
    http = TestBed.inject(HttpTestingController);
  });

  it('por defecto muestra el evento activo', () => {
    cargar([evento(1), evento(2, true)]);
    expect(sel.id()).toBe(2);
    expect(sel.activo()?.id).toBe(2);
  });

  it('sin evento activo usa el primero de la lista', () => {
    cargar([evento(5), evento(7)]);
    expect(sel.id()).toBe(5);
  });

  it('recuerda el evento elegido', () => {
    cargar([evento(1), evento(2, true)]);
    sel.elegir(1);
    expect(sel.id()).toBe(1);
    expect(localStorage.getItem('evaluacion.admin.evento')).toBe('1');
  });

  it('si el evento recordado ya no existe vuelve al activo', () => {
    localStorage.setItem('evaluacion.admin.evento', '99');
    sel = TestBed.runInInjectionContext(() => new EventoSeleccionado());
    cargar([evento(3, true)]);
    expect(sel.id()).toBe(3);
  });

  it('sin eventos no hay selección', () => {
    cargar([]);
    expect(sel.id()).toBeNull();
    expect(sel.cargados()).toBe(true);
  });
});

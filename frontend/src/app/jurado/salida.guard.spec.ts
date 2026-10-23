import { Component, signal } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { Observable, of } from 'rxjs';

import { salirGuard } from '../core/guards';
import { ADMIN, iniciarSesionComo } from '../core/pruebas';
import { ConSalidaControlada, salidaGuard } from './salida.guard';

const respuesta = signal(false);

@Component({ template: 'formulario' })
class FormularioFalso implements ConSalidaControlada {
  puedeSalir(): Observable<boolean> {
    return of(respuesta());
  }
}

@Component({ template: 'otra' })
class Otra {}

describe('Salida con formulario a medio llenar', () => {
  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([
          { path: 'form', component: FormularioFalso, canDeactivate: [salidaGuard] },
          { path: 'otra', component: Otra },
          { path: 'salir', canActivate: [salirGuard], children: [] },
          { path: 'login', component: Otra },
        ]),
      ],
    });
  });

  it('si el usuario no confirma, se queda en el formulario', async () => {
    const harness = await RouterTestingHarness.create('/form');
    respuesta.set(false);
    await harness.navigateByUrl('/otra');
    expect(TestBed.inject(Router).url).toBe('/form');
  });

  it('si confirma, sale', async () => {
    const harness = await RouterTestingHarness.create('/form');
    respuesta.set(true);
    await harness.navigateByUrl('/otra');
    expect(TestBed.inject(Router).url).toBe('/otra');
  });

  it('«Salir» con formulario a medio llenar NO borra la sesión si el usuario decide seguir', async () => {
    iniciarSesionComo(ADMIN);
    const harness = await RouterTestingHarness.create('/form');
    respuesta.set(false);
    await harness.navigateByUrl('/salir');
    expect(TestBed.inject(Router).url).toBe('/form');
    expect(sessionStorage.getItem('evaluacion.access')).not.toBeNull();
  });

  it('«Salir» confirmado borra la sesión', async () => {
    iniciarSesionComo(ADMIN);
    const harness = await RouterTestingHarness.create('/form');
    respuesta.set(true);
    await harness.navigateByUrl('/salir');
    expect(TestBed.inject(Router).url).toBe('/login');
    expect(sessionStorage.getItem('evaluacion.access')).toBeNull();
  });
});

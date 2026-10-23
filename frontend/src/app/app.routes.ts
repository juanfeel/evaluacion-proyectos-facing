import { Routes } from '@angular/router';

import { authGuard, cambioPasswordGuard, inicioGuard, invitadoGuard, rolGuard, salirGuard } from './core/guards';
import { salidaGuard } from './jurado/salida.guard';

export const routes: Routes = [
  { path: '', pathMatch: 'full', canActivate: [inicioGuard], children: [] },
  { path: 'salir', canActivate: [salirGuard], children: [] },
  {
    path: 'login',
    canActivate: [invitadoGuard],
    title: 'Ingreso · Evaluación FACING',
    loadComponent: () => import('./auth/login/login').then((m) => m.Login),
  },
  {
    path: 'cambiar-password',
    canActivate: [authGuard],
    title: 'Cambiar contraseña · Evaluación FACING',
    loadComponent: () => import('./auth/cambiar-password/cambiar-password').then((m) => m.CambiarPassword),
  },
  {
    path: 'estado',
    title: 'Estado del sistema',
    loadComponent: () => import('./estado/estado').then((m) => m.Estado),
  },
  {
    path: 'admin',
    canActivate: [authGuard, cambioPasswordGuard, rolGuard('ADMIN')],
    title: 'Administración · Evaluación FACING',
    loadComponent: () => import('./admin/layout/admin-layout').then((m) => m.AdminLayout),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'inicio' },
      { path: 'inicio', loadComponent: () => import('./admin/inicio/inicio').then((m) => m.Inicio), data: { titulo: 'Inicio' } },
      { path: 'eventos', loadComponent: () => import('./admin/eventos/eventos').then((m) => m.Eventos), data: { titulo: 'Eventos' } },
      { path: 'docentes', loadComponent: () => import('./admin/docentes/docentes').then((m) => m.Docentes), data: { titulo: 'Docentes' } },
      { path: 'proyectos', loadComponent: () => import('./admin/proyectos/proyectos').then((m) => m.Proyectos), data: { titulo: 'Proyectos' } },
      {
        path: 'proyectos/nuevo',
        loadComponent: () => import('./admin/proyectos/proyecto-form').then((m) => m.ProyectoForm),
        data: { titulo: 'Proyectos · Registrar proyecto' },
      },
      {
        path: 'proyectos/:id',
        loadComponent: () => import('./admin/proyectos/proyecto-form').then((m) => m.ProyectoForm),
        data: { titulo: 'Proyectos · Editar proyecto' },
      },
      {
        path: 'asignaciones',
        loadComponent: () => import('./admin/asignaciones/asignaciones').then((m) => m.Asignaciones),
        data: { titulo: 'Asignaciones' },
      },
      {
        path: 'resultados',
        loadComponent: () => import('./admin/resultados/resultados').then((m) => m.Resultados),
        data: { titulo: 'Resultados' },
      },
    ],
  },
  {
    path: 'jurado',
    canActivate: [authGuard, cambioPasswordGuard, rolGuard('JURADO')],
    title: 'Jurado · Evaluación FACING',
    loadComponent: () => import('./jurado/layout/jurado-layout').then((m) => m.JuradoLayout),
    children: [
      {
        path: '',
        loadComponent: () => import('./jurado/mis-proyectos/mis-proyectos').then((m) => m.MisProyectos),
        data: { titulo: 'Mis proyectos' },
      },
      {
        path: 'evaluar/:id',
        loadComponent: () => import('./jurado/evaluar/evaluar').then((m) => m.Evaluar),
        canDeactivate: [salidaGuard],
        data: { titulo: 'Evaluar proyecto' },
      },
      {
        path: 'evaluacion/:id',
        loadComponent: () => import('./jurado/evaluacion/evaluacion-enviada').then((m) => m.EvaluacionEnviada),
        data: { titulo: 'Evaluación enviada' },
      },
    ],
  },
  { path: '**', redirectTo: '' },
];

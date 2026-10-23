export type Origen = 'SEMILLERO' | 'TRABAJO_GRADO';
export type Tipo = 'INV' | 'DTI';
export type EstadoProyecto = 'PROPUESTA' | 'EN_CURSO' | 'TERMINADO';
export type EstadoEvaluacion = 'SIN_JURADOS' | 'PENDIENTE' | 'PARCIAL' | 'EVALUADO';

export const ORIGENES: { valor: Origen; texto: string }[] = [
  { valor: 'SEMILLERO', texto: 'Semillero de investigación' },
  { valor: 'TRABAJO_GRADO', texto: 'Trabajo de grado' },
];
export const TIPOS: { valor: Tipo; texto: string }[] = [
  { valor: 'INV', texto: 'Investigación (INV)' },
  { valor: 'DTI', texto: 'Desarrollo Tecnológico y/o Innovación (DTI)' },
];
export const ESTADOS_PROYECTO: { valor: EstadoProyecto; texto: string }[] = [
  { valor: 'PROPUESTA', texto: 'Propuesta' },
  { valor: 'EN_CURSO', texto: 'En curso' },
  { valor: 'TERMINADO', texto: 'Terminado' },
];
export const ESTADOS_EVALUACION: { valor: EstadoEvaluacion; texto: string }[] = [
  { valor: 'SIN_JURADOS', texto: 'Sin jurados' },
  { valor: 'PENDIENTE', texto: 'Pendiente' },
  { valor: 'PARCIAL', texto: 'Parcial (1 de 2)' },
  { valor: 'EVALUADO', texto: 'Evaluado' },
];
export const MAX_AUTORES = 5;

/** Departamentos académicos permitidos (lista cerrada; la valida también el backend). */
export const DEPARTAMENTOS = ['Sistemas', 'Ingeniería Civil', 'Electrónica'] as const;

export interface Evento {
  id: number;
  nombre: string;
  fecha: string; // AAAA-MM-DD
  activo: boolean;
  num_proyectos: number;
}

export interface Area {
  id: number;
  nombre: string;
  programa: string;
  programa_nombre: string;
}

export interface GrupoAreas {
  programa: string;
  programa_nombre: string;
  areas: Area[];
}

export interface Docente {
  id: number;
  nombre_completo: string;
  cedula: string;
  email: string;
  departamento: string;
  debe_cambiar_password: boolean;
  asignados: number;
  max_asignaciones: number;
  tiene_evaluaciones: boolean;
}

export type DocenteEntrada = Pick<Docente, 'nombre_completo' | 'cedula' | 'email' | 'departamento'>;

export interface Autor {
  id?: number;
  nombre_completo: string;
  cedula: string;
  orden?: number;
}

export interface JuradoAsignado {
  asignacion_id: number;
  docente_id: number;
  nombre_completo: string;
  evaluada: boolean;
}

export interface Proyecto {
  id: number;
  evento: number;
  evento_nombre: string;
  codigo: string;
  titulo: string;
  area: Area;
  origen: Origen;
  origen_nombre: string;
  tipo: Tipo;
  tipo_nombre: string;
  estado: EstadoProyecto;
  estado_nombre: string;
  autores: Autor[];
  jurados: JuradoAsignado[];
  estado_evaluacion: EstadoEvaluacion;
  evaluaciones_enviadas: number;
  tiene_evaluaciones: boolean;
}

export interface ProyectoEntrada {
  evento: number;
  codigo: string;
  titulo: string;
  area: number;
  origen: Origen;
  tipo: Tipo;
  estado: EstadoProyecto;
  autores: Autor[];
}

export interface FiltrosProyectos {
  evento?: number | null;
  origen?: Origen | '';
  tipo?: Tipo | '';
  estado_evaluacion?: EstadoEvaluacion | '';
}

export interface Resumen {
  evento: { id: number; nombre: string; activo: boolean };
  total_proyectos: number;
  sin_jurados: number;
  pendientes: number;
  parciales: number;
  evaluados: number;
  evaluaciones_enviadas: number;
  evaluaciones_total: number;
}

export interface FilaResultado {
  proyecto_id: number;
  puesto: number | null;
  codigo: string;
  titulo: string;
  area: string;
  programa: string;
  estado: EstadoProyecto;
  nota_jurado_1: string | null;
  nota_jurado_2: string | null;
  promedio: string | null;
  pendiente: boolean;
  evaluaciones_enviadas: number;
  reconocimiento: boolean;
  mencion_meritoria: boolean;
  sin_sustentacion: boolean;
}

export interface TablaResultados {
  origen: Origen;
  tipo: Tipo;
  titulo: string;
  proyectos: FilaResultado[];
}

export interface Resultados {
  evento: { id: number; nombre: string };
  umbrales: { reconocimiento: string; mencion_meritoria: string };
  tablas: TablaResultados[];
}

export interface DetalleCriterio {
  criterio_id: number;
  orden: number;
  nombre_criterio: string;
  nivel: number;
  nivel_nombre: string;
  puntaje: number;
  puntaje_maximo: number;
}

export interface EvaluacionCompleta {
  id: number;
  asignacion_id: number;
  total: string;
  sin_sustentacion: boolean;
  fortalezas: string;
  aspectos_mejorar: string;
  enviada: string;
  detalles: DetalleCriterio[];
  asistencias: { autor_id: number; nombre_autor: string; asistio: boolean }[];
  jurado?: { id: number; nombre_completo: string; departamento: string; email: string };
  texto_umbrales: string;
}

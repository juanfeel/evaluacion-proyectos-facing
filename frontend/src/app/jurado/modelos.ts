export interface ProyectoJurado {
  codigo: string;
  titulo: string;
  origen: string;
  origen_nombre: string;
  tipo: 'INV' | 'DTI';
  tipo_nombre: string;
  estado: string;
  estado_nombre: string;
  area: string;
  programa: string;
}

export interface AsignacionJurado {
  id: number;
  proyecto: ProyectoJurado;
  evaluada: boolean;
  enviada: string | null;
}

export interface CriterioFormulario {
  id: number;
  orden: number;
  nombre: string;
  puntajes: number[];
  descriptores: string[];
}

export interface AutorJurado {
  id: number;
  nombre_completo: string;
  orden: number;
}

export interface Formulario {
  asignacion_id: number;
  evaluada: boolean;
  evento: { nombre: string; fecha: string }; // fecha AAAA-MM-DD
  proyecto: ProyectoJurado;
  autores: AutorJurado[];
  niveles: string[];
  criterios: CriterioFormulario[];
  nota_estado: string | null;
  asistencia_alguno: string;
  asistencia_ninguno: string;
  texto_umbrales: string;
}

export interface Evaluador {
  nombre_completo: string;
  departamento: string;
  email: string;
}

export interface EnvioEvaluacion {
  niveles: Record<string, number>;
  asistencia: Record<string, boolean>;
  fortalezas: string;
  aspectos_mejorar: string;
}

export interface EvaluacionPropia {
  id: number;
  asignacion_id: number;
  proyecto: ProyectoJurado;
  total: string;
  sin_sustentacion: boolean;
  fortalezas: string;
  aspectos_mejorar: string;
  enviada: string;
  detalles: {
    criterio_id: number;
    orden: number;
    nombre_criterio: string;
    nivel: number;
    nivel_nombre: string;
    puntaje: number;
    puntaje_maximo: number;
  }[];
  asistencias: { autor_id: number; nombre_autor: string; asistio: boolean }[];
  evaluador: Evaluador;
  texto_umbrales: string;
}

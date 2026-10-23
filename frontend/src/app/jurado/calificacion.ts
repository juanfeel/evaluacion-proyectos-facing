import { CriterioFormulario } from './modelos';

/** Criterio de Sustentación: queda en Insuficiente si ningún autor asistió (RN-33). */
export const ORDEN_SUSTENTACION = 7;
export const NIVEL_INSUFICIENTE = 0;

export type Niveles = Record<number, number | undefined>; // criterio_id → nivel 0..3
export type Asistencia = Record<number, boolean | undefined>; // autor_id → asistió

/** RN-33: solo cuando TODOS los autores tienen marca y todas son "No asistió". */
export function nadieAsistio(autores: { id: number }[], asistencia: Asistencia): boolean {
  return autores.length > 0 && autores.every((a) => asistencia[a.id] === false);
}

/** Niveles efectivos: con nadie presente, la sustentación se fuerza a Insuficiente. */
export function nivelesEfectivos(criterios: CriterioFormulario[], niveles: Niveles, sinSustentacion: boolean): Niveles {
  const resultado: Niveles = { ...niveles };
  if (sinSustentacion) {
    for (const c of criterios) if (c.orden === ORDEN_SUSTENTACION) resultado[c.id] = NIVEL_INSUFICIENTE;
  }
  return resultado;
}

/** Total en vivo, igual al que calcula el backend (RN-35): suma de los puntajes elegidos. */
export function totalEnVivo(criterios: CriterioFormulario[], niveles: Niveles): number {
  return criterios.reduce((suma, c) => {
    const nivel = niveles[c.id];
    return suma + (nivel === undefined ? 0 : c.puntajes[nivel]);
  }, 0);
}

export function puntajeMaximo(criterios: CriterioFormulario[]): number {
  return criterios.reduce((suma, c) => suma + c.puntajes[c.puntajes.length - 1], 0);
}

/** Lo que falta para poder enviar (RN-31 y RN-32). Vacío = listo. */
export function pendientes(
  criterios: CriterioFormulario[],
  autores: { id: number }[],
  niveles: Niveles,
  asistencia: Asistencia,
): { criterios: number[]; autores: number } {
  return {
    criterios: criterios.filter((c) => niveles[c.id] === undefined).map((c) => c.orden),
    autores: autores.filter((a) => asistencia[a.id] === undefined).length,
  };
}

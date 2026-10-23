import { nadieAsistio, nivelesEfectivos, pendientes, puntajeMaximo, totalEnVivo } from './calificacion';
import { CriterioFormulario } from './modelos';

// Puntajes reales de la rúbrica (iguales para INV y DTI).
const PUNTAJES = [[0, 5, 10, 15], [0, 5, 10, 15], [0, 7, 13, 20], [0, 3, 7, 10], [0, 3, 7, 10], [0, 5, 10, 15], [0, 5, 10, 15]];
const CRITERIOS: CriterioFormulario[] = PUNTAJES.map((puntajes, i) => ({
  id: 100 + i, orden: i + 1, nombre: `C${i + 1}`, puntajes, descriptores: ['a', 'b', 'c', 'd'],
}));
const AUTORES = [{ id: 1 }, { id: 2 }];
const todos = (nivel: number) => Object.fromEntries(CRITERIOS.map((c) => [c.id, nivel]));

describe('Calificación en vivo', () => {
  it('el máximo es 100 y el mínimo 0', () => {
    expect(puntajeMaximo(CRITERIOS)).toBe(100);
    expect(totalEnVivo(CRITERIOS, todos(3))).toBe(100);
    expect(totalEnVivo(CRITERIOS, todos(0))).toBe(0);
  });

  it('suma los puntajes del nivel elegido en cada criterio (igual que el backend)', () => {
    expect(totalEnVivo(CRITERIOS, todos(2))).toBe(67);
    expect(totalEnVivo(CRITERIOS, todos(1))).toBe(33);
    const mixto = { 100: 3, 101: 2, 102: 1, 103: 0, 104: 3, 105: 2, 106: 1 };
    expect(totalEnVivo(CRITERIOS, mixto)).toBe(15 + 10 + 7 + 0 + 10 + 10 + 5);
  });

  it('los criterios sin elegir no suman', () => {
    expect(totalEnVivo(CRITERIOS, { 100: 3 })).toBe(15);
    expect(totalEnVivo(CRITERIOS, {})).toBe(0);
  });

  it('RN-33: nadie asistió solo si todos tienen marca "No asistió"', () => {
    expect(nadieAsistio(AUTORES, { 1: false, 2: false })).toBe(true);
    expect(nadieAsistio(AUTORES, { 1: false, 2: true })).toBe(false);
    expect(nadieAsistio(AUTORES, { 1: false })).toBe(false); // falta marcar uno
    expect(nadieAsistio([], {})).toBe(false);
  });

  it('RN-33: sin sustentación el criterio 7 queda en Insuficiente y el total máximo es 85', () => {
    const efectivos = nivelesEfectivos(CRITERIOS, todos(3), true);
    expect(efectivos[106]).toBe(0);
    expect(totalEnVivo(CRITERIOS, efectivos)).toBe(85);
    expect(nivelesEfectivos(CRITERIOS, todos(3), false)[106]).toBe(3);
  });

  it('RN-33: con nadie presente el criterio 7 cuenta como elegido', () => {
    const niveles = { ...todos(2) };
    delete niveles[106];
    const efectivos = nivelesEfectivos(CRITERIOS, niveles, true);
    expect(pendientes(CRITERIOS, AUTORES, efectivos, { 1: false, 2: false })).toEqual({ criterios: [], autores: 0 });
  });

  it('indica qué falta para poder enviar', () => {
    expect(pendientes(CRITERIOS, AUTORES, { 100: 1, 102: 2 }, { 1: true })).toEqual({
      criterios: [2, 4, 5, 6, 7],
      autores: 1,
    });
    expect(pendientes(CRITERIOS, AUTORES, todos(1), { 1: true, 2: false })).toEqual({ criterios: [], autores: 0 });
  });
});

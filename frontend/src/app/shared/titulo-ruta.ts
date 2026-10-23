import { inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router } from '@angular/router';
import { filter, map } from 'rxjs';

/**
 * Título de la sección actual: `data.titulo` de la ruta activa más profunda.
 * Se lee del estado del router (no del ActivatedRoute del layout), porque mientras el layout
 * se construye la ruta hija todavía no está activada.
 */
export function tituloDeRuta() {
  const router = inject(Router);
  const leer = () => {
    let actual = router.routerState.snapshot.root;
    while (actual.firstChild) actual = actual.firstChild;
    return (actual.data['titulo'] as string | undefined) ?? '';
  };
  return toSignal(router.events.pipe(filter((e) => e instanceof NavigationEnd), map(leer)), { initialValue: leer() });
}

# Evaluación de Proyectos · FACING · Udenar

Aplicación web con la que se evaluaron los proyectos del **I Encuentro de Semilleros de Investigación y Trabajos de
Grado** de la Facultad de Ingeniería de la Universidad de Nariño (9 de octubre de 2026). Se usó en producción el día
del evento: los jurados calificaron los pósteres desde su celular y el administrador obtuvo los rankings al instante.

## Qué hace

- **Administrador:** registra el evento, los docentes y los proyectos con sus autores; asigna dos jurados por
  proyecto y ve un tablero de avance y cuatro rankings (Semillero / Trabajo de grado × Investigación / DTI) con
  empates, promedios y reconocimientos.
- **Jurado:** entra con su correo institucional, cambia la contraseña inicial y califica cada proyecto con la rúbrica
  oficial que corresponde a su tipo y estado, marcando la asistencia de los ponentes. La evaluación enviada es
  definitiva.
- **Reglas de negocio garantizadas en el backend** (más de 40, cada una con pruebas): parejas de jurados, máximo 3
  proyectos por docente con bloqueo transaccional, puntaje calculado en el servidor, «sin sustentación» automático,
  envíos idempotentes.

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · Django 5.2 · Django REST Framework · JWT (simplejwt) · django-axes |
| Frontend | Angular (standalone + signals) · Angular Material · diseño mobile-first |
| Datos | PostgreSQL (Neon) |
| Despliegue | Vercel (Django como funciones serverless + Angular estático con rewrite `/api`) |
| Pruebas | pytest · factory-boy (≈280 pruebas) · pruebas unitarias de Angular · Playwright (humo E2E) |

La especificación completa (reglas de negocio, modelo de datos, API y fases) está en [CLAUDE.md](CLAUDE.md), el
documento que guió el desarrollo asistido con Claude Code.

## Licencia

[MIT](LICENSE).

## Fuente de la rúbrica

Los formularios de evaluación siguen los anexos oficiales, guardados en [`docs/anexos/`](docs/anexos/):

- [Anexo 6 · Evaluación de proyectos de Investigación](docs/anexos/Anexo_6_evaluacion_investigacion.docx)
- [Anexo 7 · Evaluación de proyectos de Desarrollo Tecnológico y/o Innovación](docs/anexos/Anexo_7_evaluacion_dti.docx)

Su contenido está transcrito en `backend/evaluaciones/data/rubricas.yaml` (y en la sección 6 de `CLAUDE.md`).
`backend/tests/test_rubrica_anexos.py` verifica, a través de la API, las 6 variantes (INV y DTI × Terminado,
Propuesta y En curso). Para cambiar un texto: editar el YAML y la sección 6 de `CLAUDE.md` y crear una
**migración de datos nueva** (ver `0004_rubricas_anexos_actualizados.py`); las evaluaciones ya enviadas no cambian.

## Estructura

- `backend/`: Django 5.2 + Django REST Framework (Python 3.12).
- `frontend/`: Angular (standalone + signals).

## Desarrollo local

### Requisitos
- [uv](https://docs.astral.sh/uv/) (instala Python 3.12 automáticamente)
- Node 20+ y Angular CLI
- Docker (para PostgreSQL local)

### Backend
```bash
cd backend
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
cp .env.example .env              # ajustar si hace falta
docker compose up -d              # PostgreSQL en localhost:5433
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 8000
```

Pruebas:
```bash
cd backend && .venv/bin/pytest
```

### Frontend
```bash
cd frontend
npm install
npm start                         # http://localhost:4200, /api se reenvía a :8000 (proxy.conf.json)
npx ng test --watch=false
npx ng build
```

Presupuesto del bundle inicial: 700 kB (advertencia) / 1 MB (error) en `angular.json`. Angular Material
(snackbar, overlay) forma parte del arranque porque cualquier error de la API se muestra desde la primera
pantalla; transferido con compresión pesa ~130 kB.

## Despliegue en Vercel

Arquitectura: el frontend reenvía `/api/*` al backend con un *rewrite* de Vercel (mismo dominio para el navegador: sin CORS).

### 1. Base de datos Neon
1. En Vercel: **Storage → Create Database → Neon** (Marketplace). Elegir la región más cercana (p. ej. `Washington, D.C. (iad1)` / `us-east-1`).
2. Anotar las dos cadenas de conexión:
   - **Pooled** (el host contiene `-pooler`): la usa la aplicación.
   - **Directa** (sin `-pooler`): solo para migraciones y respaldos desde la máquina local.

### 2. Proyecto del backend
1. **Add New → Project**, importar el repositorio, **Root Directory = `backend`**. Vercel detecta Django por `manage.py`.
2. Variables de entorno (Settings → Environment Variables):
   | Variable | Valor |
   |---|---|
   | `DJANGO_SECRET_KEY` | cadena aleatoria larga (`python3 -c 'import secrets;print(secrets.token_urlsafe(50))'`) |
   | `DATABASE_URL` | cadena **pooled** de Neon |
   | `DJANGO_DEBUG` | `False` |
   | `DJANGO_ALLOWED_HOSTS` | `<backend>.vercel.app` |
3. **Settings → Functions → Function Region**: la misma región de Neon.
4. Si la integración con Neon creó automáticamente `DATABASE_URL`, verificar que sea la pooled.
5. Si el frontend recibe 401 o una página de login de Vercel al llamar `/api`, desactivar **Deployment Protection** del proyecto backend (Settings → Deployment Protection) al menos para producción.

### 3. Proyecto del frontend
1. **Add New → Project**, mismo repositorio, **Root Directory = `frontend`**, preset **Angular**.
2. `frontend/vercel.json` ya apunta al backend con `"/api/(.*)" → ".../api/$1"` (no usar `:path*`: pierde la barra
   final que exigen todas las rutas) y fija `"outputDirectory": "dist/frontend/browser"`. La regla de `/api` va
   **antes** del fallback a `index.html`.
3. Desplegar y abrir `https://<frontend>.vercel.app`: debe mostrar `db: true`.

Cada `git push` a `main` despliega los dos proyectos.

## Operación (comandos contra producción, desde la máquina local)

Todos los comandos de esta sección se ejecutan en `backend/` con la cadena **directa** de Neon y
`DJANGO_DEBUG=False` (con `True`, que es lo del `.env` local, se crearían en producción las tablas del admin de Django).
Se recomienda guardar la cadena en `backend/env.prod` (ignorado por git) y cargarla así:
```bash
cd backend
export DATABASE_URL="$(sed -n 's/^DATABASE_URL=//p' env.prod | tr -d "\"'")"   # la URL contiene &
export DJANGO_DEBUG=False DJANGO_SECRET_KEY=solo-para-mantenimiento
# … comandos …
unset DATABASE_URL DJANGO_DEBUG DJANGO_SECRET_KEY   # al terminar, para no tocar producción por error
```

### Migraciones
Las migraciones **no** se ejecutan en el build. Antes de migrar, hacer un respaldo (ver abajo).
```bash
.venv/bin/python manage.py migrate --plan   # qué se aplicaría
.venv/bin/python manage.py migrate          # esquema + áreas + rúbricas (migraciones de datos)
```

### Crear el administrador
```bash
.venv/bin/python manage.py crear_admin      # pide correo, nombre y contraseña (oculta)
```

### Restablecer la contraseña de un docente / desbloquearlo
- **Desde el panel** (lo normal el día del evento): *Docentes* → ícono de llave → *Restablecer*. La contraseña vuelve a
  ser la cédula, el docente debe cambiarla al entrar y, si estaba bloqueado por intentos fallidos, queda desbloqueado.
- **Desde la terminal**, solo desbloquear (5 intentos fallidos bloquean correo + IP durante 15 minutos):
  ```bash
  .venv/bin/python manage.py axes_reset_username correo@udenar.edu.co
  ```

### Respaldo y restauración
No se necesita `pg_dump` instalado: se usa la imagen de Docker de la **misma versión mayor que Neon (PostgreSQL 18)**.
Los respaldos quedan en `backend/respaldos/`, que git ignora: **contienen cédulas y correos (Ley 1581); no compartirlos**.
```bash
cd backend
export NEON_URL="$(sed -n 's/^DATABASE_URL=//p' env.prod | tr -d "\"'")"
docker run --rm -e NEON_URL -v "$PWD/respaldos:/respaldos" postgres:18-alpine \
  sh -c 'pg_dump --format=custom --no-owner --no-privileges --dbname="$NEON_URL" --file=/respaldos/neon-$(date +%Y%m%d-%H%M).dump'
unset NEON_URL
```
Probar que el respaldo se puede restaurar (en un PostgreSQL temporal, sin tocar producción):
```bash
docker run -d --name restauracion-prueba -e POSTGRES_PASSWORD=prueba -e POSTGRES_DB=restaurada \
  -v "$PWD/respaldos:/respaldos:ro" postgres:18-alpine
# esperar a que termine de iniciar (docker logs restauracion-prueba → "PostgreSQL init process complete")
docker exec restauracion-prueba pg_restore --no-owner --no-privileges -U postgres -d restaurada /respaldos/<archivo>.dump
docker exec restauracion-prueba psql -U postgres -d restaurada -c "select count(*) from evaluaciones_evaluacion"
docker rm -f restauracion-prueba
```
Restaurar **sobre Neon** (solo ante una pérdida de datos): crear antes una **rama** en la consola de Neon
(*Branches → Create branch*) como red de seguridad y luego
`pg_restore --clean --if-exists --no-owner --no-privileges --dbname="$NEON_URL" /respaldos/<archivo>.dump`
con la misma imagen de Docker.

### Borrar los datos de prueba antes de la carga real
```bash
.venv/bin/python manage.py preparar_carga_real              # simulación: muestra lo que borraría
.venv/bin/python manage.py preparar_carga_real --confirmar  # borra eventos, proyectos, evaluaciones y jurados
```
Conserva los administradores, las áreas y la rúbrica. Hacer un respaldo antes.

> ⚠️ **Ya se ejecutó el 6 de octubre de 2026** y la base quedó lista. Desde que empezó la carga de docentes y
> proyectos **oficiales**, **no** volver a ejecutar este comando: borra todo, incluidos los datos reales.

## Pruebas de humo contra producción (Playwright)
`frontend/e2e/humo.e2e.ts`: (1) el admin entra, registra 2 docentes y un proyecto `HUMO-<sello>` y le asigna los
dos jurados; (2) un jurado entra en celular con su cédula, cambia la contraseña y envía una evaluación; (3) el admin
la ve en Resultados. Requiere un evento activo. Las credenciales van solo por variables de entorno:
```bash
cd frontend
npx playwright install chromium     # la primera vez
E2E_URL=https://<frontend>.vercel.app E2E_ADMIN_EMAIL=... E2E_ADMIN_PASSWORD=... npm run e2e    # sin E2E_URL usa http://localhost:4200
```
Después, borrar los datos `HUMO-…` desde el panel (Asignaciones → *Quitar ambos* no aplica si ya evaluaron), o con
`preparar_carga_real` si todavía no hay datos reales.

## Día del evento (9 de octubre)
1. **Carga oficial** (desde el panel): evento (activarlo) → docentes → proyectos → asignaciones (los dos jurados
   juntos). Revisar en *Inicio* que **Sin jurados = 0** y hacer un **respaldo** con los datos reales.
2. **Pruebas, si hacen falta**: solo con valores genéricos que no se confundan con los oficiales (p. ej. código
   `PRUEBA-01`, docentes `prueba1@udenar.edu.co`) y, preferiblemente, en **otro evento**. Ojo: activar el evento de
   prueba **oculta** el oficial a los jurados (RN-03); al terminar, volver a activar el oficial. Una evaluación de
   prueba es definitiva y deja su proyecto sin poder eliminarse (RN-21): mejor no evaluar proyectos oficiales.
3. **Antes de abrir**: entrar al panel unos minutos antes de que lleguen los jurados. El plan gratuito de Neon
   suspende la base tras unos minutos sin uso y el primer acceso tarda ~2 s; después responde en ~0,4 s
   (medido con 48 accesos simultáneos el 6 de octubre).
4. **Durante el evento**: *Inicio* muestra cuántos proyectos faltan por evaluar. Un jurado que olvidó su contraseña
   o quedó bloqueado → *Docentes* → ícono de llave → *Restablecer contraseña* (vuelve a ser su cédula y queda
   desbloqueado). La sesión dura hasta 12 horas o hasta cerrar la pestaña.
5. **Al cerrar**: respaldo final; resultados en *Resultados* (4 tablas; clic en una fila para ver las dos
   evaluaciones completas).

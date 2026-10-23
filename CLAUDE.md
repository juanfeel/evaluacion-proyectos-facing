# CLAUDE.md — Software de Evaluación de Proyectos (FACING · Udenar)

> Documento maestro del proyecto. Léelo completo antes de escribir código y vuelve a él al iniciar cada fase.
> Si algo de este documento contradice una petición del usuario en el chat, manda la petición del usuario; si contradice tu intuición, manda este documento.

---

## 0. Contexto

Aplicación web para el **I Encuentro de Semilleros de Investigación y Trabajos de Grado** de la Facultad de Ingeniería de la Universidad de Nariño (FACING).

- Un **administrador** registra el evento, los docentes, los proyectos con sus autores y asigna **2 jurados** a cada proyecto.
- Cada **docente (jurado)** inicia sesión, ve los proyectos que tiene asignados y los califica con la rúbrica que corresponde al **tipo** del proyecto.
- El sistema promedia las dos calificaciones y muestra al admin **4 rankings** (origen × tipo), de mayor a menor.

**Fecha del evento: 9 de octubre de 2026.** El sistema debe estar en producción, probado y con datos reales cargados el **8 de octubre**. Volumen esperado: ~24 proyectos y ~24 docentes (≈48 evaluaciones). La evaluación se hace **en el celular del jurado**, de pie, frente al póster, en el Hall del Bloque 6.

Prioridad absoluta: **funcional y confiable**. Seguro, sí; sofisticado, no.

---

## 1. Reglas de trabajo para Claude Code

1. Trabaja **fase por fase** en el orden de la sección 11. No empieces una fase sin que la anterior cumpla todos sus criterios de salida.
2. Al terminar cada fase: ejecuta las pruebas, muestra el resultado y un resumen corto de lo hecho, y **espera la confirmación del usuario** antes de pasar a la siguiente.
3. Nunca avances con pruebas fallando ni las desactives para que pasen.
4. **Ediciones mínimas**: cuando modifiques un archivo existente, cambia solo lo necesario. No reescribas ni recortes archivos enteros para hacer un cambio pequeño.
5. **No agregues funcionalidades fuera del alcance** (sección 13). Si algo parece necesario y no está aquí, pregunta.
6. Ante una ambigüedad de negocio, **pregunta** en lugar de suponer. Las dudas ya conocidas están en la sección 14.
7. Un commit por fase como mínimo, con mensaje en español: `fase N: descripción`.
8. Toda la interfaz de usuario, los mensajes de error de la API y los textos van **en español**.
9. Los modelos de dominio usan nombres en español (Evento, Proyecto, Autor, Asignacion, Evaluacion…). El resto sigue las convenciones de Python y TypeScript.
10. Nunca subas secretos al repositorio. Usa `.env` local (en `.gitignore`) y variables de entorno en Vercel.

---

## 2. Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · Django 5.2 LTS · Django REST Framework · djangorestframework-simplejwt · django-axes · dj-database-url · psycopg 3 |
| Frontend | Angular (última versión estable) con componentes standalone y signals · Angular Material · SCSS |
| Base de datos | PostgreSQL en **Neon** (plan gratuito, integración con Vercel Marketplace) |
| Despliegue | **Vercel**: dos proyectos desde el mismo repositorio (backend Django y frontend Angular) |
| Pruebas backend | pytest · pytest-django · factory-boy |
| Pruebas frontend | Pruebas unitarias del CLI de Angular · Playwright para humo E2E (fase 9) |

### Arquitectura de despliegue

```
Navegador ──► frontend.vercel.app (Angular estático, CDN)
                 │
                 └── /api/*  ──(rewrite de Vercel, proxy)──►  backend.vercel.app/api/*  (Django, Vercel Functions)
                                                                        │
                                                                        └──► Neon PostgreSQL (conexión pooled)
```

- El frontend reenvía `/api/*` al backend mediante un **rewrite** en su `vercel.json`. Para el navegador todo es el mismo dominio: **no hay CORS**.
- Autenticación con **JWT en el encabezado `Authorization`** (no cookies), así que no hay CSRF que manejar.
- En desarrollo local, Angular usa `proxy.conf.json` para enviar `/api` a `http://localhost:8000`.

### Restricciones del entorno serverless (obligatorias)

- Django corre como función; **no escribas en disco** ni dependas de memoria compartida entre peticiones.
- **No uses caché en memoria** (locmem) para nada que deba compartirse. El bloqueo de intentos de login lo hace django-axes **en la base de datos**.
- `DATABASE_URL` en producción es la cadena **pooled** de Neon; usa `CONN_MAX_AGE=0`.
- Las **migraciones no se ejecutan en el build**. Se ejecutan desde la máquina local contra la cadena **directa** (no pooled) de Neon: `DATABASE_URL=<directa> python manage.py migrate`.
- La región de las funciones de Vercel debe coincidir con la región de Neon.

---

## 3. Estructura del repositorio

```
/
├── CLAUDE.md
├── README.md                 # cómo correr local, desplegar, migrar, respaldar y operar el día del evento
├── docs/anexos/              # Anexo 6 (INV) y Anexo 7 (DTI): fuente oficial de la rúbrica
├── backend/
│   ├── manage.py
│   ├── .python-version       # 3.12
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── config/               # settings.py, urls.py, wsgi.py
│   ├── core/                 # usuarios, auth, permisos
│   ├── evaluaciones/         # eventos, áreas, proyectos, autores, asignaciones, rúbricas, evaluaciones, resultados
│   │   ├── models.py
│   │   ├── services.py       # TODA la lógica de negocio va aquí, no en vistas ni serializers
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── data/rubricas.yaml
│   │   └── migrations/       # incluye migración de datos con áreas y rúbricas
│   ├── tests/
│   └── respaldos/            # volcados de Neon (ignorados por git: contienen datos personales)
└── frontend/
    ├── vercel.json           # rewrites /api y fallback SPA
    ├── proxy.conf.json
    ├── playwright.config.ts  # pruebas de humo contra producción (e2e/humo.e2e.ts)
    └── src/app/
        ├── core/             # auth service, interceptor, guards, modelos TS
        ├── shared/           # componentes reutilizables (confirm dialog, estado chip, etc.)
        ├── auth/             # login, cambiar contraseña
        ├── admin/            # panel del administrador
        └── jurado/           # vistas del jurado (mobile-first)
```

---

## 4. Roles y reglas de negocio

### Roles

- **ADMIN**: gestiona todo. Se crea con un comando de gestión (`python manage.py crear_admin`), no desde la interfaz.
- **JURADO**: docente evaluador. Lo registra el admin.

### Reglas de negocio (RN)

Cada regla debe estar garantizada **en el backend** (servicio + restricción de base de datos cuando aplique) y cubierta por al menos una prueba. El frontend solo las refleja.

**Eventos**
- RN-01. Todo proyecto pertenece a un evento. El admin crea los eventos.
- RN-02. Solo puede haber **un evento activo** a la vez. Activar uno desactiva los demás.
- RN-03. El jurado solo ve asignaciones de proyectos del **evento activo**.

**Docentes**
- RN-04. El admin registra al docente con: nombre completo, cédula, correo institucional y departamento académico. El departamento se elige de una lista cerrada: **Sistemas**, **Ingeniería Civil** o **Electrónica**.
- RN-05. El **correo institucional es el usuario** de inicio de sesión. Correo y cédula son únicos.
- RN-06. La **contraseña inicial es la cédula del docente**. Al crearlo, el sistema la asigna automáticamente y marca `debe_cambiar_password = True`.
- RN-07. Mientras `debe_cambiar_password` sea verdadero, la API rechaza toda petición excepto `me`, `cambiar-password` y `refresh` (403 con `codigo: "CAMBIO_PASSWORD_REQUERIDO"`).
- RN-08. La nueva contraseña debe pasar los validadores de Django (mínimo 8 caracteres, no demasiado común, no solo numérica) y **no puede ser igual a la cédula**.
- RN-09. El admin puede **restablecer** la contraseña de un docente: vuelve a ser la cédula y se reactiva `debe_cambiar_password`. (Soporte el día del evento.)
- RN-10. Editar la cédula de un docente no cambia su contraseña.
- RN-11. No se puede eliminar un docente que tenga evaluaciones enviadas. Si tiene asignaciones pendientes, primero hay que reemplazarlo (o quitar los jurados de esos proyectos), para no dejar proyectos con un solo jurado.

**Proyectos**
- RN-12. Datos del proyecto (todos los llena el admin): código (texto libre), título, área de conocimiento, origen, tipo y estado del proyecto.
- RN-13. El código es único dentro del evento.
- RN-14. **Origen**: `SEMILLERO` (Semillero de investigación) o `TRABAJO_GRADO` (Trabajo de grado).
- RN-15. **Tipo**: `INV` (Investigación) o `DTI` (Desarrollo Tecnológico y/o Innovación). El tipo determina la rúbrica.
- RN-16. **Estado del proyecto**: `PROPUESTA`, `EN_CURSO` o `TERMINADO`. Lo registra el admin y ajusta los textos de la rúbrica.
- RN-17. Un proyecto de origen `TRABAJO_GRADO` **no puede** estar en estado `PROPUESTA`.
- RN-18. El programa académico se **deriva del área**; no se guarda en el proyecto.
- RN-19. Cada proyecto tiene **entre 1 y 5 autores**, cada uno con nombre completo y cédula. Solo el admin los registra y edita.
- RN-20. Solo el admin puede editar un proyecto. Cuando el proyecto ya tiene al menos una evaluación enviada: **no** se pueden cambiar evento, tipo ni estado, **ni** agregar o eliminar autores; **sí** se pueden corregir código, título, área y el nombre o cédula de los autores.
- RN-21. No se puede eliminar un proyecto con evaluaciones enviadas.

**Estado de evaluación (calculado, nunca editable)**
- RN-22. `SIN_JURADOS` (menos de 2 asignados) · `PENDIENTE` (2 asignados, 0 evaluaciones) · `PARCIAL` (1 de 2) · `EVALUADO` (2 de 2).

**Asignaciones**
- RN-23. Cada proyecto tiene **0 o 2 jurados, nunca 1 ni más de 2**. Los dos se asignan **juntos** en una sola operación (para evitar olvidos del admin); un jurado sin evaluación se puede **reemplazar** por otro en un solo paso; y los dos se **quitan juntos**.
- RN-24. Cada docente puede tener **máximo 3 proyectos asignados por evento**.
- RN-25. Un docente no puede estar asignado dos veces al mismo proyecto.
- RN-26. No se puede reemplazar a un jurado que ya envió su evaluación, ni quitar los jurados de un proyecto si alguno ya evaluó.
- RN-27. RN-23 a RN-25 se validan dentro de una transacción con `select_for_update` para que dos peticiones simultáneas no las rompan.
- RN-28. En la primera versión **no** se verifican conflictos de interés (el sistema no conoce a los asesores).

**Evaluación**
- RN-29. Un jurado solo puede ver y evaluar **sus propias** asignaciones. Si pide una ajena, recibe 404.
- RN-30. El formulario se arma con la rúbrica del **tipo** del proyecto y los textos ajustados a su **estado** (sección 6).
- RN-31. El jurado elige **un nivel** (Insuficiente, Básico, Bueno o Sobresaliente) en cada uno de los 7 criterios. Los 7 son obligatorios. El jurado **no escribe números**.
- RN-32. El jurado marca **asistió / no asistió** por cada autor del proyecto. Todas las marcas son obligatorias.
- RN-33. Si **ningún autor asistió**, el criterio 7 (Sustentación) queda forzado en nivel Insuficiente (0 puntos), aunque el cliente envíe otro valor. La evaluación queda marcada `sin_sustentacion = True`.
- RN-34. Observaciones: dos campos de texto, **Fortalezas del proyecto** y **Aspectos por mejorar** (ver sección 14 sobre obligatoriedad).
- RN-35. El total es la suma de los 7 puntajes (0–100) y **lo calcula el backend**; se ignora cualquier total enviado por el cliente.
- RN-36. Una evaluación enviada es **definitiva**: no existe endpoint de edición ni de borrado para el jurado. Restricción `OneToOne` con la asignación.
- RN-37. Antes de enviar, el frontend muestra un diálogo que advierte que la calificación **no es editable**, con botones **Confirmar envío** y **Cancelar**. Al confirmar, se muestra un indicador de carga hasta que responde el servidor.
- RN-38. Enviar dos veces (doble clic, reintento de red) no crea dos evaluaciones: la segunda responde 409 y el frontend muestra la evaluación ya registrada.
- RN-39. La evaluación guarda una **copia** del nombre del criterio, el nivel y el puntaje elegidos, para que un cambio futuro de la rúbrica no altere evaluaciones pasadas.
- RN-40. Un jurado no ve la calificación del otro jurado.

**Resultados**
- RN-41. Solo el admin ve los resultados.
- RN-42. Calificación final del proyecto = **promedio de las 2 evaluaciones**, con 2 decimales (`Decimal`, redondeo `ROUND_HALF_UP`).
- RN-43. Con menos de 2 evaluaciones, el proyecto aparece como **"Pendiente"**, sin puesto, al final de su tabla.
- RN-44. Hay **4 tablas separadas**: Semillero·INV, Semillero·DTI, Trabajo de grado·INV, Trabajo de grado·DTI. No se implementa la unificación por baja inscripción.
- RN-45. Cada tabla se ordena de **mayor a menor**. Los **empates comparten puesto** y el siguiente salta (1, 1, 3).
- RN-46. Indicadores por proyecto: **Reconocimiento** si promedio ≥ 80 y no está sin sustentación · **Mención meritoria** si promedio ≥ 85 y no está sin sustentación (confirmado por el usuario: sin sustentación el proyecto "no aspira a reconocimientos", conserva su puesto) · **Sin sustentación** si alguna de sus evaluaciones tiene `sin_sustentacion = True`.
- RN-47. El admin puede abrir el detalle de un proyecto evaluado y ver ambas evaluaciones completas (niveles, asistencia, observaciones, jurado).

---

## 5. Modelo de datos

```
Usuario (AbstractUser personalizado; USERNAME_FIELD = email)
  email               EmailField, único
  nombre_completo     CharField
  cedula              CharField, único
  departamento        CharField            # Sistemas | Ingeniería Civil | Electrónica (vacío solo para el admin)
  rol                 ADMIN | JURADO
  debe_cambiar_password  Boolean (default True)

Evento
  nombre              CharField
  fecha               DateField
  activo              Boolean              # UniqueConstraint condicional: solo uno con activo=True

AreaConocimiento
  programa            IS | IE | IC         # Ing. de Sistemas | Ing. Electrónica | Ing. Civil
  nombre              CharField
  unique (programa, nombre)

Proyecto
  evento              FK Evento (PROTECT)
  codigo              CharField            # unique (evento, codigo)
  titulo              CharField
  area                FK AreaConocimiento (PROTECT)
  origen              SEMILLERO | TRABAJO_GRADO
  tipo                INV | DTI
  estado              PROPUESTA | EN_CURSO | TERMINADO
  creado / actualizado
  CheckConstraint: NOT (origen = TRABAJO_GRADO AND estado = PROPUESTA)

Autor
  proyecto            FK Proyecto (CASCADE)
  nombre_completo     CharField
  cedula              CharField
  orden               PositiveSmallInteger
  unique (proyecto, cedula)

Asignacion
  proyecto            FK Proyecto (PROTECT)
  docente             FK Usuario (PROTECT)
  creada              DateTime
  unique (proyecto, docente)

Criterio                                   # rúbrica, cargada por migración de datos
  tipo                INV | DTI
  orden               1..7
  puntajes            JSON [p0, p1, p2, p3]   # Insuficiente, Básico, Bueno, Sobresaliente
  unique (tipo, orden)

DescriptorCriterio
  criterio            FK Criterio
  estado              BASE | PROPUESTA | EN_CURSO
  nombre              CharField            # rótulo del criterio para ese estado
  descriptores        JSON [d0, d1, d2, d3]
  unique (criterio, estado)
  # Resolución: se usa el descriptor del estado del proyecto si existe; si no, BASE.

Evaluacion
  asignacion          OneToOne Asignacion (PROTECT)
  total               Decimal(5,2)
  sin_sustentacion    Boolean
  fortalezas          TextField
  aspectos_mejorar    TextField
  enviada             DateTime

DetalleEvaluacion
  evaluacion          FK Evaluacion (CASCADE)
  criterio            FK Criterio (PROTECT)
  nivel               0..3
  puntaje             PositiveSmallInteger   # copia
  nombre_criterio     CharField              # copia
  unique (evaluacion, criterio)

Asistencia
  evaluacion          FK Evaluacion (CASCADE)
  autor               FK Autor (PROTECT)
  nombre_autor        CharField              # copia
  asistio             Boolean
  unique (evaluacion, autor)
```

### Catálogo de áreas (migración de datos, esta versión)

| Programa | Áreas |
|---|---|
| IS — Ingeniería de Sistemas | Ingeniería de software · Redes y telemática · Seguridad informática · RV/RA · Ciencia de datos e IA |
| IE — Ingeniería Electrónica | Control y automatización |
| IC — Ingeniería Civil | Vías, transporte y movilidad · Geotecnia |

---

## 6. Rúbricas (fuente de verdad)

Fuente oficial: `docs/anexos/` (Anexo 6 · Investigación y Anexo 7 · DTI, versión actualizada). Guardar este contenido en `backend/evaluaciones/data/rubricas.yaml` y cargarlo con una **migración de datos**. Los textos van **exactamente** como están aquí.

Niveles, en orden: `Insuficiente`, `Básico`, `Bueno`, `Sobresaliente`.

Pruebas obligatorias sobre la rúbrica:
- Para cada tipo y cada estado, la suma de los puntajes máximos es **100** y la de los mínimos es **0**.
- Cada tipo tiene exactamente 7 criterios con 4 puntajes y 4 descriptores cada uno.
- Los puntajes son idénticos entre INV y DTI criterio por criterio.

```yaml
niveles: [Insuficiente, Básico, Bueno, Sobresaliente]

notas_estado:
  INV:
    EN_CURSO: "En los criterios 3 y 4, valore el diseño en ejecución y los avances obtenidos a la fecha, no el trabajo terminado."
  DTI:
    EN_CURSO: "En los criterios 3 y 4, valore el enfoque en desarrollo y la madurez alcanzada a la fecha, no el desarrollo concluido."

asistencia_alguno: "Si al menos un ponente se presentó, evalúe el proyecto completo. Los ponentes ausentes no reciben certificado de ponente, y ello no afecta la calificación del proyecto ni los certificados de los demás."

asistencia_ninguno: "Si ningún ponente se presentó, califique los criterios 1 a 6; el criterio 7 queda en 0 y la evaluación se registra como «sin sustentación». El proyecto no aspira a los reconocimientos."

umbrales:
  reconocimiento: 80
  mencion_meritoria: 85

texto_umbrales: "Umbral de reconocimiento: 80 puntos. Mención meritoria: 85 puntos."

INV:
  - orden: 1
    puntajes: [0, 5, 10, 15]
    BASE:
      nombre: "Planteamiento del problema, objetivos y pertinencia"
      descriptores:
        - "Problema difuso; objetivos ausentes o incoherentes con él"
        - "Problema enunciado; objetivos vagos o sin relación clara"
        - "Problema delimitado; objetivos precisos y coherentes"
        - "Problema delimitado y pertinente; objetivos precisos y verificables"
  - orden: 2
    puntajes: [0, 5, 10, 15]
    BASE:
      nombre: "Antecedentes"
      descriptores:
        - "Sin antecedentes, o ajenos al problema planteado"
        - "Menciona fuentes aisladas, sin relación entre sí"
        - "Revisión pertinente y actualizada, dentro de los 5 años"
        - "Revisión pertinente que sitúa el vacío que el proyecto aborda"
  - orden: 3
    puntajes: [0, 7, 13, 20]
    BASE:
      nombre: "Rigor metodológico"
      descriptores:
        - "Metodología ausente o que no corresponde al problema"
        - "Metodología enunciada, sin instrumentos ni técnicas de análisis"
        - "Metodología completa y coherente con el problema"
        - "Metodología completa, coherente y justificada frente a alternativas"
    EN_CURSO:
      nombre: "Diseño en ejecución"
      descriptores:
        - "Metodología ausente o que no corresponde al problema"
        - "Metodología enunciada, sin instrumentos ni técnicas de análisis"
        - "Metodología completa y coherente con el problema"
        - "Metodología completa, coherente y justificada frente a alternativas"
  - orden: 4
    puntajes: [0, 3, 7, 10]
    BASE:
      nombre: "Resultados y avances"
      descriptores:
        - "Sin resultados ni avances declarados"
        - "Resultados enunciados, sin datos ni evidencia"
        - "Resultados presentados con evidencia suficiente"
        - "Resultados presentados, con evidencia y análisis"
    PROPUESTA:
      nombre: "Resultados esperados y viabilidad"
      descriptores:
        - "Sin plan de trabajo ni resultados esperados"
        - "Plan enunciado, sin fases ni recursos"
        - "Plan con fases y recursos definidos"
        - "Plan con fases, recursos y riesgos previstos"
    EN_CURSO:
      nombre: "Avances obtenidos hasta la fecha"
      descriptores:
        - "Sin plan de trabajo ni resultados esperados"
        - "Plan enunciado, sin fases ni recursos"
        - "Plan con fases y recursos definidos"
        - "Plan con fases, recursos y riesgos previstos"
  - orden: 5
    puntajes: [0, 3, 7, 10]
    BASE:
      nombre: "Conclusiones y trabajo futuro"
      descriptores:
        - "Ausentes o sin relación con los resultados"
        - "Enunciadas, sin sustento en los resultados"
        - "Derivadas de los resultados, sin proyección"
        - "Derivadas de los resultados, con líneas de continuidad claras"
    PROPUESTA:
      nombre: "Aportes previstos y trabajo futuro"
      descriptores:
        - "Sin aportes previstos ni siguientes pasos"
        - "Aportes enunciados de forma general"
        - "Aportes previstos coherentes con los objetivos"
        - "Aportes previstos coherentes, con siguientes pasos definidos"
  - orden: 6
    puntajes: [0, 5, 10, 15]
    BASE:
      nombre: "Calidad del póster"
      descriptores:
        - "Ilegible a un metro, o incumple la plantilla institucional"
        - "Legible, pero sobrecargado o con bloques incompletos"
        - "Legible, ordenado y conforme a la plantilla"
        - "Legible, ordenado, con figuras que aportan al contenido"
  - orden: 7
    puntajes: [0, 5, 10, 15]
    BASE:
      nombre: "Sustentación"
      descriptores:
        - "No sustenta, o no domina el proyecto que presenta"
        - "Expone con dificultad; responde parcialmente las preguntas"
        - "Expone con claridad y responde las preguntas"
        - "Expone con claridad, domina el tema y argumenta sus respuestas"

DTI:
  - orden: 1
    puntajes: [0, 5, 10, 15]
    BASE:
      nombre: "Reto tecnológico, objetivos y pertinencia"
      descriptores:
        - "Reto difuso; objetivos ausentes o incoherentes con él"
        - "Reto enunciado; objetivos vagos o sin relación clara"
        - "Reto delimitado; objetivos precisos y coherentes"
        - "Reto delimitado y pertinente; objetivos precisos y verificables"
  - orden: 2
    puntajes: [0, 5, 10, 15]
    BASE:
      nombre: "Soluciones existentes y grado de novedad"
      descriptores:
        - "Sin revisión de soluciones existentes"
        - "Menciona soluciones aisladas, sin comparación"
        - "Revisión pertinente y actualizada, dentro de los 5 años"
        - "Revisión pertinente que sustenta el grado de novedad de la propuesta"
  - orden: 3
    puntajes: [0, 7, 13, 20]
    BASE:
      nombre: "Enfoque técnico"
      descriptores:
        - "Enfoque ausente o que no corresponde al reto planteado"
        - "Enfoque enunciado, sin componentes ni tecnologías definidas"
        - "Arquitectura completa y coherente con el reto"
        - "Arquitectura completa, coherente y justificada frente a alternativas"
    EN_CURSO:
      nombre: "Enfoque en desarrollo, no el desarrollo concluido"
      descriptores:
        - "Enfoque ausente o que no corresponde al reto planteado"
        - "Enfoque enunciado, sin componentes ni tecnologías definidas"
        - "Arquitectura completa y coherente con el reto"
        - "Arquitectura completa, coherente y justificada frente a alternativas"
  - orden: 4
    puntajes: [0, 3, 7, 10]
    BASE:
      nombre: "Nivel de madurez"
      descriptores:
        - "Sin evidencia de avance del desarrollo"
        - "Avance declarado, sin evidencia que lo respalde"
        - "Nivel de madurez declarado y evidenciado"
        - "Nivel de madurez evidenciado y validado"
    PROPUESTA:
      nombre: "Madurez esperada y viabilidad"
      descriptores:
        - "Sin plan de desarrollo ni madurez esperada"
        - "Plan enunciado, sin fases ni recursos"
        - "Plan con fases y recursos definidos"
        - "Plan con fases, recursos y riesgos previstos"
    EN_CURSO:
      nombre: "Madurez alcanzada a la fecha, no el desarrollo concluido"
      descriptores:
        - "Sin plan de desarrollo ni madurez esperada"
        - "Plan enunciado, sin fases ni recursos"
        - "Plan con fases y recursos definidos"
        - "Plan con fases, recursos y riesgos previstos"
  - orden: 5
    puntajes: [0, 3, 7, 10]
    BASE:
      nombre: "Aplicabilidad y transferencia"
      descriptores:
        - "Sin aplicación identificada"
        - "Aplicación enunciada de forma general"
        - "Aplicación concreta identificada, con usuario o contexto"
        - "Aplicación concreta con ruta de transferencia definida"
    PROPUESTA:
      nombre: "Aplicabilidad prevista y trabajo futuro"
      descriptores:
        - "Sin aplicación prevista"
        - "Aplicación enunciada de forma general"
        - "Aplicación prevista con usuario o contexto identificado"
        - "Aplicación prevista con ruta de continuidad definida"
  - orden: 6
    puntajes: [0, 5, 10, 15]
    BASE:
      nombre: "Calidad del póster"
      descriptores:
        - "Ilegible a un metro, o incumple la plantilla institucional"
        - "Legible, pero sobrecargado o con bloques incompletos"
        - "Legible, ordenado y conforme a la plantilla"
        - "Legible, ordenado, con figuras que aportan al contenido"
  - orden: 7
    puntajes: [0, 5, 10, 15]
    BASE:
      nombre: "Sustentación"
      descriptores:
        - "No sustenta, o no domina el proyecto que presenta"
        - "Expone con dificultad; responde parcialmente las preguntas"
        - "Expone con claridad y responde las preguntas"
        - "Expone con claridad, domina el tema y argumenta sus respuestas"
```

---

## 7. API REST

Prefijo `/api/`. Todas las rutas terminan en `/`. Respuestas JSON. Errores con forma `{"detalle": "...", "codigo": "...", "campos": {...}}`.

### Autenticación (`core`)

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| GET | `/api/health/` | público | `{"ok": true, "db": true}`; prueba la conexión a la base de datos |
| POST | `/api/auth/login/` | público | `{email, password}` → `{access, refresh, usuario}`. Protegido por django-axes |
| POST | `/api/auth/refresh/` | público | Rota el refresh token |
| GET | `/api/auth/me/` | autenticado | Datos del usuario, rol y `debe_cambiar_password` |
| POST | `/api/auth/cambiar-password/` | autenticado | `{password_actual, password_nueva, confirmacion}`; aplica RN-08 y pone `debe_cambiar_password = False` |

JWT: access de 30 minutos, refresh de 12 horas con rotación. Guardar los tokens en `sessionStorage` (se borran al cerrar la pestaña).

### Administración (rol ADMIN)

| Método | Ruta | Descripción |
|---|---|---|
| GET/POST | `/api/admin/eventos/` | Listar / crear |
| PATCH/DELETE | `/api/admin/eventos/{id}/` | Editar / eliminar (solo sin proyectos) |
| POST | `/api/admin/eventos/{id}/activar/` | RN-02 |
| GET | `/api/admin/areas/` | Catálogo agrupado por programa |
| GET/POST | `/api/admin/docentes/` | Listar (con carga `asignados/3` en el evento activo) / crear (RN-06) |
| PATCH/DELETE | `/api/admin/docentes/{id}/` | RN-10, RN-11 |
| POST | `/api/admin/docentes/{id}/restablecer-password/` | RN-09 |
| GET/POST | `/api/admin/proyectos/?evento=&origen=&tipo=&estado_evaluacion=` | Listar con filtros / crear con autores anidados |
| GET/PATCH/DELETE | `/api/admin/proyectos/{id}/` | RN-20, RN-21 |
| POST/DELETE | `/api/admin/proyectos/{id}/jurados/` | POST `{docentes: [id1, id2]}` asigna los dos juntos; DELETE quita los dos. RN-23 a RN-27 |
| PATCH | `/api/admin/asignaciones/{id}/` | `{docente}`: reemplaza al jurado (RN-26) |
| GET | `/api/admin/resultados/?evento=` | Las 4 tablas (RN-42 a RN-46) |
| GET | `/api/admin/proyectos/{id}/evaluaciones/` | RN-47 |
| GET | `/api/admin/resumen/?evento=` | Tablero: total proyectos, sin jurados, pendientes, parciales, evaluados, evaluaciones enviadas/total |

### Jurado (rol JURADO)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/jurado/asignaciones/` | Asignaciones del evento activo con datos del proyecto y si ya evaluó |
| GET | `/api/jurado/asignaciones/{id}/formulario/` | Identificación del proyecto, autores, rúbrica resuelta por tipo y estado, nota de estado, instrucción de asistencia |
| POST | `/api/jurado/asignaciones/{id}/evaluacion/` | `{niveles: {criterio_id: 0..3}, asistencia: {autor_id: bool}, fortalezas, aspectos_mejorar}` → 201; 409 si ya existe |
| GET | `/api/jurado/asignaciones/{id}/evaluacion/` | Evaluación propia enviada, solo lectura |

Configuración DRF: en producción solo `JSONRenderer` (sin API navegable). El admin de Django **no** se expone en producción.

---

## 8. Frontend (Angular)

### Base

- Componentes standalone, signals y `inject()`.
- `AuthService`: login, logout, refresh, usuario actual (signal).
- `authInterceptor`: agrega `Authorization: Bearer`, refresca una vez ante 401 y, si falla, cierra sesión.
- Manejo del 403 `CAMBIO_PASSWORD_REQUERIDO`: redirige a `/cambiar-password`.
- Guards: `authGuard`, `rolGuard('ADMIN' | 'JURADO')`, `cambioPasswordGuard`.
- Angular Material con un tema propio sobrio (institucional, legible). Nada de la apariencia genérica por defecto: tipografía cuidada, espaciado generoso, estados con color y texto.
- Todo mensaje de error del backend se muestra al usuario en un snackbar legible, nunca como JSON crudo.

### Identidad visual

Sigue la identidad visual del sistema **SAPIENS** de la Universidad de Nariño. Estilo **moderno con tarjetas**, **solo modo claro**, **sin logos** (universidad, facultad y evento escritos en texto). Se aplica en las fases 6 a 8 **sin cambiar la funcionalidad**.

Los tokens se definen **una sola vez** en el tema global (`frontend/src/styles/`: variables CSS + tema de Angular Material). Ningún componente escribe un color, una sombra o una tipografía directamente: siempre usa el token. Los hex son aproximados; cuando lleguen los valores exactos se cambian solo en ese archivo.

| Token | Valor | Uso |
|---|---|---|
| `--color-primario` | `#2E7D32` | Color primario de Material (botones principales, selección, foco) |
| `--header-degradado-inicio` / `--header-degradado-fin` | `#2E6B3A` → `#3F8F4C` | Fondo del header; texto blanco |
| `--franja-oscura` | `#285A32` | Franja delgada bajo el header, lado izquierdo |
| `--franja-ambar` | `#EFB255` | Misma franja, a la derecha de un corte diagonal; lleva el título de la sección |
| `--color-acento` | `#E8912D` | Pestaña activa y estados destacados |
| `--color-peligro` | `#D64541` | Acciones de peligro y "Salir" |
| `--fondo-pagina` | `#EDF1EC` | Fondo de toda página |
| `--fondo-tarjeta` | `#FFFFFF` | Contenido en tarjetas blancas con sombra suave |
| `--tarjeta-encabezado` | `#64946A` | Encabezado de tarjeta; título en blanco |
| `--tarjeta-descripcion` | `#EBECF0` | Franja bajo el encabezado de tarjeta con una descripción corta en gris |
| `--tabla-encabezado` | `#285A32` | Texto de encabezados de tabla |
| Tipografía | Roboto | Toda la aplicación |

Reglas de componentes:
- **Header**: degradado verde, texto blanco. Debajo, la franja verde oscuro → corte diagonal → ámbar con el título de la sección.
- **Tarjetas**: blancas con sombra suave; encabezado verde salvia con título blanco y, debajo, franja gris clara con una descripción corta.
- **Formularios**: estilo Material con línea inferior y etiqueta flotante.
- **Tablas**: encabezados en mayúscula, letra pequeña, color `--tabla-encabezado`; filas separadas por líneas finas.
- **Botones**: con ícono a la izquierda.
- **Estados** (pendiente, enviada, evaluado, sin sustentación…): siempre color **y** texto, nunca solo color.
- En las vistas del jurado (360 px) se conservan los mismos tokens; header y franja se compactan para dejar espacio al formulario.

### Pantallas

**Comunes**
- `/login`: correo institucional y contraseña.
- `/cambiar-password`: obligatoria en el primer inicio; explica por qué y las reglas de la contraseña.

**Administrador** (`/admin`, header SAPIENS con pestañas de navegación en escritorio; en celular, menú plegable ☰)
- `/admin/inicio`: selector de evento, la cantidad de **proyectos que faltan por evaluar** destacada, tarjetas de resumen (sin jurados, pendientes, parciales, evaluados) y barra de progreso de evaluaciones.
- `/admin/eventos`: tabla, crear/editar en diálogo, botón activar.
- `/admin/docentes`: tabla con buscador y carga `x/3`; crear/editar en diálogo (nombre, cédula, correo, departamento); restablecer contraseña con confirmación. Al crear, mostrar: "La contraseña inicial es la cédula del docente".
- `/admin/proyectos`: tabla con filtros (origen, tipo, estado de evaluación) y chip de estado que deja ver cuáles faltan por evaluar y cuáles no tienen jurados; formulario con área agrupada por programa, validación de RN-17 en vivo y autores dinámicos de 1 a 5 filas. Campos bloqueados según RN-20, con explicación.
- `/admin/asignaciones`: una fila por proyecto con sus 2 espacios de jurado; los dos se eligen y se guardan **juntos** (el botón se habilita solo con ambos elegidos); selector de docente que muestra la carga de cada uno y deshabilita a quien ya tiene 3; «Cambiar» un jurado sin evaluación; «Quitar ambos» solo si ninguno evaluó.
- `/admin/resultados`: 4 pestañas o 4 tablas (Semillero·INV, Semillero·DTI, Trabajo de grado·INV, Trabajo de grado·DTI) con puesto, código, título, nota jurado 1, nota jurado 2, promedio e indicadores (Reconocimiento, Mención meritoria, Sin sustentación, Pendiente). Clic en una fila abre el detalle con ambas evaluaciones.

**Jurado** (`/jurado`, **mobile-first**: diseñar a 360 px de ancho y luego escalar)
- `/jurado`: tarjetas de proyectos asignados con código, título, tipo, estado del proyecto y estado de la evaluación propia (Pendiente / Enviada).
- `/jurado/evaluar/:asignacionId`, con las 6 secciones del anexo, en este orden y con estos títulos:
  1. **Identificación del proyecto** (solo lectura): código, título, origen, estado, programa y área de conocimiento.
  2. **Asistencia de los ponentes**: una fila por autor con Asistió / No asistió, con los dos textos de asistencia (`asistencia_alguno` y `asistencia_ninguno`).
  3. **Matriz de valoración**: una tarjeta por criterio con su nombre y 4 opciones seleccionables (nivel, puntaje y descriptor). Mostrar la nota de estado si es EN_CURSO. Si nadie asistió, el criterio 7 se fija en Insuficiente y se deshabilita con una explicación (el sistema registra «sin sustentación» solo; el jurado no lo escribe).
  4. **Puntaje total**: x / 100 en vivo, con el texto de umbrales debajo; además, visible de forma fija en la parte inferior.
  5. **Observaciones**: Fortalezas del proyecto y Aspectos por mejorar (opcionales).
  6. **Datos del evaluador** (solo lectura): nombre completo, departamento académico y correo institucional del jurado que inició sesión, y la fecha del evento activo (como en el anexo). Reemplaza la firma; la firma equivale a la confirmación de envío (RN-37). En la vista de solo lectura y en el detalle del admin se muestran la fecha y hora reales de envío.
  - Al final, botón **Enviar evaluación**, deshabilitado hasta que todo lo obligatorio esté completo → diálogo de confirmación (RN-37) → indicador de carga → pantalla de éxito → volver a la lista.
- `/jurado/evaluacion/:asignacionId`: evaluación enviada, solo lectura, con las mismas secciones y los rótulos guardados en la evaluación. El detalle de evaluaciones del admin (RN-47) usa las mismas secciones.
- Ningún texto de la rúbrica (rótulos, descriptores, notas, textos de asistencia o de umbrales) se escribe en el frontend: todo viene de la API.
- Si el jurado sale de la pantalla con el formulario a medio llenar, pedir confirmación antes de descartar.

---

## 9. Seguridad

- HTTPS lo provee Vercel. En producción: `DEBUG=False`, `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS='DENY'`, `ALLOWED_HOSTS` explícitos.
- `SECRET_KEY` solo por variable de entorno.
- Contraseñas con el hasher por defecto de Django (PBKDF2). Nunca se registran ni se devuelven.
- django-axes: 5 intentos fallidos bloquean durante 15 minutos la combinación **usuario + IP** (no solo el usuario, para que nadie pueda bloquear a un jurado a propósito). `AxesStandaloneBackend` primero en `AUTHENTICATION_BACKENDS`. Verificado en producción (fases 2 y 9): Vercel entrega la IP real del cliente en `REMOTE_ADDR`, también a través del rewrite, e ignora `X-Forwarded-For` / `X-Real-IP` enviados por el cliente; por eso axes usa `REMOTE_ADDR` y no lee `X-Forwarded-For`. «Restablecer contraseña» (RN-09) también levanta el bloqueo del docente.
- Permisos por rol en cada vista y filtrado por usuario en cada queryset del jurado (RN-29).
- El backend recalcula todo lo que importa (total, criterio 7, estado de evaluación); nunca confía en el cliente.
- Cédulas y correos solo visibles para el admin (Ley 1581 de 2012).

---

## 10. Despliegue (primera vez en Vercel: documentar cada paso en el README)

### Neon
1. Crear la base de datos desde **Vercel → Storage / Marketplace → Neon**, en la misma región que se usará para las funciones.
2. Guardar las dos cadenas: **pooled** (para la app) y **directa** (para migraciones).

### Proyecto Vercel del backend
- Importar el repositorio con **Root Directory = `backend`**. Vercel detecta Django por `manage.py`.
- `.python-version` con `3.12`; dependencias en `requirements.txt`.
- Variables de entorno: `DJANGO_SECRET_KEY`, `DATABASE_URL` (pooled), `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`.
- Región de funciones igual a la de Neon (configuración del proyecto).
- Si el proxy del frontend recibe 401 o una página de login de Vercel, revisar la **Deployment Protection** del proyecto backend.

### Proyecto Vercel del frontend
- Importar el mismo repositorio con **Root Directory = `frontend`**, preset Angular.
- `frontend/vercel.json`, con `/api` **antes** del fallback. Usar `/api/(.*)` → `$1`: el patrón `:path*` pierde la barra final que exigen todas las rutas.
```json
{
  "outputDirectory": "dist/frontend/browser",
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://<BACKEND>.vercel.app/api/$1" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

Producción: la región de las funciones de Vercel coincide con la de Neon (PostgreSQL 18). Cada `git push` a `main` despliega los dos proyectos.

### Migraciones y datos iniciales (desde la máquina local)
```bash
cd backend
# Siempre con DJANGO_DEBUG=False (con True se crearían las tablas del admin de Django). La cadena directa vive en backend/env.prod (ignorado por git).
DATABASE_URL="<cadena directa de Neon>" DJANGO_DEBUG=False DJANGO_SECRET_KEY=x python manage.py migrate        # incluye áreas y rúbricas
DATABASE_URL="<cadena directa de Neon>" DJANGO_DEBUG=False DJANGO_SECRET_KEY=x python manage.py crear_admin    # pide correo, nombre y contraseña
```

### Respaldo
Con `pg_dump` de la **misma versión mayor que Neon (18)**, vía Docker (`postgres:18-alpine`), contra la cadena directa; los archivos quedan en `backend/respaldos/`. Restauración probada en un PostgreSQL 18 temporal (conteos idénticos). Comandos en el README.

### Datos de prueba
`python manage.py preparar_carga_real` (simula) / `--confirmar` (borra eventos, proyectos, evaluaciones y jurados; conserva administradores, áreas y rúbrica). **Ya se ejecutó el 6 de octubre de 2026; no volver a usarlo con datos oficiales cargados.**

---

## 11. Orden de ejecución por fases

Cada fase lista **actividades** y **criterios de salida**. No se pasa de fase sin cumplir todos los criterios de salida.

### Fase 0 — Esqueleto y despliegue temprano
Actividades:
- Estructura del monorepo (sección 3), `.gitignore`, `README.md` inicial.
- Backend Django mínimo con `/api/health/`, settings leídos de variables de entorno, configuración de pytest.
- Frontend Angular mínimo que llama a `/api/health/` y muestra el resultado; `proxy.conf.json` para desarrollo.
- Crear Neon y los dos proyectos de Vercel; desplegar ambos.

Criterios de salida:
- [x] `pytest` pasa (prueba de `/api/health/`).
- [x] `ng build` sin errores.
- [x] En local, el frontend muestra la respuesta del backend a través del proxy.
- [x] **En producción**, `https://<frontend>.vercel.app` muestra `db: true` a través del rewrite.

### Fase 1 — Modelo de datos y datos semilla
Actividades:
- Modelos de la sección 5 con sus restricciones de base de datos.
- `rubricas.yaml` (sección 6) y migraciones de datos para áreas y rúbricas.
- Comando `crear_admin`.
- Factories de prueba.

Criterios de salida:
- [x] Migraciones aplican desde cero sin errores.
- [x] Pruebas de rúbrica (sección 6): suma 100 por tipo y estado, 7 criterios, 4 niveles, puntajes iguales entre tipos.
- [x] Prueba de resolución de descriptores (BASE / PROPUESTA / EN_CURSO) para ambos tipos.
- [x] Pruebas de restricciones: RN-02, RN-13, RN-17 (CheckConstraint), RN-25, unicidad de correo y cédula.
- [x] Catálogo de áreas cargado exactamente como la sección 5.

### Fase 2 — Autenticación
Actividades:
- Login JWT por correo, refresh, `me`, cambiar contraseña.
- Bloqueo por `debe_cambiar_password` (RN-07).
- django-axes (sección 9).

Criterios de salida:
- [x] Pruebas: login correcto e incorrecto; RN-06 (un docente nuevo entra con su cédula); RN-07 (403 con el código correcto en rutas protegidas); RN-08 (rechaza contraseña igual a la cédula y contraseñas débiles); tras cambiarla, acceso normal.
- [x] Prueba de bloqueo tras 5 intentos fallidos.
- [x] Prueba de que un JURADO recibe 403 en `/api/admin/*`.

### Fase 3 — API de administración
Actividades:
- Endpoints de eventos, áreas, docentes, proyectos con autores anidados y asignaciones (sección 7).
- Lógica en `services.py`.

Criterios de salida:
- [x] Pruebas de RN-01 a RN-06, RN-09 a RN-13, RN-17, RN-19 a RN-28.
- [x] Prueba de concurrencia: dos asignaciones simultáneas no dejan a un docente con 4 proyectos ni a un proyecto con 3 jurados.
- [x] Estado de evaluación calculado correctamente en los 4 casos (RN-22).
- [x] Filtros del listado de proyectos funcionando.

### Fase 4 — API del jurado y evaluación
Actividades:
- Listado, formulario resuelto, envío y consulta de la evaluación.

Criterios de salida:
- [x] Pruebas de RN-29 a RN-40, en particular:
  - jurado A no puede ver ni evaluar la asignación de jurado B (404);
  - el formulario de un proyecto DTI en estado PROPUESTA trae los rótulos y descriptores de PROPUESTA;
  - falta un criterio o una marca de asistencia → 400;
  - nadie asistió → criterio 7 = 0 y `sin_sustentacion = True`, aunque el cliente envíe nivel 3;
  - total enviado por el cliente se ignora;
  - segundo envío → 409 y sigue existiendo una sola evaluación;
  - no existe ruta de edición o borrado para el jurado;
  - el jurado no recibe la nota del otro jurado en ninguna respuesta.
- [x] Prueba de extremo a extremo en API: crear evento, docentes, proyecto, asignar, cambiar contraseñas, evaluar dos veces, ver estado EVALUADO.

### Fase 5 — Resultados
Actividades:
- Endpoints de resultados, detalle de evaluaciones y resumen.

Criterios de salida:
- [x] Pruebas de RN-41 a RN-47:
  - 4 tablas con los proyectos correctos;
  - promedio con 2 decimales y redondeo half-up (ej. 80 y 81 → 80.50; 77 y 80 → 78.50);
  - empates: puntajes 90, 90, 85 → puestos 1, 1, 3;
  - pendientes al final sin puesto;
  - indicadores de reconocimiento, mención y sin sustentación en los bordes (79.99, 80.00, 84.99, 85.00).

### Fase 6 — Frontend: base y autenticación
Actividades:
- Angular Material, tema, layouts de admin y jurado, `AuthService`, interceptor, guards, login y cambio de contraseña.

Criterios de salida:
- [x] `ng build` sin errores ni advertencias relevantes; pruebas unitarias del `AuthService`, el interceptor y los guards.
- [x] Manual: un docente nuevo entra con la cédula, es obligado a cambiarla y luego llega a `/jurado`; el admin llega a `/admin`; un jurado que escribe `/admin` en la URL es redirigido.
- [x] Manual: expiración del access token se maneja sin que el usuario lo note.

### Fase 7 — Frontend: panel del administrador
Actividades:
- Todas las pantallas de administrador de la sección 8.

Criterios de salida:
- [x] Manual, flujo completo: crear evento y activarlo → registrar 4 docentes → registrar 3 proyectos (uno por cada combinación distinta, con 1 y con 5 autores) → asignar jurados → ver tablero.
- [x] Los errores de negocio (cuarto proyecto a un docente, Trabajo de grado en Propuesta, tercer jurado) se muestran con mensajes claros.
- [x] Las pantallas se usan bien en escritorio y son navegables en celular.

### Fase 8 — Frontend: jurado
Actividades:
- Pantallas del jurado de la sección 8, mobile-first.

Criterios de salida:
- [x] Manual en un celular real (o emulación de 360 px): evaluar un proyecto INV y uno DTI de principio a fin; el total en vivo coincide con el que guarda el backend.
- [x] Diálogo de confirmación (RN-37), indicador de carga y pantalla de éxito funcionando.
- [x] Doble toque en "Confirmar envío" no genera errores visibles ni duplicados.
- [x] Caso "nadie asistió" se comporta como RN-33 en la interfaz.
- [x] Resultados del admin reflejan las evaluaciones y los empates correctamente.

### Fase 9 — Producción y ensayo general
Actividades:
- Aplicar migraciones en Neon, crear el admin real, revisar variables de entorno y seguridad (sección 9).
- Pruebas de humo con Playwright contra producción: (1) login de admin y creación de un proyecto de prueba; (2) login de jurado, cambio de contraseña y envío de una evaluación.
- Borrar los datos de prueba y dejar la base lista para la carga real.
- Documentar en el README: despliegue, migraciones, crear admin, restablecer contraseñas, respaldo.

Criterios de salida:
- [x] Humo E2E en verde contra la URL de producción.
- [x] `python manage.py check --deploy` sin advertencias críticas.
- [x] Bloqueo de axes verificado en producción con la IP real.
- [x] Respaldo probado (crear y restaurar en una rama o base local).
- [ ] Piloto con 2–3 docentes reales en sus celulares sin incidentes. *(Lo hace el usuario como prueba final, después de cargar los datos oficiales; las pruebas usan valores genéricos en un evento aparte.)*

---

## 12. Definición de terminado (global)

- Todas las RN tienen prueba y pasan.
- El admin puede, sin ayuda técnica: crear el evento, cargar 24 docentes y 24 proyectos, asignar jurados y ver resultados.
- Un jurado puede, solo con su celular: entrar, cambiar la contraseña, evaluar sus 3 proyectos y ver que quedaron enviados.
- El sistema está desplegado y la base de datos tiene respaldo.

---

## 13. Fuera de alcance (primera versión)

No implementar sin que el usuario lo pida:
- Exportar resultados a Excel o PDF.
- Recuperación de contraseña por correo o envío de correos de cualquier tipo.
- Unificación de combinaciones por baja inscripción.
- Verificación de conflictos de interés (asesores, coordinadores).
- Certificados, memorias, carga de archivos o pósteres.
- Registro de proyectos por parte de estudiantes o docentes.
- Revisión previa (formato de revisión sin calificación).
- Edición de evaluaciones ya enviadas, por cualquier rol.

---

## 14. Pendientes por confirmar con el usuario

Preguntar antes de cerrar la fase indicada; mientras tanto, usar el valor por defecto.

1. **Descriptores del criterio 4 en estado EN_CURSO** (INV y DTI): ✅ confirmado por el usuario con los anexos actualizados (Anexo 6 · Investigación y Anexo 7 · DTI): son los mismos de PROPUESTA.
2. **Observaciones obligatorias**: ✅ confirmado por el usuario (fase 4): **opcionales**.
3. **Regla de "sin sustentación" del proyecto**: ✅ confirmado por el usuario (fase 5): basta con que **una** de las dos evaluaciones reporte que nadie asistió; el proyecto pierde el Reconocimiento.
4. **Restablecer contraseña por el admin** (RN-09): ✅ incluido como soporte para el día del evento; además levanta el bloqueo de django-axes del docente (pedido por el usuario en la fase 2).

---

## 15. Estado del proyecto (7 de octubre de 2026)

- Fases 0 a 9 completadas y desplegadas; queda solo el piloto con docentes reales (fase 9).
- Pruebas: 283 del backend (todas las RN, concurrencia, rúbrica contra los anexos) y 54 unitarias del frontend; humo E2E en verde contra producción.
- Neon: migraciones al día (incluida `evaluaciones.0004`, rúbrica según los anexos actualizados). Base vaciada el 6 de octubre con `preparar_carga_real`; desde entonces solo contiene **datos oficiales** (carga en curso).
- Cambios pedidos por el usuario durante el desarrollo, ya reflejados en este documento: jurados asignados en pareja (RN-23), departamento de lista cerrada (RN-04), indicador «faltan por evaluar» en el tablero, identidad visual SAPIENS (sección 8), 6 secciones del anexo con «Datos del evaluador» (sección 8).
- Pruebas futuras: solo con valores genéricos (`PRUEBA-…`) en un evento aparte; activarlo oculta el evento oficial a los jurados.

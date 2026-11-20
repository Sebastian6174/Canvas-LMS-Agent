# Canvas LMS Agent

Agente que lee el microcurrículo de un curso en Google Docs y monta el curso completo en Canvas LMS: módulos, página de inicio, agenda, alineación, foro, créditos, páginas de unidad, actividades con su ponderación y rúbricas.

El proyecto tiene tres partes:

| Carpeta | Qué es |
|---|---|
| [`agent/`](agent/) | El agente en Python ([LangGraph](https://github.com/langchain-ai/langgraph)). Se puede ejecutar solo, desde la terminal. |
| [`backend/`](backend/) | API en Flask que ejecuta el agente y transmite su progreso. |
| [`frontend/`](frontend/) | Interfaz en React + Vite para configurar y lanzar una ejecución. |

## Cómo funciona

```
Google Doc ──► analista ──► configurar curso ──► módulos ──┬─► agenda ─────────┐
                (LLM)                                      ├─► alineación ─────┤
                                                           ├─► foro ───────────┼─► ítems de introducción y créditos
                                                           └─► créditos ───────┘            │
                                                                                            ▼
        programa (syllabus) ◄── rúbricas ◄── actividades ◄── páginas de unidad ◄── página de inicio
```

1. **Analista** ([`nodes/analyst.py`](agent/src/nodes/analyst.py)): es el único paso que interpreta el documento. Lo lee conservando tablas, desplegables, viñetas y enlaces ([`tools/doc_parser.py`](agent/src/tools/doc_parser.py)) y hace una consulta al LLM por sección: información básica, secuencia, cada actividad y cada rúbrica. Después ensambla la estructura del curso sin LLM ([`analysis/assembly.py`](agent/src/analysis/assembly.py)):
   - el orden y la numeración de las actividades salen de la tabla de secuencia;
   - las horas, el peso y la semana de cada actividad salen de esa misma tabla;
   - cada actividad se asocia a su unidad y a su rúbrica;
   - avisa si las ponderaciones no suman 100 % o si una rúbrica no tiene actividad.
2. **Resto de pasos**: solo usan el estado que dejó el analista. Las páginas se arman con plantillas HTML fijas ([`src/pages/`](agent/src/pages/) y [`activities/template.py`](agent/src/activities/template.py)) y se publican con la API de Canvas ([`tools/canvas_api.py`](agent/src/tools/canvas_api.py)).

Se puede ejecutar varias veces sobre el mismo curso: las páginas, actividades, rúbricas y foros existentes se actualizan por nombre en lugar de duplicarse, los ítems de los módulos se reubican en su orden, y se borran las actividades que ya no están en el documento.

## Qué se crea en Canvas

- **Módulos**, en este orden: "Introducción al curso y ayuda", una unidad por cada módulo del documento ("Unidad N. Título") y "Créditos".
- **Página de inicio**: ficha técnica, introducción, resultados de aprendizaje, botones al foro, la agenda y las unidades, y la tabla del profesor.
- **Agenda de actividades** y **Alineación de actividades**, dentro del módulo de introducción junto con el **Foro de dudas**.
- **Créditos**: profesor autor y equipo de producción.
- **Por cada unidad**: una página de introducción (presentación, RA e indicadores de logro), una de materiales de estudio, el encabezado "Actividades" y sus actividades en orden.
- **Actividades** ("Actividad N. Tipo: título"): las evaluativas valen 5 puntos y se agrupan por peso en grupos ponderados; las formativas no se califican.
- **Rúbricas** asociadas a las actividades evaluativas, con los puntos repartidos según el peso de cada criterio.
- **Programa del curso** (syllabus) con el resumen de actividades que genera Canvas.

Las imágenes (banner, botones, foto del profesor) se toman de los archivos del curso por nombre: `Bannercurso.png`, `Boton_ForoDudas.png`, `AgendaActividades.png`, `Boton_U1.png`, `Iconos_ResultadosAp.png` y una foto con el nombre del docente. Si se configura un curso plantilla (`BASE_COURSE_ID`), sus archivos se copian al curso antes de empezar.

## Formato del documento

El analista espera la plantilla de microcurrículo con estas pestañas (las reconoce por palabras del título, no por el número):

| Pestaña | Se usa para |
|---|---|
| Información básica | Nombre, programa, créditos, prerrequisitos, profesor, descripción y enlace al microcurrículo |
| Alineación RA + AF + AE | Resultados de aprendizaje e indicadores de logro |
| Secuencia | Módulos con su presentación, y la tabla de actividades (semana, AF/AE, horas, % de valoración) |
| Actividades | Descripción, recursos y evaluación de cada actividad |
| Rúbricas | Criterios con su peso y los niveles Excelente, En desarrollo, Básico e Insuficiente |

Si una pestaña no se reconoce, esa consulta se hace sobre el documento completo.

## Requisitos

- Python 3.11 o superior
- Node.js 20.19 o superior (solo para la interfaz web; lo exige Vite 7)
- Un token de la API de Canvas con permisos para editar el curso
- Una cuenta de servicio de Google Cloud con las API de Google Docs y Google Drive habilitadas
- Una clave de [OpenRouter](https://openrouter.ai) o de [Google AI Studio](https://aistudio.google.com) (Gemini)

## Instalación

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    ·    Linux/macOS: source .venv/bin/activate
pip install -r backend/requirements.txt     # instala también las dependencias del agente

cd frontend
npm install
```

### Credenciales de Google

1. Descarga el JSON de la cuenta de servicio y guárdalo como `agent/config/credentials.json`.
2. Comparte cada documento de Google Docs (el del curso y el del perfil del docente) con el correo de la cuenta de servicio, con permiso de lectura.

`credentials.json` y `.env` están en `.gitignore`: no los subas al repositorio.

### Variables de entorno

Crea `agent/.env`:

```dotenv
# Canvas
DOMAIN=univallecolombia.instructure.com
CANVAS_API_TOKEN=...
COURSE_ID=1234              # curso a poblar (obligatorio si CREATE_NEW_COURSE=false)
CREATE_NEW_COURSE=false
BASE_COURSE_ID=             # opcional: curso plantilla del que se copian los archivos

# Google Docs
DOC_ID=...                  # ID del microcurrículo (lo que va entre /d/ y /edit en la URL)
TEACHER_DOC=                # opcional: documento con el perfil profesional del docente

# LLM: si hay GOOGLE_API_KEY se usa Gemini; si no, OpenRouter
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=google/gemini-2.5-flash-lite
GOOGLE_API_KEY=
GOOGLE_MODEL=gemini-2.5-flash
```

| Variable | Por defecto | Descripción |
|---|---|---|
| `DOMAIN` | `univallecolombia.instructure.com` | Dominio de la instancia de Canvas |
| `CANVAS_API_TOKEN` | — | Token de acceso a la API de Canvas |
| `COURSE_ID` | — | Curso de Canvas a poblar |
| `CREATE_NEW_COURSE` | `false` | `true` para crear un curso nuevo en lugar de usar `COURSE_ID` |
| `BASE_COURSE_ID` | — | Curso plantilla del que se copian los archivos (imágenes, botones) |
| `DOC_ID` | — | ID del documento de Google Docs con el microcurrículo |
| `TEACHER_DOC` | — | Documento con la biografía del docente, para la portada y los créditos |
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | — / `inclusionai/ring-2.6-1t` | Credenciales y modelo de OpenRouter |
| `GOOGLE_API_KEY` / `GOOGLE_MODEL` | — / `gemini-2.5-flash` | Credenciales y modelo de Gemini; tienen prioridad sobre OpenRouter |
| `LLM_MAX_TOKENS` | `3000` | Tokens máximos de salida por llamada |
| `ANALYSIS_CONCURRENCY` | `4` | Llamadas simultáneas al LLM durante el análisis |

`TEACHER_DOC` debe contener el perfil del docente. Si apunta a otro tipo de documento, la biografía queda vacía.

## Uso

### Desde la terminal

```bash
cd agent
python main.py
```

Al terminar imprime un reporte por etapa. El código de salida es `0` si todo salió bien y `1` si alguna etapa falló. Las advertencias del analista (por ejemplo, ponderaciones que no suman 100 %) se imprimen como `Advertencia del analista: …` pero no detienen el flujo.

### Con la interfaz web

```bash
# Terminal 1: API en http://127.0.0.1:5000
python backend/app.py

# Terminal 2: interfaz en http://127.0.0.1:5173
cd frontend
npm run dev
```

Desde la interfaz se pueden cambiar `DOC_ID`, `TEACHER_DOC`, el dominio, el curso, el curso plantilla y el modelo para una ejecución, sin editar `.env`. El backend admite una sola ejecución a la vez.

| Endpoint | Descripción |
|---|---|
| `GET /api/health` | Estado del servicio |
| `GET /api/flow` | Pasos del flujo |
| `POST /api/runs` | Inicia una ejecución en segundo plano; devuelve `runId` |
| `GET /api/runs/<runId>/events` | Progreso de la ejecución como Server-Sent Events (`log`, `done`, `error`) |
| `POST /api/run-agent` | Ejecuta el agente y responde al terminar |

El cuerpo de `POST /api/runs` y `POST /api/run-agent` es `{"config": {"doc_id": "...", "course_id": "...", ...}}`.

## Tests

```bash
cd agent
python -m pytest -q
```

Los tests no llaman al LLM ni a Canvas: [`tests/conftest.py`](agent/tests/conftest.py) bloquea ambos y cada test usa simulaciones ([`tests/fakes.py`](agent/tests/fakes.py)). [`test_pipeline_flow.py`](agent/tests/test_pipeline_flow.py) recorre el grafo completo de principio a fin.

## Estructura del agente

```
agent/
├── main.py                  Punto de entrada por terminal
├── config/                  Variables de entorno y construcción del cliente LLM
└── src/
    ├── graph.py             Grafo de LangGraph (nodos y aristas)
    ├── routing.py           Decisiones de continuar o detener el flujo
    ├── state.py             Estado compartido y modelos del curso
    ├── pipeline.py          Ejecución con configuración por corrida
    ├── reporting.py         Reporte final por terminal
    ├── constants.py         Nombres de módulos y páginas en Canvas
    ├── analysis/            Analista: secciones, extracción con LLM y ensamblado
    ├── activities/          Reglas de las actividades y plantilla HTML del assignment
    ├── pages/               Plantillas HTML: inicio, agenda, alineación, créditos, foro, unidades
    ├── nodes/               Un archivo por paso del grafo
    ├── tools/               Clientes de Google Docs y de la API de Canvas
    └── utils/               Mapa de archivos del curso y banner
```

### Cambiar el contenido generado

- **Diseño de una página**: edita su plantilla en [`src/pages/`](agent/src/pages/). La de actividades está en [`activities/template.py`](agent/src/activities/template.py); [`example_activity.html`](agent/src/activities/example_activity.html) es el ejemplo de referencia.
- **Forma de entrega por defecto de cada tipo de actividad**: `DEFAULT_DELIVERY_FORM_BY_TYPE` en [`activities/rules.py`](agent/src/activities/rules.py).
- **Qué extrae el LLM y con qué instrucciones**: [`analysis/extraction.py`](agent/src/analysis/extraction.py) y [`analysis/schemas.py`](agent/src/analysis/schemas.py).
- **Nombres de módulos y páginas**: [`constants.py`](agent/src/constants.py).

## Limitaciones conocidas

- La modalidad de las actividades es siempre "Virtual" y la semana de inicio es igual a la de fin.
- "Asesoría metodológica" queda vacía en la página de créditos.
- Si el documento no indica el tipo de una actividad, el LLM lo infiere del título (por ejemplo, "Explora y mide tu progreso" se clasifica como Quiz). Conviene revisarlo en las advertencias y en Canvas.

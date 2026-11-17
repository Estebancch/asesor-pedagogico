# Asesor Pedagógico Inteligente

Plataforma web para evaluar, retroalimentar y fortalecer las competencias adquiridas en los laboratorios de las cohortes 1 y 2 de un curso de Inteligencia Artificial.

Proyecto final de Profundización I: Inteligencia Artificial — Universidad de Manizales, Ingeniería de Sistemas y Telecomunicaciones.

Equipo: Esteban Carmona, Sergio Andrés Gómez y Nicolás Herrera.

## Qué hace

Para cada laboratorio la plataforma recibe tres cosas: la descripción y los objetivos, la rúbrica y la solución del estudiante (informe PDF y código en ZIP o GitHub). Con eso:

1. Verifica el código en un sandbox: sintaxis, análisis estático y pruebas unitarias, sin red y con límites de CPU, memoria y tiempo.
2. Pide a un modelo de IA que elija un nivel de la rúbrica para cada criterio y que cite el fragmento literal de la entrega que lo sustenta. La respuesta se valida contra un JSON Schema generado desde Pydantic.
3. Comprueba que cada cita exista en la entrega y la marca como verificada, parcial o no verificada.
4. Calcula la nota de 0,0 a 5,0 en el servidor con las ponderaciones de la rúbrica. El modelo nunca produce ni ve el número.
5. Deja la evaluación como preliminar hasta que el docente la revisa, la ajusta si hace falta, la aprueba y la publica.

Con las evaluaciones publicadas genera el informe integral del aprendizaje (visible en pantalla y descargable en PDF) y un mapa mental interactivo de las temáticas de IA, con nivel de dominio, laboratorios, evidencias y aspectos por profundizar en cada tema.

## Correspondencia con el enunciado

| Requisito | Dónde está |
|---|---|
| 1. Entrada de información | Laboratorio → Enunciado, Rúbrica y Entregas |
| 2. Portafolio académico | Mi portafolio / Portafolios (por estudiante, cohorte y laboratorio; cada entrega guarda la versión de rúbrica) |
| 3. Gestión de rúbricas | Laboratorio → Rúbrica: carga de PDF, Word, Excel, CSV, Markdown o JSON; editor con detección de inconsistencias; normalización a 100 %; versiones fijadas |
| 4. Evaluación inteligente | Página de evaluación: valoración por criterio con citas, fortalezas, debilidades, recomendaciones, cálculo de la nota y revisión docente |
| 5. Informe integrado | Informe integral: notas, competencias, niveles de dominio, evolución, brechas y plan; impresión y PDF |
| 6. Mapa mental interactivo | Mapa de competencias: zoom, arrastre, búsqueda, plegado por categoría, detalle por tema, descarga en PNG y JSON, vista de tabla |
| 7. Presentación y equipo | Página pública de inicio; se edita en Administración → Proyecto y equipo |
| Evaluación estructurada y reproducible | `backend/app/services/evaluacion.py`, `calificacion.py` |
| Verificación objetiva en sandbox | `backend/app/services/sandbox.py`, `sandbox_runner.py`, `verificacion.py` |
| Modelos locales o en la nube | Administración → Modelo de IA (Gemini, Claude, OpenAI o compatible, Ollama) |
| Autenticación, usuarios, persistencia | JWT + bcrypt, roles estudiante/docente/administrador, PostgreSQL o SQLite |
| Trazabilidad y supervisión docente | Pestaña Trazabilidad de cada evaluación y registro de auditoría |

## Probarla en tu computador

Requisitos: Python 3.12 o superior y Node 20 o superior. El sandbox necesita Linux o macOS; en Windows usa WSL o Docker.

```bash
# 1) Backend
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env                 # deja SEED_DEMO=true para tener datos de ejemplo

# 2) Frontend
cd frontend && npm ci && npm run build && cd ..

# 3) Servidor (sirve la API y el frontend compilado)
cd backend && uvicorn app.main:app --port 8000
```

Abre http://localhost:8000. Para desarrollar el frontend con recarga en caliente: `cd frontend && npm run dev` (usa el backend en el puerto 8000).

Con Docker: `docker build -t asesor . && docker run -p 8000:8000 -e SEED_DEMO=true -e ADMIN_PASSWORD=Cambiar1234 asesor`.

### Cuentas de demostración (`SEED_DEMO=true`)

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | el de `ADMIN_EMAIL` (por defecto `admin@asesor.edu.co`) | la de `ADMIN_PASSWORD` (en desarrollo, `Cambiar1234`) |
| Docente | `docente@demo.edu.co` | `Docente2026` |
| Estudiante con todo publicado | `laura@demo.edu.co` | `Estudiante2026` |
| Estudiante con vacíos y evaluaciones en distintos estados | `andres@demo.edu.co` | `Estudiante2026` |

Los datos de demostración se evalúan con el modo simulado, que no usa ningún modelo de IA: sirve para recorrer el flujo, no para calificar. Para evaluar de verdad, configura un proveedor en Administración → Modelo de IA.

## Publicarla

La entrega pide una URL pública. El repositorio trae lo necesario para Render (`render.yaml` y `Dockerfile`); los pasos están en [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md).

Con el código ya en GitHub, este enlace abre Render con el repositorio elegido (cambia `USUARIO/REPOSITORIO`):

`https://render.com/deploy?repo=https://github.com/USUARIO/REPOSITORIO`

## Pruebas

```bash
cd backend && python -m pytest -q
```

29 pruebas: cálculo de la nota, validación y lectura de rúbricas, sandbox (red, subprocesos, archivos ajenos, entorno limpio, prueba colgada), capa de proveedores de IA con reintentos y la API de extremo a extremo (permisos, entrega, evaluación, revisión, publicación, informe y mapa).

## Estructura

```
backend/app
  main.py            arranque, cabeceras de seguridad, sirve el frontend
  models.py          modelo de datos (SQLAlchemy)
  routers/           API: auth, académico, entregas y evaluaciones, analítica, administración
  services/
    rubricas.py      modelo, validación, lectura de archivos y normalización de rúbricas
    extraccion.py    evidencias con identificador citable (PDF, ZIP, GitHub, PPTX, imágenes)
    verificacion.py  sintaxis, análisis estático y pruebas
    sandbox*.py      ejecución aislada del código entregado
    evaluacion.py    prompt, esquema por rúbrica, verificación de citas, reglas objetivas
    calificacion.py  cálculo de la nota (Decimal, redondeo a 1 decimal)
    informe.py       consolidado, síntesis y PDF
    mapa.py          grafo de temas a partir de las evaluaciones
    ia/              proveedores: Gemini, Anthropic, OpenAI-compatible, Ollama, simulado
frontend/src         React + Vite + Tailwind; páginas en pages/
docs/                arquitectura, modelos de IA, despliegue, uso de IA en el desarrollo, guion de sustentación
```

## Documentación

- [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md): componentes, flujo de evaluación, sandbox, seguridad, decisiones y límites conocidos.
- [docs/MODELOS_IA.md](docs/MODELOS_IA.md): proveedores, requisitos, limitaciones y cómo estimar costos.
- [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md): publicación en Render y en cualquier servidor con Docker.
- [docs/USO_DE_IA.md](docs/USO_DE_IA.md): herramientas de IA usadas en el desarrollo, aportes, limitaciones y decisiones.
- [docs/GUION_SUSTENTACION.md](docs/GUION_SUSTENTACION.md): recorrido sugerido para la socialización.

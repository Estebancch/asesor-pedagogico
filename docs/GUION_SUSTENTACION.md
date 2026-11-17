# Guion para la socialización (12 minutos, tres personas)

Cada integrante presenta un tramo y maneja su propia pestaña con la sesión ya iniciada. Abran la URL unos minutos antes (el plan gratuito tarda en despertar) y tengan a mano un informe PDF y un ZIP para la entrega en vivo.

| Minuto | Quién | Qué mostrar | Qué explicar |
|---|---|---|---|
| 0:00–1:15 | Esteban | Página de inicio: resumen, objetivos, equipo | El problema y las tres reglas: la IA elige niveles y cita evidencia; la nota la calcula el servidor; nada se publica sin el docente |
| 1:15–3:30 | Esteban | Docente → Laboratorios y rúbricas → un laboratorio → Rúbrica. Crear nueva versión, descuadrar un peso, ver la inconsistencia, «Normalizar a 100 %», validar | Requisitos 1 y 3: las tres entradas de cada laboratorio; carga de rúbricas, detección y corrección de inconsistencias, versiones fijadas con huella |
| 3:30–5:00 | Sergio | Estudiante → un laboratorio → subir PDF y ZIP → «Evaluar con IA» | Requisito 2 y condición 3: verificación en sandbox, valoración por criterio, cálculo en el servidor. El estudiante ve «En revisión docente» |
| 5:00–8:00 | Sergio | Docente → Revisión → abrir la evaluación: nota sobre la regla, tabla «Cómo se calculó la nota», una cita (clic para abrir la fuente), pestañas Verificación técnica y Trazabilidad. Ajustar un criterio, aprobar y publicar | Requisito 4 y condiciones 2 y 6: salida estructurada, citas verificadas, trazabilidad, ajuste y aprobación docente |
| 8:00–10:00 | Nicolás | Estudiante → Informe integral (evolución, competencias, brechas, plan, «Descargar PDF») → Mapa de competencias (seleccionar un tema, filtrar por cohorte, descargar imagen) | Requisitos 5 y 6: los números los calcula el servidor; la IA redacta síntesis y plan. El mapa sale de una taxonomía común de temas |
| 10:00–11:00 | Nicolás | Administrador → Modelo de IA y Sistema y auditoría | Condiciones 4 y 5: proveedor configurable (nube o local), despliegue, roles, auditoría |
| 11:00–12:00 | Nicolás | `docs/USO_DE_IA.md` | Condición 1: qué hizo la IA, qué falló, cómo se detectó, qué revisaron ustedes. Cierre con los límites conocidos |

Para comparar un caso fuerte con uno débil en los datos de demostración: Laura tiene todo publicado con notas altas; Andrés tiene una entrega sin pruebas, una con una prueba que falla y una con error de sintaxis, y evaluaciones en estado preliminar y aprobada.

## Preguntas probables

| Pregunta | Responde | Respuesta corta | Dónde está |
|---|---|---|---|
| ¿Cómo evitan que la IA invente la nota? | Sergio | No la produce: elige un nivel por criterio dentro de una lista cerrada y el servidor multiplica por las ponderaciones | `backend/app/services/calificacion.py` |
| ¿Cómo validan la salida del modelo? | Sergio | Modelo Pydantic generado para cada rúbrica → JSON Schema; hasta 3 intentos y, si no cumple, la evaluación queda con error | `evaluacion.py`, `ia/base.py` |
| ¿Y si cita algo que no está? | Sergio | La cita se busca en la entrega: verificada, parcial o no verificada, con alerta en el criterio | `evaluacion.py`, `verificar_cita` |
| ¿Es seguro ejecutar código de estudiantes? | Sergio | Proceso aparte, sin red, sin subprocesos, con límites de CPU, memoria y tiempo, en un directorio propio y con otro usuario. No es una máquina virtual | `sandbox.py`, `sandbox_runner.py` |
| ¿Qué pasa si evalúo dos veces? | Sergio | Con la misma entrega, rúbrica y modelo se reutiliza el resultado; el docente puede forzar una nueva | `evaluacion.py` |
| ¿Qué detecta la gestión de rúbricas? | Esteban | Ponderaciones que no suman 100 %, criterios sin descriptor o sin competencia, niveles repetidos o fuera de escala | `rubricas.py`, `validar` |
| ¿Por qué ese modelo de IA? | Nicolás | La razón real del equipo; la capa de proveedores permite cambiarlo sin tocar código | `docs/MODELOS_IA.md` |
| ¿Cómo se arma el mapa? | Nicolás | Cada evaluación etiqueta temas contra una taxonomía de 10 categorías y 34 temas | `taxonomia.py`, `mapa.py` |
| ¿Qué hicieron ustedes y qué hizo la IA? | Los tres | Con precisión: qué dirigieron, revisaron, probaron y corrigieron | `docs/USO_DE_IA.md` |
| ¿Qué no hace? | Nicolás | No analiza video ni audio, solo ejecuta pruebas de Python, y las evaluaciones corren en el mismo proceso web | `docs/ARQUITECTURA.md` |
| ¿Qué es el «modo simulado»? | Cualquiera | Una heurística para probar el flujo sin clave. No es una valoración y la pantalla lo advierte | `ia/simulado.py` |

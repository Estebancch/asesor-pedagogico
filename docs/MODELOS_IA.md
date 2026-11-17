# Modelos de IA: elección, requisitos, limitaciones y costos

## Cómo se conecta

La plataforma no depende de un proveedor. `backend/app/services/ia/` define una interfaz común (`generar_json` y `listar_modelos`) con cuatro implementaciones y un modo de pruebas:

| Proveedor | Tipo | Salida estructurada | Entrada multimodal | Clave |
|---|---|---|---|---|
| Google Gemini | Nube | JSON Schema nativo | Imágenes y el PDF del informe | Sí |
| Anthropic Claude | Nube | Uso forzado de una herramienta con el esquema | Imágenes y PDF | Sí |
| OpenAI o compatible (Groq, OpenRouter, LM Studio, vLLM…) | Nube o local | `json_schema`; si el servicio no lo admite, `json_object` | Imágenes | Sí |
| Ollama | Local | La de la API compatible con OpenAI | Según el modelo | No |
| Simulado | — | Heurística de términos, sin IA | — | No |

Se elige en **Administración → Modelo de IA** (proveedor, modelo, URL base, temperatura, pasadas de consistencia, multimodal y clave) o con variables de entorno (`IA_PROVEEDOR`, `IA_MODELO`, `GEMINI_API_KEY`…). Lo guardado en Administración tiene prioridad. El botón «Guardar y probar conexión» hace una llamada mínima con salida estructurada para comprobar clave, modelo y esquema; «Ver disponibles» lista los modelos que la clave puede usar.

Sea cual sea el proveedor, la respuesta pasa por la misma validación con Pydantic y los mismos reintentos. Los errores de cuota o transitorios (429, 5xx) se reintentan con espera.

## Elección para la entrega

**Gemini Flash como opción por defecto**, por tres razones: tiene nivel gratuito con el que un curso puede evaluar sin costo, admite JSON Schema de forma nativa y acepta el PDF del informe como entrada, de modo que el modelo ve también figuras y diagramas. El modelo sugerido en el código es `gemini-3.8-flash`, que figura como estable en la documentación de Google; si la clave no lo tiene disponible, «Ver disponibles» muestra cuáles sí.

Cuándo cambiar:

- **Claude u OpenAI:** si se busca mayor calidad de argumentación en rúbricas complejas y hay presupuesto.
- **Ollama:** si los trabajos no pueden salir de la universidad. Requiere que el servidor de la plataforma alcance al servidor de Ollama, lo cual no ocurre desde un alojamiento en la nube hacia un computador personal sin un túnel.

## Requisitos

- **Nube:** una clave de API del proveedor y salida a internet desde el servidor.
- **Local (Ollama):** un equipo con GPU o suficiente RAM para el modelo elegido, y un modelo que siga bien un JSON Schema. Los modelos pequeños fallan más el esquema: la plataforma reintenta y, si no lo logra, deja la evaluación con error.

## Limitaciones

- La integración con los proveedores reales está cubierta por pruebas con respuestas HTTP simuladas (`tests/test_ia.py`). Durante el desarrollo no se ejecutó contra las API reales, porque no había claves disponibles. La primera comprobación con una clave real es el botón «Guardar y probar conexión»; conviene hacerla y evaluar una entrega antes de la sustentación.
- Un modelo de lenguaje puede equivocarse al elegir un nivel. Por eso se le exige citar, las citas se verifican, las reglas objetivas las aplica el servidor y ninguna nota se publica sin el docente.
- Entregas muy grandes se recortan a `IA_MAX_CARACTERES_EVIDENCIA` (180 000 por defecto), priorizando informe, README y código principal; la evaluación indica qué archivos no entraron.
- El video no se analiza. Las imágenes sueltas del ZIP se envían hasta un máximo de 6.
- Las mismas entradas no garantizan salidas idénticas en todos los proveedores, aun con temperatura 0. La plataforma lo compensa reutilizando el resultado cuando nada cambió y con las pasadas de consistencia.
- El nivel gratuito de los proveedores tiene límites por minuto y por día, y sus condiciones de uso de datos pueden diferir de las del nivel de pago. Para trabajos reales de estudiantes, revisa esas condiciones.

## Costos

La plataforma registra los tokens de cada evaluación (pestaña Trazabilidad). Para estimar:

| Concepto | Orden de magnitud |
|---|---|
| Entrada por evaluación | Enunciado + rúbrica + evidencias. Un laboratorio típico (informe de 5 a 10 páginas y unos cientos de líneas de código) ronda 10 000 a 25 000 tokens; el tope configurado equivale a unos 50 000 a 60 000 |
| Salida por evaluación | 2 000 a 5 000 tokens |
| Síntesis del informe integral | Unos pocos miles de tokens de entrada y de salida |

`costo ≈ evaluaciones × pasadas × (tokens de entrada × precio de entrada + tokens de salida × precio de salida)`

Ejemplo de volumen: 30 estudiantes × 6 laboratorios = 180 evaluaciones, es decir, del orden de 3 a 5 millones de tokens de entrada y menos de 1 millón de salida en un semestre con una pasada. Multiplica por el precio vigente del modelo elegido; los precios cambian, así que tómalos de la página oficial del proveedor el día que decidas. Con un modelo local el costo es el del equipo y la energía.

Qué reduce el costo: reutilización de resultados cuando nada cambió, una sola pasada de consistencia, recorte de evidencias y un modelo de la gama rápida.

Alojamiento: el plan gratuito de Render alcanza para la demostración (el servicio se duerme tras un rato sin uso y tarda cerca de un minuto en despertar; la base de datos gratuita tiene fecha de vencimiento). Para uso continuo hace falta un plan de pago o un servidor propio.

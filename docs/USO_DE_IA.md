# Uso de IA como asistente de desarrollo

Equipo: Esteban Carmona, Sergio Andrés Gómez y Nicolás Herrera.

Este documento registra cómo usamos la inteligencia artificial para construir la plataforma: qué herramienta usamos, qué le delegamos, dónde se equivocó, cómo se detectó cada fallo y qué decisiones tomamos nosotros.

## Cómo trabajamos

Construimos el proyecto con un agente de codificación, no programando cada módulo a mano. Nuestro papel fue el que describe el enunciado: orientar al agente, exigirle pruebas, cuestionar sus respuestas y decidir.

| Herramienta | Etapas | Para qué la usamos |
|---|---|---|
| Claude (agente de codificación de Anthropic) | Requisitos, arquitectura, backend, frontend, pruebas, depuración, documentación y preparación del despliegue | Le entregamos el enunciado del proyecto. Propuso la arquitectura, escribió el código, lo ejecutó, lo probó en un navegador automatizado y corrigió lo que falló |

El agente trabajó en un entorno aislado en la nube, con acceso a una terminal y a un navegador de pruebas, pero sin acceso a nuestras cuentas ni a los servicios de IA externos.

## Qué le delegamos en cada etapa

- **Requisitos.** Desglosó el enunciado en las 7 funcionalidades obligatorias y las 6 condiciones de ingeniería, y las convirtió en la tabla de correspondencia del README.
- **Arquitectura.** Propuso un solo servicio (FastAPI que sirve el frontend de React compilado), archivos guardados en la base de datos, una capa propia de proveedores de IA y un sandbox por capas. Dejó escritas las alternativas descartadas y el motivo (ver `ARQUITECTURA.md`).
- **Desarrollo.** Backend por módulos (rúbricas, extracción de evidencias, verificación, sandbox, evaluación, calificación, informe, mapa) y frontend por páginas.
- **Pruebas.** 29 pruebas automáticas del backend y dos recorridos en navegador con Playwright: uno visita cada página con cada rol buscando errores de consola y de API; el otro ejecuta el flujo completo: registro, entrega, evaluación, ajuste docente, aprobación, publicación, informe, mapa, rúbrica y administración.
- **Despliegue.** Dockerfile, `render.yaml` y la guía de publicación.

## Nuestras intervenciones

Estas son las decisiones y los cuestionamientos que hicimos durante el desarrollo, y lo que cambió por cada uno:

| Qué hicimos | Qué produjo |
|---|---|
| Entregamos el enunciado completo y pedimos el producto, no fragmentos | El agente trabajó contra los requisitos y las condiciones de ingeniería del documento |
| Preguntamos directamente si el proyecto cumplía el 100 % de los requisitos | Obtuvimos la lista explícita de lo que faltaba (URL pública, prueba con un modelo real, datos del equipo, laboratorios reales) y de los límites que un evaluador estricto podía señalar |
| Cuestionamos si la IA real estaba integrada, al ver que los datos de demostración decían «modo simulado» | El agente revisó la conexión con Gemini contra la documentación oficial y corrigió un campo de la petición que no coincidía con la guía |
| Decidimos hacer nosotros la publicación en GitHub y Render | No entregamos nuestras cuentas ni contraseñas al agente; pedimos el paso a paso y lo ejecutamos |
| Aportamos la clave de Gemini para la prueba real | El entorno del agente no tiene salida hacia el servicio de Google, así que la prueba con el modelo real se hace en la plataforma publicada |
| Pedimos el guion de sustentación repartido entre los tres | Cada integrante presenta y responde por una parte del sistema |

## Fallos del código generado y cómo se detectaron

Todos estos fallos venían en código escrito por la propia IA. Ninguno se encontró leyendo el código: aparecieron al ejecutarlo y mirar el resultado.

| Problema | Cómo se detectó | Corrección |
|---|---|---|
| El frontend no compilaba: se importaba un ícono (`Github`) que la versión instalada de la librería ya no trae | Primera compilación | Se comprobaron todos los íconos contra la librería instalada |
| Al estudiante se le mostraba «Evaluando…» indefinidamente cuando la evaluación ya estaba lista y esperaba al docente | El recorrido automático se quedó esperando | Estado propio «En revisión docente» |
| Horas con 5 de diferencia: SQLite descarta la zona horaria y el navegador tomaba la hora UTC como local | En la pestaña Trazabilidad la aprobación aparecía después de la publicación | Tipo de columna que repone UTC al leer |
| El mapa tocaba los bordes y la imagen descargada salía recortada | Se midieron los márgenes en el navegador y se revisó el PNG | En la versión instalada de React Flow el `padding` numérico son píxeles y no una fracción |
| Categorías del mapa montadas unas sobre otras | Revisión del PNG exportado | El radio se calcula según la separación angular mínima |
| El informe decía «6 laboratorios evaluados» con 1 evaluado, y no mostraba plan si no había brechas | Informe de un estudiante nuevo | Se corrigió el conteo y el plan nunca queda vacío |
| Una prueba con bucle infinito hacía perder el resultado de todas las demás | Se subió a propósito un ZIP hostil (red, lectura de `/etc/passwd`, bucle) | Límite de tiempo por prueba dentro del sandbox, con su prueba de regresión |
| Los nombres de criterios leídos de una rúbrica en PDF quedaban partidos en dos líneas | Se cargaron rúbricas de prueba en Word, Excel, PDF y Markdown | Las celdas se normalizan a una línea, con su prueba de regresión |
| La petición a Gemini usaba un valor distinto al de la guía oficial | Nuestra pregunta sobre la IA real llevó a contrastar con la documentación | Se alineó con la guía; el código conserva dos formas alternativas por si el servicio rechaza la primera |
| La exportación del mapa no podía incrustar las tipografías de Google Fonts | Errores en la consola del navegador | Tipografías servidas por la propia plataforma |

## Limitaciones que encontramos en la IA

- Escribe contra la versión de las librerías que recuerda, no contra la instalada. Tres de los fallos anteriores vienen de ahí.
- Lo que no se ejecuta no está verificado. En todos los casos de la tabla el código «se veía bien».
- No puede usar lo que no tiene: sin acceso a los servicios de IA externos, la integración con los proveedores quedó cubierta con respuestas simuladas, y la comprobación real depende de la plataforma publicada.
- No puede publicar ni actuar con nuestras cuentas. El despliegue es responsabilidad nuestra.
- Su resumen de entrega mezcla lo hecho con lo pendiente. Preguntarle expresamente qué falta y qué límites tiene dio una lista más completa que la del primer resumen.

## Decisiones de ingeniería

| Decisión | Motivo |
|---|---|
| La IA elige niveles; la nota la calcula el backend | Condición 2 del enunciado: el número no depende del modelo |
| Esquema de salida generado por rúbrica, con criterios y niveles como enumeraciones | El modelo no puede inventar criterios ni niveles |
| Citas literales verificadas contra la entrega | Explicabilidad comprobable, no solo declarada |
| Reglas objetivas aplicadas por el servidor con el resultado del sandbox | La verificación técnica pesa aunque el informe diga otra cosa |
| Rúbricas con versiones fijadas y huella | Cada evaluación apunta a la rúbrica exacta con que se hizo |
| Nada se publica sin aprobación docente | Supervisión humana |
| Modo simulado claramente rotulado | Permite demostrar y probar sin clave, sin hacerlo pasar por una evaluación |
| Sandbox por capas dentro del contenedor | Los alojamientos gratuitos no permiten Docker anidado; el límite queda documentado |
| Gemini como proveedor por defecto | Nivel gratuito, JSON Schema nativo y lectura directa del PDF del informe |

## Verificación en la plataforma publicada

La comprobación con el modelo real se hace sobre la plataforma desplegada, siguiendo esta lista:

1. Administración → Modelo de IA → «Guardar y probar conexión»: el modelo responde y la salida cumple el esquema.
2. Una entrega evaluada con el modelo real: sin el aviso de modo simulado, con citas verificadas y con los tokens registrados en Trazabilidad.
3. Pestaña Verificación técnica: capas del sandbox activas en el servidor de producción.
4. Administración → Sistema: base de datos PostgreSQL.
5. Un laboratorio propio con la rúbrica del curso: carga de la rúbrica, entrega, evaluación, revisión y publicación.

## Qué nos llevamos

Dirigir a un agente cambia el trabajo del ingeniero, no lo elimina: pasa de escribir cada línea a definir qué se pide, exigir que se ejecute y se pruebe, y no aceptar una respuesta sin evidencia. Dos resultados salieron de nuestras preguntas y no del trabajo espontáneo del agente: la lista completa de pendientes y límites, y la corrección de la conexión con Gemini.

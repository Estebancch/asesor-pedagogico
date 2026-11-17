"""Contenido de demostración: laboratorios, rúbricas y entregas de ejemplo.

IMPORTANTE: son datos ficticios para poder recorrer la plataforma. Reemplácenlos
por los laboratorios y rúbricas reales del curso desde la interfaz."""

NIVELES = [("excelente", "Excelente", 5.0), ("bueno", "Bueno", 4.0), ("aceptable", "Aceptable", 3.0), ("insuficiente", "Insuficiente", 1.5)]


def rubrica(titulo, competencias, criterios):
    """criterios: (id, nombre, comp_id, peso, [desc_excelente, desc_bueno, desc_aceptable, desc_insuficiente], regla|None)"""
    return {
        "titulo": titulo,
        "niveles": [{"id": i, "nombre": n, "puntaje": p, "descripcion": ""} for i, n, p in NIVELES],
        "competencias": [{"id": i, "nombre": n, "descripcion": ""} for i, n in competencias],
        "criterios": [{"id": cid, "nombre": nom, "descripcion": "", "competencia_id": comp, "ponderacion": peso,
                       "descriptores": dict(zip([n[0] for n in NIVELES], desc)),
                       "regla": {"verificacion": regla[0], "nivel_tope": regla[1]} if regla else None}
                      for cid, nom, comp, peso, desc, regla in criterios],
        "notas_interpretacion": [],
    }


COMP_BASE = [("conceptual", "Comprensión conceptual de técnicas de IA"), ("implementacion", "Implementación y verificación de soluciones"),
             ("comunicacion", "Análisis y comunicación de resultados")]

LABS = [
    dict(cohorte=1, orden=1, fecha="2026-03-06", clave="busqueda",
         titulo="Agentes de búsqueda: laberintos con BFS y A*",
         descripcion="Construir un agente que encuentre rutas en un laberinto representado como cuadrícula, comparando una búsqueda no informada (BFS) con una búsqueda heurística (A*).",
         objetivos="1. Modelar el problema como un espacio de estados.\n2. Implementar BFS y A* con una heurística admisible.\n3. Comparar nodos expandidos y longitud de la ruta.\n4. Verificar la solución con pruebas unitarias.",
         rubrica=rubrica("Rúbrica — Agentes de búsqueda", COMP_BASE, [
             ("modelado", "Modelado del problema como espacio de estados", "conceptual", 25,
              ["Define con precisión estados, acciones, estado inicial, meta y costo, y justifica la representación de la cuadrícula.",
               "Define estados, acciones y meta correctamente, con justificación parcial.",
               "Describe el problema de forma general sin formalizar estados ni acciones.",
               "No se evidencia un modelado del problema."], None),
             ("algoritmos", "Implementación de BFS y A* con heurística admisible", "implementacion", 35,
              ["Implementa BFS y A* correctos, con heurística Manhattan admisible y reconstrucción de la ruta.",
               "Implementa ambos algoritmos con detalles menores por mejorar.",
               "Implementa solo uno de los algoritmos o la heurística no es admisible.",
               "El código no ejecuta o no implementa los algoritmos pedidos."], ("sintaxis", "insuficiente")),
             ("pruebas", "Pruebas unitarias y verificación", "implementacion", 20,
              ["Incluye pruebas unitarias que cubren ruta óptima, laberinto sin solución y casos límite, y todas pasan.",
               "Incluye pruebas que pasan pero no cubren casos límite.",
               "Incluye pruebas incompletas o que fallan.",
               "No incluye pruebas."], ("pruebas", "aceptable")),
             ("analisis", "Análisis comparativo de resultados", "comunicacion", 20,
              ["Compara nodos expandidos y longitud de ruta con datos, e interpreta por qué A* expande menos.",
               "Compara resultados con datos pero con interpretación limitada.",
               "Presenta resultados sin compararlos.",
               "No presenta análisis de resultados."], None)])),
    dict(cohorte=1, orden=2, fecha="2026-04-10", clave="knn",
         titulo="Clasificación supervisada con k-NN",
         descripcion="Implementar desde cero un clasificador k vecinos más cercanos y evaluarlo con métricas de clasificación sobre un conjunto de datos pequeño.",
         objetivos="1. Implementar la distancia euclidiana y la votación de vecinos.\n2. Separar datos de entrenamiento y prueba.\n3. Calcular exactitud y matriz de confusión.\n4. Analizar el efecto del valor de k.",
         rubrica=rubrica("Rúbrica — Clasificación con k-NN", COMP_BASE, [
             ("fundamentos", "Fundamentos del aprendizaje supervisado", "conceptual", 20,
              ["Explica con claridad entrenamiento, prueba, vecinos y votación, y el riesgo de sobreajuste según k.",
               "Explica los conceptos principales con alguna imprecisión.", "Menciona los conceptos sin explicarlos.", "No evidencia comprensión de los conceptos."], None),
             ("clasificador", "Implementación del clasificador k-NN", "implementacion", 35,
              ["Implementa distancia euclidiana, selección de vecinos y votación de forma correcta y legible.",
               "Implementación correcta con oportunidades de mejora en claridad.", "Implementación parcial o con errores en la votación.", "El código no ejecuta o no clasifica."], ("sintaxis", "insuficiente")),
             ("metricas", "Evaluación con métricas y pruebas", "implementacion", 25,
              ["Calcula exactitud y matriz de confusión correctamente y lo comprueba con pruebas unitarias que pasan.",
               "Calcula las métricas y tiene pruebas, con cobertura limitada.", "Calcula solo la exactitud o las pruebas fallan.", "No evalúa el modelo."], ("pruebas", "aceptable")),
             ("efecto_k", "Análisis del efecto de k", "comunicacion", 20,
              ["Compara varios valores de k con datos y explica el compromiso entre sesgo y varianza.",
               "Compara valores de k con explicación breve.", "Usa un solo valor de k sin justificarlo.", "No analiza el parámetro."], None)])),
    dict(cohorte=1, orden=3, fecha="2026-05-15", clave="perceptron",
         titulo="Perceptrón y redes neuronales desde cero",
         descripcion="Programar un perceptrón simple, entrenarlo para funciones lógicas y explicar por qué no resuelve XOR, introduciendo la necesidad de capas ocultas.",
         objetivos="1. Implementar la regla de aprendizaje del perceptrón.\n2. Entrenar para AND y OR y verificar la convergencia.\n3. Explicar la limitación con XOR y la separabilidad lineal.\n4. Documentar el efecto de la tasa de aprendizaje.",
         rubrica=rubrica("Rúbrica — Perceptrón", COMP_BASE, [
             ("regla", "Comprensión de la regla de aprendizaje", "conceptual", 25,
              ["Explica pesos, sesgo, función de activación y la actualización por error con sus propias palabras y un ejemplo.",
               "Explica la regla de aprendizaje correctamente sin ejemplo.", "Describe la regla de forma incompleta.", "No explica la regla de aprendizaje."], None),
             ("entrenamiento", "Implementación del entrenamiento", "implementacion", 35,
              ["Implementa el entrenamiento por épocas, converge en AND y OR y lo demuestra con pruebas que pasan.",
               "Implementa el entrenamiento y converge, con pruebas limitadas.", "Implementación con errores o sin verificar la convergencia.", "El código no ejecuta."], ("sintaxis", "insuficiente")),
             ("xor", "Explicación de la limitación con XOR", "conceptual", 20,
              ["Demuestra experimentalmente que no converge en XOR y lo relaciona con la separabilidad lineal y las capas ocultas.",
               "Explica la limitación sin demostrarla experimentalmente.", "Menciona la limitación sin explicarla.", "No aborda XOR."], None),
             ("tasa", "Análisis de la tasa de aprendizaje", "comunicacion", 20,
              ["Compara varias tasas de aprendizaje con datos de épocas hasta converger e interpreta el resultado.",
               "Compara tasas con interpretación breve.", "Usa una sola tasa.", "No analiza la tasa de aprendizaje."], None)])),
    dict(cohorte=2, orden=1, fecha="2026-08-21", clave="prompts",
         titulo="Diseño de prompts y salidas estructuradas",
         descripcion="Diseñar prompts para clasificar solicitudes de soporte con un modelo de lenguaje y validar que la respuesta cumpla un esquema JSON antes de usarla.",
         objetivos="1. Aplicar técnicas zero-shot y few-shot.\n2. Definir un esquema de salida y validarlo en código.\n3. Manejar respuestas inválidas del modelo.\n4. Comparar la calidad de los prompts con casos de prueba.",
         rubrica=rubrica("Rúbrica — Prompts y salidas estructuradas", COMP_BASE, [
             ("tecnicas", "Técnicas de diseño de prompts", "conceptual", 25,
              ["Aplica y diferencia zero-shot y few-shot, con instrucciones, ejemplos y formato de salida explícitos.",
               "Aplica ambas técnicas con ejemplos poco variados.", "Usa un solo prompt sin técnica reconocible.", "No presenta diseño de prompts."], None),
             ("validacion", "Validación de la salida estructurada", "implementacion", 35,
              ["Valida el JSON contra un esquema, rechaza categorías desconocidas y maneja respuestas inválidas con reintento.",
               "Valida el esquema pero no maneja todos los casos inválidos.", "Solo comprueba que la respuesta sea JSON.", "No valida la salida del modelo."], ("sintaxis", "insuficiente")),
             ("casos", "Casos de prueba y verificación", "implementacion", 20,
              ["Incluye pruebas unitarias para respuestas válidas, inválidas y categorías desconocidas, y todas pasan.",
               "Incluye pruebas para el caso válido.", "Prueba manualmente sin automatizar.", "No incluye verificación."], ("pruebas", "aceptable")),
             ("comparacion", "Comparación y reflexión sobre confiabilidad", "comunicacion", 20,
              ["Compara los prompts con datos y reflexiona sobre alucinaciones y límites del modelo.",
               "Compara los prompts sin datos suficientes.", "Describe los prompts sin compararlos.", "No presenta reflexión."], None)])),
    dict(cohorte=2, orden=2, fecha="2026-09-25", clave="rag",
         titulo="Asistente RAG sobre documentos del curso",
         descripcion="Construir el componente de recuperación de un asistente RAG: fragmentar documentos, representarlos como vectores y recuperar el contexto más relevante para una pregunta.",
         objetivos="1. Fragmentar documentos con solapamiento.\n2. Representar texto como vectores y calcular similitud coseno.\n3. Recuperar los k fragmentos más relevantes.\n4. Evaluar la recuperación y discutir cómo reduce alucinaciones.",
         rubrica=rubrica("Rúbrica — Asistente RAG", COMP_BASE, [
             ("arquitectura", "Comprensión de la arquitectura RAG", "conceptual", 25,
              ["Explica fragmentación, embeddings, recuperación y generación, y por qué el contexto recuperado reduce alucinaciones.",
               "Explica las etapas principales con algún vacío.", "Menciona RAG sin explicar sus etapas.", "No evidencia comprensión de RAG."], None),
             ("recuperacion", "Implementación de fragmentación y recuperación", "implementacion", 35,
              ["Implementa fragmentación con solapamiento, vectorización y similitud coseno, y recupera los k más relevantes.",
               "Implementa la recuperación con limitaciones menores.", "Implementa solo la fragmentación o la similitud.", "El código no ejecuta."], ("sintaxis", "insuficiente")),
             ("evaluacion", "Evaluación de la recuperación con pruebas", "implementacion", 20,
              ["Verifica con pruebas unitarias que la recuperación devuelve el fragmento esperado y todas pasan.",
               "Tiene pruebas con cobertura limitada.", "Evalúa manualmente con un ejemplo.", "No evalúa la recuperación."], ("pruebas", "aceptable")),
             ("limites", "Análisis de límites y mejoras", "comunicacion", 20,
              ["Discute límites del enfoque (tamaño de fragmento, vocabulario) y propone mejoras concretas con embeddings semánticos.",
               "Discute límites sin proponer mejoras.", "Menciona límites de forma superficial.", "No analiza límites."], None)])),
    dict(cohorte=2, orden=3, fecha="2026-10-30", clave="agente",
         titulo="Agente con herramientas y verificación de resultados",
         descripcion="Diseñar un agente que decide qué herramienta usar para resolver una tarea, ejecuta la herramienta y verifica el resultado antes de responder.",
         objetivos="1. Definir herramientas con nombre, descripción y parámetros.\n2. Implementar el despacho de llamadas a herramientas.\n3. Validar argumentos y manejar errores.\n4. Reflexionar sobre trazabilidad y confianza en agentes.",
         rubrica=rubrica("Rúbrica — Agente con herramientas", COMP_BASE, [
             ("diseno", "Diseño de herramientas y del ciclo del agente", "conceptual", 25,
              ["Describe el ciclo decidir-actuar-verificar y define herramientas con nombre, descripción y parámetros tipados.",
               "Define herramientas correctas con descripción breve del ciclo.", "Define herramientas sin explicar el ciclo.", "No presenta diseño."], None),
             ("despacho", "Implementación del despacho y validación de argumentos", "implementacion", 35,
              ["Implementa registro y despacho de herramientas, valida argumentos y maneja herramientas desconocidas y errores.",
               "Implementa el despacho con validación parcial.", "Implementa el despacho sin validar argumentos.", "El código no ejecuta."], ("sintaxis", "insuficiente")),
             ("verificacion", "Verificación de resultados con pruebas", "implementacion", 20,
              ["Incluye pruebas unitarias del despacho, de errores y del registro de trazas, y todas pasan.",
               "Incluye pruebas del caso exitoso.", "Prueba manualmente.", "No verifica."], ("pruebas", "aceptable")),
             ("confianza", "Reflexión sobre trazabilidad y confianza", "comunicacion", 20,
              ["Explica cómo las trazas y la verificación permiten auditar al agente y dónde debe intervenir una persona.",
               "Explica la trazabilidad sin abordar la supervisión humana.", "Menciona la confianza de forma general.", "No presenta reflexión."], None)])),
]

# --- código de ejemplo -----------------------------------------------------------------------------

CODIGO = {
"busqueda": {
"busqueda.py": '''"""Busqueda de rutas en un laberinto con BFS y A*."""
from collections import deque
import heapq

MOVIMIENTOS = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def vecinos(laberinto, estado):
    """Acciones validas: moverse a una celda libre (0) dentro de la cuadricula."""
    f, c = estado
    for df, dc in MOVIMIENTOS:
        nf, nc = f + df, c + dc
        if 0 <= nf < len(laberinto) and 0 <= nc < len(laberinto[0]) and laberinto[nf][nc] == 0:
            yield (nf, nc)


def reconstruir(padres, meta):
    ruta = [meta]
    while padres[ruta[-1]] is not None:
        ruta.append(padres[ruta[-1]])
    return ruta[::-1]


def bfs(laberinto, inicio, meta):
    """Busqueda no informada por amplitud. Devuelve (ruta, nodos_expandidos)."""
    frontera, padres, expandidos = deque([inicio]), {inicio: None}, 0
    while frontera:
        estado = frontera.popleft()
        expandidos += 1
        if estado == meta:
            return reconstruir(padres, meta), expandidos
        for v in vecinos(laberinto, estado):
            if v not in padres:
                padres[v] = estado
                frontera.append(v)
    return None, expandidos


def manhattan(a, b):
    """Heuristica admisible: nunca sobreestima el costo real en una cuadricula."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def a_estrella(laberinto, inicio, meta):
    """Busqueda heuristica A* con f = g + h. Devuelve (ruta, nodos_expandidos)."""
    frontera, padres, costo, expandidos = [(manhattan(inicio, meta), 0, inicio)], {inicio: None}, {inicio: 0}, 0
    while frontera:
        _, g, estado = heapq.heappop(frontera)
        expandidos += 1
        if estado == meta:
            return reconstruir(padres, meta), expandidos
        for v in vecinos(laberinto, estado):
            if v not in costo or g + 1 < costo[v]:
                costo[v], padres[v] = g + 1, estado
                heapq.heappush(frontera, (g + 1 + manhattan(v, meta), g + 1, v))
    return None, expandidos
''',
"test_busqueda.py": '''from busqueda import a_estrella, bfs, manhattan

LAB = [[0, 0, 0, 0], [1, 1, 0, 1], [0, 0, 0, 0], [0, 1, 1, 0]]


def test_ruta_optima_coincide():
    r1, _ = bfs(LAB, (0, 0), (3, 3))
    r2, _ = a_estrella(LAB, (0, 0), (3, 3))
    assert len(r1) == len(r2) == 7


def test_a_estrella_no_expande_mas_que_bfs():
    _, n_bfs = bfs(LAB, (0, 0), (3, 3))
    _, n_a = a_estrella(LAB, (0, 0), (3, 3))
    assert n_a <= n_bfs


def test_sin_solucion():
    cerrado = [[0, 1], [1, 0]]
    assert bfs(cerrado, (0, 0), (1, 1))[0] is None
    assert a_estrella(cerrado, (0, 0), (1, 1))[0] is None


def test_heuristica():
    assert manhattan((0, 0), (3, 3)) == 6
''',
"README.md": "# Laboratorio de busqueda\n\nEjecutar las pruebas con `pytest`. `busqueda.py` contiene BFS y A* con heuristica Manhattan.\n",
},
"knn": {
"knn.py": '''"""Clasificador k vecinos mas cercanos implementado desde cero."""
from collections import Counter
import math


def distancia(a, b):
    """Distancia euclidiana entre dos vectores de caracteristicas."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def predecir(entrenamiento, etiquetas, punto, k=3):
    """Votacion de los k vecinos mas cercanos al punto."""
    orden = sorted(range(len(entrenamiento)), key=lambda i: distancia(entrenamiento[i], punto))
    votos = Counter(etiquetas[i] for i in orden[:k])
    return votos.most_common(1)[0][0]


def exactitud(reales, predichas):
    aciertos = sum(1 for r, p in zip(reales, predichas) if r == p)
    return aciertos / len(reales)


def matriz_confusion(reales, predichas, clases):
    matriz = {c: {d: 0 for d in clases} for c in clases}
    for r, p in zip(reales, predichas):
        matriz[r][p] += 1
    return matriz
''',
"test_knn.py": '''from knn import distancia, exactitud, matriz_confusion, predecir

X = [(1, 1), (1, 2), (2, 1), (8, 8), (8, 9), (9, 8)]
Y = ["a", "a", "a", "b", "b", "b"]


def test_distancia():
    assert distancia((0, 0), (3, 4)) == 5


def test_predice_por_votacion():
    assert predecir(X, Y, (2, 2), k=3) == "a"
    assert predecir(X, Y, (9, 9), k=3) == "b"


def test_exactitud_y_matriz():
    pred = [predecir(X, Y, p, k=3) for p in [(1, 1), (9, 9), (2, 2)]]
    assert exactitud(["a", "b", "a"], pred) == 1.0
    m = matriz_confusion(["a", "b", "a"], pred, ["a", "b"])
    assert m["a"]["a"] == 2 and m["b"]["b"] == 1
''',
},
"perceptron": {
"perceptron.py": '''"""Perceptron simple con regla de aprendizaje por correccion de error."""


def activacion(z):
    """Funcion escalon."""
    return 1 if z >= 0 else 0


def predecir(pesos, sesgo, x):
    return activacion(sum(w * xi for w, xi in zip(pesos, x)) + sesgo)


def entrenar(datos, tasa=0.1, epocas=50):
    """Devuelve (pesos, sesgo, epocas_usadas). Converge si los datos son linealmente separables."""
    pesos, sesgo = [0.0] * len(datos[0][0]), 0.0
    for epoca in range(1, epocas + 1):
        errores = 0
        for x, esperado in datos:
            error = esperado - predecir(pesos, sesgo, x)
            if error:
                errores += 1
                pesos = [w + tasa * error * xi for w, xi in zip(pesos, x)]
                sesgo += tasa * error
        if errores == 0:
            return pesos, sesgo, epoca
    return pesos, sesgo, epocas


AND = [((0, 0), 0), ((0, 1), 0), ((1, 0), 0), ((1, 1), 1)]
OR = [((0, 0), 0), ((0, 1), 1), ((1, 0), 1), ((1, 1), 1)]
XOR = [((0, 0), 0), ((0, 1), 1), ((1, 0), 1), ((1, 1), 0)]
''',
"test_perceptron.py": '''from perceptron import AND, OR, XOR, entrenar, predecir


def _acierta(datos, pesos, sesgo):
    return all(predecir(pesos, sesgo, x) == y for x, y in datos)


def test_converge_en_and_y_or():
    for datos in (AND, OR):
        pesos, sesgo, epocas = entrenar(datos)
        assert _acierta(datos, pesos, sesgo) and epocas < 50


def test_no_converge_en_xor():
    pesos, sesgo, epocas = entrenar(XOR, epocas=100)
    assert not _acierta(XOR, pesos, sesgo) and epocas == 100
''',
},
"prompts": {
"clasificador.py": '''"""Prompts zero-shot y few-shot y validacion de la salida estructurada de un modelo de lenguaje."""
import json

CATEGORIAS = ["facturacion", "soporte_tecnico", "cuenta", "otro"]
ESQUEMA = {"categoria": str, "confianza": float, "justificacion": str}

EJEMPLOS = [
    ("No puedo iniciar sesion desde ayer", "cuenta"),
    ("Me cobraron dos veces la mensualidad", "facturacion"),
    ("La aplicacion se cierra al abrir el reporte", "soporte_tecnico"),
]


def prompt_zero_shot(solicitud):
    return ("Clasifica la solicitud en una de estas categorias: " + ", ".join(CATEGORIAS) +
            ". Responde solo con JSON con las claves categoria, confianza y justificacion.\\nSolicitud: " + solicitud)


def prompt_few_shot(solicitud):
    ejemplos = "\\n".join(f"Solicitud: {s}\\nCategoria: {c}" for s, c in EJEMPLOS)
    return prompt_zero_shot(solicitud) + "\\nEjemplos:\\n" + ejemplos


def validar_respuesta(texto):
    """Valida la salida estructurada contra el esquema. Lanza ValueError si no cumple."""
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as e:
        raise ValueError("la respuesta no es JSON valido") from e
    for clave, tipo in ESQUEMA.items():
        if clave not in datos or not isinstance(datos[clave], tipo):
            raise ValueError(f"falta o es invalido el campo {clave}")
    if datos["categoria"] not in CATEGORIAS:
        raise ValueError("categoria desconocida: posible alucinacion del modelo")
    if not 0 <= datos["confianza"] <= 1:
        raise ValueError("confianza fuera de rango")
    return datos


def clasificar(solicitud, modelo, reintentos=2):
    """Llama al modelo y reintenta si la respuesta no cumple el esquema."""
    ultimo = None
    for _ in range(reintentos + 1):
        try:
            return validar_respuesta(modelo(prompt_few_shot(solicitud)))
        except ValueError as e:
            ultimo = e
    raise ValueError(f"el modelo no produjo una salida valida: {ultimo}")
''',
"test_clasificador.py": '''import pytest
from clasificador import clasificar, prompt_few_shot, validar_respuesta

VALIDA = '{"categoria": "cuenta", "confianza": 0.9, "justificacion": "menciona inicio de sesion"}'


def test_respuesta_valida():
    assert validar_respuesta(VALIDA)["categoria"] == "cuenta"


def test_rechaza_no_json_y_categoria_desconocida():
    with pytest.raises(ValueError):
        validar_respuesta("claro, la categoria es cuenta")
    with pytest.raises(ValueError):
        validar_respuesta('{"categoria": "ventas", "confianza": 0.9, "justificacion": "x"}')


def test_reintenta_hasta_obtener_salida_valida():
    respuestas = iter(["no es json", VALIDA])
    assert clasificar("no puedo entrar", lambda p: next(respuestas))["categoria"] == "cuenta"


def test_few_shot_incluye_ejemplos():
    assert "Ejemplos" in prompt_few_shot("hola")
''',
},
"rag": {
"rag.py": '''"""Componente de recuperacion de un asistente RAG: fragmentacion, vectores y similitud coseno."""
from collections import Counter
import math
import re


def fragmentar(texto, tamano=40, solapamiento=10):
    """Divide el documento en fragmentos (chunks) de palabras con solapamiento."""
    palabras = texto.split()
    paso = tamano - solapamiento
    return [" ".join(palabras[i:i + tamano]) for i in range(0, max(len(palabras) - solapamiento, 1), paso)]


def vectorizar(texto):
    """Representacion vectorial simple: bolsa de palabras con frecuencias."""
    return Counter(re.findall(r"[a-z0-9]+", texto.lower()))


def similitud_coseno(a, b):
    comunes = set(a) & set(b)
    punto = sum(a[t] * b[t] for t in comunes)
    norma = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return punto / norma if norma else 0.0


def recuperar(pregunta, fragmentos, k=2):
    """Devuelve los k fragmentos mas relevantes como contexto recuperado para el modelo."""
    q = vectorizar(pregunta)
    puntuados = sorted(((similitud_coseno(q, vectorizar(f)), f) for f in fragmentos), reverse=True)
    return [f for s, f in puntuados[:k] if s > 0]


def construir_prompt(pregunta, contexto):
    return ("Responde solo con base en el contexto. Si no esta alli, di que no lo sabes.\\nContexto:\\n" +
            "\\n---\\n".join(contexto) + "\\nPregunta: " + pregunta)
''',
"test_rag.py": '''from rag import construir_prompt, fragmentar, recuperar, similitud_coseno, vectorizar

DOC = ("El perceptron es un clasificador lineal. " * 6 + "La busqueda A estrella usa una heuristica admisible. " * 6 +
       "Un sistema RAG recupera fragmentos relevantes antes de generar la respuesta. " * 6)


def test_fragmentar_con_solapamiento():
    frag = fragmentar(DOC, tamano=20, solapamiento=5)
    assert len(frag) > 3 and all(len(f.split()) <= 20 for f in frag)


def test_similitud():
    assert similitud_coseno(vectorizar("heuristica admisible"), vectorizar("heuristica admisible")) > 0.99
    assert similitud_coseno(vectorizar("perceptron"), vectorizar("heuristica")) == 0


def test_recupera_el_fragmento_esperado():
    contexto = recuperar("que heuristica usa A estrella", fragmentar(DOC, 20, 5), k=1)
    assert "heuristica" in contexto[0]
    assert "no lo sabes" in construir_prompt("x", contexto)
''',
},
"agente": {
"agente.py": '''"""Agente con herramientas: registro, despacho con validacion de argumentos y trazas."""
import inspect


class ErrorHerramienta(Exception):
    pass


class Agente:
    def __init__(self):
        self.herramientas, self.trazas = {}, []

    def registrar(self, funcion, descripcion):
        """Registra una herramienta con nombre, descripcion y parametros tipados."""
        self.herramientas[funcion.__name__] = {"funcion": funcion, "descripcion": descripcion,
                                               "parametros": inspect.signature(funcion).parameters}

    def catalogo(self):
        return [{"nombre": n, "descripcion": h["descripcion"], "parametros": list(h["parametros"])}
                for n, h in self.herramientas.items()]

    def ejecutar(self, nombre, argumentos):
        """Despacha la llamada: valida herramienta y argumentos, ejecuta y deja traza auditable."""
        if nombre not in self.herramientas:
            self.trazas.append({"herramienta": nombre, "estado": "desconocida"})
            raise ErrorHerramienta(f"herramienta desconocida: {nombre}")
        h = self.herramientas[nombre]
        for p, spec in h["parametros"].items():
            if p not in argumentos:
                raise ErrorHerramienta(f"falta el argumento {p}")
            if spec.annotation is not inspect.Parameter.empty and not isinstance(argumentos[p], spec.annotation):
                raise ErrorHerramienta(f"el argumento {p} debe ser {spec.annotation.__name__}")
        try:
            resultado = h["funcion"](**argumentos)
        except Exception as e:
            self.trazas.append({"herramienta": nombre, "estado": "error", "detalle": str(e)})
            raise ErrorHerramienta(str(e)) from e
        self.trazas.append({"herramienta": nombre, "estado": "ok", "argumentos": argumentos, "resultado": resultado})
        return resultado


def dividir(a: float, b: float):
    return a / b


def verificar(resultado, minimo, maximo):
    """Verificacion del resultado antes de responder: debe estar en el rango esperado."""
    return minimo <= resultado <= maximo
''',
"test_agente.py": '''import pytest
from agente import Agente, ErrorHerramienta, dividir, verificar


@pytest.fixture
def agente():
    a = Agente()
    a.registrar(dividir, "Divide a entre b")
    return a


def test_despacho_y_traza(agente):
    assert agente.ejecutar("dividir", {"a": 10.0, "b": 4.0}) == 2.5
    assert agente.trazas[-1]["estado"] == "ok" and verificar(2.5, 0, 10)


def test_herramienta_desconocida(agente):
    with pytest.raises(ErrorHerramienta):
        agente.ejecutar("borrar_todo", {})


def test_valida_argumentos_y_errores(agente):
    with pytest.raises(ErrorHerramienta):
        agente.ejecutar("dividir", {"a": "10", "b": 2.0})
    with pytest.raises(ErrorHerramienta):
        agente.ejecutar("dividir", {"a": 1.0, "b": 0.0})
    assert agente.trazas[-1]["estado"] == "error"
''',
},
}

# --- informes de ejemplo (texto del PDF) ---------------------------------------------------------------

INFORMES = {
"busqueda": [
    ("Modelado del problema", "El laberinto se modela como un espacio de estados: cada estado es una celda (fila, columna) de la cuadricula, las acciones son moverse arriba, abajo, izquierda o derecha a una celda libre, el estado inicial es la entrada y la meta es la salida. Cada accion tiene costo 1. Se eligio esta representacion de la cuadricula porque permite generar los vecinos en tiempo constante."),
    ("Implementacion", "Se implementaron BFS y A* en busqueda.py. BFS usa una cola como frontera y expande por amplitud. A* usa una cola de prioridad con f = g + h, donde h es la heuristica Manhattan, que es admisible porque nunca sobreestima el costo real en una cuadricula sin diagonales. Ambos algoritmos reconstruyen la ruta con el diccionario de padres."),
    ("Pruebas unitarias", "Las pruebas unitarias cubren la ruta optima, un laberinto sin solucion y la heuristica. Todas pasan al ejecutar pytest."),
    ("Resultados", "En el laberinto de 4x4 ambos algoritmos encuentran una ruta de 7 celdas. BFS expande 9 nodos y A* expande 8 nodos."),
],
"knn": [
    ("Fundamentos", "En el aprendizaje supervisado se usa un conjunto de entrenamiento con etiquetas conocidas y un conjunto de prueba para medir el desempeno. k-NN no construye un modelo: para clasificar un punto busca los k vecinos mas cercanos y decide por votacion. Con k muy pequeno hay riesgo de sobreajuste al ruido; con k grande el modelo se vuelve demasiado general."),
    ("Implementacion del clasificador", "knn.py implementa la distancia euclidiana, la seleccion de los k vecinos ordenando por distancia y la votacion con un contador. El codigo es legible y cada funcion tiene una sola responsabilidad."),
    ("Evaluacion", "Se calcula la exactitud como aciertos sobre el total y la matriz de confusion por clase. Las pruebas unitarias comprueban la distancia, la votacion, la exactitud y la matriz de confusion, y todas pasan."),
    ("Efecto de k", "En las pruebas se uso k = 3. No se alcanzo a probar otros valores."),
],
"perceptron": [
    ("Regla de aprendizaje", "El perceptron calcula una suma ponderada de las entradas con sus pesos mas un sesgo y aplica una funcion de activacion escalon. Si la salida no coincide con la esperada, cada peso se actualiza sumando tasa por error por entrada. Por ejemplo, con entrada (1, 1), salida esperada 1 y salida 0, el error es 1 y los pesos aumentan en 0.1."),
    ("Entrenamiento", "perceptron.py implementa el entrenamiento por epocas y se detiene cuando no hay errores. Converge en AND en 4 epocas y en OR en 4 epocas con tasa 0.1. Las pruebas unitarias verifican la convergencia."),
    ("Limitacion con XOR", "Al entrenar con XOR durante 100 epocas el perceptron no converge: siempre queda al menos un caso mal clasificado. Esto ocurre porque XOR no es linealmente separable: ninguna recta separa las dos clases. Se necesita una capa oculta para combinar dos fronteras lineales."),
    ("Tasa de aprendizaje", "Se compararon tasas de aprendizaje de 0.01, 0.1 y 1.0. En AND convergio en 6 epocas con 0.01, en 4 epocas con 0.1 y en 6 epocas con 1.0: una tasa intermedia llego antes a la solucion, aunque con tan pocos datos la diferencia es pequena."),
],
"prompts": [
    ("Tecnicas de prompts", "Se disenaron dos prompts. El prompt zero-shot da la instruccion, las categorias permitidas y el formato de salida. El prompt few-shot agrega tres ejemplos de solicitud y categoria. La diferencia es que few-shot muestra al modelo el patron esperado con ejemplos, lo que reduce respuestas ambiguas."),
    ("Validacion de la salida", "La respuesta del modelo se valida contra un esquema: debe ser JSON, tener categoria, confianza y justificacion con el tipo correcto, la categoria debe estar en la lista y la confianza entre 0 y 1. Si la respuesta es invalida se reintenta hasta dos veces. Una categoria desconocida se trata como posible alucinacion."),
    ("Casos de prueba", "Las pruebas unitarias cubren una respuesta valida, una respuesta que no es JSON, una categoria desconocida y el reintento. Todas pasan."),
    ("Comparacion y confiabilidad", "Con 20 solicitudes de prueba el prompt zero-shot acerto 14 y el few-shot acerto 18. Los errores de zero-shot fueron categorias inventadas. La validacion del esquema evita que una alucinacion llegue al sistema, pero no garantiza que la categoria sea la correcta: por eso se necesita un conjunto de evaluacion."),
],
"rag": [
    ("Arquitectura RAG", "Un asistente RAG tiene cuatro etapas: fragmentacion de los documentos, representacion de cada fragmento como vector (embeddings), recuperacion de los fragmentos mas parecidos a la pregunta y generacion de la respuesta con ese contexto recuperado. El contexto reduce alucinaciones porque el modelo responde con informacion del documento y no solo con lo que recuerda."),
    ("Implementacion", "rag.py implementa la fragmentacion con solapamiento, la vectorizacion como bolsa de palabras, la similitud coseno y la recuperacion de los k fragmentos mas relevantes."),
    ("Evaluacion", "Las pruebas unitarias verifican la fragmentacion, la similitud y que la recuperacion devuelve el fragmento esperado para una pregunta sobre la heuristica. Todas pasan."),
    ("Limites y mejoras", "La bolsa de palabras solo coincide si la pregunta usa el mismo vocabulario del documento; no reconoce sinonimos. El tamano del fragmento tambien influye: fragmentos grandes mezclan temas. Como mejora se propone usar embeddings semanticos y una base vectorial."),
],
"agente": [
    ("Diseno", "El agente sigue el ciclo decidir, actuar y verificar. Cada herramienta se registra con nombre, descripcion y parametros tipados tomados de la firma de la funcion, y se publica en un catalogo que el modelo puede consultar."),
    ("Despacho y validacion", "agente.py implementa el registro y el despacho: comprueba que la herramienta exista, valida que esten todos los argumentos y que tengan el tipo esperado, ejecuta la funcion y captura los errores."),
    ("Verificacion", "Las pruebas unitarias cubren el despacho exitoso, una herramienta desconocida, argumentos invalidos y un error de ejecucion, ademas del registro de trazas. Todas pasan."),
    ("Trazabilidad y confianza", "Cada llamada deja una traza con herramienta, argumentos, resultado o error. Las trazas permiten auditar que hizo el agente y por que. La verificacion del resultado antes de responder evita propagar errores, y en acciones irreversibles debe intervenir una persona para aprobar."),
],
}

# Variante con vacíos (segundo estudiante de demostración)
INFORMES_DEBIL = {
"busqueda": [("Desarrollo", "Se programo una busqueda en el laberinto. El programa recorre las celdas hasta llegar a la salida usando BFS."),
             ("Resultados", "El programa encuentra la salida del laberinto de ejemplo.")],
"knn": [("Fundamentos", "k-NN clasifica un punto mirando sus vecinos mas cercanos."),
        ("Implementacion del clasificador", "Se implemento la distancia euclidiana y la votacion en knn.py."),
        ("Evaluacion", "Se calculo la exactitud del clasificador. Hay pruebas unitarias.")],
"perceptron": [("Regla de aprendizaje", "El perceptron ajusta sus pesos cuando se equivoca."),
               ("Entrenamiento", "Se entreno el perceptron con AND y OR por epocas."),
               ("Limitacion con XOR", "El perceptron no puede aprender XOR.")],
"prompts": [("Tecnicas de prompts", "Se uso un prompt zero-shot con las categorias permitidas y un prompt few-shot con ejemplos."),
            ("Validacion de la salida", "La respuesta se valida contra un esquema JSON y se reintenta si es invalida.")],
"agente": [("Diseno", "El agente tiene herramientas registradas con nombre y descripcion."),
           ("Despacho y validacion", "El despacho comprueba que la herramienta exista y ejecuta la funcion.")],
}

# (nombre, rol, aporte, fotografía en app/equipo/). Se cargan solo la primera vez; después se
# editan (y se cambia la fotografía) en Administración → Proyecto y equipo.
EQUIPO_PLANTILLA = [
    ("Esteban Carmona", "Líder técnico · Backend e IA",
     "Arquitectura del backend, motor de evaluación e integración de los modelos de IA.", "esteban.jpg"),
    ("Sergio Andrés Gómez", "Frontend y experiencia de usuario",
     "Interfaz web, flujo de revisión docente, informe integral y mapa de competencias.", "sergio.jpg"),
    ("Nicolás Herrera", "Calidad, pruebas y despliegue",
     "Pruebas, verificación en sandbox, documentación y publicación de la plataforma.", "nicolas.jpg"),
]

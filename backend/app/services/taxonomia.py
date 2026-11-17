"""Taxonomía de temáticas de IA. Sirve de vocabulario común para que temas de
laboratorios distintos (y de las dos cohortes) converjan en los mismos nodos
del mapa mental. El modelo puede proponer temas nuevos con tema_id="otro"."""
from __future__ import annotations

CATEGORIAS = {
    "fundamentos": "Fundamentos y agentes inteligentes",
    "busqueda": "Búsqueda y optimización",
    "conocimiento": "Conocimiento y razonamiento",
    "ml": "Aprendizaje automático",
    "dl": "Aprendizaje profundo",
    "pln": "Lenguaje natural y modelos de lenguaje",
    "vision": "Visión por computador",
    "genai": "IA generativa y agentes",
    "datos": "Datos e ingeniería de IA",
    "etica": "Ética y confianza en IA",
}

# id: (categoría, nombre, palabras clave para el modo simulado, temas relacionados)
TEMAS: dict[str, tuple[str, str, list[str], list[str]]] = {
    "agentes_racionales": ("fundamentos", "Agentes racionales y entornos", ["agente racional", "entorno", "percepcion", "peas", "actuador"], ["busqueda_no_informada", "agentes_llm"]),
    "busqueda_no_informada": ("busqueda", "Búsqueda no informada", ["bfs", "dfs", "amplitud", "profundidad", "costo uniforme", "frontera"], ["busqueda_heuristica"]),
    "busqueda_heuristica": ("busqueda", "Búsqueda heurística (A*)", ["a*", "a_estrella", "astar", "heuristica admisible", "manhattan", "cola de prioridad"], ["busqueda_adversaria", "optimizacion_metaheuristica"]),
    "busqueda_adversaria": ("busqueda", "Búsqueda adversaria y juegos", ["minimax", "alfa-beta", "alpha-beta", "poda", "juego"], []),
    "optimizacion_metaheuristica": ("busqueda", "Metaheurísticas de optimización", ["genetico", "recocido", "enjambre", "hill climbing", "mutacion", "cruce"], []),
    "csp": ("busqueda", "Satisfacción de restricciones", ["restricciones", "backtracking", "csp", "n reinas"], []),
    "logica_inferencia": ("conocimiento", "Lógica e inferencia", ["logica proposicional", "inferencia", "predicado", "prolog", "encadenamiento"], ["sistemas_expertos"]),
    "sistemas_expertos": ("conocimiento", "Sistemas expertos", ["sistema experto", "base de conocimiento", "motor de inferencia", "reglas"], []),
    "razonamiento_probabilistico": ("conocimiento", "Razonamiento probabilístico", ["bayes", "probabilidad", "red bayesiana", "markov", "naive bayes"], ["clasificacion"]),
    "logica_difusa": ("conocimiento", "Lógica difusa", ["difusa", "fuzzy", "pertenencia"], []),
    "regresion": ("ml", "Regresión", ["regresion lineal", "minimos cuadrados", "mse", "descenso de gradiente", "pendiente"], ["evaluacion_modelos", "redes_neuronales"]),
    "clasificacion": ("ml", "Clasificación supervisada", ["clasificacion supervisada", "clasificador", "knn", "k-nn", "vecinos mas cercanos", "arbol de decision", "svm", "regresion logistica"], ["evaluacion_modelos", "preprocesamiento_datos"]),
    "agrupamiento": ("ml", "Agrupamiento (no supervisado)", ["clustering", "k-means", "kmeans", "no supervisado", "centroide"], ["preprocesamiento_datos"]),
    "evaluacion_modelos": ("ml", "Evaluación y validación de modelos", ["accuracy", "exactitud", "recall", "f1", "matriz de confusion", "validacion cruzada", "sobreajuste", "overfitting"], []),
    "aprendizaje_refuerzo": ("ml", "Aprendizaje por refuerzo", ["refuerzo", "q-learning", "recompensa", "politica"], ["agentes_racionales"]),
    "redes_neuronales": ("dl", "Redes neuronales", ["perceptron", "red neuronal", "backpropagation", "retropropagacion", "funcion de activacion", "epocas", "capa oculta"], ["cnn", "transformers"]),
    "cnn": ("dl", "Redes convolucionales", ["convolucional", "cnn", "pooling", "kernel"], ["deteccion_reconocimiento"]),
    "rnn_secuencias": ("dl", "Modelos de secuencia (RNN/LSTM)", ["rnn", "lstm", "recurrente", "secuencia"], ["transformers"]),
    "transformers": ("dl", "Transformers y atención", ["transformer", "atencion", "attention", "self-attention"], ["llm_prompting", "embeddings_semanticos"]),
    "pln_clasico": ("pln", "Procesamiento clásico de lenguaje", ["tokenizacion", "tf-idf", "bolsa de palabras", "stopwords", "sentimiento", "lematizacion"], ["embeddings_semanticos"]),
    "llm_prompting": ("pln", "Modelos de lenguaje y diseño de prompts", ["prompt", "llm", "few-shot", "zero-shot", "modelo de lenguaje", "temperatura", "gemini", "gpt", "claude"], ["salidas_estructuradas", "rag", "evaluacion_llm"]),
    "embeddings_semanticos": ("pln", "Embeddings y búsqueda semántica", ["embedding", "vectorial", "similitud coseno", "semantica"], ["rag"]),
    "evaluacion_llm": ("pln", "Evaluación de modelos de lenguaje", ["alucinacion", "benchmark", "evaluacion del modelo", "groundedness"], ["explicabilidad_confianza"]),
    "rag": ("genai", "Generación aumentada por recuperación (RAG)", [" rag ", "recuperacion", "retrieval", "chunk", "fragmentacion", "base vectorial", "contexto recuperado"], ["agentes_llm"]),
    "agentes_llm": ("genai", "Agentes y uso de herramientas", ["function calling", "herramientas", "despacho", "orquestacion", "langchain", "catalogo", "multiagente"], ["salidas_estructuradas"]),
    "salidas_estructuradas": ("genai", "Salidas estructuradas y validación", ["json schema", "pydantic", "salida estructurada", "structured output", "esquema", "json valido"], ["explicabilidad_confianza"]),
    "ia_multimodal": ("genai", "IA generativa multimodal", ["multimodal", "generacion de imagenes", "difusion", "audio", "voz", "whisper", "tts"], ["vision_clasica"]),
    "desarrollo_asistido": ("genai", "Desarrollo de software asistido por IA", ["copilot", "asistente de codigo", "cursor", "claude code", "vibe coding", "pair programming"], ["mlops_despliegue"]),
    "vision_clasica": ("vision", "Procesamiento de imágenes", ["opencv", "filtro", "bordes", "segmentacion", "histograma", "pixel"], ["cnn"]),
    "deteccion_reconocimiento": ("vision", "Detección y reconocimiento visual", ["deteccion de objetos", "yolo", "reconocimiento facial", "ocr"], []),
    "preprocesamiento_datos": ("datos", "Preparación y análisis de datos", ["normalizacion", "limpieza", "dataset", "pandas", "caracteristicas", "features", "train_test_split", "escalado"], []),
    "mlops_despliegue": ("datos", "Despliegue e ingeniería de sistemas de IA", ["despliegue", "fastapi", "docker", "api rest", "produccion", "pipeline", "endpoint"], []),
    "etica_sesgos": ("etica", "Ética, sesgos y privacidad", ["sesgo algoritmico", "sesgos", "etica", "equidad", "privacidad", "datos personales"], ["explicabilidad_confianza"]),
    "explicabilidad_confianza": ("etica", "Explicabilidad, trazabilidad y confianza", ["explicabilidad", "interpretabilidad", "trazabilidad", "auditar", "auditable", "supervision humana"], []),
}


def texto_para_prompt() -> str:
    lineas = []
    for cat_id, cat in CATEGORIAS.items():
        lineas.append(f"[{cat_id}] {cat}")
        for tid, (c, nombre, _, _) in TEMAS.items():
            if c == cat_id:
                lineas.append(f"  - {tid}: {nombre}")
    return "\n".join(lineas)


def etiqueta_dominio(puntaje: float | None) -> str:
    """Escala nacional de desempeño usada para comunicar el nivel de dominio."""
    if puntaje is None:
        return "Sin evidencia"
    if puntaje >= 4.6:
        return "Superior"
    if puntaje >= 4.0:
        return "Alto"
    if puntaje >= 3.0:
        return "Básico"
    return "Bajo"

"""Capa de abstracción de modelos de IA (condición 4: conexión configurable con
modelos locales o servicios en la nube).

Todos los proveedores exponen `generar_json`. `generar_estructurado` añade lo
que hace confiable el resultado: validación con Pydantic y reintento con el
error de validación como retroalimentación."""
from __future__ import annotations

import copy
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class ErrorIA(RuntimeError):
    pass


@dataclass
class Adjunto:
    nombre: str
    mime: str
    datos: bytes


@dataclass
class RespuestaIA:
    texto: str
    datos: Any = None
    uso: dict = field(default_factory=dict)
    modelo: str = ""
    intentos: int = 1


class ProveedorIA:
    nombre = "base"
    multimodal = False
    acepta_pdf = False

    def __init__(self, *, modelo: str, api_key: str = "", base_url: str = "", temperatura: float | None = None,
                 timeout_s: int = 180, transporte: httpx.BaseTransport | None = None):
        self.modelo, self.api_key, self.base_url = modelo, api_key, base_url.rstrip("/")
        self.temperatura, self.timeout_s = temperatura, timeout_s
        self._transporte = transporte

    def _cliente(self) -> httpx.Client:
        return httpx.Client(timeout=httpx.Timeout(self.timeout_s, connect=20), transport=self._transporte)

    def _post(self, url: str, cuerpo: dict, cabeceras: dict) -> httpx.Response:
        """POST con reintentos ante límites de cuota y errores transitorios."""
        ultimo: Exception | None = None
        with self._cliente() as c:
            for intento in range(4):
                try:
                    r = c.post(url, json=cuerpo, headers=cabeceras)
                except httpx.TimeoutException as e:
                    # Sin respuesta en el tiempo límite: no se insiste con el mismo modelo (cada intento
                    # costaría otros minutos); el proveedor puede pasar a un modelo de respaldo.
                    error = ErrorIA(f"El modelo no respondió en {self.timeout_s} s ({self.nombre}): {type(e).__name__}.")
                    error.codigo = "timeout"
                    raise error from e
                except httpx.HTTPError as e:
                    ultimo = e
                    time.sleep(min(2 ** intento, 8))
                    continue
                if r.status_code == 429 and intento >= 1:
                    return r  # cuota agotada: un solo reintento; después se prueba otro modelo
                if r.status_code in (429, 500, 502, 503, 504, 529) and intento < 3:
                    espera = r.headers.get("retry-after")
                    m = re.search(r'"retryDelay":\s*"(\d+)', r.text)
                    seg = float(espera) if espera and espera.replace(".", "").isdigit() else float(m.group(1)) if m else 2 ** (intento + 1)
                    time.sleep(min(seg, 45))
                    continue
                return r
        raise ErrorIA(f"No se pudo contactar al servicio de IA ({self.nombre}): {ultimo}")

    @staticmethod
    def _error(r: httpx.Response, proveedor: str) -> ErrorIA:
        try:
            cuerpo = r.json()
            msg = cuerpo.get("error", {}).get("message") if isinstance(cuerpo.get("error"), dict) else cuerpo.get("error") or r.text
        except ValueError:
            msg = r.text
        pistas = {401: "La clave de API no es válida.", 403: "La clave de API no tiene permiso para este modelo.",
                  404: "El modelo configurado no existe o no está disponible para esta clave.",
                  429: "Se alcanzó el límite de uso del servicio; intenta de nuevo en unos minutos."}
        pistas[503] = "El modelo está saturado en este momento; vuelve a intentarlo en unos minutos o elige otro modelo."
        error = ErrorIA(f"{proveedor} respondió {r.status_code}. {pistas.get(r.status_code, '')} Detalle: {str(msg)[:400]}")
        error.codigo = r.status_code
        return error

    # --- interfaz -----------------------------------------------------------------
    def generar_json(self, *, sistema: str, usuario: str, esquema: dict, adjuntos: list[Adjunto] | None = None,
                     contexto: dict | None = None) -> RespuestaIA:
        raise NotImplementedError

    def listar_modelos(self) -> list[str]:
        return []


def esquema_plano(modelo: type[BaseModel]) -> dict:
    """JSON Schema del modelo Pydantic con las referencias $ref resueltas en línea
    y sin palabras clave que algunos proveedores rechazan."""
    esquema = modelo.model_json_schema()
    defs = esquema.pop("$defs", {})

    def resolver(nodo):
        if isinstance(nodo, dict):
            if "$ref" in nodo:
                nombre = nodo["$ref"].rsplit("/", 1)[-1]
                base = resolver(copy.deepcopy(defs[nombre]))
                extra = {k: v for k, v in nodo.items() if k != "$ref"}
                base.update(extra)
                return base
            if "allOf" in nodo and len(nodo["allOf"]) == 1:
                base = resolver(nodo["allOf"][0])
                base.update({k: resolver(v) for k, v in nodo.items() if k != "allOf"})
                return base
            return {k: resolver(v) for k, v in nodo.items() if k not in ("title", "default")}
        if isinstance(nodo, list):
            return [resolver(x) for x in nodo]
        return nodo

    return resolver(esquema)


def extraer_json(texto: str) -> Any:
    """Tolera respuestas envueltas en ```json … ``` o con texto alrededor."""
    texto = texto.strip()
    m = re.search(r"```(?:json)?\s*(.+?)```", texto, re.S)
    if m:
        texto = m.group(1).strip()
    try:
        return json.loads(texto)
    except ValueError:
        ini, fin = texto.find("{"), texto.rfind("}")
        if ini >= 0 and fin > ini:
            return json.loads(texto[ini:fin + 1])
        raise


def generar_estructurado(proveedor: ProveedorIA, modelo: type[T], *, sistema: str, usuario: str,
                         adjuntos: list[Adjunto] | None = None, contexto: dict | None = None,
                         validar_extra=None, reintentos: int = 2) -> tuple[T, RespuestaIA]:
    """Pide una respuesta que cumpla el esquema de `modelo` y la valida.
    `validar_extra(obj)` puede devolver una lista de errores semánticos
    (p. ej. criterios faltantes) que también disparan un reintento."""
    esquema = esquema_plano(modelo)
    mensaje = usuario
    uso_total: dict[str, int] = {}
    ultimo_error = ""
    for intento in range(1, reintentos + 2):
        resp = proveedor.generar_json(sistema=sistema, usuario=mensaje, esquema=esquema, adjuntos=adjuntos, contexto=contexto)
        for k, v in (resp.uso or {}).items():
            if isinstance(v, (int, float)):
                uso_total[k] = uso_total.get(k, 0) + v
        try:
            datos = resp.datos if resp.datos is not None else extraer_json(resp.texto)
            obj = modelo.model_validate(datos)
            errores = validar_extra(obj) if validar_extra else []
            if not errores:
                resp.uso, resp.intentos = uso_total, intento
                return obj, resp
            ultimo_error = "; ".join(errores)
        except (ValidationError, ValueError) as e:
            ultimo_error = str(e)[:1500]
        mensaje = (usuario + "\n\n---\nTu respuesta anterior NO fue aceptada por el validador. Corrige y responde de nuevo "
                   "con el JSON completo.\nErrores: " + ultimo_error)
    raise ErrorIA("El modelo no produjo una respuesta válida según el esquema tras "
                  f"{reintentos + 1} intentos. Último error: {ultimo_error[:600]}")

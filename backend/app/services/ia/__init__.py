"""Selección del proveedor de IA. La configuración efectiva es: lo guardado en
Administración → Modelo de IA (tabla config) y, si no hay, las variables de entorno."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ...config import MODELOS_POR_DEFECTO, URLS_POR_DEFECTO, obtener_ajustes
from ...models import Config
from ...security import cifrar, descifrar
from .anthropic import Anthropic
from .base import Adjunto, ErrorIA, ProveedorIA, RespuestaIA, generar_estructurado  # noqa: F401
from .gemini import Gemini
from .openai_compat import Ollama, OpenAICompatible
from .simulado import Simulado

CLASES = {"gemini": Gemini, "openai": OpenAICompatible, "anthropic": Anthropic, "ollama": Ollama, "simulado": Simulado}

# Temperatura por defecto. Para Gemini se deja la del servicio: Google recomienda
# no bajarla en la serie 3.x; la reproducibilidad se asegura con salida
# estructurada, reutilización por huella y pasadas de consistencia.
TEMPERATURA_DEFECTO = {"gemini": None, "openai": 0.0, "anthropic": 0.0, "ollama": 0.0, "simulado": 0.0}


def _clave_entorno(proveedor: str) -> str:
    aj = obtener_ajustes()
    return {"gemini": aj.gemini_api_key, "openai": aj.openai_api_key, "anthropic": aj.anthropic_api_key}.get(proveedor, "")


def config_ia(db: Session) -> dict:
    """Configuración efectiva (sin exponer la clave)."""
    aj = obtener_ajustes()
    fila = db.get(Config, "ia")
    g = dict(fila.valor) if fila else {}
    proveedor = g.get("proveedor") or aj.ia_proveedor
    if proveedor not in CLASES:
        proveedor = "simulado"
    mismo = proveedor == aj.ia_proveedor
    clave_bd = descifrar(g.get("api_key_cifrada", "")) if g.get("api_key_cifrada") and g.get("proveedor") == proveedor else ""
    temp = g["temperatura"] if "temperatura" in g else (aj.ia_temperatura if aj.ia_temperatura is not None else TEMPERATURA_DEFECTO[proveedor])
    return {
        "proveedor": proveedor,
        "modelo": g.get("modelo") or (aj.ia_modelo if mismo and aj.ia_modelo else MODELOS_POR_DEFECTO[proveedor]),
        "base_url": g.get("base_url") or (aj.ia_base_url if mismo and aj.ia_base_url else URLS_POR_DEFECTO[proveedor]),
        "temperatura": temp,
        "multimodal": g.get("multimodal", aj.ia_multimodal),
        "pasadas_consistencia": int(g.get("pasadas_consistencia", aj.ia_pasadas_consistencia) or 1),
        "_api_key": clave_bd or _clave_entorno(proveedor),
        "origen_clave": "administración" if clave_bd else ("variable de entorno" if _clave_entorno(proveedor) else "sin clave"),
    }


def guardar_config_ia(db: Session, datos: dict) -> None:
    fila = db.get(Config, "ia")
    actual = dict(fila.valor) if fila else {}
    cambia_proveedor = datos.get("proveedor") and datos.get("proveedor") != actual.get("proveedor")
    for k in ("proveedor", "modelo", "base_url", "temperatura", "multimodal", "pasadas_consistencia"):
        if k in datos:
            actual[k] = datos[k]
    if cambia_proveedor and not datos.get("api_key"):
        actual.pop("api_key_cifrada", None)
    if datos.get("api_key"):
        actual["api_key_cifrada"] = cifrar(datos["api_key"])
    if datos.get("borrar_api_key"):
        actual.pop("api_key_cifrada", None)
    if fila:
        fila.valor = actual
    else:
        db.add(Config(clave="ia", valor=actual))


def crear_proveedor(cfg: dict, transporte=None) -> ProveedorIA:
    return CLASES[cfg["proveedor"]](modelo=cfg["modelo"], api_key=cfg.get("_api_key", ""), base_url=cfg.get("base_url", ""),
                                    temperatura=cfg.get("temperatura"), timeout_s=obtener_ajustes().ia_timeout_s,
                                    transporte=transporte)


def obtener_proveedor(db: Session) -> tuple[ProveedorIA, dict]:
    cfg = config_ia(db)
    return crear_proveedor(cfg), cfg

"""Configuración central de la plataforma (variables de entorno, ver .env.example)."""
from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_BACKEND = Path(__file__).resolve().parent.parent
RAIZ_PROYECTO = RAIZ_BACKEND.parent


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(RAIZ_PROYECTO / ".env", RAIZ_BACKEND / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Aplicación -------------------------------------------------------
    app_nombre: str = "Asesor Pedagógico Inteligente"
    entorno: str = "desarrollo"  # desarrollo | produccion | pruebas
    secret_key: str = ""
    access_token_min: int = 480
    database_url: str = f"sqlite:///{RAIZ_BACKEND / 'data' / 'asesor.db'}"
    frontend_dist: str = str(RAIZ_PROYECTO / "frontend" / "dist")
    cors_origenes: str = ""  # separados por coma; vacío = mismo origen
    max_upload_mb: int = 25

    # --- Usuarios ---------------------------------------------------------
    admin_email: str = "admin@asesor.edu.co"
    admin_password: str = ""
    admin_nombre: str = "Administración"
    registro_abierto: bool = True
    seed_demo: bool = False

    # --- Inteligencia artificial -----------------------------------------
    ia_proveedor: str = "simulado"  # gemini | openai | anthropic | ollama | simulado
    ia_modelo: str = ""
    ia_base_url: str = ""
    ia_temperatura: float | None = None  # None = valor recomendado por proveedor
    ia_timeout_s: int = 180
    ia_max_caracteres_evidencia: int = 180_000
    ia_multimodal: bool = True
    ia_pasadas_consistencia: int = 1
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # --- Sandbox de verificación técnica ---------------------------------
    sandbox_habilitado: bool = True
    sandbox_timeout_s: int = 60
    sandbox_cpu_s: int = 30
    sandbox_prueba_s: int = 10  # límite por prueba: una prueba colgada no borra el resultado de las demás
    sandbox_memoria_mb: int = 1024
    sandbox_permitir_red: bool = False

    @field_validator("database_url")
    @classmethod
    def _normalizar_bd(cls, v: str) -> str:
        # Render/Heroku entregan postgres:// o postgresql://; SQLAlchemy 2 + psycopg 3
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    @field_validator("ia_temperatura", mode="before")
    @classmethod
    def _temp_vacia(cls, v):
        return None if v in ("", None) else v


@lru_cache
def obtener_ajustes() -> Ajustes:
    a = Ajustes()
    if not a.secret_key:
        # Sin SECRET_KEY las sesiones no sobreviven a un reinicio. Aceptable en
        # desarrollo; en producción debe definirse (render.yaml la genera).
        a.secret_key = secrets.token_urlsafe(48)
    return a


MODELOS_POR_DEFECTO = {
    # Verificado en la documentación oficial de Gemini (nov. 2026). Cambiable
    # desde Administración → Modelo de IA sin tocar código.
    "gemini": "gemini-3.8-flash",
    "anthropic": "claude-sonnet-5-5",
    "openai": "",
    "ollama": "llama3.1",
    "simulado": "heuristico-v1",
}

URLS_POR_DEFECTO = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "ollama": "http://localhost:11434/v1",
    "simulado": "",
}

from __future__ import annotations

import base64
import hashlib
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from .config import obtener_ajustes

ALGORITMO = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode()


def verificar_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode())
    except ValueError:
        return False


def crear_token(usuario_id: int, rol: str) -> str:
    aj = obtener_ajustes()
    exp = datetime.now(timezone.utc) + timedelta(minutes=aj.access_token_min)
    return jwt.encode({"sub": str(usuario_id), "rol": rol, "exp": exp}, aj.secret_key, algorithm=ALGORITMO)


def leer_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, obtener_ajustes().secret_key, algorithms=[ALGORITMO])
    except jwt.PyJWTError:
        return None


def _fernet() -> Fernet:
    clave = hashlib.sha256(("cfg:" + obtener_ajustes().secret_key).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(clave))


def cifrar(texto: str) -> str:
    return _fernet().encrypt(texto.encode()).decode()


def descifrar(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return ""


class LimitadorIntentos:
    """Freno simple a fuerza bruta en el inicio de sesión (en memoria)."""

    def __init__(self, maximo: int = 8, ventana_s: int = 300):
        self.maximo, self.ventana_s = maximo, ventana_s
        self._intentos: dict[str, list[float]] = defaultdict(list)

    def bloqueado(self, clave: str) -> bool:
        t = time.time()
        self._intentos[clave] = [x for x in self._intentos[clave] if t - x < self.ventana_s]
        return len(self._intentos[clave]) >= self.maximo

    def registrar_fallo(self, clave: str) -> None:
        self._intentos[clave].append(time.time())

    def limpiar(self, clave: str) -> None:
        self._intentos.pop(clave, None)


limitador_login = LimitadorIntentos()

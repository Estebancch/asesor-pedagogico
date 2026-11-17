from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .db import obtener_db
from .models import Auditoria, Usuario
from .security import leer_token


def usuario_actual(request: Request, db: Session = Depends(obtener_db)) -> Usuario:
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else ""
    datos = leer_token(token) if token else None
    if not datos:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no válida o vencida. Inicia sesión de nuevo.")
    usuario = db.get(Usuario, int(datos["sub"]))
    if not usuario or not usuario.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "La cuenta no existe o está desactivada.")
    return usuario


def requiere(*roles: str):
    def _dep(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Tu rol no tiene permiso para esta acción.")
        return usuario
    return _dep


docente_o_admin = requiere("docente", "admin")
solo_admin = requiere("admin")


def es_docente(u: Usuario) -> bool:
    return u.rol in ("docente", "admin")


def auditar(db: Session, usuario: Usuario | None, accion: str, entidad: str,
            entidad_id: int | None = None, detalle: dict | None = None) -> None:
    db.add(Auditoria(usuario_id=usuario.id if usuario else None, accion=accion,
                     entidad=entidad, entidad_id=entidad_id, detalle=detalle or {}))

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import obtener_ajustes
from ..db import obtener_db
from ..deps import auditar, docente_o_admin, solo_admin, usuario_actual
from ..models import Usuario
from ..security import crear_token, hash_password, limitador_login, verificar_password

router = APIRouter(prefix="/api", tags=["usuarios"])
RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def publico(u: Usuario) -> dict:
    return {"id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol, "codigo": u.codigo, "activo": u.activo,
            "creado_en": u.creado_en.isoformat() if u.creado_en else None}


def _validar_password(p: str) -> str:
    if len(p) < 8 or not re.search(r"[A-Za-z]", p) or not re.search(r"\d", p):
        raise ValueError("La contraseña debe tener al menos 8 caracteres e incluir letras y números.")
    return p


class Credenciales(BaseModel):
    email: str
    password: str


class Registro(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    email: str
    password: str
    codigo: str = ""

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        v = v.strip().lower()
        if not RE_EMAIL.match(v):
            raise ValueError("Escribe un correo válido.")
        return v

    @field_validator("password")
    @classmethod
    def _clave(cls, v):
        return _validar_password(v)


class UsuarioNuevo(Registro):
    rol: str = "estudiante"


class UsuarioCambio(BaseModel):
    nombre: str | None = None
    rol: str | None = None
    codigo: str | None = None
    activo: bool | None = None
    password: str | None = None


class CambioPassword(BaseModel):
    actual: str
    nueva: str

    @field_validator("nueva")
    @classmethod
    def _clave(cls, v):
        return _validar_password(v)


@router.post("/auth/login")
def login(datos: Credenciales, request: Request, db: Session = Depends(obtener_db)):
    email = datos.email.strip().lower()
    clave = f"{email}|{request.client.host if request.client else ''}"
    if limitador_login.bloqueado(clave):
        raise HTTPException(429, "Demasiados intentos fallidos. Espera unos minutos e inténtalo de nuevo.")
    u = db.scalars(select(Usuario).where(func.lower(Usuario.email) == email)).first()
    if not u or not u.activo or not verificar_password(datos.password, u.password_hash):
        limitador_login.registrar_fallo(clave)
        raise HTTPException(401, "Correo o contraseña incorrectos.")
    limitador_login.limpiar(clave)
    return {"token": crear_token(u.id, u.rol), "usuario": publico(u)}


@router.post("/auth/registro", status_code=201)
def registro(datos: Registro, db: Session = Depends(obtener_db)):
    if not obtener_ajustes().registro_abierto:
        raise HTTPException(403, "El registro está cerrado. Pide tu cuenta al docente o al administrador.")
    if db.scalars(select(Usuario).where(func.lower(Usuario.email) == datos.email)).first():
        raise HTTPException(409, "Ya existe una cuenta con ese correo.")
    u = Usuario(nombre=datos.nombre.strip(), email=datos.email, password_hash=hash_password(datos.password),
                rol="estudiante", codigo=datos.codigo.strip())
    db.add(u)
    db.flush()
    auditar(db, u, "registro", "usuario", u.id)
    db.commit()
    return {"token": crear_token(u.id, u.rol), "usuario": publico(u)}


@router.get("/auth/yo")
def yo(u: Usuario = Depends(usuario_actual)):
    return publico(u)


@router.post("/auth/cambiar-password")
def cambiar_password(datos: CambioPassword, u: Usuario = Depends(usuario_actual), db: Session = Depends(obtener_db)):
    if not verificar_password(datos.actual, u.password_hash):
        raise HTTPException(400, "La contraseña actual no coincide.")
    u.password_hash = hash_password(datos.nueva)
    auditar(db, u, "cambio_password", "usuario", u.id)
    db.commit()
    return {"ok": True}


@router.get("/usuarios")
def listar(rol: str | None = None, u: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    q = select(Usuario).order_by(Usuario.rol, Usuario.nombre)
    if u.rol != "admin":
        q = q.where(Usuario.rol == "estudiante")
    elif rol:
        q = q.where(Usuario.rol == rol)
    return [publico(x) for x in db.scalars(q)]


@router.post("/usuarios", status_code=201)
def crear(datos: UsuarioNuevo, actor: Usuario = Depends(docente_o_admin), db: Session = Depends(obtener_db)):
    if datos.rol not in ("admin", "docente", "estudiante"):
        raise HTTPException(422, "Rol no válido.")
    if actor.rol != "admin" and datos.rol != "estudiante":
        raise HTTPException(403, "Solo un administrador puede crear docentes o administradores.")
    if db.scalars(select(Usuario).where(func.lower(Usuario.email) == datos.email)).first():
        raise HTTPException(409, "Ya existe una cuenta con ese correo.")
    u = Usuario(nombre=datos.nombre.strip(), email=datos.email, password_hash=hash_password(datos.password),
                rol=datos.rol, codigo=datos.codigo.strip())
    db.add(u)
    db.flush()
    auditar(db, actor, "usuario_creado", "usuario", u.id, {"rol": u.rol})
    db.commit()
    return publico(u)


@router.patch("/usuarios/{uid}")
def modificar(uid: int, datos: UsuarioCambio, actor: Usuario = Depends(solo_admin), db: Session = Depends(obtener_db)):
    u = db.get(Usuario, uid)
    if not u:
        raise HTTPException(404, "Usuario no encontrado.")
    cambios = datos.model_dump(exclude_none=True)
    if "rol" in cambios and cambios["rol"] not in ("admin", "docente", "estudiante"):
        raise HTTPException(422, "Rol no válido.")
    if u.id == actor.id and (cambios.get("activo") is False or cambios.get("rol", "admin") != "admin"):
        raise HTTPException(400, "No puedes desactivar tu propia cuenta ni quitarte el rol de administrador.")
    if "password" in cambios:
        try:
            u.password_hash = hash_password(_validar_password(cambios.pop("password")))
        except ValueError as e:
            raise HTTPException(422, str(e))
    for k, v in cambios.items():
        setattr(u, k, v.strip() if isinstance(v, str) else v)
    auditar(db, actor, "usuario_modificado", "usuario", u.id, {"campos": sorted(datos.model_dump(exclude_none=True))})
    db.commit()
    return publico(u)

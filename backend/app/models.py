"""Modelo de datos. Las evaluaciones conservan todo lo necesario para auditar
un resultado: evidencias analizadas, versión de rúbrica, modelo, pruebas y
justificaciones (condición 6 del enunciado)."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer,
                        LargeBinary, String, Text, TypeDecorator, UniqueConstraint)
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from .db import Base


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class FechaUTC(TypeDecorator):
    """Fecha y hora siempre en UTC y con zona. SQLite descarta la zona al guardar;
    aquí se repone al leer para que la API entregue siempre ISO 8601 con +00:00
    y el navegador la convierta bien a la hora local."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(20), default="estudiante")  # admin|docente|estudiante
    codigo: Mapped[str] = mapped_column(String(40), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(FechaUTC, default=ahora)


class Cohorte(Base):
    __tablename__ = "cohortes"
    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(Integer, unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    periodo: Mapped[str] = mapped_column(String(60), default="")
    descripcion: Mapped[str] = mapped_column(Text, default="")
    laboratorios: Mapped[list["Laboratorio"]] = relationship(
        back_populates="cohorte", order_by="Laboratorio.orden", cascade="all, delete-orphan")


class Laboratorio(Base):
    __tablename__ = "laboratorios"
    id: Mapped[int] = mapped_column(primary_key=True)
    cohorte_id: Mapped[int] = mapped_column(ForeignKey("cohortes.id"))
    orden: Mapped[int] = mapped_column(Integer, default=1)
    titulo: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    objetivos: Mapped[str] = mapped_column(Text, default="")
    fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    pruebas_docente: Mapped[str] = mapped_column(Text, default="")  # pytest opcional
    creado_en: Mapped[datetime] = mapped_column(FechaUTC, default=ahora)
    cohorte: Mapped[Cohorte] = relationship(back_populates="laboratorios")
    rubricas: Mapped[list["RubricaVersion"]] = relationship(
        back_populates="laboratorio", order_by="RubricaVersion.version", cascade="all, delete-orphan")
    entregas: Mapped[list["Entrega"]] = relationship(back_populates="laboratorio", cascade="all, delete-orphan")


class Archivo(Base):
    """Almacenamiento de archivos dentro de la base de datos. Decisión de
    ingeniería: en hosting gratuito el disco es efímero; así la BD es el único
    punto de persistencia y respaldo."""
    __tablename__ = "archivos"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(260))
    mime: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    tamano: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    contenido: Mapped[bytes] = deferred(mapped_column(LargeBinary))
    subido_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(FechaUTC, default=ahora)


class RubricaVersion(Base):
    __tablename__ = "rubrica_versiones"
    __table_args__ = (UniqueConstraint("laboratorio_id", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    laboratorio_id: Mapped[int] = mapped_column(ForeignKey("laboratorios.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    estado: Mapped[str] = mapped_column(String(20), default="borrador")  # borrador|validada
    contenido: Mapped[dict] = mapped_column(JSON, default=dict)
    inconsistencias: Mapped[list] = mapped_column(JSON, default=list)
    hash: Mapped[str] = mapped_column(String(64), default="")
    origen: Mapped[str] = mapped_column(String(30), default="manual")
    interpretada_por: Mapped[str] = mapped_column(String(120), default="")
    archivo_id: Mapped[int | None] = mapped_column(ForeignKey("archivos.id"), nullable=True)
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(FechaUTC, default=ahora)
    validada_en: Mapped[datetime | None] = mapped_column(FechaUTC, nullable=True)
    laboratorio: Mapped[Laboratorio] = relationship(back_populates="rubricas")
    archivo: Mapped[Archivo | None] = relationship()


class Entrega(Base):
    __tablename__ = "entregas"
    id: Mapped[int] = mapped_column(primary_key=True)
    laboratorio_id: Mapped[int] = mapped_column(ForeignKey("laboratorios.id"), index=True)
    estudiante_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    numero: Mapped[int] = mapped_column(Integer, default=1)  # intento
    rubrica_version_id: Mapped[int | None] = mapped_column(ForeignKey("rubrica_versiones.id"), nullable=True)
    informe_id: Mapped[int | None] = mapped_column(ForeignKey("archivos.id"), nullable=True)
    codigo_id: Mapped[int | None] = mapped_column(ForeignKey("archivos.id"), nullable=True)
    repo_url: Mapped[str] = mapped_column(String(300), default="")
    repo_commit: Mapped[str] = mapped_column(String(80), default="")
    video_url: Mapped[str] = mapped_column(String(300), default="")
    presentacion_id: Mapped[int | None] = mapped_column(ForeignKey("archivos.id"), nullable=True)
    presentacion_url: Mapped[str] = mapped_column(String(300), default="")
    comentario: Mapped[str] = mapped_column(Text, default="")
    creado_en: Mapped[datetime] = mapped_column(FechaUTC, default=ahora)
    laboratorio: Mapped[Laboratorio] = relationship(back_populates="entregas")
    estudiante: Mapped[Usuario] = relationship()
    rubrica_version: Mapped[RubricaVersion | None] = relationship()
    informe: Mapped[Archivo | None] = relationship(foreign_keys=[informe_id])
    codigo: Mapped[Archivo | None] = relationship(foreign_keys=[codigo_id])
    presentacion: Mapped[Archivo | None] = relationship(foreign_keys=[presentacion_id])
    evaluaciones: Mapped[list["Evaluacion"]] = relationship(
        back_populates="entrega", order_by="Evaluacion.id", cascade="all, delete-orphan")


class Evaluacion(Base):
    __tablename__ = "evaluaciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    entrega_id: Mapped[int] = mapped_column(ForeignKey("entregas.id"), index=True)
    rubrica_version_id: Mapped[int] = mapped_column(ForeignKey("rubrica_versiones.id"))
    # en_cola | procesando | preliminar | aprobada | publicada | error
    estado: Mapped[str] = mapped_column(String(20), default="en_cola", index=True)
    progreso: Mapped[str] = mapped_column(String(200), default="")
    proveedor: Mapped[str] = mapped_column(String(40), default="")
    modelo: Mapped[str] = mapped_column(String(120), default="")
    parametros: Mapped[dict] = mapped_column(JSON, default=dict)
    prompt_version: Mapped[str] = mapped_column(String(40), default="")
    hash_evidencias: Mapped[str] = mapped_column(String(64), default="")
    clave_reproducibilidad: Mapped[str] = mapped_column(String(64), default="", index=True)
    evidencias: Mapped[dict] = mapped_column(JSON, default=dict)  # manifiesto
    evidencias_texto: Mapped[dict] = deferred(mapped_column(JSON, default=dict))  # fuente -> texto
    verificacion: Mapped[dict] = mapped_column(JSON, default=dict)
    resultado_ia: Mapped[dict] = deferred(mapped_column(JSON, default=dict))  # salida validada, inmutable
    resultado: Mapped[dict] = mapped_column(JSON, default=dict)  # vigente (con ajustes docentes)
    calculo: Mapped[dict] = mapped_column(JSON, default=dict)
    nota_preliminar: Mapped[float | None] = mapped_column(Float, nullable=True)
    nota_final: Mapped[float | None] = mapped_column(Float, nullable=True)
    observacion_docente: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    uso: Mapped[dict] = mapped_column(JSON, default=dict)
    duracion_s: Mapped[float] = mapped_column(Float, default=0)
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(FechaUTC, default=ahora)
    aprobado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    aprobado_en: Mapped[datetime | None] = mapped_column(FechaUTC, nullable=True)
    publicado_en: Mapped[datetime | None] = mapped_column(FechaUTC, nullable=True)
    entrega: Mapped[Entrega] = relationship(back_populates="evaluaciones")
    rubrica_version: Mapped[RubricaVersion] = relationship()


class Auditoria(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    accion: Mapped[str] = mapped_column(String(80))
    entidad: Mapped[str] = mapped_column(String(40), index=True)
    entidad_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    detalle: Mapped[dict] = mapped_column(JSON, default=dict)
    creado_en: Mapped[datetime] = mapped_column(FechaUTC, default=ahora)
    usuario: Mapped[Usuario | None] = relationship()


class Informe(Base):
    __tablename__ = "informes"
    id: Mapped[int] = mapped_column(primary_key=True)
    estudiante_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    alcance: Mapped[str] = mapped_column(String(20), default="publicadas")
    contenido: Mapped[dict] = mapped_column(JSON, default=dict)
    modelo: Mapped[str] = mapped_column(String(120), default="")
    creado_en: Mapped[datetime] = mapped_column(FechaUTC, default=ahora)


class Config(Base):
    __tablename__ = "config"
    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[dict] = mapped_column(JSON, default=dict)


class Integrante(Base):
    __tablename__ = "integrantes"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160))
    rol: Mapped[str] = mapped_column(String(160), default="")
    descripcion: Mapped[str] = mapped_column(Text, default="")
    enlace: Mapped[str] = mapped_column(String(300), default="")
    foto_id: Mapped[int | None] = mapped_column(ForeignKey("archivos.id"), nullable=True)
    orden: Mapped[int] = mapped_column(Integer, default=1)

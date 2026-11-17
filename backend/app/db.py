from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import obtener_ajustes

_aj = obtener_ajustes()
_es_sqlite = _aj.database_url.startswith("sqlite")
if _es_sqlite:
    ruta = _aj.database_url.split("sqlite:///", 1)[-1]
    if ruta and ruta != ":memory:":
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    _aj.database_url,
    connect_args={"check_same_thread": False, "timeout": 30} if _es_sqlite else {},
    pool_pre_ping=True,
)

if _es_sqlite:
    @event.listens_for(engine, "connect")
    def _pragma(dbapi_con, _):  # integridad referencial y mejor concurrencia
        cur = dbapi_con.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()

SesionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def obtener_db():
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()

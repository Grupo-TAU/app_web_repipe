import re
from dataclasses import dataclass, field
from datetime import date

ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")  # mismo criterio que el CHECK de la base


def id_valido(texto: str) -> bool:
    return bool(ID_RE.fullmatch(texto or ""))


@dataclass
class Observacion:
    obs_interna: str


@dataclass
class Patologia:
    patologia: str
    metros: float | None = None
    nro_figura: int | None = None


@dataclass
class Inspeccion:
    id: str
    ubicacion: str
    solicitante: str | None = None
    operario: str | None = None
    fecha: date | None = None
    acceso: str | None = None
    diametro: float | None = None
    material: str | None = None
    largo: float | None = None
    limpieza: str | None = None
    conclusiones: str | None = None
    drive_folder_id: str | None = None
    observaciones: list[Observacion] = field(default_factory=list)
    patologias: list[Patologia] = field(default_factory=list)


@dataclass
class Foto:
    """Foto ya reducida y lista para incrustar (data URI JPEG)."""
    nombre: str
    data_uri: str


@dataclass
class FichaDatos:
    inspeccion: Inspeccion
    fijas: dict[str, Foto | None]            # claves: general, tapa, camara
    figuras: dict[int, Foto]                 # nro_figura -> foto
    avisos: list[str] = field(default_factory=list)

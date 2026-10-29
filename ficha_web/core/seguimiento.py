"""Seguimiento de visitas y presupuestos: lectura (solo lectura) de la planilla de Google Sheets.

La planilla la mantienen los scripts de Apps Script (calendario / recordatorio / cancelado);
acá nunca se escribe en ella. Sin Streamlit: `pages/5_Seguimiento.py` solo invoca esto.
"""
import json
import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .config import Config
from .fotos import normalizar

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Estados de la columna «Presupuesto». Vacío = todavía sin presupuesto enviado.
ESTADOS = ("Enviado", "Aceptado", "Cancelado")
SIN_ESTADO = "Sin enviar"

# encabezado normalizado -> campo de Visita
_COLUMNAS = {
    "fecha de visita": "fecha", "fecha": "fecha",
    "hora": "hora",
    "direccion": "direccion",
    "nombre": "nombre",
    "apellido": "apellido",
    "correo": "correo",
    "telefono": "telefono",
    "recordatorio": "recordatorio",
    "presupuesto": "presupuesto",
    "comentario": "comentario",
}
_CAMPOS_TEXTO = ("hora", "direccion", "nombre", "apellido", "correo",
                 "telefono", "recordatorio", "presupuesto", "comentario")


class SeguimientoError(Exception):
    """Problema esperable (sin configurar, sin permiso, hoja inexistente)."""


@dataclass(frozen=True)
class Visita:
    fila: int                      # número de fila en la planilla (1 = encabezado)
    fecha: date | None
    hora: str
    direccion: str
    nombre: str
    apellido: str
    correo: str
    telefono: str
    recordatorio: str
    presupuesto: str               # texto tal cual está en la planilla
    comentario: str

    @property
    def cliente(self) -> str:
        return " ".join(p for p in (self.nombre, self.apellido) if p)

    @property
    def estado(self) -> str:
        """Enviado / Aceptado / Cancelado / Sin enviar (o el texto raro tal cual)."""
        txt = self.presupuesto.strip()
        if not txt:
            return SIN_ESTADO
        for e in ESTADOS:
            if normalizar(txt) == normalizar(e):
                return e
        return txt


# ---------------------------------------------------------------- parseo

def parsear_fecha(txt: str) -> date | None:
    """dd/mm/aaaa (formato de la planilla); también acepta aaaa-mm-dd."""
    txt = (txt or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            continue
    return None


def extraer_id_planilla(texto: str) -> str:
    """Acepta el ID pelado o la URL completa de la planilla."""
    texto = (texto or "").strip()
    m = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", texto)
    return m.group(1) if m else texto


def visitas_desde_filas(filas: list[list]) -> list[Visita]:
    """`filas[0]` es el encabezado; las columnas se ubican por nombre, no por posición."""
    if not filas:
        return []
    indices: dict[str, int] = {}
    for i, h in enumerate(filas[0]):
        campo = _COLUMNAS.get(normalizar(str(h)))
        if campo and campo not in indices:
            indices[campo] = i
    if "fecha" not in indices:
        raise SeguimientoError("La hoja no tiene la columna «Fecha de visita».")

    def celda(fila: list, campo: str) -> str:
        i = indices.get(campo)
        return str(fila[i]).strip() if i is not None and i < len(fila) else ""

    visitas = []
    for n, fila in enumerate(filas[1:], start=2):
        if not any(str(c).strip() for c in fila):
            continue
        visitas.append(Visita(
            fila=n, fecha=parsear_fecha(celda(fila, "fecha")),
            **{c: celda(fila, c) for c in _CAMPOS_TEXTO}))
    return visitas


# ---------------------------------------------------------------- métricas

@dataclass(frozen=True)
class Resumen:
    total: int
    hoy: int
    proximos_7_dias: int
    por_estado: dict[str, int]
    tasa_aceptacion: float | None    # aceptados / (aceptados + enviados)
    tasa_cancelacion: float | None   # cancelados / visitas de hoy o pasadas
    pendientes: list[Visita]         # visita ya pasada y sin presupuesto
    por_mes: dict[str, int]          # "2026-10" -> cantidad


def resumir(visitas: list[Visita], hoy: date | None = None) -> Resumen:
    hoy = hoy or date.today()
    estados = Counter(v.estado for v in visitas)
    por_estado = {e: estados.get(e, 0) for e in (SIN_ESTADO, *ESTADOS)}
    for e, n in estados.items():  # textos no previstos, para no perderlos
        por_estado.setdefault(e, n)

    realizadas = [v for v in visitas if v.fecha and v.fecha <= hoy]
    cancelados = sum(1 for v in realizadas if v.estado == "Cancelado")
    con_presupuesto = por_estado["Aceptado"] + por_estado["Enviado"]
    pendientes = sorted(
        (v for v in visitas if v.fecha and v.fecha < hoy and v.estado == SIN_ESTADO),
        key=lambda v: v.fecha)
    por_mes = Counter(v.fecha.strftime("%Y-%m") for v in visitas if v.fecha)
    return Resumen(
        total=len(visitas),
        hoy=sum(1 for v in visitas if v.fecha == hoy and v.estado != "Cancelado"),
        proximos_7_dias=sum(1 for v in visitas
                            if v.fecha and hoy < v.fecha <= hoy + timedelta(days=7) and v.estado != "Cancelado"),
        por_estado=por_estado,
        tasa_aceptacion=(por_estado["Aceptado"] / con_presupuesto) if con_presupuesto else None,
        tasa_cancelacion=(cancelados / len(realizadas)) if realizadas else None,
        pendientes=pendientes,
        por_mes=dict(sorted(por_mes.items())),
    )


def filtrar(visitas: list[Visita], estados: set[str] | None = None, texto: str = "",
            desde: date | None = None, hasta: date | None = None) -> list[Visita]:
    q = normalizar(texto) if texto.strip() else ""
    salida = []
    for v in visitas:
        if estados and v.estado not in estados:
            continue
        if desde and (v.fecha is None or v.fecha < desde):
            continue
        if hasta and (v.fecha is None or v.fecha > hasta):
            continue
        if q and q not in normalizar(" ".join((v.cliente, v.direccion, v.correo, v.telefono, v.comentario))):
            continue
        salida.append(v)
    return salida


# ---------------------------------------------------------------- fuentes

class FuenteSeguimiento(ABC):
    @abstractmethod
    def visitas(self) -> list[Visita]: ...


class MockFuenteSeguimiento(FuenteSeguimiento):
    """Datos de ejemplo relativos a hoy, para probar sin planilla."""

    _CASOS = [  # (días desde hoy, hora, dirección, nombre, apellido, presupuesto)
        (-40, "10:00", "Soriano 1398", "Rony", "Mejia", "Aceptado"),
        (-35, "9:00", "26 de marzo 3269 apto 2", "Carina", "Depetro", "Aceptado"),
        (-30, "11:00", "Anzani 1989", "Sandra", "Varela", "Enviado"),
        (-24, "10:00", "Cerrito 327", "Info", "Anhec", "Enviado"),
        (-20, "15:00", "Mississippi 1536", "Washington", "Freire", "Enviado"),
        (-18, "14:00", "Reyes 1580", "Sandra", "Porta", "Aceptado"),
        (-15, "10:00", "Gral Hornos 4504", "Guisel", "Gahn", "Cancelado"),
        (-12, "14:00", "Atanasio Aguirre 1122", "Daniel", "Pineyro", "Cancelado"),
        (-9, "11:00", "Lombardia 5853", "Martin", "Figueroa", "Enviado"),
        (-6, "15:00", "Solano Garcia 2448", "Juan", "Pablo Zinno", "Aceptado"),
        (-4, "8:00", "Defensa 2046", "Santiago", "Baez", "Enviado"),
        (-3, "13:00", "Rambla Armenia 3837", "Anderson", "Arq", ""),
        (-1, "10:00", "Libertad 2396", "Javier", "Emmenegger", ""),
        (0, "9:00", "Francisco Joaquin Munoz 3257", "German", "Lungo", ""),
        (1, "13:00", "Bulevar Artigas 1200", "Lucia", "Pereira", ""),
        (3, "10:00", "Av. Italia 3300", "Marcos", "Mott", ""),
        (6, "15:00", "Garibaldi 2227", "Rosa", "Techera", ""),
        (14, "9:00", "Chiavari 3093", "Jose", "Castelar Viera", ""),
    ]

    def __init__(self, hoy: date | None = None):
        self._hoy = hoy or date.today()

    def visitas(self) -> list[Visita]:
        return [
            Visita(fila=n, fecha=self._hoy + timedelta(days=dias), hora=hora, direccion=direccion,
                   nombre=nombre, apellido=apellido,
                   correo=f"{nombre.lower()}.{apellido.split()[0].lower()}@example.com",
                   telefono="99000000", recordatorio="", presupuesto=presupuesto, comentario="")
            for n, (dias, hora, direccion, nombre, apellido, presupuesto) in enumerate(self._CASOS, start=2)
        ]


class SheetsFuenteSeguimiento(FuenteSeguimiento):
    """Lee la planilla con la cuenta de servicio (la misma de Drive; hay que compartirle la planilla)."""

    def __init__(self, cfg: Config):
        if not cfg.seguimiento_sheet_id:
            raise SeguimientoError("Falta configurar SEGUIMIENTO_SHEET_ID.")
        self._cfg = cfg
        self._id = extraer_id_planilla(cfg.seguimiento_sheet_id)
        self._creds = self._credenciales()

    def _credenciales(self):
        from google.oauth2 import service_account
        try:
            if self._cfg.google_sa_json:
                return service_account.Credentials.from_service_account_info(
                    json.loads(self._cfg.google_sa_json), scopes=SCOPES)
            if self._cfg.google_sa_json_path:
                return service_account.Credentials.from_service_account_file(
                    self._cfg.google_sa_json_path, scopes=SCOPES)
        except Exception as e:
            raise SeguimientoError(f"No se pudo leer la credencial de Google: {e}") from e
        raise SeguimientoError("Falta configurar GOOGLE_SA_JSON_PATH o GOOGLE_SA_JSON.")

    def visitas(self) -> list[Visita]:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        try:
            svc = build("sheets", "v4", credentials=self._creds, cache_discovery=False)
            # FORMATTED_VALUE: fechas y horas llegan como se ven en la planilla (dd/mm/aaaa, 9:00)
            r = svc.spreadsheets().values().get(
                spreadsheetId=self._id, range=f"'{self._cfg.seguimiento_hoja}'!A:J",
                valueRenderOption="FORMATTED_VALUE").execute()
        except HttpError as e:
            codigo = getattr(e.resp, "status", None)
            if codigo in (400, 403, 404):
                raise SeguimientoError(
                    "No se pudo abrir la planilla o la pestaña. Revisá SEGUIMIENTO_SHEET_ID, "
                    f"SEGUIMIENTO_HOJA («{self._cfg.seguimiento_hoja}») y que esté compartida "
                    f"(Lector) con la cuenta de servicio. Detalle de Google: {codigo} {e.reason}") from e
            raise SeguimientoError(f"Error de Google Sheets ({codigo}).") from e
        return visitas_desde_filas(r.get("values", []))


def crear_fuente_seguimiento(cfg: Config) -> FuenteSeguimiento:
    return MockFuenteSeguimiento() if cfg.use_mock else SheetsFuenteSeguimiento(cfg)

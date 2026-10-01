"""Fuentes de fotos (Drive / carpeta local) y clasificación por nombre de archivo."""
import io
import json
import re
import threading
import time
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .modelos import Inspeccion

# ── Reglas de clasificación (único lugar a tocar si cambia la convención de nombres) ──
PALABRAS_FIJAS = ("general", "tapa", "camara")   # ya normalizadas (sin tildes, minúsculas)
PATRON_FIGURA = re.compile(r"^(?:fig(?:ura)?[\s_-]*)?0*(\d+)$")
EXTENSIONES_LOCALES = {".jpg", ".jpeg", ".png", ".webp"}

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
ID_CARPETA_RE = re.compile(r"[A-Za-z0-9_-]+")
TTL_LISTADO_PADRE = 300  # s


class FotosError(Exception):
    """Problema esperable con las fotos (sin carpeta, duplicadas, Drive caído). Se muestra como aviso."""


@dataclass(frozen=True)
class ArchivoFoto:
    id: str
    nombre: str
    modificado: str = ""


@dataclass
class Listado:
    archivos: list[ArchivoFoto]
    carpeta_id: str | None = None   # carpeta resuelta (para guardarla en la base)


@dataclass
class Clasificacion:
    fijas: dict[str, ArchivoFoto] = field(default_factory=dict)
    figuras: dict[int, ArchivoFoto] = field(default_factory=dict)
    sin_clasificar: list[ArchivoFoto] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


# ── Funciones puras ───────────────────────────────────────────────────────────

def normalizar(nombre: str) -> str:
    """Nombre sin extensión, sin tildes, en minúsculas."""
    base = nombre.rsplit(".", 1)[0] if "." in nombre else nombre
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", base) if not unicodedata.combining(c))
    return sin_tildes.casefold().strip()


def clasificar_nombre(nombre: str) -> tuple[str, str | int] | None:
    """('fija', 'tapa') | ('figura', 3) | None."""
    n = normalizar(nombre)
    for palabra in PALABRAS_FIJAS:
        if palabra in n:
            return ("fija", palabra)
    m = PATRON_FIGURA.fullmatch(n)
    if m and int(m.group(1)) > 0:
        return ("figura", int(m.group(1)))
    return None


def clasificar_archivos(archivos: list[ArchivoFoto]) -> Clasificacion:
    res = Clasificacion()
    for a in sorted(archivos, key=lambda x: x.nombre.casefold()):
        c = clasificar_nombre(a.nombre)
        if c is None:
            res.sin_clasificar.append(a)
            continue
        tipo, valor = c
        destino = res.fijas if tipo == "fija" else res.figuras
        etiqueta = valor.capitalize() if tipo == "fija" else f"Fig. {valor}"
        if valor in destino:
            res.avisos.append(
                f"Hay más de una foto para {etiqueta}: se usa «{destino[valor].nombre}» y se ignora «{a.nombre}»."
            )
        else:
            destino[valor] = a
    return res


def extraer_id_carpeta(texto: str) -> str:
    """ID de carpeta desde una URL de Drive o un ID pelado. '' si no hay nada."""
    texto = (texto or "").strip()
    m = re.search(r"/folders/([A-Za-z0-9_-]+)", texto)
    return m.group(1) if m else texto


def carpeta_id_valido(texto: str) -> bool:
    return bool(ID_CARPETA_RE.fullmatch(texto or ""))


# ── Interfaz ──────────────────────────────────────────────────────────────────

class FuenteFotos(ABC):
    @abstractmethod
    def listar(self, inspeccion: Inspeccion) -> Listado: ...

    @abstractmethod
    def descargar(self, archivo: ArchivoFoto) -> bytes: ...


class CarpetaLocalFuenteFotos(FuenteFotos):
    """Lee <base>/<id>/... (modo mock y tests)."""

    def __init__(self, base: Path):
        self._base = Path(base)

    def listar(self, inspeccion):
        carpeta = self._base / inspeccion.id
        if not carpeta.is_dir():
            raise FotosError(f"No hay carpeta de fotos local para la inspección {inspeccion.id}.")
        archivos = [
            ArchivoFoto(id=str(p), nombre=p.name, modificado=str(p.stat().st_mtime))
            for p in carpeta.iterdir() if p.suffix.lower() in EXTENSIONES_LOCALES
        ]
        return Listado(archivos)

    def descargar(self, archivo):
        return Path(archivo.id).read_bytes()


class DriveFuenteFotos(FuenteFotos):
    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._local = threading.local()           # httplib2 no es thread-safe: un servicio por hilo
        self._cache_padre: tuple[float, list[dict]] | None = None
        self._lock = threading.Lock()
        self._credenciales()                      # falla temprano si falta la credencial

    # -- cliente --
    def _credenciales(self):
        from google.oauth2 import service_account
        try:
            if self._cfg.google_sa_json:
                return service_account.Credentials.from_service_account_info(
                    json.loads(self._cfg.google_sa_json), scopes=SCOPES)
            if self._cfg.google_sa_json_path:
                return service_account.Credentials.from_service_account_file(
                    self._cfg.google_sa_json_path, scopes=SCOPES)
        except Exception as e:  # credencial ilegible
            raise FotosError(f"No se pudo leer la credencial de Google: {e}") from e
        raise FotosError("Falta configurar GOOGLE_SA_JSON_PATH o GOOGLE_SA_JSON.")

    def _svc(self):
        if not hasattr(self._local, "svc"):
            import google_auth_httplib2
            import httplib2
            from googleapiclient.discovery import build
            http = google_auth_httplib2.AuthorizedHttp(self._credenciales(), http=httplib2.Http(timeout=30))
            self._local.svc = build("drive", "v3", http=http, cache_discovery=False)
        return self._local.svc

    @staticmethod
    def _con_reintentos(fn, intentos: int = 3):
        from googleapiclient.errors import HttpError
        for i in range(intentos):
            try:
                return fn()
            except HttpError as e:
                if e.resp.status in (429, 500, 502, 503, 504) and i < intentos - 1:
                    time.sleep(2 ** i)
                    continue
                raise FotosError(_mensaje_http(e)) from e
            except (OSError, TimeoutError) as e:   # red / timeout
                if i < intentos - 1:
                    time.sleep(2 ** i)
                    continue
                raise FotosError(f"No se pudo conectar con Google Drive: {e}") from e

    # -- listados --
    def _listar(self, q: str, campos: str) -> list[dict]:
        resultado, token = [], None
        while True:
            r = self._con_reintentos(lambda: self._svc().files().list(
                q=q, fields=f"nextPageToken, files({campos})", pageSize=200, pageToken=token,
                supportsAllDrives=True, includeItemsFromAllDrives=True, corpora="allDrives",
            ).execute())
            resultado += r["files"]
            token = r.get("nextPageToken")
            if not token:
                return resultado

    def _subcarpetas_padre(self) -> list[dict]:
        padre = self._cfg.drive_parent_folder_id
        if not carpeta_id_valido(padre):
            raise FotosError("DRIVE_PARENT_FOLDER_ID no está configurado o es inválido.")
        with self._lock:
            if self._cache_padre and time.time() - self._cache_padre[0] < TTL_LISTADO_PADRE:
                return self._cache_padre[1]
        q = f"'{padre}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'"
        carpetas = self._listar(q, "id, name")
        with self._lock:
            self._cache_padre = (time.time(), carpetas)
        return carpetas

    def resolver_carpeta(self, inspeccion: Inspeccion) -> str:
        if inspeccion.drive_folder_id:
            return inspeccion.drive_folder_id
        prefijo = f"{inspeccion.id} - "
        # Filtro en Python: `name contains` de la API no matchea por prefijo
        candidatas = [c for c in self._subcarpetas_padre() if c["name"].startswith(prefijo)]
        if not candidatas:
            raise FotosError(f"No hay carpeta de Drive para la inspección {inspeccion.id} (se busca «{prefijo}…»).")
        if len(candidatas) > 1:
            nombres = "; ".join(c["name"] for c in candidatas)
            raise FotosError(f"Hay carpetas duplicadas para la inspección {inspeccion.id}: {nombres}. "
                             "Pegá el link de la correcta en el formulario.")
        return candidatas[0]["id"]

    def listar(self, inspeccion):
        carpeta = self.resolver_carpeta(inspeccion)
        if not carpeta_id_valido(carpeta):
            raise FotosError(f"ID de carpeta de Drive inválido: {carpeta!r}")
        q = f"'{carpeta}' in parents and trashed=false and mimeType contains 'image/'"
        filas = self._listar(q, "id, name, modifiedTime")
        return Listado([ArchivoFoto(f["id"], f["name"], f.get("modifiedTime", "")) for f in filas], carpeta)

    def descargar(self, archivo):
        from googleapiclient.http import MediaIoBaseDownload

        def _bajar():
            buf = io.BytesIO()
            dl = MediaIoBaseDownload(buf, self._svc().files().get_media(fileId=archivo.id, supportsAllDrives=True))
            listo = False
            while not listo:
                _, listo = dl.next_chunk()
            return buf.getvalue()

        return self._con_reintentos(_bajar)


def _mensaje_http(e) -> str:
    s = e.resp.status
    if s == 404:
        return "Drive no encuentra la carpeta o la cuenta de servicio no tiene acceso (revisar permisos de Lector)."
    if s == 403:
        return "Drive denegó el acceso (permisos insuficientes o cuota excedida)."
    return f"Error de Google Drive (HTTP {s})."


def crear_fuente_fotos(cfg: Config) -> FuenteFotos:
    if cfg.use_mock:
        return CarpetaLocalFuenteFotos(cfg.fotos_local_dir)
    return DriveFuenteFotos(cfg)

"""Configuración: se lee una sola vez, de variables de entorno (o de un mapping equivalente)."""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

RAIZ = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    supabase_url: str = ""
    supabase_key: str = ""
    google_sa_json_path: str = ""
    google_sa_json: str = ""
    drive_parent_folder_id: str = ""
    use_mock: bool = False
    fotos_local_dir: Path = RAIZ / "fixtures" / "fotos"
    # Página del PDF (CSS @page). No hay .qpt en el repo: A4 vertical por defecto.
    pagina: str = "A4 portrait"
    margen: str = "12mm"


def _verdadero(valor: str) -> bool:
    return valor.strip().lower() in {"1", "true", "yes", "si", "sí"}


def cargar_config(entorno: Mapping[str, str] | None = None) -> Config:
    if entorno is None:
        try:
            from dotenv import load_dotenv
            load_dotenv(RAIZ / ".env")
        except ImportError:
            pass
        entorno = os.environ

    def g(clave: str, defecto: str = "") -> str:
        return str(entorno.get(clave) or defecto)

    carpeta_fotos = g("FOTOS_LOCAL_DIR")
    return Config(
        supabase_url=g("SUPABASE_URL"),
        supabase_key=g("SUPABASE_KEY"),
        google_sa_json_path=g("GOOGLE_SA_JSON_PATH"),
        google_sa_json=g("GOOGLE_SA_JSON"),
        drive_parent_folder_id=g("DRIVE_PARENT_FOLDER_ID"),
        use_mock=_verdadero(g("USE_MOCK", "0")),
        fotos_local_dir=Path(carpeta_fotos) if carpeta_fotos else RAIZ / "fixtures" / "fotos",
        pagina=g("PAGINA", "A4 portrait"),
        margen=g("MARGEN", "12mm"),
    )

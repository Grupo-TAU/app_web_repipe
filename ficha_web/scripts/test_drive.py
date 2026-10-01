"""Verifica credencial, permisos e ID de carpeta de Drive.

Uso: python scripts/test_drive.py <ruta_al_json_de_la_cuenta_de_servicio> <url_o_id_de_carpeta>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import Config  # noqa: E402
from core.fotos import ArchivoFoto, DriveFuenteFotos, extraer_id_carpeta  # noqa: E402
from core.modelos import Inspeccion  # noqa: E402


def main():
    ruta_json, carpeta = sys.argv[1], extraer_id_carpeta(sys.argv[2])
    fuente = DriveFuenteFotos(Config(google_sa_json_path=ruta_json))
    # Inspección ficticia solo para reutilizar listar() con un ID de carpeta explícito
    listado = fuente.listar(Inspeccion(id="prueba", ubicacion="-", drive_folder_id=carpeta))
    archivos = sorted(listado.archivos, key=lambda a: a.nombre.casefold())
    print(f"{len(archivos)} imágenes en la carpeta {carpeta}")
    for a in archivos:
        print(f"{a.nombre:<40} id={a.id}")
    if archivos:
        datos = fuente.descargar(ArchivoFoto(archivos[0].id, archivos[0].nombre))
        print(f"Descarga OK: {archivos[0].nombre} ({len(datos)} bytes)")


if __name__ == "__main__":
    main()

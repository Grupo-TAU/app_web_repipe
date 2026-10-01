"""Arma FichaDatos (datos + fotos + avisos) a partir de un ID."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from .fotos import ArchivoFoto, FotosError, FuenteFotos, clasificar_archivos
from .modelos import FichaDatos, Foto
from .render import reducir_a_data_uri
from .repositorio import Repositorio

ETIQUETAS_FIJAS = {"general": "General", "tapa": "Tapa", "camara": "Cámara"}
TTL_IMAGENES = 600  # s
HILOS = 4

_cache: dict[tuple[str, str], tuple[float, str]] = {}
_cache_lock = threading.Lock()


class InspeccionNoEncontrada(Exception):
    pass


def _data_uri(fuente: FuenteFotos, archivo: ArchivoFoto) -> str:
    """Descarga + reduce; cacheado por (id de archivo, fecha de modificación)."""
    clave = (archivo.id, archivo.modificado)
    with _cache_lock:
        hit = _cache.get(clave)
        if hit and time.time() - hit[0] < TTL_IMAGENES:
            return hit[1]
    uri = reducir_a_data_uri(fuente.descargar(archivo))
    with _cache_lock:
        _cache[clave] = (time.time(), uri)
    return uri


def armar_ficha(id_inspeccion: str, repo: Repositorio, fuente: FuenteFotos) -> FichaDatos:
    insp = repo.obtener(id_inspeccion)
    if insp is None:
        raise InspeccionNoEncontrada(id_inspeccion)

    avisos: list[str] = []
    fijas: dict[str, Foto | None] = {k: None for k in ETIQUETAS_FIJAS}
    figuras: dict[int, Foto] = {}

    try:
        listado = fuente.listar(insp)
    except FotosError as e:
        avisos.append(f"Fotos: {e}")
        listado = None
    except Exception as e:  # ningún error de fotos debe tumbar la ficha
        avisos.append(f"Fotos: error inesperado al leer la carpeta ({type(e).__name__}).")
        listado = None

    if listado is not None:
        if listado.carpeta_id and listado.carpeta_id != insp.drive_folder_id:
            try:
                repo.guardar_carpeta_drive(insp.id, listado.carpeta_id)
            except Exception:
                avisos.append("No se pudo guardar el ID de la carpeta de Drive en la base (la ficha se generó igual).")

        clas = clasificar_archivos(listado.archivos)
        avisos += clas.avisos
        avisos += [f"Foto sin clasificar: «{a.nombre}»." for a in clas.sin_clasificar]

        figuras_usadas = {p.nro_figura for p in insp.patologias if p.nro_figura is not None}
        for nro in sorted(set(clas.figuras) - figuras_usadas):
            avisos.append(f"Hay foto para la Fig. {nro} pero no hay patología cargada con esa figura (no se imprime).")

        # Solo se descargan las fotos que la ficha va a usar
        pedidas: list[tuple[str | int, ArchivoFoto]] = [(k, a) for k, a in clas.fijas.items()]
        pedidas += [(n, a) for n, a in clas.figuras.items() if n in figuras_usadas]

        def bajar(par):
            clave, archivo = par
            try:
                return clave, archivo, _data_uri(fuente, archivo), None
            except Exception as e:
                return clave, archivo, None, e

        with ThreadPoolExecutor(HILOS) as pool:
            for clave, archivo, uri, err in pool.map(bajar, pedidas):
                if err is not None:
                    avisos.append(f"No se pudo obtener la foto «{archivo.nombre}»: {err}")
                elif isinstance(clave, str):
                    fijas[clave] = Foto(archivo.nombre, uri)
                else:
                    figuras[clave] = Foto(archivo.nombre, uri)

        for clave, etiqueta in ETIQUETAS_FIJAS.items():
            if clave not in clas.fijas:
                avisos.append(f"Falta la foto {etiqueta}.")
        for p in sorted((p for p in insp.patologias if p.nro_figura is not None), key=lambda p: p.nro_figura):
            if p.nro_figura not in figuras and p.nro_figura not in clas.figuras:
                avisos.append(f"La patología «{p.patologia}» (Fig. {p.nro_figura}) no tiene foto.")

    return FichaDatos(insp, fijas, figuras, avisos)

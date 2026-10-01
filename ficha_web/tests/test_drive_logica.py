"""Lógica de resolución de carpeta de Drive, sin llamar a la API real."""
import pytest

from core.config import Config
from core.fotos import DriveFuenteFotos, FotosError
from core.modelos import Inspeccion


class DriveFalso(DriveFuenteFotos):
    def __init__(self, subcarpetas):
        self._cfg = Config(drive_parent_folder_id="PADRE123")
        self._subcarpetas = subcarpetas
        self._cache_padre = None

    def _subcarpetas_padre(self):
        return self._subcarpetas


def insp(id_, carpeta=None):
    return Inspeccion(id=id_, ubicacion="x", drive_folder_id=carpeta)


def test_id_guardado_tiene_prioridad():
    assert DriveFalso([]).resolver_carpeta(insp("1", "ABC")) == "ABC"


def test_resuelve_por_prefijo():
    d = DriveFalso([{"id": "F1", "name": "10 - Calle"}, {"id": "F2", "name": "1001 - Av. Italia"}])
    assert d.resolver_carpeta(insp("1001")) == "F2"   # «10 - » no matchea «1001 - »


def test_sin_carpeta():
    with pytest.raises(FotosError, match="No hay carpeta"):
        DriveFalso([{"id": "F1", "name": "2 - x"}]).resolver_carpeta(insp("1"))


def test_carpetas_duplicadas():
    d = DriveFalso([{"id": "F1", "name": "1 - a"}, {"id": "F2", "name": "1 - b"}])
    with pytest.raises(FotosError, match="duplicadas"):
        d.resolver_carpeta(insp("1"))


def test_id_de_carpeta_invalido_no_se_interpola():
    with pytest.raises(FotosError, match="inválido"):
        DriveFalso([]).listar(insp("1", "x' or '1'='1"))

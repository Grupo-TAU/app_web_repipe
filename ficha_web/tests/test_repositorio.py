from datetime import date

import pytest

from core.modelos import Inspeccion, Patologia
from core.repositorio import MockRepositorio


def test_guardar_y_volver_a_cargar():
    repo = MockRepositorio()
    insp = repo.obtener("1001")
    insp.operario = "Otro"
    insp.patologias.append(Patologia("Nueva", 50.0, 4))
    repo.guardar(insp)
    de_nuevo = repo.obtener("1001")
    assert de_nuevo.operario == "Otro" and len(de_nuevo.patologias) == 4
    assert de_nuevo.fecha == date(2026, 9, 15)


def test_id_invalido():
    with pytest.raises(ValueError):
        MockRepositorio().guardar(Inspeccion(id="con espacio", ubicacion="x"))

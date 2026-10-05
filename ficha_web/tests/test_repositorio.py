from datetime import date

import pytest

from core.modelos import Inspeccion, Patologia
from core.repositorio import MockRepositorio, OpcionDuplicada


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


def test_opciones_semilla_agregar_y_quitar():
    repo = MockRepositorio()
    assert repo.listar_opciones("operario") == ["FE", "TP"]
    assert "Hierro Fundido" in repo.listar_opciones("material")
    repo.agregar_opcion("operario", "XY")
    assert repo.listar_opciones("operario")[-1] == "XY"
    with pytest.raises(OpcionDuplicada):
        repo.agregar_opcion("operario", "xy")      # sin distinguir mayúsculas
    repo.quitar_opcion("operario", "XY")
    assert "XY" not in repo.listar_opciones("operario")


def test_nro_figura_unico_por_inspeccion():
    repo = MockRepositorio()
    insp = repo.obtener("1001")
    insp.patologias.append(Patologia("Otra", 5.0, 1))   # la Fig. 1 ya está usada
    with pytest.raises(ValueError, match="repetidas"):
        repo.guardar(insp)
    insp.patologias[-1].nro_figura = None                # sin figura: permitido
    insp.patologias.append(Patologia("Otra más", 6.0, None))
    repo.guardar(insp)

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


def test_listar_recientes_el_ultimo_guardado_primero():
    repo = MockRepositorio()
    repo.guardar(Inspeccion(id="2002", ubicacion="Otra calle"))
    repo.guardar(Inspeccion(id="2003", ubicacion="Y otra"))
    assert [r.id for r in repo.listar_recientes(20)] == ["2003", "2002", "1001"]
    assert len(repo.listar_recientes(2)) == 2
    repo.guardar(repo.obtener("1001"))                # volver a guardar la sube al tope
    assert repo.listar_recientes()[0].id == "1001"


def test_categorias_de_opciones():
    from core.modelos import CATEGORIAS_OPCIONES
    assert list(CATEGORIAS_OPCIONES) == ["solicitante", "operario", "acceso", "material", "limpieza", "patologia"]
    assert MockRepositorio().listar_opciones("acceso") == []

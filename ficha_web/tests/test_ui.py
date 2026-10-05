"""Pruebas de la interfaz del formulario con el AppTest de Streamlit (modo mock)."""
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from core.config import RAIZ  # noqa: E402


@pytest.fixture
def formulario(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "1")
    at = AppTest.from_file(str(RAIZ / "pages" / "1_Formulario.py"), default_timeout=30)
    at.run()
    at.text_input(key="f_id").set_value("1001")
    at.button[0].click().run()          # Cargar
    return at


def _boton(at, texto):
    return next(b for b in at.button if b.label == texto)


def test_carga_con_desplegables(formulario):
    at = formulario
    assert not at.exception
    assert at.selectbox(key="f_operario").value == "FE"
    assert at.selectbox(key="f_material").value == "Hormigón"
    assert "GRESS" in at.selectbox(key="f_material").options


def test_figura_repetida_bloquea_el_guardado(formulario):
    at = formulario
    _boton(at, "➕ Agregar patología").click().run()
    nueva = at.session_state["f_pat"][-1]
    at.text_input(key=f"pp_{nueva}").set_value("Otra")
    at.number_input(key=f"pf_{nueva}").set_value(1)    # la Fig. 1 ya existe
    _boton(at, "Guardar").click().run()
    assert any("repetido" in e.value for e in at.error)
    assert not at.success


def test_guardar_ok(formulario):
    at = formulario
    _boton(at, "Guardar").click().run()
    assert not at.error and any("guardada" in s.value for s in at.success)

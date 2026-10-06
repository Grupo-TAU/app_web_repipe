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
    at.text_input(key=f"pp_{nueva}_t").set_value("Otra")   # sin opciones de patología: texto libre
    at.number_input(key=f"pf_{nueva}").set_value(1)    # la Fig. 1 ya existe
    _boton(at, "Guardar").click().run()
    assert any("repetido" in e.value for e in at.error)
    assert not at.success


def test_guardar_ok(formulario):
    at = formulario
    _boton(at, "Guardar").click().run()
    assert not at.error and any("guardada" in s.value for s in at.success)


def _app(monkeypatch, mock: bool):
    monkeypatch.setenv("USE_MOCK", "1" if mock else "0")
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:9")
    monkeypatch.setenv("SUPABASE_KEY", "sb_publishable_prueba")
    import ui
    ui.config.clear()
    return AppTest.from_file(str(RAIZ / "app.py"), default_timeout=30).run()


def test_sin_sesion_solo_se_ve_el_login(monkeypatch):
    at = _app(monkeypatch, mock=False)
    assert not at.exception
    assert [b.label for b in at.button] == ["Ingresar"]     # sin «Cerrar sesión» ni páginas
    assert at.text_input[1].proto.type == 1                   # contraseña oculta (password)
    assert not any(t.value == "Formulario de inspección" for t in at.title)


def test_login_con_campos_vacios_avisa(monkeypatch):
    at = _app(monkeypatch, mock=False)
    at.button[0].click().run()
    assert any("Completá" in e.value for e in at.error)


def test_con_mock_entra_directo(monkeypatch):
    at = _app(monkeypatch, mock=True)
    assert any(t.value == "Formulario de inspección" for t in at.title)


def test_css_del_tema_no_se_escapa_como_texto():
    import ui
    css = ui._css()
    assert css.count("</style>") == 1 and css.endswith("</style>")
    assert "unsafe_allow_html" not in css and "--rp-green-500" in css


def test_campos_sin_opciones_son_texto_libre_y_se_guardan(formulario):
    at = formulario
    assert [s.key for s in at.selectbox] == ["f_solicitante", "f_operario", "f_material", "f_limpieza"]
    at.text_input(key="f_acceso_t").set_value("Cámara de registro")      # «acceso» no tiene opciones
    _boton(at, "Guardar").click().run()
    assert any("guardada" in s.value for s in at.success)
    from ui import repositorio
    assert repositorio().obtener("1001").acceso == "Cámara de registro"


def test_fichas_lista_las_ultimas_inspecciones(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "1")
    at = AppTest.from_file(str(RAIZ / "pages" / "2_Ficha.py"), default_timeout=30).run()
    assert not at.exception
    assert any("Últimas 20" in s.value for s in at.subheader)
    assert any("1001" in m.value for m in at.markdown)
    assert any(b.label == "Ver ficha" for b in at.button)

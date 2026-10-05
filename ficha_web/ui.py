"""Pegamento Streamlit <-> core: configuración, repositorio y fuente de fotos por sesión."""
import time

import streamlit as st

from core.config import Config, cargar_config
from core.fotos import FotosError, FuenteFotos, crear_fuente_fotos
from core.repositorio import MockRepositorio, Repositorio, SupabaseRepositorio


@st.cache_resource
def config() -> Config:
    entorno = {}
    try:  # st.secrets si existe (hostings sin .env)
        entorno = {k: v for k, v in st.secrets.items() if isinstance(v, str)}
    except Exception:
        pass
    import os
    return cargar_config({**entorno, **os.environ})


@st.cache_resource
def _repo_mock() -> MockRepositorio:
    return MockRepositorio()


@st.cache_resource
def _fuente(_cfg: Config):
    try:
        return crear_fuente_fotos(_cfg), None
    except FotosError as e:
        return None, str(e)


def repositorio() -> Repositorio:
    if config().use_mock:
        return _repo_mock()
    return SupabaseRepositorio(st.session_state["sb_cliente"])


def fuente_fotos() -> FuenteFotos:
    fuente, error = _fuente(config())
    if fuente is None:
        return _FuenteRota(error)
    return fuente


class _FuenteRota(FuenteFotos):
    """Si Drive no se pudo inicializar, la ficha sale igual con un aviso."""

    def __init__(self, mensaje: str):
        self._mensaje = mensaje

    def listar(self, inspeccion):
        raise FotosError(self._mensaje)

    def descargar(self, archivo):
        raise FotosError(self._mensaje)


_ESTILOS = """
<style>
/* Botones y campos cómodos para el dedo */
.stButton > button, .stDownloadButton > button { min-height: 2.9rem; }
.stTextInput input, .stNumberInput input, .stDateInput input { min-height: 2.6rem; font-size: 16px; }
@media (max-width: 640px) {
  .block-container { padding: 3.5rem 0.9rem 4rem 0.9rem !important; }
  h1 { font-size: 1.6rem !important; }
  .stButton > button, .stDownloadButton > button { width: 100%; }
}
</style>
"""


def ocultar_sidebar():
    """Pantalla de login: ni menú lateral ni su botón de abrir/cerrar."""
    st.markdown(
        "<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'],"
        " [data-testid='collapsedControl'] { display: none !important; }</style>",
        unsafe_allow_html=True,
    )


def estilos():
    """CSS para móvil/tablet (los campos a 16px evitan el zoom automático de iOS)."""
    st.markdown(_ESTILOS, unsafe_allow_html=True)


TTL_OPCIONES = 60  # s


def opciones(categoria: str) -> list[str]:
    """Valores del desplegable; cacheados un minuto por sesión (se refrescan al editarlos)."""
    clave = f"_opc_{categoria}"
    hit = st.session_state.get(clave)
    if hit and time.time() - hit[0] < TTL_OPCIONES:
        return hit[1]
    try:
        valores = repositorio().listar_opciones(categoria)
    except Exception:
        return hit[1] if hit else []
    st.session_state[clave] = (time.time(), valores)
    return valores


def refrescar_opciones():
    for k in [k for k in st.session_state if str(k).startswith("_opc_")]:
        del st.session_state[k]


def ir_a_ficha(id_inspeccion: str, ejecutar: bool = False):
    st.session_state["ficha_id_prefill"] = id_inspeccion
    st.session_state.pop("_ficha_cache", None)
    if ejecutar:
        st.session_state["ficha_id"] = id_inspeccion
        st.switch_page("pages/3_Vista_previa.py")
    st.switch_page("pages/2_Ficha.py")

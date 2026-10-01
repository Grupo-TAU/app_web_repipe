"""Pegamento Streamlit <-> core: configuración, repositorio y fuente de fotos por sesión."""
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


def ir_a_ficha(id_inspeccion: str, ejecutar: bool = False):
    st.session_state["ficha_id_prefill"] = id_inspeccion
    st.session_state.pop("_ficha_cache", None)
    if ejecutar:
        st.session_state["ficha_id"] = id_inspeccion
        st.switch_page("pages/3_Vista_previa.py")
    st.switch_page("pages/2_Ficha.py")

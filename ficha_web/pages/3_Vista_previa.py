import streamlit as st
import streamlit.components.v1 as components

import ui
from core.ficha import InspeccionNoEncontrada, armar_ficha
from core.render import render_html, render_pdf

st.title("Vista previa de la ficha")

id_insp = st.session_state.get("ficha_id")
if not id_insp:
    st.info("Primero elegí una inspección.")
    if st.button("Ir a Ficha"):
        st.switch_page("pages/2_Ficha.py")
    st.stop()

cache = st.session_state.get("_ficha_cache")
if not cache or cache["id"] != id_insp:
    try:
        with st.spinner("Armando la ficha (trayendo fotos)…"):
            ficha = armar_ficha(id_insp, ui.repositorio(), ui.fuente_fotos())
            html = render_html(ficha, ui.config())
            pdf = render_pdf(html)
    except InspeccionNoEncontrada:
        st.error(f"No existe la inspección «{id_insp}».")
        st.stop()
    except Exception as e:
        st.error(f"No se pudo armar la ficha: {e}")
        st.stop()
    cache = {"id": id_insp, "avisos": ficha.avisos, "html": html, "pdf": pdf}
    st.session_state["_ficha_cache"] = cache

col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
if col1.button("← Volver"):
    st.switch_page("pages/2_Ficha.py")
if col2.button("Editar datos"):
    st.session_state["form_cargar_id"] = id_insp
    st.switch_page("pages/1_Formulario.py")
col3.download_button("Descargar PDF", data=cache["pdf"], file_name=f"Ficha_{id_insp}.pdf",
                     mime="application/pdf", type="primary", on_click="ignore")

if cache["avisos"]:
    with st.container(border=True):
        st.markdown("**Avisos** (no se imprimen)")
        for a in cache["avisos"]:
            st.warning(a, icon="⚠️")

components.html(cache["html"], height=1250, scrolling=True)

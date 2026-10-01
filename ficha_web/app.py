"""Entrada Streamlit: login (Supabase Auth) + navegación."""
import streamlit as st

import ui
from core.auth import iniciar_sesion

st.set_page_config(page_title="Fichas de inspección", page_icon="📋", layout="wide")

cfg = ui.config()


def pantalla_login():
    st.title("Fichas de inspección")
    with st.form("login"):
        email = st.text_input("Email")
        clave = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            try:
                st.session_state["sb_cliente"] = iniciar_sesion(cfg, email.strip(), clave)
                st.rerun()
            except Exception:
                st.error("Email o contraseña incorrectos, o no hay conexión con Supabase.")
    st.stop()


if not cfg.use_mock and "sb_cliente" not in st.session_state:
    if not (cfg.supabase_url and cfg.supabase_key):
        st.error("Falta configurar SUPABASE_URL y SUPABASE_KEY (o poner USE_MOCK=1).")
        st.stop()
    pantalla_login()

if cfg.use_mock:
    st.sidebar.warning("Modo mock: datos en memoria, sin Supabase ni Drive.")
else:
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

navegacion = st.navigation([
    st.Page("pages/1_Formulario.py", title="Formulario", icon="📝", url_path="formulario", default=True),
    st.Page("pages/2_Ficha.py", title="Ficha", icon="📄", url_path="ficha"),
    st.Page("pages/3_Vista_previa.py", title="Vista previa", icon="🔍", url_path="vista-previa"),
])
navegacion.run()

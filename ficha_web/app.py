"""Entrada Streamlit: login (Supabase Auth) y, recién después, la navegación."""
import streamlit as st

import ui
from core.auth import iniciar_sesion

cfg = ui.config()
logueado = cfg.use_mock or "sb_cliente" in st.session_state

st.set_page_config(page_title="Fichas de inspección", page_icon="📋", layout="wide",
                   initial_sidebar_state="auto" if logueado else "collapsed")
ui.estilos()


def login():
    ui.ocultar_sidebar()
    _, centro, _ = st.columns([1, 1.4, 1])
    with centro:
        st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)
        st.title("📋 Fichas de inspección")
        st.caption("Ingresá con tu usuario para continuar.")
        if not (cfg.supabase_url and cfg.supabase_key):
            st.error("Falta configurar SUPABASE_URL y SUPABASE_KEY (o poner USE_MOCK=1).")
            return
        with st.form("login"):
            email = st.text_input("Email", autocomplete="username")
            clave = st.text_input("Contraseña", type="password", autocomplete="current-password")
            enviar = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
        if enviar:
            if not email.strip() or not clave:
                st.error("Completá el email y la contraseña.")
                return
            try:
                st.session_state["sb_cliente"] = iniciar_sesion(cfg, email.strip(), clave)
            except Exception as e:
                if "invalid login credentials" in str(e).lower():
                    st.error("Email o contraseña incorrectos.")
                else:
                    st.error("No se pudo conectar con Supabase. Probá de nuevo en unos segundos.")
                return
            st.rerun()


if not logueado:
    # Solo el login: sin pestañas ni menú lateral hasta iniciar sesión
    st.navigation([st.Page(login, title="Ingresar", url_path="ingreso")]).run()
    st.stop()

if cfg.use_mock:
    st.sidebar.warning("Modo mock: datos en memoria, sin Supabase ni Drive.")
elif st.sidebar.button("Cerrar sesión"):
    st.session_state.clear()
    st.rerun()

# Streamlit borra el estado de los widgets que no se dibujan en una ejecución (p. ej. al ir a
# Configuración a agregar una opción): se reasigna para no perder lo cargado en el Formulario.
for _k in [k for k in st.session_state if str(k).startswith(("f_", "o_", "pm_", "pp_", "pf_"))]:
    st.session_state[_k] = st.session_state[_k]

navegacion = st.navigation([
    st.Page("pages/1_Formulario.py", title="Formulario", icon="📝", url_path="formulario", default=True),
    st.Page("pages/2_Ficha.py", title="Fichas", icon="📄", url_path="ficha"),
    st.Page("pages/3_Vista_previa.py", title="Vista previa", icon="🔍", url_path="vista-previa"),
    st.Page("pages/4_Configuracion.py", title="Configuración", icon="⚙️", url_path="configuracion"),
])
navegacion.run()

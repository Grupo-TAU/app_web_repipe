import streamlit as st

import ui
from core.modelos import id_valido

st.title("Ficha PDF")

id_in = st.text_input("ID de inspección", value=st.session_state.get("ficha_id_prefill", ""))
if st.button("Aceptar", type="primary"):
    id_in = id_in.strip()
    if not id_valido(id_in):
        st.error("El ID solo admite letras, números, punto, guion y guion bajo.")
    else:
        try:
            existe = ui.repositorio().obtener(id_in) is not None
        except Exception as e:
            st.error(f"No se pudo consultar la base: {e}")
            st.stop()
        if not existe:
            st.error(f"No existe la inspección «{id_in}». Cargala primero en el Formulario.")
        else:
            st.session_state["ficha_id"] = id_in
            st.session_state.pop("_ficha_cache", None)
            st.switch_page("pages/3_Vista_previa.py")

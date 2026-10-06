import streamlit as st

import ui
from core import formato
from core.modelos import id_valido

st.title("Fichas")

repo = ui.repositorio()


def abrir(id_inspeccion: str):
    st.session_state["ficha_id"] = id_inspeccion
    st.session_state.pop("_ficha_cache", None)
    st.switch_page("pages/3_Vista_previa.py")


id_in = st.text_input("ID de inspección", value=st.session_state.get("ficha_id_prefill", ""))
if st.button("Aceptar", type="primary"):
    id_in = id_in.strip()
    if not id_valido(id_in):
        st.error("El ID solo admite letras, números, punto, guion y guion bajo.")
    else:
        try:
            existe = repo.obtener(id_in) is not None
        except Exception as e:
            st.error(f"No se pudo consultar la base: {e}")
            st.stop()
        if not existe:
            st.error(f"No existe la inspección «{id_in}». Cargala primero en el Formulario.")
        else:
            abrir(id_in)

st.subheader("Últimas 20 inspecciones")
try:
    recientes = repo.listar_recientes(20)
except Exception as e:
    st.error(f"No se pudo leer el listado: {e}")
    recientes = []

if not recientes:
    st.caption("Todavía no hay inspecciones cargadas.")
for r in recientes:
    with st.container(border=True):
        datos, accion = st.columns([5, 1.4], vertical_alignment="center")
        datos.markdown(f"**{r.id}** · {r.ubicacion}")
        datos.caption(f"{formato.fecha(r.fecha)} · Operario: {formato.texto(r.operario)}")
        if accion.button("Ver ficha", key=f"ver_{r.id}", use_container_width=True):
            abrir(r.id)

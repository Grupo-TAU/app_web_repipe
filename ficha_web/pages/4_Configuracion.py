import streamlit as st

import ui
from core.modelos import CATEGORIAS_OPCIONES
from core.repositorio import OpcionDuplicada

st.title("Configuración")
st.caption("Opciones de los desplegables del formulario. Quitar una opción no modifica las inspecciones ya guardadas.")

repo = ui.repositorio()
ss = st.session_state

if "cfg_msg" in ss:
    tipo, texto = ss.pop("cfg_msg")
    getattr(st, tipo)(texto)


def quitar(categoria: str, valor: str):
    try:
        repo.quitar_opcion(categoria, valor)
        ui.refrescar_opciones()
    except Exception as e:
        ss["cfg_msg"] = ("error", f"No se pudo quitar «{valor}»: {e}")


def agregar(categoria: str):
    valor = " ".join((ss.get(f"cfg_nueva_{categoria}") or "").split())
    if not valor:
        return
    if len(valor) > 80:
        ss["cfg_msg"] = ("error", "La opción es demasiado larga (máximo 80 caracteres).")
        return
    try:
        repo.agregar_opcion(categoria, valor)
        ui.refrescar_opciones()
        ss[f"cfg_nueva_{categoria}"] = ""
        ss["cfg_msg"] = ("success", f"«{valor}» agregado.")
    except OpcionDuplicada:
        ss["cfg_msg"] = ("warning", f"«{valor}» ya existe.")
    except Exception as e:
        ss["cfg_msg"] = ("error", f"No se pudo agregar: {e}")


for categoria, titulo in CATEGORIAS_OPCIONES.items():
    st.subheader(titulo)
    try:
        valores = repo.listar_opciones(categoria)
    except Exception as e:
        st.error(f"No se pudieron leer las opciones: {e}")
        continue
    if not valores:
        st.caption("Todavía no hay opciones.")
    for v in valores:
        col_v, col_x = st.columns([6, 1], vertical_alignment="center")
        col_v.markdown(v)
        col_x.button("🗑", key=f"x_{categoria}_{v}", on_click=quitar, args=(categoria, v),
                     help=f"Quitar «{v}»", use_container_width=True)
    c1, c2 = st.columns([5, 2], vertical_alignment="bottom")
    c1.text_input(f"Nueva opción de {titulo.lower()}", key=f"cfg_nueva_{categoria}",
                  on_change=agregar, args=(categoria,))
    c2.button("➕ Agregar", key=f"add_{categoria}", on_click=agregar, args=(categoria,), use_container_width=True)
    st.divider()

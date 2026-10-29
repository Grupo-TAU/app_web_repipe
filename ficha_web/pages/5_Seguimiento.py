import pandas as pd
import streamlit as st

import ui
from core import seguimiento as seg

st.title("Seguimiento")
st.caption("Visitas y presupuestos, leídos de la planilla de seguimiento (solo lectura). "
           "Se edita en Google Sheets.")


@st.cache_resource
def _fuente(_cfg):
    try:
        return seg.crear_fuente_seguimiento(_cfg), None
    except seg.SeguimientoError as e:
        return None, str(e)


@st.cache_data(ttl=120, show_spinner="Leyendo la planilla…")
def _visitas(_fuente_obj, clave: str):
    return _fuente_obj.visitas()


cfg = ui.config()
fuente, error = _fuente(cfg)
if fuente is None:
    st.error(error)
    st.stop()

if st.button("🔄 Actualizar"):
    _visitas.clear()

try:
    visitas = _visitas(fuente, "mock" if cfg.use_mock else cfg.seguimiento_sheet_id)
except seg.SeguimientoError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error(f"No se pudo leer la planilla: {e}")
    st.stop()

if not visitas:
    st.info("La planilla no tiene visitas todavía.")
    st.stop()

r = seg.resumir(visitas)


def pct(x):
    return "—" if x is None else f"{x:.0%}"


c = st.columns(4)
c[0].metric("Visitas hoy", r.hoy)
c[1].metric("Próximos 7 días", r.proximos_7_dias)
c[2].metric("Aceptación", pct(r.tasa_aceptacion), help="Aceptados sobre presupuestos enviados + aceptados.")
c[3].metric("Cancelación", pct(r.tasa_cancelacion), help="Canceladas sobre visitas de hoy o ya pasadas.")

g1, g2 = st.columns(2)
with g1:
    st.subheader("Presupuestos por estado")
    st.bar_chart(pd.Series(r.por_estado, name="Visitas"), color="#2E7D3E")
with g2:
    st.subheader("Visitas por mes")
    st.bar_chart(pd.Series(r.por_mes, name="Visitas"), color="#2E7D3E")

st.subheader(f"Pendientes de presupuesto ({len(r.pendientes)})")
st.caption("Visitas ya realizadas sin estado en la columna Presupuesto.")
if r.pendientes:
    st.dataframe(
        [{"Fecha": v.fecha, "Cliente": v.cliente, "Dirección": v.direccion, "Teléfono": v.telefono,
          "Correo": v.correo, "Fila": v.fila} for v in r.pendientes],
        hide_index=True, use_container_width=True,
        column_config={"Fecha": st.column_config.DateColumn(format="DD/MM/YYYY")})
else:
    st.success("No hay visitas pendientes.")

st.subheader("Todas las visitas")
f1, f2 = st.columns([2, 3])
estados = f1.multiselect("Estado", list(r.por_estado), placeholder="Todas")
texto = f2.text_input("Buscar", placeholder="Cliente, dirección, correo, teléfono…")
filas = seg.filtrar(visitas, set(estados) or None, texto)
filas.sort(key=lambda v: (v.fecha is None, v.fecha), reverse=True)
st.caption(f"{len(filas)} de {len(visitas)} visitas")
st.dataframe(
    [{"Fecha": v.fecha, "Hora": v.hora, "Cliente": v.cliente, "Dirección": v.direccion,
      "Teléfono": v.telefono, "Correo": v.correo, "Presupuesto": v.estado, "Comentario": v.comentario}
     for v in filas],
    hide_index=True, use_container_width=True,
    column_config={"Fecha": st.column_config.DateColumn(format="DD/MM/YYYY")})

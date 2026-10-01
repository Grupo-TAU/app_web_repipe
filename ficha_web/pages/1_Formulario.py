from datetime import date

import pandas as pd
import streamlit as st

import ui
from core.fotos import carpeta_id_valido, extraer_id_carpeta
from core.modelos import Inspeccion, Observacion, Patologia, id_valido

st.title("Formulario de inspección")

repo = ui.repositorio()
ss = st.session_state

COLS_OBS = ["obs_interna"]
COLS_PAT = ["metros", "patologia", "nro_figura"]
CAMPOS = {  # clave de widget -> valor por defecto
    "f_ubicacion": "", "f_solicitante": "", "f_operario": "", "f_fecha": date.today(),
    "f_acceso": "", "f_diametro": None, "f_material": "", "f_largo": None,
    "f_limpieza": "", "f_conclusiones": "", "f_drive": "",
}

# estado inicial
ss.setdefault("f_id", "")
ss.setdefault("f_ver", 0)  # cambiar la versión reinicia los data_editor
ss.setdefault("f_df_obs", pd.DataFrame(columns=COLS_OBS))
ss.setdefault("f_df_pat", pd.DataFrame({"metros": pd.Series(dtype="float"), "patologia": pd.Series(dtype="str"),
                                        "nro_figura": pd.Series(dtype="Int64")}))
for k, v in CAMPOS.items():
    ss.setdefault(k, v)


def cargar(id_inspeccion: str):
    id_inspeccion = id_inspeccion.strip()
    ss["f_id"] = id_inspeccion
    if not id_valido(id_inspeccion):
        ss["f_msg"] = ("error", "El ID solo admite letras, números, punto, guion y guion bajo.")
        return
    try:
        insp = repo.obtener(id_inspeccion)
    except Exception as e:
        ss["f_msg"] = ("error", f"No se pudo consultar la base: {e}")
        return
    ss["f_ver"] += 1
    if insp is None:
        for k, v in CAMPOS.items():
            ss[k] = v
        ss["f_df_obs"] = pd.DataFrame(columns=COLS_OBS)
        ss["f_df_pat"] = pd.DataFrame({"metros": pd.Series(dtype="float"), "patologia": pd.Series(dtype="str"),
                                       "nro_figura": pd.Series(dtype="Int64")})
        ss["f_msg"] = ("info", f"La inspección «{id_inspeccion}» no existe: formulario en blanco para crearla.")
        return
    ss.update({
        "f_ubicacion": insp.ubicacion or "", "f_solicitante": insp.solicitante or "",
        "f_operario": insp.operario or "", "f_fecha": insp.fecha, "f_acceso": insp.acceso or "",
        "f_diametro": insp.diametro, "f_material": insp.material or "", "f_largo": insp.largo,
        "f_limpieza": insp.limpieza or "", "f_conclusiones": insp.conclusiones or "",
        "f_drive": insp.drive_folder_id or "",
    })
    ss["f_df_obs"] = pd.DataFrame({"obs_interna": [o.obs_interna for o in insp.observaciones]})
    ss["f_df_pat"] = pd.DataFrame({
        "metros": pd.Series([p.metros for p in insp.patologias], dtype="float"),
        "patologia": pd.Series([p.patologia for p in insp.patologias], dtype="str"),
        "nro_figura": pd.Series([p.nro_figura for p in insp.patologias], dtype="Int64"),
    })
    ss["f_msg"] = ("success", f"Inspección «{id_inspeccion}» cargada.")


# llegada desde «Editar datos»
if "form_cargar_id" in ss:
    cargar(ss.pop("form_cargar_id"))

c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
id_in = c1.text_input("ID de inspección", key="f_id")
c2.button("Cargar", on_click=lambda: cargar(ss["f_id"]))

if "f_msg" in ss:
    tipo, texto = ss.pop("f_msg")
    getattr(st, tipo)(texto)

st.text_input("Ubicación *", key="f_ubicacion")
a, b, c = st.columns(3)
a.text_input("Solicitante", key="f_solicitante")
b.text_input("Operario", key="f_operario")
c.date_input("Fecha", key="f_fecha", format="DD/MM/YYYY")
a, b, c, d = st.columns(4)
a.text_input("Acceso", key="f_acceso")
b.number_input("Diámetro (mm)", key="f_diametro", min_value=0.0, step=1.0, format="%.1f", value=None)
c.text_input("Material", key="f_material")
d.number_input("Largo (m)", key="f_largo", min_value=0.0, step=0.5, format="%.2f", value=None)
st.text_input("Limpieza", key="f_limpieza")
st.text_area("Conclusiones", key="f_conclusiones")
st.text_input("Link de la carpeta de Drive (opcional)", key="f_drive",
              help="Pegá el link de la carpeta de fotos o su ID. Si lo dejás vacío se busca por nombre «<id> - …».")

st.subheader("Observaciones (internas, no se imprimen)")
df_obs = st.data_editor(ss["f_df_obs"], num_rows="dynamic", use_container_width=True,
                        key=f"f_obs_{ss['f_ver']}",
                        column_config={"obs_interna": st.column_config.TextColumn("Observación interna")})

st.subheader("Patologías")
df_pat = st.data_editor(ss["f_df_pat"], num_rows="dynamic", use_container_width=True,
                        key=f"f_pat_{ss['f_ver']}",
                        column_config={
                            "metros": st.column_config.NumberColumn("Metros", min_value=0.0, format="%.2f"),
                            "patologia": st.column_config.TextColumn("Patología"),
                            "nro_figura": st.column_config.NumberColumn("N° figura", min_value=1, step=1),
                        })


def _num(v):
    return None if pd.isna(v) else float(v)


def construir() -> tuple[Inspeccion | None, list[str], list[str]]:
    errores, avisos = [], []
    id_ = ss["f_id"].strip()
    if not id_valido(id_):
        errores.append("El ID es obligatorio y solo admite letras, números, punto, guion y guion bajo.")
    if not ss["f_ubicacion"].strip():
        errores.append("La ubicación es obligatoria.")
    carpeta = extraer_id_carpeta(ss["f_drive"])
    if carpeta and not carpeta_id_valido(carpeta):
        errores.append("El link/ID de la carpeta de Drive no es válido.")

    pats = []
    for _, fila in df_pat.iterrows():
        nombre = "" if pd.isna(fila["patologia"]) else str(fila["patologia"]).strip()
        metros = _num(fila["metros"])
        fig = None if pd.isna(fila["nro_figura"]) else int(fila["nro_figura"])
        if not nombre and metros is None and fig is None:
            continue
        if not nombre:
            errores.append("Hay una fila de patologías sin descripción.")
            continue
        if metros is not None and metros < 0:
            errores.append(f"Los metros de «{nombre}» no pueden ser negativos.")
        pats.append(Patologia(nombre, metros, fig))
    figuras = [p.nro_figura for p in pats if p.nro_figura is not None]
    repetidas = sorted({f for f in figuras if figuras.count(f) > 1})
    if repetidas:
        avisos.append("Figuras repetidas: " + ", ".join(map(str, repetidas)) + ". Se guarda igual.")

    obs = [Observacion(str(o).strip()) for o in df_obs["obs_interna"] if not pd.isna(o) and str(o).strip()]
    if errores:
        return None, errores, avisos
    return Inspeccion(
        id=id_, ubicacion=ss["f_ubicacion"].strip(),
        solicitante=ss["f_solicitante"].strip() or None, operario=ss["f_operario"].strip() or None,
        fecha=ss["f_fecha"], acceso=ss["f_acceso"].strip() or None,
        diametro=ss["f_diametro"], material=ss["f_material"].strip() or None,
        largo=ss["f_largo"], limpieza=ss["f_limpieza"].strip() or None,
        conclusiones=ss["f_conclusiones"].strip() or None, drive_folder_id=carpeta or None,
        observaciones=obs, patologias=pats,
    ), errores, avisos


g, p = st.columns([1, 1])
if g.button("Guardar", type="primary"):
    insp, errores, avisos = construir()
    for e in errores:
        st.error(e)
    for a in avisos:
        st.warning(a)
    if insp:
        try:
            repo.guardar(insp)
            ss.pop("_ficha_cache", None)
            st.success(f"Inspección «{insp.id}» guardada.")
        except Exception as e:
            st.error(f"No se pudo guardar: {e}")
if p.button("Sacar ficha PDF"):
    if not id_valido(ss["f_id"].strip()):
        st.error("Ingresá un ID válido.")
    else:
        ui.ir_a_ficha(ss["f_id"].strip())

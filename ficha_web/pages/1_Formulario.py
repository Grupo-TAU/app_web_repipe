from datetime import date

import streamlit as st

import ui
from core.fotos import carpeta_id_valido, extraer_id_carpeta
from core.modelos import Inspeccion, Observacion, Patologia, id_valido

st.title("Formulario de inspección")

repo = ui.repositorio()
ss = st.session_state

CAMPOS = {  # clave de widget -> valor por defecto
    "f_ubicacion": "", "f_solicitante": "", "f_operario": None, "f_fecha": date.today(),
    "f_acceso": "", "f_diametro": None, "f_material": None, "f_largo": None,
    "f_limpieza": "", "f_conclusiones": "", "f_drive": "",
}

# Observaciones y patologías son listas de filas con un uid; cada fila tiene sus propios widgets
# (en pantallas chicas las columnas se apilan, a diferencia de una tabla editable).
ss.setdefault("f_id", "")
ss.setdefault("f_uid", 0)
ss.setdefault("f_obs", [])
ss.setdefault("f_pat", [])
for k, v in CAMPOS.items():
    ss.setdefault(k, v)


def _uid() -> int:
    ss["f_uid"] += 1
    return ss["f_uid"]


def agregar_obs(texto: str = ""):
    u = _uid()
    ss["f_obs"].append(u)
    ss[f"o_{u}"] = texto


def agregar_pat(metros=None, patologia: str = "", figura=None):
    u = _uid()
    ss["f_pat"].append(u)
    ss[f"pm_{u}"], ss[f"pp_{u}"], ss[f"pf_{u}"] = metros, patologia, figura


def quitar(lista: str, u: int):
    ss[lista].remove(u)


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
    ss["f_obs"], ss["f_pat"] = [], []
    if insp is None:
        ss.update(CAMPOS)
        ss["f_msg"] = ("info", f"La inspección «{id_inspeccion}» no existe: formulario en blanco para crearla.")
        return
    ss.update({
        "f_ubicacion": insp.ubicacion or "", "f_solicitante": insp.solicitante or "",
        "f_operario": insp.operario or None, "f_fecha": insp.fecha, "f_acceso": insp.acceso or "",
        "f_diametro": insp.diametro, "f_material": insp.material or None, "f_largo": insp.largo,
        "f_limpieza": insp.limpieza or "", "f_conclusiones": insp.conclusiones or "",
        "f_drive": insp.drive_folder_id or "",
    })
    for o in insp.observaciones:
        agregar_obs(o.obs_interna)
    for p in insp.patologias:
        agregar_pat(p.metros, p.patologia, p.nro_figura)
    ss["f_msg"] = ("success", f"Inspección «{id_inspeccion}» cargada.")


# llegada desde «Editar datos»
if "form_cargar_id" in ss:
    cargar(ss.pop("form_cargar_id"))

c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
c1.text_input("ID de inspección", key="f_id")
c2.button("Cargar", on_click=lambda: cargar(ss["f_id"]), use_container_width=True)

if "f_msg" in ss:
    tipo, texto = ss.pop("f_msg")
    getattr(st, tipo)(texto)

st.text_input("Ubicación *", key="f_ubicacion")
def _opciones(categoria: str, key: str) -> list[str]:
    """Opciones del desplegable + el valor actual si ya no está en la lista (inspecciones viejas)."""
    lista = ui.opciones(categoria)
    actual = ss.get(key)
    return lista + [actual] if actual and actual not in lista else lista


a, b, c = st.columns(3)
a.text_input("Solicitante", key="f_solicitante")
b.selectbox("Operario", _opciones("operario", "f_operario"), index=None, key="f_operario",
            placeholder="Elegir…", help="¿No está? Agregalo en Configuración.")
c.date_input("Fecha", key="f_fecha", format="DD/MM/YYYY")
a, b, c, d = st.columns(4)
a.text_input("Acceso", key="f_acceso")
b.number_input("Diámetro (mm)", key="f_diametro", min_value=0.0, step=1.0, format="%.1f", value=None)
c.selectbox("Material", _opciones("material", "f_material"), index=None, key="f_material",
            placeholder="Elegir…", help="¿No está? Agregalo en Configuración.")
d.number_input("Largo (m)", key="f_largo", min_value=0.0, step=0.5, format="%.2f", value=None)
st.text_input("Limpieza", key="f_limpieza")
st.text_area("Conclusiones", key="f_conclusiones")
st.text_input("Link de la carpeta de Drive (opcional)", key="f_drive",
              help="Pegá el link de la carpeta de fotos o su ID. Si lo dejás vacío se busca por nombre «<id> - …».")

st.subheader("Observaciones (internas, no se imprimen)")
for u in ss["f_obs"]:
    col_t, col_x = st.columns([6, 1], vertical_alignment="center")
    col_t.text_input("Observación interna", key=f"o_{u}", label_visibility="collapsed",
                     placeholder="Observación interna")
    col_x.button("🗑", key=f"xo_{u}", on_click=quitar, args=("f_obs", u), help="Quitar", use_container_width=True)
st.button("➕ Agregar observación", on_click=agregar_obs)

st.subheader("Patologías")
for u in ss["f_pat"]:
    with st.container(border=True):
        m, f, t, x = st.columns([2, 2, 6, 1], vertical_alignment="bottom")
        m.number_input("Metros", key=f"pm_{u}", min_value=0.0, step=0.5, format="%.2f", value=None)
        f.number_input("N° figura", key=f"pf_{u}", min_value=1, step=1, value=None)
        t.text_input("Patología", key=f"pp_{u}")
        x.button("🗑", key=f"xp_{u}", on_click=quitar, args=("f_pat", u), help="Quitar", use_container_width=True)
st.button("➕ Agregar patología", on_click=agregar_pat)


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
    for u in ss["f_pat"]:
        nombre = (ss.get(f"pp_{u}") or "").strip()
        metros = ss.get(f"pm_{u}")
        fig = ss.get(f"pf_{u}")
        fig = int(fig) if fig is not None else None
        if not nombre and metros is None and fig is None:
            continue
        if not nombre:
            errores.append("Hay una patología sin descripción.")
            continue
        pats.append(Patologia(nombre, metros, fig))
    figuras = [p.nro_figura for p in pats if p.nro_figura is not None]
    repetidas = sorted({f for f in figuras if figuras.count(f) > 1})
    if repetidas:  # el N° de figura es único por inspección (también lo exige la base)
        errores.append("N° de figura repetido: " + ", ".join(map(str, repetidas)) + ". Cada figura puede usarse una sola vez.")

    obs = [Observacion(t.strip()) for u in ss["f_obs"] if (t := ss.get(f"o_{u}") or "").strip()]
    if errores:
        return None, errores, avisos
    return Inspeccion(
        id=id_, ubicacion=ss["f_ubicacion"].strip(),
        solicitante=ss["f_solicitante"].strip() or None, operario=ss["f_operario"] or None,
        fecha=ss["f_fecha"], acceso=ss["f_acceso"].strip() or None,
        diametro=ss["f_diametro"], material=ss["f_material"] or None,
        largo=ss["f_largo"], limpieza=ss["f_limpieza"].strip() or None,
        conclusiones=ss["f_conclusiones"].strip() or None, drive_folder_id=carpeta or None,
        observaciones=obs, patologias=pats,
    ), errores, avisos


g, p = st.columns(2)
if g.button("Guardar", type="primary", use_container_width=True):
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
if p.button("Sacar ficha PDF", use_container_width=True):
    if not id_valido(ss["f_id"].strip()):
        st.error("Ingresá un ID válido.")
    else:
        ui.ir_a_ficha(ss["f_id"].strip())

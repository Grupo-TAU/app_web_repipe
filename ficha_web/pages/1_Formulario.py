from datetime import date

import streamlit as st

import ui
from core.fotos import carpeta_id_valido, extraer_id_carpeta
from core.modelos import Inspeccion, Observacion, Patologia, id_valido

st.title("Formulario de inspección")

repo = ui.repositorio()
ss = st.session_state

# Campos con desplegable editable desde Configuración: clave de widget -> categoría
CAMPOS_OPCION = {
    "f_solicitante": "solicitante", "f_operario": "operario",
    "f_acceso_1": "acceso", "f_acceso_2": "acceso",   # Acceso 1 y 2 comparten la misma lista de opciones
    "f_material": "material", "f_limpieza": "limpieza",
}
CAMPOS = {  # clave de widget -> valor por defecto
    "f_ubicacion": "", "f_fecha": date.today(), "f_diametro": None, "f_largo": None,
    "f_conclusiones": "", "f_drive": "",
    **{k: None for k in CAMPOS_OPCION},          # desplegable sin elegir...
    **{k + "_t": "" for k in CAMPOS_OPCION},     # ...o texto libre si la categoría aún no tiene opciones
}

# Observaciones y patologías son listas de filas con un uid; cada fila tiene sus propios widgets
# (en pantallas chicas las columnas se apilan, a diferencia de una tabla editable).
ss.setdefault("f_id", "")
ss.setdefault("f_cargado", None)   # ID de la inspección cargada desde la base (None: formulario nuevo)
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
    ss[f"pm_{u}"], ss[f"pf_{u}"] = metros, figura
    poner(f"pp_{u}", patologia)


def quitar(lista: str, u: int):
    ss[lista].remove(u)


def poner(key: str, valor: str | None):
    """Asigna un valor a un campo con desplegable (y a su variante de texto libre)."""
    ss[key] = valor or None
    ss[key + "_t"] = valor or ""


def valor(key: str) -> str | None:
    """Valor actual del campo, según esté dibujado como desplegable o como texto libre."""
    if ss.get(key + "_modo") == "txt":
        return (ss.get(key + "_t") or "").strip() or None
    return ss.get(key) or None


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
    if insp is None:
        # ID nuevo. Si había otra inspección cargada se limpia el formulario; si no, se conserva lo escrito.
        if ss["f_cargado"] is not None:
            ss["f_obs"], ss["f_pat"] = [], []
            ss.update(CAMPOS)
            ss["f_cargado"] = None
        ss["f_msg"] = ("info", f"Inspección nueva «{id_inspeccion}».")
        return
    ss["f_obs"], ss["f_pat"] = [], []
    ss["f_cargado"] = id_inspeccion
    ss.update({
        "f_ubicacion": insp.ubicacion or "", "f_fecha": insp.fecha, "f_diametro": insp.diametro,
        "f_largo": insp.largo, "f_conclusiones": insp.conclusiones or "",
        "f_drive": insp.drive_folder_id or "",
    })
    poner("f_solicitante", insp.solicitante)
    poner("f_operario", insp.operario)
    poner("f_acceso_1", insp.acceso_1)
    poner("f_acceso_2", insp.acceso_2)
    poner("f_material", insp.material)
    poner("f_limpieza", insp.limpieza)
    for o in insp.observaciones:
        agregar_obs(o.obs_interna)
    for p in insp.patologias:
        agregar_pat(p.metros, p.patologia, p.nro_figura)
    ss["f_msg"] = ("success", f"Inspección «{id_inspeccion}» cargada.")


# llegada desde «Editar datos»
if "form_cargar_id" in ss:
    cargar(ss.pop("form_cargar_id"))

def _al_cambiar_id():
    if ss["f_id"].strip():
        cargar(ss["f_id"])


st.text_input("ID de inspección", key="f_id", on_change=_al_cambiar_id,
              help="Escribí el ID y apretá Enter: si ya existe, se cargan sus datos para editarla; si no, es una inspección nueva.")

if "f_msg" in ss:
    tipo, texto = ss.pop("f_msg")
    getattr(st, tipo)(texto)

def _opciones(categoria: str, key: str) -> list[str]:
    """Opciones del desplegable + el valor actual si ya no está en la lista (inspecciones viejas)."""
    lista = ui.opciones(categoria)
    actual = ss.get(key)
    return lista + [actual] if actual and actual not in lista else lista


def campo_opcion(contenedor, etiqueta: str, key: str, categoria: str, libre: bool = False):
    """Desplegable con las opciones configuradas; si la categoría aún no tiene, texto libre.

    Con `libre=True` el desplegable además deja escribir un valor nuevo (solo para esa fila/inspección,
    sin sumarlo a la lista) y nunca cae a texto libre.
    """
    previo = ss.get(key + "_modo")
    if libre or ui.opciones(categoria):
        if previo == "txt" and ss.get(key + "_t"):      # se agregaron opciones: conservar lo escrito
            ss[key] = ss[key + "_t"].strip() or None
        ss[key + "_modo"] = "sel"
        contenedor.selectbox(
            etiqueta, _opciones(categoria, key), index=None, key=key, accept_new_options=libre,
            placeholder="Elegir o escribir…" if libre else "Elegir…",
            help=("Elegí una descripción o escribí una nueva (solo para esta fila). "
                  "Para sumarla a la lista, usá Configuración.") if libre
            else "¿No está? Agregalo en Configuración.")
    else:
        if previo == "sel" and ss.get(key):             # se quedó sin opciones: conservar lo elegido
            ss[key + "_t"] = ss[key]
        ss[key + "_modo"] = "txt"
        contenedor.text_input(etiqueta, key=key + "_t",
                              help="Todavía no hay opciones: se escribe a mano. Cargalas en Configuración.")


st.text_input("Ubicación *", key="f_ubicacion")
a, b, c = st.columns(3)
campo_opcion(a, "Solicitante", "f_solicitante", "solicitante")
campo_opcion(b, "Operario", "f_operario", "operario")
c.date_input("Fecha", key="f_fecha", format="DD/MM/YYYY")
a, b, c = st.columns(3)
campo_opcion(a, "Acceso 1", "f_acceso_1", "acceso")
campo_opcion(b, "Acceso 2", "f_acceso_2", "acceso")
campo_opcion(c, "Material", "f_material", "material")
a, b, c = st.columns(3)
a.number_input("Diámetro (mm)", key="f_diametro", min_value=0.0, step=1.0, format="%.1f", value=None)
b.number_input("Largo (m)", key="f_largo", min_value=0.0, step=0.5, format="%.2f", value=None)
campo_opcion(c, "Limpieza", "f_limpieza", "limpieza")
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
        campo_opcion(t, "Patología", f"pp_{u}", "patologia", libre=True)
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
        nombre = valor(f"pp_{u}") or ""
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
        solicitante=valor("f_solicitante"), operario=valor("f_operario"),
        fecha=ss["f_fecha"], acceso_1=valor("f_acceso_1"), acceso_2=valor("f_acceso_2"),
        diametro=ss["f_diametro"], material=valor("f_material"),
        largo=ss["f_largo"], limpieza=valor("f_limpieza"),
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

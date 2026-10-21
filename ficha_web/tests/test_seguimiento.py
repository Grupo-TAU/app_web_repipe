from datetime import date

from core import seguimiento as seg

HOY = date(2026, 10, 21)

FILAS = [
    ["Fecha de visita", "Hora", "Direccion", "Nombre", "Apellido", "Correo", "Telefono",
     "Recordatorio", "Presupuesto", "Comentario"],
    ["15/10/2026", "8:00", "Defensa 2046", "Santiago", "Baez", "s@x.com", "99", "", "Enviado", ""],
    ["06/10/2026", "15:00", "Solano 2448", "Juan", "Zinno", "j@x.com", "98", "", "aceptado ", ""],
    ["08/10/2026", "14:00", "Aguirre 1122", "Daniel", "Pineyro", "d@x.com", "95", "", "Cancelado", ""],
    ["20/10/2026", "8:00", "Libertad 2396", "Javier", "Emm", "jv@x.com", "91"],   # fila corta, sin estado
    ["21/10/2026", "13:00", "Muñoz 3257", "German", "Lungo", "g@x.com", "99", "", "", ""],
    ["", "", "", "", "", "", "", "", "", ""],                                     # fila vacía
    ["25/10/2026", "10:00", "Italia 1", "Ana", "Paz", "a@x.com", "90", "", "", ""],
]


def test_parseo_ubica_columnas_por_nombre_y_salta_vacias():
    v = seg.visitas_desde_filas(FILAS)
    assert len(v) == 6
    assert v[0].fecha == date(2026, 10, 15) and v[0].cliente == "Santiago Baez"
    assert v[3].presupuesto == "" and v[3].fila == 5


def test_columnas_en_otro_orden():
    filas = [["Presupuesto", "Fecha de visita"], ["Aceptado", "01/10/2026"]]
    (v,) = seg.visitas_desde_filas(filas)
    assert v.estado == "Aceptado" and v.fecha == date(2026, 10, 1)


def test_sin_columna_fecha_falla():
    try:
        seg.visitas_desde_filas([["Nombre"], ["x"]])
    except seg.SeguimientoError:
        return
    raise AssertionError("debía fallar")


def test_estado_normaliza_mayusculas_y_espacios():
    v = seg.visitas_desde_filas(FILAS)
    assert v[1].estado == "Aceptado"
    assert v[3].estado == seg.SIN_ESTADO


def test_resumen():
    r = seg.resumir(seg.visitas_desde_filas(FILAS), HOY)
    assert r.total == 6
    assert r.hoy == 1                       # la de hoy sin cancelar
    assert r.proximos_7_dias == 1           # 25/10
    assert r.por_estado["Enviado"] == 1 and r.por_estado["Aceptado"] == 1
    assert r.tasa_aceptacion == 0.5
    assert r.tasa_cancelacion == 1 / 5      # 1 cancelada de 5 visitas hasta hoy
    assert [p.cliente for p in r.pendientes] == ["Javier Emm"]
    assert r.por_mes == {"2026-10": 6}


def test_resumen_sin_datos_no_divide_por_cero():
    r = seg.resumir([], HOY)
    assert r.tasa_aceptacion is None and r.tasa_cancelacion is None


def test_filtrar():
    v = seg.visitas_desde_filas(FILAS)
    assert [x.cliente for x in seg.filtrar(v, {"Cancelado"})] == ["Daniel Pineyro"]
    assert len(seg.filtrar(v, texto="MUNOZ")) == 1         # ñ/mayúsculas indiferentes
    assert len(seg.filtrar(v, desde=date(2026, 10, 20), hasta=date(2026, 10, 21))) == 2


def test_extraer_id_planilla():
    url = "https://docs.google.com/spreadsheets/d/1e-n4To02pc_dfXw/edit?gid=0#gid=0"
    assert seg.extraer_id_planilla(url) == "1e-n4To02pc_dfXw"
    assert seg.extraer_id_planilla(" abc123 ") == "abc123"


def test_mock_genera_datos_coherentes():
    v = seg.MockFuenteSeguimiento(HOY).visitas()
    r = seg.resumir(v, HOY)
    assert r.hoy == 1 and r.pendientes and r.tasa_aceptacion is not None

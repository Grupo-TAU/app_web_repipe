"""Jinja2 -> HTML, WeasyPrint -> PDF, y reducción de imágenes."""
import base64
import io
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image, ImageOps

from . import formato
from .config import RAIZ, Config
from .fotos import ETIQUETAS_FIJAS
from .modelos import FichaDatos

ANCHO_MAX = 1600
CALIDAD_JPEG = 80
COLUMNAS = 3

_env = Environment(
    loader=FileSystemLoader(RAIZ / "templates"),
    autoescape=select_autoescape(["html", "xml", "j2"], default_for_string=True, default=True),
)


def reducir_a_data_uri(datos: bytes) -> str:
    """Corrige orientación EXIF, achica a 1600 px de ancho y devuelve un data URI JPEG."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(datos)))
    img = img.convert("RGB")
    if img.width > ANCHO_MAX:
        img = img.resize((ANCHO_MAX, round(img.height * ANCHO_MAX / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=CALIDAD_JPEG, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _linea_observacion(p) -> str:
    texto = f"{formato.numero(p.metros)} m – {p.patologia}" if p.metros is not None else p.patologia
    return f"{texto} (Fig. {p.nro_figura})" if p.nro_figura is not None else texto


def contexto(ficha: FichaDatos, cfg: Config | None = None) -> dict:
    cfg = cfg or Config()
    i = ficha.inspeccion
    # sin metros al final; por metros ascendente
    ordenadas = sorted(i.patologias, key=lambda p: (p.metros is None, p.metros or 0))

    fotos_fijas = [
        {"etiqueta": etiqueta, "src": f.data_uri if (f := ficha.fijas.get(clave)) else None}
        for clave, etiqueta in ETIQUETAS_FIJAS.items()
    ]

    con_figura = sorted((p for p in i.patologias if p.nro_figura is not None), key=lambda p: p.nro_figura)
    celdas = []
    for p in con_figura:
        foto = ficha.figuras.get(p.nro_figura)
        pie = f"Fig. {p.nro_figura} — {formato.numero(p.metros)} m — {p.patologia}"
        celdas.append({"nro": p.nro_figura, "src": foto.data_uri if foto else None, "pie": pie})
    filas = [celdas[k:k + COLUMNAS] for k in range(0, len(celdas), COLUMNAS)]
    filas = [fila + [None] * (COLUMNAS - len(fila)) for fila in filas]

    return {
        "pagina": cfg.pagina,
        "margen": cfg.margen,
        "id": i.id,
        "ubicacion": i.ubicacion,
        "solicitante": formato.texto(i.solicitante),
        "fecha": formato.fecha(i.fecha),
        "acceso": formato.texto(i.acceso),
        "operario": formato.texto(i.operario),
        "material": formato.texto(i.material),
        "diametro": formato.numero(i.diametro, 1),
        "largo": formato.numero(i.largo),
        "limpieza": formato.texto(i.limpieza),
        "conclusiones": i.conclusiones or "",
        "observaciones": [_linea_observacion(p) for p in ordenadas],
        "fotos_fijas": fotos_fijas,
        "filas_figuras": filas,
    }


def render_html(ficha: FichaDatos, cfg: Config | None = None) -> str:
    return _env.get_template("ficha.html.j2").render(contexto(ficha, cfg))


def render_pdf(html: str) -> bytes:
    from weasyprint import HTML  # import tardío: necesita Pango (solo disponible en el contenedor)
    return HTML(string=html, base_url=str(Path(RAIZ))).write_pdf()

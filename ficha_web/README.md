# ficha_web — fichas de inspección sin QGIS

App web (Streamlit) con dos funciones:

1. **Formulario** para cargar/editar inspecciones, guardadas en **Supabase**.
2. **Ficha PDF**: ingresás el ID de inspección → vista previa (datos de Supabase, fotos de Google Drive) → descarga del PDF.

La lógica vive en `core/` (sin Streamlit); `pages/`, `app.py` y `ui.py` solo la invocan.

## Modo mock (sin Supabase ni Drive)

Es lo más rápido para probar. Con Docker (recomendado; WeasyPrint necesita Pango, que en Windows es complicado):

```bash
docker compose up --build
```

Abrir <http://localhost:8501>. Sin `.env` arranca en modo mock con la inspección `1001` y fotos de ejemplo (`fixtures/fotos/1001/`; la Fig. 3 falta a propósito para ver el recuadro «Sin foto» y el aviso). Los datos mock viven en memoria: se pierden al reiniciar.

## Configuración real

```bash
cp .env.example .env     # completar y poner USE_MOCK=0
```

| Variable | Qué es |
| --- | --- |
| `SUPABASE_URL`, `SUPABASE_KEY` | URL del proyecto y clave **publicable** (nunca la `service_role`) |
| `GOOGLE_SA_JSON_PATH` o `GOOGLE_SA_JSON` | JSON de la cuenta de servicio (ruta, o su contenido) |
| `DRIVE_PARENT_FOLDER_ID` | ID de la carpeta `05 - INSPECCIONES` |
| `USE_MOCK` | `1` = modo mock |
| `FOTOS_LOCAL_DIR` | Carpeta de fotos para modo mock |

Preparación de los servicios: `docs/02_supabase_setup.md` (ejecutar `supabase/migrations/0001_init.sql`, crear usuarios, desactivar registro abierto) y `docs/03_drive_fotos_setup.md` (cuenta de servicio y permiso de Lector).

Con Docker, para Drive montar el JSON como volumen de solo lectura (ver comentario en `docker-compose.yml`) y apuntar `GOOGLE_SA_JSON_PATH` a la ruta dentro del contenedor.

## Tests

```bash
docker compose run --rm --no-deps -v "${PWD}:/app" app pytest -q
```

## Verificar Drive

```bash
python scripts/test_drive.py <ruta_al_json> <url_o_id_de_carpeta>
```

## Convención de nombres de fotos

`General`, `Tapa`, `Camara` (con o sin tilde) y `Fig_1`, `Fig 02`, `Figura-3` o `4`, cualquier extensión de imagen. Las reglas están al inicio de `core/fotos.py`.

## Notas

- La app **no guarda estado local**: todo está en Supabase y Drive, así que puede moverse de la PC/servidor de la oficina a un hosting accesible desde internet sin cambiar código.
- Fuera de la v1 (ganchos dejados): croquis (`{# TODO croquis #}` en la plantilla), subida de fotos, roles, lotes, historial, uso desde el campo.
- Las fotos de ejemplo se regeneran con `python scripts/generar_fixtures.py`.

## Decisiones

- **Plantilla** basada en `Informe-OS-provisional.html` (original en `templates/Informe-OS-provisional.original.html`), no en `Informe-OS.html`. Ese archivo no traía barra de etiqueta de foto (`.fig-label-bar`), ni Acceso/Diámetro/Largo: se agregaron.
- **Página**: no hay `.qpt` en el repo; A4 vertical, márgenes 12 mm (`PAGINA` / `MARGEN` para cambiarlos).
- **Recuadro 4:3** (`padding-bottom: 75%` + `position:absolute`): se verificó que WeasyPrint lo renderiza bien; no hizo falta alto fijo.
- **Números**: hasta 2 decimales sin ceros finales (`27` y no `27,00`); el diámetro, 1 decimal.
- **Cache** de imágenes (clave `(file_id, modifiedTime)`, TTL 10 min) y del listado de la carpeta padre (5 min) con un cache propio en memoria dentro de `core/`, en vez de `st.cache_data`, para que `core/` no dependa de Streamlit.
- **`FuenteFotos.listar`** devuelve un `Listado(archivos, carpeta_id)`; así `core/ficha.py` guarda en la base el ID de carpeta resuelto sin acoplarse a Drive. Los problemas esperables de fotos se levantan como `FotosError` y se convierten en avisos.
- **Responsive (celular/tablet)**: el formulario usa filas con sus propios campos (observaciones y patologías) en vez de `st.data_editor`, porque una tabla editable es incómoda con el dedo; en pantallas angostas las columnas se apilan. CSS en `ui.estilos()` (botones altos, campos a 16 px para evitar el zoom de iOS) y una regla `@media screen` en la plantilla para la vista previa; el PDF no se ve afectado. Probado en emulación de 375 px (sin scroll horizontal), no en un dispositivo real.
- **Archivos extra** respecto a la estructura pedida: `ui.py` (pegamento con Streamlit), `core/auth.py` (login Supabase), `scripts/generar_fixtures.py`.
- El **PDF y la vista previa** se arman una vez por ficha y se guardan en la sesión; se invalidan al guardar o al volver a pedir la ficha.
- `pytest` va en `requirements.txt` (la imagen sirve también para correr los tests).
- Los `.md` de `docs/` son los de Notion con las credenciales reemplazadas por placeholders.

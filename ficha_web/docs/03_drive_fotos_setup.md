# 03_drive_fotos_setup

# 03 — Fotos en Google Drive: qué configurar para que la app las lea por ID / carpeta

Vértice 3 de 3. Objetivo: que la app web de fichas (`ficha_web/`) pueda, dado un N° de inspección, encontrar su carpeta de fotos en la Unidad compartida y descargar las imágenes para incrustarlas en la ficha PDF.

Carpeta de trabajo actual (Drive for Desktop en las PCs):

```
G:\Unidades compartidas\GRUPO TAU\04 - REPIPE\05 - INSPECCIONES\<id> - <ubicacion>
```

---

## 1. Concepto: por qué la ruta `G:\…` no sirve y qué la reemplaza

`G:\Unidades compartidas\…` existe solo en las PCs que tienen **Drive for Desktop** montado, y con la letra que cada una tenga. Un servidor (o un hosting) no tiene esa unidad, y este mismo problema de rutas ya les dio dolores de cabeza en los proyectos de QGIS.

Lo que sí funciona desde un servidor es la **API de Google Drive** con una **cuenta de servicio**: un “usuario robot” con su propia credencial (un archivo JSON) al que se le da permiso de **solo lectura** sobre la carpeta de inspecciones. La app le pide a la API “listame los archivos de la carpeta X” y “dame los bytes del archivo Y”. Los archivos siguen viviendo donde están; nadie tiene que cambiar cómo los sube.

La ruta `G:\…\<id> - <ubicacion>` se traduce a la API de más de una manera (ver sección 6); recomiendo **guardar el ID de la carpeta de Drive** en la base.

## 2. Antes de empezar: quién necesita qué permiso

| Paso | Quién puede hacerlo | Posible bloqueo |
| --- | --- | --- |
| Crear proyecto en Google Cloud y habilitar Drive API | Cualquiera con cuenta Google (mejor una de la empresa) | Ninguno usual |
| Crear la cuenta de servicio y su clave JSON | Dueño del proyecto de Cloud | En organizaciones de Google Cloud, una política puede **bloquear la creación de claves** de cuentas de servicio. Si aparece el error, el administrador de la organización debe levantarla para este proyecto |
| Agregar la cuenta de servicio a la Unidad compartida | Administrador de la Unidad compartida (o admin de Workspace) | Workspace puede **restringir compartir con cuentas externas** al dominio; la cuenta de servicio cuenta como externa |

Si algún paso se bloquea y el admin no lo habilita, hay un plan B en la sección 9 (credencial OAuth de un usuario técnico dedicado).

## 3. Google Cloud: proyecto, API y cuenta de servicio

1. Ir a [https://console.cloud.google.com](https://console.cloud.google.com/) y crear un proyecto: `ficha-web` (o similar).
2. **APIs y servicios → Biblioteca** → buscar **Google Drive API** → **Habilitar**.
3. **IAM y administración → Cuentas de servicio → Crear cuenta de servicio**:
    - Nombre: `ficha-web-lector correo electronico:` [ficha-web-lector@<proyecto-gcp>.iam.gserviceaccount.com](mailto:ficha-web-lector@<proyecto-gcp>.iam.gserviceaccount.com)
    - No asignarle roles a nivel de proyecto (no los necesita: el acceso se da desde Drive, no desde Cloud).
4. Entrar a la cuenta creada → pestaña **Claves → Agregar clave → Crear clave nueva → JSON**. Se descarga un `.json`. 
5. Copiar el **email de la cuenta de servicio**; se ve así:
[ficha-web-lector@<proyecto-gcp>.iam.gserviceaccount.com](mailto:ficha-web-lector@<proyecto-gcp>.iam.gserviceaccount.com)

Sobre el archivo JSON:

- Es una credencial: quien lo tiene lee todo lo que la cuenta pueda leer.
- **Nunca** va al repo ni se pega en chats. Agregar `.json` de credenciales al `.gitignore`.
- La app lo lee desde una ruta (`GOOGLE_SA_JSON_PATH`) o desde una variable con el contenido (`GOOGLE_SA_JSON`), según dónde corra (ver `01_prompt…`).
- Si se filtra: borrar la clave en la consola y crear otra (rotación).
- Quedo el archivo en: Escritorio/<proyecto-gcp>-590da4be997b.json

## 4. Darle acceso a la cuenta de servicio en Drive

Abrir Drive en el navegador con un usuario que administre la Unidad compartida.

**Opción recomendada (mínimo privilegio):** compartir solo la carpeta necesaria.

1. Navegar a `GRUPO TAU / 04 - REPIPE / 05 - INSPECCIONES`.
2. Clic derecho → **Compartir** → pegar el email de la cuenta de servicio → rol **Lector** → desmarcar “Notificar” → **Compartir**.

Desde ahí la cuenta lee esa carpeta y todo lo que tiene adentro (subcarpetas `<id> - <ubicacion>` incluidas).

**Alternativa (más amplia):** agregarla como miembro de toda la Unidad compartida GRUPO TAU (menú de la unidad → **Administrar miembros**) con rol Lector. No recomendado: le da lectura de todo lo demás de la unidad.

Verificación: abrir la carpeta → Compartir → debe figurar el email con “Lector”.

## 5. Obtener los IDs que la app necesita

El **ID** de una carpeta de Drive es el tramo final de su URL:

```
https://drive.google.com/drive/folders/1w06qXz9hrVLtuoimGMzln-8m6FxYv2A3
                                       └────────── ID de la carpeta ──────────┘
```

(Si la URL termina en `?usp=sharing` o similar, ese sufijo no es parte del ID.)

Se necesitan:

| Variable | Qué es | Cómo obtenerlo |
| --- | --- | --- |
| `DRIVE_PARENT_FOLDER_ID` | ID de la carpeta `05 - INSPECCIONES : <ID carpeta 05 - INSPECCIONES>` | Abrirla en el navegador y copiar el ID de la URL |
| `inspeccion.drive_folder_id` (por inspección) | ID de la carpeta `<id> - <ubicacion>` de esa inspección | Pegar la URL de la carpeta en el formulario de la app (extrae el ID), o resolverlo por nombre (sección 6) |

## 6. Cómo la app encuentra la carpeta de una inspección

Tres estrategias, en este orden de prioridad. La app las aplica en cascada.

### A. Por ID guardado (recomendada, principal)

`inspeccion.drive_folder_id` ya tiene valor → se listan directamente las imágenes de esa carpeta. Una sola llamada, sin ambigüedad, y **no se rompe si cambian el nombre de la carpeta** (corregir una tilde en la ubicación, por ejemplo).

Cómo se llena: el formulario tiene un campo opcional “Link de la carpeta de Drive”; el usuario pega la URL y la app extrae el ID con:

```python
m = re.search(r"/folders/([A-Za-z0-9_-]+)", texto)   # o el texto tal cual si ya es un ID
```

### B. Por nombre, con prefijo de ID (fallback + autocompletado)

Si `drive_folder_id` está vacío, la app busca dentro de `DRIVE_PARENT_FOLDER_ID` la subcarpeta cuyo nombre **empiece con `"<id> - "`**, y **guarda el ID encontrado** en `inspeccion.drive_folder_id` para no volver a buscar.

Por qué prefijo y no el nombre exacto `"<id> - <ubicacion>"`:

- La ubicación en la base y el nombre de la carpeta se cargan a mano en dos lugares: cualquier diferencia (una tilde, doble espacio, “Av.” vs “Avenida”, un espacio final) hace fallar el match exacto.
- Los acentos pueden estar en formas Unicode distintas (NFC vs NFD) que se ven idénticas y no comparan igual.
- Con prefijo solo importa el ID, que es la clave real.

Implementación: **no** usar `name contains` de la API (matchea por palabras, no por prefijo de texto). Listar las subcarpetas del padre (paginado) y filtrar en Python:

```python
carpetas = [f for f in listar_subcarpetas(svc, PARENT_ID) if f["name"].startswith(f"{id_insp} - ")]
# 0 resultados -> error claro "no hay carpeta para la inspección X"
# 2+ resultados -> error claro "hay carpetas duplicadas: ..." (no adivinar)
```

Cachear el listado del padre unos minutos (son cientos de carpetas, no miles).

### C. Ruta exacta `<id> - <ubicacion>` (no recomendada)

Solo si se quisiera reproducir literalmente la expresión de QGIS `"id" || ' - ' || "ubicacion"`. Es la más frágil por los motivos de B. Si igual se implementa, comparar con normalización (`unicodedata.normalize("NFC", …)`, `casefold()`, espacios colapsados).

**Recomendación:** A como camino normal + B como red de seguridad que se auto-corrige. Descartar C.

## 7. Convención de nombres de fotos (decisión pendiente, importante)

La ficha necesita saber **qué foto es cuál**: las tres fijas (General, Tapa, Cámara) y una foto por figura (`patologias.nro_figura`).

El problema: QField nombra las fotos `<N°_OS>-<timestamp>.<ext>`, y ese nombre **no contiene el número de figura**. Sin una convención, no hay forma confiable de emparejar “Figura 2” con un archivo (emparejar por orden de captura es frágil: una foto repetida corre todo).

**Convención propuesta** (al copiar las fotos a la carpeta de Drive, renombrarlas así):

| Tipo | Nombre de archivo (cualquier extensión de imagen) |
| --- | --- |
| General | `general.jpg` |
| Acceso 1 | `acceso_1.jpg` |
| Acceso 2 | `acceso_2.jpg` |
| Figura N | `1.jpg`, `2.jpg`, `3.jpg`… (también `Fig_1.jpg`, `Figura-3.jpg`) |

Reglas de matching que implementa la app (sobre el nombre sin extensión, sin distinguir mayúsculas ni tildes):

- Tipo fijo si el nombre empieza con `general`, o es `acceso` + 1 o 2 (`acceso_1`, `Acceso 2`, `acceso-02`).
- Figura N si coincide con `^(?:fig(?:ura)?[\s_-]*)?0*(\d+)$`.
- Si hay más de una foto para la misma figura → se usa la primera por orden alfabético y se avisa en la vista previa.
- Archivos que no encajan en ninguna regla se ignoran y se listan como aviso (“fotos sin clasificar”).

**Acción para vos:** abrir 2 o 3 carpetas reales de inspecciones y ver cómo se llaman hoy las fotos. Si ya hay una convención (por ejemplo `1001_fig3.jpg`), pasásela a la app: las reglas están en un solo archivo de configuración y se ajustan sin tocar el resto. Si no hay ninguna, adoptar la de arriba.

## 8. Detalles de la API y script de prueba

**Alcance (scope):** `https://www.googleapis.com/auth/drive.readonly` (solo lectura).

**Parámetros obligatorios para Unidades compartidas.** Sin ellos la API responde como si la carpeta estuviera vacía o no existiera:

- En `files.list`: `supportsAllDrives=True`, `includeItemsFromAllDrives=True`, `corpora="allDrives"`.
- En `files.get` / `get_media`: `supportsAllDrives=True`.

**Pesos de imagen:** las fotos de tablet pesan 2–6 MB cada una. Antes de incrustarlas en el HTML del PDF conviene reducirlas (ancho máx. ~1600 px, JPEG calidad ~80, corregir orientación EXIF con `ImageOps.exif_transpose`) con Pillow. Ficha de 6 fotos sin reducir = PDF de 20 MB+.

**Limitaciones:** los accesos directos de Drive (shortcuts) no se siguen; solo archivos reales. Formato HEIC no lo procesa Pillow por defecto: si las tablets guardan JPEG (lo habitual en Android) no hay problema.

### Script de prueba: `ficha_web/scripts/test_drive.py`

Correrlo **antes** de integrar nada: confirma que credencial, permisos e ID están bien.

```python
"""Uso: python test_drive.py <ruta_al_json_de_la_cuenta_de_servicio> <url_o_id_de_carpeta>"""
import io
import re
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def cliente_drive(ruta_json):
    creds = service_account.Credentials.from_service_account_file(ruta_json, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def id_de_carpeta(texto):
    m = re.search(r"/folders/([A-Za-z0-9_-]+)", texto)
    return m.group(1) if m else texto.strip()

def listar_imagenes(svc, carpeta_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", carpeta_id):
        raise ValueError(f"ID de carpeta inválido:{carpeta_id!r}")
    q = f"'{carpeta_id}' in parents and trashed=false and mimeType contains 'image/'"
    archivos, token = [], None
    while True:
        r = svc.files().list(
            q=q,
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
            pageSize=200,
            pageToken=token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
        ).execute()
        archivos += r["files"]
        token = r.get("nextPageToken")
        if not token:
            return sorted(archivos, key=lambda f: f["name"].casefold())

def descargar(svc, file_id):
    buf = io.BytesIO()
    req = svc.files().get_media(fileId=file_id, supportsAllDrives=True)
    dl = MediaIoBaseDownload(buf, req)
    listo = False
    while not listo:
        _, listo = dl.next_chunk()
    return buf.getvalue()

if __name__ == "__main__":
    ruta_json, carpeta = sys.argv[1], id_de_carpeta(sys.argv[2])
    svc = cliente_drive(ruta_json)
    imgs = listar_imagenes(svc, carpeta)
    print(f"{len(imgs)} imágenes en la carpeta{carpeta}")
    for f in imgs:
        print(f"{f['name']:<40}{int(f.get('size', 0)) / 1024:>8.0f} KB   id={f['id']}")
    if imgs:
        datos = descargar(svc, imgs[0]["id"])
        print(f"Descarga OK:{imgs[0]['name']} ({len(datos)} bytes)")
```

Instalación: `pip install google-api-python-client google-auth pillow`.

### Diagnóstico de errores

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| `404 File not found: <id>` | La cuenta de servicio no tiene acceso a esa carpeta, o el ID está mal copiado | Revisar sección 4; verificar que el email figure como Lector |
| Lista vacía pero la carpeta tiene fotos | Faltan `supportsAllDrives` / `includeItemsFromAllDrives`, o las “fotos” son accesos directos | Revisar parámetros; abrir la carpeta y confirmar que son archivos reales |
| `403 insufficientFilePermissions` | Rol insuficiente o compartido en otra carpeta | Compartir la carpeta correcta con rol Lector |
| `invalid_grant` / `Invalid JWT` | Clave revocada, o reloj del servidor desfasado | Generar clave nueva; sincronizar hora (NTP) |
| `403 rateLimitExceeded` / `429` | Demasiadas llamadas seguidas | Reintentar con espera creciente; cachear listados |
| `invalid_scope` | Scope mal escrito | Usar exactamente el de esta guía |

## 9. Cómo escalar desde acá

1. **Cache de archivos en la base.** Tabla `fotos(id_inspeccion, drive_file_id, nombre, tipo, nro_figura, modified_at)` llenada por un sync (al abrir la ficha, o un job nocturno). La ficha deja de listar la carpeta en cada apertura y se puede mostrar “fotos cargadas: 5/6” en el formulario.
2. **Cache de imágenes reducidas.** Guardar las versiones reducidas (o el PDF ya generado, con su `modifiedTime`) para no descargar y reprocesar 6 fotos por cada vista previa.
3. **Subir fotos desde la app.** Requiere scope de escritura (`drive.file` o `drive`), permiso de Editor para la cuenta de servicio sobre la carpeta, y resolver dónde se crea la carpeta `<id> - <ubicacion>`. Es el paso natural para eliminar el renombrado manual de la sección 7.
4. **Avisos de cambios.** `changes.watch` de la API notifica cuando aparecen archivos nuevos; es más complejidad de la que se justifica hasta tener mucho volumen.
5. **Plan B si el admin bloquea la cuenta de servicio.** Usar OAuth con un **usuario técnico dedicado** (ej. `fichas@…`, con acceso de Lector a la carpeta): se autoriza una vez y se guarda el refresh token como secreto. Funciona igual, pero depende de una cuenta de usuario (cambios de contraseña, 2FA, baja de la persona) y no de una identidad de servicio: es peor a mediano plazo.
6. **Acceso desde el campo.** Como la app habla con Drive por API y con Supabase por internet, no depende de que el usuario esté en la red de la oficina: si la app se despliega en un hosting accesible desde internet (o detrás de una VPN), el acceso remoto queda resuelto sin cambiar nada de este documento.
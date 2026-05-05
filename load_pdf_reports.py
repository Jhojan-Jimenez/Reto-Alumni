"""
load_pdf_report.py
Extrae skills de reportes PDF (WEF, Coursera, OCDE, McKinsey, etc.)
usando Google Document AI para OCR/parsing de alta calidad.
Asocia cada skill al año del reporte para análisis de tendencias.

──────────────────────────────────────────────────────────────────
SETUP DE GOOGLE CLOUD DOCUMENT AI (solo la primera vez)
──────────────────────────────────────────────────────────────────
1. Crea o selecciona un proyecto en https://console.cloud.google.com
2. Habilita la API:
     gcloud services enable documentai.googleapis.com
3. Crea un procesador Document AI:
   - Ve a: Console → Document AI → Mis procesadores → + Crear
   - Tipo recomendado: "Document OCR" (cubre PDFs escaneados y nativos)
   - Anota el PROCESSOR_ID que aparece en el detalle del procesador
4. Crea credenciales de servicio:
     gcloud iam service-accounts create observatorio-laboral
     gcloud projects add-iam-policy-binding TU_PROJECT_ID \
       --member="serviceAccount:observatorio-laboral@TU_PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/documentai.apiUser"
     gcloud iam service-accounts keys create credenciales_docai.json \
       --iam-account=observatorio-laboral@TU_PROJECT_ID.iam.gserviceaccount.com
5. Exporta las credenciales:
     export GOOGLE_APPLICATION_CREDENTIALS="ruta/a/credenciales_docai.json"
6. Instala el cliente:
     pip install google-cloud-documentai pdfplumber

FALLBACK SIN GOOGLE CLOUD:
   Si no tienes credenciales, el script usa pdfplumber automáticamente.
   Menor precisión en PDFs escaneados, igual de bueno en PDFs nativos.
──────────────────────────────────────────────────────────────────

Uso:
    python3 load_pdf_report.py <archivo.pdf> [opciones]

Opciones:
    --anio      Año del reporte (si no se especifica, se detecta del texto)
    --fuente    Nombre corto de la fuente (ej: "Coursera", "WEF", "McKinsey")
    --idioma    es|en  (default: en — la mayoría de reportes globales están en inglés)
    --salida    Ruta del JSON de salida (default: data/processed/pdf_skills_<fuente>_<anio>.json)

Ejemplos:
    python3 load_pdf_report.py "Job-Skills-Report-2025.pdf" --fuente Coursera --idioma en
    python3 load_pdf_report.py "WEF_Future_of_Jobs_2023.pdf" --fuente WEF --anio 2023
    python3 load_pdf_report.py "reporte_mintic_2022.pdf" --fuente MinTIC --idioma es --anio 2022
"""

import os
import re
import sys
import json
import argparse
import warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

DICT_PATH = Path("data/processed/diccionario_skills.json")
PROCESSED = Path("data/processed")

# ─────────────────────────────────────────────────────────────────────────────
# Google Document AI — configuración
# ─────────────────────────────────────────────────────────────────────────────

GCP_PROJECT_ID  = os.environ.get("GCP_PROJECT_ID",  "TU_PROJECT_ID")
GCP_LOCATION    = os.environ.get("GCP_LOCATION",    "us")       # "us" o "eu"
DOCAI_PROCESSOR = os.environ.get("DOCAI_PROCESSOR", "TU_PROCESSOR_ID")


# ─────────────────────────────────────────────────────────────────────────────
# Extracción de texto
# ─────────────────────────────────────────────────────────────────────────────

def extraer_texto_documentai(ruta_pdf: Path) -> tuple[str, dict]:
    """
    Extrae texto completo del PDF usando Google Document AI.
    Retorna (texto_completo, metadatos_docai).
    Lanza ImportError si el cliente no está instalado.
    Lanza Exception si las credenciales no están configuradas.
    """
    from google.cloud import documentai

    print("  Usando Google Document AI...")
    client = documentai.DocumentProcessorServiceClient()

    processor_name = client.processor_path(
        GCP_PROJECT_ID, GCP_LOCATION, DOCAI_PROCESSOR
    )

    with open(ruta_pdf, "rb") as f:
        contenido = f.read()

    documento_raw = documentai.RawDocument(
        content=contenido,
        mime_type="application/pdf"
    )
    request = documentai.ProcessRequest(
        name=processor_name,
        raw_document=documento_raw
    )

    resultado = client.process_document(request=request)
    doc = resultado.document

    # Metadatos útiles que Document AI provee
    meta = {
        "paginas":       len(doc.pages),
        "idioma_detectado": doc.pages[0].detected_languages[0].language_code
                            if doc.pages and doc.pages[0].detected_languages
                            else "desconocido",
    }

    return doc.text, meta


def extraer_texto_pdfplumber(ruta_pdf: Path) -> tuple[str, dict]:
    """
    Fallback: extrae texto con pdfplumber (sin costo, sin credenciales).
    Bueno para PDFs nativos (texto seleccionable). Menos preciso en scaneados.
    """
    import pdfplumber

    print("  Usando pdfplumber (fallback sin Document AI)...")
    paginas_texto = []

    with pdfplumber.open(ruta_pdf) as pdf:
        num_paginas = len(pdf.pages)
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                paginas_texto.append(texto)

    texto_completo = "\n".join(paginas_texto)
    meta = {"paginas": num_paginas, "idioma_detectado": "desconocido"}
    return texto_completo, meta


def extraer_metadatos_nativos_pdf(ruta_pdf: Path) -> dict:
    """
    Lee los metadatos XMP/Info nativos del PDF sin necesidad de OCR.
    Los PDFs bien formados incluyen campos como CreationDate, ModDate,
    dc:title, pdf:Keywords, xmp:CreateDate, etc.
    Retorna un dict con los campos encontrados (puede estar vacío).
    """
    metadatos = {}

    # Intento 1: pypdf (más completo para metadatos XMP)
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(ruta_pdf))

        # Metadatos /Info estándar (autor, título, creador, fecha)
        info = reader.metadata
        if info:
            for campo, valor in info.items():
                if valor:
                    # Limpiar prefijo "/" de claves como "/CreationDate"
                    clave_limpia = campo.lstrip("/")
                    metadatos[clave_limpia] = str(valor)

        # Metadatos XMP (más ricos, incluyen dc:date, xmp:CreateDate, etc.)
        xmp = reader.xmp_metadata
        if xmp:
            for campo in ["dc_date", "xmp_create_date", "xmp_modify_date",
                          "dc_title", "dc_description", "pdf_keywords"]:
                valor = getattr(xmp, campo, None)
                if valor:
                    metadatos[f"xmp_{campo}"] = str(valor)

        return metadatos

    except ImportError:
        pass
    except Exception:
        pass

    # Intento 2: pdfplumber como fallback para metadatos
    try:
        import pdfplumber
        with pdfplumber.open(ruta_pdf) as pdf:
            if pdf.metadata:
                for k, v in pdf.metadata.items():
                    if v:
                        metadatos[k.lstrip("/")] = str(v)
        return metadatos
    except Exception:
        return metadatos


def anio_de_metadatos_pdf(metadatos: dict) -> int | None:
    """
    Intenta extraer el año de los metadatos nativos del PDF.
    Busca en campos de fecha con el siguiente orden de confianza:
      1. xmp:CreateDate / CreationDate  → fecha de creación del documento
      2. ModDate / xmp:ModifyDate       → fecha de modificación (menos confiable)
      3. dc:date                        → fecha Dublin Core (publicación)
    Los valores pueden venir en formatos: "D:20250115120000", "2025-01-15T12:00:00Z", "2025"
    """
    anio_actual = datetime.now().year
    rango_valido = range(2010, anio_actual + 2)

    # Campos a revisar en orden de prioridad
    campos_fecha = [
        "xmp_xmp_create_date",   # XMP CreateDate
        "xmp_dc_date",           # Dublin Core date
        "CreationDate",          # PDF /Info CreationDate
        "xmp_xmp_modify_date",   # XMP ModifyDate
        "ModDate",               # PDF /Info ModDate
    ]

    patron_anio = re.compile(r'(20\d{2})')

    for campo in campos_fecha:
        valor = metadatos.get(campo, "")
        if not valor:
            continue
        match = patron_anio.search(str(valor))
        if match:
            anio = int(match.group(1))
            if anio in rango_valido:
                print(f"  Año detectado de metadatos PDF ({campo}): {anio}")
                return anio

    return None


def extraer_texto(ruta_pdf: Path) -> tuple[str, dict, str]:
    """
    Intenta Document AI primero; cae a pdfplumber si no hay credenciales.
    Retorna (texto, metadatos, metodo_usado).
    """
    # Siempre extraemos metadatos nativos del PDF antes del OCR —
    # son independientes del método de extracción y se usan para detectar el año.
    meta_nativos = extraer_metadatos_nativos_pdf(ruta_pdf)
    if meta_nativos:
        print(f"  Metadatos nativos del PDF encontrados: {list(meta_nativos.keys())}")

    credenciales_ok = (
        GCP_PROJECT_ID != "TU_PROJECT_ID" and
        DOCAI_PROCESSOR != "TU_PROCESSOR_ID" and
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    )

    if credenciales_ok:
        try:
            texto, meta = extraer_texto_documentai(ruta_pdf)
            meta["metadatos_nativos"] = meta_nativos
            return texto, meta, "document_ai"
        except ImportError:
            print("  [!] google-cloud-documentai no instalado. Usando pdfplumber.")
        except Exception as e:
            print(f"  [!] Error en Document AI: {e}. Usando pdfplumber.")

    texto, meta = extraer_texto_pdfplumber(ruta_pdf)
    meta["metadatos_nativos"] = meta_nativos
    return texto, meta, "pdfplumber"


# ─────────────────────────────────────────────────────────────────────────────
# Detección del año
# ─────────────────────────────────────────────────────────────────────────────

def detectar_anio(texto: str, nombre_archivo: str, meta_docai: dict | None = None) -> int | None:
    """
    Detecta el año del reporte en este orden de confianza:

    1. Metadatos nativos del PDF (CreationDate, XMP dates) — más confiable
       porque son puestos por el autor al publicar el documento.
    2. Patrón "Report 2025" / "Informe 2023" en las primeras páginas.
    3. Año más frecuente en las primeras 2.000 caracteres.
    4. Año en el nombre del archivo.

    Cuando el año viene de metadatos PERO difiere del año mencionado
    prominentemente en el título (ej: doc creado en dic 2024 para el
    reporte "2025"), se usa el año del título porque refleja la
    intención editorial, no la fecha técnica de generación.
    """
    anio_actual  = datetime.now().year
    rango_valido = range(2010, anio_actual + 2)

    # ── Estrategia 1: metadatos nativos del PDF ───────────────────────────────
    anio_meta = None
    if meta_docai and meta_docai.get("metadatos_nativos"):
        anio_meta = anio_de_metadatos_pdf(meta_docai["metadatos_nativos"])

    # ── Estrategia 2: patrón "Report YYYY" en título/primeras páginas ─────────
    patron_titulo = re.compile(
        r'\b(?:Report|Informe|Survey|Reporte|Index|Outlook|Study|Brief|Skills)\s+(20\d{2})\b',
        re.IGNORECASE
    )
    anio_titulo = None
    match = patron_titulo.search(texto[:3000])
    if match:
        candidato = int(match.group(1))
        if candidato in rango_valido:
            anio_titulo = candidato

    # ── Resolución: metadatos vs. título ──────────────────────────────────────
    if anio_meta and anio_titulo:
        if anio_meta != anio_titulo:
            # Si el título dice un año posterior al de los metadatos, es probable
            # que el doc se preparó antes de publicarlo (ej: "2025 Report" creado
            # en nov 2024). Usamos el año del título por ser la fecha editorial.
            if anio_titulo > anio_meta:
                print(f"  Año del título ({anio_titulo}) > metadatos ({anio_meta}): usando título.")
                return anio_titulo
            else:
                # Metadatos más recientes que el título: inusual, avisamos.
                print(f"  Año metadatos ({anio_meta}) > título ({anio_titulo}): usando metadatos.")
                return anio_meta
        print(f"  Año detectado — metadatos y título coinciden: {anio_meta}")
        return anio_meta

    if anio_titulo:
        print(f"  Año detectado del título: {anio_titulo}")
        return anio_titulo

    if anio_meta:
        return anio_meta  # ya imprimió su propio mensaje en anio_de_metadatos_pdf()

    # ── Estrategia 3: año más frecuente en el inicio del texto ───────────────
    from collections import Counter
    anios_encontrados = re.findall(r'\b(20\d{2})\b', texto[:2000])
    if anios_encontrados:
        conteo = Counter(a for a in anios_encontrados if int(a) in rango_valido)
        if conteo:
            anio = int(conteo.most_common(1)[0][0])
            print(f"  Año detectado del texto (frecuencia): {anio}")
            return anio

    # ── Estrategia 4: año en el nombre del archivo ────────────────────────────
    match_archivo = re.search(r'(20\d{2})', nombre_archivo)
    if match_archivo:
        anio = int(match_archivo.group(1))
        if anio in rango_valido:
            print(f"  Año detectado del nombre de archivo: {anio}")
            return anio

    print("  [!] No se pudo detectar el año por ninguna estrategia.")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Extracción de skills
# ─────────────────────────────────────────────────────────────────────────────

def normalizar(texto: str) -> str:
    import unicodedata
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def cargar_diccionario() -> dict:
    if not DICT_PATH.exists():
        raise FileNotFoundError(
            f"Diccionario de skills no encontrado en: {DICT_PATH}\n"
            "Asegúrate de tener el archivo data/processed/diccionario_skills.json"
        )
    with open(DICT_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_terminos(diccionario: dict, idioma: str) -> list[str]:
    if idioma == "en":
        soft_en  = list(diccionario["blandas"]["mapping_en"].values())
        tech     = diccionario["tecnicas"]["terminos"]
        return sorted(set(soft_en + tech))
    return diccionario["busqueda_rapida"]


def extraer_skills_del_texto(texto: str, diccionario: dict, idioma: str) -> dict:
    """
    Extrae skills del texto y retorna:
    {
      "skills_encontradas": [...],
      "frecuencias": {"skill": conteo, ...},
      "por_categoria": {"blandas": [...], "tecnicas": [...], ...}
    }
    """
    import re
    terminos = get_terminos(diccionario, idioma)
    texto_norm = normalizar(texto)

    frecuencias = {}
    for termino in terminos:
        patron = re.compile(r'\b' + re.escape(normalizar(termino)) + r'\b')
        matches = patron.findall(texto_norm)
        if matches:
            frecuencias[termino] = len(matches)

    # Categorizar
    blandas_norm  = {normalizar(s) for s in diccionario["blandas"]["terminos_es"]}
    tecnicas_norm = {normalizar(s) for s in diccionario["tecnicas"]["terminos"]}
    conocimientos = set(diccionario["ocupacol"]["conocimientos"])

    por_categoria = {"blandas": [], "tecnicas": [], "conocimientos": [], "destrezas": []}
    for skill in frecuencias:
        s_n = normalizar(skill)
        if s_n in blandas_norm:
            por_categoria["blandas"].append(skill)
        elif s_n in tecnicas_norm:
            por_categoria["tecnicas"].append(skill)
        elif skill in conocimientos:
            por_categoria["conocimientos"].append(skill)
        else:
            por_categoria["destrezas"].append(skill)

    return {
        "skills_encontradas": sorted(frecuencias.keys()),
        "frecuencias":        dict(sorted(frecuencias.items(), key=lambda x: -x[1])),
        "por_categoria":      por_categoria,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Guardado con metadatos temporales
# ─────────────────────────────────────────────────────────────────────────────

def guardar_resultado(
    resultado_skills: dict,
    anio: int,
    fuente: str,
    ruta_pdf: Path,
    metodo: str,
    meta_docai: dict,
    ruta_salida: Path
):
    """
    Guarda un JSON estructurado con las skills extraídas y sus metadatos temporales.
    Este JSON es consumido luego por build_tendencias.py para construir el historial.
    """
    salida = {
        "meta": {
            "fuente":          fuente,
            "anio":            anio,
            "archivo_origen":  ruta_pdf.name,
            "metodo_extraccion": metodo,
            "paginas":         meta_docai.get("paginas"),
            "idioma_detectado": meta_docai.get("idioma_detectado"),
            "metadatos_nativos_pdf": meta_docai.get("metadatos_nativos", {}),
            "fecha_procesamiento": datetime.now().isoformat(),
            "total_skills":    len(resultado_skills["skills_encontradas"]),
        },
        "skills": resultado_skills["frecuencias"],          # skill → menciones
        "por_categoria": resultado_skills["por_categoria"],
        "skills_lista":  resultado_skills["skills_encontradas"],
    }

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\n  ✓ Guardado: {ruta_salida}")


def mostrar_resumen(resultado: dict, fuente: str, anio: int):
    por_cat = resultado["por_categoria"]
    freq    = resultado["frecuencias"]
    top10   = list(freq.items())[:10]

    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RESUMEN — {fuente} {anio}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Skills únicas detectadas : {len(freq):>4}
  ├── Blandas    : {len(por_cat['blandas']):>4}
  ├── Técnicas   : {len(por_cat['tecnicas']):>4}
  ├── Conocimientos: {len(por_cat['conocimientos']):>4}
  └── Destrezas  : {len(por_cat['destrezas']):>4}

  TOP 10 SKILLS MÁS MENCIONADAS:
""")
    for skill, conteo in top10:
        barra = "█" * min(conteo, 40)
        print(f"  {skill:<45} {conteo:>3}x  {barra}")
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("""
  Próximo paso — actualizar el historial de tendencias:

    python3 build_tendencias.py

  Esto integrará este PDF con las demás fuentes (O*NET, Ocupacol, Adzuna)
  y calculará tendencias creciente/estable/decreciente por skill.
""")


# ─────────────────────────────────────────────────────────────────────────────
# Entrada principal
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extrae skills de un reporte PDF con metadatos temporales."
    )
    parser.add_argument("pdf", help="Ruta al archivo PDF")
    parser.add_argument("--anio",    type=int, default=None,
                        help="Año del reporte (se detecta automáticamente si no se da)")
    parser.add_argument("--fuente",  default="PDF",
                        help="Nombre corto de la fuente (ej: Coursera, WEF, McKinsey)")
    parser.add_argument("--idioma",  default="en", choices=["es", "en"],
                        help="Idioma del reporte: es|en (default: en)")
    parser.add_argument("--salida",  default=None,
                        help="Ruta de salida del JSON (auto-generada si no se da)")
    return parser.parse_args()


def main():
    args = parse_args()
    ruta_pdf = Path(args.pdf)

    if not ruta_pdf.exists():
        print(f"\n  ERROR: Archivo no encontrado: {ruta_pdf}")
        sys.exit(1)

    print(f"\n[1/4] Extrayendo texto de: {ruta_pdf.name}")
    texto, meta_docai, metodo = extraer_texto(ruta_pdf)
    print(f"  Páginas procesadas: {meta_docai.get('paginas', '?')}")
    print(f"  Caracteres extraídos: {len(texto):,}")

    print(f"\n[2/4] Detectando año del reporte...")
    anio = args.anio or detectar_anio(texto, ruta_pdf.name, meta_docai)
    if anio is None:
        # Si se llama desde Streamlit (no hay terminal interactiva), usar año actual
        if not sys.stdin.isatty():
            anio = datetime.now().year
            print(f"  [!] No se detectó el año. Se usará el año actual: {anio}")
            print(f"      Puedes especificarlo con --anio <año> para mayor precisión.")
        else:
            anio = int(input("  No se detectó el año. Ingrésalo manualmente: ").strip())

    print(f"\n[3/4] Extrayendo skills del texto (idioma: {args.idioma.upper()})...")
    diccionario = cargar_diccionario()
    resultado   = extraer_skills_del_texto(texto, diccionario, args.idioma)
    print(f"  Skills detectadas: {len(resultado['skills_encontradas'])}")

    print(f"\n[4/4] Guardando resultado...")
    nombre_salida = args.salida or str(
        PROCESSED / f"pdf_skills_{args.fuente.lower()}_{anio}.json"
    )
    guardar_resultado(
        resultado_skills = resultado,
        anio             = anio,
        fuente           = args.fuente,
        ruta_pdf         = ruta_pdf,
        metodo           = metodo,
        meta_docai       = meta_docai,
        ruta_salida      = Path(nombre_salida),
    )

    mostrar_resumen(resultado, args.fuente, anio)


if __name__ == "__main__":
    main()
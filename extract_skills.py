"""
extract_skills.py
Extrae skills de cualquier archivo CSV/Excel dado el nombre de la columna de descripción.

Uso:
    python3 extract_skills.py <archivo> <columna> [id_columna] [--idioma es|en]

Ejemplos:
    python3 extract_skills.py "Servicio de Empleo.csv" DESCRIPCION_VACANTE CODIGO_VACANTE
    python3 extract_skills.py linkedin_sample.csv descripcion id_oferta --idioma en

Modos de idioma:
    --idioma es  (default) Español: términos de Ocupacol + traducciones ES de O*NET + tech
    --idioma en            Inglés:  términos originales EN de O*NET + tech
                           Usar con datasets en inglés (LinkedIn, WEF, etc.)
"""

import sys
import json
import re
import unicodedata
from pathlib import Path
import pandas as pd

DICT_PATH  = Path("data/processed/diccionario_skills.json")
PROCESSED  = Path("data/processed")


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de texto
# ─────────────────────────────────────────────────────────────────────────────

def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes para comparación robusta."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


def cargar_diccionario() -> dict:
    with open(DICT_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_terminos(diccionario: dict, idioma: str) -> list[str]:
    """Retorna la lista de términos según el idioma del dataset."""
    if idioma == "en":
        # Nombres originales de O*NET en inglés + tech tools (neutras)
        soft_en   = list(diccionario["blandas"]["mapping_en"].values())
        tech      = diccionario["tecnicas"]["terminos"]
        return sorted(set(soft_en + tech))
    else:
        # Español (default): lista completa del diccionario
        return diccionario["busqueda_rapida"]


def cargar_archivo(ruta: str) -> pd.DataFrame:
    ruta = Path(ruta)
    if ruta.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(ruta)
    else:
        # Intenta utf-8-sig primero (archivos con BOM del gobierno colombiano)
        for enc in ("utf-8-sig", "latin-1", "utf-8"):
            try:
                return pd.read_csv(ruta, encoding=enc, low_memory=False)
            except UnicodeDecodeError:
                continue
    raise ValueError(f"No se pudo leer el archivo: {ruta}")


# ─────────────────────────────────────────────────────────────────────────────
# Motor de extracción
# ─────────────────────────────────────────────────────────────────────────────

def construir_patrones(terminos: list[str]) -> list[tuple[str, re.Pattern]]:
    """
    Construye patrones regex con límites de palabra para evitar falsos positivos.
    Ej: "R" no debe matchear dentro de "trabajar".
    """
    patrones = []
    for termino in terminos:
        termino_norm = normalizar(termino)
        # Términos cortos (≤2 chars) requieren límite de palabra estricto
        patron = r"\b" + re.escape(termino_norm) + r"\b"
        patrones.append((termino, re.compile(patron)))
    return patrones


def extraer_skills(descripcion: str, patrones: list[tuple[str, re.Pattern]]) -> list[str]:
    """Retorna la lista de skills encontradas en una descripción."""
    if not isinstance(descripcion, str) or not descripcion.strip():
        return []
    texto_norm = normalizar(descripcion)
    return [termino for termino, patron in patrones if patron.search(texto_norm)]


# ─────────────────────────────────────────────────────────────────────────────
# Proceso principal
# ─────────────────────────────────────────────────────────────────────────────

def procesar(archivo: str, col_descripcion: str, col_id: str | None = None, idioma: str = "es"):

    print(f"\n[1/4] Cargando diccionario de skills (modo: {idioma.upper()})...")
    diccionario = cargar_diccionario()
    terminos = get_terminos(diccionario, idioma)
    patrones = construir_patrones(terminos)
    print(f"  Términos cargados: {len(terminos)}")

    print(f"\n[2/4] Cargando archivo: {archivo}")
    df = cargar_archivo(archivo)
    print(f"  Filas: {len(df):,} | Columnas: {list(df.columns)}")

    if col_descripcion not in df.columns:
        print(f"\n  ERROR: columna '{col_descripcion}' no existe.")
        print(f"  Columnas disponibles: {list(df.columns)}")
        sys.exit(1)

    print(f"\n[3/4] Extrayendo skills de '{col_descripcion}'...")
    df["skills_encontradas"] = df[col_descripcion].apply(
        lambda desc: extraer_skills(desc, patrones)
    )
    df["num_skills"] = df["skills_encontradas"].apply(len)

    # Añadir categoría por tipo de skill
    blandas_norm   = [normalizar(s) for s in diccionario["blandas"]["terminos_es"]]
    tecnicas_norm  = [normalizar(s) for s in diccionario["tecnicas"]["terminos"]]

    def categorizar(skills_lista):
        cats = {"blandas": [], "tecnicas": [], "conocimientos": [], "destrezas": []}
        for s in skills_lista:
            s_n = normalizar(s)
            if s_n in blandas_norm:
                cats["blandas"].append(s)
            elif s_n in tecnicas_norm:
                cats["tecnicas"].append(s)
            else:
                # Conocimientos y destrezas Ocupacol
                if s in diccionario["ocupacol"]["conocimientos"]:
                    cats["conocimientos"].append(s)
                else:
                    cats["destrezas"].append(s)
        return cats

    df["skills_por_categoria"] = df["skills_encontradas"].apply(categorizar)

    print(f"\n[4/4] Generando archivos de salida...")

    # ── Archivo principal con skills por fila ──────────────────────────────
    nombre_base = Path(archivo).stem
    salida_main = PROCESSED / f"{nombre_base}_con_skills.csv"

    df_salida = df.copy()
    df_salida["skills_encontradas"]   = df_salida["skills_encontradas"].apply(json.dumps)
    df_salida["skills_por_categoria"] = df_salida["skills_por_categoria"].apply(json.dumps)
    df_salida.to_csv(salida_main, index=False, encoding="utf-8-sig")
    print(f"  ✓ Dataset con skills: {salida_main}")

    # ── Tabla de frecuencias de skills ────────────────────────────────────
    from collections import Counter
    todas_skills = [s for lista in df["skills_encontradas"] for s in lista]
    freq = Counter(todas_skills)

    df_freq = pd.DataFrame(freq.most_common(), columns=["skill", "menciones"])
    df_freq["porcentaje_ofertas"] = (df_freq["menciones"] / len(df) * 100).round(1)

    # Añadir categoría a la tabla de frecuencias
    def get_categoria(skill):
        s_n = normalizar(skill)
        if s_n in blandas_norm:   return "blanda"
        if s_n in tecnicas_norm:  return "técnica"
        if skill in diccionario["ocupacol"]["conocimientos"]: return "conocimiento"
        return "destreza"

    df_freq["categoria"] = df_freq["skill"].apply(get_categoria)

    salida_freq = PROCESSED / f"{nombre_base}_frecuencia_skills.csv"
    df_freq.to_csv(salida_freq, index=False, encoding="utf-8-sig")
    print(f"  ✓ Frecuencia de skills: {salida_freq}")

    # ── Resumen en consola ─────────────────────────────────────────────────
    con_skills = (df["num_skills"] > 0).sum()
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RESUMEN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total ofertas procesadas : {len(df):>6,}
  Ofertas con ≥1 skill     : {con_skills:>6,} ({con_skills/len(df)*100:.1f}%)
  Skills únicas detectadas : {len(freq):>6,}
  Promedio skills/oferta   : {df['num_skills'].mean():>6.1f}

  TOP 10 SKILLS MÁS DEMANDADAS:
""")
    for i, (_, row) in enumerate(df_freq.head(10).iterrows(), 1):
        barra = "█" * int(row["porcentaje_ofertas"] / 2)
        print(f"  {i:>2}. {row['skill']:<40} {row['menciones']:>4} menciones  {barra}")

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# ─────────────────────────────────────────────────────────────────────────────
# Entrada
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    args          = sys.argv[1:]
    idioma_arg    = "es"
    if "--idioma" in args:
        idx        = args.index("--idioma")
        idioma_arg = args[idx + 1]
        args       = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]

    archivo_entrada = args[0]
    columna_desc    = args[1]
    columna_id      = args[2] if len(args) > 2 else None

    procesar(archivo_entrada, columna_desc, columna_id, idioma=idioma_arg)

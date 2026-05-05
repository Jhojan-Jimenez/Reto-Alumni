"""
build_tendencias.py
Consolida TODAS las fuentes del Observatorio Laboral y construye
un historial temporal por skill para detectar tendencias.

Fuentes integradas:
  ┌─────────────────────┬──────────────┬───────────────────────────────────────────┐
  │ Fuente              │ Años         │ Cómo se genera                            │
  ├─────────────────────┼──────────────┼───────────────────────────────────────────┤
  │ O*NET               │ año base     │ build_dictionary.py                       │
  │ Ocupacol            │ año base     │ build_dictionary.py                       │
  │ Adzuna              │ año descarga │ load_adzuna.py + extract_skills.py        │
  │ LinkedIn            │ año descarga │ load_linkedin.py + extract_skills.py      │
  │ SPE (Serv. Empleo)  │ año vacante  │ extract_skills.py sobre CSV del gobierno  │
  │ PDF reports         │ año reporte  │ load_pdf_report.py                        │
  └─────────────────────┴──────────────┴───────────────────────────────────────────┘

Salida: data/processed/skills_tendencias.json
  {
    "pensamiento crítico": {
      "historial": {
        "2022": {"menciones": 145, "fuentes": ["SPE", "Ocupacol"]},
        "2023": {"menciones": 312, "fuentes": ["SPE", "Adzuna", "WEF"]},
        "2024": {"menciones": 589, "fuentes": ["SPE", "Adzuna", "Coursera", "LinkedIn"]}
      },
      "tendencia": "creciente",          # creciente | estable | decreciente
      "score_tendencia": 0.87,           # 0-1: qué tan fuerte es la señal
      "primera_aparicion": 2022,
      "ultima_aparicion": 2024,
      "categoria": "blanda"
    },
    ...
  }

Uso:
    python3 build_tendencias.py [--anio-base YYYY]

    --anio-base: año a usar para fuentes sin fecha explícita (O*NET, Ocupacol)
                 default: año actual
"""

import json
import re
import glob
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DICT_PATH        = Path("data/processed/diccionario_skills.json")
FREQ_PATTERN     = "data/processed/*_frecuencia_skills.csv"
PDF_PATTERN      = "data/processed/pdf_skills_*.json"
SALIDA           = Path("data/processed/skills_tendencias.json")


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────────────

def normalizar(texto: str) -> str:
    import unicodedata
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def cargar_diccionario() -> dict:
    with open(DICT_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_categoria(skill: str, diccionario: dict) -> str:
    s_n = normalizar(skill)
    blandas_norm  = {normalizar(s) for s in diccionario["blandas"]["terminos_es"]}
    tecnicas_norm = {normalizar(s) for s in diccionario["tecnicas"]["terminos"]}
    conocimientos = set(diccionario["ocupacol"]["conocimientos"])

    if s_n in blandas_norm:    return "blanda"
    if s_n in tecnicas_norm:   return "técnica"
    if skill in conocimientos: return "conocimiento"
    return "destreza"


# ─────────────────────────────────────────────────────────────────────────────
# Detectar año en nombre de archivo CSV (ej: "spe_2023_con_skills.csv")
# ─────────────────────────────────────────────────────────────────────────────

def detectar_anio_de_archivo(nombre: str, anio_fallback: int) -> int:
    match = re.search(r'(20\d{2})', nombre)
    return int(match.group(1)) if match else anio_fallback


def detectar_fuente_de_archivo(nombre: str) -> str:
    """Intenta inferir la fuente del nombre del CSV."""
    nombre_lower = nombre.lower()
    if "linkedin"  in nombre_lower: return "LinkedIn"
    if "adzuna"    in nombre_lower: return "Adzuna"
    if "spe"       in nombre_lower: return "SPE"
    if "servicio"  in nombre_lower: return "SPE"
    if "empleo"    in nombre_lower: return "SPE"
    return Path(nombre).stem.split("_")[0].capitalize()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Cargar aportaciones del diccionario base (O*NET + Ocupacol)
# ─────────────────────────────────────────────────────────────────────────────

def cargar_skills_base(diccionario: dict, anio_base: int) -> list[dict]:
    """
    O*NET y Ocupacol son fuentes estructurales: indican qué skills existen
    pero no su volumen real de demanda.

    Las registramos en un año ancla fijo (2020) con menciones=1 como línea base.
    Esto permite que cuando lleguen datos reales de PDFs o CSVs en años
    posteriores, la regresión lineal tenga dos o más puntos y pueda detectar
    pendiente (creciente / decreciente).

    Si el único dato disponible es este ancla → la skill quedará "estable",
    que es el comportamiento correcto cuando no hay evidencia de cambio.
    """
    ANIO_ANCLA = 2019   # año ancla separado de los datos simulados (que arrancan en 2020)
    registros = []
    for skill in diccionario["blandas"]["terminos_es"]:
        registros.append({
            "skill": skill, "anio": ANIO_ANCLA,
            "menciones": 1, "fuente": "ONET"
        })
    for skill in diccionario["tecnicas"]["terminos"]:
        registros.append({
            "skill": skill, "anio": ANIO_ANCLA,
            "menciones": 1, "fuente": "ONET"
        })
    for skill in diccionario["ocupacol"]["conocimientos"]:
        registros.append({
            "skill": skill, "anio": ANIO_ANCLA,
            "menciones": 1, "fuente": "Ocupacol"
        })
    for skill in diccionario["ocupacol"]["destrezas"]:
        registros.append({
            "skill": skill, "anio": ANIO_ANCLA,
            "menciones": 1, "fuente": "Ocupacol"
        })
    print(f"  Año ancla para fuentes base: {ANIO_ANCLA}")
    return registros


# ─────────────────────────────────────────────────────────────────────────────
# 2. Cargar aportaciones de los CSVs de frecuencia (extract_skills.py)
# ─────────────────────────────────────────────────────────────────────────────

def cargar_skills_csv_frecuencia(anio_fallback: int) -> list[dict]:
    """
    Lee todos los archivos *_frecuencia_skills.csv generados por extract_skills.py.
    Cada fila tiene: skill, menciones, porcentaje_ofertas, categoria.
    """
    import pandas as pd
    registros = []
    archivos  = glob.glob(FREQ_PATTERN)

    if not archivos:
        print("  [!] No se encontraron archivos *_frecuencia_skills.csv")
        return registros

    for ruta in archivos:
        nombre = Path(ruta).name
        anio   = detectar_anio_de_archivo(nombre, anio_fallback)
        fuente = detectar_fuente_de_archivo(nombre)

        try:
            df = pd.read_csv(ruta, encoding="utf-8-sig")
            for _, fila in df.iterrows():
                registros.append({
                    "skill":     str(fila["skill"]),
                    "anio":      anio,
                    "menciones": int(fila.get("menciones", 1)),
                    "fuente":    fuente,
                })
            print(f"  ✓ CSV cargado: {nombre} ({len(df)} skills, año {anio})")
        except Exception as e:
            print(f"  [!] Error leyendo {nombre}: {e}")

    return registros


# ─────────────────────────────────────────────────────────────────────────────
# 3. Cargar aportaciones de PDFs (load_pdf_report.py)
# ─────────────────────────────────────────────────────────────────────────────

def cargar_skills_pdf(anio_fallback: int) -> list[dict]:
    """
    Lee todos los json generados por load_pdf_report.py.
    """
    registros = []
    archivos  = glob.glob(PDF_PATTERN)

    if not archivos:
        print("  [!] No se encontraron archivos pdf_skills_*.json")
        return registros

    for ruta in archivos:
        try:
            with open(ruta, encoding="utf-8") as f:
                datos = json.load(f)

            meta   = datos.get("meta", {})
            anio   = meta.get("anio") or anio_fallback
            fuente = meta.get("fuente", "PDF")
            skills = datos.get("skills", {})  # {skill: menciones}

            for skill, menciones in skills.items():
                registros.append({
                    "skill":     skill,
                    "anio":      anio,
                    "menciones": int(menciones),
                    "fuente":    fuente,
                })
            print(f"  ✓ PDF cargado: {Path(ruta).name} ({len(skills)} skills, año {anio}, fuente: {fuente})")
        except Exception as e:
            print(f"  [!] Error leyendo {Path(ruta).name}: {e}")

    return registros


# ─────────────────────────────────────────────────────────────────────────────
# 4. Consolidar historial
# ─────────────────────────────────────────────────────────────────────────────

def construir_mapping_en_es(diccionario: dict) -> dict:
    """
    Construye un mapa de normalización: nombre_en_inglés → nombre_en_español.

    Esto permite que 'Critical Thinking' (Adzuna/PDF en inglés) y
    'pensamiento crítico' (SPE en español) se consoliden como la misma skill,
    acumulando puntos en múltiples años y permitiendo calcular tendencias.
    """
    mapping = {}
    # Soft skills O*NET: mapping_en = {es_term: en_term} → invertir a en → es
    for es_term, en_term in diccionario["blandas"]["mapping_en"].items():
        mapping[en_term.lower()] = es_term
        mapping[es_term.lower()] = es_term
    # Tech skills (iguales en ambos idiomas — normaliza capitalización)
    for skill in diccionario["tecnicas"]["terminos"]:
        mapping[skill.lower()] = skill
    # Ocupacol (español)
    for skill in diccionario["ocupacol"]["conocimientos"] + diccionario["ocupacol"]["destrezas"]:
        mapping[skill.lower()] = skill
    return mapping


_SKILL_MAPPING: dict = {}   # se inicializa en main()


def normalizar_skill_nombre(skill: str) -> str:
    """Retorna el nombre canónico de una skill (español, capitalización estándar)."""
    return _SKILL_MAPPING.get(skill.lower().strip(), skill)


def consolidar_historial(registros: list[dict]) -> dict:
    """
    Agrupa todos los registros por skill → año → {menciones, fuentes}.

    Normaliza los nombres para unificar variantes EN/ES:
      'Critical Thinking' + 'pensamiento crítico' → 'pensamiento crítico'
      'python' → 'Python'
    """
    historial = defaultdict(lambda: defaultdict(lambda: {"menciones": 0, "fuentes": set()}))

    for r in registros:
        skill = normalizar_skill_nombre(r["skill"])   # ← unifica EN↔ES
        anio  = str(r["anio"])
        historial[skill][anio]["menciones"] += r["menciones"]
        historial[skill][anio]["fuentes"].add(r["fuente"])

    # Convertir sets a listas para serialización JSON
    resultado = {}
    for skill, anios in historial.items():
        resultado[skill] = {
            anio: {
                "menciones": datos["menciones"],
                "fuentes":   sorted(datos["fuentes"]),
            }
            for anio, datos in sorted(anios.items())
        }
    return resultado


# ─────────────────────────────────────────────────────────────────────────────
# 5. Calcular tendencia
# ─────────────────────────────────────────────────────────────────────────────

def calcular_tendencia(historial_skill: dict) -> tuple[str, float]:
    """
    Calcula si una skill tiene tendencia creciente, estable o decreciente.

    Método:
    - Excluye el año ancla ONET (2019, menciones=1) del cálculo de pendiente,
      ya que ese valor artificial distorsiona la regresión.
    - Si quedan < 2 años reales → "estable"
    - Regresión lineal ponderada (años recientes tienen más peso)
    """
    ANIO_ANCLA_EXCLUIR = "2019"

    # Filtrar el año ancla estructural para no distorsionar la pendiente
    anios_reales = {a: v for a, v in historial_skill.items()
                    if a != ANIO_ANCLA_EXCLUIR and v["menciones"] > 1}

    # Si no quedan datos reales, usar todo (comportamiento de fallback)
    if len(anios_reales) < 2:
        anios_reales = historial_skill

    anios_ordenados = sorted(anios_reales.keys())

    if len(anios_ordenados) < 2:
        return "estable", 0.5

    x = list(range(len(anios_ordenados)))
    y = [anios_reales[a]["menciones"] for a in anios_ordenados]

    # Ponderación: años recientes pesan más (peso = posición + 1)
    w = [xi + 1 for xi in x]
    sw   = sum(w)
    swx  = sum(wi * xi for wi, xi in zip(w, x))
    swy  = sum(wi * yi for wi, yi in zip(w, y))
    swxx = sum(wi * xi * xi for wi, xi in zip(w, x))
    swxy = sum(wi * xi * yi for wi, xi, yi in zip(w, x, y))

    denominador = sw * swxx - swx ** 2
    if denominador == 0:
        return "estable", 0.5

    pendiente = (sw * swxy - swx * swy) / denominador

    # Normalizar pendiente respecto a la media ponderada de Y
    media_y = swy / sw if sw else 1
    pendiente_norm = pendiente / media_y if media_y else 0

    UMBRAL = 0.08
    if pendiente_norm > UMBRAL:
        score = min(1.0, 0.5 + pendiente_norm * 2)
        return "creciente", round(score, 3)
    elif pendiente_norm < -UMBRAL:
        score = min(1.0, 0.5 + abs(pendiente_norm) * 2)
        return "decreciente", round(score, 3)
    else:
        score = max(0.2, 0.5 - abs(pendiente_norm) / UMBRAL * 0.3)
        return "estable", round(score, 3)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Construir estructura final
# ─────────────────────────────────────────────────────────────────────────────

def construir_tendencias(historial_consolidado: dict, diccionario: dict) -> dict:
    tendencias = {}

    for skill, historial in historial_consolidado.items():
        tendencia, score = calcular_tendencia(historial)
        anios_str        = sorted(historial.keys())
        categoria        = get_categoria(skill, diccionario)

        # Calcular total de menciones y número de fuentes únicas
        total_menciones = sum(d["menciones"] for d in historial.values())
        fuentes_unicas  = sorted(set(
            f for d in historial.values() for f in d["fuentes"]
        ))

        tendencias[skill] = {
            "historial":        historial,
            "tendencia":        tendencia,
            "score_tendencia":  score,
            "primera_aparicion": int(anios_str[0]),
            "ultima_aparicion":  int(anios_str[-1]),
            "total_menciones":  total_menciones,
            "num_fuentes":      len(fuentes_unicas),
            "fuentes":          fuentes_unicas,
            "categoria":        categoria,
            "anios_cubiertos":  len(anios_str),
        }

    return tendencias


# ─────────────────────────────────────────────────────────────────────────────
# 7. Guardar y mostrar resumen
# ─────────────────────────────────────────────────────────────────────────────

def guardar_tendencias(tendencias: dict):
    meta = {
        "total_skills":    len(tendencias),
        "crecientes":      sum(1 for v in tendencias.values() if v["tendencia"] == "creciente"),
        "estables":        sum(1 for v in tendencias.values() if v["tendencia"] == "estable"),
        "decrecientes":    sum(1 for v in tendencias.values() if v["tendencia"] == "decreciente"),
        "fecha_generacion": datetime.now().isoformat(),
    }

    salida = {"meta": meta, "skills": tendencias}

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Tendencias guardadas en: {SALIDA}")
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RESUMEN DE TENDENCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total skills analizadas : {meta['total_skills']:>5}
  📈 Crecientes           : {meta['crecientes']:>5}
  ➡  Estables             : {meta['estables']:>5}
  📉 Decrecientes         : {meta['decrecientes']:>5}
""")

    # Top 10 crecientes
    top_crecientes = sorted(
        [(s, v) for s, v in tendencias.items() if v["tendencia"] == "creciente"],
        key=lambda x: -x[1]["score_tendencia"]
    )[:10]

    print("  TOP 10 SKILLS CON MAYOR CRECIMIENTO:\n")
    for skill, datos in top_crecientes:
        anios_con_data = " → ".join(
            f"{a}({datos['historial'][a]['menciones']})"
            for a in sorted(datos["historial"])
        )
        print(f"  ▲ {skill:<40} [{anios_con_data}]")

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("""
  Uso en dashboard.py:
    import json
    with open("data/processed/skills_tendencias.json") as f:
        datos = json.load(f)
    skills_crecientes = [
        s for s, v in datos["skills"].items()
        if v["tendencia"] == "creciente"
    ]
""")


# ─────────────────────────────────────────────────────────────────────────────
# Entrada principal
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Consolida todas las fuentes y calcula tendencias por skill."
    )
    parser.add_argument(
        "--anio-base", type=int, default=datetime.now().year,
        help=f"Año a asignar a fuentes sin fecha explícita (default: {datetime.now().year})"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    anio_base = args.anio_base

    print(f"\n[1/5] Cargando diccionario de skills...")
    diccionario = cargar_diccionario()
    print(f"  Skills en diccionario: {len(diccionario['busqueda_rapida'])}")

    # Inicializar mapping EN→ES para normalización de nombres
    global _SKILL_MAPPING
    _SKILL_MAPPING = construir_mapping_en_es(diccionario)
    print(f"  Mapping EN↔ES construido: {len(_SKILL_MAPPING)} entradas")

    print(f"\n[2/5] Cargando fuentes base (O*NET + Ocupacol) → año ancla 2019...")
    registros = cargar_skills_base(diccionario, anio_base)
    print(f"  Registros base: {len(registros)}")

    print(f"\n[3/5] Cargando CSVs de frecuencia (extract_skills.py)...")
    registros += cargar_skills_csv_frecuencia(anio_base)

    print(f"\n[4/5] Cargando JSONs de reportes PDF (load_pdf_report.py)...")
    registros += cargar_skills_pdf(anio_base)

    print(f"\n  Total de registros consolidados: {len(registros):,}")

    print(f"\n[5/5] Calculando tendencias...")
    historial   = consolidar_historial(registros)
    tendencias  = construir_tendencias(historial, diccionario)
    guardar_tendencias(tendencias)


if __name__ == "__main__":
    main()
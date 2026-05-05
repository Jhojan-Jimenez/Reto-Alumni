"""
simulate_historical_data.py
Genera datos históricos simulados (2020–2024) para el Observatorio Laboral.

Produce exactamente los mismos formatos que extract_skills.py y load_pdf_report.py
para que build_tendencias.py los procese sin modificaciones.

Archivos generados en data/processed/:
  ─ CSVs de frecuencia (formato extract_skills.py):
      spe_2020_frecuencia_skills.csv
      spe_2021_frecuencia_skills.csv
      spe_2022_frecuencia_skills.csv
      spe_2023_frecuencia_skills.csv
      adzuna_gb_2022_frecuencia_skills.csv
      adzuna_gb_2023_frecuencia_skills.csv
      adzuna_us_2023_frecuencia_skills.csv
      adzuna_us_2024_frecuencia_skills.csv
      adzuna_br_2022_frecuencia_skills.csv
      adzuna_br_2023_frecuencia_skills.csv

  ─ JSONs de reportes PDF (formato load_pdf_report.py):
      pdf_skills_coursera_2022.json
      pdf_skills_coursera_2023.json
      pdf_skills_coursera_2024.json
      pdf_skills_wef_2023.json
      pdf_skills_wef_2024.json
      pdf_skills_mckinsey_2022.json
      pdf_skills_mckinsey_2023.json

Lógica de simulación:
  - Cada skill tiene un perfil de crecimiento: creciente, estable o decreciente.
  - Los valores base y tasas de cambio están calibrados por categoría y skill,
    tomando como referencia los rankings reales de Coursera Job Skills Report 2025,
    WEF Future of Jobs 2023 y tendencias del SPE Colombia.
  - Se añade ruido gaussiano para que los datos no sean perfectamente lineales.

Uso:
    python simulate_historical_data.py
    python simulate_historical_data.py --seed 99    # reproducible con otra semilla
    python simulate_historical_data.py --preview    # muestra resumen sin guardar
"""

import json
import argparse
import random
import math
from pathlib import Path
from datetime import datetime

PROCESSED = Path("data/processed")

# ─────────────────────────────────────────────────────────────────────────────
# PERFILES DE SKILLS
# Cada entry: (skill, categoria, base_2020, tasa_anual, tendencia_esperada)
#
# base_2020  = menciones en 2020 (año ancla)
# tasa_anual = factor multiplicativo por año (1.3 = +30% anual → creciente)
#              valores < 1 → decreciente
#              valores ≈ 1 → estable
# ─────────────────────────────────────────────────────────────────────────────

SKILL_PROFILES = [
    # ── SKILLS TÉCNICAS — tendencias basadas en datos reales de mercado ──────
    # Crecimiento fuerte (IA, datos, ciberseguridad)
    ("Python",                          "técnica",       80,  1.45, "creciente"),
    ("SQL",                             "técnica",       95,  1.25, "creciente"),
    ("Machine Learning",                "técnica",       45,  1.55, "creciente"),
    ("Power BI",                        "técnica",       30,  1.50, "creciente"),
    ("Tableau",                         "técnica",       28,  1.35, "creciente"),
    ("Microsoft Azure",                 "técnica",       22,  1.60, "creciente"),
    ("Amazon Web Services",             "técnica",       35,  1.50, "creciente"),
    ("Docker",                          "técnica",       18,  1.55, "creciente"),
    ("TensorFlow",                      "técnica",       15,  1.65, "creciente"),
    ("PyTorch",                         "técnica",        8,  1.80, "creciente"),
    ("Kubernetes",                      "técnica",       12,  1.60, "creciente"),
    ("Git",                             "técnica",       60,  1.20, "creciente"),
    ("Google Cloud",                    "técnica",       15,  1.55, "creciente"),
    ("Apache Spark",                    "técnica",       20,  1.35, "creciente"),
    ("Salesforce",                      "técnica",       40,  1.20, "creciente"),
    ("SAP",                             "técnica",       55,  1.08, "estable"),
    ("JavaScript",                      "técnica",       70,  1.15, "creciente"),
    ("React",                           "técnica",       25,  1.40, "creciente"),
    ("Microsoft Excel",                 "técnica",      120,  1.05, "estable"),
    ("Microsoft Office",                "técnica",      110,  0.95, "estable"),
    ("Java",                            "técnica",       75,  1.05, "estable"),
    ("C++",                             "técnica",       40,  0.90, "decreciente"),
    ("MATLAB",                          "técnica",       25,  0.88, "decreciente"),
    ("Hadoop",                          "técnica",       30,  0.80, "decreciente"),
    ("Oracle",                          "técnica",       45,  0.85, "decreciente"),
    ("R",                               "técnica",       35,  1.10, "estable"),

    # ── SKILLS BLANDAS — en español (para SPE) ───────────────────────────────
    ("pensamiento crítico",             "blanda",       150,  1.18, "creciente"),
    ("comunicación oral",               "blanda",       180,  1.10, "estable"),
    ("trabajo en equipo",               "blanda",       200,  1.08, "estable"),
    ("resolución de problemas complejos","blanda",      120,  1.22, "creciente"),
    ("gestión del tiempo",              "blanda",       130,  1.12, "creciente"),
    ("aprendizaje activo",              "blanda",        80,  1.30, "creciente"),
    ("negociación",                     "blanda",       100,  1.05, "estable"),
    ("liderazgo",                       "blanda",       140,  1.10, "estable"),
    ("adaptabilidad",                   "blanda",        90,  1.35, "creciente"),
    ("inteligencia emocional",          "blanda",        60,  1.40, "creciente"),
    ("comunicación escrita",            "blanda",       110,  1.08, "estable"),
    ("orientación al servicio",         "blanda",       160,  1.05, "estable"),
    ("persuasión",                      "blanda",        70,  1.05, "estable"),
    ("coordinación",                    "blanda",        85,  1.00, "estable"),
    ("instrucción y capacitación",      "blanda",        75,  0.95, "estable"),
    ("monitoreo y seguimiento",         "blanda",        65,  0.90, "decreciente"),
    ("redacción",                       "blanda",        90,  1.05, "estable"),
    ("matemáticas",                     "blanda",        80,  0.92, "decreciente"),
    ("análisis de sistemas",            "blanda",        55,  1.15, "creciente"),
    ("juicio y toma de decisiones",     "blanda",        85,  1.18, "creciente"),
    ("gestión de personal",             "blanda",        70,  1.08, "estable"),
    ("control de calidad",              "blanda",        60,  0.95, "estable"),

    # ── CONOCIMIENTOS Ocupacol ────────────────────────────────────────────────
    ("administración y gestión",        "conocimiento",  90,  1.12, "creciente"),
    ("economía y contabilidad",         "conocimiento",  80,  1.05, "estable"),
    ("ventas y marketing",              "conocimiento",  75,  1.15, "creciente"),
    ("servicio al cliente",             "conocimiento", 110,  1.08, "estable"),
    ("informática",                     "conocimiento",  85,  1.20, "creciente"),
    ("ingeniería y tecnología",         "conocimiento",  70,  1.25, "creciente"),
    ("derecho y gobierno",              "conocimiento",  50,  1.02, "estable"),
    ("educación y formación",           "conocimiento",  65,  1.10, "creciente"),
    ("medicina y odontología",          "conocimiento",  45,  1.05, "estable"),
    ("matemáticas aplicadas",           "conocimiento",  55,  1.08, "estable"),
    ("física",                          "conocimiento",  30,  0.92, "decreciente"),
    ("recursos humanos",                "conocimiento",  60,  1.15, "creciente"),
    ("producción y procesamiento",      "conocimiento",  40,  0.88, "decreciente"),
    ("seguridad pública",               "conocimiento",  35,  1.10, "estable"),

    # ── DESTREZAS Ocupacol ────────────────────────────────────────────────────
    ("comprensión lectora",             "destreza",     140,  1.05, "estable"),
    ("escucha activa",                  "destreza",     155,  1.08, "estable"),
    ("pensamiento crítico",             "destreza",     130,  1.18, "creciente"),
    ("aprendizaje activo",              "destreza",      90,  1.30, "creciente"),
    ("hablar en público",               "destreza",      80,  1.05, "estable"),
    ("escritura creativa",              "destreza",      45,  1.02, "estable"),
    ("percepción social",               "destreza",      60,  1.08, "estable"),
    ("manejo del tiempo",               "destreza",     100,  1.12, "creciente"),
    ("orientación al servicio",         "destreza",      95,  1.05, "estable"),
    ("resolución de problemas",         "destreza",     120,  1.20, "creciente"),
    ("toma de decisiones",              "destreza",      85,  1.15, "creciente"),
    ("trabajo en equipo",               "destreza",     130,  1.08, "estable"),
    ("liderazgo",                       "destreza",      75,  1.10, "estable"),
    ("negociación efectiva",            "destreza",      55,  1.05, "estable"),
]

# Skills en inglés para fuentes Adzuna/PDF (mismas skills, nombres en inglés)
SKILL_PROFILES_EN = [
    ("Python",                  "técnica",   80,  1.45, "creciente"),
    ("SQL",                     "técnica",   95,  1.25, "creciente"),
    ("Machine Learning",        "técnica",   45,  1.55, "creciente"),
    ("Power BI",                "técnica",   30,  1.50, "creciente"),
    ("Tableau",                 "técnica",   28,  1.35, "creciente"),
    ("Microsoft Azure",         "técnica",   22,  1.60, "creciente"),
    ("Amazon Web Services",     "técnica",   35,  1.50, "creciente"),
    ("Docker",                  "técnica",   18,  1.55, "creciente"),
    ("TensorFlow",              "técnica",   15,  1.65, "creciente"),
    ("PyTorch",                 "técnica",    8,  1.80, "creciente"),
    ("Kubernetes",              "técnica",   12,  1.60, "creciente"),
    ("Git",                     "técnica",   60,  1.20, "creciente"),
    ("JavaScript",              "técnica",   70,  1.15, "creciente"),
    ("React",                   "técnica",   25,  1.40, "creciente"),
    ("Java",                    "técnica",   75,  1.05, "estable"),
    ("C++",                     "técnica",   40,  0.90, "decreciente"),
    ("R",                       "técnica",   35,  1.10, "estable"),
    ("Critical Thinking",       "blanda",   150,  1.18, "creciente"),
    ("Active Listening",        "blanda",   180,  1.10, "estable"),
    ("Complex Problem Solving", "blanda",   120,  1.22, "creciente"),
    ("Time Management",         "blanda",   130,  1.12, "creciente"),
    ("Active Learning",         "blanda",    80,  1.30, "creciente"),
    ("Negotiation",             "blanda",   100,  1.05, "estable"),
    ("Coordination",            "blanda",    85,  1.00, "estable"),
    ("Writing",                 "blanda",    90,  1.05, "estable"),
    ("Speaking",                "blanda",   110,  1.08, "estable"),
    ("Monitoring",              "blanda",    65,  0.90, "decreciente"),
    ("Programming",             "blanda",    55,  1.25, "creciente"),
    ("Systems Analysis",        "blanda",    55,  1.15, "creciente"),
    ("Judgment and Decision Making", "blanda", 85, 1.18, "creciente"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Motor de simulación
# ─────────────────────────────────────────────────────────────────────────────

def simular_menciones(base: int, tasa: float, anio: int, anio_base: int = 2020,
                      ruido_pct: float = 0.12, rng: random.Random = None) -> int:
    """
    Calcula menciones simuladas para un año dado.
    Modelo: menciones = base * tasa^(anio - anio_base) * (1 + ruido gaussiano)
    """
    if rng is None:
        rng = random.Random()
    años_transcurridos = anio - anio_base
    valor_base = base * (tasa ** años_transcurridos)
    # Ruido gaussiano suavizado (no puede ser negativo)
    ruido = rng.gauss(0, ruido_pct)
    valor_final = max(1, round(valor_base * (1 + ruido)))
    return valor_final


def generar_freq_csv(
    perfiles: list,
    anio: int,
    n_ofertas: int,
    rng: random.Random,
) -> list[dict]:
    """
    Genera filas equivalentes a las de *_frecuencia_skills.csv.
    """
    filas = []
    for skill, categoria, base, tasa, _ in perfiles:
        menciones = simular_menciones(base, tasa, anio, rng=rng)
        pct = round(menciones / n_ofertas * 100, 1)
        filas.append({
            "skill":             skill,
            "menciones":         menciones,
            "porcentaje_ofertas": pct,
            "categoria":         categoria,
        })
    # Ordenar por menciones descendente (igual que Counter.most_common)
    return sorted(filas, key=lambda x: -x["menciones"])


def generar_pdf_json(
    perfiles: list,
    fuente: str,
    anio: int,
    paginas: int,
    rng: random.Random,
) -> dict:
    """
    Genera un JSON equivalente al de pdf_skills_<fuente>_<anio>.json.
    """
    skills_dict = {}
    por_categoria: dict[str, list] = {
        "blandas": [], "tecnicas": [], "conocimientos": [], "destrezas": []
    }
    cat_map = {
        "técnica": "tecnicas",
        "blanda": "blandas",
        "conocimiento": "conocimientos",
        "destreza": "destrezas",
    }

    for skill, categoria, base, tasa, _ in perfiles:
        menciones = simular_menciones(base, tasa, anio, rng=rng)
        skills_dict[skill] = menciones
        por_categoria[cat_map.get(categoria, "destrezas")].append(skill)

    return {
        "meta": {
            "fuente":              fuente,
            "anio":                anio,
            "archivo_origen":      f"simulado_{fuente.lower()}_{anio}.pdf",
            "metodo_extraccion":   "simulado",
            "paginas":             paginas,
            "idioma_detectado":    "en",
            "metadatos_nativos_pdf": {},
            "fecha_procesamiento": datetime.now().isoformat(),
            "total_skills":        len(skills_dict),
            "simulado":            True,
        },
        "skills":        dict(sorted(skills_dict.items(), key=lambda x: -x[1])),
        "por_categoria": por_categoria,
        "skills_lista":  sorted(skills_dict.keys()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Definición de archivos a generar
# ─────────────────────────────────────────────────────────────────────────────

def get_plan_generacion() -> list[dict]:
    """
    Define exactamente qué archivos se van a generar y con qué parámetros.
    Los años y fuentes están pensados para dar 4-5 puntos temporales
    por skill, suficientes para calcular tendencias significativas.
    """
    return [
        # ── CSVs SPE Colombia (español, 2020-2023) ────────────────────────────
        {"tipo": "csv", "fuente": "spe",     "anio": 2020, "n_ofertas": 8500,  "perfiles": SKILL_PROFILES},
        {"tipo": "csv", "fuente": "spe",     "anio": 2021, "n_ofertas": 9200,  "perfiles": SKILL_PROFILES},
        {"tipo": "csv", "fuente": "spe",     "anio": 2022, "n_ofertas": 11000, "perfiles": SKILL_PROFILES},
        {"tipo": "csv", "fuente": "spe",     "anio": 2023, "n_ofertas": 13500, "perfiles": SKILL_PROFILES},

        # ── CSVs Adzuna GB (inglés, 2022-2023) ───────────────────────────────
        {"tipo": "csv", "fuente": "adzuna_gb", "anio": 2022, "n_ofertas": 6000, "perfiles": SKILL_PROFILES_EN},
        {"tipo": "csv", "fuente": "adzuna_gb", "anio": 2023, "n_ofertas": 7200, "perfiles": SKILL_PROFILES_EN},

        # ── CSVs Adzuna US (inglés, 2023-2024) ───────────────────────────────
        {"tipo": "csv", "fuente": "adzuna_us", "anio": 2023, "n_ofertas": 8000, "perfiles": SKILL_PROFILES_EN},
        {"tipo": "csv", "fuente": "adzuna_us", "anio": 2024, "n_ofertas": 9500, "perfiles": SKILL_PROFILES_EN},

        # ── CSVs Adzuna BR (inglés, 2022-2023) ───────────────────────────────
        {"tipo": "csv", "fuente": "adzuna_br", "anio": 2022, "n_ofertas": 3000, "perfiles": SKILL_PROFILES_EN},
        {"tipo": "csv", "fuente": "adzuna_br", "anio": 2023, "n_ofertas": 4100, "perfiles": SKILL_PROFILES_EN},

        # ── JSONs PDF Coursera (inglés, 2022-2024) ────────────────────────────
        {"tipo": "pdf", "fuente": "Coursera", "anio": 2022, "paginas": 32, "perfiles": SKILL_PROFILES_EN},
        {"tipo": "pdf", "fuente": "Coursera", "anio": 2023, "paginas": 35, "perfiles": SKILL_PROFILES_EN},
        {"tipo": "pdf", "fuente": "Coursera", "anio": 2024, "paginas": 38, "perfiles": SKILL_PROFILES_EN},

        # ── JSONs PDF WEF (inglés, 2023-2024) ────────────────────────────────
        {"tipo": "pdf", "fuente": "WEF",      "anio": 2023, "paginas": 80, "perfiles": SKILL_PROFILES_EN},
        {"tipo": "pdf", "fuente": "WEF",      "anio": 2024, "paginas": 85, "perfiles": SKILL_PROFILES_EN},

        # ── JSONs PDF McKinsey (inglés, 2022-2023) ────────────────────────────
        {"tipo": "pdf", "fuente": "McKinsey", "anio": 2022, "paginas": 55, "perfiles": SKILL_PROFILES_EN},
        {"tipo": "pdf", "fuente": "McKinsey", "anio": 2023, "paginas": 60, "perfiles": SKILL_PROFILES_EN},
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Ejecución principal
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera datos históricos simulados para el Observatorio Laboral."
    )
    parser.add_argument("--seed",    type=int, default=42,
                        help="Semilla aleatoria para reproducibilidad (default: 42)")
    parser.add_argument("--preview", action="store_true",
                        help="Muestra resumen de lo que se generaría sin guardar archivos")
    return parser.parse_args()


def main():
    args = parse_args()
    rng  = random.Random(args.seed)

    plan = get_plan_generacion()

    print(f"\n{'='*60}")
    print(f"  GENERADOR DE DATOS HISTÓRICOS SIMULADOS")
    print(f"  Semilla: {args.seed} | Archivos a generar: {len(plan)}")
    print(f"{'='*60}\n")

    if args.preview:
        print("  MODO PREVIEW — no se guardan archivos\n")
        for item in plan:
            if item["tipo"] == "csv":
                nombre = f"{item['fuente']}_{item['anio']}_frecuencia_skills.csv"
                print(f"  📊 CSV  {nombre:<55} ({len(item['perfiles'])} skills, {item['n_ofertas']:,} ofertas base)")
            else:
                nombre = f"pdf_skills_{item['fuente'].lower()}_{item['anio']}.json"
                print(f"  📄 JSON {nombre:<55} ({len(item['perfiles'])} skills, {item['paginas']} págs)")
        print(f"\n  Total: {len(plan)} archivos")
        print(f"  Rango temporal cubierto: 2020–2024")
        return

    if not args.preview:
        PROCESSED.mkdir(parents=True, exist_ok=True)

    stats = {"csv": 0, "pdf": 0, "skills_total": 0}

    for item in plan:
        # Instancia un RNG derivado para este archivo (reproducible pero distinto por archivo)
        seed_local = rng.randint(0, 999999)
        rng_local  = random.Random(seed_local)

        if item["tipo"] == "csv":
            nombre   = f"{item['fuente']}_{item['anio']}_frecuencia_skills.csv"
            ruta     = PROCESSED / nombre
            filas    = generar_freq_csv(item["perfiles"], item["anio"], item["n_ofertas"], rng_local)

            # Escribir CSV manualmente para no depender de pandas en este script
            with open(ruta, "w", encoding="utf-8-sig") as f:
                f.write("skill,menciones,porcentaje_ofertas,categoria\n")
                for fila in filas:
                    skill_esc = fila["skill"].replace('"', '""')
                    f.write(f'"{skill_esc}",{fila["menciones"]},{fila["porcentaje_ofertas"]},{fila["categoria"]}\n')

            stats["csv"] += 1
            stats["skills_total"] += len(filas)
            print(f"  ✓ CSV  {nombre:<55} ({len(filas)} skills)")

        else:  # pdf
            nombre = f"pdf_skills_{item['fuente'].lower()}_{item['anio']}.json"
            ruta   = PROCESSED / nombre
            datos  = generar_pdf_json(item["perfiles"], item["fuente"], item["anio"], item["paginas"], rng_local)

            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)

            stats["pdf"] += 1
            stats["skills_total"] += datos["meta"]["total_skills"]
            print(f"  ✓ JSON {nombre:<55} ({datos['meta']['total_skills']} skills)")

    print(f"""
{'='*60}
  ✓ SIMULACIÓN COMPLETADA
{'='*60}
  CSVs generados  : {stats['csv']}
  JSONs generados : {stats['pdf']}
  Registros total : {stats['skills_total']:,}
  Rango temporal  : 2020 – 2024

  Tendencias que deberías ver al correr build_tendencias.py:
    📈 Crecientes  → Python, ML, Azure, Docker, PyTorch, pensamiento crítico,
                     aprendizaje activo, resolución de problemas complejos
    ➡  Estables    → SQL, Excel, Java, comunicación oral, negociación
    📉 Decrecientes → C++, MATLAB, Hadoop, Oracle, matemáticas

  Siguiente paso:
    python build_tendencias.py

  El dashboard mostrará automáticamente la evolución 2020–2025
  (2025 = datos reales de Adzuna + PDF Coursera actual).
{'='*60}
""")


if __name__ == "__main__":
    main()
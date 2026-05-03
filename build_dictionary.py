"""
build_dictionary.py
Construye el diccionario de skills bilingüe (ES/EN) para el Observatorio Laboral.

Fuentes:
  - O*NET Skills.xlsx          → soft skills (EN → traducción manual ES)
  - O*NET Technology Skills.xlsx → tech tools filtradas a Hot Technology
  - Ocupacol (web)             → conocimientos y destrezas en español por ocupación
"""

import json
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path

ONET_DIR   = Path("data/ONET")
OUTPUT     = Path("data/processed/diccionario_skills.json")
HEADERS    = {"User-Agent": "Mozilla/5.0 (Academic - Universidad de La Sabana)"}


def _dedup_normalizado(terminos: list[str]) -> list[str]:
    """Elimina duplicados que difieren solo en capitalización o tildes.
    Conserva la forma con mayúscula/acento original (la primera encontrada)."""
    import unicodedata
    vistos = {}
    for t in terminos:
        clave = unicodedata.normalize("NFD", t.lower())
        clave = "".join(c for c in clave if unicodedata.category(c) != "Mn")
        if clave not in vistos:
            vistos[clave] = t
    return sorted(vistos.values())

# ─────────────────────────────────────────────────────────────────────────────
# 1. SOFT SKILLS: O*NET (EN) con traducción manual al español
# ─────────────────────────────────────────────────────────────────────────────
SOFT_SKILLS = {
    "Reading Comprehension":            "comprensión lectora",
    "Active Listening":                 "escucha activa",
    "Writing":                          "redacción",
    "Speaking":                         "comunicación oral",
    "Mathematics":                      "matemáticas",
    "Science":                          "ciencias",
    "Critical Thinking":                "pensamiento crítico",
    "Active Learning":                  "aprendizaje activo",
    "Learning Strategies":              "estrategias de aprendizaje",
    "Monitoring":                       "monitoreo y seguimiento",
    "Social Perceptiveness":            "percepción social",
    "Coordination":                     "coordinación",
    "Persuasion":                       "persuasión",
    "Negotiation":                      "negociación",
    "Instructing":                      "instrucción y capacitación",
    "Service Orientation":              "orientación al servicio",
    "Complex Problem Solving":          "resolución de problemas complejos",
    "Operations Analysis":              "análisis de operaciones",
    "Technology Design":                "diseño tecnológico",
    "Equipment Selection":              "selección de equipos",
    "Installation":                     "instalación",
    "Programming":                      "programación",
    "Operations Monitoring":            "monitoreo de operaciones",
    "Operation and Control":            "operación y control de sistemas",
    "Equipment Maintenance":            "mantenimiento de equipos",
    "Troubleshooting":                  "diagnóstico y resolución de fallas",
    "Repairing":                        "reparación",
    "Quality Control Analysis":         "control de calidad",
    "Judgment and Decision Making":     "juicio y toma de decisiones",
    "Systems Analysis":                 "análisis de sistemas",
    "Systems Evaluation":               "evaluación de sistemas",
    "Time Management":                  "gestión del tiempo",
    "Management of Financial Resources":"gestión de recursos financieros",
    "Management of Material Resources": "gestión de recursos materiales",
    "Management of Personnel Resources":"gestión de personal",
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. TECH SKILLS: O*NET Technology Skills filtradas a Hot Technology = Y
# ─────────────────────────────────────────────────────────────────────────────
def get_tech_skills() -> list[str]:
    df = pd.read_excel(ONET_DIR / "Technology Skills.xlsx")
    hot = df[df["Hot Technology"] == "Y"]["Example"].dropna().unique().tolist()
    return sorted(hot)

# ─────────────────────────────────────────────────────────────────────────────
# 3. OCUPACOL: buscar ocupaciones y scrapear sus perfiles
# ─────────────────────────────────────────────────────────────────────────────

# Ocupaciones representativas de los programas de La Sabana
OCCUPATION_KEYWORDS = [
    "abogado", "psicólogo", "administrador", "ingeniero de sistemas",
    "ingeniero industrial", "contador", "comunicador", "médico",
    "enfermero", "economista", "diseñador", "trabajador social",
    "nutricionista", "fisioterapeuta", "arquitecto", "docente",
    "analista de datos", "desarrollador", "gerente de proyectos",
    "auditor", "financiero", "marketing", "recursos humanos"
]

def search_ocupacol(keyword: str) -> list[int]:
    """Busca una ocupación y retorna los IDs de perfil encontrados."""
    url = "https://ocupacol.mintrabajo.gov.co/Searches/AdvancedSearch"
    try:
        r = requests.get(url, params={"Keyword": keyword},
                         headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        ids = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/Profile/OccupationalProfile/" in href:
                try:
                    ids.append(int(href.split("/")[-1]))
                except ValueError:
                    pass
        return list(set(ids))
    except Exception as e:
        print(f"  [!] Error buscando '{keyword}': {e}")
        return []

def scrape_profile(occupation_id: int) -> dict:
    """Scrapea conocimientos y destrezas de un perfil de Ocupacol."""
    url = f"https://ocupacol.mintrabajo.gov.co/Profile/OccupationalProfile/{occupation_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        conocimientos, destrezas = [], []

        for card in soup.find_all("div", class_="card"):
            header = card.find("span", class_="card-header")
            if not header:
                continue

            section = header.get_text(strip=True)
            badges = card.find_all("span", class_="badge-primary")
            items = [b.get_text(strip=True) for b in badges if b.get_text(strip=True)]

            if "Conocimiento" in section:
                conocimientos = items
            elif "Destreza" in section:
                destrezas = items

        return {"conocimientos": conocimientos, "destrezas": destrezas}
    except Exception as e:
        print(f"  [!] Error en perfil {occupation_id}: {e}")
        return {}

def get_ocupacol_skills() -> dict:
    """Recopila skills de Ocupacol para todas las ocupaciones objetivo."""
    all_conocimientos = set()
    all_destrezas     = set()
    scraped_ids       = set()

    for keyword in OCCUPATION_KEYWORDS:
        print(f"  Buscando: {keyword}")
        ids = search_ocupacol(keyword)

        for oid in ids[:3]:  # máximo 3 perfiles por keyword
            if oid in scraped_ids:
                continue
            scraped_ids.add(oid)
            result = scrape_profile(oid)
            all_conocimientos.update(result.get("conocimientos", []))
            all_destrezas.update(result.get("destrezas", []))
            time.sleep(1)  # pausa para no saturar el servidor

    print(f"  Perfiles scrapeados: {len(scraped_ids)}")
    return {
        "conocimientos": sorted(all_conocimientos),
        "destrezas":     sorted(all_destrezas),
    }

# ─────────────────────────────────────────────────────────────────────────────
# 4. CONSTRUCCIÓN DEL DICCIONARIO FINAL
# ─────────────────────────────────────────────────────────────────────────────
def build_dictionary():
    print("\n[1/3] Cargando tech skills de O*NET...")
    tech_skills = get_tech_skills()
    print(f"  Tech skills (Hot Technology): {len(tech_skills)}")

    print("\n[2/3] Scrapeando perfiles de Ocupacol...")
    ocupacol = get_ocupacol_skills()
    print(f"  Conocimientos únicos: {len(ocupacol['conocimientos'])}")
    print(f"  Destrezas únicas:     {len(ocupacol['destrezas'])}")

    print("\n[3/3] Construyendo diccionario final...")

    diccionario = {
        # Skills blandas: búsqueda en español, referencia en inglés
        "blandas": {
            "terminos_es": sorted(SOFT_SKILLS.values()),
            "mapping_en":  {v: k for k, v in SOFT_SKILLS.items()},
        },
        # Tech tools: mismas en ES y EN (Python = Python)
        "tecnicas": {
            "terminos": tech_skills,
        },
        # Conocimientos y destrezas validados por MinTrabajo Colombia
        "ocupacol": {
            "conocimientos": ocupacol["conocimientos"],
            "destrezas":     ocupacol["destrezas"],
        },
        # Lista plana para búsqueda rápida — deduplicada por forma normalizada
        # (evita que "Programación" y "programación" cuenten como dos términos)
        "busqueda_rapida": _dedup_normalizado(
            list(SOFT_SKILLS.values()) +
            tech_skills +
            ocupacol["conocimientos"] +
            ocupacol["destrezas"]
        ),
        "meta": {
            "total_soft_skills":    len(SOFT_SKILLS),
            "total_tech_skills":    len(tech_skills),
            "total_conocimientos":  len(ocupacol["conocimientos"]),
            "total_destrezas":      len(ocupacol["destrezas"]),
            "total_busqueda_rapida": 0,  # se actualiza abajo
        }
    }

    diccionario["meta"]["total_busqueda_rapida"] = len(diccionario["busqueda_rapida"])

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(diccionario, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Diccionario guardado en: {OUTPUT}")
    print(f"  Total términos de búsqueda: {diccionario['meta']['total_busqueda_rapida']}")
    print(f"  ├── Soft skills (ES):  {diccionario['meta']['total_soft_skills']}")
    print(f"  ├── Tech skills:       {diccionario['meta']['total_tech_skills']}")
    print(f"  ├── Conocimientos:     {diccionario['meta']['total_conocimientos']}")
    print(f"  └── Destrezas:         {diccionario['meta']['total_destrezas']}")

if __name__ == "__main__":
    build_dictionary()

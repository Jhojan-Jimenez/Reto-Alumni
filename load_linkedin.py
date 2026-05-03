"""
load_linkedin.py
Descarga el dataset de LinkedIn desde Kaggle, selecciona columnas relevantes,
toma una muestra y guarda un CSV listo para extract_skills.py.

Uso:
    python3 load_linkedin.py [muestra]

    muestra: número de filas a tomar (default: 5000)

Nota sobre idioma:
    Las descripciones de LinkedIn están en inglés. Por eso extract_skills.py
    se corre con --idioma en, que usa los nombres originales de O*NET en inglés
    en vez de las traducciones al español.
    Las herramientas técnicas (Python, SQL, Power BI...) son iguales en ambos idiomas.
"""

import sys
import json
import warnings
import pandas as pd
import kagglehub
from kagglehub import KaggleDatasetAdapter
from pathlib import Path

warnings.filterwarnings("ignore")

SALIDA      = Path("data/processed/linkedin_sample.csv")
MUESTRA     = int(sys.argv[1]) if len(sys.argv) > 1 else 5000

COLUMNAS = {
    "job_id":                    "id_oferta",
    "title":                     "titulo",
    "description":               "descripcion",
    "company_name":              "empresa",
    "location":                  "ubicacion",
    "formatted_work_type":       "modalidad",
    "formatted_experience_level":"nivel_experiencia",
    "remote_allowed":            "remoto",
    "min_salary":                "salario_min",
    "max_salary":                "salario_max",
    "normalized_salary":         "salario_normalizado",
    "currency":                  "moneda",
}


def cargar_linkedin(muestra: int) -> pd.DataFrame:
    print(f"[1/3] Cargando dataset LinkedIn desde Kaggle (muestra={muestra:,})...")
    df = kagglehub.load_dataset(
        KaggleDatasetAdapter.PANDAS,
        "arshkon/linkedin-job-postings",
        "postings.csv",
        pandas_kwargs={"usecols": list(COLUMNAS.keys()), "nrows": muestra * 3}
    )

    # Filtrar filas con descripción vacía
    df = df.dropna(subset=["description"])
    df = df[df["description"].str.strip().str.len() > 100]

    # Tomar muestra aleatoria reproducible
    df = df.sample(n=min(muestra, len(df)), random_state=42).reset_index(drop=True)

    # Renombrar columnas a español para consistencia con el resto del sistema
    df = df.rename(columns=COLUMNAS)

    print(f"  Filas cargadas: {len(df):,}")
    print(f"  Columnas: {list(df.columns)}")
    return df


def guardar(df: pd.DataFrame):
    print(f"\n[2/3] Guardando en {SALIDA}...")
    df.to_csv(SALIDA, index=False, encoding="utf-8-sig")
    print(f"  ✓ Guardado: {SALIDA} ({SALIDA.stat().st_size / 1024:.0f} KB)")


def instrucciones():
    print(f"""
[3/3] Listo. Próximo paso:

  El dataset de LinkedIn está en inglés, así que usa el modo inglés
  del extractor para que los soft skills también hagan match:

    python3 extract_skills.py linkedin_sample.csv descripcion id_oferta --idioma en

  Con --idioma en se usan los nombres originales de O*NET en inglés:
    "Critical Thinking", "Negotiation", "Time Management"...
  más todas las herramientas técnicas (Python, SQL, etc.) que son iguales.

  Comparación de cobertura:
    SPE (español)    → soft skills ES + tech tools  → perfil mercado colombiano
    LinkedIn (inglés)→ soft skills EN + tech tools  → benchmark internacional
""")


if __name__ == "__main__":
    df = cargar_linkedin(MUESTRA)
    guardar(df)
    instrucciones()

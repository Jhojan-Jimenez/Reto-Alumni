"""
load_geih_salarios.py
Procesa el GEIH (Gran Encuesta Integrada de Hogares) del DANE
para extraer salarios en COP por ocupación y nivel educativo.

Uso:
    python3 load_geih_salarios.py --geih_dir data/raw/GEIH --salida data/processed/geih_salarios.json

El script busca automáticamente los módulos del GEIH:
  - Ocupados.csv / Ocupados.dta   → INGLABO (ingreso laboral), RAMA2D_R4 (sector)
  - Caracteristicas_generales.csv → P6210 (nivel educativo)

Si el archivo es un ZIP (como Febrero_2026.zip), extrae automáticamente.

Salida JSON:
{
  "meta": {"periodo": "Feb 2026", "n_ocupados": 12345, "fuente": "GEIH DANE"},
  "por_nucleo": {
    "Ciencias Económicas": {"mediana": 2800000, "p25": 1800000, "p75": 4200000, "n": 342},
    ...
  },
  "por_sector": {
    "Actividades financieras": {"mediana": 3500000, ...},
    ...
  },
  "por_nivel_educativo": {
    "Universitario": {"mediana": 3100000, ...},
    ...
  },
  "spe_rangos": [
    {"rango": "$1.500.001 - $2.000.000", "participacion": 54.6, "variacion": 193.5},
    ...
  ]
}
"""

import argparse
import json
import zipfile
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Mapeo de códigos CIIU → sectores legibles
# ─────────────────────────────────────────────────────────────────────────────
CIIU_SECTORES = {
    "A": "Agricultura, ganadería y pesca",
    "B": "Explotación de minas y canteras",
    "C": "Industrias manufactureras",
    "D": "Suministro de electricidad y gas",
    "E": "Suministro de agua y gestión de desechos",
    "F": "Construcción",
    "G": "Comercio y reparación de vehículos",
    "H": "Transporte y almacenamiento",
    "I": "Alojamiento y servicios de comida",
    "J": "Información y comunicaciones",
    "K": "Actividades financieras y de seguros",
    "L": "Actividades inmobiliarias",
    "M": "Actividades profesionales y científicas",
    "N": "Actividades de servicios administrativos",
    "O": "Administración pública y defensa",
    "P": "Educación",
    "Q": "Atención de la salud humana",
    "R": "Actividades artísticas y recreativas",
    "S": "Otras actividades de servicios",
    "T": "Actividades de los hogares",
}

# Mapeo nivel educativo GEIH (P6210) → etiqueta
NIVEL_EDU = {
    1: "Ninguno",
    2: "Preescolar",
    3: "Primaria",
    4: "Secundaria",
    5: "Técnico/Tecnológico",
    6: "Universitario",
    7: "Especialización",
    8: "Maestría",
    9: "Doctorado",
}

# Mapeo NBC (Núcleo Básico del Conocimiento) GEIH → etiqueta
# La variable en GEIH suele ser INGLABO con cruce por P6220 (título obtenido)
NBC_MAP = {
    "Administración": "Ciencias Económicas",
    "Economía": "Ciencias Económicas",
    "Contaduría": "Ciencias Económicas",
    "Ingeniería": "Ingenierías y afines",
    "Sistemas": "Ingenierías y afines",
    "Medicina": "Ciencias de la salud",
    "Enfermería": "Ciencias de la salud",
    "Derecho": "Ciencias sociales y humanas",
    "Psicología": "Ciencias sociales y humanas",
    "Educación": "Ciencias de la educación",
    "Licenciatura": "Ciencias de la educación",
}

# ─────────────────────────────────────────────────────────────────────────────
# Rangos SPE (datos reales del boletín Feb 2026 — Tabla 7)
# ─────────────────────────────────────────────────────────────────────────────
SPE_RANGOS_FIJOS = [
    {"rango": "Hasta $1.000.000",          "min_cop": 0,         "max_cop": 1_000_000,   "participacion": 1.1,  "variacion": -49.6},
    {"rango": "$1.000.001 – $1.500.000",   "min_cop": 1_000_001, "max_cop": 1_500_000,   "participacion": 4.6,  "variacion": -91.2},
    {"rango": "$1.500.001 – $2.000.000",   "min_cop": 1_500_001, "max_cop": 2_000_000,   "participacion": 54.6, "variacion": 193.5},
    {"rango": "$2.000.001 – $3.000.000",   "min_cop": 2_000_001, "max_cop": 3_000_000,   "participacion": 12.4, "variacion": 9.0},
    {"rango": "$3.000.001 – $4.000.000",   "min_cop": 3_000_001, "max_cop": 4_000_000,   "participacion": 4.2,  "variacion": 64.3},
    {"rango": "Más de $4.000.000",         "min_cop": 4_000_001, "max_cop": 99_000_000,  "participacion": 1.9,  "variacion": 18.6},
    {"rango": "A convenir",                "min_cop": None,      "max_cop": None,         "participacion": 21.2, "variacion": -34.8},
]

# Tasa de cambio USD→COP de referencia (actualizar periódicamente)
TRM_USD_COP = 4_150  # aprox Mayo 2026


def _estadisticas(serie: pd.Series) -> dict:
    """Calcula estadísticas salariales básicas en COP."""
    s = serie.dropna()
    s = s[(s > 500_000) & (s < 50_000_000)]  # filtrar outliers
    if len(s) < 5:
        return None
    return {
        "mediana":  int(s.median()),
        "media":    int(s.mean()),
        "p25":      int(s.quantile(0.25)),
        "p75":      int(s.quantile(0.75)),
        "p10":      int(s.quantile(0.10)),
        "p90":      int(s.quantile(0.90)),
        "n":        int(len(s)),
        "min":      int(s.min()),
        "max":      int(s.max()),
    }


def _buscar_archivo(directorio: Path, patrones: list[str]) -> Path | None:
    """Busca un archivo por patrones de nombre (case-insensitive)."""
    for patron in patrones:
        hits = list(directorio.rglob(f"*{patron}*"))
        hits = [h for h in hits if h.is_file() and h.suffix.lower() in (".csv", ".dta", ".xlsx")]
        if hits:
            return hits[0]
    return None


def _leer_modulo(ruta: Path) -> pd.DataFrame | None:
    """Lee un módulo GEIH desde CSV, DTA o XLSX."""
    try:
        sufijo = ruta.suffix.lower()
        if sufijo == ".csv":
            for enc in ["latin-1", "utf-8", "utf-8-sig", "cp1252"]:
                try:
                    df = pd.read_csv(ruta, encoding=enc, low_memory=False, sep=None, engine="python")
                    return df
                except Exception:
                    continue
        elif sufijo == ".dta":
            return pd.read_stata(ruta)
        elif sufijo in (".xlsx", ".xls"):
            return pd.read_excel(ruta)
    except Exception as e:
        print(f"  ⚠ Error leyendo {ruta.name}: {e}")
    return None


def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nombres de columnas a mayúsculas sin espacios."""
    df.columns = [str(c).strip().upper().replace(" ", "_") for c in df.columns]
    return df


def procesar_geih(geih_dir: Path, periodo: str = "Feb 2026") -> dict:
    """
    Procesa el directorio GEIH y retorna el JSON de salarios.
    Soporta ZIP o carpeta con CSVs.
    """
    tmp_dir = None

    # Si es un ZIP, extraer a temporal
    if geih_dir.suffix.lower() == ".zip":
        tmp_dir = Path(tempfile.mkdtemp())
        print(f"  📦 Extrayendo ZIP en {tmp_dir}...")
        with zipfile.ZipFile(geih_dir, "r") as z:
            z.extractall(tmp_dir)
        geih_dir = tmp_dir

    print(f"  🔍 Buscando módulos en: {geih_dir}")

    # ── Buscar módulo Ocupados ─────────────────────────────────────────────
    df_ocup = None
    ocup_path = _buscar_archivo(geih_dir, ["Ocupados", "ocupados", "OCUPADOS"])
    if ocup_path:
        print(f"  ✓ Módulo Ocupados: {ocup_path.name}")
        df_ocup = _leer_modulo(ocup_path)
        if df_ocup is not None:
            df_ocup = _normalizar_columnas(df_ocup)
    else:
        print("  ⚠ No se encontró módulo Ocupados — usando datos SPE únicamente")

    # ── Buscar módulo Características generales ────────────────────────────
    df_caract = None
    caract_path = _buscar_archivo(
        geih_dir, ["Caracteristicas_generales", "caracteristicas", "CARACTERISTICAS"]
    )
    if caract_path:
        print(f"  ✓ Módulo Características: {caract_path.name}")
        df_caract = _leer_modulo(caract_path)
        if df_caract is not None:
            df_caract = _normalizar_columnas(df_caract)

    # ── Construir resultado ────────────────────────────────────────────────
    resultado = {
        "meta": {
            "periodo":   periodo,
            "fuente":    "GEIH DANE + SPE Colombia",
            "n_ocupados": 0,
            "con_ingreso": 0,
            "trm_usd_cop": TRM_USD_COP,
            "nota": "Salarios en COP (pesos colombianos). Fuente: DANE GEIH.",
        },
        "por_nivel_educativo": {},
        "por_sector": {},
        "por_nucleo": {},
        "spe_rangos": SPE_RANGOS_FIJOS,
        "tiene_geih": False,
    }

    if df_ocup is not None:
        # Detectar columna de ingreso laboral
        col_ingreso = None
        for candidato in ["INGLABO", "INGRESO_LABORAL", "INGTOTAL", "INGLABO_R"]:
            if candidato in df_ocup.columns:
                col_ingreso = candidato
                break

        if col_ingreso is None:
            # Buscar columnas que contengan "ING"
            ing_cols = [c for c in df_ocup.columns if "ING" in c]
            if ing_cols:
                col_ingreso = ing_cols[0]
                print(f"  ℹ Usando columna de ingreso alternativa: {col_ingreso}")

        if col_ingreso:
            df_ocup[col_ingreso] = pd.to_numeric(df_ocup[col_ingreso], errors="coerce")
            df_con_ingreso = df_ocup[df_ocup[col_ingreso] > 0].copy()

            resultado["meta"]["n_ocupados"] = int(len(df_ocup))
            resultado["meta"]["con_ingreso"] = int(len(df_con_ingreso))
            resultado["tiene_geih"] = True

            print(f"  📊 Ocupados: {len(df_ocup):,} | Con ingreso: {len(df_con_ingreso):,}")

            # ── Por nivel educativo ────────────────────────────────────────
            col_edu = None
            for c in ["P6210", "NIVEL_EDUCATIVO", "EDUC", "P3271"]:
                if c in df_ocup.columns:
                    col_edu = c
                    break

            if col_edu:
                df_con_ingreso["_nivel"] = (
                    pd.to_numeric(df_con_ingreso[col_edu], errors="coerce")
                    .map(NIVEL_EDU)
                )
                for nivel, grp in df_con_ingreso.groupby("_nivel"):
                    if pd.notna(nivel):
                        stats = _estadisticas(grp[col_ingreso])
                        if stats:
                            resultado["por_nivel_educativo"][str(nivel)] = stats

            # ── Por sector (RAMA2D_R4 o similar) ──────────────────────────
            col_rama = None
            for c in ["RAMA2D_R4", "RAMA_R4", "RAMA2D", "CLASE"]:
                if c in df_ocup.columns:
                    col_rama = c
                    break

            if col_rama:
                df_con_ingreso["_sector"] = df_con_ingreso[col_rama].astype(str).str.strip().str.upper().str[0]
                df_con_ingreso["_sector_nombre"] = df_con_ingreso["_sector"].map(CIIU_SECTORES)
                for sector, grp in df_con_ingreso[df_con_ingreso["_sector_nombre"].notna()].groupby("_sector_nombre"):
                    stats = _estadisticas(grp[col_ingreso])
                    if stats:
                        resultado["por_sector"][str(sector)] = stats

            # ── Por núcleo básico de conocimiento ──────────────────────────
            # Si hay módulo de características, hacer join para obtener carrera
            if df_caract is not None:
                col_id = None
                for c in ["DIRECTORIO", "SECUENCIA_P", "ORDEN", "ID_HOGAR"]:
                    if c in df_ocup.columns and c in df_caract.columns:
                        col_id = c
                        break

                col_titulo = None
                for c in ["P6220", "CARRERA", "TITULO", "P3042"]:
                    if c in df_caract.columns:
                        col_titulo = c
                        break

                if col_id and col_titulo:
                    df_merged = df_con_ingreso.merge(
                        df_caract[[col_id, col_titulo]], on=col_id, how="left"
                    )
                    df_merged["_nbc"] = (
                        df_merged[col_titulo]
                        .astype(str)
                        .apply(lambda x: next(
                            (v for k, v in NBC_MAP.items() if k.lower() in x.lower()), None
                        ))
                    )
                    for nbc, grp in df_merged[df_merged["_nbc"].notna()].groupby("_nbc"):
                        stats = _estadisticas(grp[col_ingreso])
                        if stats:
                            resultado["por_nucleo"][str(nbc)] = stats
        else:
            print("  ⚠ No se encontró columna de ingreso laboral en el módulo Ocupados")
    
    # Limpiar temporal
    if tmp_dir:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return resultado


def main():
    parser = argparse.ArgumentParser(description="Procesa GEIH para extraer salarios en COP")
    parser.add_argument("--geih_dir", default="data/raw/GEIH",
                        help="Ruta al directorio o ZIP del GEIH (default: data/raw/GEIH)")
    parser.add_argument("--salida", default="data/processed/geih_salarios.json",
                        help="Ruta de salida JSON (default: data/processed/geih_salarios.json)")
    parser.add_argument("--periodo", default="Feb 2026",
                        help="Etiqueta del período (ej: 'Feb 2026')")
    args = parser.parse_args()

    geih_path = Path(args.geih_dir)
    salida    = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*55}")
    print("  PROCESADOR GEIH — Observatorio Laboral UniSabana")
    print(f"{'='*55}")

    if not geih_path.exists():
        print(f"\n  ⚠ No se encontró: {geih_path}")
        print("  → Generando archivo con datos SPE únicamente...")
        resultado = {
            "meta": {
                "periodo":    args.periodo,
                "fuente":     "SPE Colombia (GEIH no disponible)",
                "n_ocupados": 0,
                "con_ingreso": 0,
                "trm_usd_cop": TRM_USD_COP,
                "nota": "Carga el GEIH en data/raw/GEIH/ para salarios reales del DANE.",
            },
            "por_nivel_educativo": {},
            "por_sector": {},
            "por_nucleo": {},
            "spe_rangos": SPE_RANGOS_FIJOS,
            "tiene_geih": False,
        }
    else:
        resultado = procesar_geih(geih_path, periodo=args.periodo)

    with open(salida, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"\n  ✅ Guardado en: {salida}")
    print(f"  • Sectores: {len(resultado['por_sector'])}")
    print(f"  • Niveles educativos: {len(resultado['por_nivel_educativo'])}")
    print(f"  • Núcleos NBC: {len(resultado['por_nucleo'])}")
    print(f"  • Rangos SPE: {len(resultado['spe_rangos'])}")


if __name__ == "__main__":
    main()

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
# CNO-2015 (Clasificación Nacional de Ocupaciones) — grupos y subgrupos
# Variable GEIH: OFICIO (código CNO 1–4 dígitos)
# ─────────────────────────────────────────────────────────────────────────────
CNO_GRUPOS = {
    "0": "Ocupaciones militares",
    "1": "Directivos y gerentes",
    "2": "Profesionales científicos e intelectuales",
    "3": "Técnicos y profesionales de nivel medio",
    "4": "Personal de apoyo administrativo",
    "5": "Trabajadores de servicios y vendedores",
    "6": "Agricultores y trabajadores agropecuarios calificados",
    "7": "Oficiales, operarios y artesanos",
    "8": "Operadores de instalaciones y máquinas",
    "9": "Ocupaciones elementales",
}

CNO_SUBGRUPOS = {
    "11": "Directivos generales y gerentes de grandes empresas",
    "12": "Gerentes de áreas funcionales especializadas",
    "13": "Gerentes de pequeñas empresas",
    "14": "Gerentes y directivos del sector público",
    "21": "Especialistas en ciencias físicas, matemáticas, ingeniería y TIC",
    "22": "Especialistas en ciencias de la salud",
    "23": "Especialistas en enseñanza",
    "24": "Especialistas en administración de empresas y economía",
    "25": "Especialistas en TIC",
    "26": "Especialistas en derecho, ciencias sociales y culturales",
    "31": "Técnicos en ciencias físicas e ingeniería",
    "32": "Técnicos en salud",
    "33": "Técnicos y profesionales en finanzas y administración",
    "34": "Técnicos en asuntos jurídicos, sociales y culturales",
    "35": "Técnicos en TIC",
    "41": "Secretarios y auxiliares de oficina",
    "42": "Empleados en atención al cliente",
    "43": "Empleados en contabilidad y finanzas",
    "44": "Empleados de información al cliente",
    "51": "Personal de los servicios personales",
    "52": "Vendedores",
    "53": "Cuidadores personales y trabajadores de salud",
    "54": "Trabajadores de protección y seguridad",
    "61": "Agricultores y trabajadores agropecuarios calificados",
    "62": "Trabajadores forestales calificados y pescadores",
    "71": "Oficiales y operarios de la construcción",
    "72": "Oficiales de metalurgia y construcción mecánica",
    "73": "Artesanos y operarios en imprenta y artes",
    "74": "Electricistas e instaladores de redes",
    "75": "Trabajadores de procesamiento de alimentos y afines",
    "81": "Operadores de instalaciones mineras y procesamiento",
    "82": "Operadores de maquinaria",
    "83": "Conductores y operadores de transporte",
    "91": "Trabajadores domésticos y limpiadores",
    "92": "Trabajadores agrícolas de subsistencia",
    "93": "Trabajadores de servicios básicos y callejeros",
    "94": "Vendedores ambulantes",
    "95": "Recolectores de desechos y afines",
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
    """
    Busca archivos por patrones (case-insensitive).
    Cubre nombres del DANE: 'Cabecera - Ocupados.csv', 'Area_Ocupados_Feb26.csv', etc.
    Prefiere el archivo más grande cuando hay múltiples coincidencias.
    """
    ext_validas = {".csv", ".dta", ".xlsx", ".xls"}
    todos = [f for f in directorio.rglob("*")
             if f.is_file() and f.suffix.lower() in ext_validas]
    for patron in patrones:
        hits = [f for f in todos if patron.lower() in f.name.lower()]
        if hits:
            hits.sort(key=lambda f: -f.stat().st_size)
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
    ocup_path = _buscar_archivo(geih_dir, [
        "Ocupados", "ocupados", "OCUPADOS", "Ocup", "ocup", "Empleo",
    ])
    if ocup_path:
        print(f"  ✓ Módulo Ocupados: {ocup_path.name}")
        df_ocup = _leer_modulo(ocup_path)
        if df_ocup is not None:
            df_ocup = _normalizar_columnas(df_ocup)
    else:
        ext_validas = {".csv", ".dta", ".xlsx", ".xls"}
        disponibles = [f.name for f in geih_dir.rglob("*")
                       if f.is_file() and f.suffix.lower() in ext_validas]
        print("  ⚠ No se encontró módulo Ocupados.")
        if disponibles:
            print("  ℹ Archivos disponibles en el ZIP/carpeta:")
            for n in sorted(disponibles):
                print(f"     • {n}")
        print("  → Usando datos SPE únicamente")

    caract_path = _buscar_archivo(geih_dir, [
        "Caracteristicas_generales", "Características_generales",
        "caracteristicas", "Caracter", "General", "Hogares",
    ])
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
        "por_ocupacion": {},
        "por_ocupacion_detalle": {},
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

            # ── Por ocupación CNO (OFICIO) ─────────────────────────────────
            col_oficio = None
            for c in ["OFICIO", "P6430", "P6435", "COD_OCUP", "OCUPACION"]:
                if c in df_ocup.columns:
                    col_oficio = c
                    break
            # Fallback: buscar cualquier columna con "OFIC" u "OCUP"
            if col_oficio is None:
                for c in df_ocup.columns:
                    if "OFIC" in c or ("OCUP" in c and c != col_rama):
                        col_oficio = c
                        break

            if col_oficio:
                print(f"  ✓ Columna de ocupación CNO: {col_oficio}")
                # Normalizar: convertir a string y extraer dígitos
                df_con_ingreso["_cno_raw"] = (
                    df_con_ingreso[col_oficio]
                    .astype(str).str.strip().str.extract(r"(\d+)")[0]
                )
                # Grupo principal (1 dígito)
                df_con_ingreso["_cno_grupo"] = df_con_ingreso["_cno_raw"].str[:1]
                df_con_ingreso["_cno_grupo_nombre"] = df_con_ingreso["_cno_grupo"].map(CNO_GRUPOS)
                for grupo, grp in df_con_ingreso[df_con_ingreso["_cno_grupo_nombre"].notna()].groupby("_cno_grupo_nombre"):
                    stats = _estadisticas(grp[col_ingreso])
                    if stats:
                        resultado["por_ocupacion"][str(grupo)] = stats

                # Subgrupo (2 dígitos) — mayor detalle
                df_con_ingreso["_cno_sub"] = df_con_ingreso["_cno_raw"].str[:2]
                df_con_ingreso["_cno_sub_nombre"] = df_con_ingreso["_cno_sub"].map(CNO_SUBGRUPOS)
                for subgrupo, grp in df_con_ingreso[df_con_ingreso["_cno_sub_nombre"].notna()].groupby("_cno_sub_nombre"):
                    stats = _estadisticas(grp[col_ingreso])
                    if stats:
                        resultado["por_ocupacion_detalle"][str(subgrupo)] = stats

                print(f"  📋 Grupos CNO: {len(resultado['por_ocupacion'])} | Subgrupos: {len(resultado['por_ocupacion_detalle'])}")
            else:
                print("  ⚠ No se encontró columna de ocupación CNO (OFICIO/P6430). Se omite por_ocupacion.")

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
    parser = argparse.ArgumentParser(
        description="Procesa GEIH para extraer salarios en COP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python load_geih_salarios.py --geih_dir "data/raw/GEIH/Febrero_2026.zip"
  python load_geih_salarios.py --geih_dir "data/raw/GEIH/Febrero_2026.zip" --listar
  python load_geih_salarios.py --geih_dir "data/raw/GEIH" --periodo "Feb 2026"
        """
    )
    parser.add_argument("--geih_dir",  default="data/raw/GEIH",
                        help="Ruta al ZIP o carpeta del GEIH (default: data/raw/GEIH)")
    parser.add_argument("--salida",    default="data/processed/geih_salarios.json")
    parser.add_argument("--periodo",   default="Feb 2026")
    parser.add_argument("--listar",    action="store_true",
                        help="Solo lista archivos dentro del ZIP/carpeta sin procesar")
    args = parser.parse_args()

    geih_path = Path(args.geih_dir)
    salida    = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*55}")
    print("  PROCESADOR GEIH — Observatorio Laboral UniSabana")
    print(f"{'='*55}")
    print(f"  Ruta: {geih_path}")

    # ── Modo --listar ──────────────────────────────────────────────────────
    if args.listar:
        if not geih_path.exists():
            print(f"\n  ⚠  No existe: {geih_path}")
            return
        if geih_path.suffix.lower() == ".zip":
            print(f"\n  📦 Contenido de '{geih_path.name}':")
            with zipfile.ZipFile(geih_path) as z:
                for name in sorted(z.namelist()):
                    if not name.endswith("/"):
                        kb = z.getinfo(name).file_size / 1024
                        print(f"    {name:<65} {kb:>8.1f} KB")
        else:
            ext = {".csv", ".dta", ".xlsx", ".xls"}
            archivos = [f for f in geih_path.rglob("*") if f.is_file() and f.suffix.lower() in ext]
            print(f"\n  📁 Archivos en '{geih_path}':")
            for f in sorted(archivos):
                kb = f.stat().st_size / 1024
                print(f"    {str(f.relative_to(geih_path)):<65} {kb:>8.1f} KB")
        return

    # ── Ruta no encontrada ─────────────────────────────────────────────────
    if not geih_path.exists():
        print(f"\n  ⚠  No se encontró: {geih_path}")
        print("""
  Pasa la ruta correcta con --geih_dir, por ejemplo:
    python load_geih_salarios.py --geih_dir "data/raw/GEIH/Febrero_2026.zip"
    python load_geih_salarios.py --geih_dir "data/raw/GEIH/Febrero_2026.zip" --listar
        """)
        resultado = {
            "meta": {
                "periodo": args.periodo, "fuente": "SPE Colombia (GEIH no disponible)",
                "n_ocupados": 0, "con_ingreso": 0, "trm_usd_cop": TRM_USD_COP,
                "nota": "Pasa la ruta al ZIP con --geih_dir.",
            },
            "por_nivel_educativo": {}, "por_sector": {}, "por_nucleo": {},
            "por_ocupacion": {}, "por_ocupacion_detalle": {},
            "spe_rangos": SPE_RANGOS_FIJOS, "tiene_geih": False,
        }
    else:
        resultado = procesar_geih(geih_path, periodo=args.periodo)

    with open(salida, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    tiene = resultado.get("tiene_geih", False)
    print(f"\n  ✅ Guardado en: {salida}")
    print(f"  • Tiene GEIH real     : {'Sí' if tiene else 'No — solo SPE'}")
    print(f"  • Sectores            : {len(resultado['por_sector'])}")
    print(f"  • Niveles educativos  : {len(resultado['por_nivel_educativo'])}")
    print(f"  • Núcleos NBC         : {len(resultado['por_nucleo'])}")
    print(f"  • Grupos CNO          : {len(resultado['por_ocupacion'])}")
    print(f"  • Subgrupos CNO       : {len(resultado['por_ocupacion_detalle'])}")
    print(f"  • Rangos SPE          : {len(resultado['spe_rangos'])}")
    if tiene:
        m = resultado["meta"]
        print(f"  • Ocupados totales    : {m.get('n_ocupados', 0):,}")
        print(f"  • Con ingreso laboral : {m.get('con_ingreso', 0):,}")


if __name__ == "__main__":
    main()
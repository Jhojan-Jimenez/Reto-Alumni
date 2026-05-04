"""
load_adzuna.py
Descarga ofertas laborales desde la API de Adzuna, normaliza las columnas
al mismo formato del sistema y guarda un CSV listo para extract_skills.py.

Uso:
    python3 load_adzuna.py [opciones]

Opciones:
    --pais      Código de país (default: co — Colombia)
                Otros: gb, us, au, de, fr, ca, br, in, nl, nz, pl, ru, sg, za
    --query     Término de búsqueda (default: vacío → todas las ofertas)
    --muestra   Número de ofertas a recolectar (default: 5000)
    --salida    Ruta del CSV de salida (default: data/processed/adzuna_sample.csv)

Ejemplos:
    python3 load_adzuna.py
    python3 load_adzuna.py --pais gb --query "data scientist" --muestra 2000
    python3 load_adzuna.py --pais us --query "software engineer" --muestra 3000

Variables de entorno requeridas (o editar directamente las constantes abajo):
    ADZUNA_APP_ID
    ADZUNA_APP_KEY

Nota sobre idioma:
    Para países de habla inglesa (gb, us, au…) usa --idioma en en extract_skills.
    Para Colombia (co) usa --idioma es (default).

    Ejemplo completo:
        python3 load_adzuna.py --pais gb --muestra 3000
        python3 extract_skills.py adzuna_sample.csv descripcion id_oferta --idioma en
"""

import os
import sys
import time
import argparse
import warnings
import requests
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# Configuración — edita aquí o usa variables de entorno
# ─────────────────────────────────────────────────────────────────────────────

APP_ID  = os.environ.get("ADZUNA_APP_ID",  "aa178fc6")
APP_KEY = os.environ.get("ADZUNA_APP_KEY", "abba0bd969a03f00b96926ceef86152a")

BASE_URL          = "https://api.adzuna.com/v1/api/jobs"
RESULTS_POR_PAGINA = 50          # Máximo permitido por Adzuna
PAUSA_ENTRE_LLAMADAS = 1.0       # Segundos entre requests (evita rate limit)

PROCESSED         = Path("data/processed")
SALIDA_DEFAULT    = PROCESSED / "adzuna_sample.csv"
 
# Países soportados oficialmente por Adzuna (CO no está disponible)
# https://developer.adzuna.com/overview
PAISES_SOPORTADOS = {
    "gb", "us", "au", "ca", "de", "fr", "in",
    "nl", "nz", "pl", "ru", "sg", "za", "br", "at", "be",
}
 
# Países de habla inglesa (para sugerir --idioma en)
PAISES_EN = {"gb", "us", "au", "ca", "nz", "sg", "in", "za"}
 
# Columnas que extrae la API de Adzuna → nombre interno del sistema
COLUMNAS_MAPEADAS = {
    "id":                   "id_oferta",
    "title":                "titulo",
    "description":          "descripcion",
    "company.display_name": "empresa",
    "location.display_name":"ubicacion",
    "contract_type":        "modalidad",
    "category.label":       "categoria",
    "salary_min":           "salario_min",
    "salary_max":           "salario_max",
    "redirect_url":         "url_oferta",
    "created":              "fecha_publicacion",
}
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Llamada a la API
# ─────────────────────────────────────────────────────────────────────────────
 
def _extraer_campo(objeto: dict, ruta: str):
    """
    Extrae un campo anidado usando notación de punto.
    Ej: "company.display_name" → objeto["company"]["display_name"]
    """
    partes = ruta.split(".")
    valor = objeto
    for parte in partes:
        if isinstance(valor, dict):
            valor = valor.get(parte)
        else:
            return None
    return valor
 
 
def fetch_pagina(pais: str, query: str, pagina: int) -> dict:
    """Llama a la API de Adzuna y retorna el JSON de una página."""
    url = f"{BASE_URL}/{pais}/search/{pagina}"
 
    # content-type va en HEADERS, no en query params
    headers = {"Content-Type": "application/json"}
 
    params = {
        "app_id":           APP_ID,
        "app_key":          APP_KEY,
        "results_per_page": RESULTS_POR_PAGINA,
    }
    if query.strip():
        params["what"] = query.strip()
 
    response = requests.get(url, params=params, headers=headers, timeout=20)
    response.raise_for_status()
    return response.json()
 
 
def normalizar_oferta(oferta: dict) -> dict:
    """Convierte un objeto JSON de Adzuna al formato interno del sistema."""
    fila = {}
    for campo_api, nombre_interno in COLUMNAS_MAPEADAS.items():
        fila[nombre_interno] = _extraer_campo(oferta, campo_api)
    return fila
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Recolección paginada
# ─────────────────────────────────────────────────────────────────────────────
 
def cargar_adzuna(pais: str, query: str, muestra: int) -> pd.DataFrame:
    """
    Itera páginas de la API hasta alcanzar `muestra` ofertas válidas
    (con descripción no vacía).
    """
    print(f"\n[1/3] Conectando a Adzuna API...")
    print(f"  País   : {pais.upper()}")
    print(f"  Query  : '{query}' (vacío = todas las categorías)")
    print(f"  Muestra: {muestra:,} ofertas objetivo")
 
    # Adzuna NO soporta Colombia (co) ni la mayoría de países latinoamericanos.
    # Validar antes de hacer la llamada para dar un error claro.
    if pais not in PAISES_SOPORTADOS:
        print(f"\n  ⚠  El país '{pais}' no está soportado por Adzuna.")
        print(f"  Países disponibles: {', '.join(sorted(PAISES_SOPORTADOS))}")
        print(f"  Para datos del mercado colombiano usa el SPE (Servicio Público de Empleo).")
        print(f"  Sugerencia: usa --pais br (Brasil) o --pais gb (Reino Unido) como benchmark.\n")
        import sys; sys.exit(1)
 
    # Verificar credenciales con una primera llamada
    try:
        datos_iniciales = fetch_pagina(pais, query, pagina=1)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("\n  ERROR 401: Credenciales inválidas.")
            print("  Verifica APP_ID y APP_KEY en load_adzuna.py o como variables de entorno.")
        elif e.response.status_code == 400:
            print(f"\n  ERROR 400: Parámetros inválidos. ¿El código de país '{pais}' es correcto?")
        else:
            print(f"\n  ERROR HTTP {e.response.status_code}: {e}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("\n  ERROR: No se pudo conectar a api.adzuna.com. Verifica tu conexión.")
        sys.exit(1)
 
    total_disponible = datos_iniciales.get("count", 0)
    total_a_recolectar = min(muestra, total_disponible)
    paginas_necesarias = -(-total_a_recolectar // RESULTS_POR_PAGINA)  # Ceil division
 
    print(f"  Ofertas disponibles en Adzuna : {total_disponible:,}")
    print(f"  Ofertas a recolectar          : {total_a_recolectar:,}")
    print(f"  Páginas a consultar           : {paginas_necesarias}")
 
    # Primera página ya la tenemos
    todas_las_ofertas = [
        normalizar_oferta(o) for o in datos_iniciales.get("results", [])
    ]
 
    for pagina in range(2, paginas_necesarias + 1):
        if len(todas_las_ofertas) >= muestra:
            break
 
        print(f"  Descargando página {pagina}/{paginas_necesarias}...", end="\r")
 
        try:
            datos = fetch_pagina(pais, query, pagina=pagina)
            resultados = datos.get("results", [])
            if not resultados:
                print(f"\n  No hay más resultados en página {pagina}. Finalizando.")
                break
            todas_las_ofertas.extend([normalizar_oferta(o) for o in resultados])
        except requests.exceptions.RequestException as e:
            print(f"\n  [!] Error en página {pagina}: {e}. Reintentando en 5s...")
            time.sleep(5)
            continue
 
        time.sleep(PAUSA_ENTRE_LLAMADAS)
 
    print(f"\n  Ofertas brutas descargadas: {len(todas_las_ofertas):,}")
 
    # Construir DataFrame y limpiar
    df = pd.DataFrame(todas_las_ofertas)
 
    # Filtrar descripciones vacías o muy cortas
    df = df.dropna(subset=["descripcion"])
    df = df[df["descripcion"].str.strip().str.len() > 100]
    df = df.drop_duplicates(subset=["id_oferta"])
 
    # Recortar a la muestra pedida
    df = df.head(muestra).reset_index(drop=True)
 
    # Añadir metadatos de la fuente
    df["fuente"]  = "adzuna"
    df["pais"]    = pais.upper()
    df["idioma"]  = "en" if pais in PAISES_EN else "es"
 
    print(f"  Ofertas limpias finales      : {len(df):,}")
    return df
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Guardar y mostrar instrucciones
# ─────────────────────────────────────────────────────────────────────────────
 
def guardar(df: pd.DataFrame, ruta: Path):
    print(f"\n[2/3] Guardando CSV en {ruta}...")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    size_kb = ruta.stat().st_size / 1024
    print(f"  ✓ Guardado: {ruta} ({size_kb:.0f} KB)")
    print(f"  Columnas: {list(df.columns)}")
 
 
def instrucciones(pais: str, ruta: Path):
    idioma = "en" if pais in PAISES_EN else "es"
    nombre = ruta.name
 
    print(f"""
[3/3] Listo. Próximo paso — extrae las skills:
 
  python3 extract_skills.py {nombre} descripcion id_oferta --idioma {idioma}
 
  {'⚠  País de habla inglesa → se usa --idioma en (soft skills en inglés de O*NET)'
   if idioma == 'en'
   else '✓  País hispanohablante → se usa --idioma es (soft skills en español)'}
 
  ⚠  NOTA: Adzuna no cubre Colombia (co). Para datos del mercado colombiano
     usa el Servicio Público de Empleo (SPE) directamente con extract_skills.py.
 
  Países soportados por Adzuna:
    gb (UK), us (EE.UU.), au (Australia), ca (Canadá),
    de (Alemania), fr (Francia), br (Brasil), in (India),
    nl (Países Bajos), nz (Nueva Zelanda), pl (Polonia),
    ru (Rusia), sg (Singapur), za (Sudáfrica), at (Austria), be (Bélgica)
""")
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Argparse y entrada principal
# ─────────────────────────────────────────────────────────────────────────────
 
def parse_args():
    parser = argparse.ArgumentParser(
        description="Descarga ofertas de Adzuna al formato del Observatorio Laboral.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Ejemplos:
  python load_adzuna.py                          # UK, 5000 ofertas
  python load_adzuna.py --pais us --muestra 3000
  python load_adzuna.py --paises gb us br        # los tres a la vez (comparación global)
  python load_adzuna.py --paises gb us br --muestra 2000  # 2000 por cada país
        """
    )
    parser.add_argument("--pais",    default="gb",
                        help="Código de país (default: gb)\nPaíses: gb us au ca de fr br in nl nz pl sg za at be")
    parser.add_argument("--paises",  nargs="+", metavar="PAIS",
                        help="Varios países a descargar en secuencia, ej: --paises gb us br\n(sobreescribe --pais)")
    parser.add_argument("--query",   default="",
                        help="Término de búsqueda (default: vacío = todas las categorías)")
    parser.add_argument("--muestra", default=3000, type=int,
                        help="Número de ofertas por país (default: 2000)")
    parser.add_argument("--salida",  default=None,
                        help="Ruta CSV de salida (solo aplica con --pais individual)")
    return parser.parse_args()
 
 
def procesar_un_pais(pais: str, query: str, muestra: int, salida_override: str | None) -> Path:
    """Descarga y guarda ofertas de un país. Retorna la ruta del CSV generado."""
    nombre_salida = salida_override or str(
        PROCESSED / f"adzuna_{pais}_{muestra}.csv"
    )
    salida = Path(nombre_salida)
    df = cargar_adzuna(pais=pais, query=query, muestra=muestra)
    guardar(df, salida)
    instrucciones(pais, salida)
    return salida
 
 
if __name__ == "__main__":
    args = parse_args()
 
    if APP_ID == "TU_APP_ID_AQUI" or APP_KEY == "TU_APP_KEY_AQUI":
        print("\n⚠  ATENCIÓN: No has configurado tus credenciales de Adzuna.")
        print("   Edita las constantes APP_ID y APP_KEY en load_adzuna.py")
        print("   o expórtalas como variables de entorno:")
        print("     set ADZUNA_APP_ID=tu_id      (Windows)")
        print("     export ADZUNA_APP_ID='tu_id' (Mac/Linux)")
        print("   Regístrate gratis en: https://developer.adzuna.com/\n")
        sys.exit(1)
 
    # ── Modo multi-país ──────────────────────────────────────────────────────
    lista_paises = args.paises if args.paises else [args.pais]
 
    if len(lista_paises) > 1:
        print(f"\n{'='*55}")
        print(f"  MODO COMPARACIÓN GLOBAL — {len(lista_paises)} países")
        print(f"  Países : {', '.join(p.upper() for p in lista_paises)}")
        print(f"  Muestra: {args.muestra:,} ofertas por país")
        print(f"{'='*55}")
 
        rutas_generadas = []
        for i, pais in enumerate(lista_paises, 1):
            print(f"\n[País {i}/{len(lista_paises)}] ── {pais.upper()} {'─'*30}")
            ruta = procesar_un_pais(pais, args.query, args.muestra, salida_override=None)
            rutas_generadas.append((pais, ruta))
 
        print(f"\n{'='*55}")
        print("  ✓ Descarga multi-país completada")
        print(f"{'='*55}")
        print("\n  Archivos generados:")
        for pais, ruta in rutas_generadas:
            idioma = "en" if pais in PAISES_EN else "es"
            print(f"    {pais.upper()}: {ruta}")
            print(f"         → python extract_skills.py {ruta.name} descripcion id_oferta --idioma {idioma}")
 
        print(f"""
  Para análisis de tendencias comparativo, ejecuta extract_skills
  en cada archivo y luego consolida con build_tendencias.py:
 
    python build_tendencias.py
 
  Esto cruzará automáticamente las {len(lista_paises)} fuentes de Adzuna
  con O*NET, Ocupacol y PDFs para calcular tendencias globales.
""")
 
    else:
        # ── Modo país único ──────────────────────────────────────────────────
        procesar_un_pais(lista_paises[0], args.query, args.muestra, args.salida)
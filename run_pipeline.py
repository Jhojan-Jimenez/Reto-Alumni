# run_pipeline.py

import subprocess
import sys
from pathlib import Path

PYTHON = sys.executable

def run(cmd):
    print(f"\n Ejecutando: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Error en: {cmd}")
        sys.exit(1)

def main():
    print("\n INICIANDO PIPELINE COMPLETO\n")

    # 1. Diccionario
    run(f"{PYTHON} build_dictionary.py")

    # 2. Datos históricos simulados (2020-2024)
    #    Genera CSVs y JSONs con el mismo formato que las fuentes reales.
    #    Omitir este paso si ya tienes datos reales históricos suficientes.
    run(f"{PYTHON} simulate_historical_data.py")

    # 3. Adzuna (datos reales 2025 — tres países para comparación global)
    run(f"{PYTHON} Load_adzuna.py --paises gb us br --muestra 1000")
    run(f"{PYTHON} extract_skills.py data/processed/adzuna_gb_1000.csv descripcion id_oferta --idioma en")
    run(f"{PYTHON} extract_skills.py data/processed/adzuna_us_1000.csv descripcion id_oferta --idioma en")
    run(f"{PYTHON} extract_skills.py data/processed/adzuna_br_1000.csv descripcion id_oferta --idioma en")

    # 4. LinkedIn
    run(f"{PYTHON} load_linkedin.py")
    run(f"{PYTHON} extract_skills.py data/processed/linkedin_sample.csv descripcion id_oferta --idioma en")

    # 5. SPE → si tienes archivo local
    spe_file = Path("data/raw/spe.csv")
    if spe_file.exists():
        run(f"{PYTHON} extract_skills.py {spe_file} DESCRIPCION_VACANTE")

    # 6. PDFs: procesar individualmente con:
    #    python load_pdf_reports.py "archivo.pdf" --fuente Coursera --anio 2025 --idioma en

    # 7. Construir tendencias (integra simulados + reales automáticamente)
    run(f"{PYTHON} build_tendencias.py")

    print("\nPIPELINE FINALIZADO\n")

if __name__ == "__main__":
    main()
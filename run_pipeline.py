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

    # 2. Adzuna
    run(f"{PYTHON} Load_adzuna.py")
    run(f"{PYTHON} extract_skills.py data/processed/adzuna_sample.csv descripcion id_oferta")

    # 3. LinkedIn
    run(f"{PYTHON} load_linkedin.py")
    run(f"{PYTHON} extract_skills.py data/processed/linkedin_sample.csv descripcion id_oferta --idioma en")

    # 4. (Opcional) SPE → si tienes archivo local
    spe_file = Path("data/raw/spe.csv")
    if spe_file.exists():
        run(f"{PYTHON} extract_skills.py {spe_file} DESCRIPCION_VACANTE")

    # 5. PDFs: se procesan individualmente desde el dashboard o con:
    #    python load_pdf_reports.py "archivo.pdf" --fuente WEF --anio 2024 --idioma en
    #    Una vez procesados, build_tendencias los integra automáticamente.

    # 6. Construir tendencias
    run(f"{PYTHON} build_tendencias.py")

    print("\nPIPELINE FINALIZADO\n")

if __name__ == "__main__":
    main()
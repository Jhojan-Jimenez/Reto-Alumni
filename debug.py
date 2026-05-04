from pathlib import Path

p = Path("data/processed/skills_tendencias.json")

print("EXISTE:", p.exists())
print("RUTA ABSOLUTA:", p.resolve())
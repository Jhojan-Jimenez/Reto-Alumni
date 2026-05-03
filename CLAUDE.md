# Observatorio Laboral – Universidad de La Sabana

Dashboard interactivo de análisis del mercado laboral para la Dirección de Alumni.

## Estructura del proyecto

```
.
├── dashboard.py          # App principal Streamlit (punto de entrada)
├── build_dictionary.py   # Construye el diccionario de skills (O*NET + Ocupacol)
├── extract_skills.py     # Extrae skills de cualquier CSV/Excel por columna
├── load_linkedin.py      # Descarga y prepara el dataset de LinkedIn (Kaggle)
├── requirements.txt
│
├── data/
│   ├── ONET/             # Fuente de taxonomía O*NET (27.3) — no modificar
│   ├── raw/              # Datos crudos originales
│   │   ├── Servicio de Empleo.csv   # SPE Colombia (1000 vacantes)
│   │   ├── Ocupacol.csv             # Clasificación Nacional de Ocupaciones
│   │   └── Ole.xlsx                 # Observatorio Laboral para la Educación (MEN)
│   └── processed/        # Generados por los scripts — no subir a Git
│       ├── diccionario_skills.json
│       ├── Servicio de Empleo_con_skills.csv
│       ├── Servicio de Empleo_frecuencia_skills.csv
│       └── linkedin_sample*.csv
│
└── docs/
    ├── Reto.txt          # Enunciado original del reto
    ├── Ideacion.md       # Propuesta técnica completa
    └── Ideas.txt         # Ideas y referencias iniciales
```

## Cómo correr el dashboard

```bash
~/.local/bin/streamlit run dashboard.py
# Abre http://localhost:8501
```

## Cómo regenerar los datos procesados

```bash
# 1. Reconstruir el diccionario de skills (O*NET + Ocupacol web)
python3 build_dictionary.py

# 2. Extraer skills del SPE (español)
python3 extract_skills.py "data/raw/Servicio de Empleo.csv" DESCRIPCION_VACANTE CODIGO_VACANTE

# 3. Descargar y procesar LinkedIn (inglés)
python3 load_linkedin.py 5000
python3 extract_skills.py data/processed/linkedin_sample.csv descripcion id_oferta --idioma en
```

## Fuentes de datos

| Fuente | Tipo | Idioma | Actualización |
|---|---|---|---|
| O*NET 27.3 | Taxonomía de ocupaciones y skills | Inglés | Semestral |
| SPE Colombia | Vacantes reales del mercado colombiano | Español | Continua |
| Ocupacol (MinTrabajo) | Perfiles de ocupación colombianos | Español | Periódica |
| OLE (MEN) | Empleabilidad de graduados por carrera | Español | Anual |
| LinkedIn (Kaggle) | Dataset histórico de ofertas globales | Inglés | Dataset fijo |

## Stack tecnológico

- **Dashboard**: Streamlit + Plotly
- **Pipeline ETL**: Python (pandas, requests, BeautifulSoup)
- **Diccionario de skills**: O*NET (EN) + Ocupacol web (ES) + mapeo manual
- **Base de datos**: CSV/Excel (prototipo) → PostgreSQL (producción)

## Despliegue

**Local:**
```bash
pip install -r requirements.txt
~/.local/bin/streamlit run dashboard.py
```

**Streamlit Community Cloud:**
1. Subir repo a GitHub (sin `data/processed/` ni `.env`)
2. Conectar en share.streamlit.io → seleccionar `dashboard.py`
3. Los archivos `data/ONET/` y `data/raw/` deben estar en el repo

**VM propia:**
```bash
streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0
# Abrir puerto 8501 en el firewall
```

## Notas importantes

- `data/processed/` está en `.gitignore` — se regenera con los scripts
- El dataset de LinkedIn se descarga automáticamente vía `kagglehub` (requiere cuenta Kaggle)
- `build_dictionary.py` scrapea Ocupacol (~53 perfiles, ~1 min) — solo correr cuando se quiera actualizar el diccionario
- Los archivos O*NET son de uso académico — no redistribuir comercialmente

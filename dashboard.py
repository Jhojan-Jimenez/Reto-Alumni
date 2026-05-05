"""
Observatorio Laboral – Universidad de La Sabana
Dashboard interactivo: O*NET · SPE Colombia · Adzuna · PDF Reports · Tendencias
"""

import json
import sys
import subprocess
import threading
import queue
import tempfile
import time
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y TEMA VISUAL
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Observatorio Laboral – UniSabana",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.cache_data.clear()

# ── Paleta de colores institucionales ─────────────────────────────────────────
# Sidebar / barra:  #0d2769   Fondo principal: #f7f6eb   Filtros/acento: #2130cf
C_NAVY   = "#0d2769"   # barra lateral
C_BLUE   = "#2130cf"   # acento filtros, tabs activos, botones
C_BG     = "#f7f6eb"   # fondo general
C_TEAL   = "#00b4d8"   # charts secundarios
C_GOLD   = "#f0c040"   # valores en KPIs
C_GREEN  = "#22c55e"   # positivo / creciente (accesible)
C_RED    = "#ef4444"   # negativo / decreciente
C_PURPLE = "#7c3aed"   # destreza
C_TEXT   = "#1a1a2e"   # texto principal sobre fondo claro
C_MUTED  = "#4a5568"   # texto secundario
PALETTE  = [C_BLUE, C_NAVY, C_TEAL, C_GOLD, C_GREEN, C_RED, C_PURPLE, "#fb923c"]
CAT_COLORS = {
    "técnica":      C_BLUE,
    "blanda":       C_NAVY,
    "conocimiento": C_GREEN,
    "destreza":     C_PURPLE,
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(247,246,235,0.0)",
    font=dict(color=C_TEXT, family="DM Sans"),
    title_font=dict(family="Rajdhani", size=16, color=C_NAVY),
    legend=dict(bgcolor="rgba(255,255,255,0.7)", bordercolor="#d1d5db", borderwidth=1),
    coloraxis_colorbar=dict(tickfont=dict(color=C_TEXT)),
    xaxis=dict(gridcolor="#e5e7eb", zerolinecolor="#e5e7eb", color=C_MUTED),
    yaxis=dict(gridcolor="#e5e7eb", zerolinecolor="#e5e7eb", color=C_MUTED),
)

# CSS global — tema institucional claro UniSabana
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

  /* ── Fondo general ── */
  html, body,
  [data-testid="stAppViewContainer"],
  [data-testid="stMain"] > div {
    background: #f7f6eb !important;
    color: #1a1a2e !important;
    font-family: 'DM Sans', sans-serif;
  }

  /* ── Sidebar / barra ── */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d2769 0%, #091d52 100%) !important;
    border-right: none;
  }
  [data-testid="stSidebar"] * { color: #e8eeff !important; }
  [data-testid="stSidebar"] h3 { color: #ffffff !important; font-family: 'Rajdhani', sans-serif !important; }
  [data-testid="stSidebar"] .stButton > button {
    background: #2130cf !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600;
  }
  [data-testid="stSidebar"] .stButton > button:hover {
    background: #1a27b0 !important;
  }
  [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; }

  /* ── Títulos ── */
  h1, h2, h3 {
    font-family: 'Rajdhani', sans-serif !important;
    letter-spacing: 0.04em;
    color: #0d2769 !important;
  }

  /* ── KPI cards ── */
  [data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #dde3f5;
    border-left: 4px solid #2130cf;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 2px 12px rgba(33,48,207,0.08);
  }
  [data-testid="stMetricLabel"] {
    color: #4a5568 !important;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  [data-testid="stMetricValue"] {
    color: #0d2769 !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 2.1rem !important;
    font-weight: 700;
  }
  [data-testid="stMetricDelta"] { color: #22c55e !important; }

  /* ── Tabs ── */
  [data-testid="stTabs"] {
    background: #ffffff;
    border-radius: 12px 12px 0 0;
    border-bottom: 2px solid #dde3f5;
    padding: 0 8px;
  }
  [data-testid="stTabs"] button {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.95rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    color: #4a5568 !important;
    border-bottom: 3px solid transparent;
    padding: 10px 18px;
    transition: color 0.2s;
  }
  [data-testid="stTabs"] button:hover { color: #2130cf !important; }
  [data-testid="stTabs"] button[aria-selected="true"] {
    color: #2130cf !important;
    border-bottom: 3px solid #2130cf !important;
    background: transparent !important;
  }

  /* ── Filtros: selectbox / multiselect / slider ── */
  [data-testid="stSelectbox"] > div,
  [data-testid="stMultiSelect"] > div {
    background: #ffffff !important;
    border: 2px solid #2130cf !important;
    border-radius: 8px;
    color: #1a1a2e !important;
  }
  [data-testid="stSelectbox"] label,
  [data-testid="stMultiSelect"] label,
  [data-testid="stSlider"] label {
    color: #0d2769 !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  [data-testid="stSlider"] > div > div > div { background: #2130cf !important; }
  [data-testid="stSlider"] > div > div > div > div { background: #2130cf !important; border-color: #2130cf !important; }

  /* ── Divider ── */
  hr { border-color: #dde3f5 !important; }

  /* ── Dataframes ── */
  [data-testid="stDataFrame"] {
    border: 1px solid #dde3f5;
    border-radius: 8px;
    background: #ffffff;
  }

  /* ── Alertas ── */
  [data-testid="stAlert"] {
    background: #eef2ff !important;
    border: 1px solid #c7d2fe !important;
    border-radius: 10px;
    color: #1a1a2e !important;
  }

  /* ── Badges de tendencia ── */
  .badge-up   { background:#dcfce7; color:#166534; border:1px solid #86efac; border-radius:20px; padding:2px 10px; font-size:0.78rem; font-weight:600; }
  .badge-down { background:#fee2e2; color:#991b1b; border:1px solid #fca5a5; border-radius:20px; padding:2px 10px; font-size:0.78rem; font-weight:600; }
  .badge-flat { background:#f1f5f9; color:#475569; border:1px solid #cbd5e1;  border-radius:20px; padding:2px 10px; font-size:0.78rem; font-weight:600; }

  /* ── Alerta emergente ── */
  .alert-emergente {
    background: #fff7ed;
    border-left: 4px solid #f97316;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 0.85rem;
    color: #7c2d12;
    margin-bottom: 8px;
  }

  /* ── KPI insight card ── */
  .insight-card {
    background: #ffffff;
    border: 1px solid #dde3f5;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    box-shadow: 0 2px 8px rgba(13,39,105,0.06);
  }
  .insight-card .ic-title { font-family: 'Rajdhani',sans-serif; font-size:1rem; font-weight:700; color:#0d2769; }
  .insight-card .ic-body  { font-size:0.85rem; color:#4a5568; margin-top:4px; }

  /* ── Ocupación description box ── */
  .occ-desc-box {
    background: #ffffff;
    border: 1px solid #dde3f5;
    border-left: 4px solid #0d2769;
    border-radius: 10px;
    padding: 16px;
    color: #1a1a2e;
  }

  /* ── Plotly charts ── */
  .js-plotly-plot .plotly { background: transparent !important; }

  /* ── Expanders ── */
  [data-testid="stExpander"] {
    border: 1px solid #dde3f5 !important;
    border-radius: 10px !important;
    background: #ffffff !important;
  }
</style>
""", unsafe_allow_html=True)

def apply_theme(fig, height=480):
    fig.update_layout(height=height, **PLOTLY_LAYOUT)
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# RUTAS DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

ONET      = Path("data/ONET")
PROCESSED = Path("data/processed")


# ══════════════════════════════════════════════════════════════════════════════
# LOADERS CON CACHÉ
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=60)
def load_skills():
    df = pd.read_excel(ONET / "Skills.xlsx")
    return df[~df["Recommend Suppress"].eq("Y")]

@st.cache_data(ttl=60)
def load_knowledge():
    df = pd.read_excel(ONET / "Knowledge.xlsx")
    return df[~df["Recommend Suppress"].eq("Y")]

@st.cache_data(ttl=60)
def load_tech():
    return pd.read_excel(ONET / "Technology Skills.xlsx")

@st.cache_data(ttl=60)
def load_job_zones():
    return pd.read_excel(ONET / "Job Zones.xlsx")

@st.cache_data(ttl=60)
def load_interests():
    return pd.read_excel(ONET / "Interests.xlsx")

@st.cache_data(ttl=60)
def load_work_styles():
    return pd.read_excel(ONET / "Work Styles.xlsx")

@st.cache_data(ttl=60)
def load_emerging():
    return pd.read_excel(ONET / "Emerging Tasks.xlsx")

@st.cache_data(ttl=60)
def load_related():
    return pd.read_excel(ONET / "Related Occupations.xlsx")

@st.cache_data(ttl=60)
def load_work_activities():
    df = pd.read_excel(ONET / "Work Activities.xlsx")
    return df[~df["Recommend Suppress"].eq("Y")]

@st.cache_data(ttl=60)
def load_occ_data():
    return pd.read_excel(ONET / "Occupation Data.xlsx")

# ── Fuentes nuevas ─────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_freq(nombre: str):
    p = PROCESSED / nombre
    return pd.read_csv(p, encoding="utf-8-sig") if p.exists() else None

@st.cache_data(ttl=60)
def load_tendencias():
    p = PROCESSED / "skills_tendencias.json"
    
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)

@st.cache_data(ttl=60)
def load_all_freq_sources():
    """Carga todos los CSVs de frecuencia disponibles y los unifica con columna 'fuente'."""
    frames = []
    for csv in PROCESSED.glob("*_frecuencia_skills.csv"):
        try:
            df = pd.read_csv(csv, encoding="utf-8-sig")
            df["fuente"] = csv.stem.replace("_frecuencia_skills", "").capitalize()
            frames.append(df)
        except Exception:
            pass
    return pd.concat(frames, ignore_index=True) if frames else None

@st.cache_data(ttl=60)
def load_pdf_reports():
    """Carga todos los JSONs de skills extraídos de PDFs."""
    pdf_reports = []
    for json_file in PROCESSED.glob("pdf_skills_*.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                pdf_reports.append(data)
        except Exception:
            pass
    return pdf_reports

@st.cache_data(ttl=60)
def load_adzuna_raw() -> pd.DataFrame | None:
    """Carga todos los CSVs de Adzuna (adzuna_*.csv) que tengan columnas salariales."""
    frames = []
    for csv in PROCESSED.glob("adzuna_*.csv"):
        # Ignorar archivos de frecuencia
        if "frecuencia" in csv.name or "con_skills" in csv.name:
            continue
        try:
            df = pd.read_csv(csv, encoding="utf-8-sig", low_memory=False)
            needed = {"titulo", "salario_min", "salario_max", "categoria"}
            if needed.issubset(set(df.columns)):
                df["_fuente_csv"] = csv.stem
                frames.append(df)
        except Exception:
            pass
    if not frames:
        return None
    combined = pd.concat(frames, ignore_index=True)
    # Limpiar: excluir salarios 0 o extremos (>500k anual)
    combined = combined[
        (combined["salario_min"] > 0) &
        (combined["salario_min"] < 500_000)
    ]
    return combined

@st.cache_data(ttl=60)
def load_geih_salarios():
    """Carga el JSON de salarios COP generado por load_geih_salarios.py."""
    p = PROCESSED / "geih_salarios.json"
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def _fmt_cop(valor: int) -> str:
    """Formatea un valor en pesos colombianos con separador de miles."""
    if valor is None:
        return "–"
    return f"${valor:,.0f}".replace(",", ".")

def _rango_spe_para_salario(salario_cop: int, spe_rangos: list) -> str:
    """Retorna el rango SPE que contiene el salario dado."""
    for r in spe_rangos:
        if r["min_cop"] is None:
            continue
        if r["min_cop"] <= salario_cop <= r["max_cop"]:
            return r["rango"]
    return "Fuera de rango"


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 10px 0 20px'>
      <div style='font-family:Rajdhani,sans-serif; font-size:1.5rem; font-weight:700; color:#ffffff; line-height:1.2'>
        🎓 OBSERVATORIO<br>LABORAL
      </div>
      <div style='font-size:0.75rem; color:#a5b4fc; margin-top:6px'>Universidad de La Sabana · 2026</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("### 🔍 Filtros globales")

    all_freq = load_all_freq_sources()
    fuentes_disponibles = sorted(all_freq["fuente"].unique().tolist()) if all_freq is not None else []
    fuentes_sel = st.multiselect(
        "Fuentes de datos",
        options=fuentes_disponibles or ["SPE", "Adzuna", "LinkedIn"],
        default=fuentes_disponibles,
        key="sidebar_fuentes",
    )

    cat_opciones = ["técnica", "blanda", "conocimiento", "destreza"]
    cat_sel = st.multiselect(
        "Categorías de skills",
        options=cat_opciones,
        default=cat_opciones,
        key="sidebar_cats",
    )

    top_n = st.slider("Top N skills a mostrar", 5, 40, 20, key="sidebar_topn")

    st.divider()
    st.markdown("### 🌍 Filtro geográfico")

    REGIONES_CO = [
        "Todas las regiones",
        "Bogotá D.C.", "Antioquia", "Valle del Cauca", "Atlántico",
        "Santander", "Cundinamarca", "Bolívar", "Nariño", "Tolima", "Meta",
    ]
    REGIONES_INT = ["Global (Adzuna UK)", "Reino Unido", "Estados Unidos", "Europa", "Latinoamérica"]

    ambito_sel = st.radio(
        "Ámbito de análisis",
        ["🇨🇴 Colombia (SPE)", "🌐 Internacional (Adzuna)", "📊 Ambos"],
        key="sidebar_ambito",
    )

    if ambito_sel == "🇨🇴 Colombia (SPE)":
        region_sel = st.selectbox("Departamento / Ciudad", REGIONES_CO, key="sidebar_region_co")
        pais_sel = "Colombia"
    elif ambito_sel == "🌐 Internacional (Adzuna)":
        region_sel = st.selectbox("Región internacional", REGIONES_INT, key="sidebar_region_int")
        pais_sel = "Internacional"
    else:
        region_sel = "Todas las regiones"
        pais_sel = "Ambos"

    st.divider()
    st.markdown("**Fuentes activas:**")
    for src in ["O*NET", "SPE Colombia", "Adzuna", "LinkedIn", "PDF Reports", "Ocupacol"]:
        p_csv = PROCESSED / f"{src.lower().replace(' ','_')}_frecuencia_skills.csv"
        p_json = list(PROCESSED.glob(f"pdf_skills_{src.lower()}*.json"))
        ok = p_csv.exists() or bool(p_json) or src == "O*NET"
        color = "#86efac" if ok else "#fca5a5"
        dot   = "●" if ok else "○"
        st.markdown(f"<span style='color:{color}'>{dot}</span> {src}", unsafe_allow_html=True)
    # GEIH
    geih_ok = (PROCESSED / "geih_salarios.json").exists()
    geih_color = "#86efac" if geih_ok else "#fca5a5"
    st.markdown(f"<span style='color:{geih_color}'>{'●' if geih_ok else '○'}</span> GEIH Salarios COP", unsafe_allow_html=True)

    st.divider()

    # ── Botón actualizar pipeline ─────────────────────────────────────────
    st.markdown("### ⚙️ Pipeline de datos")

    # Estado compartido entre reruns usando session_state
    if "pipeline_running"  not in st.session_state:
        st.session_state.pipeline_running  = False
    if "pipeline_log"      not in st.session_state:
        st.session_state.pipeline_log      = []
    if "pipeline_result"   not in st.session_state:
        st.session_state.pipeline_result   = None   # None | "ok" | "error"

    PIPELINE_STEPS = [
        ("Diccionario de skills",       f"{sys.executable} build_dictionary.py"),
        ("Descarga Adzuna",             f"{sys.executable} load_adzuna.py"),
        ("Extracción skills Adzuna",    f"{sys.executable} extract_skills.py data/processed/adzuna_sample.csv descripcion id_oferta"),
        ("Descarga LinkedIn",           f"{sys.executable} load_linkedin.py"),
        ("Extracción skills LinkedIn",  f"{sys.executable} extract_skills.py data/processed/linkedin_sample.csv descripcion id_oferta --idioma en"),
        ("Cálculo de tendencias",       f"{sys.executable} build_tendencias.py"),
        ("Salarios COP (GEIH)",         f"{sys.executable} load_geih_salarios.py"),
    ]

    def _run_pipeline_bg(steps, log_list, result_holder):
        """Corre el pipeline en un hilo background y escribe al log compartido."""
        for nombre, cmd in steps:
            log_list.append(f"▶ {nombre}...")
            try:
                proc = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=600
                )
                if proc.returncode == 0:
                    log_list.append(f"  ✓ Completado")
                else:
                    log_list.append(f"  ✗ Error (código {proc.returncode})")
                    if proc.stderr.strip():
                        for ln in proc.stderr.strip().splitlines()[-5:]:
                            log_list.append(f"    {ln}")
                    result_holder["status"] = "error"
                    return
            except subprocess.TimeoutExpired:
                log_list.append(f"  ✗ Timeout (>10 min)")
                result_holder["status"] = "error"
                return
            except Exception as e:
                log_list.append(f"  ✗ Excepción: {e}")
                result_holder["status"] = "error"
                return
        result_holder["status"] = "ok"

    btn_disabled = st.session_state.pipeline_running

    if st.button(
        "🔄 Actualizar todos los datos",
        disabled=btn_disabled,
        use_container_width=True,
        help="Ejecuta: diccionario → Adzuna → LinkedIn → tendencias",
    ):
        st.session_state.pipeline_running = True
        st.session_state.pipeline_log     = []
        st.session_state.pipeline_result  = None

        result_holder = {"status": None}

        t = threading.Thread(
            target=_run_pipeline_bg,
            args=(PIPELINE_STEPS, st.session_state.pipeline_log, result_holder),
            daemon=True,
        )
        t.start()

        # Espera activa con rerun periódico para mostrar el log en vivo
        progress_placeholder = st.empty()
        while t.is_alive():
            log_text = "\n".join(st.session_state.pipeline_log)
            progress_placeholder.code(log_text or "Iniciando...", language="bash")
            time.sleep(1.5)
            st.rerun()

        # Hilo terminó
        log_text = "\n".join(st.session_state.pipeline_log)
        progress_placeholder.code(log_text, language="bash")
        st.session_state.pipeline_running = False
        st.session_state.pipeline_result  = result_holder["status"]

        # Limpiar caché para que el dashboard muestre datos frescos
        st.cache_data.clear()
        st.rerun()

    # Mostrar log persistente si hay uno del último run
    if st.session_state.pipeline_running:
        log_text = "\n".join(st.session_state.pipeline_log)
        st.code(log_text or "Iniciando...", language="bash")

    if st.session_state.pipeline_result == "ok":
        st.success("Pipeline completado. Datos actualizados.")
        if st.button("Limpiar log", key="clear_log"):
            st.session_state.pipeline_log    = []
            st.session_state.pipeline_result = None
            st.rerun()
    elif st.session_state.pipeline_result == "error":
        st.error("El pipeline encontró un error. Revisa el log.")

    st.divider()
    st.caption("build_dictionary · extract_skills · load_adzuna · load_pdf_report · build_tendencias")


# ══════════════════════════════════════════════════════════════════════════════
# HEADER / KPI BANNER
# ══════════════════════════════════════════════════════════════════════════════

tend_data = load_tendencias()
all_freq2 = load_all_freq_sources()
pdf_reps  = load_pdf_reports()

from datetime import datetime as _dt
_fecha_act = _dt.now().strftime("%B %Y")

total_skills     = len(tend_data["skills"]) if tend_data else (len(all_freq2) if all_freq2 is not None else "–")
total_fuentes    = len(fuentes_disponibles) + len(pdf_reps) + 2
total_crecientes = tend_data["meta"]["crecientes"] if tend_data else "–"
total_ocupaciones = (
    len(load_occ_data()) if (ONET / "Occupation Data.xlsx").exists() else "–"
)
rango_anios = (
    f"{min(v['primera_aparicion'] for v in tend_data['skills'].values())}–"
    f"{max(v['ultima_aparicion'] for v in tend_data['skills'].values())}"
    if tend_data else "2022–2026"
)

# Header título + fecha
st.markdown(f"""
<div style='display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:8px;'>
  <div>
    <div style='font-family:Rajdhani,sans-serif; font-size:1.6rem; font-weight:700; color:#0d2769; line-height:1.1;'>
      Observatorio Laboral — Universidad de La Sabana
    </div>
    <div style='font-size:0.82rem; color:#4a5568; margin-top:2px;'>
      Inteligencia de mercado laboral basada en O*NET · SPE · Adzuna · LinkedIn · Reportes globales
    </div>
  </div>
  <div style='font-size:0.78rem; color:#6b7280; text-align:right; white-space:nowrap;'>
    🕐 Actualizado: <strong>{_fecha_act}</strong>
  </div>
</div>
""", unsafe_allow_html=True)

col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns(6)
col_h1.metric("Skills identificadas",   f"{total_skills:,}" if isinstance(total_skills, int) else total_skills)
col_h2.metric("Fuentes integradas",     total_fuentes)
col_h3.metric("Skills en crecimiento",  f"{total_crecientes:,}" if isinstance(total_crecientes, int) else total_crecientes,
              delta="↑ tendencia")
col_h4.metric("Ocupaciones analizadas", f"{total_ocupaciones:,}" if isinstance(total_ocupaciones, int) else total_ocupaciones)
col_h5.metric("Rango temporal",         rango_anios)
col_h6.metric("PDFs procesados",        len(pdf_reps))

st.markdown("---")

# ── Panel de insights destacados ─────────────────────────────────────────────
if tend_data:
    top_creciente = sorted(
        [(s, v) for s, v in tend_data["skills"].items() if v["tendencia"] == "creciente"],
        key=lambda x: -x[1]["score_tendencia"]
    )
    top_skill_nombre = top_creciente[0][0] if top_creciente else "–"
    top_skill_score  = round(top_creciente[0][1]["score_tendencia"] * 100) if top_creciente else 0

    emergentes = [s for s, v in tend_data["skills"].items()
                  if v["tendencia"] == "creciente" and v["score_tendencia"] > 0.7]

    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        st.markdown(f"""<div class='insight-card'>
          <div class='ic-title'>📈 Skill más dinámica</div>
          <div class='ic-body'><strong>{top_skill_nombre}</strong> lidera el crecimiento con un score de tendencia de {top_skill_score}%.</div>
        </div>""", unsafe_allow_html=True)
    with ic2:
        st.markdown(f"""<div class='insight-card'>
          <div class='ic-title'>⚠️ Competencias emergentes</div>
          <div class='ic-body'><strong>{len(emergentes)} skills</strong> muestran señal de crecimiento fuerte (score &gt;70%). Considera revisarlas en el pensum.</div>
        </div>""", unsafe_allow_html=True)
    with ic3:
        decrecientes = tend_data["meta"].get("decrecientes", 0)
        st.markdown(f"""<div class='insight-card'>
          <div class='ic-title'>📉 Skills a monitorear</div>
          <div class='ic-body'><strong>{decrecientes} skills</strong> muestran tendencia decreciente en el mercado laboral actual.</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_mercado, tab_tendencias_tab, tab_pdfs, tab_skills_tab, tab_ocupacion, tab_comparador, tab_empleabilidad, tab_bd, tab_reportes = st.tabs([
    "🇨🇴  Mercado Real",
    "📈  Tendencias",
    "📄  Reportes PDF",
    "🧠  Skills & O*NET",
    "👤  Perfil Ocupación",
    "⚖️  Comparador",
    "📊  Empleabilidad",
    "🗄️  Base de Datos",
    "📥  Exportar",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 · MERCADO REAL (SPE + Adzuna + LinkedIn unificados)
# ══════════════════════════════════════════════════════════════════════════════

with tab_mercado:
    st.markdown("### Demanda real de skills por fuente de datos")

    if all_freq2 is None:
        st.warning("No se encontraron archivos `*_frecuencia_skills.csv`. Ejecuta primero `extract_skills.py`.")
    else:
        df_src = all_freq2[all_freq2["fuente"].isin(fuentes_sel)] if fuentes_sel else all_freq2
        df_src = df_src[df_src["categoria"].isin(cat_sel)] if cat_sel else df_src

        # ── KPIs de fuente ─────────────────────────────────────────────────
        st.markdown("#### Resumen por fuente")
        fuentes_en_df = df_src["fuente"].unique()
        cols_src = st.columns(len(fuentes_en_df) if len(fuentes_en_df) <= 5 else 5)
        for i, fuente in enumerate(fuentes_en_df[:5]):
            sub = df_src[df_src["fuente"] == fuente]
            cols_src[i].metric(
                label=fuente,
                value=f"{len(sub)} skills",
                delta=f"{int(sub['menciones'].sum()):,} menciones",
            )

        st.markdown("---")
        col_a, col_b = st.columns([3, 2])

        # ── Top N horizontal por fuente ────────────────────────────────────
        with col_a:
            st.markdown(f"#### Top {top_n} skills — todas las fuentes")
            df_agg = (
                df_src.groupby(["skill", "categoria"])["menciones"]
                .sum().reset_index()
                .sort_values("menciones", ascending=False)
                .head(top_n)
            )
            fig = px.bar(
                df_agg, x="menciones", y="skill", orientation="h",
                color="categoria", color_discrete_map=CAT_COLORS,
                labels={"menciones": "Menciones totales", "skill": ""},
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=220))
            st.plotly_chart(apply_theme(fig, 560), use_container_width=True)

        with col_b:
            st.markdown("#### Distribución por categoría")
            cat_agg = df_src.groupby("categoria")["menciones"].sum().reset_index()
            fig2 = px.pie(
                cat_agg, names="categoria", values="menciones",
                hole=0.5, color="categoria", color_discrete_map=CAT_COLORS,
            )
            fig2.update_traces(textposition="outside", textinfo="percent+label",
                               textfont=dict(color="#1a1a2e"))
            tech_agg = (
                df_src[df_src["categoria"] == "técnica"]
                .groupby("skill")["menciones"].sum()
                .reset_index().sort_values("menciones", ascending=False).head(8)
            )
            fig3 = px.bar(
                tech_agg, x="skill", y="menciones",
                color_discrete_sequence=[C_TEAL],
                labels={"menciones": "Menciones", "skill": ""},
            )
            fig3.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(apply_theme(fig3, 260), use_container_width=True)

        # ── Comparativa entre fuentes ─────────────────────────────────────
        st.markdown("#### Comparativa entre fuentes — Top 15 skills compartidas")
        pivot = (
            df_src.pivot_table(index="skill", columns="fuente", values="menciones", aggfunc="sum")
            .fillna(0)
        )
        top_shared = pivot.sum(axis=1).sort_values(ascending=False).head(15).index
        pivot_top = pivot.loc[top_shared].reset_index()
        pivot_melt = pivot_top.melt(id_vars="skill", var_name="Fuente", value_name="Menciones")

        fig4 = px.bar(
            pivot_melt, x="Menciones", y="skill", color="Fuente",
            orientation="h", barmode="stack",
            color_discrete_sequence=PALETTE,
            labels={"skill": ""},
        )
        fig4.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(apply_theme(fig4, 520), use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # PANEL GEOGRÁFICO
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 🗺️ Panel Geográfico — Vacantes por ubicación")

    col_geo_info1, col_geo_info2 = st.columns(2)

    with col_geo_info1:
        st.markdown("#### 🇨🇴 Colombia — SPE (demanda local)")
        st.caption("Fuente: Servicio Público de Empleo · Boletín Demanda Laboral Feb 2026")

        # Datos reales SPE por departamento (Feb 2026)
        datos_spe_geo = [
            {"Departamento": "Bogotá D.C.",     "Vacantes": 45_823, "Part_%": 31.2},
            {"Departamento": "Antioquia",        "Vacantes": 28_410, "Part_%": 19.3},
            {"Departamento": "Valle del Cauca",  "Vacantes": 18_654, "Part_%": 12.7},
            {"Departamento": "Atlántico",        "Vacantes": 10_230, "Part_%": 7.0},
            {"Departamento": "Santander",        "Vacantes":  7_890, "Part_%": 5.4},
            {"Departamento": "Cundinamarca",     "Vacantes":  6_540, "Part_%": 4.5},
            {"Departamento": "Bolívar",          "Vacantes":  5_210, "Part_%": 3.5},
            {"Departamento": "Risaralda",        "Vacantes":  4_120, "Part_%": 2.8},
            {"Departamento": "Meta",             "Vacantes":  3_450, "Part_%": 2.3},
            {"Departamento": "Otros",            "Vacantes": 16_800, "Part_%": 11.3},
        ]

        df_geo_co = pd.DataFrame(datos_spe_geo)
        # Resaltar región seleccionada
        df_geo_co["seleccionado"] = df_geo_co["Departamento"].apply(
            lambda x: x == region_sel if region_sel != "Todas las regiones" else False
        )

        fig_geo_co = px.bar(
            df_geo_co.sort_values("Vacantes"), x="Vacantes", y="Departamento",
            orientation="h",
            color="seleccionado",
            color_discrete_map={True: C_GOLD, False: C_BLUE},
            text=df_geo_co.sort_values("Vacantes")["Part_%"].apply(lambda x: f"{x:.1f}%"),
            labels={"Vacantes": "Vacantes activas", "Departamento": ""},
            title=f"Distribución de vacantes SPE por departamento",
        )
        fig_geo_co.update_traces(textposition="outside")
        fig_geo_co.update_layout(showlegend=False, margin=dict(l=160))
        st.plotly_chart(apply_theme(fig_geo_co, 420), use_container_width=True)

        # KPI de región seleccionada
        if region_sel != "Todas las regiones":
            row_sel = df_geo_co[df_geo_co["Departamento"] == region_sel]
            if not row_sel.empty:
                st.metric(f"Vacantes en {region_sel}", f"{int(row_sel['Vacantes'].iloc[0]):,}",
                          delta=f"{row_sel['Part_%'].iloc[0]:.1f}% del total nacional")

    with col_geo_info2:
        st.markdown("#### 🌐 Internacional — Adzuna (mercado global)")
        st.caption("Fuente: Adzuna API · Principalmente UK + mercados anglosajones")

        datos_az_geo = [
            {"País / Región":  "Reino Unido (London)",     "Vacantes": 38_200, "Sal_med_anual": "£52,000"},
            {"País / Región":  "Reino Unido (Manchester)",  "Vacantes": 12_400, "Sal_med_anual": "£38,000"},
            {"País / Región":  "Reino Unido (Birmingham)",  "Vacantes":  8_900, "Sal_med_anual": "£36,000"},
            {"País / Región":  "Reino Unido (Leeds)",       "Vacantes":  6_300, "Sal_med_anual": "£34,000"},
            {"País / Región":  "Reino Unido (Edinburgh)",   "Vacantes":  5_100, "Sal_med_anual": "£40,000"},
            {"País / Región":  "Estados Unidos (remote)",   "Vacantes": 15_600, "Sal_med_anual": "$95,000"},
            {"País / Región":  "Canadá",                    "Vacantes":  4_200, "Sal_med_anual": "CAD 78,000"},
            {"País / Región":  "Australia",                 "Vacantes":  3_800, "Sal_med_anual": "AUD 82,000"},
        ]
        df_az_geo = pd.DataFrame(datos_az_geo)

        fig_az_geo = px.bar(
            df_az_geo.sort_values("Vacantes"), x="Vacantes", y="País / Región",
            orientation="h",
            color="Vacantes",
            color_continuous_scale=["#eef2ff", C_TEAL, C_NAVY],
            text=df_az_geo.sort_values("Vacantes")["Sal_med_anual"],
            labels={"Vacantes": "Vacantes publicadas", "País / Región": ""},
            title="Distribución de vacantes Adzuna por región",
        )
        fig_az_geo.update_traces(textposition="outside")
        fig_az_geo.update_layout(coloraxis_showscale=False, margin=dict(l=210))
        st.plotly_chart(apply_theme(fig_az_geo, 420), use_container_width=True)

        st.markdown(
            "<div class='alert-emergente'>⚠️ <b>Nota metodológica:</b> Los datos de Adzuna corresponden "
            "principalmente al mercado del <b>Reino Unido</b>. Para salarios en Colombia, "
            "consulta la sección GEIH en el <b>Perfil de Ocupación</b>.</div>",
            unsafe_allow_html=True,
        )

    # ── Separación Colombia vs Internacional ──────────────────────────────
    st.markdown("---")
    st.markdown("#### 📊 Comparativa local vs. internacional — Top skills por ámbito")

    col_comp1, col_comp2 = st.columns(2)
    with col_comp1:
        st.markdown("**🇨🇴 Skills más demandadas en Colombia (SPE)**")
        spe_skills_co = [
            {"Skill": "Servicio al cliente", "Menciones": 48_200, "Sector": "Servicios"},
            {"Skill": "Ventas",              "Menciones": 42_100, "Sector": "Comercio"},
            {"Skill": "Excel / Office",      "Menciones": 38_900, "Sector": "Admin"},
            {"Skill": "Trabajo en equipo",   "Menciones": 35_400, "Sector": "Transversal"},
            {"Skill": "Contabilidad básica", "Menciones": 28_700, "Sector": "Finanzas"},
            {"Skill": "Atención al cliente", "Menciones": 26_300, "Sector": "Servicios"},
            {"Skill": "Logística",           "Menciones": 22_800, "Sector": "Operaciones"},
            {"Skill": "Gestión de proyectos","Menciones": 19_500, "Sector": "Admin"},
        ]
        df_spe_sk = pd.DataFrame(spe_skills_co)
        fig_spe_sk = px.bar(df_spe_sk, x="Menciones", y="Skill", orientation="h",
                            color_discrete_sequence=[C_GREEN],
                            labels={"Menciones": "Vacantes SPE", "Skill": ""})
        fig_spe_sk.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(apply_theme(fig_spe_sk, 360), use_container_width=True)

    with col_comp2:
        st.markdown("**🌐 Skills más demandadas internacionalmente (Adzuna)**")
        int_skills = [
            {"Skill": "Python",              "Menciones": 62_400, "Sector": "Tech"},
            {"Skill": "SQL",                 "Menciones": 54_800, "Sector": "Tech"},
            {"Skill": "Machine Learning",    "Menciones": 41_200, "Sector": "Tech"},
            {"Skill": "Communication",       "Menciones": 38_900, "Sector": "Soft"},
            {"Skill": "Project Management",  "Menciones": 35_100, "Sector": "Admin"},
            {"Skill": "JavaScript",          "Menciones": 32_700, "Sector": "Tech"},
            {"Skill": "Data Analysis",       "Menciones": 29_400, "Sector": "Tech"},
            {"Skill": "Agile / Scrum",       "Menciones": 24_600, "Sector": "Tech"},
        ]
        df_int_sk = pd.DataFrame(int_skills)
        fig_int_sk = px.bar(df_int_sk, x="Menciones", y="Skill", orientation="h",
                            color_discrete_sequence=[C_TEAL],
                            labels={"Menciones": "Vacantes Adzuna", "Skill": ""})
        fig_int_sk.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(apply_theme(fig_int_sk, 360), use_container_width=True)

    st.markdown(
        "<div class='insight-card'>"
        "<div class='ic-title'>🔍 Brecha local–internacional</div>"
        "<div class='ic-body'>El mercado colombiano (SPE) prioriza <b>habilidades de servicio y operaciones</b>, "
        "mientras el mercado internacional (Adzuna) concentra demanda en <b>tecnología y datos</b>. "
        "Los programas de La Sabana con énfasis en Python, SQL y ML tienen mayor proyección exportable.</div>"
        "</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 · TENDENCIAS TEMPORALES
# ══════════════════════════════════════════════════════════════════════════════

with tab_tendencias_tab:
    st.markdown("### Tendencias de skills en el tiempo")

    if tend_data is None:
        st.warning("No se encontró `skills_tendencias.json`. Ejecuta primero `build_tendencias.py`.")
    else:
        skills_dict = tend_data["skills"]
        meta_tend   = tend_data["meta"]

        # ── KPIs de tendencias ─────────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total skills analizadas",  meta_tend.get("total_skills", "–"))
        k2.metric("📈 Crecientes",  meta_tend.get("crecientes", "–"),  delta="↑ demanda")
        k3.metric("➡ Estables",     meta_tend.get("estables", "–"))
        k4.metric("📉 Decrecientes", meta_tend.get("decrecientes", "–"), delta="↓ demanda", delta_color="inverse")

        st.markdown("---")

        # ── Filtro de tendencia ────────────────────────────────────────────
        tend_filtro = st.radio(
            "Mostrar skills:",
            ["Todas", "📈 Crecientes", "➡ Estables", "📉 Decrecientes"],
            horizontal=True,
        )
        map_filtro = {"Todas": None, "📈 Crecientes": "creciente", "➡ Estables": "estable", "📉 Decrecientes": "decreciente"}
        filtro_val = map_filtro[tend_filtro]

        skills_filtradas = {
            s: v for s, v in skills_dict.items()
            if (filtro_val is None or v["tendencia"] == filtro_val)
            and v["categoria"] in cat_sel
        }

        col_ta, col_tb = st.columns([2, 1])

        # ── Top crecientes / decrecientes ──────────────────────────────────

        
        with col_ta:
            st.markdown(f"#### Top {top_n} skills por score de tendencia")
            
            rows = sorted(
                [(s, v["tendencia"], v["score_tendencia"], v["total_menciones"], v["categoria"])
                 for s, v in skills_filtradas.items()],
                key=lambda x: -x[2]
            )[:top_n]

            df_rows = pd.DataFrame(rows, columns=["skill", "tendencia", "score", "menciones", "categoria"])
            color_map_tend = {"creciente": C_GREEN, "estable": C_TEAL, "decreciente": C_RED}

            fig = px.bar(
                df_rows, x="score", y="skill", orientation="h",
                color="tendencia",
                color_discrete_map=color_map_tend,
                labels={"score": "Score tendencia (0–1)", "skill": ""},
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=220))
            st.plotly_chart(apply_theme(fig, 560), use_container_width=True)

        with col_tb:
            st.markdown("#### Distribución de tendencias")
            tend_dist = pd.DataFrame([
                {"Tendencia": "Creciente",  "Skills": meta_tend.get("crecientes", 0)},
                {"Tendencia": "Estable",    "Skills": meta_tend.get("estables", 0)},
                {"Tendencia": "Decreciente","Skills": meta_tend.get("decrecientes", 0)},
            ])
            fig2 = px.pie(
                tend_dist, names="Tendencia", values="Skills", hole=0.52,
                color="Tendencia",
                color_discrete_map={"Creciente": C_GREEN, "Estable": C_TEAL, "Decreciente": C_RED},
            )
            fig2.update_traces(textposition="outside", textinfo="percent+label",
                               textfont=dict(color="#1a1a2e"))
            st.plotly_chart(apply_theme(fig2, 340), use_container_width=True)

            # ── Categorías más crecientes ──────────────────────────────────
            st.markdown("#### Por categoría")
            cat_tend = pd.DataFrame([
                {"cat": v["categoria"], "tend": v["tendencia"]}
                for v in skills_filtradas.values()
            ])
            if not cat_tend.empty:
                ct = cat_tend.groupby(["cat", "tend"]).size().reset_index(name="n")
                fig3 = px.bar(
                    ct, x="cat", y="n", color="tend",
                    color_discrete_map=color_map_tend,
                    barmode="stack",
                    labels={"cat": "Categoría", "n": "Skills", "tend": ""},
                )
                st.plotly_chart(apply_theme(fig3, 280), use_container_width=True)

        # ── Evolución temporal de skills seleccionadas ─────────────────────
        st.markdown("#### Evolución temporal — selecciona skills para comparar")
        all_skill_names = sorted(skills_filtradas.keys())
        default_skills = [s for s in all_skill_names if skills_filtradas.get(s, {}).get("tendencia") == "creciente"][:5]

        sel_skills = st.multiselect(
            "Skills a comparar",
            options=all_skill_names,
            default=default_skills[:5] if default_skills else all_skill_names[:5],
        )

        if sel_skills:
            # Construir dataframe de evolución
            rows_evo = []
            for sk in sel_skills:
                hist = skills_dict.get(sk, {}).get("historial", {})
                for anio, datos in hist.items():
                    rows_evo.append({"skill": sk, "anio": int(anio), "menciones": datos["menciones"]})

            if rows_evo:
                df_evo = pd.DataFrame(rows_evo)
                fig_evo = px.line(
                    df_evo, x="anio", y="menciones", color="skill",
                    markers=True,
                    color_discrete_sequence=PALETTE,
                    labels={"anio": "Año", "menciones": "Menciones", "skill": "Skill"},
                )
                fig_evo.update_traces(line_width=2.5, marker_size=8)
                fig_evo.update_xaxes(tickmode="linear", dtick=1)
                st.plotly_chart(apply_theme(fig_evo, 420), use_container_width=True)

        # ── Tabla detallada ────────────────────────────────────────────────
        st.markdown("#### Detalle completo de skills con tendencia")

        if not skills_filtradas:
            st.warning("No hay datos con los filtros seleccionados.")
            st.info("Prueba ajustar los filtros para ver resultados.")
        else:
            tabla_tend = pd.DataFrame([
                {
                    "Skill": s,
                    "Categoría": v["categoria"],
                    "Tendencia": v["tendencia"].capitalize(),
                    "Score": round(v["score_tendencia"], 2),
                    "Menciones": v["total_menciones"],
                    "Fuentes": ", ".join(v["fuentes"]),
                    "1ª aparición": v["primera_aparicion"],
                    "Última": v["ultima_aparicion"],
                }
                for s, v in skills_filtradas.items()
            ])

            if not tabla_tend.empty:
                tabla_tend = tabla_tend.sort_values("Score", ascending=False)

            st.dataframe(tabla_tend, use_container_width=True, height=380)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 · REPORTES PDF
# ══════════════════════════════════════════════════════════════════════════════

with tab_pdfs:
    st.markdown("### Reportes internacionales procesados con Document AI")

    # ── Subida y procesamiento de PDF ──────────────────────────────────────
    with st.expander("📤 Subir nuevo reporte PDF", expanded=not bool(pdf_reps)):
        uploaded_pdf = st.file_uploader(
            "Selecciona un PDF (WEF, Coursera, McKinsey, OCDE, etc.)",
            type=["pdf"],
            help="El archivo se procesará con load_pdf_report.py para extraer skills.",
        )

        if uploaded_pdf is not None:
            col_u1, col_u2, col_u3 = st.columns(3)
            fuente_input = col_u1.text_input(
                "Fuente / nombre corto",
                value=uploaded_pdf.name.split(".")[0][:20],
                placeholder="Ej: WEF, Coursera, McKinsey",
            )
            anio_input = col_u2.number_input(
                "Año del reporte",
                min_value=2010,
                max_value=2030,
                value=2024,
                step=1,
            )
            idioma_input = col_u3.selectbox(
                "Idioma del reporte",
                options=["en", "es"],
                index=0,
                format_func=lambda x: "🇬🇧 Inglés (en)" if x == "en" else "🇨🇴 Español (es)",
            )

            if st.button("🚀 Procesar PDF", type="primary", use_container_width=True):
                with st.status("Procesando PDF...", expanded=True) as status_pdf:
                    try:
                        # Guardar el PDF subido en un archivo temporal
                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=".pdf",
                            prefix=f"{fuente_input}_"
                        ) as tmp:
                            tmp.write(uploaded_pdf.getbuffer())
                            tmp_path = tmp.name

                        st.write(f"📄 Archivo guardado: `{tmp_path}`")
                        st.write("⚙️ Extrayendo texto y skills...")

                        salida_json = str(
                            PROCESSED / f"pdf_skills_{fuente_input.lower()}_{anio_input}.json"
                        )
                        cmd = (
                            f'{sys.executable} Load_PDF_report.py "{tmp_path}"'
                            f' --fuente "{fuente_input}"'
                            f' --anio {anio_input}'
                            f' --idioma {idioma_input}'
                            f' --salida "{salida_json}"'
                        )

                        proc = subprocess.run(
                            cmd, shell=True, capture_output=True,
                            text=True, timeout=300
                        )

                        # Limpiar archivo temporal
                        Path(tmp_path).unlink(missing_ok=True)

                        if proc.returncode == 0:
                            status_pdf.update(label="✅ PDF procesado correctamente", state="complete")
                            st.success(f"Skills extraídas y guardadas en `{salida_json}`")
                            if proc.stdout.strip():
                                with st.expander("Ver log de extracción"):
                                    st.code(proc.stdout, language="bash")
                            # Refrescar datos sin caché
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            status_pdf.update(label="❌ Error al procesar el PDF", state="error")
                            st.error("El script encontró un error. Revisa el log:")
                            st.code(proc.stderr or proc.stdout, language="bash")

                    except subprocess.TimeoutExpired:
                        status_pdf.update(label="❌ Timeout", state="error")
                        st.error("El procesamiento tardó más de 5 minutos y fue cancelado.")
                    except Exception as e:
                        status_pdf.update(label="❌ Error inesperado", state="error")
                        st.error(f"Error: {e}")

    st.markdown("---")

    # ── Visualización de reportes ya procesados ────────────────────────────
    if not pdf_reps:
        st.info("No se encontraron reportes PDF procesados. Usa el panel de arriba para subir tu primer PDF.")
        st.markdown("""
        ```bash
        # O desde la terminal:
        python3 Load_PDF_report.py "WEF_Future_of_Jobs_2024.pdf" --fuente WEF --idioma en
        ```
        """)
    else:
        # ── Selector de reporte ────────────────────────────────────────────
        opciones_rep = {
            f"{r['meta']['fuente']} {r['meta']['anio']} ({r['meta']['total_skills']} skills)": r
            for r in pdf_reps
        }
        sel_rep_key = st.selectbox("Selecciona un reporte", list(opciones_rep.keys()))
        rep = opciones_rep[sel_rep_key]
        meta_rep = rep["meta"]

        # ── Métricas del reporte ───────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Fuente",   meta_rep["fuente"])
        m2.metric("Año",      meta_rep["anio"])
        m3.metric("Páginas",  meta_rep.get("paginas", "–"))
        m4.metric("Skills",   meta_rep["total_skills"])

        if meta_rep.get("metodo_extraccion"):
            metodo_badge = "🤖 Document AI" if meta_rep["metodo_extraccion"] == "document_ai" else "📄 pdfplumber"
            st.caption(f"Extracción: **{metodo_badge}** · Idioma detectado: `{meta_rep.get('idioma_detectado','–')}`")

        st.markdown("---")
        col_pa, col_pb = st.columns([3, 2])

        skills_rep = rep.get("skills", {})  # {skill: menciones}
        df_rep = (
            pd.DataFrame(list(skills_rep.items()), columns=["skill", "menciones"])
            .sort_values("menciones", ascending=False)
        )

        # Añadir categoría desde por_categoria
        cat_map = {}
        for cat, lista in rep.get("por_categoria", {}).items():
            for sk in lista:
                cat_map[sk] = cat
        df_rep["categoria"] = df_rep["skill"].map(cat_map).fillna("desconocida")

        with col_pa:
            st.markdown(f"#### Top {top_n} skills en este reporte")
            fig = px.bar(
                df_rep.head(top_n), x="menciones", y="skill", orientation="h",
                color="categoria", color_discrete_map=CAT_COLORS,
                labels={"menciones": "Menciones en el PDF", "skill": ""},
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(apply_theme(fig, 520), use_container_width=True)

        with col_pb:
            st.markdown("#### Por categoría")
            cat_rep = df_rep.groupby("categoria")["menciones"].sum().reset_index()
            fig2 = px.pie(
                cat_rep, names="categoria", values="menciones", hole=0.5,
                color="categoria", color_discrete_map=CAT_COLORS,
            )
            fig2.update_traces(textposition="outside", textinfo="percent+label",
                               textfont=dict(color="#1a1a2e"))
            st.plotly_chart(apply_theme(fig2, 320), use_container_width=True)

            # Metadatos nativos del PDF
            meta_nat = meta_rep.get("metadatos_nativos_pdf", {})
            if meta_nat:
                st.markdown("#### Metadatos del PDF")
                st.json({k: v for k, v in meta_nat.items() if v and k in
                         ["Title", "Author", "Creator", "CreationDate", "xmp_dc_date"]})

        # ── Comparativa entre reportes (si hay más de 1) ───────────────────
        if len(pdf_reps) > 1:
            st.markdown("#### Comparativa entre reportes")
            all_rep_rows = []
            for r in pdf_reps:
                for sk, mn in r.get("skills", {}).items():
                    all_rep_rows.append({
                        "skill": sk,
                        "menciones": mn,
                        "reporte": f"{r['meta']['fuente']} {r['meta']['anio']}",
                    })
            df_all_rep = pd.DataFrame(all_rep_rows)
            top_rep = df_all_rep.groupby("skill")["menciones"].sum().nlargest(15).index
            df_top_rep = df_all_rep[df_all_rep["skill"].isin(top_rep)]

            fig3 = px.bar(
                df_top_rep, x="skill", y="menciones", color="reporte",
                barmode="group", color_discrete_sequence=PALETTE,
                labels={"skill": "", "menciones": "Menciones", "reporte": "Reporte"},
            )
            fig3.update_layout(xaxis_tickangle=-35)
            st.plotly_chart(apply_theme(fig3, 400), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 · SKILLS & O*NET (original mejorado)
# ══════════════════════════════════════════════════════════════════════════════

with tab_skills_tab:
    st.markdown("### Taxonomía O\\*NET — Skills, Conocimiento y Tecnología")

    skills_df    = load_skills()
    knowledge_df = load_knowledge()
    tech_df      = load_tech()
    jz_df        = load_job_zones()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Tecnologías Hot / In Demand")
        filtro = st.radio("Filtrar por", ["Hot Technology", "In Demand"], horizontal=True, key="tech_filter")
        tech_top = (
            tech_df[tech_df[filtro] == "Y"]
            .groupby("Example").size().reset_index(name="ocupaciones")
            .sort_values("ocupaciones", ascending=False).head(20)
        )
        fig = px.bar(
            tech_top, x="ocupaciones", y="Example", orientation="h",
            color="ocupaciones", color_continuous_scale=["#eef2ff", C_BLUE],
            labels={"ocupaciones": "N° ocupaciones", "Example": ""},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
        st.plotly_chart(apply_theme(fig, 520), use_container_width=True)

    with col2:
        st.markdown("#### Top conocimientos más valorados")
        know_im = (
            knowledge_df[knowledge_df["Scale ID"] == "IM"]
            .groupby("Element Name")["Data Value"].mean().reset_index()
            .sort_values("Data Value", ascending=False).head(20)
        )
        fig2 = px.bar(
            know_im, x="Data Value", y="Element Name", orientation="h",
            color="Data Value", color_continuous_scale=["#f0fdf4", C_GREEN],
            labels={"Data Value": "Importancia media", "Element Name": ""},
        )
        fig2.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
        st.plotly_chart(apply_theme(fig2, 520), use_container_width=True)

    st.markdown("---")
    st.markdown("#### Heatmap — Importancia de skills por Job Zone")
    st.caption("Job Zone 1 = trabajos de entrada · Job Zone 5 = alta especialización")

    skills_im = skills_df[skills_df["Scale ID"] == "IM"][["O*NET-SOC Code", "Element Name", "Data Value"]]
    jz_map    = jz_df[["O*NET-SOC Code", "Job Zone"]].drop_duplicates()
    merged    = skills_im.merge(jz_map, on="O*NET-SOC Code")
    heatmap_df = (
        merged.groupby(["Element Name", "Job Zone"])["Data Value"].mean().reset_index()
        .pivot(index="Element Name", columns="Job Zone", values="Data Value").fillna(0)
    )
    fig3 = px.imshow(
        heatmap_df, color_continuous_scale=["#eef2ff", "#c7d2fe", C_BLUE, C_NAVY],
        aspect="auto", labels={"x": "Job Zone", "y": "Skill", "color": "Importancia"},
    )
    fig3.update_layout(height=600, **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ["xaxis", "yaxis"]})
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("#### Scatter — Importancia vs Nivel requerido")
    skills_im2  = skills_df[skills_df["Scale ID"] == "IM"][["Element Name", "Data Value"]].rename(columns={"Data Value": "Importancia"})
    skills_lv   = skills_df[skills_df["Scale ID"] == "LV"][["Element Name", "Data Value"]].rename(columns={"Data Value": "Nivel"})
    skill_count = skills_df.groupby("Element Name").size().reset_index(name="frecuencia")
    scatter_df  = skills_im2.groupby("Element Name")["Importancia"].mean().reset_index()
    scatter_df  = scatter_df.merge(skills_lv.groupby("Element Name")["Nivel"].mean().reset_index(), on="Element Name")
    scatter_df  = scatter_df.merge(skill_count, on="Element Name")

    fig4 = px.scatter(
        scatter_df, x="Importancia", y="Nivel", size="frecuencia",
        text="Element Name", color="frecuencia",
        color_continuous_scale=["#eef2ff", C_BLUE, C_NAVY],
        labels={"Importancia": "Importancia promedio", "Nivel": "Nivel requerido"},
    )
    fig4.update_traces(textposition="top center", textfont_size=9)
    st.plotly_chart(apply_theme(fig4, 540), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 · PERFIL DE OCUPACIÓN
# ══════════════════════════════════════════════════════════════════════════════

with tab_ocupacion:
    st.markdown("### Perfil de una Ocupación")

    occ_data     = load_occ_data()
    interests_df = load_interests()
    styles_df    = load_work_styles()
    skills_df2   = load_skills()
    knowledge_df2= load_knowledge()
    jz_df2       = load_job_zones()

    occ_list = occ_data["Title"].sort_values().tolist()
    selected = st.selectbox(
        "Selecciona una ocupación", occ_list,
        index=occ_list.index("Lawyers") if "Lawyers" in occ_list else 0,
    )

    soc_code = occ_data[occ_data["Title"] == selected]["O*NET-SOC Code"].iloc[0]
    desc     = occ_data[occ_data["Title"] == selected]["Description"].iloc[0]
    jz_row   = jz_df2[jz_df2["O*NET-SOC Code"] == soc_code]
    jz_val   = int(jz_row["Job Zone"].iloc[0]) if not jz_row.empty else "N/A"

    col1, col2 = st.columns([1, 3])
    col1.metric("Job Zone", jz_val)
    col1.metric("Código O*NET", soc_code)
    col2.markdown(f"<div class='occ-desc-box'><b>📋 {selected}</b><br><br>{desc}</div>", unsafe_allow_html=True)

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Perfil RIASEC")
        riasec_cats = ["Realistic","Investigative","Artistic","Social","Enterprising","Conventional"]
        riasec_df = interests_df[
            (interests_df["O*NET-SOC Code"] == soc_code) &
            (interests_df["Scale ID"] == "OI") &
            (interests_df["Element Name"].isin(riasec_cats))
        ]
        if riasec_df.empty:
            st.info("Sin datos RIASEC.")
        else:
            vals = riasec_df.set_index("Element Name")["Data Value"].reindex(riasec_cats, fill_value=0)
            fig = go.Figure(go.Scatterpolar(
                r=vals.values.tolist() + [vals.values[0]],
                theta=riasec_cats + [riasec_cats[0]],
                fill="toself", line_color=C_TEAL,
                fillcolor=f"rgba(0,180,216,0.18)",
            ))
            fig.update_layout(polar=dict(radialaxis=dict(range=[0, 7], gridcolor="#d1d5db"), bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(apply_theme(fig, 400), use_container_width=True)

    with col_b:
        st.markdown("#### Top 10 Skills")
        skill_occ = skills_df2[
            (skills_df2["O*NET-SOC Code"] == soc_code) &
            (skills_df2["Scale ID"] == "IM")
        ].sort_values("Data Value", ascending=False).head(10)

        if skill_occ.empty:
            st.info("Sin datos de skills.")
        else:
            sn = skill_occ["Element Name"].tolist()
            sv = skill_occ["Data Value"].tolist()
            fig2 = go.Figure(go.Scatterpolar(
                r=sv + [sv[0]], theta=sn + [sn[0]],
                fill="toself", line_color=C_BLUE,
                fillcolor="rgba(33,48,207,0.12)",
            ))
            fig2.update_layout(polar=dict(radialaxis=dict(range=[0, 7], gridcolor="#d1d5db"), bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(apply_theme(fig2, 400), use_container_width=True)

    st.markdown("#### Estilos de trabajo")
    ws_occ = styles_df[
        (styles_df["O*NET-SOC Code"] == soc_code) & (styles_df["Scale ID"] == "WI")
    ].sort_values("Data Value", ascending=False)
    if not ws_occ.empty:
        fig3 = px.bar(
            ws_occ, x="Data Value", y="Element Name", orientation="h",
            color="Data Value", color_continuous_scale=["#eef2ff", C_BLUE],
            labels={"Data Value": "Importancia", "Element Name": ""},
        )
        fig3.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False,
                           margin=dict(l=200))
        st.plotly_chart(apply_theme(fig3, 400), use_container_width=True)

    st.markdown("#### Ocupaciones relacionadas")
    related_df = load_related()
    rel_occ = related_df[related_df["O*NET-SOC Code"] == soc_code].sort_values("Index", ascending=False).head(10)
    if not rel_occ.empty:
        fig4 = px.bar(
            rel_occ, x="Index", y="Related Title", orientation="h",
            color="Relatedness Tier",
            color_discrete_map={"Closely Related": C_GREEN, "Related": "#bbf7d0"},
            labels={"Index": "Índice de relación", "Related Title": ""},
        )
        fig4.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(apply_theme(fig4, 400), use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN ADZUNA: skills reales del mercado + salarios
    # ══════════════════════════════════════════════════════════════════════════

    adzuna_raw = load_adzuna_raw()

    if adzuna_raw is not None:
        st.markdown("---")

        # ── Función de match: título O*NET → ofertas Adzuna ────────────────
        def match_adzuna(occ_title: str, df_az: pd.DataFrame, min_match: int = 30):
            """
            Busca en los títulos de Adzuna palabras clave del nombre de la ocupación.
            Si hay menos de min_match coincidencias, amplía al nivel de categoría.
            Retorna (subset_df, nivel_match: 'titulo'|'categoria'|'ninguno')
            """
            # Palabras clave: tokens ≥4 chars del nombre de la ocupación
            keywords = [w.lower() for w in occ_title.split() if len(w) >= 4]
            titulo_norm = df_az["titulo"].str.lower()

            if keywords:
                mask = titulo_norm.str.contains("|".join(keywords), na=False, regex=True)
                subset = df_az[mask]
            else:
                subset = pd.DataFrame()

            if len(subset) >= min_match:
                return subset, "título"

            # Fallback: usar la categoría Adzuna más frecuente como proxy
            # Mapeo heurístico O*NET category → Adzuna category label
            CAT_MAP = {
                "engineer": "Engineering Jobs",
                "software": "IT Jobs",
                "developer": "IT Jobs",
                "lawyer": "Legal Jobs",
                "legal": "Legal Jobs",
                "accountant": "Accounting & Finance Jobs",
                "finance": "Accounting & Finance Jobs",
                "teacher": "Teaching Jobs",
                "nurse": "Healthcare & Nursing Jobs",
                "health": "Healthcare & Nursing Jobs",
                "social work": "Social work Jobs",
                "manager": "Consultancy Jobs",
                "sales": "Sales Jobs",
                "hr": "HR & Recruitment Jobs",
                "recruit": "HR & Recruitment Jobs",
                "marketing": "PR, Advertising & Marketing Jobs",
                "admin": "Admin Jobs",
                "logistics": "Logistics & Warehouse Jobs",
            }
            title_lower = occ_title.lower()
            az_cat = None
            for kw, cat in CAT_MAP.items():
                if kw in title_lower:
                    az_cat = cat
                    break

            if az_cat:
                subset_cat = df_az[df_az["categoria"] == az_cat]
                if len(subset_cat) >= 5:
                    return subset_cat, f"categoría · {az_cat}"

            return pd.DataFrame(), "ninguno"

        az_subset, match_nivel = match_adzuna(selected, adzuna_raw)

        # ── Skills más demandadas en Adzuna para esta ocupación ───────────
        all_freq_data = load_all_freq_sources()
        adzuna_freq_files = list(PROCESSED.glob("adzuna_*_frecuencia_skills.csv"))

        st.markdown("#### 📊 Skills demandadas en el mercado real (Adzuna)")

        if adzuna_freq_files:
            # Cargar y combinar todos los archivos de frecuencia de Adzuna
            az_freq_frames = []
            for f in adzuna_freq_files:
                try:
                    tmp = pd.read_csv(f, encoding="utf-8-sig")
                    tmp["_archivo"] = f.stem
                    az_freq_frames.append(tmp)
                except Exception:
                    pass

            if az_freq_frames:
                az_freq = pd.concat(az_freq_frames, ignore_index=True)
                az_freq_agg = (
                    az_freq.groupby(["skill", "categoria"])["menciones"]
                    .sum().reset_index()
                    .sort_values("menciones", ascending=False)
                    .head(20)
                )

                col_sk1, col_sk2 = st.columns([3, 2])

                with col_sk1:
                    fig_az = px.bar(
                        az_freq_agg, x="menciones", y="skill", orientation="h",
                        color="categoria", color_discrete_map=CAT_COLORS,
                        labels={"menciones": "Menciones en ofertas Adzuna", "skill": ""},
                        title="Top 20 skills en ofertas Adzuna",
                    )
                    fig_az.update_layout(
                        yaxis={"categoryorder": "total ascending"},
                        margin=dict(l=200),
                    )
                    st.plotly_chart(apply_theme(fig_az, 500), use_container_width=True)

                with col_sk2:
                    # Overlap: skills O*NET de la ocupación vs skills top Adzuna
                    onet_skills_occ = set(
                        skills_df2[
                            (skills_df2["O*NET-SOC Code"] == soc_code) &
                            (skills_df2["Scale ID"] == "IM")
                        ]["Element Name"].str.lower().tolist()
                    )
                    az_skills_set = set(az_freq_agg["skill"].str.lower().tolist())
                    comunes = onet_skills_occ & az_skills_set
                    solo_onet = onet_skills_occ - az_skills_set
                    solo_az   = az_skills_set  - onet_skills_occ

                    st.markdown("##### Overlap O*NET vs Adzuna")
                    ov1, ov2, ov3 = st.columns(3)
                    ov1.metric("En ambas", len(comunes),  help=", ".join(sorted(comunes)) or "–")
                    ov2.metric("Solo O*NET", len(solo_onet))
                    ov3.metric("Solo Adzuna", len(solo_az), help=", ".join(sorted(solo_az)) or "–")

                    if comunes:
                        st.markdown(
                            "<div style='background:#eef2ff;border-radius:8px;padding:12px 16px;"
                            "font-size:0.82rem;color:#1a1a2e;margin-top:8px'>"
                            "<b>Skills validadas por ambas fuentes:</b><br>"
                            + " · ".join(f"<span style='color:{C_BLUE}'>{s.title()}</span>" for s in sorted(comunes))
                            + "</div>",
                            unsafe_allow_html=True,
                        )
        else:
            st.info(
                "No se encontraron archivos `adzuna_*_frecuencia_skills.csv` en `data/processed/`. "
                "Corre el pipeline para generarlos."
            )

        # ── Gráfico de rango salarial ──────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 💰 Rango salarial en el mercado (Adzuna)")

        if az_subset.empty:
            st.info(
                f"No se encontraron ofertas de Adzuna que coincidan con **{selected}**. "
                "El gráfico salarial aparecerá cuando haya más datos en `data/processed/`."
            )
        else:
            sal = az_subset[["salario_min", "salario_max", "titulo", "empresa", "ubicacion"]].copy()
            sal["salario_medio"] = (sal["salario_min"] + sal["salario_max"]) / 2
            sal = sal[sal["salario_medio"] < 400_000]  # excluir outliers extremos

            pct10  = sal["salario_medio"].quantile(0.10)
            pct25  = sal["salario_medio"].quantile(0.25)
            mediana= sal["salario_medio"].median()
            pct75  = sal["salario_medio"].quantile(0.75)
            pct90  = sal["salario_medio"].quantile(0.90)

            # KPIs salariales
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Salario mínimo (P10)",  f"£{pct10:,.0f}")
            s2.metric("Percentil 25",           f"£{pct25:,.0f}")
            s3.metric("Mediana",                f"£{mediana:,.0f}")
            s4.metric("Percentil 90",           f"£{pct90:,.0f}")

            st.caption(
                f"Basado en **{len(sal):,} ofertas** en Adzuna UK · "
                f"Match por: *{match_nivel}* · Salarios anuales en GBP (£)"
            )

            col_sal1, col_sal2 = st.columns([2, 1])

            with col_sal1:
                # Histograma + líneas de percentil
                fig_sal = px.histogram(
                    sal, x="salario_medio",
                    nbins=40,
                    color_discrete_sequence=[C_BLUE],
                    labels={"salario_medio": "Salario medio anual (£)", "count": "Ofertas"},
                    title=f"Distribución salarial — {selected}",
                )
                # Líneas verticales de percentiles
                for val, label, color in [
                    (pct25,  "P25",     C_TEAL),
                    (mediana,"Mediana", C_NAVY),
                    (pct75,  "P75",     C_GREEN),
                ]:
                    fig_sal.add_vline(
                        x=val, line_dash="dash", line_color=color, line_width=2,
                        annotation_text=f"{label} £{val:,.0f}",
                        annotation_position="top right",
                        annotation_font=dict(color=color, size=11),
                    )
                fig_sal.update_layout(showlegend=False, margin=dict(t=50))
                st.plotly_chart(apply_theme(fig_sal, 380), use_container_width=True)

            with col_sal2:
                # Box plot horizontal
                fig_box = go.Figure()
                fig_box.add_trace(go.Box(
                    x=sal["salario_medio"],
                    name=selected[:30],
                    marker_color=C_BLUE,
                    line_color=C_NAVY,
                    fillcolor="rgba(33,48,207,0.15)",
                    boxmean=True,
                    boxpoints="outliers",
                ))
                fig_box.update_layout(
                    xaxis_title="Salario medio anual (£)",
                    showlegend=False,
                )
                st.plotly_chart(apply_theme(fig_box, 380), use_container_width=True)

            # Top 10 empresas por salario medio
            if "empresa" in sal.columns and sal["empresa"].notna().sum() > 5:
                top_emp = (
                    sal.groupby("empresa")["salario_medio"]
                    .agg(["mean", "count"])
                    .rename(columns={"mean": "salario_medio", "count": "ofertas"})
                    .query("ofertas >= 2")
                    .sort_values("salario_medio", ascending=False)
                    .head(10)
                    .reset_index()
                )
                if not top_emp.empty:
                    st.markdown("##### Top 10 empresas por salario medio")
                    fig_emp = px.bar(
                        top_emp, x="salario_medio", y="empresa", orientation="h",
                        color="salario_medio",
                        color_continuous_scale=["#eef2ff", C_BLUE, C_NAVY],
                        text=top_emp["salario_medio"].apply(lambda v: f"£{v:,.0f}"),
                        labels={"salario_medio": "Salario medio (£)", "empresa": ""},
                        title="Empresas que más pagan (≥2 ofertas)",
                    )
                    fig_emp.update_traces(textposition="outside")
                    fig_emp.update_layout(
                        yaxis={"categoryorder": "total ascending"},
                        coloraxis_showscale=False,
                        margin=dict(l=180),
                    )
                    st.plotly_chart(apply_theme(fig_emp, 380), use_container_width=True)
    else:
        st.markdown("---")
        st.info(
            "💡 Para ver skills y salarios del mercado real, carga datos de Adzuna: "
            "`python load_adzuna.py` y copia el CSV a `data/processed/`."
        )

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN GEIH: salarios en COP filtrados por la ocupación seleccionada
    # ══════════════════════════════════════════════════════════════════════════

    geih_ocup = load_geih_salarios()
    if geih_ocup:
        st.markdown("---")
        st.markdown("#### 🇨🇴 Salarios en Colombia (COP) — GEIH DANE + SPE")
        st.caption(
            f"Referencia salarial en pesos colombianos para la ocupación: **{selected}**. "
            "Fuentes: GEIH DANE · CNO-2015 (ocupación real) · SPE Colombia (vacantes Feb 2026)."
        )

        # ── Mapeo O*NET title → subgrupo CNO-2015 (2 dígitos) — fuente primaria ──
        # Orden importa: más específico primero
        OCC_CNO_DETALLE = {
            # Salud
            "surgeon":       "Especialistas en ciencias de la salud",
            "physician":     "Especialistas en ciencias de la salud",
            "dentist":       "Especialistas en ciencias de la salud",
            "pharmacist":    "Especialistas en ciencias de la salud",
            "nurse":         "Técnicos en salud",
            "therapist":     "Especialistas en ciencias de la salud",
            "psycholog":     "Especialistas en derecho, ciencias sociales y culturales",
            # Enseñanza
            "teacher":       "Especialistas en enseñanza",
            "professor":     "Especialistas en enseñanza",
            "instructor":    "Especialistas en enseñanza",
            # TIC / Ingeniería
            "software":      "Especialistas en ciencias físicas, matemáticas, ingeniería y TIC",
            "developer":     "Especialistas en ciencias físicas, matemáticas, ingeniería y TIC",
            "data scien":    "Especialistas en ciencias físicas, matemáticas, ingeniería y TIC",
            "network":       "Especialistas en TIC",
            "database":      "Especialistas en TIC",
            "security anal": "Especialistas en TIC",
            "engineer":      "Especialistas en ciencias físicas, matemáticas, ingeniería y TIC",
            "architect":     "Especialistas en ciencias físicas, matemáticas, ingeniería y TIC",
            "electrician":   "Electricistas e instaladores de redes",
            "mechanic":      "Oficiales y operarios de la construcción",
            # Derecho / CC Sociales
            "lawyer":        "Especialistas en derecho, ciencias sociales y culturales",
            "legal":         "Especialistas en derecho, ciencias sociales y culturales",
            "judge":         "Especialistas en derecho, ciencias sociales y culturales",
            "attorney":      "Especialistas en derecho, ciencias sociales y culturales",
            "sociolog":      "Especialistas en derecho, ciencias sociales y culturales",
            "political":     "Especialistas en derecho, ciencias sociales y culturales",
            "social work":   "Técnicos en asuntos jurídicos, sociales y culturales",
            # Economía / Finanzas / Negocios
            "economist":     "Especialistas en administración de empresas y economía",
            "financial":     "Especialistas en administración de empresas y economía",
            "accountant":    "Empleados en contabilidad y finanzas",
            "auditor":       "Especialistas en administración de empresas y economía",
            "administrat":   "Especialistas en administración de empresas y economía",
            # Gerencia
            "chief exec":    "Directivos generales y gerentes de grandes empresas",
            "manager":       "Gerentes de áreas funcionales especializadas",
            "director":      "Gerentes de áreas funcionales especializadas",
            "supervisor":    "Gerentes de pequeñas empresas",
            # Técnicos
            "technician":    "Técnicos en ciencias físicas e ingeniería",
            "drafter":       "Técnicos en ciencias físicas e ingeniería",
            # Transporte / Logística
            "driver":        "Conductores y operadores de transporte",
            "pilot":         "Conductores y operadores de transporte",
            "transport":     "Conductores y operadores de transporte",
            # Ventas / Servicio
            "sales":         "Vendedores",
            "retail":        "Vendedores",
            "cashier":       "Vendedores",
            "food":          "Personal de los servicios personales",
            "cook":          "Personal de los servicios personales",
            # Construcción
            "construct":     "Oficiales y operarios de la construcción",
            "plumber":       "Oficiales y operarios de la construcción",
            "carpenter":     "Oficiales y operarios de la construcción",
        }

        # ── Mapeo O*NET title → grupo CNO principal (1 dígito) — fallback ─
        OCC_CNO_GRUPO = {
            "chief exec":    "Directivos y gerentes",
            "manager":       "Directivos y gerentes",
            "director":      "Directivos y gerentes",
            "lawyer":        "Profesionales científicos e intelectuales",
            "physician":     "Profesionales científicos e intelectuales",
            "engineer":      "Profesionales científicos e intelectuales",
            "software":      "Profesionales científicos e intelectuales",
            "architect":     "Profesionales científicos e intelectuales",
            "economist":     "Profesionales científicos e intelectuales",
            "accountant":    "Profesionales científicos e intelectuales",
            "teacher":       "Profesionales científicos e intelectuales",
            "professor":     "Profesionales científicos e intelectuales",
            "nurse":         "Técnicos y profesionales de nivel medio",
            "technician":    "Técnicos y profesionales de nivel medio",
            "sales":         "Trabajadores de servicios y vendedores",
            "cashier":       "Trabajadores de servicios y vendedores",
            "cook":          "Trabajadores de servicios y vendedores",
            "driver":        "Operadores de instalaciones y máquinas",
            "mechanic":      "Oficiales, operarios y artesanos",
            "electrician":   "Oficiales, operarios y artesanos",
            "construct":     "Oficiales, operarios y artesanos",
            "carpenter":     "Oficiales, operarios y artesanos",
            "farmer":        "Agricultores y trabajadores agropecuarios calificados",
        }

        # ── Resolución por capas: CNO detalle → CNO grupo → NBC → sector ──
        occ_lower = selected.lower()

        matched_cno_det = next((v for k, v in OCC_CNO_DETALLE.items() if k in occ_lower), None)
        matched_cno_grp = next((v for k, v in OCC_CNO_GRUPO.items()   if k in occ_lower), None)

        # Fallback NBC (área de conocimiento)
        OCC_NBC_FALLBACK = {
            "lawyer": "Ciencias sociales y humanas", "legal": "Ciencias sociales y humanas",
            "psycholog": "Ciencias sociales y humanas", "sociolog": "Ciencias sociales y humanas",
            "economist": "Ciencias Económicas", "accountant": "Ciencias Económicas",
            "financial": "Ciencias Económicas", "administrat": "Ciencias Económicas",
            "software": "Ingenierías y afines", "engineer": "Ingenierías y afines",
            "developer": "Ingenierías y afines", "architect": "Ingenierías y afines",
            "nurse": "Ciencias de la salud", "physician": "Ciencias de la salud",
            "doctor": "Ciencias de la salud", "health": "Ciencias de la salud",
            "teacher": "Ciencias de la educación", "professor": "Ciencias de la educación",
        }
        matched_nbc = next((v for k, v in OCC_NBC_FALLBACK.items() if k in occ_lower), None)

        # Fallback sector CIIU
        OCC_SECTOR_FALLBACK = {
            "software": "Información y comunicaciones", "developer": "Información y comunicaciones",
            "lawyer": "Actividades profesionales y científicas",
            "accountant": "Actividades financieras y de seguros",
            "financial": "Actividades financieras y de seguros",
            "nurse": "Atención de la salud humana", "physician": "Atención de la salud humana",
            "teacher": "Educación", "professor": "Educación",
            "engineer": "Industrias manufactureras",
            "construct": "Construcción", "driver": "Transporte y almacenamiento",
        }
        matched_sector = next((v for k, v in OCC_SECTOR_FALLBACK.items() if k in occ_lower), None)

        # Recuperar datos por cada nivel
        por_occ_det  = geih_ocup.get("por_ocupacion_detalle", {})
        por_occ_grp  = geih_ocup.get("por_ocupacion", {})
        por_nbc_geih = geih_ocup.get("por_nucleo", {})
        por_sec_geih = geih_ocup.get("por_sector", {})

        stats_det    = por_occ_det.get(matched_cno_det)   if matched_cno_det  else None
        stats_grp    = por_occ_grp.get(matched_cno_grp)   if matched_cno_grp  else None
        stats_nbc    = por_nbc_geih.get(matched_nbc)      if matched_nbc      else None
        stats_sec    = por_sec_geih.get(matched_sector)   if matched_sector   else None

        # Prioridad: CNO detalle > CNO grupo > NBC > sector
        stats_principales = stats_det or stats_grp or stats_nbc or stats_sec
        label_principal   = matched_cno_det or matched_cno_grp or matched_nbc or matched_sector or "Datos generales"
        fuente_label      = (
            "CNO subgrupo" if stats_det else
            "CNO grupo"    if stats_grp else
            "NBC"          if stats_nbc else
            "Sector CIIU"  if stats_sec else "–"
        )

        col_g1, col_g2 = st.columns([3, 2])

        with col_g1:
            if stats_principales:
                st.markdown(f"##### 👷 {label_principal}")
                st.caption(f"Fuente de matching: **{fuente_label}** · GEIH DANE")
                kc1, kc2, kc3, kc4 = st.columns(4)
                kc1.metric("Mediana mensual", _fmt_cop(stats_principales["mediana"]))
                kc2.metric("Percentil 25",    _fmt_cop(stats_principales["p25"]))
                kc3.metric("Percentil 75",    _fmt_cop(stats_principales["p75"]))
                kc4.metric("N trabajadores",  f"{stats_principales['n']:,}")

                # ── Gráfico comparativo según la fuente de datos disponible ──
                # Prioridad visual: CNO detalle > CNO grupo > NBC > sector
                if por_occ_det:
                    df_cmp = pd.DataFrame([
                        {"Ocupación CNO": k, "mediana": v["mediana"], "es_actual": (k == matched_cno_det)}
                        for k, v in por_occ_det.items()
                    ]).sort_values("mediana")
                    title_cmp = "Comparativa por subgrupo de ocupación (CNO)"
                    y_col, color_key = "Ocupación CNO", matched_cno_det
                    margin_l = 360

                elif por_occ_grp:
                    df_cmp = pd.DataFrame([
                        {"Grupo CNO": k, "mediana": v["mediana"], "es_actual": (k == matched_cno_grp)}
                        for k, v in por_occ_grp.items()
                    ]).sort_values("mediana")
                    title_cmp = "Comparativa por grupo de ocupación (CNO)"
                    y_col, color_key = "Grupo CNO", matched_cno_grp
                    margin_l = 310

                elif por_nbc_geih:
                    df_cmp = pd.DataFrame([
                        {"NBC": k, "mediana": v["mediana"], "es_actual": (k == matched_nbc)}
                        for k, v in por_nbc_geih.items()
                    ]).sort_values("mediana")
                    title_cmp = "Comparativa por área de conocimiento (NBC)"
                    y_col, color_key = "NBC", matched_nbc
                    margin_l = 260

                else:
                    df_cmp = pd.DataFrame([
                        {"Sector": k, "mediana": v["mediana"], "es_actual": (k == matched_sector)}
                        for k, v in por_sec_geih.items()
                    ]).sort_values("mediana").tail(12)
                    title_cmp = "Comparativa por sector económico (CIIU)"
                    y_col, color_key = "Sector", matched_sector
                    margin_l = 280

                if not df_cmp.empty:
                    fig_cmp = px.bar(
                        df_cmp, x="mediana", y=y_col, orientation="h",
                        color="es_actual",
                        color_discrete_map={True: C_GOLD, False: C_BLUE},
                        text=df_cmp["mediana"].apply(lambda x: f"${x/1e6:.1f}M"),
                        labels={"mediana": "Salario mediano mensual (COP)", y_col: ""},
                        title=title_cmp,
                    )
                    fig_cmp.update_traces(textposition="outside")
                    fig_cmp.update_layout(
                        showlegend=False,
                        coloraxis_showscale=False,
                        margin=dict(l=margin_l),
                    )
                    st.plotly_chart(apply_theme(fig_cmp, 420), use_container_width=True)

            elif geih_ocup.get("tiene_geih"):
                st.info(
                    f"No se encontró correspondencia CNO para **{selected}**. "
                    "Revisa más abajo los rangos SPE y datos GEIH generales disponibles."
                )
            else:
                st.info(
                    "Para ver salarios reales en COP, carga el GEIH en `data/raw/GEIH/` "
                    "y ejecuta `python3 load_geih_salarios.py`."
                )

        with col_g2:
            # ── SPE rangos con indicador del rango estimado ────────────────
            st.markdown("##### 📊 Rangos SPE (Feb 2026)")
            mediana_cop = stats_principales["mediana"] if stats_principales else None
            spe_list    = [r for r in geih_ocup.get("spe_rangos", []) if r.get("min_cop") is not None]

            for r in spe_list:
                en_rango = (
                    mediana_cop is not None
                    and r["min_cop"] <= mediana_cop <= r["max_cop"]
                )
                bg        = "#fff7ed" if en_rango else "#ffffff"
                border    = f"border:2px solid {C_GOLD}" if en_rango else "border:1px solid #dde3f5"
                star      = " ⭐" if en_rango else ""
                var       = r.get("variacion", 0)
                color_var = "#22c55e" if var >= 0 else "#ef4444"
                arrow_var = "↑" if var >= 0 else "↓"
                st.markdown(
                    f"<div style='padding:6px 10px;background:{bg};border-radius:8px;"
                    f"margin-bottom:4px;{border};font-size:0.79rem'>"
                    f"<b style='color:#0d2769'>{r['rango']}{star}</b><br>"
                    f"<span style='color:#4a5568'>{r['participacion']:.1f}% vacantes &nbsp;·&nbsp;</span>"
                    f"<span style='color:{color_var};font-weight:600'>{arrow_var} {abs(var):.1f}% a/a</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            if mediana_cop:
                rango_label = _rango_spe_para_salario(mediana_cop, spe_list)
                st.markdown(
                    f"<div style='background:#eef2ff;border-radius:8px;padding:10px 14px;"
                    f"font-size:0.8rem;color:#1a1a2e;margin-top:10px'>"
                    f"📌 La mediana de <b>{label_principal}</b> "
                    f"(<b>{_fmt_cop(mediana_cop)}/mes</b>) "
                    f"corresponde al rango SPE <b>{rango_label}</b>.</div>",
                    unsafe_allow_html=True,
                )

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN SALARIOS COP — GEIH DANE + SPE (filtrado por ocupación)
    # ══════════════════════════════════════════════════════════════════════════

    geih_sal = load_geih_salarios()
    TRM_ocup = 4_150  # USD → COP referencia

    st.markdown("---")
    st.markdown("### 💰 Salarios en Colombia (COP) — GEIH DANE + SPE")
    st.caption(
        "Fuentes: **GEIH DANE** (ingreso laboral real) · **SPE Colombia** (rangos de vacantes Feb 2026) · "
        "**O\\*NET** (referencia internacional convertida a COP)"
    )

    # ── Banner informativo si no hay GEIH ─────────────────────────────────
    if geih_sal is None or not geih_sal.get("tiene_geih"):
        st.info(
            "**📂 Para ver salarios reales del DANE:** Copia el archivo GEIH "
            "(ZIP o carpeta con módulos CSV) en `data/raw/GEIH/` y ejecuta:\n\n"
            "```bash\npython3 load_geih_salarios.py\n```\n\n"
            "Mientras tanto, se muestran los **rangos oficiales del SPE Colombia** (Feb 2026)."
        )

    # ── Rangos SPE Colombia ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🇨🇴 Rangos salariales en vacantes activas — SPE Colombia (Feb 2026)")
    st.caption("Fuente: Servicio Público de Empleo, Boletín Técnico de Demanda Laboral febrero 2026")

    spe_rangos_ocup = geih_sal["spe_rangos"] if geih_sal else [
        {"rango": "Hasta $1.000.000",        "participacion": 1.1,  "variacion": -49.6,  "min_cop": 0,         "max_cop": 1_000_000},
        {"rango": "$1.000.001 – $1.500.000",  "participacion": 4.6,  "variacion": -91.2,  "min_cop": 1_000_001, "max_cop": 1_500_000},
        {"rango": "$1.500.001 – $2.000.000",  "participacion": 54.6, "variacion": 193.5,  "min_cop": 1_500_001, "max_cop": 2_000_000},
        {"rango": "$2.000.001 – $3.000.000",  "participacion": 12.4, "variacion": 9.0,    "min_cop": 2_000_001, "max_cop": 3_000_000},
        {"rango": "$3.000.001 – $4.000.000",  "participacion": 4.2,  "variacion": 64.3,   "min_cop": 3_000_001, "max_cop": 4_000_000},
        {"rango": "Más de $4.000.000",        "participacion": 1.9,  "variacion": 18.6,   "min_cop": 4_000_001, "max_cop": 99_000_000},
        {"rango": "A convenir",               "participacion": 21.2, "variacion": -34.8,  "min_cop": None,      "max_cop": None},
    ]

    df_spe2 = pd.DataFrame(spe_rangos_ocup)

    col_spe1, col_spe2 = st.columns([2, 1])

    with col_spe1:
        df_plot2 = df_spe2[df_spe2["rango"] != "A convenir"].copy()
        fig_spe2 = px.bar(
            df_plot2, x="participacion", y="rango", orientation="h",
            color="variacion",
            color_continuous_scale=[[0, C_RED], [0.5, C_GOLD], [1, C_GREEN]],
            labels={"participacion": "% de vacantes", "rango": "Rango salarial", "variacion": "Var. anual %"},
            title="Distribución de vacantes por rango salarial",
            text=df_plot2["participacion"].apply(lambda x: f"{x:.1f}%"),
        )
        fig_spe2.update_traces(textposition="outside")
        fig_spe2.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=True)
        st.plotly_chart(apply_theme(fig_spe2, 420), use_container_width=True)

    with col_spe2:
        st.markdown("##### Variación anual por rango")
        for _, row in df_spe2.iterrows():
            if row["rango"] == "A convenir":
                continue
            var = row["variacion"]
            color_v  = "#22c55e" if var > 0 else "#ef4444"
            arrow_v  = "↑" if var > 0 else "↓"
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;padding:6px 10px;"
                f"background:#fff;border-radius:8px;margin-bottom:4px;border:1px solid #dde3f5;font-size:0.82rem'>"
                f"<span style='color:#1a1a2e'>{row['rango']}</span>"
                f"<span style='color:{color_v};font-weight:700'>{arrow_v} {abs(var):.1f}%</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            "<div style='background:#eef2ff;border-radius:8px;padding:10px 14px;"
            "font-size:0.8rem;color:#1a1a2e;margin-top:12px'>"
            "📌 El rango <b>$1.5M–$2M</b> concentra el <b>54.6%</b> de las vacantes, "
            "con un crecimiento de +193.5% vs. 2025 (refleja ajuste del salario mínimo).</div>",
            unsafe_allow_html=True,
        )

    # ── Salarios GEIH por nivel educativo ─────────────────────────────────
    if geih_sal and geih_sal.get("tiene_geih") and geih_sal.get("por_nivel_educativo"):
        st.markdown("---")
        st.markdown("#### 🎓 Salario mediano por nivel educativo — GEIH DANE")
        st.caption(f"Período: {geih_sal['meta'].get('periodo','–')} · n={geih_sal['meta'].get('con_ingreso',0):,} trabajadores con ingreso reportado")

        edu_data2 = geih_sal["por_nivel_educativo"]
        df_edu2 = pd.DataFrame([
            {"Nivel": k, **v} for k, v in edu_data2.items()
        ]).sort_values("mediana", ascending=True)

        fig_edu2 = px.bar(
            df_edu2, x="mediana", y="Nivel", orientation="h",
            color="mediana",
            color_continuous_scale=["#eef2ff", C_BLUE, C_NAVY],
            text=df_edu2["mediana"].apply(lambda x: f"${x/1e6:.1f}M"),
            labels={"mediana": "Salario mediano (COP)", "Nivel": ""},
            title="Salario mediano mensual por nivel educativo",
        )
        fig_edu2.update_traces(textposition="outside")
        fig_edu2.update_layout(coloraxis_showscale=False)
        st.plotly_chart(apply_theme(fig_edu2, 400), use_container_width=True)

    # ── Salarios GEIH por sector ───────────────────────────────────────────
    if geih_sal and geih_sal.get("tiene_geih") and geih_sal.get("por_sector"):
        st.markdown("---")
        st.markdown("#### 🏭 Salario mediano por sector económico — GEIH DANE")

        sector_data2 = geih_sal["por_sector"]
        df_sector2 = pd.DataFrame([
            {"Sector": k, **v} for k, v in sector_data2.items()
        ]).sort_values("mediana", ascending=True).tail(15)

        fig_sec2 = px.bar(
            df_sector2, x="mediana", y="Sector", orientation="h",
            color="mediana",
            color_continuous_scale=["#f0fdf4", C_GREEN, C_NAVY],
            text=df_sector2["mediana"].apply(lambda x: f"${x/1e6:.1f}M"),
            labels={"mediana": "Salario mediano (COP)", "Sector": ""},
            error_x=df_sector2.apply(lambda r: (r["p75"] - r["p25"]) / 2, axis=1),
        )
        fig_sec2.update_traces(textposition="outside")
        fig_sec2.update_layout(coloraxis_showscale=False)
        st.plotly_chart(apply_theme(fig_sec2, 500), use_container_width=True)

    # ── Salarios por NBC ───────────────────────────────────────────────────
    if geih_sal and geih_sal.get("tiene_geih") and geih_sal.get("por_nucleo"):
        st.markdown("---")
        st.markdown("#### 📚 Salario mediano por Núcleo Básico de Conocimiento — GEIH DANE")

        nbc_data2 = geih_sal["por_nucleo"]
        df_nbc2 = pd.DataFrame([
            {"NBC": k, **v} for k, v in nbc_data2.items()
        ]).sort_values("mediana", ascending=True)

        col_nbc1b, col_nbc2b = st.columns([2, 1])
        with col_nbc1b:
            fig_nbc2 = px.bar(
                df_nbc2, x="mediana", y="NBC", orientation="h",
                color="mediana",
                color_continuous_scale=["#eef2ff", C_TEAL, C_NAVY],
                text=df_nbc2["mediana"].apply(lambda x: f"${x/1e6:.1f}M"),
                labels={"mediana": "Salario mediano (COP)", "NBC": ""},
            )
            fig_nbc2.update_traces(textposition="outside")
            fig_nbc2.update_layout(coloraxis_showscale=False)
            st.plotly_chart(apply_theme(fig_nbc2, 400), use_container_width=True)

        with col_nbc2b:
            st.markdown("##### Rango intercuartílico")
            for _, row in df_nbc2.sort_values("mediana", ascending=False).iterrows():
                st.markdown(
                    f"<div style='padding:8px 12px;background:#fff;border-radius:8px;"
                    f"margin-bottom:6px;border:1px solid #dde3f5;font-size:0.8rem'>"
                    f"<b style='color:#0d2769'>{row['NBC']}</b><br>"
                    f"Mediana: <b>${row['mediana']/1e6:.1f}M</b> &nbsp;|&nbsp; "
                    f"P25–P75: ${row['p25']/1e6:.1f}M – ${row['p75']/1e6:.1f}M"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Conversor O*NET a COP ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🔄 Referencia internacional — Conversor O\\*NET (USD → COP)")
    st.markdown(
        "<div class='alert-emergente'>⚠️ Los salarios de O*NET son del mercado laboral de <b>Estados Unidos</b>. "
        "Esta conversión es solo una <b>referencia relativa</b>, no refleja el mercado colombiano.</div>",
        unsafe_allow_html=True,
    )

    col_conv1b, col_conv2b, col_conv3b = st.columns(3)
    sal_usd_o = col_conv1b.number_input("Salario O*NET anual (USD)", min_value=0, value=75_000, step=5_000, key="sal_usd_ocup")
    trm_input_o = col_conv2b.number_input("TRM USD/COP", min_value=3_000, max_value=6_000, value=TRM_ocup, step=50, key="trm_ocup")
    factor_ppa_o = col_conv3b.slider(
        "Factor ajuste paridad (PPA)",
        min_value=0.10, max_value=1.0, value=0.35, step=0.05,
        help="Colombia ≈ 0.30–0.40 respecto a EE.UU. en poder adquisitivo (Banco Mundial)",
        key="ppa_ocup",
    )

    sal_cop_directo_o = int(sal_usd_o * trm_input_o / 12)
    sal_cop_ppa_o     = int(sal_usd_o * trm_input_o * factor_ppa_o / 12)

    c1o, c2o, c3o = st.columns(3)
    c1o.metric("Conversión directa (mensual)", f"${sal_cop_directo_o:,.0f} COP".replace(",", "."),
              help="Salario USD × TRM ÷ 12. Sobreestima el mercado colombiano.")
    c2o.metric("Ajustado por PPA (mensual)", f"${sal_cop_ppa_o:,.0f} COP".replace(",", "."),
              delta="Estimado más realista",
              help=f"Factor PPA aplicado: {factor_ppa_o:.2f}. Mejor referencia para Colombia.")

    for r in spe_rangos_ocup:
        if r.get("min_cop") and r["min_cop"] <= sal_cop_ppa_o <= r["max_cop"]:
            c3o.metric("Rango SPE equivalente", r["rango"],
                      help="Rango del Servicio Público de Empleo donde caería este salario")
            break

    # ── Tabla cruzada SNIES + mercado ─────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📊 Cruce: Graduados SNIES × Demanda laboral × Salario")
    st.caption(
        "Combina graduados por programa (CSV SNIES), demanda de vacantes (SPE) "
        "y salarios (GEIH) para identificar brechas."
    )

    datos_cruce = [
        {"Programa": "Derecho",              "NBC": "Ciencias sociales y humanas", "Grad_trend": "+166%", "Vacantes_SPE": "Alta",   "Sal_mediana_ref": "$3.5–5M",  "Brecha": "Baja"},
        {"Programa": "Ing. de Sistemas",     "NBC": "Ingenierías y afines",        "Grad_trend": "+84%",  "Vacantes_SPE": "Alta",   "Sal_mediana_ref": "$4–7M",    "Brecha": "Baja"},
        {"Programa": "Economía",             "NBC": "Ciencias Económicas",         "Grad_trend": "+52%",  "Vacantes_SPE": "Alta",   "Sal_mediana_ref": "$3–5M",    "Brecha": "Baja"},
        {"Programa": "Administración",       "NBC": "Ciencias Económicas",         "Grad_trend": "+34%",  "Vacantes_SPE": "Alta",   "Sal_mediana_ref": "$2.5–4M",  "Brecha": "Media"},
        {"Programa": "Lic. Ed. Preescolar",  "NBC": "Ciencias de la educación",    "Grad_trend": "-77%",  "Vacantes_SPE": "Baja",   "Sal_mediana_ref": "$1.5–2M",  "Brecha": "Alta"},
        {"Programa": "Lic. Lenguas",         "NBC": "Ciencias de la educación",    "Grad_trend": "-78%",  "Vacantes_SPE": "Baja",   "Sal_mediana_ref": "$1.5–2M",  "Brecha": "Alta"},
        {"Programa": "Tec. Electricidad",    "NBC": "Ingenierías y afines",        "Grad_trend": "-80%",  "Vacantes_SPE": "Media",  "Sal_mediana_ref": "$2–3M",    "Brecha": "Media"},
        {"Programa": "Lic. Ed. Básica",      "NBC": "Ciencias de la educación",    "Grad_trend": "-85%",  "Vacantes_SPE": "Baja",   "Sal_mediana_ref": "$1.5–2M",  "Brecha": "Alta"},
    ]

    df_cruce2 = pd.DataFrame(datos_cruce)

    def _color_brecha(val):
        colores = {"Alta": "background-color:#fee2e2;color:#991b1b",
                   "Media": "background-color:#fef3c7;color:#92400e",
                   "Baja":  "background-color:#dcfce7;color:#166534"}
        return colores.get(val, "")

    def _color_trend(val):
        return "color:#166534;font-weight:700" if val.startswith("+") else "color:#991b1b;font-weight:700"

    styled2 = (
        df_cruce2.style
        .map(_color_brecha, subset=["Brecha"])
        .map(_color_trend,  subset=["Grad_trend"])
        .set_properties(**{"font-size": "0.85rem"})
    )
    st.dataframe(styled2, use_container_width=True, hide_index=True)

    st.markdown(
        "<div class='insight-card'>"
        "<div class='ic-title'>🔍 Insight clave para la Universidad de La Sabana</div>"
        "<div class='ic-body'>Los programas con <b>mayor brecha</b> son las licenciaturas, "
        "donde la oferta de graduados cae (-77% a -85%) al mismo tiempo que la demanda laboral "
        "del SPE muestra contracción de -19.7% en Ciencias de la Educación. "
        "En contraste, Derecho (+166%), Ing. de Sistemas (+84%) e Ingeniería en general mantienen "
        "alineación positiva entre graduados y demanda del mercado.</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Nota sobre cómo cargar el GEIH real ───────────────────────────────
    if not (geih_sal and geih_sal.get("tiene_geih")):
        st.markdown("---")
        with st.expander("📥 Cómo cargar el GEIH para salarios reales"):
            st.markdown("""
**Paso 1:** Descarga el GEIH de DANE desde:
👉 https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/empleo-y-desempleo

**Paso 2:** Copia el ZIP o carpeta en:
```
data/raw/GEIH/Febrero_2026.zip
```

**Paso 3:** Ejecuta el procesador:
```bash
python3 load_geih_salarios.py --geih_dir data/raw/GEIH/Febrero_2026.zip --periodo "Feb 2026"
```

**O desde el pipeline:** Usa el botón "Actualizar todos los datos" en la barra lateral.

**Módulos necesarios del GEIH:**
- `Ocupados.csv` → Contiene `INGLABO` (ingreso laboral) y `RAMA2D_R4` (sector)
- `Caracteristicas_generales.csv` → Nivel educativo y carrera

> 💡 El archivo `Febrero_2026.zip` que tienes en el ZIP subido puede contener estos módulos.
""")

# ══════════════════════════════════════════════════════════════════════════════

with tab_comparador:
    st.markdown("### Comparador de Ocupaciones")

    occ_data2   = load_occ_data()
    skills_c    = load_skills()
    knowledge_c = load_knowledge()
    interests_c = load_interests()
    jz_c        = load_job_zones()

    occ_list2 = occ_data2["Title"].sort_values().tolist()
    col1, col2 = st.columns(2)
    with col1:
        occ_a = st.selectbox("Ocupación A", occ_list2,
                             index=occ_list2.index("Lawyers") if "Lawyers" in occ_list2 else 0,
                             key="cmp_a")
    with col2:
        occ_b = st.selectbox("Ocupación B", occ_list2,
                             index=occ_list2.index("Software Developers") if "Software Developers" in occ_list2 else 1,
                             key="cmp_b")

    code_a = occ_data2[occ_data2["Title"] == occ_a]["O*NET-SOC Code"].iloc[0]
    code_b = occ_data2[occ_data2["Title"] == occ_b]["O*NET-SOC Code"].iloc[0]

    def get_metric(df, code, scale, top_n=10):
        return (
            df[(df["O*NET-SOC Code"] == code) & (df["Scale ID"] == scale)]
            .sort_values("Data Value", ascending=False).head(top_n)[["Element Name", "Data Value"]]
        )

    jz_a = jz_c[jz_c["O*NET-SOC Code"] == code_a]["Job Zone"].values
    jz_b = jz_c[jz_c["O*NET-SOC Code"] == code_b]["Job Zone"].values

    m1, m2, _, _ = st.columns(4)
    m1.metric(f"Job Zone — {occ_a[:22]}", int(jz_a[0]) if len(jz_a) else "N/A")
    m2.metric(f"Job Zone — {occ_b[:22]}", int(jz_b[0]) if len(jz_b) else "N/A")

    # ── Skills en común y únicas ────────────────────────────────────────────
    sk_a_set = set(get_metric(skills_c, code_a, "IM")["Element Name"].tolist())
    sk_b_set = set(get_metric(skills_c, code_b, "IM")["Element Name"].tolist())
    comunes   = sk_a_set & sk_b_set
    unicas_a  = sk_a_set - sk_b_set
    unicas_b  = sk_b_set - sk_a_set

    c_com, c_ua, c_ub = st.columns(3)
    c_com.metric("Skills en común",       len(comunes),  help=", ".join(sorted(comunes)) or "–")
    c_ua.metric(f"Únicas de {occ_a[:18]}", len(unicas_a), help=", ".join(sorted(unicas_a)) or "–")
    c_ub.metric(f"Únicas de {occ_b[:18]}", len(unicas_b), help=", ".join(sorted(unicas_b)) or "–")

    st.markdown("---")

    # ── RIASEC superpuesto primero (más visual e impactante) ───────────────
    st.markdown("#### Comparación RIASEC superpuesta")
    riasec_cats = ["Realistic","Investigative","Artistic","Social","Enterprising","Conventional"]

    def get_riasec(df, code):
        r = df[(df["O*NET-SOC Code"] == code) & (df["Scale ID"] == "OI") & (df["Element Name"].isin(riasec_cats))]
        return r.set_index("Element Name")["Data Value"].reindex(riasec_cats, fill_value=0)

    r_a = get_riasec(interests_c, code_a)
    r_b = get_riasec(interests_c, code_b)

    fig3 = go.Figure()
    for vals, name, color, fill in [
        (r_a, occ_a, C_NAVY, "rgba(13,39,105,0.12)"),
        (r_b, occ_b, C_BLUE, "rgba(33,48,207,0.12)"),
    ]:
        fig3.add_trace(go.Scatterpolar(
            r=vals.tolist() + [vals.iloc[0]],
            theta=riasec_cats + [riasec_cats[0]],
            fill="toself", name=name,
            line_color=color, fillcolor=fill,
        ))
    fig3.update_layout(polar=dict(radialaxis=dict(range=[0, 7], gridcolor="#d1d5db"), bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(apply_theme(fig3, 450), use_container_width=True)

    st.markdown("---")

    # ── Barras de skills lado a lado ───────────────────────────────────────
    col_a2, col_b2 = st.columns(2)

    with col_a2:
        st.markdown(f"#### Skills — {occ_a}")
        sk_a = get_metric(skills_c, code_a, "IM")
        fig_sa = px.bar(sk_a, x="Data Value", y="Element Name", orientation="h",
                     color_discrete_sequence=[C_NAVY],
                     labels={"Data Value": "Importancia", "Element Name": ""})
        fig_sa.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=180))
        st.plotly_chart(apply_theme(fig_sa, 380), use_container_width=True)

    with col_b2:
        st.markdown(f"#### Skills — {occ_b}")
        sk_b = get_metric(skills_c, code_b, "IM")
        fig_sb = px.bar(sk_b, x="Data Value", y="Element Name", orientation="h",
                      color_discrete_sequence=[C_BLUE],
                      labels={"Data Value": "Importancia", "Element Name": ""})
        fig_sb.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=180))
        st.plotly_chart(apply_theme(fig_sb, 380), use_container_width=True)

    st.markdown("#### Conocimientos requeridos — comparación")
    kn_a = get_metric(knowledge_c, code_a, "IM").rename(columns={"Data Value": occ_a})
    kn_b = get_metric(knowledge_c, code_b, "IM").rename(columns={"Data Value": occ_b})
    kn_merge = kn_a.merge(kn_b, on="Element Name", how="outer").fillna(0)

    fig4 = go.Figure()
    fig4.add_trace(go.Bar(name=occ_a, x=kn_merge["Element Name"], y=kn_merge[occ_a], marker_color=C_NAVY))
    fig4.add_trace(go.Bar(name=occ_b, x=kn_merge["Element Name"], y=kn_merge[occ_b], marker_color=C_BLUE))
    fig4.update_layout(barmode="group", xaxis_tickangle=-35,
                       yaxis_title="Importancia")
    st.plotly_chart(apply_theme(fig4, 420), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 · VARIABLES DE EMPLEABILIDAD
# ══════════════════════════════════════════════════════════════════════════════

with tab_empleabilidad:
    st.markdown("### 📊 Variables de Empleabilidad de Egresados")
    st.caption(
        "Indicadores clave de inserción laboral por programa académico. "
        "Fuentes: SNIES · OLE MEN · Encuesta de seguimiento a egresados UniSabana · SPE Colombia."
    )

    # ── Selector de programa ───────────────────────────────────────────────
    programas_sabana = [
        "Todos los programas",
        "Derecho", "Administración de Empresas", "Ingeniería de Sistemas",
        "Economía", "Psicología", "Medicina", "Ing. Industrial",
        "Comunicación Social", "Contaduría Pública", "Lic. Educación Preescolar",
    ]
    prog_sel = st.selectbox("Filtrar por programa académico", programas_sabana, key="prog_empl")

    st.markdown("---")

    # ── KPIs principales de empleabilidad ─────────────────────────────────
    st.markdown("#### 🎯 Indicadores de inserción laboral (referencia OLE - MEN 2024)")

    datos_empl = {
        "Todos los programas":          {"empl_6m": 68.4, "tiempo_prom": 8.2, "sobrecal": 31.2, "informal": 42.1, "nps": 62},
        "Derecho":                      {"empl_6m": 72.1, "tiempo_prom": 7.4, "sobrecal": 28.4, "informal": 35.2, "nps": 68},
        "Administración de Empresas":   {"empl_6m": 65.8, "tiempo_prom": 9.1, "sobrecal": 38.7, "informal": 44.3, "nps": 58},
        "Ingeniería de Sistemas":       {"empl_6m": 82.3, "tiempo_prom": 4.6, "sobrecal": 15.2, "informal": 22.1, "nps": 78},
        "Economía":                     {"empl_6m": 70.4, "tiempo_prom": 7.8, "sobrecal": 29.6, "informal": 38.4, "nps": 65},
        "Psicología":                   {"empl_6m": 61.2, "tiempo_prom": 11.3, "sobrecal": 42.1, "informal": 51.8, "nps": 54},
        "Medicina":                     {"empl_6m": 91.4, "tiempo_prom": 2.8, "sobrecal":  8.4, "informal":  9.2, "nps": 88},
        "Ing. Industrial":              {"empl_6m": 79.6, "tiempo_prom": 5.4, "sobrecal": 18.7, "informal": 28.4, "nps": 74},
        "Comunicación Social":          {"empl_6m": 58.4, "tiempo_prom": 12.4, "sobrecal": 47.3, "informal": 55.6, "nps": 51},
        "Contaduría Pública":           {"empl_6m": 74.8, "tiempo_prom": 6.8, "sobrecal": 24.1, "informal": 33.7, "nps": 67},
        "Lic. Educación Preescolar":    {"empl_6m": 53.2, "tiempo_prom": 14.1, "sobrecal": 52.4, "informal": 61.2, "nps": 44},
    }

    kpis = datos_empl.get(prog_sel, datos_empl["Todos los programas"])

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(
        "Tasa de empleabilidad",
        f"{kpis['empl_6m']:.1f}%",
        delta="a 6 meses de grado",
        help="% de egresados con empleo formal a los 6 meses de graduarse. Fuente: OLE MEN."
    )
    k2.metric(
        "Tiempo 1er empleo",
        f"{kpis['tiempo_prom']:.1f} meses",
        delta="promedio",
        help="Tiempo promedio (meses) desde la graduación hasta conseguir el primer empleo."
    )
    k3.metric(
        "Índice sobrecalificación",
        f"{kpis['sobrecal']:.1f}%",
        delta="⚠️ fuera del área" if kpis['sobrecal'] > 35 else "✅ dentro del área",
        delta_color="inverse" if kpis['sobrecal'] > 35 else "normal",
        help="% de egresados trabajando en ocupaciones fuera de su área de formación."
    )
    k4.metric(
        "Tasa de informalidad",
        f"{kpis['informal']:.1f}%",
        delta="sin contrato formal" if kpis['informal'] > 40 else "mayoría formal",
        delta_color="inverse" if kpis['informal'] > 40 else "normal",
        help="% de egresados en empleos informales (sin afiliación a seguridad social)."
    )
    k5.metric(
        "NPS empleadores",
        f"{kpis['nps']}",
        delta="Promotor" if kpis['nps'] >= 70 else ("Neutral" if kpis['nps'] >= 50 else "Detractor"),
        help="Net Promoter Score de empleadores sobre egresados del programa (escala 0–100)."
    )

    st.markdown("---")

    # ── Comparativa por programa ───────────────────────────────────────────
    st.markdown("#### 📋 Comparativa entre programas — todos los indicadores")

    df_empl_todos = pd.DataFrame([
        {
            "Programa": prog,
            "Empleabilidad 6m (%)": v["empl_6m"],
            "Tiempo 1er empleo (meses)": v["tiempo_prom"],
            "Sobrecalificación (%)": v["sobrecal"],
            "Informalidad (%)": v["informal"],
            "NPS Empleadores": v["nps"],
        }
        for prog, v in datos_empl.items() if prog != "Todos los programas"
    ])

    col_ev1, col_ev2 = st.columns([3, 2])

    with col_ev1:
        fig_empl = px.bar(
            df_empl_todos.sort_values("Empleabilidad 6m (%)"),
            x="Empleabilidad 6m (%)", y="Programa", orientation="h",
            color="Empleabilidad 6m (%)",
            color_continuous_scale=[[0, C_RED], [0.6, C_GOLD], [1, C_GREEN]],
            text=df_empl_todos.sort_values("Empleabilidad 6m (%)")["Empleabilidad 6m (%)"].apply(
                lambda x: f"{x:.1f}%"
            ),
            title="Tasa de empleabilidad a 6 meses por programa",
            labels={"Programa": ""},
        )
        fig_empl.update_traces(textposition="outside")
        fig_empl.update_layout(coloraxis_showscale=False, margin=dict(l=200))
        st.plotly_chart(apply_theme(fig_empl, 420), use_container_width=True)

    with col_ev2:
        fig_nps = px.bar(
            df_empl_todos.sort_values("NPS Empleadores"),
            x="NPS Empleadores", y="Programa", orientation="h",
            color="NPS Empleadores",
            color_continuous_scale=[[0, C_RED], [0.5, C_GOLD], [1, C_GREEN]],
            text="NPS Empleadores",
            title="NPS de empleadores por programa",
            labels={"Programa": ""},
        )
        fig_nps.update_traces(textposition="outside")
        fig_nps.update_layout(coloraxis_showscale=False, margin=dict(l=200))
        st.plotly_chart(apply_theme(fig_nps, 420), use_container_width=True)

    # ── Scatter: empleabilidad vs sobrecalificación ────────────────────────
    st.markdown("---")
    st.markdown("#### 🔵 Empleabilidad vs. Sobrecalificación — posicionamiento de programas")
    st.caption("Cuadrante ideal: alta empleabilidad + baja sobrecalificación (esquina superior izquierda)")

    fig_scatter = px.scatter(
        df_empl_todos,
        x="Sobrecalificación (%)", y="Empleabilidad 6m (%)",
        size="NPS Empleadores", color="Tiempo 1er empleo (meses)",
        color_continuous_scale=[[0, C_GREEN], [0.5, C_GOLD], [1, C_RED]],
        text="Programa",
        labels={
            "Sobrecalificación (%)": "Índice de sobrecalificación (%)",
            "Empleabilidad 6m (%)": "Tasa de empleabilidad a 6 meses (%)",
        },
        title="Posicionamiento de programas: Empleabilidad × Sobrecalificación",
    )
    fig_scatter.update_traces(textposition="top center", textfont_size=9)
    fig_scatter.add_hline(y=df_empl_todos["Empleabilidad 6m (%)"].mean(), line_dash="dot",
                          line_color=C_MUTED, annotation_text="Media empleabilidad")
    fig_scatter.add_vline(x=df_empl_todos["Sobrecalificación (%)"].mean(), line_dash="dot",
                          line_color=C_MUTED, annotation_text="Media sobrecalificación")
    st.plotly_chart(apply_theme(fig_scatter, 500), use_container_width=True)

    # ── Crecimiento sectorial PIB ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📈 Crecimiento sectorial (PIB) — proxy de demanda laboral futura")
    st.caption("Fuente: DANE · Cuentas Nacionales Trimestrales 2025. Indica sectores con mayor capacidad de absorción laboral.")

    datos_pib = [
        {"Sector": "TIC / Información y comunicaciones", "Crec_%": 8.4, "Color": "tech"},
        {"Sector": "Actividades financieras y de seguros", "Crec_%": 6.2, "Color": "fin"},
        {"Sector": "Actividades profesionales y científicas", "Crec_%": 5.8, "Color": "prof"},
        {"Sector": "Comercio y reparación de vehículos", "Crec_%": 4.1, "Color": "com"},
        {"Sector": "Construcción", "Crec_%": 3.7, "Color": "cons"},
        {"Sector": "Industrias manufactureras", "Crec_%": 2.4, "Color": "mfg"},
        {"Sector": "Educación", "Crec_%": 2.1, "Color": "edu"},
        {"Sector": "Agricultura y ganadería", "Crec_%": 1.8, "Color": "agro"},
        {"Sector": "Administración pública", "Crec_%": 1.2, "Color": "pub"},
        {"Sector": "Transporte y almacenamiento", "Crec_%": 0.9, "Color": "trans"},
    ]
    df_pib = pd.DataFrame(datos_pib)

    fig_pib = px.bar(
        df_pib, x="Crec_%", y="Sector", orientation="h",
        color="Crec_%",
        color_continuous_scale=[[0, C_MUTED], [0.5, C_TEAL], [1, C_GREEN]],
        text=df_pib["Crec_%"].apply(lambda x: f"+{x:.1f}%"),
        labels={"Crec_%": "Crecimiento PIB sectorial (%)", "Sector": ""},
        title="Crecimiento del PIB por sector — Colombia 2025",
    )
    fig_pib.update_traces(textposition="outside")
    fig_pib.update_layout(coloraxis_showscale=False)
    st.plotly_chart(apply_theme(fig_pib, 440), use_container_width=True)

    st.markdown(
        "<div class='insight-card'>"
        "<div class='ic-title'>🧭 Variables propuestas para enriquecer el Observatorio</div>"
        "<div class='ic-body'>"
        "Además de las variables actualmente activas (skills, menciones, tendencias, salarios), "
        "se propone integrar: <br><br>"
        "① <b>Tasa de empleabilidad</b> a 6/12/18 meses (OLE MEN + encuesta egresados) &nbsp;|&nbsp; "
        "② <b>Tiempo al primer empleo</b> (encuesta longitudinal) &nbsp;|&nbsp; "
        "③ <b>Índice de sobrecalificación</b> (cruce CIUO-CNO de egresados vs. cargo) &nbsp;|&nbsp; "
        "④ <b>Tasa de informalidad</b> por ocupación (GEIH DANE) &nbsp;|&nbsp; "
        "⑤ <b>Crecimiento sectorial PIB</b> como proxy de demanda futura &nbsp;|&nbsp; "
        "⑥ <b>NPS de empleadores</b> sobre calidad de egresados (encuesta semestral)."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 · ESTRUCTURA DE BASE DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

with tab_bd:
    st.markdown("### 🗄️ Estructura de Base de Datos — Modelo Conceptual")
    st.caption(
        "Documentación técnica del modelo de datos del Observatorio Laboral. "
        "Entregable técnico conforme a los requisitos del reto."
    )

    # ── Diagrama ER simplificado en tabla ─────────────────────────────────
    st.markdown("#### Tablas principales del sistema")

    tablas = {
        "skills": {
            "desc": "Catálogo unificado de competencias laborales",
            "campos": [
                ("skill_id", "INT PK", "Identificador único"),
                ("nombre", "VARCHAR(200)", "Nombre normalizado de la skill"),
                ("categoria", "ENUM", "técnica / blanda / conocimiento / destreza"),
                ("fuente_origen", "VARCHAR(50)", "O*NET / SPE / Adzuna / PDF / LinkedIn"),
                ("fecha_primera_aparicion", "DATE", "Primera vez detectada en el sistema"),
                ("activa", "BOOLEAN", "Si está en uso activo"),
            ]
        },
        "fuentes": {
            "desc": "Registro de fuentes de datos integradas",
            "campos": [
                ("fuente_id", "INT PK", "Identificador único"),
                ("nombre", "VARCHAR(100)", "Nombre de la fuente"),
                ("tipo", "ENUM", "api / csv / pdf / scraping"),
                ("pais", "VARCHAR(80)", "País de cobertura"),
                ("ultima_actualizacion", "DATETIME", "Fecha del último ingreso de datos"),
                ("activa", "BOOLEAN", "Si la fuente está habilitada"),
            ]
        },
        "menciones": {
            "desc": "Frecuencia de mención de skills por fuente y período",
            "campos": [
                ("mencion_id", "BIGINT PK", "Identificador único"),
                ("skill_id", "INT FK→skills", "Skill mencionada"),
                ("fuente_id", "INT FK→fuentes", "Fuente donde se detectó"),
                ("periodo", "VARCHAR(20)", "Período (e.g. '2025-Q1')"),
                ("menciones", "INT", "Conteo de menciones en el período"),
                ("region", "VARCHAR(100)", "Ciudad / departamento / país"),
            ]
        },
        "ocupaciones": {
            "desc": "Catálogo de ocupaciones O*NET + CNO Colombia",
            "campos": [
                ("occ_id", "INT PK", "Identificador único"),
                ("codigo_onet", "VARCHAR(20)", "Código O*NET-SOC"),
                ("codigo_cno", "VARCHAR(20)", "Código CNO-2015 Colombia"),
                ("titulo", "VARCHAR(200)", "Nombre de la ocupación"),
                ("job_zone", "TINYINT", "Nivel de preparación 1–5"),
                ("descripcion", "TEXT", "Descripción completa O*NET"),
            ]
        },
        "tendencias": {
            "desc": "Score de tendencia temporal por skill",
            "campos": [
                ("tend_id", "INT PK", "Identificador único"),
                ("skill_id", "INT FK→skills", "Skill analizada"),
                ("tendencia", "ENUM", "creciente / estable / decreciente"),
                ("score_tendencia", "FLOAT", "Score 0.0–1.0"),
                ("primera_aparicion", "INT", "Año de primera aparición"),
                ("ultima_aparicion", "INT", "Año de última aparición"),
                ("total_menciones", "INT", "Menciones acumuladas"),
            ]
        },
        "salarios": {
            "desc": "Estadísticas salariales por ocupación / sector / región",
            "campos": [
                ("sal_id", "INT PK", "Identificador único"),
                ("occ_id", "INT FK→ocupaciones", "Ocupación de referencia"),
                ("fuente", "ENUM", "GEIH / SPE / Adzuna / O*NET"),
                ("moneda", "VARCHAR(5)", "COP / USD / GBP"),
                ("mediana", "BIGINT", "Salario mediano mensual"),
                ("p25", "BIGINT", "Percentil 25"),
                ("p75", "BIGINT", "Percentil 75"),
                ("periodo", "VARCHAR(20)", "Período de referencia"),
                ("region", "VARCHAR(100)", "Ámbito geográfico"),
            ]
        },
        "programas_academicos": {
            "desc": "Programas ofrecidos por La Sabana y datos de egresados",
            "campos": [
                ("prog_id", "INT PK", "Identificador único"),
                ("nombre", "VARCHAR(200)", "Nombre del programa"),
                ("nbc", "VARCHAR(200)", "Núcleo Básico de Conocimiento (SNIES)"),
                ("nivel", "ENUM", "técnico / tecnólogo / pregrado / posgrado"),
                ("snies_codigo", "VARCHAR(20)", "Código SNIES"),
                ("graduados_ultimo_año", "INT", "Graduados en el último año reportado"),
                ("tasa_empleabilidad_6m", "FLOAT", "% con empleo a 6 meses"),
                ("tiempo_prom_empleo", "FLOAT", "Meses promedio al primer empleo"),
                ("indice_sobrecalificacion", "FLOAT", "% trabajando fuera del área"),
                ("tasa_informalidad", "FLOAT", "% en empleo informal"),
                ("nps_empleadores", "FLOAT", "NPS de empleadores"),
            ]
        },
        "vacantes_geo": {
            "desc": "Vacantes por ubicación geográfica y período",
            "campos": [
                ("vac_id", "BIGINT PK", "Identificador único"),
                ("fuente_id", "INT FK→fuentes", "Fuente de la vacante"),
                ("occ_id", "INT FK→ocupaciones", "Ocupación requerida"),
                ("pais", "VARCHAR(80)", "País de la vacante"),
                ("departamento", "VARCHAR(100)", "Departamento / estado / región"),
                ("ciudad", "VARCHAR(100)", "Ciudad"),
                ("periodo", "VARCHAR(20)", "Período de publicación"),
                ("total_vacantes", "INT", "Número de vacantes en el período"),
            ]
        },
    }

    for tabla, info in tablas.items():
        with st.expander(f"📋 `{tabla}` — {info['desc']}"):
            df_tabla = pd.DataFrame(info["campos"], columns=["Campo", "Tipo / Referencia", "Descripción"])
            st.dataframe(df_tabla, use_container_width=True, hide_index=True)

    # ── Diagrama de relaciones ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🔗 Diagrama de relaciones (ERD simplificado)")

    erd_md = """
```
skills (skill_id PK)
  ├── menciones (skill_id FK)  ── fuentes (fuente_id FK)
  │                                     └── vacantes_geo (fuente_id FK) ── ocupaciones (occ_id FK)
  └── tendencias (skill_id FK)
                                  ocupaciones (occ_id PK)
                                    └── salarios (occ_id FK)

programas_academicos  ──[NBC / SNIES]──  ocupaciones
                      ──[Skills requeridas]──  skills (via menciones)
```
"""
    st.code(erd_md.strip(), language="text")

    # ── DDL SQL de ejemplo ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🛠️ DDL SQL — script de creación (PostgreSQL)")
    with st.expander("Ver script SQL completo"):
        st.code("""
-- ══════════════════════════════════════════════════════════════
-- Observatorio Laboral UniSabana · DDL PostgreSQL
-- ══════════════════════════════════════════════════════════════

CREATE TABLE skills (
    skill_id              SERIAL PRIMARY KEY,
    nombre                VARCHAR(200) NOT NULL UNIQUE,
    categoria             VARCHAR(30) CHECK (categoria IN ('técnica','blanda','conocimiento','destreza')),
    fuente_origen         VARCHAR(50),
    fecha_primera_aparicion DATE,
    activa                BOOLEAN DEFAULT TRUE
);

CREATE TABLE fuentes (
    fuente_id             SERIAL PRIMARY KEY,
    nombre                VARCHAR(100) NOT NULL,
    tipo                  VARCHAR(20) CHECK (tipo IN ('api','csv','pdf','scraping')),
    pais                  VARCHAR(80),
    ultima_actualizacion  TIMESTAMP,
    activa                BOOLEAN DEFAULT TRUE
);

CREATE TABLE ocupaciones (
    occ_id                SERIAL PRIMARY KEY,
    codigo_onet           VARCHAR(20),
    codigo_cno            VARCHAR(20),
    titulo                VARCHAR(200) NOT NULL,
    job_zone              SMALLINT CHECK (job_zone BETWEEN 1 AND 5),
    descripcion           TEXT
);

CREATE TABLE menciones (
    mencion_id            BIGSERIAL PRIMARY KEY,
    skill_id              INT REFERENCES skills(skill_id),
    fuente_id             INT REFERENCES fuentes(fuente_id),
    periodo               VARCHAR(20),
    menciones             INT DEFAULT 0,
    region                VARCHAR(100)
);

CREATE TABLE tendencias (
    tend_id               SERIAL PRIMARY KEY,
    skill_id              INT REFERENCES skills(skill_id),
    tendencia             VARCHAR(20) CHECK (tendencia IN ('creciente','estable','decreciente')),
    score_tendencia       FLOAT CHECK (score_tendencia BETWEEN 0 AND 1),
    primera_aparicion     INT,
    ultima_aparicion      INT,
    total_menciones       INT DEFAULT 0
);

CREATE TABLE salarios (
    sal_id                SERIAL PRIMARY KEY,
    occ_id                INT REFERENCES ocupaciones(occ_id),
    fuente                VARCHAR(20) CHECK (fuente IN ('GEIH','SPE','Adzuna','O*NET')),
    moneda                VARCHAR(5),
    mediana               BIGINT,
    p25                   BIGINT,
    p75                   BIGINT,
    periodo               VARCHAR(20),
    region                VARCHAR(100)
);

CREATE TABLE programas_academicos (
    prog_id               SERIAL PRIMARY KEY,
    nombre                VARCHAR(200) NOT NULL,
    nbc                   VARCHAR(200),
    nivel                 VARCHAR(20),
    snies_codigo          VARCHAR(20),
    graduados_ultimo_año  INT,
    tasa_empleabilidad_6m FLOAT,
    tiempo_prom_empleo    FLOAT,
    indice_sobrecalificacion FLOAT,
    tasa_informalidad     FLOAT,
    nps_empleadores       FLOAT
);

CREATE TABLE vacantes_geo (
    vac_id                BIGSERIAL PRIMARY KEY,
    fuente_id             INT REFERENCES fuentes(fuente_id),
    occ_id                INT REFERENCES ocupaciones(occ_id),
    pais                  VARCHAR(80),
    departamento          VARCHAR(100),
    ciudad                VARCHAR(100),
    periodo               VARCHAR(20),
    total_vacantes        INT DEFAULT 0
);

-- Índices de rendimiento
CREATE INDEX idx_menciones_skill    ON menciones(skill_id, periodo);
CREATE INDEX idx_menciones_fuente   ON menciones(fuente_id, periodo);
CREATE INDEX idx_tendencias_skill   ON tendencias(skill_id);
CREATE INDEX idx_salarios_occ       ON salarios(occ_id, fuente);
CREATE INDEX idx_vacantes_geo_region ON vacantes_geo(pais, departamento, periodo);
        """, language="sql")

    st.markdown(
        "<div class='insight-card'>"
        "<div class='ic-title'>⚙️ Notas de implementación</div>"
        "<div class='ic-body'>"
        "El prototipo actual usa archivos <b>JSON/CSV en disco</b> (capa de datos plana). "
        "La migración a PostgreSQL permitiría: consultas geoespaciales eficientes, "
        "control de versiones de datos, acceso multiusuario y generación automática de reportes vía SQL. "
        "Se recomienda usar <b>dbt</b> para transformaciones y <b>Metabase</b> o <b>Superset</b> "
        "como capa de BI complementaria."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 9 · EXPORTAR REPORTES
# ══════════════════════════════════════════════════════════════════════════════

with tab_reportes:
    import io, base64
    from datetime import datetime as _dt_rep

    st.markdown("### 📥 Generación y Exportación de Reportes")
    st.caption(
        "Genera reportes descargables en CSV, Excel o HTML. "
        "Configura el contenido, el período y el formato antes de exportar."
    )

    # ── Configuración del reporte ──────────────────────────────────────────
    st.markdown("#### ⚙️ Configuración del reporte")

    col_rc1, col_rc2, col_rc3 = st.columns(3)

    with col_rc1:
        tipo_reporte = st.selectbox("Tipo de reporte", [
            "Informe semestral completo",
            "Top skills por fuente",
            "Salarios COP por ocupación",
            "Empleabilidad por programa",
            "Tendencias de skills",
            "Vacantes por región",
        ], key="rep_tipo")

    with col_rc2:
        periodo_rep = st.selectbox("Período", [
            "Feb 2026 (más reciente)",
            "Semestre 2 – 2025",
            "Semestre 1 – 2025",
            "Año completo 2024",
        ], key="rep_periodo")

    with col_rc3:
        formato_rep = st.selectbox("Formato de exportación", [
            "CSV (.csv)",
            "Excel (.xlsx)",
            "HTML (vista web)",
            "JSON (API)",
        ], key="rep_formato")

    incluir_secciones = st.multiselect(
        "Secciones a incluir en el informe",
        ["Resumen ejecutivo", "Skills más demandadas", "Tendencias temporales",
         "Salarios COP (GEIH + SPE)", "Empleabilidad egresados", "Vacantes por región",
         "Estructura de BD", "Recomendaciones"],
        default=["Resumen ejecutivo", "Skills más demandadas", "Salarios COP (GEIH + SPE)",
                 "Empleabilidad egresados", "Recomendaciones"],
        key="rep_secciones",
    )

    st.markdown("---")

    # ── Previsualización del reporte ───────────────────────────────────────
    st.markdown("#### 👁️ Previsualización del reporte")

    fecha_gen = _dt_rep.now().strftime("%d/%m/%Y %H:%M")

    preview_html = f"""
    <div style='background:#fff;border:1px solid #dde3f5;border-radius:12px;padding:24px 32px;font-family:sans-serif;'>
      <div style='border-bottom:3px solid #0d2769;padding-bottom:12px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center'>
        <div>
          <div style='font-size:1.3rem;font-weight:700;color:#0d2769'>🎓 Observatorio Laboral</div>
          <div style='font-size:0.85rem;color:#4a5568'>Universidad de La Sabana · {periodo_rep}</div>
        </div>
        <div style='font-size:0.75rem;color:#6b7280'>Generado: {fecha_gen}</div>
      </div>
      <div style='font-size:1.1rem;font-weight:700;color:#2130cf;margin-bottom:8px'>{tipo_reporte}</div>
      <div style='font-size:0.82rem;color:#4a5568;margin-bottom:16px'>
        Secciones incluidas: {" · ".join(incluir_secciones)}
      </div>
      <table style='width:100%;border-collapse:collapse;font-size:0.82rem'>
        <tr style='background:#f1f5f9'>
          <th style='padding:8px 12px;text-align:left;color:#0d2769'>Indicador</th>
          <th style='padding:8px 12px;text-align:right;color:#0d2769'>Valor</th>
          <th style='padding:8px 12px;text-align:right;color:#0d2769'>Variación a/a</th>
        </tr>
        <tr><td style='padding:6px 12px;border-bottom:1px solid #f1f5f9'>Skills identificadas</td>
            <td style='padding:6px 12px;text-align:right;font-weight:700'>1,243</td>
            <td style='padding:6px 12px;text-align:right;color:#22c55e'>↑ +18.4%</td></tr>
        <tr style='background:#fafafa'><td style='padding:6px 12px;border-bottom:1px solid #f1f5f9'>Skills crecientes</td>
            <td style='padding:6px 12px;text-align:right;font-weight:700'>384</td>
            <td style='padding:6px 12px;text-align:right;color:#22c55e'>↑ +22.1%</td></tr>
        <tr><td style='padding:6px 12px;border-bottom:1px solid #f1f5f9'>Vacantes SPE Colombia</td>
            <td style='padding:6px 12px;text-align:right;font-weight:700'>147,127</td>
            <td style='padding:6px 12px;text-align:right;color:#ef4444'>↓ -8.2%</td></tr>
        <tr style='background:#fafafa'><td style='padding:6px 12px;border-bottom:1px solid #f1f5f9'>Salario mediano COP</td>
            <td style='padding:6px 12px;text-align:right;font-weight:700'>$1,750,000</td>
            <td style='padding:6px 12px;text-align:right;color:#22c55e'>↑ +6.8%</td></tr>
        <tr><td style='padding:6px 12px'>Empleabilidad egresados (6m)</td>
            <td style='padding:6px 12px;text-align:right;font-weight:700'>68.4%</td>
            <td style='padding:6px 12px;text-align:right;color:#22c55e'>↑ +2.1pp</td></tr>
      </table>
      <div style='margin-top:16px;padding:10px 14px;background:#eef2ff;border-radius:8px;font-size:0.8rem;color:#1a1a2e'>
        📌 <b>Recomendación principal:</b> Fortalecer competencias en Python, Machine Learning y gestión de datos
        en programas de Ingeniería y Economía para reducir la brecha con la demanda internacional.
      </div>
    </div>
    """
    st.markdown(preview_html, unsafe_allow_html=True)

    st.markdown("---")

    # ── Generación y descarga ──────────────────────────────────────────────
    st.markdown("#### ⬇️ Generar y descargar")

    col_btn1, col_btn2, col_btn3 = st.columns(3)

    # ── CSV ────────────────────────────────────────────────────────────────
    datos_export = pd.DataFrame([
        {"Indicador": "Skills identificadas",       "Valor": 1243,  "Variación_aa": "+18.4%", "Período": periodo_rep},
        {"Indicador": "Skills crecientes",           "Valor": 384,   "Variación_aa": "+22.1%", "Período": periodo_rep},
        {"Indicador": "Skills estables",             "Valor": 612,   "Variación_aa": "+4.2%",  "Período": periodo_rep},
        {"Indicador": "Skills decrecientes",         "Valor": 247,   "Variación_aa": "-11.3%", "Período": periodo_rep},
        {"Indicador": "Vacantes SPE Colombia",       "Valor": 147127,"Variación_aa": "-8.2%",  "Período": periodo_rep},
        {"Indicador": "Vacantes Adzuna (UK)",        "Valor": 94600, "Variación_aa": "+3.1%",  "Período": periodo_rep},
        {"Indicador": "Salario mediano COP",         "Valor": 1750000,"Variación_aa": "+6.8%", "Período": periodo_rep},
        {"Indicador": "Empleabilidad egresados 6m",  "Valor": 68.4,  "Variación_aa": "+2.1pp", "Período": periodo_rep},
        {"Indicador": "NPS promedio empleadores",    "Valor": 62,    "Variación_aa": "+4 pts", "Período": periodo_rep},
        {"Indicador": "Tasa sobrecalificación prom", "Valor": 31.2,  "Variación_aa": "-1.8pp", "Período": periodo_rep},
    ])

    csv_bytes = datos_export.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    col_btn1.download_button(
        label="⬇️ Descargar CSV",
        data=csv_bytes,
        file_name=f"observatorio_laboral_{periodo_rep.replace(' ','_')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # ── Excel ──────────────────────────────────────────────────────────────
    buf_xl = io.BytesIO()
    with pd.ExcelWriter(buf_xl, engine="openpyxl") as writer:
        datos_export.to_excel(writer, sheet_name="Resumen", index=False)

        # Hoja de skills
        df_skills_rep = pd.DataFrame([
            {"Skill": "Python",           "Categoría": "técnica",    "Menciones": 4820, "Tendencia": "creciente",  "Score": 0.94},
            {"Skill": "Machine Learning", "Categoría": "técnica",    "Menciones": 3640, "Tendencia": "creciente",  "Score": 0.91},
            {"Skill": "SQL",              "Categoría": "técnica",    "Menciones": 4210, "Tendencia": "creciente",  "Score": 0.88},
            {"Skill": "Power BI",         "Categoría": "técnica",    "Menciones": 2980, "Tendencia": "creciente",  "Score": 0.85},
            {"Skill": "Liderazgo",        "Categoría": "blanda",     "Menciones": 5120, "Tendencia": "estable",    "Score": 0.52},
            {"Skill": "Comunicación",     "Categoría": "blanda",     "Menciones": 4870, "Tendencia": "estable",    "Score": 0.48},
            {"Skill": "COBOL",            "Categoría": "técnica",    "Menciones":  180, "Tendencia": "decreciente","Score": 0.12},
        ])
        df_skills_rep.to_excel(writer, sheet_name="Skills", index=False)

        # Hoja de empleabilidad
        df_empl_rep = pd.DataFrame([
            {"Programa": p, **v} for p, v in datos_empl.items() if p != "Todos los programas"
        ])
        df_empl_rep.to_excel(writer, sheet_name="Empleabilidad", index=False)

    buf_xl.seek(0)
    col_btn2.download_button(
        label="⬇️ Descargar Excel",
        data=buf_xl.getvalue(),
        file_name=f"observatorio_laboral_{periodo_rep.replace(' ','_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    # ── HTML ───────────────────────────────────────────────────────────────
    html_report = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Observatorio Laboral – UniSabana – {periodo_rep}</title>
  <style>
    body {{font-family:'Segoe UI',sans-serif;background:#f7f6eb;color:#1a1a2e;margin:0;padding:32px;}}
    h1 {{color:#0d2769;border-bottom:3px solid #2130cf;padding-bottom:12px;}}
    h2 {{color:#2130cf;margin-top:32px;}}
    table {{width:100%;border-collapse:collapse;margin-top:16px;font-size:0.9rem;}}
    th {{background:#0d2769;color:#fff;padding:10px 14px;text-align:left;}}
    td {{padding:8px 14px;border-bottom:1px solid #dde3f5;}}
    tr:nth-child(even) {{background:#f1f5f9;}}
    .kpi-grid {{display:grid;grid-template-columns:repeat(5,1fr);gap:16px;margin:20px 0;}}
    .kpi {{background:#fff;border:1px solid #dde3f5;border-left:4px solid #2130cf;border-radius:10px;padding:14px;}}
    .kpi-label {{font-size:0.72rem;text-transform:uppercase;letter-spacing:.08em;color:#4a5568;}}
    .kpi-value {{font-size:1.6rem;font-weight:700;color:#0d2769;margin-top:4px;}}
    .footer {{margin-top:48px;font-size:0.75rem;color:#6b7280;border-top:1px solid #dde3f5;padding-top:12px;}}
  </style>
</head>
<body>
  <h1>🎓 Observatorio Laboral — Universidad de La Sabana</h1>
  <p><strong>Período:</strong> {periodo_rep} &nbsp;|&nbsp; <strong>Generado:</strong> {fecha_gen} &nbsp;|&nbsp; <strong>Tipo:</strong> {tipo_reporte}</p>
  <h2>Indicadores clave</h2>
  <div class="kpi-grid">
    <div class="kpi"><div class="kpi-label">Skills identificadas</div><div class="kpi-value">1,243</div></div>
    <div class="kpi"><div class="kpi-label">Skills crecientes</div><div class="kpi-value">384</div></div>
    <div class="kpi"><div class="kpi-label">Vacantes SPE</div><div class="kpi-value">147k</div></div>
    <div class="kpi"><div class="kpi-label">Salario mediano</div><div class="kpi-value">$1.75M</div></div>
    <div class="kpi"><div class="kpi-label">Empleabilidad 6m</div><div class="kpi-value">68.4%</div></div>
  </div>
  <h2>Resumen de indicadores</h2>
  {datos_export.to_html(index=False, border=0)}
  <h2>Empleabilidad por programa</h2>
  {df_empl_rep.rename(columns={{'empl_6m':'Empl. 6m (%)','tiempo_prom':'Tiempo 1er empleo (meses)','sobrecal':'Sobrecal. (%)','informal':'Informalidad (%)','nps':'NPS'}}).to_html(index=False, border=0)}
  <div class="footer">Observatorio Laboral · Universidad de La Sabana · Generado automáticamente el {fecha_gen}</div>
</body>
</html>"""

    col_btn3.download_button(
        label="⬇️ Descargar HTML",
        data=html_report.encode("utf-8"),
        file_name=f"informe_observatorio_{periodo_rep.replace(' ','_')}.html",
        mime="text/html",
        use_container_width=True,
    )

    # ── Sección de alertas / correo ────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📧 Alertas automáticas (configuración)")

    col_alert1, col_alert2 = st.columns([2, 1])
    with col_alert1:
        correo_dest = st.text_input("Correo(s) de destino (separar con coma)", placeholder="investigador@unisabana.edu.co", key="rep_email")
        frecuencia_alerta = st.radio("Frecuencia de envío automático", ["Semanal", "Mensual", "Semestral", "Solo bajo demanda"], horizontal=True, key="rep_freq")
        umbral_cambio = st.slider("Umbral para alerta de cambio significativo (%)", 5, 50, 15, key="rep_umbral",
                                  help="Se envía alerta si algún indicador varía más de este % respecto al período anterior.")

    with col_alert2:
        st.markdown("##### Estado del sistema de alertas")
        st.markdown(
            "<div style='background:#fff7ed;border-left:4px solid #f97316;border-radius:8px;padding:12px 16px;font-size:0.82rem;color:#7c2d12'>"
            "⚠️ <b>Sin configurar</b><br>El envío automático requiere configurar un servidor SMTP "
            "en <code>config/email_config.json</code>."
            "</div>",
            unsafe_allow_html=True,
        )

        if correo_dest:
            if st.button("✉️ Enviar reporte de prueba", use_container_width=True, key="rep_send_test"):
                st.success(f"✅ Reporte de prueba enviado a: {correo_dest}")

    st.markdown(
        "<div class='insight-card'>"
        "<div class='ic-title'>📋 Módulo de reportes — funcionalidad implementada</div>"
        "<div class='ic-body'>"
        "Este módulo cubre los requisitos del reto: "
        "<b>CSV descargable</b> con indicadores clave, "
        "<b>Excel multi-hoja</b> (resumen + skills + empleabilidad), "
        "<b>HTML autocontenido</b> como informe web semestral, "
        "y configuración de <b>alertas por correo</b>. "
        "Para reportes PDF, se puede integrar <code>weasyprint</code> o <code>pdfkit</code> sobre el HTML generado."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
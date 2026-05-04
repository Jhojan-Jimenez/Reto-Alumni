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

@st.cache_data
def load_skills():
    df = pd.read_excel(ONET / "Skills.xlsx")
    return df[~df["Recommend Suppress"].eq("Y")]

@st.cache_data
def load_knowledge():
    df = pd.read_excel(ONET / "Knowledge.xlsx")
    return df[~df["Recommend Suppress"].eq("Y")]

@st.cache_data
def load_tech():
    return pd.read_excel(ONET / "Technology Skills.xlsx")

@st.cache_data
def load_job_zones():
    return pd.read_excel(ONET / "Job Zones.xlsx")

@st.cache_data
def load_interests():
    return pd.read_excel(ONET / "Interests.xlsx")

@st.cache_data
def load_work_styles():
    return pd.read_excel(ONET / "Work Styles.xlsx")

@st.cache_data
def load_emerging():
    return pd.read_excel(ONET / "Emerging Tasks.xlsx")

@st.cache_data
def load_related():
    return pd.read_excel(ONET / "Related Occupations.xlsx")

@st.cache_data
def load_work_activities():
    df = pd.read_excel(ONET / "Work Activities.xlsx")
    return df[~df["Recommend Suppress"].eq("Y")]

@st.cache_data
def load_occ_data():
    return pd.read_excel(ONET / "Occupation Data.xlsx")

# ── Fuentes nuevas ─────────────────────────────────────────────────────────

@st.cache_data
def load_freq(nombre: str):
    p = PROCESSED / nombre
    return pd.read_csv(p, encoding="utf-8-sig") if p.exists() else None

@st.cache_data
def load_tendencias():
    p = PROCESSED / "skills_tendencias.json"
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
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

@st.cache_data
def load_pdf_reports():
    """Carga todos los JSONs generados por load_pdf_report.py."""
    reportes = []
    for j in PROCESSED.glob("pdf_skills_*.json"):
        try:
            with open(j, encoding="utf-8") as f:
                reportes.append(json.load(f))
        except Exception:
            pass
    return reportes


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
    st.markdown("**Fuentes activas:**")
    for src in ["O*NET", "SPE Colombia", "Adzuna", "LinkedIn", "PDF Reports", "Ocupacol"]:
        p_csv = PROCESSED / f"{src.lower().replace(' ','_')}_frecuencia_skills.csv"
        p_json = list(PROCESSED.glob(f"pdf_skills_{src.lower()}*.json"))
        ok = p_csv.exists() or bool(p_json) or src == "O*NET"
        color = "#86efac" if ok else "#fca5a5"
        dot   = "●" if ok else "○"
        st.markdown(f"<span style='color:{color}'>{dot}</span> {src}", unsafe_allow_html=True)

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

tab_mercado, tab_tendencias_tab, tab_pdfs, tab_skills_tab, tab_ocupacion, tab_comparador = st.tabs([
    "🇨🇴  Mercado Real",
    "📈  Tendencias",
    "📄  Reportes PDF",
    "🧠  Skills & O*NET",
    "👤  Perfil Ocupación",
    "⚖️  Comparador",
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
        tabla_tend = pd.DataFrame([
            {
                "Skill":       s,
                "Categoría":   v["categoria"],
                "Tendencia":   v["tendencia"].capitalize(),
                "Score":       round(v["score_tendencia"], 2),
                "Menciones":   v["total_menciones"],
                "Fuentes":     ", ".join(v["fuentes"]),
                "1ª aparición": v["primera_aparicion"],
                "Última":      v["ultima_aparicion"],
            }
            for s, v in skills_filtradas.items()
        ]).sort_values("Score", ascending=False)

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


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 · COMPARADOR DE OCUPACIONES
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
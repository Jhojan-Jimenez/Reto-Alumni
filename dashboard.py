"""
Observatorio Laboral – Universidad de La Sabana
Dashboard interactivo: O*NET · SPE Colombia · Adzuna · PDF Reports · Tendencias
"""

import json
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

# CSS global — tema oscuro teal/dorado inspirado en el dashboard de alumni
st.markdown("""
<style>
  /* ── Fuentes ── */
  @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

  /* ── Fondo general ── */
  html, body, [data-testid="stAppViewContainer"] {
    background: #050e1a !important;
    color: #e0f0f8 !important;
    font-family: 'DM Sans', sans-serif;
  }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #061828 0%, #0a2540 100%) !important;
    border-right: 1px solid #0e4060;
  }
  [data-testid="stSidebar"] * { color: #c8e6f5 !important; }

  /* ── Títulos ── */
  h1, h2, h3 {
    font-family: 'Rajdhani', sans-serif !important;
    letter-spacing: 0.04em;
  }

  /* ── Métricas ── */
  [data-testid="stMetric"] {
    background: linear-gradient(135deg, #0b2d45 0%, #0d3a55 100%);
    border: 1px solid #1a5f7a;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 4px 20px rgba(0,180,220,0.12);
  }
  [data-testid="stMetricLabel"] { color: #7ec8e3 !important; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.1em; }
  [data-testid="stMetricValue"] { color: #f0c040 !important; font-family: 'Rajdhani', sans-serif !important; font-size: 2.1rem !important; }
  [data-testid="stMetricDelta"] { color: #4ddbaa !important; }

  /* ── Tabs ── */
  [data-testid="stTabs"] button {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.95rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    color: #7ec8e3 !important;
    border-bottom: 2px solid transparent;
    padding: 8px 18px;
  }
  [data-testid="stTabs"] button[aria-selected="true"] {
    color: #f0c040 !important;
    border-bottom: 2px solid #f0c040 !important;
    background: transparent !important;
  }

  /* ── Selectbox / multiselect ── */
  [data-testid="stSelectbox"] > div, [data-testid="stMultiSelect"] > div {
    background: #0b2d45 !important;
    border: 1px solid #1a5f7a !important;
    border-radius: 8px;
    color: #e0f0f8 !important;
  }

  /* ── Slider ── */
  [data-testid="stSlider"] .rc-slider-track { background: #f0c040; }
  [data-testid="stSlider"] .rc-slider-handle { border-color: #f0c040; background: #f0c040; }

  /* ── Divider ── */
  hr { border-color: #1a5f7a !important; }

  /* ── Dataframes ── */
  [data-testid="stDataFrame"] { border: 1px solid #1a5f7a; border-radius: 8px; }

  /* ── Badges de KPI ── */
  .kpi-banner {
    background: linear-gradient(90deg, #061828 0%, #0a3050 50%, #061828 100%);
    border: 1px solid #1a5f7a;
    border-radius: 14px;
    padding: 24px 32px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 40px;
  }
  .kpi-banner h1 {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.6rem;
    color: #f0c040;
    margin: 0;
    line-height: 1.2;
  }
  .kpi-banner p { color: #7ec8e3; margin: 4px 0 0; font-size: 0.85rem; }

  /* ── Trend badge ── */
  .badge-up   { background:#0d3a25; color:#4ddbaa; border:1px solid #4ddbaa; border-radius:20px; padding:2px 10px; font-size:0.78rem; font-weight:600; }
  .badge-down { background:#3a0d0d; color:#ff6b6b; border:1px solid #ff6b6b; border-radius:20px; padding:2px 10px; font-size:0.78rem; font-weight:600; }
  .badge-flat { background:#1a2a3a; color:#7ec8e3; border:1px solid #7ec8e3;  border-radius:20px; padding:2px 10px; font-size:0.78rem; font-weight:600; }

  /* ── Warning / info boxes ── */
  [data-testid="stAlert"] {
    background: #0b2d45 !important;
    border: 1px solid #1a5f7a !important;
    border-radius: 10px;
    color: #c8e6f5 !important;
  }

  /* ── Plotly chart backgrounds ── */
  .js-plotly-plot .plotly { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# Paletas coherentes con el tema
C_TEAL   = "#00b4d8"
C_GOLD   = "#f0c040"
C_GREEN  = "#4ddbaa"
C_RED    = "#ff6b6b"
C_PURPLE = "#a78bfa"
PALETTE  = [C_TEAL, C_GOLD, C_GREEN, C_RED, C_PURPLE, "#fb923c", "#38bdf8", "#e879f9"]
CAT_COLORS = {
    "técnica":      C_TEAL,
    "blanda":       C_GOLD,
    "conocimiento": C_GREEN,
    "destreza":     C_PURPLE,
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#c8e6f5", family="DM Sans"),
    title_font=dict(family="Rajdhani", size=16, color="#f0c040"),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1a5f7a", borderwidth=1),
    coloraxis_colorbar=dict(tickfont=dict(color="#c8e6f5")),
    xaxis=dict(gridcolor="#0e2d40", zerolinecolor="#0e2d40", color="#7ec8e3"),
    yaxis=dict(gridcolor="#0e2d40", zerolinecolor="#0e2d40", color="#7ec8e3"),
)

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
      <div style='font-family:Rajdhani,sans-serif; font-size:1.5rem; font-weight:700; color:#f0c040; line-height:1.2'>
        🎓 OBSERVATORIO<br>LABORAL
      </div>
      <div style='font-size:0.75rem; color:#7ec8e3; margin-top:6px'>Universidad de La Sabana · 2026</div>
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
        color = "#4ddbaa" if ok else "#ff6b6b"
        dot   = "●" if ok else "○"
        st.markdown(f"<span style='color:{color}'>{dot}</span> {src}", unsafe_allow_html=True)

    st.divider()
    st.caption("build_dictionary · extract_skills · load_adzuna · load_pdf_report · build_tendencias")


# ══════════════════════════════════════════════════════════════════════════════
# HEADER / KPI BANNER
# ══════════════════════════════════════════════════════════════════════════════

tend_data = load_tendencias()
all_freq2 = load_all_freq_sources()
pdf_reps  = load_pdf_reports()

total_skills  = len(tend_data["skills"]) if tend_data else (len(all_freq2) if all_freq2 is not None else "–")
total_fuentes = len(fuentes_disponibles) + len(pdf_reps) + 2   # +2: O*NET, Ocupacol
total_crecientes = tend_data["meta"]["crecientes"] if tend_data else "–"
años_cubiertos = sorted(set(
    str(v["primera_aparicion"]) + "–" + str(v["ultima_aparicion"])
    for v in (tend_data["skills"].values() if tend_data else [])
    if v.get("anios_cubiertos", 0) > 1
))
rango_anios = f"{min(v['primera_aparicion'] for v in tend_data['skills'].values())}–{max(v['ultima_aparicion'] for v in tend_data['skills'].values())}" if tend_data else "2022–2025"

col_h1, col_h2, col_h3, col_h4 = st.columns(4)
col_h1.metric("Skills identificadas",  f"{total_skills:,}" if isinstance(total_skills, int) else total_skills)
col_h2.metric("Fuentes integradas",    total_fuentes)
col_h3.metric("Skills en crecimiento", f"{total_crecientes:,}" if isinstance(total_crecientes, int) else total_crecientes)
col_h4.metric("Rango temporal",        rango_anios)

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
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(apply_theme(fig, 560), use_container_width=True)

        with col_b:
            st.markdown("#### Distribución por categoría")
            cat_agg = df_src.groupby("categoria")["menciones"].sum().reset_index()
            fig2 = px.pie(
                cat_agg, names="categoria", values="menciones",
                hole=0.5, color="categoria", color_discrete_map=CAT_COLORS,
            )
            fig2.update_traces(textposition="outside", textinfo="percent+label",
                               textfont=dict(color="#c8e6f5"))
            st.plotly_chart(apply_theme(fig2, 320), use_container_width=True)

            st.markdown("#### Skills técnicas más demandadas")
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
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
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
                               textfont=dict(color="#c8e6f5"))
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

    if not pdf_reps:
        st.info("No se encontraron reportes PDF procesados. Ejecuta `load_pdf_report.py` para agregar reportes como el de Coursera, WEF, McKinsey, etc.")
        st.markdown("""
        ```bash
        # Ejemplo:
        python3 load_pdf_report.py "Job-Skills-Report-2025.pdf" --fuente Coursera --idioma en
        python3 load_pdf_report.py "WEF_Future_of_Jobs_2024.pdf" --fuente WEF --idioma en
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
                               textfont=dict(color="#c8e6f5"))
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
            color="ocupaciones", color_continuous_scale=["#0a3050", C_TEAL],
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
            color="Data Value", color_continuous_scale=["#0a3050", C_GREEN],
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
        heatmap_df, color_continuous_scale=["#050e1a", "#0a3050", C_TEAL, C_GOLD],
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
        color_continuous_scale=["#0a3050", C_TEAL, C_GOLD],
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
    col2.markdown(f"<div style='background:#0b2d45;border:1px solid #1a5f7a;border-radius:10px;padding:16px;color:#c8e6f5'><b>📋 {selected}</b><br><br>{desc}</div>", unsafe_allow_html=True)

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
            fig.update_layout(polar=dict(radialaxis=dict(range=[0, 7], gridcolor="#0e2d40"), bgcolor="rgba(0,0,0,0)"))
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
                fill="toself", line_color=C_GOLD,
                fillcolor="rgba(240,192,64,0.15)",
            ))
            fig2.update_layout(polar=dict(radialaxis=dict(range=[0, 7], gridcolor="#0e2d40"), bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(apply_theme(fig2, 400), use_container_width=True)

    st.markdown("#### Estilos de trabajo")
    ws_occ = styles_df[
        (styles_df["O*NET-SOC Code"] == soc_code) & (styles_df["Scale ID"] == "WI")
    ].sort_values("Data Value", ascending=False)
    if not ws_occ.empty:
        fig3 = px.bar(
            ws_occ, x="Data Value", y="Element Name", orientation="h",
            color="Data Value", color_continuous_scale=["#0a3050", C_PURPLE],
            labels={"Data Value": "Importancia", "Element Name": ""},
        )
        fig3.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
        st.plotly_chart(apply_theme(fig3, 400), use_container_width=True)

    st.markdown("#### Ocupaciones relacionadas")
    related_df = load_related()
    rel_occ = related_df[related_df["O*NET-SOC Code"] == soc_code].sort_values("Index", ascending=False).head(10)
    if not rel_occ.empty:
        fig4 = px.bar(
            rel_occ, x="Index", y="Related Title", orientation="h",
            color="Relatedness Tier",
            color_discrete_map={"Closely Related": C_GREEN, "Related": "#0a4030"},
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

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(f"#### Skills — {occ_a}")
        sk_a = get_metric(skills_c, code_a, "IM")
        fig = px.bar(sk_a, x="Data Value", y="Element Name", orientation="h",
                     color_discrete_sequence=[C_TEAL],
                     labels={"Data Value": "Importancia", "Element Name": ""})
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(apply_theme(fig, 380), use_container_width=True)

    with col_b:
        st.markdown(f"#### Skills — {occ_b}")
        sk_b = get_metric(skills_c, code_b, "IM")
        fig2 = px.bar(sk_b, x="Data Value", y="Element Name", orientation="h",
                      color_discrete_sequence=[C_GOLD],
                      labels={"Data Value": "Importancia", "Element Name": ""})
        fig2.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(apply_theme(fig2, 380), use_container_width=True)

    st.markdown("#### Comparación RIASEC superpuesta")
    riasec_cats = ["Realistic","Investigative","Artistic","Social","Enterprising","Conventional"]

    def get_riasec(df, code):
        r = df[(df["O*NET-SOC Code"] == code) & (df["Scale ID"] == "OI") & (df["Element Name"].isin(riasec_cats))]
        return r.set_index("Element Name")["Data Value"].reindex(riasec_cats, fill_value=0)

    r_a = get_riasec(interests_c, code_a)
    r_b = get_riasec(interests_c, code_b)

    fig3 = go.Figure()
    for vals, name, color, fill in [
        (r_a, occ_a, C_TEAL,  "rgba(0,180,216,0.15)"),
        (r_b, occ_b, C_GOLD,  "rgba(240,192,64,0.15)"),
    ]:
        fig3.add_trace(go.Scatterpolar(
            r=vals.tolist() + [vals.iloc[0]],
            theta=riasec_cats + [riasec_cats[0]],
            fill="toself", name=name,
            line_color=color, fillcolor=fill,
        ))
    fig3.update_layout(polar=dict(radialaxis=dict(range=[0, 7], gridcolor="#0e2d40"), bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(apply_theme(fig3, 450), use_container_width=True)

    st.markdown("#### Conocimientos requeridos — comparación")
    kn_a = get_metric(knowledge_c, code_a, "IM").rename(columns={"Data Value": occ_a})
    kn_b = get_metric(knowledge_c, code_b, "IM").rename(columns={"Data Value": occ_b})
    kn_merge = kn_a.merge(kn_b, on="Element Name", how="outer").fillna(0)

    fig4 = go.Figure()
    fig4.add_trace(go.Bar(name=occ_a, x=kn_merge["Element Name"], y=kn_merge[occ_a], marker_color=C_TEAL))
    fig4.add_trace(go.Bar(name=occ_b, x=kn_merge["Element Name"], y=kn_merge[occ_b], marker_color=C_GOLD))
    fig4.update_layout(barmode="group", xaxis_tickangle=-35,
                       yaxis_title="Importancia")
    st.plotly_chart(apply_theme(fig4, 420), use_container_width=True)
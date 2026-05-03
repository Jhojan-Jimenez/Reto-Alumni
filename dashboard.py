"""
Observatorio Laboral – Universidad de La Sabana
Dashboard interactivo: O*NET + SPE Colombia
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ─── Configuración ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Observatorio Laboral – UniSabana",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

ONET    = Path("data/ONET")
PALETTE = px.colors.qualitative.Bold

# ─── Loaders con caché ────────────────────────────────────────────────────────

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

@st.cache_data
def load_spe_freq():
    p = Path("data/processed/Servicio de Empleo_frecuencia_skills.csv")
    return pd.read_csv(p, encoding="utf-8-sig") if p.exists() else None


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Universidad_de_La_Sabana_logo.svg/200px-Universidad_de_La_Sabana_logo.svg.png", width=160)
    st.markdown("## Observatorio Laboral")
    st.markdown("**Universidad de La Sabana**  \nDirección de Alumni · 2026")
    st.divider()
    st.caption("Fuentes: O\\*NET · SPE Colombia · Ocupacol")


# ─── Título ───────────────────────────────────────────────────────────────────
st.title("🎓 Observatorio Laboral – Universidad de La Sabana")
st.markdown("Análisis del mercado laboral basado en O\\*NET y datos del Servicio Público de Empleo de Colombia.")

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_mercado, tab_skills, tab_ocupacion, tab_tendencias, tab_comparador = st.tabs([
    "🇨🇴 Mercado Real (SPE)",
    "🧠 Skills & Conocimiento",
    "👤 Perfil de Ocupación",
    "📈 Tendencias",
    "⚖️ Comparador",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: MERCADO REAL (SPE Colombia)
# ══════════════════════════════════════════════════════════════════════════════
with tab_mercado:
    spe = load_spe_freq()

    if spe is None:
        st.warning("No se encontró `Servicio de Empleo_frecuencia_skills.csv`. Ejecuta primero `extract_skills.py`.")
    else:
        st.subheader("Mercado laboral colombiano — Servicio Público de Empleo")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total skills detectadas", len(spe))
        col2.metric("Skill más demandada", spe.iloc[0]["skill"])
        col3.metric("Menciones top skill", int(spe.iloc[0]["menciones"]))

        st.divider()

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### Top 20 skills más demandadas")
            n = st.slider("Número de skills", 5, 30, 20, key="spe_top_n")
            df_top = spe.head(n)
            fig = px.bar(
                df_top, x="menciones", y="skill", orientation="h",
                color="categoria",
                color_discrete_map={
                    "técnica":      "#1f77b4",
                    "blanda":       "#ff7f0e",
                    "conocimiento": "#2ca02c",
                    "destreza":     "#9467bd",
                },
                labels={"menciones": "Menciones", "skill": "Skill", "categoria": "Categoría"},
                title=f"Top {n} skills demandadas en Colombia (SPE)",
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=520)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown("#### Distribución por categoría")
            cat_counts = spe.groupby("categoria")["menciones"].sum().reset_index()
            fig2 = px.pie(
                cat_counts, names="categoria", values="menciones",
                hole=0.45, color_discrete_sequence=PALETTE,
                title="Proporción de menciones por tipo de skill",
            )
            fig2.update_traces(textposition="outside", textinfo="percent+label")
            st.plotly_chart(fig2, use_container_width=True)

            st.markdown("#### Skills técnicas en detalle")
            tech_spe = spe[spe["categoria"] == "técnica"].head(10)
            fig3 = px.bar(
                tech_spe, x="skill", y="menciones",
                color_discrete_sequence=["#1f77b4"],
                title="Top herramientas técnicas (SPE Colombia)",
            )
            fig3.update_layout(xaxis_tickangle=-35)
            st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: SKILLS & CONOCIMIENTO (O*NET)
# ══════════════════════════════════════════════════════════════════════════════
with tab_skills:
    st.subheader("Taxonomía de Skills y Conocimiento — O\\*NET")

    skills_df    = load_skills()
    knowledge_df = load_knowledge()
    tech_df      = load_tech()
    jz_df        = load_job_zones()

    col1, col2 = st.columns(2)

    # ── Tecnologías Hot ────────────────────────────────────────────────────
    with col1:
        st.markdown("#### Tecnologías 'Hot' más frecuentes")
        filtro = st.radio("Filtrar por", ["Hot Technology", "In Demand"], horizontal=True, key="tech_filter")
        col_map = {"Hot Technology": "Hot Technology", "In Demand": "In Demand"}
        tech_top = (
            tech_df[tech_df[col_map[filtro]] == "Y"]
            .groupby("Example")
            .size()
            .reset_index(name="ocupaciones")
            .sort_values("ocupaciones", ascending=False)
            .head(20)
        )
        fig = px.bar(
            tech_top, x="ocupaciones", y="Example", orientation="h",
            color="ocupaciones", color_continuous_scale="Blues",
            title=f"Top 20 tecnologías ({filtro})",
            labels={"ocupaciones": "N° ocupaciones", "Example": "Tecnología"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=520, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ── Top conocimientos globales ─────────────────────────────────────────
    with col2:
        st.markdown("#### Top conocimientos más valorados")
        know_im = (
            knowledge_df[knowledge_df["Scale ID"] == "IM"]
            .groupby("Element Name")["Data Value"]
            .mean()
            .reset_index()
            .sort_values("Data Value", ascending=False)
            .head(20)
        )
        fig2 = px.bar(
            know_im, x="Data Value", y="Element Name", orientation="h",
            color="Data Value", color_continuous_scale="Greens",
            title="Top 20 conocimientos (importancia promedio O*NET)",
            labels={"Data Value": "Importancia media", "Element Name": "Conocimiento"},
        )
        fig2.update_layout(yaxis={"categoryorder": "total ascending"}, height=520, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Heatmap Skills vs Job Zone ─────────────────────────────────────────
    st.markdown("#### Heatmap — Importancia de skills por Job Zone")
    st.caption("Job Zone 1 = trabajos de entrada · Job Zone 5 = alta especialización")

    skills_im = skills_df[skills_df["Scale ID"] == "IM"][["O*NET-SOC Code", "Element Name", "Data Value"]]
    jz_map    = jz_df[["O*NET-SOC Code", "Job Zone"]].drop_duplicates()
    merged    = skills_im.merge(jz_map, on="O*NET-SOC Code")

    heatmap_df = (
        merged.groupby(["Element Name", "Job Zone"])["Data Value"]
        .mean()
        .reset_index()
        .pivot(index="Element Name", columns="Job Zone", values="Data Value")
        .fillna(0)
    )

    fig3 = px.imshow(
        heatmap_df,
        color_continuous_scale="RdYlGn",
        aspect="auto",
        title="Importancia de skills por Job Zone (O*NET)",
        labels={"x": "Job Zone", "y": "Skill", "color": "Importancia"},
    )
    fig3.update_layout(height=600)
    st.plotly_chart(fig3, use_container_width=True)

    # ── Scatter Importancia vs Nivel ───────────────────────────────────────
    st.markdown("#### Scatter — Importancia vs Nivel requerido por skill")

    skills_im2  = skills_df[skills_df["Scale ID"] == "IM"][["Element Name", "Data Value"]].rename(columns={"Data Value": "Importancia"})
    skills_lv   = skills_df[skills_df["Scale ID"] == "LV"][["Element Name", "Data Value"]].rename(columns={"Data Value": "Nivel"})
    skill_count = skills_df.groupby("Element Name").size().reset_index(name="frecuencia")
    scatter_df  = skills_im2.groupby("Element Name")["Importancia"].mean().reset_index()
    scatter_df  = scatter_df.merge(skills_lv.groupby("Element Name")["Nivel"].mean().reset_index(), on="Element Name")
    scatter_df  = scatter_df.merge(skill_count, on="Element Name")

    fig4 = px.scatter(
        scatter_df, x="Importancia", y="Nivel", size="frecuencia",
        text="Element Name", color="frecuencia",
        color_continuous_scale="Viridis",
        title="Skills: importancia vs nivel requerido (tamaño = frecuencia en empleos)",
        labels={"Importancia": "Importancia promedio", "Nivel": "Nivel requerido"},
    )
    fig4.update_traces(textposition="top center", textfont_size=9)
    fig4.update_layout(height=540)
    st.plotly_chart(fig4, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: PERFIL DE OCUPACIÓN
# ══════════════════════════════════════════════════════════════════════════════
with tab_ocupacion:
    st.subheader("Perfil de una Ocupación")

    occ_data    = load_occ_data()
    interests_df = load_interests()
    styles_df   = load_work_styles()
    skills_df2  = load_skills()
    knowledge_df2 = load_knowledge()
    jz_df2      = load_job_zones()

    occ_list = occ_data["Title"].sort_values().tolist()
    selected = st.selectbox("Selecciona una ocupación", occ_list, index=occ_list.index("Lawyers") if "Lawyers" in occ_list else 0)

    soc_code = occ_data[occ_data["Title"] == selected]["O*NET-SOC Code"].iloc[0]
    desc     = occ_data[occ_data["Title"] == selected]["Description"].iloc[0]

    jz_row = jz_df2[jz_df2["O*NET-SOC Code"] == soc_code]
    jz_val = int(jz_row["Job Zone"].iloc[0]) if not jz_row.empty else "N/A"

    col1, col2 = st.columns([1, 3])
    col1.metric("Job Zone", jz_val)
    col1.metric("Código O*NET", soc_code)
    col2.markdown(f"**Descripción:** {desc}")

    st.divider()

    col_a, col_b = st.columns(2)

    # ── Radar RIASEC ──────────────────────────────────────────────────────
    with col_a:
        st.markdown("#### Perfil RIASEC")
        riasec_cats = ["Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional"]
        riasec_df = interests_df[
            (interests_df["O*NET-SOC Code"] == soc_code) &
            (interests_df["Scale ID"] == "OI") &
            (interests_df["Element Name"].isin(riasec_cats))
        ]

        if riasec_df.empty:
            st.info("Sin datos RIASEC para esta ocupación.")
        else:
            vals = riasec_df.set_index("Element Name")["Data Value"].reindex(riasec_cats, fill_value=0)
            fig = go.Figure(go.Scatterpolar(
                r=vals.values.tolist() + [vals.values[0]],
                theta=riasec_cats + [riasec_cats[0]],
                fill="toself",
                line_color="#1f77b4",
                fillcolor="rgba(31,119,180,0.2)",
            ))
            fig.update_layout(polar=dict(radialaxis=dict(range=[0, 7])), title="Perfil de Intereses RIASEC", height=420)
            st.plotly_chart(fig, use_container_width=True)

    # ── Radar Skills ──────────────────────────────────────────────────────
    with col_b:
        st.markdown("#### Perfil de Skills")
        skill_occ = skills_df2[
            (skills_df2["O*NET-SOC Code"] == soc_code) &
            (skills_df2["Scale ID"] == "IM")
        ].sort_values("Data Value", ascending=False).head(10)

        if skill_occ.empty:
            st.info("Sin datos de skills para esta ocupación.")
        else:
            skill_names = skill_occ["Element Name"].tolist()
            skill_vals  = skill_occ["Data Value"].tolist()
            fig2 = go.Figure(go.Scatterpolar(
                r=skill_vals + [skill_vals[0]],
                theta=skill_names + [skill_names[0]],
                fill="toself",
                line_color="#ff7f0e",
                fillcolor="rgba(255,127,14,0.2)",
            ))
            fig2.update_layout(polar=dict(radialaxis=dict(range=[0, 7])), title="Top 10 Skills por Importancia", height=420)
            st.plotly_chart(fig2, use_container_width=True)

    # ── Work Styles (horizontal bar) ──────────────────────────────────────
    st.markdown("#### Estilos de trabajo")
    ws_occ = styles_df[
        (styles_df["O*NET-SOC Code"] == soc_code) &
        (styles_df["Scale ID"] == "WI")
    ].sort_values("Data Value", ascending=False)

    if not ws_occ.empty:
        fig3 = px.bar(
            ws_occ, x="Data Value", y="Element Name", orientation="h",
            color="Data Value", color_continuous_scale="Purples",
            title="Estilos de trabajo (Work Styles)",
            labels={"Data Value": "Importancia", "Element Name": "Estilo"},
        )
        fig3.update_layout(yaxis={"categoryorder": "total ascending"}, height=420, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    # ── Ocupaciones relacionadas ───────────────────────────────────────────
    st.markdown("#### Ocupaciones relacionadas")
    related_df = load_related()
    rel_occ = related_df[related_df["O*NET-SOC Code"] == soc_code].sort_values("Index", ascending=False).head(10)

    if not rel_occ.empty:
        fig4 = px.bar(
            rel_occ, x="Index", y="Related Title", orientation="h",
            color="Relatedness Tier",
            color_discrete_map={"Closely Related": "#2ca02c", "Related": "#98df8a"},
            title="Ocupaciones más relacionadas",
            labels={"Index": "Índice de relación", "Related Title": "Ocupación"},
        )
        fig4.update_layout(yaxis={"categoryorder": "total ascending"}, height=420)
        st.plotly_chart(fig4, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: TENDENCIAS
# ══════════════════════════════════════════════════════════════════════════════
with tab_tendencias:
    st.subheader("Tendencias del Mercado Laboral")

    emerging_df = load_emerging()
    wa_df       = load_work_activities()
    jz_df3      = load_job_zones()

    col1, col2 = st.columns(2)

    # ── Tareas emergentes por categoría ──────────────────────────────────
    with col1:
        st.markdown("#### Tareas emergentes por categoría")
        emg_count = emerging_df.groupby("Category").size().reset_index(name="tareas")
        fig = px.pie(
            emg_count, names="Category", values="tareas",
            hole=0.4, color_discrete_sequence=PALETTE,
            title="Distribución de tareas emergentes por categoría",
        )
        fig.update_traces(textposition="outside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    # ── Distribución Job Zone ─────────────────────────────────────────────
    with col2:
        st.markdown("#### Distribución de ocupaciones por Job Zone")
        jz_count = jz_df3["Job Zone"].value_counts().reset_index()
        jz_count.columns = ["Job Zone", "Ocupaciones"]
        jz_count["Job Zone"] = jz_count["Job Zone"].astype(str)
        jz_labels = {
            "1": "JZ1: Sin preparación",
            "2": "JZ2: Baja preparación",
            "3": "JZ3: Preparación media",
            "4": "JZ4: Alta preparación",
            "5": "JZ5: Muy alta preparación",
        }
        jz_count["Nivel"] = jz_count["Job Zone"].map(jz_labels)
        fig2 = px.pie(
            jz_count, names="Nivel", values="Ocupaciones",
            hole=0.45, color_discrete_sequence=px.colors.sequential.Blues_r,
            title="Ocupaciones por Job Zone (nivel de preparación requerido)",
        )
        fig2.update_traces(textposition="outside", textinfo="percent+label")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Treemap actividades de trabajo ────────────────────────────────────
    st.markdown("#### Treemap — Actividades de trabajo por importancia")
    wa_im = (
        wa_df[wa_df["Scale ID"] == "IM"]
        .groupby("Element Name")["Data Value"]
        .mean()
        .reset_index()
        .sort_values("Data Value", ascending=False)
        .head(40)
    )
    wa_im["root"] = "Actividades"
    fig3 = px.treemap(
        wa_im, path=["root", "Element Name"], values="Data Value",
        color="Data Value", color_continuous_scale="RdYlGn",
        title="Top 40 actividades de trabajo por importancia promedio (O*NET)",
    )
    fig3.update_layout(height=520)
    st.plotly_chart(fig3, use_container_width=True)

    # ── Tareas emergentes: tabla explorable ───────────────────────────────
    st.markdown("#### Explorar tareas emergentes")
    cat_filter = st.multiselect(
        "Filtrar por categoría",
        options=emerging_df["Category"].unique().tolist(),
        default=emerging_df["Category"].unique().tolist()[:2],
    )
    emg_filtered = emerging_df[emerging_df["Category"].isin(cat_filter)]
    st.dataframe(
        emg_filtered[["Title", "Task", "Category", "Date"]].rename(columns={
            "Title": "Ocupación", "Task": "Tarea emergente",
            "Category": "Categoría", "Date": "Fecha"
        }),
        use_container_width=True, height=380,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: COMPARADOR DE OCUPACIONES
# ══════════════════════════════════════════════════════════════════════════════
with tab_comparador:
    st.subheader("Comparador de Ocupaciones")

    occ_data2    = load_occ_data()
    skills_c     = load_skills()
    knowledge_c  = load_knowledge()
    interests_c  = load_interests()
    styles_c     = load_work_styles()
    jz_c         = load_job_zones()

    occ_list2 = occ_data2["Title"].sort_values().tolist()

    col1, col2 = st.columns(2)
    with col1:
        occ_a = st.selectbox("Ocupación A", occ_list2, index=occ_list2.index("Lawyers") if "Lawyers" in occ_list2 else 0, key="cmp_a")
    with col2:
        occ_b = st.selectbox("Ocupación B", occ_list2, index=occ_list2.index("Software Developers") if "Software Developers" in occ_list2 else 1, key="cmp_b")

    code_a = occ_data2[occ_data2["Title"] == occ_a]["O*NET-SOC Code"].iloc[0]
    code_b = occ_data2[occ_data2["Title"] == occ_b]["O*NET-SOC Code"].iloc[0]

    def get_metric(df, code, scale, top_n=10):
        return (
            df[(df["O*NET-SOC Code"] == code) & (df["Scale ID"] == scale)]
            .sort_values("Data Value", ascending=False)
            .head(top_n)[["Element Name", "Data Value"]]
        )

    st.divider()

    # ── Métricas rápidas ──────────────────────────────────────────────────
    jz_a = jz_c[jz_c["O*NET-SOC Code"] == code_a]["Job Zone"].values
    jz_b = jz_c[jz_c["O*NET-SOC Code"] == code_b]["Job Zone"].values

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"Job Zone — {occ_a[:25]}", int(jz_a[0]) if len(jz_a) else "N/A")
    m2.metric(f"Job Zone — {occ_b[:25]}", int(jz_b[0]) if len(jz_b) else "N/A")

    col_a, col_b = st.columns(2)

    # ── Skills comparadas ─────────────────────────────────────────────────
    with col_a:
        st.markdown(f"#### Skills — {occ_a}")
        sk_a = get_metric(skills_c, code_a, "IM")
        fig = px.bar(sk_a, x="Data Value", y="Element Name", orientation="h",
                     color_discrete_sequence=["#1f77b4"],
                     labels={"Data Value": "Importancia", "Element Name": "Skill"})
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=380)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown(f"#### Skills — {occ_b}")
        sk_b = get_metric(skills_c, code_b, "IM")
        fig2 = px.bar(sk_b, x="Data Value", y="Element Name", orientation="h",
                      color_discrete_sequence=["#ff7f0e"],
                      labels={"Data Value": "Importancia", "Element Name": "Skill"})
        fig2.update_layout(yaxis={"categoryorder": "total ascending"}, height=380)
        st.plotly_chart(fig2, use_container_width=True)

    # ── Radar superpuesto RIASEC ──────────────────────────────────────────
    st.markdown("#### Comparación RIASEC superpuesta")
    riasec_cats = ["Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional"]

    def get_riasec(df, code):
        r = df[(df["O*NET-SOC Code"] == code) & (df["Scale ID"] == "OI") & (df["Element Name"].isin(riasec_cats))]
        return r.set_index("Element Name")["Data Value"].reindex(riasec_cats, fill_value=0)

    r_a = get_riasec(interests_c, code_a)
    r_b = get_riasec(interests_c, code_b)

    fig3 = go.Figure()
    for vals, name, color, fill in [
        (r_a, occ_a, "#1f77b4", "rgba(31,119,180,0.15)"),
        (r_b, occ_b, "#ff7f0e", "rgba(255,127,14,0.15)"),
    ]:
        fig3.add_trace(go.Scatterpolar(
            r=vals.tolist() + [vals.iloc[0]],
            theta=riasec_cats + [riasec_cats[0]],
            fill="toself", name=name,
            line_color=color, fillcolor=fill,
        ))
    fig3.update_layout(polar=dict(radialaxis=dict(range=[0, 7])), title="RIASEC superpuesto", height=450)
    st.plotly_chart(fig3, use_container_width=True)

    # ── Conocimientos comparados ───────────────────────────────────────────
    st.markdown("#### Conocimientos requeridos — comparación")
    kn_a = get_metric(knowledge_c, code_a, "IM").rename(columns={"Data Value": occ_a})
    kn_b = get_metric(knowledge_c, code_b, "IM").rename(columns={"Data Value": occ_b})
    kn_merge = kn_a.merge(kn_b, on="Element Name", how="outer").fillna(0)

    fig4 = go.Figure()
    fig4.add_trace(go.Bar(name=occ_a, x=kn_merge["Element Name"], y=kn_merge[occ_a], marker_color="#1f77b4"))
    fig4.add_trace(go.Bar(name=occ_b, x=kn_merge["Element Name"], y=kn_merge[occ_b], marker_color="#ff7f0e"))
    fig4.update_layout(barmode="group", xaxis_tickangle=-35, height=420,
                       title="Conocimientos requeridos (importancia O*NET)",
                       yaxis_title="Importancia")
    st.plotly_chart(fig4, use_container_width=True)

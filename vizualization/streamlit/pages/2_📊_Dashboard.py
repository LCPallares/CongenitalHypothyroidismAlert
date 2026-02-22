# pages/2_📊_Dashboard.py
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import folium
from streamlit_folium import st_folium

from utils.constantes import CSS, TSH_CORTE, CSV_REGISTROS

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.title("📊 Dashboard / Reportes")


@st.cache_data
def load_data():
    try:
        df = pd.read_csv(CSV_REGISTROS, low_memory=False)
    except FileNotFoundError:
        return pd.DataFrame()

    date_cols = [
        "fecha_ingreso", "fecha_nacimiento", "fecha_toma_muestra",
        "fecha_resultado", "fecha_toma_muestra_2", "fecha_resultado_muestra_2",
        "fecha_toma_rechazada", "fecha_resultado_rechazada",
    ]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in ["prematuro", "transfundido", "informacion_completa",
                "muestra_adecuada", "muestra_rechazada"]:
        if col in df.columns:
            df[col] = df[col].map({"VERDADERO": True, "FALSO": False})

    df["tsh_neonatal"]      = pd.to_numeric(df.get("tsh_neonatal", 0), errors="coerce").fillna(0)
    df["resultado_muestra_2"] = pd.to_numeric(df.get("resultado_muestra_2", 0), errors="coerce").fillna(0)
    df["sospecha_hipotiroidismo"]  = df["tsh_neonatal"] >= TSH_CORTE
    df["confirmado_hipotiroidismo"] = (
        (df["tsh_neonatal"] >= TSH_CORTE) & (df["resultado_muestra_2"] >= TSH_CORTE)
    )
    return df


def graficar_mapa(df):
    city_coords = {
        "Bogota":       [4.6097, -74.0817],
        "Cundinamarca": [4.7000, -73.8000],
    }
    m = folium.Map(location=[4.6097, -74.0817], zoom_start=6, tiles="cartodbpositron")
    for city, casos in df.groupby("ciudad")["confirmado_hipotiroidismo"].sum().items():
        if city in city_coords:
            folium.Marker(
                location=city_coords[city],
                popup=f"<b>{city}</b><br>Confirmados: {int(casos)}",
                tooltip=city,
                icon=folium.Icon(color="red", icon="plus-square", prefix="fa"),
            ).add_to(m)
    st_folium(m, width=700, height=500)


# ── Cargar datos ──────────────────────────────────────────────────────────────
df = load_data()

if df.empty:
    st.warning("⚠️ Aún no hay registros. Ingresa datos desde la página **📝 Formulario**.")
    st.stop()

# ── Botón refrescar (invalida caché) ─────────────────────────────────────────
if st.button("🔄 Refrescar datos"):
    st.cache_data.clear()
    st.rerun()

# ── Métricas generales ────────────────────────────────────────────────────────
st.header("🔍 Información General")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Registros",            f"{df.shape[0]:,}")
col2.metric(f"Sospechosos (TSH ≥ {TSH_CORTE})", f"{df['sospecha_hipotiroidismo'].sum():,}")
col3.metric("Confirmados",                   f"{df['confirmado_hipotiroidismo'].sum():,}")
col4.metric("Pendientes (sin TSH)",
            f"{(df['tsh_neonatal'] == 0).sum():,}")

# ── Sidebar filtros ───────────────────────────────────────────────────────────
st.sidebar.header("📋 Filtros")

años = sorted(df["fecha_nacimiento"].dt.year.dropna().unique().tolist()) if "fecha_nacimiento" in df.columns else []
años_sel = st.sidebar.multiselect("Año nacimiento:", años, default=años)

sexos = sorted(df["sexo"].dropna().unique().tolist()) if "sexo" in df.columns else []
sexos_sel = st.sidebar.multiselect("Sexo:", sexos, default=sexos)

prem_sel = st.sidebar.radio("Prematuridad:", ["Todos", "Prematuros", "No Prematuros"])

tipos = sorted(df["tipo_muestra"].dropna().unique().tolist()) if "tipo_muestra" in df.columns else []
tipos_sel = st.sidebar.multiselect("Tipo de Muestra:", tipos, default=tipos)

deptos = sorted(df["departamento"].dropna().unique().tolist()) if "departamento" in df.columns else []
deptos_sel = st.sidebar.multiselect("Departamento:", deptos, default=deptos)

estado_sel = st.sidebar.radio("Estado:", ["Todos", "Sospechosos", "Confirmados", "Normales", "Pendientes"])

st.sidebar.header("⚙️ Configuración")
tsh_umbral = st.sidebar.slider("Umbral TSH (mIU/L):", 1.0, 30.0, float(TSH_CORTE), 0.5)

# ── Aplicar filtros ───────────────────────────────────────────────────────────
fdf = df.copy()
if años_sel and "fecha_nacimiento" in fdf.columns:
    fdf = fdf[fdf["fecha_nacimiento"].dt.year.isin(años_sel)]
if sexos_sel and "sexo" in fdf.columns:
    fdf = fdf[fdf["sexo"].isin(sexos_sel)]
if prem_sel == "Prematuros"    and "prematuro" in fdf.columns:
    fdf = fdf[fdf["prematuro"] == True]
elif prem_sel == "No Prematuros" and "prematuro" in fdf.columns:
    fdf = fdf[fdf["prematuro"] == False]
if tipos_sel and "tipo_muestra" in fdf.columns:
    fdf = fdf[fdf["tipo_muestra"].isin(tipos_sel)]
if deptos_sel and "departamento" in fdf.columns:
    fdf = fdf[fdf["departamento"].isin(deptos_sel)]
if estado_sel == "Sospechosos":
    fdf = fdf[fdf["sospecha_hipotiroidismo"]]
elif estado_sel == "Confirmados":
    fdf = fdf[fdf["confirmado_hipotiroidismo"]]
elif estado_sel == "Normales":
    fdf = fdf[~fdf["sospecha_hipotiroidismo"]]
elif estado_sel == "Pendientes":
    fdf = fdf[fdf["tsh_neonatal"] == 0]

st.sidebar.markdown(f"**Registros filtrados:** {fdf.shape[0]:,}")

# ── Sub-tabs ──────────────────────────────────────────────────────────────────
t1, t2, t3, t4 = st.tabs(["Resumen Ejecutivo", "Análisis TSH",
                            "Análisis Temporal", "Factores de Riesgo"])

# ─────────────────────────────────────────────────────────────────────────────
with t1:
    st.header("📌 Resumen Ejecutivo")

    sosp  = int(df["sospecha_hipotiroidismo"].sum())
    conf  = int(df["confirmado_hipotiroidismo"].sum())
    tasa  = conf / sosp if sosp > 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Sospechosos (TSH ≥ {TSH_CORTE})", f"{sosp:,}")
    c2.metric("Confirmados", f"{conf:,}")
    c3.metric("Tasa de Confirmación", f"{tasa:.1%}")

    fig_funnel = go.Figure(go.Funnel(
        y=["Tamizados", f"TSH ≥ {TSH_CORTE}", "Confirmados"],
        x=[df.shape[0], sosp, conf],
        textinfo="value+percent initial",
        marker={"color": ["#4682B4", "#FFA500", "#FF4500"]},
    ))
    fig_funnel.update_layout(title="Pirámide de Diagnóstico", height=400)
    st.plotly_chart(fig_funnel, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        if "sexo" in fdf.columns:
            sc = fdf.groupby(["sexo", "confirmado_hipotiroidismo"]).size().unstack(fill_value=0)
            for v in [False, True]:
                if v not in sc.columns: sc[v] = 0
            sc.columns = ["Normal", "Hipotiroidismo"]
            st.plotly_chart(
                px.bar(sc.reset_index(), x="sexo", y=["Normal","Hipotiroidismo"],
                       barmode="group", title="Distribución por Sexo",
                       color_discrete_map={"Normal":"#4682B4","Hipotiroidismo":"#FF4500"}),
                use_container_width=True)
    with c2:
        if "prematuro" in fdf.columns:
            pc = fdf.copy()
            pc["prematuro"] = pc["prematuro"].fillna(False)
            pc = pc.groupby(["prematuro","confirmado_hipotiroidismo"]).size().unstack(fill_value=0)
            for v in [False, True]:
                if v not in pc.columns: pc[v] = 0
            pc.columns = ["Normal","Hipotiroidismo"]
            pc = pc.reset_index()
            pc["prematuro"] = pc["prematuro"].map({True:"Prematuro",False:"No Prematuro"})
            st.plotly_chart(
                px.bar(pc, x="prematuro", y=["Normal","Hipotiroidismo"],
                       barmode="group", title="Distribución por Prematuridad",
                       color_discrete_map={"Normal":"#4682B4","Hipotiroidismo":"#FF4500"}),
                use_container_width=True)

    if "ciudad" in fdf.columns:
        graficar_mapa(fdf)

# ─────────────────────────────────────────────────────────────────────────────
with t2:
    st.header("📊 Análisis de TSH Neonatal")
    c1, c2 = st.columns(2)
    with c1:
        cap = fdf["tsh_neonatal"].quantile(0.99)
        fig = px.histogram(fdf[fdf["tsh_neonatal"] <= cap], x="tsh_neonatal", nbins=30,
                           color_discrete_sequence=["#3CB371"],
                           labels={"tsh_neonatal":"TSH (mIU/L)"},
                           title="Distribución de TSH Neonatal")
        fig.add_vline(x=tsh_umbral, line_dash="dash", line_color="red",
                      annotation_text=f"Umbral: {tsh_umbral}")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        d2 = fdf.dropna(subset=["tsh_neonatal","resultado_muestra_2"])
        d2 = d2[d2["resultado_muestra_2"] > 0]
        if not d2.empty:
            fig2 = px.scatter(d2, x="tsh_neonatal", y="resultado_muestra_2",
                              color="confirmado_hipotiroidismo",
                              color_discrete_map={True:"#FF4500",False:"#4682B4"},
                              title="TSH 1ª vs 2ª Muestra",
                              labels={"tsh_neonatal":"TSH 1ª","resultado_muestra_2":"TSH 2ª"})
            fig2.add_hline(y=tsh_umbral, line_dash="dash", line_color="red")
            fig2.add_vline(x=tsh_umbral, line_dash="dash", line_color="red")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Aún no hay registros con 2ª muestra.")

    c1, c2 = st.columns(2)
    with c1:
        if "sexo" in fdf.columns:
            fig = px.box(fdf, x="sexo", y="tsh_neonatal", color="sexo",
                         points="outliers", title="TSH por Sexo")
            fig.add_hline(y=tsh_umbral, line_dash="dash", line_color="red")
            fig.update_yaxes(range=[0, 40])
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        if "prematuro" in fdf.columns:
            ymax = max(30, fdf["tsh_neonatal"].quantile(0.95))
            fig = px.box(fdf, x="prematuro", y="tsh_neonatal", color="prematuro",
                         points="outliers", title="TSH por Prematuridad")
            fig.add_hline(y=tsh_umbral, line_dash="dash", line_color="red")
            fig.update_yaxes(range=[0, ymax])
            st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
with t3:
    st.header("⏱️ Análisis Temporal")
    if "fecha_nacimiento" in fdf.columns and not fdf["fecha_nacimiento"].isna().all():
        tmp = fdf.copy()
        tmp["año_mes"] = tmp["fecha_nacimiento"].dt.to_period("M")
        temp = tmp.groupby("año_mes").agg(
            total=("tsh_neonatal","count"),
            sospechosos=("sospecha_hipotiroidismo","sum"),
            confirmados=("confirmado_hipotiroidismo","sum"),
            tsh_prom=("tsh_neonatal","mean"),
        ).reset_index()
        temp["año_mes"] = temp["año_mes"].dt.to_timestamp()
        temp["tasa"] = temp["confirmados"] / temp["sospechosos"].replace(0, np.nan)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=temp["año_mes"], y=temp["sospechosos"],
                                 mode="lines+markers", name="Sospechosos",
                                 line=dict(color="#FFA500", width=2)))
        fig.add_trace(go.Scatter(x=temp["año_mes"], y=temp["confirmados"],
                                 mode="lines+markers", name="Confirmados",
                                 line=dict(color="#FF4500", width=2)))
        fig.add_trace(go.Scatter(x=temp["año_mes"], y=temp["tasa"],
                                 mode="lines", name="Tasa confirmación",
                                 line=dict(color="#4682B4", dash="dot"), yaxis="y2"))
        fig.update_layout(
            title="Evolución Temporal",
            yaxis=dict(title="Casos"),
            yaxis2=dict(title="Tasa", overlaying="y", side="right", range=[0,1]),
            legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay suficientes datos temporales aún.")

# ─────────────────────────────────────────────────────────────────────────────
with t4:
    st.header("🔬 Factores de Riesgo")
    if "peso" in fdf.columns:
        dr = fdf.copy()
        dr["peso_kg"] = pd.to_numeric(dr["peso"], errors="coerce") / 1000
        fig = px.scatter(dr, x="peso_kg", y="tsh_neonatal",
                         color="confirmado_hipotiroidismo",
                         color_discrete_map={True:"#FF4500",False:"#4682B4"},
                         title="Peso al Nacer vs TSH",
                         labels={"peso_kg":"Peso (kg)","tsh_neonatal":"TSH (mIU/L)"},
                         trendline="ols", opacity=0.7)
        fig.add_hline(y=tsh_umbral, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        if "tipo_muestra" in fdf.columns and "id" in fdf.columns:
            tm = fdf.groupby("tipo_muestra").agg(
                total=("id","count"), conf=("confirmado_hipotiroidismo","sum")).reset_index()
            tm["incidencia"] = (tm["conf"] / tm["total"]) * 100
            st.plotly_chart(
                px.bar(tm, x="tipo_muestra", y="incidencia",
                       title="Incidencia por Tipo de Muestra",
                       color="incidencia", color_continuous_scale="Reds"),
                use_container_width=True)
    with c2:
        if "sexo" in fdf.columns and "id" in fdf.columns:
            sx = fdf.groupby("sexo").agg(
                total=("id","count"), conf=("confirmado_hipotiroidismo","sum")).reset_index()
            sx["incidencia"] = (sx["conf"] / sx["total"]) * 100
            st.plotly_chart(
                px.bar(sx, x="sexo", y="incidencia",
                       title="Incidencia por Sexo",
                       color="incidencia", color_continuous_scale="Reds"),
                use_container_width=True)

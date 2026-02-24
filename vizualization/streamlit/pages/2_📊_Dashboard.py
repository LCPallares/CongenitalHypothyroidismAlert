# pages/2_📊_Dashboard.py
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

from utils.constantes import CSS, TSH_CORTE, CSV_REGISTROS
from utils.graficos import (
    fig_embudo_diagnostico,
    fig_distribucion_sexo,
    fig_distribucion_prematuridad,
    graficar_mapa,
    fig_histograma_tsh,
    fig_scatter_tsh1_vs_tsh2,
    fig_boxplot_tsh_sexo,
    fig_boxplot_tsh_prematuridad,
    fig_evolucion_temporal,
    fig_peso_vs_tsh,
    fig_incidencia_por_tipo_muestra,
    fig_incidencia_por_sexo,
)

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.title("📊 Dashboard / Reportes")


@st.cache_data
def load_data() -> pd.DataFrame:
    try:
        df = pd.read_csv(CSV_REGISTROS, low_memory=False)
    except FileNotFoundError:
        return pd.DataFrame()
    for col in ["fecha_ingreso","fecha_nacimiento","fecha_toma_muestra","fecha_resultado",
                "fecha_toma_muestra_2","fecha_resultado_muestra_2","fecha_toma_rechazada"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    # for col in ["prematuro","transfundido","informacion_completa","muestra_adecuada","muestra_rechazada"]:
    #     if col in df.columns:
    #         df[col] = df[col].map({"VERDADERO": True, "FALSO": False})
    df["tsh_neonatal"]        = pd.to_numeric(df.get("tsh_neonatal",0), errors="coerce").fillna(0)
    df["resultado_muestra_2"] = pd.to_numeric(df.get("resultado_muestra_2",0), errors="coerce").fillna(0)
    df["sospecha_hipotiroidismo"]   = df["tsh_neonatal"] >= TSH_CORTE
    df["confirmado_hipotiroidismo"] = (df["tsh_neonatal"] >= TSH_CORTE) & (df["resultado_muestra_2"] >= TSH_CORTE)
    return df


df = load_data()

if df.empty:
    st.warning("⚠️ Aún no hay registros. Ingresa datos desde **📝 Formulario**.")
    st.stop()

if st.button("🔄 Refrescar datos"):
    st.cache_data.clear()
    st.rerun()

st.header("🔍 Información General")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Registros",              f"{df.shape[0]:,}")
c2.metric(f"Sospechosos (TSH≥{TSH_CORTE})",f"{df['sospecha_hipotiroidismo'].sum():,}")
c3.metric("Confirmados",                  f"{df['confirmado_hipotiroidismo'].sum():,}")
c4.metric("Pendientes (sin TSH)",         f"{(df['tsh_neonatal']==0).sum():,}")

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("📋 Filtros")
años      = sorted(df["fecha_nacimiento"].dt.year.dropna().unique()) if "fecha_nacimiento" in df.columns else []
años_sel  = st.sidebar.multiselect("Año nacimiento:", años, default=años)
sexos     = sorted(df["sexo"].dropna().unique()) if "sexo" in df.columns else []
sexos_sel = st.sidebar.multiselect("Sexo:", sexos, default=sexos)
prem_sel  = st.sidebar.radio("Prematuridad:", ["Todos","Prematuros","No Prematuros"])
tipos     = sorted(df["tipo_muestra"].dropna().unique()) if "tipo_muestra" in df.columns else []
tipos_sel = st.sidebar.multiselect("Tipo Muestra:", tipos, default=tipos)
col_depto = "nombre_departamento" if "nombre_departamento" in df.columns else "departamento"
deptos    = sorted(df[col_depto].dropna().unique()) if col_depto in df.columns else []
deptos_sel= st.sidebar.multiselect("Departamento:", deptos, default=deptos)
col_ciudad = "nombre_ciudad" if "nombre_ciudad" in df.columns else "ciudad"
ciudades = sorted(df["ciudad"].dropna().unique().tolist()) if "ciudad" in df.columns else []
ciudades_sel = st.sidebar.multiselect("Ciudad:", ciudades, default=ciudades)
estado_sel= st.sidebar.radio("Estado:", ["Todos","Sospechosos","Confirmados","Normales","Pendientes"])
st.sidebar.header("⚙️ Configuración")
tsh_umbral= st.sidebar.slider("Umbral TSH (mIU/L):", 1.0, 30.0, float(TSH_CORTE), 0.5)

# ── Filtros ───────────────────────────────────────────────────────────────────
fdf = df.copy()
if años_sel  and "fecha_nacimiento" in fdf.columns:
    fdf = fdf[fdf["fecha_nacimiento"].dt.year.isin(años_sel)]
if sexos_sel and "sexo" in fdf.columns:
    fdf = fdf[fdf["sexo"].isin(sexos_sel)]
if prem_sel == "Prematuros"    and "prematuro" in fdf.columns: fdf = fdf[fdf["prematuro"]==True]
elif prem_sel == "No Prematuros" and "prematuro" in fdf.columns: fdf = fdf[fdf["prematuro"]==False]
if tipos_sel  and "tipo_muestra" in fdf.columns: fdf = fdf[fdf["tipo_muestra"].isin(tipos_sel)]
if deptos_sel and col_depto in fdf.columns: fdf = fdf[fdf[col_depto].isin(deptos_sel)]
if ciudades_sel and col_ciudad in fdf.columns: fdf = fdf[fdf[col_ciudad].isin(ciudades_sel)]
if   estado_sel == "Sospechosos":  fdf = fdf[fdf["sospecha_hipotiroidismo"]]
elif estado_sel == "Confirmados":  fdf = fdf[fdf["confirmado_hipotiroidismo"]]
elif estado_sel == "Normales":     fdf = fdf[~fdf["sospecha_hipotiroidismo"]]
elif estado_sel == "Pendientes":   fdf = fdf[fdf["tsh_neonatal"]==0]
st.sidebar.markdown(f"**Filtrados:** {fdf.shape[0]:,} registros")

# ── Tabs ──────────────────────────────────────────────────────────────────────
t1, t2, t3, t4 = st.tabs(["Resumen Ejecutivo","Análisis TSH","Análisis Temporal","Factores de Riesgo"])

with t1:
    st.header("📌 Resumen Ejecutivo")
    sosp = int(df["sospecha_hipotiroidismo"].sum())
    conf = int(df["confirmado_hipotiroidismo"].sum())
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Sospechosos (TSH≥{TSH_CORTE})", f"{sosp:,}")
    c2.metric("Confirmados", f"{conf:,}")
    c3.metric("Tasa Confirmación", f"{conf/sosp:.1%}" if sosp else "—")

    st.plotly_chart(fig_embudo_diagnostico(df), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        if "sexo" in fdf.columns:
            st.plotly_chart(fig_distribucion_sexo(fdf), use_container_width=True)
    with c2:
        if "prematuro" in fdf.columns:
            st.plotly_chart(fig_distribucion_prematuridad(fdf), use_container_width=True)

    col_mun = "nombre_municipio" if "nombre_municipio" in fdf.columns else "ciudad"
    if col_mun in fdf.columns:
        graficar_mapa(fdf)

with t2:
    st.header("📊 Análisis de TSH Neonatal")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(fig_histograma_tsh(fdf, tsh_umbral), use_container_width=True)
    with c2:
        fig = fig_scatter_tsh1_vs_tsh2(fdf, tsh_umbral)
        if fig: st.plotly_chart(fig, use_container_width=True)
        else:   st.info("Aún no hay registros con 2ª muestra.")
    c1, c2 = st.columns(2)
    with c1:
        if "sexo" in fdf.columns:
            st.plotly_chart(fig_boxplot_tsh_sexo(fdf, tsh_umbral), use_container_width=True)
    with c2:
        if "prematuro" in fdf.columns:
            st.plotly_chart(fig_boxplot_tsh_prematuridad(fdf, tsh_umbral), use_container_width=True)

with t3:
    st.header("⏱️ Análisis Temporal")
    fig = fig_evolucion_temporal(fdf)
    if fig: st.plotly_chart(fig, use_container_width=True)
    else:   st.info("No hay suficientes datos temporales aún.")

with t4:
    st.header("🔬 Factores de Riesgo")
    fig = fig_peso_vs_tsh(fdf, tsh_umbral)
    if fig: st.plotly_chart(fig, use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        fig = fig_incidencia_por_tipo_muestra(fdf)
        if fig: st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = fig_incidencia_por_sexo(fdf)
        if fig: st.plotly_chart(fig, use_container_width=True)

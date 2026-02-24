# utils/graficos.py
# ─── Funciones de gráficas — cada una retorna un go.Figure ───────────────────
#
# Principio: estas funciones solo construyen y retornan figuras.
# El st.plotly_chart() siempre se llama desde la página, no aquí.
# Así las gráficas son reutilizables en cualquier página sin depender de Streamlit.

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

from utils.constantes import TSH_CORTE

# ── Paleta compartida ─────────────────────────────────────────────────────────
COLOR_NORMAL    = "#4682B4"
COLOR_SOSPECHA  = "#FFA500"
COLOR_CONFIRMADO= "#FF4500"
COLOR_TSH       = "#3CB371"


# ══════════════════════════════════════════════════════════════════════════════
# RESUMEN EJECUTIVO
# ══════════════════════════════════════════════════════════════════════════════

def fig_embudo_diagnostico(df: pd.DataFrame) -> go.Figure:
    """
    Pirámide/embudo: Tamizados → Sospechosos → Confirmados.
    Usa el DataFrame completo (sin filtrar) para mostrar totales reales.
    """
    total = df.shape[0]
    sosp  = int(df["sospecha_hipotiroidismo"].sum())
    conf  = int(df["confirmado_hipotiroidismo"].sum())

    fig = go.Figure(go.Funnel(
        y=["Tamizados", f"TSH ≥ {TSH_CORTE}", "Confirmados"],
        x=[total, sosp, conf],
        textinfo="value+percent initial",
        marker={"color": [COLOR_NORMAL, COLOR_SOSPECHA, COLOR_CONFIRMADO]},
    ))
    fig.update_layout(title="Pirámide de Diagnóstico", height=400)
    return fig


def fig_distribucion_sexo(df: pd.DataFrame) -> go.Figure:
    """Barras agrupadas: Normal vs Hipotiroidismo por sexo."""
    sc = df.groupby(["sexo", "confirmado_hipotiroidismo"]).size().unstack(fill_value=0)
    for v in [False, True]:
        if v not in sc.columns:
            sc[v] = 0
    sc.columns = ["Normal", "Hipotiroidismo"]
    return px.bar(
        sc.reset_index(), x="sexo", y=["Normal", "Hipotiroidismo"],
        barmode="group", title="Distribución por Sexo",
        color_discrete_map={"Normal": COLOR_NORMAL, "Hipotiroidismo": COLOR_CONFIRMADO},
    )


def fig_distribucion_prematuridad(df: pd.DataFrame) -> go.Figure:
    """Barras agrupadas: Normal vs Hipotiroidismo por prematuridad."""
    pc = df.copy()
    pc["prematuro"] = pc["prematuro"].fillna(False)
    pc = pc.groupby(["prematuro", "confirmado_hipotiroidismo"]).size().unstack(fill_value=0)
    for v in [False, True]:
        if v not in pc.columns:
            pc[v] = 0
    pc.columns = ["Normal", "Hipotiroidismo"]
    pc = pc.reset_index()
    pc["prematuro"] = pc["prematuro"].map({True: "Prematuro", False: "No Prematuro"})
    return px.bar(
        pc, x="prematuro", y=["Normal", "Hipotiroidismo"],
        barmode="group", title="Distribución por Prematuridad",
        color_discrete_map={"Normal": COLOR_NORMAL, "Hipotiroidismo": COLOR_CONFIRMADO},
    )


def graficar_mapa(df: pd.DataFrame):
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


# ══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS TSH
# ══════════════════════════════════════════════════════════════════════════════

def fig_histograma_tsh(df: pd.DataFrame, tsh_umbral: float = TSH_CORTE) -> go.Figure:
    """Histograma de TSH neonatal con línea de umbral. Recorta outliers al p99."""
    cap = df["tsh_neonatal"].quantile(0.99)
    fig = px.histogram(
        df[df["tsh_neonatal"] <= cap], x="tsh_neonatal", nbins=30,
        color_discrete_sequence=[COLOR_TSH],
        labels={"tsh_neonatal": "TSH (mIU/L)"},
        title="Distribución de TSH Neonatal",
    )
    fig.add_vline(
        x=tsh_umbral, line_dash="dash", line_color="red",
        annotation_text=f"Umbral: {tsh_umbral}",
    )
    return fig


def fig_scatter_tsh1_vs_tsh2(df: pd.DataFrame, tsh_umbral: float = TSH_CORTE) -> go.Figure | None:
    """
    Scatter TSH 1ª vs TSH 2ª muestra, coloreado por confirmación.
    Retorna None si no hay registros con 2ª muestra.
    """
    d = df.dropna(subset=["tsh_neonatal", "resultado_muestra_2"])
    d = d[d["resultado_muestra_2"] > 0]
    if d.empty:
        return None
    fig = px.scatter(
        d, x="tsh_neonatal", y="resultado_muestra_2",
        color="confirmado_hipotiroidismo",
        color_discrete_map={True: COLOR_CONFIRMADO, False: COLOR_NORMAL},
        title="TSH 1ª vs 2ª Muestra",
        labels={"tsh_neonatal": "TSH 1ª (mIU/L)", "resultado_muestra_2": "TSH 2ª (mIU/L)"},
    )
    fig.add_hline(y=tsh_umbral, line_dash="dash", line_color="red")
    fig.add_vline(x=tsh_umbral, line_dash="dash", line_color="red")
    return fig


def fig_boxplot_tsh_sexo(df: pd.DataFrame, tsh_umbral: float = TSH_CORTE) -> go.Figure:
    """Boxplot TSH por sexo."""
    fig = px.box(df, x="sexo", y="tsh_neonatal", color="sexo",
                 points="outliers", title="TSH por Sexo",
                 labels={"tsh_neonatal": "TSH (mIU/L)"})
    fig.add_hline(y=tsh_umbral, line_dash="dash", line_color="red",
                  annotation_text=f"Umbral: {tsh_umbral}")
    fig.update_yaxes(range=[0, 40])
    return fig


def fig_boxplot_tsh_prematuridad(df: pd.DataFrame, tsh_umbral: float = TSH_CORTE) -> go.Figure:
    """Boxplot TSH por prematuridad."""
    ymax = max(30, df["tsh_neonatal"].quantile(0.95)) if not df.empty else 30
    fig = px.box(df, x="prematuro", y="tsh_neonatal", color="prematuro",
                 points="outliers", title="TSH por Prematuridad",
                 labels={"tsh_neonatal": "TSH (mIU/L)"})
    fig.add_hline(y=tsh_umbral, line_dash="dash", line_color="red",
                  annotation_text=f"Umbral: {tsh_umbral}")
    fig.update_yaxes(range=[0, ymax])
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS TEMPORAL
# ══════════════════════════════════════════════════════════════════════════════

def fig_evolucion_temporal(df: pd.DataFrame) -> go.Figure | None:
    """
    Líneas de sospechosos y confirmados por mes, con tasa de confirmación en eje Y2.
    Retorna None si no hay datos de fecha válidos.
    """
    if "fecha_nacimiento" not in df.columns or df["fecha_nacimiento"].isna().all():
        return None

    tmp = df.copy()
    tmp["año_mes"] = tmp["fecha_nacimiento"].dt.to_period("M")
    temp = (
        tmp.groupby("año_mes")
        .agg(
            sospechosos=("sospecha_hipotiroidismo", "sum"),
            confirmados=("confirmado_hipotiroidismo", "sum"),
        )
        .reset_index()
    )
    temp["año_mes"] = temp["año_mes"].dt.to_timestamp()
    temp["tasa"]    = temp["confirmados"] / temp["sospechosos"].replace(0, np.nan)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=temp["año_mes"], y=temp["sospechosos"],
        mode="lines+markers", name="Sospechosos",
        line=dict(color=COLOR_SOSPECHA, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=temp["año_mes"], y=temp["confirmados"],
        mode="lines+markers", name="Confirmados",
        line=dict(color=COLOR_CONFIRMADO, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=temp["año_mes"], y=temp["tasa"],
        mode="lines", name="Tasa confirmación",
        line=dict(color=COLOR_NORMAL, dash="dot"),
        yaxis="y2",
    ))
    fig.update_layout(
        title="Evolución Temporal de Casos",
        yaxis=dict(title="Número de Casos"),
        yaxis2=dict(title="Tasa de Confirmación", overlaying="y",
                    side="right", range=[0, 1]),
        legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# FACTORES DE RIESGO
# ══════════════════════════════════════════════════════════════════════════════

def fig_peso_vs_tsh(df: pd.DataFrame, tsh_umbral: float = TSH_CORTE) -> go.Figure | None:
    """Scatter peso al nacer vs TSH con línea de tendencia."""
    if "peso" not in df.columns:
        return None
    dr = df.copy()
    dr["peso_kg"] = pd.to_numeric(dr["peso"], errors="coerce") / 1000
    dr = dr.dropna(subset=["peso_kg", "tsh_neonatal"])
    if dr.empty:
        return None
    fig = px.scatter(
        dr, x="peso_kg", y="tsh_neonatal",
        color="confirmado_hipotiroidismo",
        color_discrete_map={True: COLOR_CONFIRMADO, False: COLOR_NORMAL},
        title="Peso al Nacer vs TSH",
        labels={"peso_kg": "Peso (kg)", "tsh_neonatal": "TSH (mIU/L)"},
        trendline="ols", opacity=0.7,
    )
    fig.add_hline(y=tsh_umbral, line_dash="dash", line_color="red",
                  annotation_text=f"Umbral: {tsh_umbral}")
    return fig


def fig_incidencia_por_tipo_muestra(df: pd.DataFrame) -> go.Figure | None:
    """Barras de incidencia (%) por tipo de muestra."""
    if "tipo_muestra" not in df.columns or "id" not in df.columns:
        return None
    tm = (
        df.groupby("tipo_muestra")
        .agg(total=("id", "count"), conf=("confirmado_hipotiroidismo", "sum"))
        .reset_index()
    )
    tm["incidencia"] = (tm["conf"] / tm["total"]) * 100
    return px.bar(
        tm, x="tipo_muestra", y="incidencia",
        title="Incidencia por Tipo de Muestra (%)",
        color="incidencia", color_continuous_scale="Reds",
        labels={"incidencia": "Incidencia (%)"},
    )


def fig_incidencia_por_sexo(df: pd.DataFrame) -> go.Figure | None:
    """Barras de incidencia (%) por sexo."""
    if "sexo" not in df.columns or "id" not in df.columns:
        return None
    sx = (
        df.groupby("sexo")
        .agg(total=("id", "count"), conf=("confirmado_hipotiroidismo", "sum"))
        .reset_index()
    )
    sx["incidencia"] = (sx["conf"] / sx["total"]) * 100
    return px.bar(
        sx, x="sexo", y="incidencia",
        title="Incidencia por Sexo (%)",
        color="incidencia", color_continuous_scale="Reds",
        labels={"incidencia": "Incidencia (%)"},
    )


# ══════════════════════════════════════════════════════════════════════════════
# ALERTAS (reutilizable desde pages/3)
# ══════════════════════════════════════════════════════════════════════════════

def fig_tsh_confirmados(df: pd.DataFrame) -> go.Figure:
    """Histograma de TSH 2ª muestra en casos confirmados."""
    return px.histogram(
        df, x="resultado_muestra_2", nbins=20,
        title="Distribución TSH 2ª Muestra (Confirmados)",
        labels={"resultado_muestra_2": "TSH 2ª (mIU/L)"},
        color_discrete_sequence=[COLOR_CONFIRMADO],
    )

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

import folium
from streamlit_folium import st_folium

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Hipotiroidismo Congénito",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("📊 Dashboard de Hipotiroidismo Congénito")
st.markdown("---")

# Cargar los datos
@st.cache_data

def load_data():
    try:
        # Cargar el CSV con low_memory=False para evitar problemas con tipos de datos mixtos
        df = pd.read_csv('../../data/dataset_corregido_v2b_anom2.csv', low_memory=False)
       
        # Convertir columnas de fecha a datetime 
        date_columns = ['fecha_ingreso', 'fecha_nacimiento', 'fecha_toma_muestra',
                        'fecha_resultado', 'fecha_toma_muestra_2', 'fecha_resultado_muestra_2',
                        'fecha_toma_rechazada', 'fecha_resultado_rechazada']
       
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
       
        # Convertir columnas booleanas
        bool_columns = ['prematuro', 'transfundido', 'informacion_completa',
                        'muestra_adecuada', 'muestra_rechazada']
       
        for col in bool_columns:
            if col in df.columns:
                # Mapear específicamente VERDADERO y FALSO
                df[col] = df[col].map({'VERDADERO': True, 'FALSO': False})
                # Convertir NaN a False
                #df[col] = df[col].fillna(False)
       
        # Manejar valores nulos en columnas numéricas clave
        df['tsh_neonatal'] = pd.to_numeric(df['tsh_neonatal'], errors='coerce').fillna(0)
        df['resultado_muestra_2'] = pd.to_numeric(df['resultado_muestra_2'], errors='coerce').fillna(0)
       
        # Crear columna 'sospecha_hipotiroidismo'
        df['sospecha_hipotiroidismo'] = df['tsh_neonatal'] >= 15
       
        # Crear columna 'confirmado_hipotiroidismo'
        # Solo es True si tsh_neonatal >= 15 Y resultado_muestra_2 >= 15
        df['confirmado_hipotiroidismo'] = (df['tsh_neonatal'] >= 15) & (df['resultado_muestra_2'] >= 15)
       
        return df
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return pd.DataFrame()

df = load_data()


def graficar_mapa_casos(df):

    # Diccionario de coordenadas para tus ciudades
    city_coordinates = {
        "Bogota": [4.6097, -74.0817],
        "Cundinamarca": [4.7000, -73.8000], # Coordenada central aproximada
        # Agrega aquí más ciudades según aparezcan en tu columna 'ciudad'
    }

    # Centrado en Colombia (o cerca de Bogotá para tu GeoJSON)
    m = folium.Map(location=[4.6097, -74.0817], zoom_start=6, tiles="cartodbpositron")
    
    # Agrupamos por 'ciudad' y sumamos 'confirmado_hipotiroidismo'
    # Nota: Asegúrate de que 'confirmado_hipotiroidismo' sea numérico (0 y 1)
    df_grouped = df.groupby('ciudad')['confirmado_hipotiroidismo'].sum().items()
    
    for city, casos in df_grouped:
        if city in city_coordinates:
            # Solo ponemos marcador si hay al menos 1 caso o para todas las ciudades
            folium.Marker(
                location=city_coordinates[city],
                popup=f"<b>{city}</b><br>Casos Confirmados: {int(casos)}",
                tooltip=city,
                icon=folium.Icon(color='red', icon='plus-square', prefix='fa')
            ).add_to(m)
        else:
            # Opcional: mostrar advertencia si falta una coordenada
            pass

    # Mostrar en Streamlit
    st_folium(m, width=700, height=500)

# Verificar que los datos se cargaron correctamente
if df.empty:
    st.error("No se pudieron cargar los datos. Por favor verifica el archivo CSV.")
    st.stop()

# Mostrar información general
st.header("🔍 Información General del Dataset")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total de Registros", f"{df.shape[0]:,}")
with col2:
    st.metric("Casos Sospechosos (TSH ≥ 15)", f"{df['sospecha_hipotiroidismo'].sum():,}")
with col3:
    st.metric("Casos Confirmados", f"{df['confirmado_hipotiroidismo'].sum():,}")
with col4:
    # Calcular el promedio de días hasta el resultado
    dias_promedio = round(df['dias_pasados'].mean(), 1)
    st.metric("Promedio Días hasta Resultado", f"{dias_promedio}")

# Sidebar para filtros
st.sidebar.header("📋 Filtros")

# Filtro por año
años_disponibles = sorted(df['fecha_nacimiento'].dt.year.unique().tolist())
años_seleccionados = st.sidebar.multiselect(
    "Seleccionar Años:",
    options=años_disponibles,
    default=años_disponibles
)

# Filtro por sexo
sexos_disponibles = sorted(df['sexo'].unique().tolist())
sexos_seleccionados = st.sidebar.multiselect(
    "Seleccionar Sexo:",
    options=sexos_disponibles,
    default=sexos_disponibles
)

# Filtro por condición de prematuro
prematuro_opciones = ["Todos", "Prematuros", "No Prematuros"]
prematuro_seleccionado = st.sidebar.radio("Condición de Nacimiento:", prematuro_opciones)

# Filtro por tipo de muestra
tipos_muestra = sorted(df['tipo_muestra'].unique().tolist())
tipo_muestra_seleccionado = st.sidebar.multiselect(
    "Tipo de Muestra:",
    options=tipos_muestra,
    default=tipos_muestra
)

# Filtro por departamento
departamentos = sorted(df['departamento'].unique().tolist())
departamento_seleccionado = st.sidebar.multiselect(
    "Departamento:",
    options=departamentos,
    default=departamentos
)

# Filtro por ciudad
ciudades = sorted(df['ciudad'].unique().tolist())
ciudad_seleccionado = st.sidebar.multiselect(
    "Ciudad:",
    options=ciudades,
    default=ciudades
)

# Filtro por estado de hipotiroidismo
hipotiroidismo_opciones = ["Todos", "Sospechosos", "Confirmados", "Normales"]
hipotiroidismo_seleccionado = st.sidebar.radio("Estado de Hipotiroidismo:", hipotiroidismo_opciones)

# Aplicar filtros
filtered_df = df.copy()

if años_seleccionados:
    filtered_df = filtered_df[filtered_df['fecha_nacimiento'].dt.year.isin(años_seleccionados)]

if sexos_seleccionados:
    filtered_df = filtered_df[filtered_df['sexo'].isin(sexos_seleccionados)]

if prematuro_seleccionado == "Prematuros":
    filtered_df = filtered_df[filtered_df['prematuro'] == True]
elif prematuro_seleccionado == "No Prematuros":
    filtered_df = filtered_df[filtered_df['prematuro'] == False]

if tipo_muestra_seleccionado:
    filtered_df = filtered_df[filtered_df['tipo_muestra'].isin(tipo_muestra_seleccionado)]

if departamento_seleccionado:
    filtered_df = filtered_df[filtered_df['departamento'].isin(departamento_seleccionado)]

if ciudad_seleccionado:
    filtered_df = filtered_df[filtered_df['ciudad'].isin(ciudad_seleccionado)]

# Aplicar filtro de estado de hipotiroidismo
if hipotiroidismo_seleccionado == "Sospechosos":
    filtered_df = filtered_df[filtered_df['sospecha_hipotiroidismo'] == True]
elif hipotiroidismo_seleccionado == "Confirmados":
    filtered_df = filtered_df[filtered_df['confirmado_hipotiroidismo'] == True]
elif hipotiroidismo_seleccionado == "Normales":
    filtered_df = filtered_df[filtered_df['sospecha_hipotiroidismo'] == False]

# Mostrar el número de registros después de filtrar
st.sidebar.markdown(f"**Registros después de filtrar:** {filtered_df.shape[0]:,}")

# Umbral para TSH
st.sidebar.header("⚙️ Configuración")
tsh_umbral = st.sidebar.slider(
    "Umbral TSH (mIU/L):",
    min_value=1.0,
    max_value=30.0,
    value=15.0,
    step=0.5
)

# Pestaña de resumen ejecutivo
st.markdown("---")
tabs = st.tabs(["Resumen Ejecutivo", "Análisis de TSH", "Análisis Temporal", "Factores de Riesgo", "Casos Confirmados"])

with tabs[0]:
    st.header("📌 Resumen Ejecutivo")
    
    # Estadísticas clave
    summary_metrics = {
        "total_casos": df.shape[0],
        "sospechosos": df['sospecha_hipotiroidismo'].sum(),
        "confirmados": df['confirmado_hipotiroidismo'].sum(),
        "tasa_confirmacion": df['confirmado_hipotiroidismo'].sum() / df['sospecha_hipotiroidismo'].sum() if df['sospecha_hipotiroidismo'].sum() > 0 else 0,
        "incidencia": df['confirmado_hipotiroidismo'].sum() / df.shape[0] if df.shape[0] > 0 else 0,
    }
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Casos Sospechosos (TSH ≥ 15)", f"{summary_metrics['sospechosos']:,}")
    with col2:
        st.metric("Casos Confirmados", f"{summary_metrics['confirmados']:,}")
    with col3:
        st.metric("Tasa de Confirmación", f"{summary_metrics['tasa_confirmacion']:.1%}")
    
    # Gráfico de pirámide de diagnóstico
    stages = ['Tamizados', 'TSH ≥ 15', 'Confirmados']
    values = [df.shape[0], df['sospecha_hipotiroidismo'].sum(), df['confirmado_hipotiroidismo'].sum()]
    
    fig_funnel = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textinfo="value+percent initial",
        marker={"color": ["#4682B4", "#FFA500", "#FF4500"]}
    ))
    
    fig_funnel.update_layout(
        title="Pirámide de Diagnóstico de Hipotiroidismo Congénito",
        width=800,
        height=500
    )
    
    st.plotly_chart(fig_funnel, use_container_width=True)
    
    # Distribución por sexo y prematuridad
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribución por sexo
        #sex_counts = filtered_df.groupby(['sexo', 'confirmado_hipotiroidismo']).size().unstack(fill_value=0)
        #sex_counts.columns = ['Normal', 'Hipotiroidismo']
        #sex_counts = sex_counts.reset_index()

        # Agrupar y contar los casos por sexo y estado de hipotiroidismo
        sex_counts = filtered_df.groupby(['sexo', 'confirmado_hipotiroidismo']).size().unstack(fill_value=0)

        # Asegurarse de que haya exactamente 2 columnas (False y True)
        if False not in sex_counts.columns:
            sex_counts[False] = 0  # Agregar columna para casos no confirmados
        if True not in sex_counts.columns:
            sex_counts[True] = 0  # Agregar columna para casos confirmados

        # Renombrar las columnas
        sex_counts.columns = ['Normal', 'Hipotiroidismo']

        # Resetear el índice para convertir 'sexo' en una columna explícita
        sex_counts_reset = sex_counts.reset_index()

        # Crear el gráfico de barras
        fig_sex = px.bar(
            sex_counts_reset,  # Usar el DataFrame con el índice reseteado
            x="sexo",          # Eje X: sexo (Masculino/Femenino)
            y=["Normal", "Hipotiroidismo"],  # Eje Y: valores de las columnas Normal y Hipotiroidismo
            title="Distribución de Casos por Sexo",  # Título del gráfico
            labels={
                "value": "Cantidad de Casos",  # Etiqueta del eje Y
                "sexo": "Sexo",                # Etiqueta del eje X
                "variable": "Estado"           # Leyenda: Normal vs Hipotiroidismo
            },
            color_discrete_map={
                "Normal": "#4682B4",       # Color para casos normales
                "Hipotiroidismo": "#FF4500"  # Color para casos confirmados
            },
            barmode='group'  # Agrupar las barras (Normal y Hipotiroidismo juntas para cada sexo)
        )

        # Personalizar el diseño del gráfico
        fig_sex.update_layout(
            xaxis_title="Sexo",  # Etiqueta del eje X
            yaxis_title="Cantidad de Casos",  # Etiqueta del eje Y
            legend_title="Estado",  # Título de la leyenda
            showlegend=True,  # Mostrar la leyenda
            template="plotly_white"  # Usar un tema claro para el gráfico
        )

        # Mostrar el gráfico en Streamlit
        st.plotly_chart(fig_sex, use_container_width=True)
        

        kv2 = '''
        fig_sex = px.bar(
            sex_counts, 
            x="sexo", 
            y=["Normal", "Hipotiroidismo"],
            title="Distribución por Sexo",
            labels={"value": "Cantidad", "sexo": "Sexo", "variable": "Estado"},
            color_discrete_map={"Normal": "#4682B4", "Hipotiroidismo": "#FF4500"}
        )
        fig_sex.update_layout(barmode='group')
        st.plotly_chart(fig_sex, use_container_width=True)
        '''
    
    with col2:
        kv3 = '''
        # Distribución por prematuridad
        premature_counts = filtered_df.groupby(['prematuro', 'confirmado_hipotiroidismo']).size().unstack(fill_value=0)
        premature_counts.columns = ['Normal', 'Hipotiroidismo']
        premature_counts = premature_counts.reset_index()
        premature_counts['prematuro'] = premature_counts['prematuro'].map({True: 'Prematuro', False: 'No Prematuro'})
        
        fig_premature = px.bar(
            premature_counts, 
            x="prematuro", 
            y=["Normal", "Hipotiroidismo"],
            title="Distribución por Prematuridad",
            labels={"value": "Cantidad", "prematuro": "Condición", "variable": "Estado"},
            color_discrete_map={"Normal": "#4682B4", "Hipotiroidismo": "#FF4500"}
        )
        fig_premature.update_layout(barmode='group')
        st.plotly_chart(fig_premature, use_container_width=True)
        '''
        # Manejar valores NaN en 'prematuro' (eliminar o rellenar)
        #filtered_df = filtered_df.dropna(subset=['prematuro'])  # Opción 1: Eliminar filas con NaN
        filtered_df['prematuro'] = filtered_df['prematuro'].fillna(False)  # Opción 2: Rellenar NaN con False
        
        # Distribución por prematuridad
        premature_counts = filtered_df.groupby(['prematuro', 'confirmado_hipotiroidismo']).size().unstack(fill_value=0)
        #print(premature_counts)
        #print(filtered_df[['prematuro', 'confirmado_hipotiroidismo']].head())
        # Asegurarse de que haya exactamente 2 columnas (False y True)
        if False not in premature_counts.columns:
            premature_counts[False] = 0  # Agregar columna para casos no confirmados
        if True not in premature_counts.columns:
            premature_counts[True] = 0  # Agregar columna para casos confirmados

        # Renombrar las columnas
        premature_counts.columns = ['Normal', 'Hipotiroidismo']

        # Resetear el índice para convertir 'prematuro' en una columna explícita
        premature_counts_reset = premature_counts.reset_index()

        # Convertir la columna 'prematuro' a etiquetas legibles
        premature_counts_reset['prematuro'] = premature_counts_reset['prematuro'].map({True: 'Prematuro', False: 'No Prematuro'})

        # Crear el gráfico de barras
        fig_premature = px.bar(
            premature_counts_reset, 
            x="prematuro", 
            y=["Normal", "Hipotiroidismo"],
            title="Distribución de Casos por Prematuridad",
            labels={"value": "Cantidad de Casos", "prematuro": "Prematuridad", "variable": "Estado"},
            color_discrete_map={"Normal": "#4682B4", "Hipotiroidismo": "#FF4500"},
            barmode='group'
        )

        # Personalizar el diseño del gráfico
        fig_premature.update_layout(
            xaxis_title="Prematuridad",
            yaxis_title="Cantidad de Casos",
            legend_title="Estado",
            showlegend=True,
            template="plotly_white"
        )

        # Mostrar el gráfico en Streamlit
        st.plotly_chart(fig_premature, use_container_width=True)


    graficar_mapa_casos(filtered_df)


with tabs[1]:
    st.header("📊 Análisis de TSH Neonatal")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Histograma de valores TSH
        st.subheader("Distribución de TSH Neonatal")
        
        # Filtrar valores extremos para mejor visualización
        tsh_max_visual = filtered_df['tsh_neonatal'].quantile(0.99)
        df_tsh_visual = filtered_df[filtered_df['tsh_neonatal'] <= tsh_max_visual]
        
        fig_tsh_hist = px.histogram(
            df_tsh_visual, 
            x='tsh_neonatal',
            nbins=30,
            color_discrete_sequence=['#3CB371'],
            labels={'tsh_neonatal': 'TSH Neonatal (mIU/L)'}
        )
        
        # Añadir línea vertical para el umbral
        fig_tsh_hist.add_vline(
            x=15, 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"Umbral: 15 mIU/L",
            annotation_position="top right"
        )
        
        fig_tsh_hist.update_layout(xaxis_title="Valor de TSH (mIU/L)", yaxis_title="Frecuencia")
        st.plotly_chart(fig_tsh_hist, use_container_width=True)
    
    with col2:
        # Comparación de TSH inicial vs segunda muestra
        st.subheader("Comparación TSH Inicial vs Segunda Muestra")
        
        # Filtrar solo casos con segunda muestra
        df_with_second = filtered_df.dropna(subset=['tsh_neonatal', 'resultado_muestra_2'])
        
        fig_scatter_tsh = px.scatter(
            df_with_second,
            x='tsh_neonatal',
            y='resultado_muestra_2',
            color='confirmado_hipotiroidismo',
            color_discrete_map={True: '#FF4500', False: '#4682B4'},
            labels={
                'tsh_neonatal': 'TSH Neonatal Primera Muestra (mIU/L)',
                'resultado_muestra_2': 'TSH Segunda Muestra (mIU/L)',
                'confirmado_hipotiroidismo': 'Hipotiroidismo Confirmado'
            },
            opacity=0.7
        )
        
        # Añadir líneas de umbral
        fig_scatter_tsh.add_hline(
            y=15, 
            line_dash="dash", 
            line_color="red"
        )
        fig_scatter_tsh.add_vline(
            x=15, 
            line_dash="dash", 
            line_color="red"
        )
        
        fig_scatter_tsh.update_layout(
            xaxis_title="TSH Primera Muestra (mIU/L)", 
            yaxis_title="TSH Segunda Muestra (mIU/L)"
        )
        st.plotly_chart(fig_scatter_tsh, use_container_width=True)
    
    # Boxplot de TSH por sexo y prematuridad
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("TSH por Sexo")
        
        fig_box_sex = px.box(
            filtered_df,
            x='sexo',
            y='tsh_neonatal',
            color='sexo',
            points="outliers",
            labels={'sexo': 'Sexo', 'tsh_neonatal': 'TSH Neonatal (mIU/L)'},
            # OPCIÓN A: Escala logarítmica (evita el aplanamiento de forma matemática)
            # log_y=True 
        )
        
        # OPCIÓN B: Limitar el rango del eje Y manualmente (evita el aplanamiento visual)
        # Ajustamos el rango de 0 a un poco más del umbral (ej. 30) o el percentil 95
        fig_box_sex.update_yaxes(range=[0, 40]) 

        fig_box_sex.add_hline(
            y=15, 
            line_dash="dash", 
            line_color="red",
            annotation_text="Umbral: 15 mIU/L",
            annotation_position="top right"
        )

        # Mejorar la estética para que no se vea "apretado"
        fig_box_sex.update_layout(
            height=500,  # Forzar una altura fija ayuda a que no se vea aplanado
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig_box_sex, use_container_width=True)
    
    with col2:
        st.subheader("TSH por Prematuridad")
        
        # 1. Crear el gráfico base
        fig_box_premature = px.box(
            filtered_df,
            x='prematuro',
            y='tsh_neonatal',
            color='prematuro',
            points="outliers",
            labels={'prematuro': 'Condición', 'tsh_neonatal': 'TSH Neonatal (mIU/L)'},
            category_orders={"prematuro": [True, False]} # Mantenemos el orden lógico
        )

        # 2. NORMALIZACIÓN VISUAL (Evita el efecto aplanado)
        # Calculamos un límite superior dinámico: el percentil 95 o al menos 30 para ver el umbral
        if not filtered_df.empty:
            ymax = max(30, filtered_df['tsh_neonatal'].quantile(0.95))
            fig_box_premature.update_yaxes(range=[0, ymax])

        # 3. Ajuste de etiquetas y estética
        fig_box_premature.update_xaxes(
            ticktext=["Prematuro", "No Prematuro"], 
            tickvals=[True, False]
        )
        
        fig_box_premature.add_hline(
            y=15, 
            line_dash="dash", 
            line_color="red",
            annotation_text="Umbral: 15 mIU/L",
            annotation_position="top right"
        )

        fig_box_premature.update_layout(
            height=500, # Altura fija para consistencia visual
            showlegend=False # Opcional: ocultar leyenda si las etiquetas del eje X son claras
        )
        
        st.plotly_chart(fig_box_premature, use_container_width=True)

with tabs[2]:
    st.header("⏱️ Análisis Temporal")
    
    # Agrupar datos por mes y año
    filtered_df['año_mes'] = filtered_df['fecha_nacimiento'].dt.to_period('M')
    
    # Tendencia temporal de casos
    temporal_df = filtered_df.groupby(['año_mes']).agg(
        total_casos=('tsh_neonatal', 'count'),
        casos_sospechosos=('sospecha_hipotiroidismo', 'sum'),
        casos_confirmados=('confirmado_hipotiroidismo', 'sum'),
        tsh_promedio=('tsh_neonatal', 'mean')
    ).reset_index()
    
    temporal_df['año_mes'] = temporal_df['año_mes'].dt.to_timestamp()
    temporal_df['tasa_confirmacion'] = temporal_df['casos_confirmados'] / temporal_df['casos_sospechosos']
    temporal_df['incidencia'] = temporal_df['casos_confirmados'] / temporal_df['total_casos']
    
    # Gráfico de línea para casos y tasa de confirmación
    fig_temporal = go.Figure()
    
    fig_temporal.add_trace(go.Scatter(
        x=temporal_df['año_mes'],
        y=temporal_df['casos_sospechosos'],
        mode='lines+markers',
        name='Casos Sospechosos',
        line=dict(color='#FFA500', width=2)
    ))
    
    fig_temporal.add_trace(go.Scatter(
        x=temporal_df['año_mes'],
        y=temporal_df['casos_confirmados'],
        mode='lines+markers',
        name='Casos Confirmados',
        line=dict(color='#FF4500', width=2)
    ))
    
    fig_temporal.add_trace(go.Scatter(
        x=temporal_df['año_mes'],
        y=temporal_df['tasa_confirmacion'],
        mode='lines',
        name='Tasa de Confirmación',
        line=dict(color='#4682B4', width=2, dash='dot'),
        yaxis='y2'
    ))
    
    fig_temporal.update_layout(
        title='Evolución Temporal de Casos de Hipotiroidismo Congénito',
        xaxis_title='Fecha',
        yaxis=dict(
            title={'text': 'Número de Casos', 'font': {'color': '#FF4500'}},  # Corrección aquí
            tickfont=dict(color='#FF4500')
        ),
        yaxis2=dict(
            title={'text': 'Tasa de Confirmación', 'font': {'color': '#4682B4'}},  # Corrección aquí
            tickfont=dict(color='#4682B4'),
            anchor='x',
            overlaying='y',
            side='right',
            range=[0, 1]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    st.plotly_chart(fig_temporal, use_container_width=True)
    
    # Análisis de estacionalidad (por mes)
    filtered_df['mes'] = filtered_df['fecha_nacimiento'].dt.month
    
    seasonality_df = filtered_df.groupby('mes').agg(
        total_casos=('tsh_neonatal', 'count'),
        casos_sospechosos=('sospecha_hipotiroidismo', 'sum'),
        casos_confirmados=('confirmado_hipotiroidismo', 'sum'),
        tsh_promedio=('tsh_neonatal', 'mean')
    ).reset_index()
    
    seasonality_df['mes_nombre'] = seasonality_df['mes'].map({
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    })
    
    fig_seasonality = px.line(
        seasonality_df,
        x='mes',
        y=['casos_sospechosos', 'casos_confirmados', 'tsh_promedio'],
        labels={
            'mes': 'Mes',
            'value': 'Valor',
            'variable': 'Métrica'
        },
        title='Estacionalidad de Casos por Mes',
        color_discrete_map={
            'casos_sospechosos': '#FFA500',
            'casos_confirmados': '#FF4500',
            'tsh_promedio': '#4682B4'
        }
    )
    
    fig_seasonality.update_layout(
        xaxis=dict(
            tickvals=list(range(1, 13)),
            ticktext=['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        )
    )
    
    st.plotly_chart(fig_seasonality, use_container_width=True)
    
    # Análisis de tiempos de procesamiento
    st.subheader("Análisis de Tiempos de Procesamiento")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Histograma de días hasta el resultado
        fig_dias = px.histogram(
            filtered_df,
            x='dias_pasados',
            nbins=20,
            title='Distribución de Días hasta el Resultado',
            labels={'dias_pasados': 'Días hasta Resultado'},
            color_discrete_sequence=['#4682B4']
        )
        st.plotly_chart(fig_dias, use_container_width=True)
    
    with col2:
        # Comparación de tiempos entre casos normales y anormales
        tiempos_df = filtered_df.groupby('sospecha_hipotiroidismo')['dias_pasados'].mean().reset_index()
        tiempos_df['sospecha_hipotiroidismo'] = tiempos_df['sospecha_hipotiroidismo']


        tiempos_df['Estado'] = tiempos_df['sospecha_hipotiroidismo'].map({True: 'Sospechoso (TSH ≥ 15)', False: 'Normal (TSH < 15)'})
        
        fig_tiempos = px.bar(
            tiempos_df,
            x='Estado',
            y='dias_pasados',
            title='Tiempo Promedio de Procesamiento por Estado',
            labels={'dias_pasados': 'Días Promedio', 'Estado': 'Estado'},
            color='Estado',
            color_discrete_map={
                'Sospechoso (TSH ≥ 15)': '#FF4500',
                'Normal (TSH < 15)': '#4682B4'
            }
        )
        st.plotly_chart(fig_tiempos, use_container_width=True)

with tabs[3]:
    st.header("🔬 Análisis de Factores de Riesgo")
    
    # Relación entre peso al nacer y TSH
    st.subheader("Relación entre Peso al Nacer y TSH")
    
    # Conversión de peso a kilogramos para mejor visualización
    filtered_df['peso_kg'] = filtered_df['peso'] / 1000
    
    fig_peso_tsh = px.scatter(
        filtered_df,
        x='peso_kg',
        y='tsh_neonatal',
        color='confirmado_hipotiroidismo',
        color_discrete_map={True: '#FF4500', False: '#4682B4'},
        labels={
            'peso_kg': 'Peso al Nacer (kg)',
            'tsh_neonatal': 'TSH Neonatal (mIU/L)',
            'confirmado_hipotiroidismo': 'Hipotiroidismo Confirmado'
        },
        trendline="ols",
        opacity=0.7
    )
    
    fig_peso_tsh.add_hline(
        y=15, 
        line_dash="dash", 
        line_color="red",
        annotation_text="Umbral TSH: 15 mIU/L",
        annotation_position="top right"
    )
    
    st.plotly_chart(fig_peso_tsh, use_container_width=True)
    
    # Estadísticas por factores de riesgo
    st.subheader("Incidencia por Factores de Riesgo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Incidencia por tipo de muestra
        tipo_muestra_df = filtered_df.groupby('tipo_muestra').agg(
            total=('id', 'count'),
            confirmados=('confirmado_hipotiroidismo', 'sum')
        ).reset_index()
        
        tipo_muestra_df['incidencia'] = (tipo_muestra_df['confirmados'] / tipo_muestra_df['total']) * 100
        
        fig_tipo_muestra = px.bar(
            tipo_muestra_df,
            x='tipo_muestra',
            y='incidencia',
            title='Incidencia por Tipo de Muestra',
            labels={'incidencia': 'Incidencia (%)', 'tipo_muestra': 'Tipo de Muestra'},
            color='incidencia',
            color_continuous_scale='Reds'
        )
        
        st.plotly_chart(fig_tipo_muestra, use_container_width=True)
    
    with col2:
        # Incidencia por sexo
        sexo_df = filtered_df.groupby('sexo').agg(
            total=('id', 'count'),
            confirmados=('confirmado_hipotiroidismo', 'sum')
        ).reset_index()
        
        sexo_df['incidencia'] = (sexo_df['confirmados'] / sexo_df['total']) * 100
        
        fig_sexo = px.bar(
            sexo_df,
            x='sexo',
            y='incidencia',
            title='Incidencia por Sexo',
            labels={'incidencia': 'Incidencia (%)', 'sexo': 'Sexo'},
            color='incidencia',
            color_continuous_scale='Reds'
        )
        
        st.plotly_chart(fig_sexo, use_container_width=True)
    
    # Factores combinados: prematuridad y peso
    st.subheader("Factores Combinados: Prematuridad y Peso")
    
    # Crear rangos de peso
    bins = [0, 1500, 2500, 4000, 10000]
    labels = ['Muy bajo (<1.5kg)', 'Bajo (1.5-2.5kg)', 'Normal (2.5-4kg)', 'Alto (>4kg)']
    filtered_df['rango_peso'] = pd.cut(filtered_df['peso'], bins=bins, labels=labels)
    
    # Agrupar por prematuridad y rango de peso
    peso_prematuro_df = filtered_df.groupby(['prematuro', 'rango_peso']).agg(
        total=('id', 'count'),
        confirmados=('confirmado_hipotiroidismo', 'sum')
    ).reset_index()
    
    peso_prematuro_df['incidencia'] = (peso_prematuro_df['confirmados'] / peso_prematuro_df['total']) * 100
    peso_prematuro_df['prematuro_label'] = peso_prematuro_df['prematuro'].map({True: 'Prematuro', False: 'No Prematuro'})
    
    fig_peso_prematuro = px.bar(
        peso_prematuro_df,
        x='rango_peso',
        y='incidencia',
        color='prematuro_label',
        barmode='group',
        title='Incidencia por Peso y Prematuridad',
        labels={
            'incidencia': 'Incidencia (%)', 
            'rango_peso': 'Rango de Peso', 
            'prematuro_label': 'Condición'
        },
        color_discrete_map={'Prematuro': '#FF4500', 'No Prematuro': '#4682B4'}
    )
    
    st.plotly_chart(fig_peso_prematuro, use_container_width=True)
    
    # Matriz de correlación entre variables numéricas
    st.subheader("Correlaciones entre Variables Numéricas")
    
    # Convertir la columna 'sexo' a valores numéricos
    filtered_df['sexo_num'] = filtered_df['sexo'].map({'MASCULINO': 0, 'FEMENINO': 1})

    # Seleccionar solo columnas numéricas para la correlación
    numeric_cols = ['peso', 'tsh_neonatal', 'resultado_muestra_2', 'dias_pasados', 'sexo_num']
    corr_df = filtered_df[numeric_cols].corr()
    
    fig_corr = px.imshow(
        corr_df,
        text_auto=True,
        aspect="auto",
        color_continuous_scale='RdBu_r',
        title='Matriz de Correlación'
    )
    
    st.plotly_chart(fig_corr, use_container_width=True)


with tabs[4]:

    st.header("🚨 Análisis de Casos Confirmados")
    
    # Filtrar solo casos confirmados
    confirmed_df = filtered_df[filtered_df['confirmado_hipotiroidismo'] == True]
   
    if confirmed_df.empty:
        st.warning("No hay casos confirmados con los filtros actuales.")
    else:
        # Sección de envío de alertas por SMS con Twilio
        st.subheader("Enviar Alerta por SMS")
        
        # Seleccionar caso para enviar alerta
        selected_case = st.selectbox(
            "Seleccionar caso para enviar alerta:",
            options=confirmed_df.index,
            format_func=lambda x: f"ID: {confirmed_df.loc[x, 'id']} - {confirmed_df.loc[x, 'ciudad']}"
        )
        
        # Obtener la fila seleccionada
        fila = confirmed_df.loc[selected_case]
        
        # Mostrar detalles del caso seleccionado
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**ID:** {fila['id']}")
            st.write(f"**TSH Neonatal:** {fila['resultado_muestra_2']} mIU/L")
            st.write(f"**ARS:** {fila['ars']}")
        with col2:
            st.write(f"**Ciudad:** {fila['ciudad']}")
            st.write(f"**Departamento:** {fila['departamento']}")
            
        # Número de teléfono del destinatario
        telefono = st.text_input("Número de teléfono (incluir código de país):", placeholder="+573XXXXXXXXX")
        
        # Mensaje predeterminado
        mensaje = (
            f"Prueba de Alerta: El resultado de TSH neonatal de su hijo es {fila['resultado_muestra_2']}. "
            f"Por favor, contacte a {fila['ars']} para más información."
        )
        
        # Permitir editar el mensaje
        mensaje_editado = st.text_area("Mensaje:", value=mensaje, height=100)
        
        # Botón para enviar SMS
        if st.button("Enviar SMS"):
            if telefono:
                try:
                    # Verificar si secrets.toml está configurado
                    has_secrets = False
                    try:
                        account_sid = st.secrets["twilio"]["account_sid"]
                        auth_token = st.secrets["twilio"]["auth_token"]
                        from_phone_number = st.secrets["twilio"]["from_phone_number"]
                        has_secrets = True
                    except Exception:
                        st.warning("No se encontró el archivo secrets.toml con las credenciales de Twilio. Se mostrará el mensaje que se enviaría.")
                    
                    # Registrar en log
                    st.session_state.setdefault('sms_log', []).append({
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'id_caso': fila['id'],
                        'telefono': telefono,
                        'mensaje': mensaje_editado,
                        'status': "Simulado (sin credenciales Twilio)"
                    })
                    
                    if has_secrets:
                        # Importar cliente de Twilio
                        from twilio.rest import Client
                        
                        # Inicializar cliente de Twilio
                        client = Client(account_sid, auth_token)
                        
                        # Enviar mensaje
                        message = client.messages.create(
                            body=mensaje_editado,
                            from_=from_phone_number,
                            to=telefono
                        )
                        #print(telefono)
                        
                        # Actualizar status en el log
                        st.session_state.sms_log[-1]['status'] = "Enviado"
                        st.session_state.sms_log[-1]['sid'] = message.sid
                        
                        # Mostrar confirmación
                        st.success(f"Mensaje enviado correctamente. SID: {message.sid}")
                    else:
                        # Mostrar mensaje simulado
                        st.info(f"SIMULACIÓN: Se enviaría el siguiente mensaje a {telefono}:\n\n{mensaje_editado}")
                    
                except Exception as e:
                    st.error(f"Error al enviar el mensaje: {str(e)}")
            else:
                st.warning("Por favor, ingrese un número de teléfono válido.")
        
        # Sección para envío masivo de alertas
        st.subheader("Enviar Alertas a Todos los Casos Confirmados")
        
        # Verificar si existen las columnas de teléfono
        has_phone_columns = any(col in confirmed_df.columns for col in ['telefono_1', 'telefono_2'])
        
        if not has_phone_columns:
            st.warning("No se encontraron las columnas 'telefono_1' o 'telefono_2' en los datos.")
        else:
            # Contar cuántos casos tienen teléfono disponible
            phone_count = confirmed_df.apply(lambda row: pd.notna(row.get('telefono_1', None)) or pd.notna(row.get('telefono_2', None)), axis=1).sum()
            
            st.write(f"Se encontraron {phone_count} de {len(confirmed_df)} casos con número de teléfono disponible.")
            
            # Plantilla de mensaje para envío masivo
            mensaje_masivo_template = st.text_area(
                "Plantilla de mensaje (use {tsh} y {ars} como marcadores):",
                value="Prueba de Alerta: El resultado de TSH neonatal de su hijo es {tsh}. Por favor, contacte a {ars} para más información.",
                height=100,
                key="mensaje_masivo"
            )
            
            # Opción para enviar un mensaje de prueba
            test_mode = st.checkbox("Modo de prueba (solo registrar mensajes sin enviarlos)", value=True)
            
            # Botón para enviar a todos
            if st.button("Enviar SMS a Todos los Casos"):
                # Configuración de Twilio
                try:
                    # Verificar si secrets.toml está configurado
                    has_secrets = False
                    try:
                        account_sid = st.secrets["twilio"]["account_sid"]
                        auth_token = st.secrets["twilio"]["auth_token"]
                        from_phone_number = st.secrets["twilio"]["from_phone_number"]
                        has_secrets = True
                    except Exception:
                        st.warning("No se encontró el archivo secrets.toml con las credenciales de Twilio. Se usará el modo de simulación.")
                        test_mode = True
                    
                    # Importar cliente de Twilio
                    if has_secrets and not test_mode:
                        from twilio.rest import Client
                        client = Client(account_sid, auth_token)
                    
                    # Crear barra de progreso
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Contador de mensajes enviados y fallidos
                    sent_count = 0
                    failed_count = 0
                    
                    # Procesar cada caso
                    for i, (idx, row) in enumerate(confirmed_df.iterrows()):
                        # Actualizar barra de progreso
                        progress = (i + 1) / len(confirmed_df)
                        progress_bar.progress(progress)
                        status_text.text(f"Procesando {i+1} de {len(confirmed_df)} casos...")
                        
                        # Obtener teléfono (priorizar telefono_1)
                        telefono = None
                        if 'telefono_1' in row and pd.notna(row['telefono_1']):
                            telefono = row['telefono_1']
                        elif 'telefono_2' in row and pd.notna(row['telefono_2']):
                            telefono = row['telefono_2']
                        
                        # Solo procesar si hay un teléfono disponible
                        if telefono:
                            # Formatear teléfono si es necesario (asegurar formato internacional)
                            if not telefono.startswith('+'):
                                telefono = '+57' + telefono
                            
                            # Personalizar mensaje con los datos del paciente
                            tsh = str(row['resultado_muestra_2'])
                            ars = str(row.get('ars', 'su servicio de salud'))
                            mensaje_personalizado = mensaje_masivo_template.replace('{tsh}', tsh).replace('{ars}', ars)
                            
                            try:
                                # En modo real, enviar mensaje
                                if not test_mode:
                                    message = client.messages.create(
                                        body=mensaje_personalizado,
                                        from_=twilio_number,
                                        to=telefono
                                    )
                                    message_sid = message.sid
                                    status = "Enviado"
                                    #print(telefono)
                                else:
                                    # En modo de prueba, simular éxito
                                    message_sid = f"TEST-{i}"
                                    status = "Prueba"
                                    #print(telefono)
                                
                                # Registrar mensaje en el historial
                                st.session_state.setdefault('sms_log', []).append({
                                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    'id_caso': row.get('id', idx),
                                    'telefono': telefono,
                                    'mensaje': mensaje_personalizado,
                                    'status': status,
                                    'sid': message_sid
                                })
                                
                                sent_count += 1
                                
                            except Exception as e:
                                # Registrar error
                                st.session_state.setdefault('sms_log', []).append({
                                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    'id_caso': row.get('id', idx),
                                    'telefono': telefono,
                                    'mensaje': mensaje_personalizado,
                                    'status': f"Error: {str(e)}"
                                })
                                
                                failed_count += 1
                    
                    # Mostrar resumen
                    if test_mode:
                        st.success(f"Modo de prueba: Se procesaron {sent_count} mensajes exitosamente (simulados) y {failed_count} fallaron.")
                    else:
                        st.success(f"Se enviaron {sent_count} mensajes exitosamente y {failed_count} fallaron.")
                    
                except Exception as e:
                    st.error(f"Error al configurar Twilio: {str(e)}")
        
        # Historial de mensajes enviados
        if 'sms_log' in st.session_state and st.session_state.sms_log:
            with st.expander("Historial de mensajes enviados"):
                log_df = pd.DataFrame(st.session_state.sms_log)
                st.dataframe(log_df)
        
        # Línea divisoria
        st.markdown("---")
        
        # Estadísticas descriptivas de los casos confirmados
        st.subheader("Estadísticas Descriptivas de Casos Confirmados")
       
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Casos Confirmados", f"{confirmed_df.shape[0]}")
        with col2:
            st.metric("TSH Promedio", f"{confirmed_df['tsh_neonatal'].mean():.1f} mIU/L")
        with col3:
            st.metric("Edad Promedio al Diagnóstico", f"{confirmed_df['dias_pasados'].mean():.1f} días")
       
        # Distribución de TSH en casos confirmados
        st.subheader("Distribución de TSH en Casos Confirmados")
       
        fig_confirmed_tsh = px.histogram(
            confirmed_df,
            x='tsh_neonatal',
            nbins=20,
            title='Distribución de TSH en Casos Confirmados',
            labels={'tsh_neonatal': 'TSH Neonatal (mIU/L)'},
            color_discrete_sequence=['#FF4500']
        )
       
        st.plotly_chart(fig_confirmed_tsh, use_container_width=True)
       
        # Distribución geográfica de casos
        st.subheader("Distribución Geográfica de Casos Confirmados")
       
        # Tabla de casos por departamento
        geo_counts = confirmed_df.groupby('departamento').size().reset_index(name='casos')
        geo_counts = geo_counts.sort_values('casos', ascending=False)
       
        col1, col2 = st.columns([2, 1])
       
        with col1:
            fig_geo = px.bar(
                geo_counts,
                x='departamento',
                y='casos',
                title='Casos Confirmados por Departamento',
                labels={'casos': 'Número de Casos', 'departamento': 'Departamento'},
                color='casos',
                color_continuous_scale='Reds'
            )
           
            st.plotly_chart(fig_geo, use_container_width=True)
       
        with col2:
            st.dataframe(geo_counts, width=300, height=400)
       
        # Tabla de casos confirmados
        st.subheader("Detalle de Casos Confirmados")
       
        # Seleccionar columnas relevantes para mostrar
        columns_to_show = [
            'id', 'ciudad', 'departamento', 'sexo', 'fecha_nacimiento',
            'peso', 'prematuro', 'tsh_neonatal', 'resultado_muestra_2', 'dias_pasados'
        ]
       
        confirmed_table = confirmed_df[columns_to_show].copy()
        confirmed_table['peso_kg'] = confirmed_table['peso'] / 1000
        confirmed_table.rename(columns={'peso_kg': 'Peso (kg)'}, inplace=True)
       
        st.dataframe(confirmed_table, height=400)
       
        # Opción para descargar los datos de casos confirmados
        csv = confirmed_table.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Descargar Datos de Casos Confirmados",
            csv,
            "casos_confirmados.csv",
            "text/csv",
            key='download-csv'
        )

# Información del proyecto en el sidebar
st.sidebar.markdown("---")
st.sidebar.info(
    """
    **Proyecto de Análisis de Hipotiroidismo Congénito**
    
    Este dashboard permite analizar datos de tamizaje neonatal 
    para la detección temprana de hipotiroidismo congénito.
    
    Desarrollado por: Luis Carlos Pallares Ascanio
    """
)

# Footer
st.markdown("---")
st.markdown(
    """
### Notas:
- **Sospecha Matrizde hipotiroidismo**: TSH ≥ 15 mIU/L en la primera muestra.
- **Confirmación de hipotiroidismo**: TSH ≥ 15 mIU/L en la primera y segunda muestra.

    <div style="text-align: center">
        <p>Dashboard de Hipotiroidismo Congénito v1.0 | © 2025</p>
    </div>
    """, 
    unsafe_allow_html=True
)

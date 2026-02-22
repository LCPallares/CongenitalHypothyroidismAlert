# app.py  — Punto de entrada principal
# Streamlit carga automáticamente las páginas en pages/

import streamlit as st
from utils.constantes import CSS

st.set_page_config(
    page_title="Hipotiroidismo Congénito",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CSS, unsafe_allow_html=True)

st.title("🏥 Sistema de Tamizaje — Hipotiroidismo Congénito")
st.markdown("Selecciona una sección en el menú de la izquierda.")

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Hipotiroidismo Congénito**

📝 Ingresa datos desde la tarjeta física  
📊 Analiza resultados y tendencias  
🚨 Gestiona alertas a pacientes e IRS  
""")
st.sidebar.markdown("---")
st.sidebar.caption("Desarrollado por: Luis Carlos Pallares Ascanio")

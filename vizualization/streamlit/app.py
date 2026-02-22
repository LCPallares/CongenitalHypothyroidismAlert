"""
Sistema de Tamizaje — Hipotiroidismo Congénito
==============================================
Tabs:
  1. 📝 Ingreso de Datos   — Formulario con validación + envío SMS
  2. 📊 Dashboard          — Reportes y análisis (código original)
  3. 🚨 Casos Confirmados  — Alertas SMS masivas

Instalación:
    pip install streamlit pandas plotly folium streamlit-folium twilio
"""

import csv
import os
from datetime import datetime, date

import folium
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

# ─── Configuración ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hipotiroidismo Congénito",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS personalizado ────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Tabs más grandes */
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] {
    padding: 10px 24px;
    font-size: 15px;
    font-weight: 600;
    border-radius: 8px 8px 0 0;
}
/* Tarjetas de métricas */
[data-testid="metric-container"] {
    background: #0e1525;
    border: 1px solid #1e3050;
    border-radius: 10px;
    padding: 12px 16px;
}
/* Secciones del formulario */
.form-section {
    background: #0e1525;
    border-left: 3px solid #2fb8d4;
    border-radius: 0 8px 8px 0;
    padding: 10px 16px;
    margin: 14px 0 8px 0;
    font-size: 15px;
    font-weight: 700;
    color: #2fb8d4;
}
/* Alerta TSH */
.tsh-alert {
    background: #2d1f00;
    border: 1px solid #f39c12;
    border-radius: 8px;
    padding: 10px 16px;
    color: #f39c12;
    font-weight: 600;
    margin: 8px 0;
}
/* Alerta éxito */
.success-box {
    background: #0d2a1a;
    border: 1px solid #27ae60;
    border-radius: 8px;
    padding: 10px 16px;
    color: #2ecc71;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ─── Constantes ───────────────────────────────────────────────────────────────
CSV_REGISTROS = "../../data/hipotiroidismo_registros.csv"
TSH_MIN, TSH_MAX = 0.1, 300.0
PESO_MIN, PESO_MAX = 400, 8000
TSH_CORTE = 15.0          # umbral clínico del cliente

FIELDNAMES = [
    "Id", "No de ficha", "Fecha de ingreso", "Institucion", "ARS",
    "Historia clinica", "Tipo de Documento", "Numero de Documento",
    "Ciudad", "Departamento", "Telefono uno", "Telefono dos", "Direccion",
    "Primer Apellido", "Segundo Apellido", "Nombre Hijo de",
    "Fecha de Nacimiento", "Peso", "Sexo", "Prematuro", "Transfundido",
    "Informacion completa", "Muestra adecuada", "Destino muestra",
    "Tipo de muestra", "Fecha toma de la muestra", "Fecha de resultado",
    "Resultados TSH neonatal", "No de ficha dos", "Tipo de muestra 2",
    "Fecha toma de la muestra 2", "Fecha resultado muestra 2",
    "Resultado toma de muestra 2", "Contador", "muestra rechazada",
    "Fecha toma rechazada", "Tipo de Vinculacion", "Resultado Rechazada",
    "Fecha resultado rechazada",
]

DEPARTAMENTOS = [
    "Seleccionar...", "Amazonas", "Antioquia", "Arauca", "Atlántico",
    "Bolívar", "Boyacá", "Caldas", "Caquetá", "Casanare", "Cauca",
    "Cesar", "Chocó", "Córdoba", "Cundinamarca", "Guainía", "Guaviare",
    "Huila", "La Guajira", "Magdalena", "Meta", "Nariño",
    "Norte de Santander", "Putumayo", "Quindío", "Risaralda",
    "San Andrés", "Santander", "Sucre", "Tolima", "Valle del Cauca",
    "Vaupés", "Vichada",
]

# ─── Helpers de validación ────────────────────────────────────────────────────

def val_fecha(text, campo="Fecha"):
    if not text.strip():
        return None, f"{campo} es obligatoria"
    for fmt in ("%d-%b-%y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date(), None
        except ValueError:
            pass
    return None, f"{campo}: formato inválido (ej: 5-May-19 o 05/05/2019)"

def val_tsh(text, campo="TSH"):
    if not str(text).strip():
        return None, f"{campo} es obligatorio"
    try:
        v = float(str(text).replace(",", "."))
    except ValueError:
        return None, f"{campo} debe ser un número"
    if v < TSH_MIN: return None, f"{campo} demasiado bajo (mín {TSH_MIN})"
    if v > TSH_MAX: return None, f"{campo} imposible (máx {TSH_MAX} µIU/mL)"
    return v, None

def val_peso(text):
    if not str(text).strip():
        return None, "Peso es obligatorio"
    try:
        v = float(str(text).replace(",", "."))
    except ValueError:
        return None, "Peso debe ser un número"
    if v < PESO_MIN: return None, f"Peso muy bajo (mín {PESO_MIN} g)"
    if v > PESO_MAX: return None, f"Peso imposible (máx {PESO_MAX} g)"
    return v, None

def next_id():
    if not os.path.isfile(CSV_REGISTROS):
        return 1
    with open(CSV_REGISTROS, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return 1
    try:
        return max(int(r.get("Id", 0)) for r in rows) + 1
    except Exception:
        return len(rows) + 1

def guardar_registro(row: dict):
    existe = os.path.isfile(CSV_REGISTROS)
    with open(CSV_REGISTROS, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not existe:
            w.writeheader()
        w.writerow(row)

# ─── Carga del dataset principal (dashboard) ─────────────────────────────────

@st.cache_data
def load_data():
    path = "../../data/dataset_corregido_v2b_anom2.csv"
    try:
        df = pd.read_csv(path, low_memory=False)
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
        df["tsh_neonatal"] = pd.to_numeric(df.get("tsh_neonatal", 0), errors="coerce").fillna(0)
        df["resultado_muestra_2"] = pd.to_numeric(df.get("resultado_muestra_2", 0), errors="coerce").fillna(0)
        df["sospecha_hipotiroidismo"] = df["tsh_neonatal"] >= TSH_CORTE
        df["confirmado_hipotiroidismo"] = (
            (df["tsh_neonatal"] >= TSH_CORTE) & (df["resultado_muestra_2"] >= TSH_CORTE)
        )
        return df
    except Exception as e:
        st.error(f"Error al cargar dataset principal: {e}")
        return pd.DataFrame()

def graficar_mapa_casos(df):
    city_coordinates = {
        "Bogota":      [4.6097, -74.0817],
        "Cundinamarca":[4.7000, -73.8000],
    }
    m = folium.Map(location=[4.6097, -74.0817], zoom_start=6, tiles="cartodbpositron")
    for city, casos in df.groupby("ciudad")["confirmado_hipotiroidismo"].sum().items():
        if city in city_coordinates:
            folium.Marker(
                location=city_coordinates[city],
                popup=f"<b>{city}</b><br>Casos Confirmados: {int(casos)}",
                tooltip=city,
                icon=folium.Icon(color="red", icon="plus-square", prefix="fa"),
            ).add_to(m)
    st_folium(m, width=700, height=500)

# ─── Función de envío SMS (Twilio) ────────────────────────────────────────────

def enviar_sms(telefono: str, mensaje: str, test_mode: bool = True):
    """
    Retorna (bool éxito, str mensaje_estado).
    Si test_mode=True nunca llama a Twilio.
    Credenciales se leen de st.secrets["twilio"].
    """
    if not telefono.startswith("+"):
        telefono = "+57" + telefono.strip()

    if test_mode:
        return True, f"[SIMULADO] Mensaje a {telefono}: {mensaje[:60]}..."

    try:
        from twilio.rest import Client
        sid   = st.secrets["twilio"]["account_sid"]
        token = st.secrets["twilio"]["auth_token"]
        from_ = st.secrets["twilio"]["from_phone_number"]
        client = Client(sid, token)
        msg = client.messages.create(body=mensaje, from_=from_, to=telefono)
        return True, f"Enviado — SID: {msg.sid}"
    except KeyError:
        return False, "Configura st.secrets['twilio'] con account_sid, auth_token y from_phone_number"
    except Exception as e:
        return False, f"Error Twilio: {e}"

# ═════════════════════════════════════════════════════════════════════════════
# LAYOUT PRINCIPAL — 3 TABS
# ═════════════════════════════════════════════════════════════════════════════

tab_form, tab_dash, tab_alertas = st.tabs([
    "📝  Ingreso de Datos",
    "📊  Dashboard / Reportes",
    "🚨  Casos Confirmados",
])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — FORMULARIO DE INGRESO
# ═════════════════════════════════════════════════════════════════════════════

with tab_form:
    st.markdown("## 📝 Digitalización de Tarjeta de Tamizaje")
    st.caption("Complete los datos de la tarjeta física enviada por la IRS. Los campos marcados con ★ son obligatorios.")

    # ── Inicializar session_state para el formulario ──────────────────────────
    if "form_errors" not in st.session_state:
        st.session_state.form_errors = []
    if "form_submitted" not in st.session_state:
        st.session_state.form_submitted = False
    if "tsh1_val" not in st.session_state:
        st.session_state.tsh1_val = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # SECCIÓN 1 — ACUDIENTE / DATOS GENERALES
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="form-section">👤  Datos del Acudiente / Institución</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        ficha        = st.text_input("★ No. de Ficha", placeholder="369980")
        fecha_ingreso= st.text_input("★ Fecha de Ingreso", placeholder="5-May-19",
                                      help="Formatos: 5-May-19  |  05/05/2019  |  2019-05-05")
        institucion  = st.text_input("★ Institución", placeholder="VICTORIA")
    with c2:
        ars          = st.text_input("★ ARS / EPS", placeholder="MEDIMAS")
        historia     = st.text_input("Historia Clínica", placeholder="Número")
        tipo_doc     = st.selectbox("★ Tipo de Documento",
                                     ["Seleccionar...", "CC", "CE", "PA", "RC", "TI"])
    with c3:
        num_doc      = st.text_input("★ Número de Documento", placeholder="123456789")
        ciudad       = st.text_input("★ Ciudad", placeholder="Bogotá")
        departamento = st.selectbox("★ Departamento", DEPARTAMENTOS)

    c4, c5 = st.columns(2)
    with c4:
        tel1     = st.text_input("Teléfono 1", placeholder="3130000000")
        tipo_vinc= st.selectbox("★ Tipo de Vinculación",
                                  ["Seleccionar...", "CONTRIBUTIVO", "SUBSIDIADO",
                                   "VINCULADO", "PARTICULAR", "ESPECIAL"])
    with c5:
        tel2     = st.text_input("Teléfono 2 (opcional)")
        direccion= st.text_input("Dirección")

    # ─────────────────────────────────────────────────────────────────────────
    # SECCIÓN 2 — RECIÉN NACIDO
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="form-section">👶  Datos del Recién Nacido</div>', unsafe_allow_html=True)

    c6, c7, c8 = st.columns(3)
    with c6:
        apellido1 = st.text_input("★ Primer Apellido")
        apellido2 = st.text_input("Segundo Apellido")
    with c7:
        nombre    = st.text_input("★ Nombre / Hijo(a) de")
        fecha_nac = st.text_input("★ Fecha de Nacimiento", placeholder="5-May-19")
    with c8:
        peso      = st.text_input("★ Peso al nacer (g)", placeholder="2890")
        sexo      = st.selectbox("★ Sexo",
                                  ["Seleccionar...", "MASCULINO", "FEMENINO", "INDETERMINADO"])

    c9, c10 = st.columns(2)
    with c9:
        prematuro    = st.checkbox("Prematuro")
        transfundido = st.checkbox("Transfundido")
    with c10:
        info_completa = st.checkbox("Información completa")
        muestra_adec  = st.checkbox("Muestra adecuada")

    # ─────────────────────────────────────────────────────────────────────────
    # SECCIÓN 3 — MUESTRA 1
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="form-section">🔬  Muestra 1</div>', unsafe_allow_html=True)

    c11, c12, c13 = st.columns(3)
    with c11:
        tipo_muestra1  = st.selectbox("★ Tipo de Muestra",
                                       ["Seleccionar...", "CORDON", "TALON", "VENA"])
        destino        = st.selectbox("★ Destino muestra",
                                       ["Seleccionar...", "ACEPTADA", "RECHAZADA"])
    with c12:
        fecha_muestra1 = st.text_input("★ Fecha toma muestra 1", placeholder="5-May-19")
        fecha_result1  = st.text_input("★ Fecha resultado 1",    placeholder="6-May-19")
    with c13:
        tsh1_str = st.text_input("★ Resultado TSH 1 (µIU/mL)", placeholder="7.2")

    # Calcular TSH1 en tiempo real para mostrar alerta
    tsh1_num = None
    if tsh1_str.strip():
        try:
            tsh1_num = float(tsh1_str.replace(",", "."))
        except ValueError:
            pass

    if tsh1_num is not None and tsh1_num >= TSH_CORTE:
        st.markdown(
            f'<div class="tsh-alert">⚠️  TSH1 = <strong>{tsh1_num} µIU/mL</strong> — '
            f'Supera el umbral de {TSH_CORTE} µIU/mL. <strong>Se requiere 2ª muestra de confirmación.</strong></div>',
            unsafe_allow_html=True,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # SECCIÓN 4 — MUESTRA 2 (solo si TSH1 ≥ umbral)
    # ─────────────────────────────────────────────────────────────────────────
    necesita_m2 = tsh1_num is not None and tsh1_num >= TSH_CORTE

    ficha2 = tipo_m2 = fecha_m2 = f_res2 = tsh2_str = ""

    if necesita_m2:
        st.markdown('<div class="form-section">🔁  Muestra 2 — Confirmación</div>', unsafe_allow_html=True)
        c14, c15, c16 = st.columns(3)
        with c14:
            ficha2   = st.text_input("No. Ficha 2")
            tipo_m2  = st.selectbox("★ Tipo muestra 2",
                                     ["Seleccionar...", "CORDON", "TALON", "VENA"],
                                     key="tipo_m2")
        with c15:
            fecha_m2 = st.text_input("★ Fecha toma muestra 2", placeholder="5-May-19", key="fm2")
            f_res2   = st.text_input("★ Fecha resultado 2",    placeholder="6-May-19", key="fr2")
        with c16:
            tsh2_str = st.text_input("★ Resultado TSH 2 (µIU/mL)", placeholder="18.5", key="tsh2")

        if tsh2_str.strip():
            try:
                tsh2_num = float(tsh2_str.replace(",", "."))
                if tsh2_num >= TSH_CORTE:
                    st.error(f"🚨 TSH2 = {tsh2_num} µIU/mL — **HIPOTIROIDISMO CONFIRMADO**. "
                             f"Se deberá notificar al paciente y a la IRS.")
                else:
                    st.success(f"✅ TSH2 = {tsh2_num} µIU/mL — Resultado normal en segunda muestra.")
            except ValueError:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # SECCIÓN 5 — MUESTRA RECHAZADA
    # ─────────────────────────────────────────────────────────────────────────
    with st.expander("❌  Muestra rechazada (opcional)"):
        m_rechazada = st.checkbox("¿Hubo muestra rechazada?")
        c17, c18 = st.columns(2)
        with c17:
            fecha_rechaz     = st.text_input("Fecha toma rechazada", key="frech")
            res_rechaz       = st.selectbox("Resultado rechazada",
                                             ["", "PENDIENTE", "NORMAL", "ALTERADO"])
        with c18:
            fecha_res_rechaz = st.text_input("Fecha resultado rechazada", key="frr")

    # ─────────────────────────────────────────────────────────────────────────
    # SECCIÓN 6 — SMS AL GUARDAR
    # ─────────────────────────────────────────────────────────────────────────
    if necesita_m2:
        st.markdown('<div class="form-section">📱  Notificación SMS al guardar</div>', unsafe_allow_html=True)
        st.caption("Si el caso es positivo confirmado, se puede enviar SMS al paciente y/o a la IRS al momento de guardar.")

        c_sms1, c_sms2 = st.columns(2)
        with c_sms1:
            enviar_al_paciente = st.checkbox("Notificar al paciente/acudiente por SMS")
            if enviar_al_paciente:
                tel_paciente = st.text_input("Teléfono paciente",
                                              value=tel1 or tel2,
                                              placeholder="+573130000000",
                                              key="tel_pac")
                msg_paciente = st.text_area(
                    "Mensaje paciente",
                    value=(f"Alerta: El resultado del tamizaje de hipotiroidismo de su hijo(a) "
                           f"es POSITIVO (TSH: {tsh2_str} µIU/mL). "
                           f"Por favor contacte a {ars} para iniciar tratamiento urgente."),
                    height=100, key="msg_pac",
                )
        with c_sms2:
            enviar_a_irs = st.checkbox("Notificar a la IRS por SMS")
            if enviar_a_irs:
                tel_irs  = st.text_input("Teléfono IRS", placeholder="+573130000000", key="tel_irs")
                msg_irs  = st.text_area(
                    "Mensaje IRS",
                    value=(f"Caso positivo: Paciente {apellido1} {apellido2}, "
                           f"Ciudad: {ciudad}, TSH: {tsh2_str} µIU/mL. "
                           f"ARS: {ars}. Requiere seguimiento urgente."),
                    height=100, key="msg_irs",
                )
        sms_test_mode = st.checkbox("🧪 Modo de prueba SMS (no envía realmente)", value=True)
    else:
        enviar_al_paciente = False
        enviar_a_irs = False
        sms_test_mode = True

    # ─────────────────────────────────────────────────────────────────────────
    # BOTÓN GUARDAR
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        guardar = st.button("💾  Guardar Registro", use_container_width=True, type="primary")

    if guardar:
        errors = []

        # Validar campos obligatorios simples
        for val, label in [
            (ficha, "No. de Ficha"), (institucion, "Institución"),
            (ars, "ARS"), (num_doc, "Número Documento"),
            (ciudad, "Ciudad"), (apellido1, "Primer Apellido"),
            (nombre, "Nombre"),
        ]:
            if not val.strip():
                errors.append(f"**{label}** es obligatorio")

        # Spinners
        for val, label in [
            (tipo_doc, "Tipo de Documento"), (departamento, "Departamento"),
            (sexo, "Sexo"), (tipo_vinc, "Tipo Vinculación"),
            (tipo_muestra1, "Tipo de Muestra"), (destino, "Destino muestra"),
        ]:
            if not val or val == "Seleccionar...":
                errors.append(f"**{label}** es obligatorio")

        # Fechas
        d_fi, e = val_fecha(fecha_ingreso, "Fecha de ingreso")
        if e: errors.append(e)
        d_fn, e = val_fecha(fecha_nac, "Fecha de Nacimiento")
        if e: errors.append(e)
        if d_fi and d_fn:
            if d_fn > d_fi:
                errors.append("Fecha de nacimiento no puede ser posterior a la fecha de ingreso")
            if (date.today() - d_fn).days > 365:
                errors.append("Fecha de nacimiento inusual (más de 1 año atrás)")

        _, e = val_fecha(fecha_muestra1, "Fecha toma muestra 1")
        if e: errors.append(e)
        d_r1, e = val_fecha(fecha_result1, "Fecha resultado 1")
        if e: errors.append(e)

        # Peso
        v_peso, e = val_peso(peso)
        if e: errors.append(e)

        # TSH1
        v_tsh1, e = val_tsh(tsh1_str, "TSH 1")
        if e: errors.append(e)

        # Muestra 2
        v_tsh2 = None
        if necesita_m2:
            v_tsh2, e = val_tsh(tsh2_str if tsh2_str else "", "TSH 2")
            if e: errors.append(e)
            if not tipo_m2 or tipo_m2 == "Seleccionar...":
                errors.append("Tipo de muestra 2 es obligatorio")
            _, e = val_fecha(fecha_m2, "Fecha toma muestra 2")
            if e: errors.append(e)
            _, e = val_fecha(f_res2, "Fecha resultado 2")
            if e: errors.append(e)

        # ── Mostrar errores o guardar ─────────────────────────────────────
        if errors:
            st.error(f"**Se encontraron {len(errors)} error(es):**")
            for err in errors:
                st.markdown(f"- {err}")
        else:
            # Construir fila
            row = {
                "Id":                           next_id(),
                "No de ficha":                  ficha.strip(),
                "Fecha de ingreso":             fecha_ingreso.strip(),
                "Institucion":                  institucion.strip(),
                "ARS":                          ars.strip(),
                "Historia clinica":             historia.strip(),
                "Tipo de Documento":            tipo_doc,
                "Numero de Documento":          num_doc.strip(),
                "Ciudad":                       ciudad.strip(),
                "Departamento":                 departamento,
                "Telefono uno":                 tel1.strip() or "0",
                "Telefono dos":                 tel2.strip() or "0",
                "Direccion":                    direccion.strip(),
                "Primer Apellido":              apellido1.strip(),
                "Segundo Apellido":             apellido2.strip(),
                "Nombre Hijo de":               nombre.strip(),
                "Fecha de Nacimiento":          fecha_nac.strip(),
                "Peso":                         v_peso,
                "Sexo":                         sexo,
                "Prematuro":                    "VERDADERO" if prematuro else "FALSO",
                "Transfundido":                 "VERDADERO" if transfundido else "FALSO",
                "Informacion completa":         "VERDADERO" if info_completa else "FALSO",
                "Muestra adecuada":             "VERDADERO" if muestra_adec else "FALSO",
                "Destino muestra":              destino,
                "Tipo de muestra":              tipo_muestra1,
                "Fecha toma de la muestra":     fecha_muestra1.strip(),
                "Fecha de resultado":           fecha_result1.strip(),
                "Resultados TSH neonatal":      v_tsh1,
                "No de ficha dos":              ficha2.strip() or "0",
                "Tipo de muestra 2":            tipo_m2 if necesita_m2 and tipo_m2 != "Seleccionar..." else "",
                "Fecha toma de la muestra 2":   fecha_m2.strip() if necesita_m2 else "",
                "Fecha resultado muestra 2":    f_res2.strip() if necesita_m2 else "",
                "Resultado toma de muestra 2":  v_tsh2 if v_tsh2 else "",
                "Contador":                     "1" if necesita_m2 else "0",
                "muestra rechazada":            "VERDADERO" if m_rechazada else "FALSO",
                "Fecha toma rechazada":         fecha_rechaz.strip() if m_rechazada else "",
                "Tipo de Vinculacion":          tipo_vinc,
                "Resultado Rechazada":          res_rechaz if m_rechazada else "",
                "Fecha resultado rechazada":    fecha_res_rechaz.strip() if m_rechazada else "",
            }
            guardar_registro(row)

            st.markdown(
                f'<div class="success-box">✅ Registro <strong>#{row["Id"]}</strong> guardado '
                f'correctamente en <code>{CSV_REGISTROS}</code></div>',
                unsafe_allow_html=True,
            )

            # ── Envío SMS ─────────────────────────────────────────────────
            sms_log = st.session_state.setdefault("sms_log", [])

            confirmado_ahora = (v_tsh2 is not None and v_tsh2 >= TSH_CORTE)

            if confirmado_ahora:
                if enviar_al_paciente and tel_paciente:
                    ok, status = enviar_sms(tel_paciente, msg_paciente, sms_test_mode)
                    sms_log.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "id_caso":   row["Id"],
                        "destino":   "Paciente",
                        "telefono":  tel_paciente,
                        "status":    status,
                    })
                    if ok:
                        st.success(f"📱 SMS paciente: {status}")
                    else:
                        st.error(f"📱 SMS paciente fallido: {status}")

                if enviar_a_irs and tel_irs:
                    ok, status = enviar_sms(tel_irs, msg_irs, sms_test_mode)
                    sms_log.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "id_caso":   row["Id"],
                        "destino":   "IRS",
                        "telefono":  tel_irs,
                        "status":    status,
                    })
                    if ok:
                        st.success(f"🏥 SMS IRS: {status}")
                    else:
                        st.error(f"🏥 SMS IRS fallido: {status}")
            elif necesita_m2 and not confirmado_ahora:
                st.info("TSH2 normal — no se requiere notificación de caso positivo.")

    # ── Historial de envíos de esta sesión ────────────────────────────────────
    if st.session_state.get("sms_log"):
        with st.expander("📋  Historial de SMS enviados en esta sesión"):
            st.dataframe(pd.DataFrame(st.session_state["sms_log"]), use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — DASHBOARD (código original intacto)
# ═════════════════════════════════════════════════════════════════════════════

with tab_dash:

    df = load_data()

    if df.empty:
        st.error("No se pudieron cargar los datos. Verifica el archivo CSV en data/")
        st.stop()

    # ── Métricas generales ────────────────────────────────────────────────────
    st.header("🔍 Información General del Dataset")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Registros", f"{df.shape[0]:,}")
    with col2:
        st.metric(f"Casos Sospechosos (TSH ≥ {TSH_CORTE})", f"{df['sospecha_hipotiroidismo'].sum():,}")
    with col3:
        st.metric("Casos Confirmados", f"{df['confirmado_hipotiroidismo'].sum():,}")
    with col4:
        dias_promedio = round(df["dias_pasados"].mean(), 1) if "dias_pasados" in df.columns else "—"
        st.metric("Promedio Días hasta Resultado", f"{dias_promedio}")

    # ── Sidebar filtros ───────────────────────────────────────────────────────
    st.sidebar.header("📋 Filtros")

    años_disponibles = sorted(df["fecha_nacimiento"].dt.year.dropna().unique().tolist()) if "fecha_nacimiento" in df.columns else []
    años_seleccionados = st.sidebar.multiselect("Seleccionar Años:", options=años_disponibles, default=años_disponibles)

    sexos_disponibles = sorted(df["sexo"].dropna().unique().tolist()) if "sexo" in df.columns else []
    sexos_seleccionados = st.sidebar.multiselect("Seleccionar Sexo:", options=sexos_disponibles, default=sexos_disponibles)

    prematuro_opciones = ["Todos", "Prematuros", "No Prematuros"]
    prematuro_seleccionado = st.sidebar.radio("Condición de Nacimiento:", prematuro_opciones)

    tipos_muestra = sorted(df["tipo_muestra"].dropna().unique().tolist()) if "tipo_muestra" in df.columns else []
    tipo_muestra_seleccionado = st.sidebar.multiselect("Tipo de Muestra:", options=tipos_muestra, default=tipos_muestra)

    departamentos = sorted(df["departamento"].dropna().unique().tolist()) if "departamento" in df.columns else []
    departamento_seleccionado = st.sidebar.multiselect("Departamento:", options=departamentos, default=departamentos)

    ciudades = sorted(df["ciudad"].dropna().unique().tolist()) if "ciudad" in df.columns else []
    ciudad_seleccionado = st.sidebar.multiselect("Ciudad:", options=ciudades, default=ciudades)

    hipotiroidismo_opciones = ["Todos", "Sospechosos", "Confirmados", "Normales"]
    hipotiroidismo_seleccionado = st.sidebar.radio("Estado de Hipotiroidismo:", hipotiroidismo_opciones)

    st.sidebar.header("⚙️ Configuración")
    tsh_umbral = st.sidebar.slider("Umbral TSH (mIU/L):", min_value=1.0, max_value=30.0, value=float(TSH_CORTE), step=0.5)

    # ── Aplicar filtros ───────────────────────────────────────────────────────
    filtered_df = df.copy()
    if años_seleccionados and "fecha_nacimiento" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["fecha_nacimiento"].dt.year.isin(años_seleccionados)]
    if sexos_seleccionados and "sexo" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["sexo"].isin(sexos_seleccionados)]
    if prematuro_seleccionado == "Prematuros" and "prematuro" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["prematuro"] == True]
    elif prematuro_seleccionado == "No Prematuros" and "prematuro" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["prematuro"] == False]
    if tipo_muestra_seleccionado and "tipo_muestra" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["tipo_muestra"].isin(tipo_muestra_seleccionado)]
    if departamento_seleccionado and "departamento" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["departamento"].isin(departamento_seleccionado)]
    if ciudad_seleccionado and "ciudad" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["ciudad"].isin(ciudad_seleccionado)]
    if hipotiroidismo_seleccionado == "Sospechosos":
        filtered_df = filtered_df[filtered_df["sospecha_hipotiroidismo"] == True]
    elif hipotiroidismo_seleccionado == "Confirmados":
        filtered_df = filtered_df[filtered_df["confirmado_hipotiroidismo"] == True]
    elif hipotiroidismo_seleccionado == "Normales":
        filtered_df = filtered_df[filtered_df["sospecha_hipotiroidismo"] == False]

    st.sidebar.markdown(f"**Registros filtrados:** {filtered_df.shape[0]:,}")

    # ── Tabs del dashboard ────────────────────────────────────────────────────
    d_tabs = st.tabs(["Resumen Ejecutivo", "Análisis de TSH", "Análisis Temporal",
                      "Factores de Riesgo"])

    # ── Resumen Ejecutivo ─────────────────────────────────────────────────────
    with d_tabs[0]:
        st.header("📌 Resumen Ejecutivo")

        tasa_conf = (df["confirmado_hipotiroidismo"].sum() / df["sospecha_hipotiroidismo"].sum()
                     if df["sospecha_hipotiroidismo"].sum() > 0 else 0)
        col1, col2, col3 = st.columns(3)
        with col1: st.metric(f"Casos Sospechosos (TSH ≥ {TSH_CORTE})", f"{df['sospecha_hipotiroidismo'].sum():,}")
        with col2: st.metric("Casos Confirmados", f"{df['confirmado_hipotiroidismo'].sum():,}")
        with col3: st.metric("Tasa de Confirmación", f"{tasa_conf:.1%}")

        stages = ["Tamizados", f"TSH ≥ {TSH_CORTE}", "Confirmados"]
        values = [df.shape[0], int(df["sospecha_hipotiroidismo"].sum()), int(df["confirmado_hipotiroidismo"].sum())]
        fig_funnel = go.Figure(go.Funnel(
            y=stages, x=values, textinfo="value+percent initial",
            marker={"color": ["#4682B4", "#FFA500", "#FF4500"]},
        ))
        fig_funnel.update_layout(title="Pirámide de Diagnóstico de Hipotiroidismo Congénito", height=500)
        st.plotly_chart(fig_funnel, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if "sexo" in filtered_df.columns:
                sex_counts = filtered_df.groupby(["sexo", "confirmado_hipotiroidismo"]).size().unstack(fill_value=0)
                if False not in sex_counts.columns: sex_counts[False] = 0
                if True  not in sex_counts.columns: sex_counts[True]  = 0
                sex_counts.columns = ["Normal", "Hipotiroidismo"]
                fig_sex = px.bar(sex_counts.reset_index(), x="sexo",
                                 y=["Normal","Hipotiroidismo"],
                                 title="Distribución por Sexo", barmode="group",
                                 color_discrete_map={"Normal":"#4682B4","Hipotiroidismo":"#FF4500"})
                st.plotly_chart(fig_sex, use_container_width=True)

        with col2:
            if "prematuro" in filtered_df.columns:
                filtered_df["prematuro"] = filtered_df["prematuro"].fillna(False)
                prem_counts = filtered_df.groupby(["prematuro","confirmado_hipotiroidismo"]).size().unstack(fill_value=0)
                if False not in prem_counts.columns: prem_counts[False] = 0
                if True  not in prem_counts.columns: prem_counts[True]  = 0
                prem_counts.columns = ["Normal","Hipotiroidismo"]
                prem_counts = prem_counts.reset_index()
                prem_counts["prematuro"] = prem_counts["prematuro"].map({True:"Prematuro",False:"No Prematuro"})
                fig_prem = px.bar(prem_counts, x="prematuro", y=["Normal","Hipotiroidismo"],
                                  title="Distribución por Prematuridad", barmode="group",
                                  color_discrete_map={"Normal":"#4682B4","Hipotiroidismo":"#FF4500"})
                st.plotly_chart(fig_prem, use_container_width=True)

        if "ciudad" in filtered_df.columns and "confirmado_hipotiroidismo" in filtered_df.columns:
            graficar_mapa_casos(filtered_df)

    # ── Análisis TSH ──────────────────────────────────────────────────────────
    with d_tabs[1]:
        st.header("📊 Análisis de TSH Neonatal")
        col1, col2 = st.columns(2)
        with col1:
            tsh_max_v = filtered_df["tsh_neonatal"].quantile(0.99)
            df_tsh_v  = filtered_df[filtered_df["tsh_neonatal"] <= tsh_max_v]
            fig_hist = px.histogram(df_tsh_v, x="tsh_neonatal", nbins=30,
                                    color_discrete_sequence=["#3CB371"],
                                    labels={"tsh_neonatal":"TSH Neonatal (mIU/L)"},
                                    title="Distribución de TSH Neonatal")
            fig_hist.add_vline(x=tsh_umbral, line_dash="dash", line_color="red",
                               annotation_text=f"Umbral: {tsh_umbral}")
            st.plotly_chart(fig_hist, use_container_width=True)
        with col2:
            df_s2 = filtered_df.dropna(subset=["tsh_neonatal","resultado_muestra_2"])
            fig_sc = px.scatter(df_s2, x="tsh_neonatal", y="resultado_muestra_2",
                                color="confirmado_hipotiroidismo",
                                color_discrete_map={True:"#FF4500",False:"#4682B4"},
                                title="TSH 1ª vs 2ª Muestra",
                                labels={"tsh_neonatal":"TSH 1ª muestra","resultado_muestra_2":"TSH 2ª muestra"})
            fig_sc.add_hline(y=tsh_umbral, line_dash="dash", line_color="red")
            fig_sc.add_vline(x=tsh_umbral, line_dash="dash", line_color="red")
            st.plotly_chart(fig_sc, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if "sexo" in filtered_df.columns:
                fig_box = px.box(filtered_df, x="sexo", y="tsh_neonatal", color="sexo",
                                 points="outliers", title="TSH por Sexo",
                                 labels={"tsh_neonatal":"TSH (mIU/L)"})
                fig_box.add_hline(y=tsh_umbral, line_dash="dash", line_color="red",
                                  annotation_text=f"Umbral: {tsh_umbral}")
                fig_box.update_yaxes(range=[0, 40])
                st.plotly_chart(fig_box, use_container_width=True)
        with col2:
            if "prematuro" in filtered_df.columns:
                ymax = max(30, filtered_df["tsh_neonatal"].quantile(0.95)) if not filtered_df.empty else 30
                fig_bp = px.box(filtered_df, x="prematuro", y="tsh_neonatal", color="prematuro",
                                points="outliers", title="TSH por Prematuridad",
                                labels={"tsh_neonatal":"TSH (mIU/L)"})
                fig_bp.add_hline(y=tsh_umbral, line_dash="dash", line_color="red",
                                 annotation_text=f"Umbral: {tsh_umbral}")
                fig_bp.update_yaxes(range=[0, ymax])
                st.plotly_chart(fig_bp, use_container_width=True)

    # ── Análisis Temporal ─────────────────────────────────────────────────────
    with d_tabs[2]:
        st.header("⏱️ Análisis Temporal")
        if "fecha_nacimiento" in filtered_df.columns:
            df_t = filtered_df.copy()
            df_t["año_mes"] = df_t["fecha_nacimiento"].dt.to_period("M")
            temp_df = df_t.groupby("año_mes").agg(
                total_casos=("tsh_neonatal","count"),
                casos_sospechosos=("sospecha_hipotiroidismo","sum"),
                casos_confirmados=("confirmado_hipotiroidismo","sum"),
                tsh_promedio=("tsh_neonatal","mean"),
            ).reset_index()
            temp_df["año_mes"] = temp_df["año_mes"].dt.to_timestamp()
            temp_df["tasa_confirmacion"] = temp_df["casos_confirmados"] / temp_df["casos_sospechosos"].replace(0, np.nan)

            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(x=temp_df["año_mes"], y=temp_df["casos_sospechosos"],
                                          mode="lines+markers", name="Sospechosos",
                                          line=dict(color="#FFA500", width=2)))
            fig_temp.add_trace(go.Scatter(x=temp_df["año_mes"], y=temp_df["casos_confirmados"],
                                          mode="lines+markers", name="Confirmados",
                                          line=dict(color="#FF4500", width=2)))
            fig_temp.add_trace(go.Scatter(x=temp_df["año_mes"], y=temp_df["tasa_confirmacion"],
                                          mode="lines", name="Tasa Confirmación",
                                          line=dict(color="#4682B4", dash="dot"), yaxis="y2"))
            fig_temp.update_layout(
                title="Evolución Temporal",
                yaxis=dict(title="Número de Casos", tickfont=dict(color="#FF4500")),
                yaxis2=dict(title="Tasa de Confirmación", overlaying="y", side="right",
                            range=[0,1], tickfont=dict(color="#4682B4")),
                legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"),
            )
            st.plotly_chart(fig_temp, use_container_width=True)

            df_t["mes"] = df_t["fecha_nacimiento"].dt.month
            seas = df_t.groupby("mes").agg(
                casos_sospechosos=("sospecha_hipotiroidismo","sum"),
                casos_confirmados=("confirmado_hipotiroidismo","sum"),
                tsh_promedio=("tsh_neonatal","mean"),
            ).reset_index()
            fig_seas = px.line(seas, x="mes",
                               y=["casos_sospechosos","casos_confirmados","tsh_promedio"],
                               title="Estacionalidad por Mes",
                               color_discrete_map={"casos_sospechosos":"#FFA500",
                                                   "casos_confirmados":"#FF4500",
                                                   "tsh_promedio":"#4682B4"})
            fig_seas.update_layout(xaxis=dict(
                tickvals=list(range(1,13)),
                ticktext=["Ene","Feb","Mar","Abr","May","Jun",
                          "Jul","Ago","Sep","Oct","Nov","Dic"]))
            st.plotly_chart(fig_seas, use_container_width=True)

            if "dias_pasados" in filtered_df.columns:
                st.subheader("Tiempos de Procesamiento")
                c1, c2 = st.columns(2)
                with c1:
                    fig_d = px.histogram(filtered_df, x="dias_pasados", nbins=20,
                                         title="Días hasta el Resultado",
                                         color_discrete_sequence=["#4682B4"])
                    st.plotly_chart(fig_d, use_container_width=True)
                with c2:
                    t_df = filtered_df.groupby("sospecha_hipotiroidismo")["dias_pasados"].mean().reset_index()
                    t_df["Estado"] = t_df["sospecha_hipotiroidismo"].map(
                        {True:f"Sospechoso (TSH ≥ {TSH_CORTE})", False:f"Normal (TSH < {TSH_CORTE})"})
                    fig_t = px.bar(t_df, x="Estado", y="dias_pasados",
                                   title="Tiempo Promedio por Estado",
                                   color="Estado",
                                   color_discrete_map={
                                       f"Sospechoso (TSH ≥ {TSH_CORTE})":"#FF4500",
                                       f"Normal (TSH < {TSH_CORTE})":"#4682B4"})
                    st.plotly_chart(fig_t, use_container_width=True)

    # ── Factores de Riesgo ────────────────────────────────────────────────────
    with d_tabs[3]:
        st.header("🔬 Análisis de Factores de Riesgo")
        if "peso" in filtered_df.columns:
            df_r = filtered_df.copy()
            df_r["peso_kg"] = pd.to_numeric(df_r["peso"], errors="coerce") / 1000
            fig_pr = px.scatter(df_r, x="peso_kg", y="tsh_neonatal",
                                color="confirmado_hipotiroidismo",
                                color_discrete_map={True:"#FF4500",False:"#4682B4"},
                                title="Peso al Nacer vs TSH",
                                labels={"peso_kg":"Peso (kg)","tsh_neonatal":"TSH (mIU/L)"},
                                trendline="ols", opacity=0.7)
            fig_pr.add_hline(y=tsh_umbral, line_dash="dash", line_color="red",
                             annotation_text=f"Umbral {tsh_umbral}")
            st.plotly_chart(fig_pr, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if "tipo_muestra" in filtered_df.columns and "id" in filtered_df.columns:
                tm_df = filtered_df.groupby("tipo_muestra").agg(
                    total=("id","count"), confirmados=("confirmado_hipotiroidismo","sum")).reset_index()
                tm_df["incidencia"] = (tm_df["confirmados"] / tm_df["total"]) * 100
                fig_tm = px.bar(tm_df, x="tipo_muestra", y="incidencia",
                                title="Incidencia por Tipo de Muestra",
                                color="incidencia", color_continuous_scale="Reds")
                st.plotly_chart(fig_tm, use_container_width=True)
        with col2:
            if "sexo" in filtered_df.columns and "id" in filtered_df.columns:
                sx_df = filtered_df.groupby("sexo").agg(
                    total=("id","count"), confirmados=("confirmado_hipotiroidismo","sum")).reset_index()
                sx_df["incidencia"] = (sx_df["confirmados"] / sx_df["total"]) * 100
                fig_sx = px.bar(sx_df, x="sexo", y="incidencia",
                                title="Incidencia por Sexo",
                                color="incidencia", color_continuous_scale="Reds")
                st.plotly_chart(fig_sx, use_container_width=True)

        if "peso" in filtered_df.columns and "prematuro" in filtered_df.columns:
            bins = [0, 1500, 2500, 4000, 10000]
            labels_b = ["Muy bajo (<1.5kg)","Bajo (1.5-2.5kg)","Normal (2.5-4kg)","Alto (>4kg)"]
            df_r2 = filtered_df.copy()
            df_r2["peso_num"] = pd.to_numeric(df_r2["peso"], errors="coerce")
            df_r2["rango_peso"] = pd.cut(df_r2["peso_num"], bins=bins, labels=labels_b)
            pp_df = df_r2.groupby(["prematuro","rango_peso"]).agg(
                total=("tsh_neonatal","count"),
                confirmados=("confirmado_hipotiroidismo","sum")).reset_index()
            pp_df["incidencia"] = (pp_df["confirmados"] / pp_df["total"]) * 100
            pp_df["prematuro_label"] = pp_df["prematuro"].map({True:"Prematuro",False:"No Prematuro"})
            fig_pp = px.bar(pp_df, x="rango_peso", y="incidencia",
                            color="prematuro_label", barmode="group",
                            title="Incidencia por Peso y Prematuridad",
                            color_discrete_map={"Prematuro":"#FF4500","No Prematuro":"#4682B4"})
            st.plotly_chart(fig_pp, use_container_width=True)

        if all(c in filtered_df.columns for c in ["peso","tsh_neonatal","resultado_muestra_2","dias_pasados","sexo"]):
            df_c = filtered_df.copy()
            df_c["sexo_num"] = df_c["sexo"].map({"MASCULINO":0,"FEMENINO":1})
            corr = df_c[["peso","tsh_neonatal","resultado_muestra_2","dias_pasados","sexo_num"]].corr()
            fig_corr = px.imshow(corr, text_auto=True, aspect="auto",
                                 color_continuous_scale="RdBu_r", title="Matriz de Correlación")
            st.plotly_chart(fig_corr, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — CASOS CONFIRMADOS + ALERTAS SMS
# ═════════════════════════════════════════════════════════════════════════════

with tab_alertas:
    st.header("🚨 Casos Confirmados y Alertas SMS")

    # Cargar dataset para esta tab
    df_a = load_data()

    if df_a.empty:
        st.warning("Sin datos disponibles. Verifica el archivo CSV principal.")
    else:
        confirmed_df = df_a[df_a["confirmado_hipotiroidismo"] == True].copy()

        if confirmed_df.empty:
            st.info("No hay casos confirmados en el dataset actual.")
        else:
            # ── Métricas rápidas ──────────────────────────────────────────
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Total Confirmados", confirmed_df.shape[0])
            with c2: st.metric("TSH Promedio", f"{confirmed_df['tsh_neonatal'].mean():.1f} mIU/L")
            with c3:
                if "dias_pasados" in confirmed_df.columns:
                    st.metric("Días prom. diagnóstico", f"{confirmed_df['dias_pasados'].mean():.1f}")

            st.markdown("---")

            # ── SMS Individual ────────────────────────────────────────────
            st.subheader("📱 Envío Individual")
            col_sel, col_det = st.columns([1, 2])

            with col_sel:
                id_col = "id" if "id" in confirmed_df.columns else confirmed_df.columns[0]
                ciudad_col = "ciudad" if "ciudad" in confirmed_df.columns else ""
                options = confirmed_df.index.tolist()
                fmt = lambda x: (f"ID: {confirmed_df.loc[x, id_col]} — "
                                 f"{confirmed_df.loc[x, ciudad_col] if ciudad_col else x}")
                selected = st.selectbox("Seleccionar caso:", options=options, format_func=fmt)

            fila = confirmed_df.loc[selected]
            with col_det:
                d1, d2 = st.columns(2)
                with d1:
                    st.write(f"**ID:** {fila.get('id','—')}")
                    st.write(f"**TSH 1ª muestra:** {fila.get('tsh_neonatal','—')} mIU/L")
                    st.write(f"**TSH 2ª muestra:** {fila.get('resultado_muestra_2','—')} mIU/L")
                with d2:
                    st.write(f"**Ciudad:** {fila.get('ciudad','—')}")
                    st.write(f"**Departamento:** {fila.get('departamento','—')}")
                    st.write(f"**ARS:** {fila.get('ars','—')}")

            tel_ind = st.text_input("Teléfono destinatario:", placeholder="+573XXXXXXXXX", key="tel_ind")
            tel_irs_ind = st.text_input("Teléfono IRS:", placeholder="+573XXXXXXXXX", key="tel_irs_ind")

            msg_ind = st.text_area(
                "Mensaje al paciente/acudiente:",
                value=(f"Alerta: El resultado del tamizaje de hipotiroidismo de su hijo(a) "
                       f"es POSITIVO (TSH: {fila.get('resultado_muestra_2','—')} mIU/L). "
                       f"Contacte a {fila.get('ars','su EPS')} para iniciar tratamiento urgente."),
                height=90, key="msg_ind",
            )
            msg_irs_ind = st.text_area(
                "Mensaje a la IRS:",
                value=(f"Caso confirmado: ID {fila.get('id','—')}, "
                       f"Ciudad {fila.get('ciudad','—')}, "
                       f"TSH: {fila.get('resultado_muestra_2','—')} mIU/L. "
                       f"ARS: {fila.get('ars','—')}. Requiere seguimiento urgente."),
                height=90, key="msg_irs_ind",
            )
            test_ind = st.checkbox("🧪 Modo prueba", value=True, key="test_ind")

            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("📤 Enviar SMS al Paciente", key="btn_pac"):
                    if tel_ind:
                        ok, status = enviar_sms(tel_ind, msg_ind, test_ind)
                        (st.success if ok else st.error)(status)
                        st.session_state.setdefault("sms_log", []).append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "id_caso": fila.get("id","—"), "destino":"Paciente",
                            "telefono": tel_ind, "status": status,
                        })
                    else:
                        st.warning("Ingresa un teléfono.")

            with c_btn2:
                if st.button("🏥 Enviar SMS a la IRS", key="btn_irs"):
                    if tel_irs_ind:
                        ok, status = enviar_sms(tel_irs_ind, msg_irs_ind, test_ind)
                        (st.success if ok else st.error)(status)
                        st.session_state.setdefault("sms_log", []).append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "id_caso": fila.get("id","—"), "destino":"IRS",
                            "telefono": tel_irs_ind, "status": status,
                        })
                    else:
                        st.warning("Ingresa el teléfono de la IRS.")

            st.markdown("---")

            # ── SMS Masivo ────────────────────────────────────────────────
            st.subheader("📡 Envío Masivo a Todos los Confirmados")

            has_phones = any(c in confirmed_df.columns for c in ["telefono_1","telefono_2","tel1","tel2"])
            if not has_phones:
                st.warning("No se encontraron columnas de teléfono en el dataset (telefono_1 / telefono_2).")
            else:
                phone_col = next((c for c in ["telefono_1","telefono_2","tel1","tel2"]
                                  if c in confirmed_df.columns), None)
                n_con_tel = confirmed_df[phone_col].notna().sum() if phone_col else 0
                st.info(f"{n_con_tel} de {len(confirmed_df)} casos tienen teléfono disponible.")

                tmpl_pac = st.text_area(
                    "Plantilla mensaje paciente (use {tsh} y {ars}):",
                    value="Alerta: El TSH neonatal de su hijo(a) es {tsh} mIU/L. Contacte a {ars} urgente.",
                    height=80, key="tmpl_pac",
                )
                tmpl_irs_col = st.text_input("Teléfono IRS (único para todos):", key="irs_mass")
                tmpl_irs_msg = st.text_area(
                    "Plantilla mensaje IRS:",
                    value="Nuevo caso confirmado: TSH {tsh} mIU/L — ARS {ars}. Requiere seguimiento.",
                    height=80, key="tmpl_irs_msg",
                )
                test_mass = st.checkbox("🧪 Modo prueba masivo", value=True, key="test_mass")

                if st.button("🚀 Enviar a Todos los Casos Confirmados", key="btn_mass"):
                    log_mass = []
                    bar = st.progress(0)
                    status_txt = st.empty()
                    sent, failed = 0, 0

                    rows_list = list(confirmed_df.iterrows())
                    for i, (idx, row) in enumerate(rows_list):
                        bar.progress((i + 1) / len(rows_list))
                        status_txt.text(f"Procesando {i+1}/{len(rows_list)}…")

                        tel = str(row.get(phone_col, "")).strip() if phone_col else ""
                        tsh_v = str(row.get("resultado_muestra_2", ""))
                        ars_v = str(row.get("ars", "su EPS"))

                        if tel and tel not in ("nan","0",""):
                            msg_p = tmpl_pac.replace("{tsh}", tsh_v).replace("{ars}", ars_v)
                            ok, s = enviar_sms(tel, msg_p, test_mass)
                            log_mass.append({"id": row.get("id","—"), "destino":"Paciente",
                                             "telefono": tel, "status": s})
                            sent += 1 if ok else 0
                            failed += 0 if ok else 1

                        if tmpl_irs_col:
                            msg_i = tmpl_irs_msg.replace("{tsh}", tsh_v).replace("{ars}", ars_v)
                            ok, s = enviar_sms(tmpl_irs_col, msg_i, test_mass)
                            log_mass.append({"id": row.get("id","—"), "destino":"IRS",
                                             "telefono": tmpl_irs_col, "status": s})

                    bar.progress(1.0)
                    status_txt.empty()
                    st.success(f"✅ Completado: {sent} enviados, {failed} fallidos.")
                    st.session_state.setdefault("sms_log", []).extend(log_mass)

            st.markdown("---")

            # ── Tabla casos + descarga ────────────────────────────────────
            st.subheader("📋 Detalle de Casos Confirmados")
            cols_show = [c for c in ["id","ciudad","departamento","sexo","fecha_nacimiento",
                                      "peso","prematuro","tsh_neonatal","resultado_muestra_2",
                                      "dias_pasados"] if c in confirmed_df.columns]
            st.dataframe(confirmed_df[cols_show], use_container_width=True, height=350)

            csv_bytes = confirmed_df[cols_show].to_csv(index=False).encode("utf-8")
            st.download_button("⬇  Descargar casos confirmados CSV",
                               csv_bytes, "casos_confirmados.csv", "text/csv")

            # TSH distribución
            fig_tsh_c = px.histogram(confirmed_df, x="tsh_neonatal", nbins=20,
                                     title="Distribución TSH en Casos Confirmados",
                                     color_discrete_sequence=["#FF4500"])
            st.plotly_chart(fig_tsh_c, use_container_width=True)

    # ── Log global de SMS ─────────────────────────────────────────────────────
    if st.session_state.get("sms_log"):
        st.markdown("---")
        with st.expander("📋  Historial completo de SMS"):
            log_df = pd.DataFrame(st.session_state["sms_log"])
            st.dataframe(log_df, use_container_width=True)
            st.download_button("⬇ Exportar log", log_df.to_csv(index=False).encode(),
                               "sms_log.csv", "text/csv")

# ── Sidebar info ──────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.info("""
**Hipotiroidismo Congénito — Sistema de Tamizaje**

📝 Ingresa datos desde la tarjeta física
📊 Analiza resultados y tendencias
🚨 Gestiona alertas a pacientes e IRS

Desarrollado por: Luis Carlos Pallares Ascanio
""")
st.sidebar.markdown("---")
st.sidebar.markdown(f"""
**Notas clínicas:**
- Sospecha: TSH ≥ {TSH_CORTE} mIU/L en 1ª muestra
- Confirmación: TSH ≥ {TSH_CORTE} mIU/L en 2ª muestra
""")
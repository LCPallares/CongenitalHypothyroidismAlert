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
    "id", "ficha_id", "fecha_ingreso", "institucion", "ars",
    "historia_clinica", "tipo_documento", "numero_documento",
    "ciudad", "departamento", "telefono_1", "telefono_2", "direccion",
    "apellido_1", "apellido_2", "nombre_hijo",
    "fecha_nacimiento", "peso", "sexo", "prematuro", "transfundido",
    "informacion_completa", "muestra_adecuada", "destino_muestra",
    "tipo_muestra", "fecha_toma_muestra", "fecha_resultado", "tsh_neonatal",
    "ficha_id_2", "tipo_muestra_2", "fecha_toma_muestra_2",
    "fecha_resultado_muestra_2", "resultado_muestra_2", "contador",
    "muestra_rechazada", "fecha_toma_rechazada", "tipo_vinculacion",
    "resultado_rechazada", "fecha_resultado_rechazada",
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
        return max(int(r.get("id", 0)) for r in rows) + 1
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
    path = "../../data/hipotiroidismo_registros.csv"
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

# ─── Helpers CSV de registros propios ────────────────────────────────────────

def leer_registros() -> pd.DataFrame:
    """Lee el CSV de registros propios. Retorna DataFrame vacío si no existe."""
    if not os.path.isfile(CSV_REGISTROS):
        return pd.DataFrame(columns=FIELDNAMES)
    df = pd.read_csv(CSV_REGISTROS, dtype=str).fillna("")
    return df

def actualizar_registro(id_registro: int, campos: dict):
    """Sobreescribe los campos indicados en la fila con el id dado."""
    df = leer_registros()
    mask = df["id"].astype(str) == str(id_registro)
    for col, val in campos.items():
        if col in df.columns:
            df.loc[mask, col] = str(val)
    df.to_csv(CSV_REGISTROS, index=False)

def buscar_por_ficha(ficha: str) -> pd.Series | None:
    """Retorna la fila cuyo 'ficha_id' == ficha, o None."""
    df = leer_registros()
    if df.empty:
        return None
    match = df[df["ficha_id"].str.strip() == ficha.strip()]
    if match.empty:
        return None
    return match.iloc[0]


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — FORMULARIO DE INGRESO
# ═════════════════════════════════════════════════════════════════════════════

with tab_form:

    # ── Selector de modo ─────────────────────────────────────────────────────
    modo = st.radio(
        "¿Qué deseas hacer?",
        ["📋  Registrar nueva tarjeta", "🔬  Cargar resultados de laboratorio"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # MODO A — NUEVO REGISTRO (solo datos del paciente y muestra, sin TSH)
    # ══════════════════════════════════════════════════════════════════════════
    if modo == "📋  Registrar nueva tarjeta":

        st.markdown("## 📋 Nueva Tarjeta de Tamizaje")
        st.caption("Ingrese los datos de la tarjeta física enviada por la IRS. ★ = obligatorio.")

        # ── Sección institución ───────────────────────────────────────────────
        st.markdown('<div class="form-section">🏥  Institución / Acudiente</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            ficha         = st.text_input("★ No. de Ficha", placeholder="369980", key="n_ficha")
            fecha_ingreso = st.date_input("★ Fecha de Ingreso", value=None,
                                          min_value=date(2000, 1, 1), max_value=date.today(),
                                          key="n_fi")
            institucion   = st.text_input("★ Institución", placeholder="VICTORIA", key="n_inst")
        with c2:
            ars           = st.text_input("★ ARS / EPS", placeholder="MEDIMAS", key="n_ars")
            historia      = st.text_input("Historia Clínica", key="n_hist")
            tipo_doc      = st.selectbox("★ Tipo de Documento",
                                         ["Seleccionar...", "CC", "CE", "PA", "RC", "TI"], key="n_tdoc")
        with c3:
            num_doc       = st.text_input("★ Número de Documento", key="n_ndoc")
            ciudad        = st.text_input("★ Ciudad", placeholder="Bogotá", key="n_ciudad")
            departamento  = st.selectbox("★ Departamento", DEPARTAMENTOS, key="n_depto")

        c4, c5 = st.columns(2)
        with c4:
            tel1      = st.text_input("Teléfono 1", placeholder="3130000000", key="n_tel1")
            tipo_vinc = st.selectbox("★ Tipo de Vinculación",
                                     ["Seleccionar...", "CONTRIBUTIVO", "SUBSIDIADO",
                                      "VINCULADO", "PARTICULAR", "ESPECIAL"], key="n_vinc")
        with c5:
            tel2      = st.text_input("Teléfono 2 (opcional)", key="n_tel2")
            direccion = st.text_input("Dirección", key="n_dir")

        # ── Sección neonato ───────────────────────────────────────────────────
        st.markdown('<div class="form-section">👶  Datos del Recién Nacido</div>', unsafe_allow_html=True)
        c6, c7, c8 = st.columns(3)
        with c6:
            apellido1 = st.text_input("★ Primer Apellido", key="n_ap1")
            apellido2 = st.text_input("Segundo Apellido", key="n_ap2")
        with c7:
            nombre    = st.text_input("★ Nombre / Hijo(a) de", key="n_nom")
            fecha_nac = st.date_input("★ Fecha de Nacimiento", value=None,
                                      min_value=date(2000, 1, 1), max_value=date.today(),
                                      key="n_fnac")
        with c8:
            peso      = st.text_input("★ Peso al nacer (g)", placeholder="2890", key="n_peso")
            sexo      = st.selectbox("★ Sexo",
                                     ["Seleccionar...", "MASCULINO", "FEMENINO", "INDETERMINADO"], key="n_sexo")

        c9, c10 = st.columns(2)
        with c9:
            prematuro    = st.checkbox("Prematuro", key="n_prem")
            transfundido = st.checkbox("Transfundido", key="n_trans")
        with c10:
            info_completa = st.checkbox("Información completa", key="n_info")
            muestra_adec  = st.checkbox("Muestra adecuada", key="n_madec")

        # ── Sección muestra (sin resultados) ──────────────────────────────────
        st.markdown('<div class="form-section">🔬  Datos de la Muestra</div>', unsafe_allow_html=True)
        st.caption("Solo se registra la toma. Los resultados de laboratorio se cargan después.")

        c11, c12, c13 = st.columns(3)
        with c11:
            tipo_muestra1 = st.selectbox("★ Tipo de Muestra",
                                         ["Seleccionar...", "CORDON", "TALON", "VENA"], key="n_tm1")
            destino       = st.selectbox("★ Destino muestra",
                                         ["Seleccionar...", "ACEPTADA", "RECHAZADA"], key="n_dest")
        with c12:
            fecha_muestra1 = st.date_input("★ Fecha toma muestra", value=None,
                                           min_value=date(2000, 1, 1), max_value=date.today(),
                                           key="n_fm1")
        with c13:
            tipo_vinc_m = ""  # placeholder — vinculación ya capturada arriba

        # Muestra rechazada (opcional)
        with st.expander("❌  Muestra rechazada (si aplica)"):
            m_rechazada      = st.checkbox("¿Hubo muestra rechazada?", key="n_mrech")
            fecha_rechaz     = st.date_input("Fecha toma rechazada", value=None,
                                              min_value=date(2000, 1, 1), max_value=date.today(),
                                              key="n_frech")

        # ── Botón guardar ─────────────────────────────────────────────────────
        st.markdown("---")
        if st.button("💾  Guardar Tarjeta", type="primary", key="btn_guardar_nueva"):
            errors = []

            # Obligatorios texto
            for val, label in [
                (ficha, "No. de Ficha"), (institucion, "Institución"), (ars, "ARS"),
                (num_doc, "Número Documento"), (ciudad, "Ciudad"),
                (apellido1, "Primer Apellido"), (nombre, "Nombre"),
            ]:
                if not val.strip():
                    errors.append(f"**{label}** es obligatorio")

            # Obligatorios selectbox
            for val, label in [
                (tipo_doc, "Tipo de Documento"), (departamento, "Departamento"),
                (sexo, "Sexo"), (tipo_vinc, "Tipo de Vinculación"),
                (tipo_muestra1, "Tipo de Muestra"), (destino, "Destino muestra"),
            ]:
                if not val or val == "Seleccionar...":
                    errors.append(f"**{label}** es obligatorio")

            # Fechas — ya son objetos date, solo verificar que se seleccionaron
            d_fi = fecha_ingreso  # date object o None
            d_fn = fecha_nac      # date object o None
            if d_fi is None:
                errors.append("**Fecha de Ingreso** es obligatoria")
            if d_fn is None:
                errors.append("**Fecha de Nacimiento** es obligatoria")
            if d_fi and d_fn:
                if d_fn > d_fi:
                    errors.append("Fecha de nacimiento no puede ser posterior a la fecha de ingreso")
                if (date.today() - d_fn).days > 365:
                    errors.append("Fecha de nacimiento inusual (más de 1 año atrás)")
            if fecha_muestra1 is None:
                errors.append("**Fecha toma muestra** es obligatoria")

            # Peso
            v_peso, e = val_peso(peso)
            if e: errors.append(e)

            if ficha.strip() and buscar_por_ficha(ficha):
                errors.append(f"Ya existe un registro con la ficha **{ficha}**. "
                               f"Para cargar resultados usa el modo 'Cargar resultados de laboratorio'.")

            if errors:
                st.error(f"**{len(errors)} error(es) encontrados:**")
                for e in errors:
                    st.markdown(f"- {e}")
            else:
                row = {f: "" for f in FIELDNAMES}
                row.update({
                    "id":                       next_id(),
                    "ficha_id":                 ficha.strip(),
                    "fecha_ingreso":            fecha_ingreso.isoformat() if fecha_ingreso else "",
                    "institucion":              institucion.strip(),
                    "ars":                      ars.strip(),
                    "historia_clinica":         historia.strip(),
                    "tipo_documento":           tipo_doc,
                    "numero_documento":         num_doc.strip(),
                    "ciudad":                   ciudad.strip(),
                    "departamento":             departamento,
                    "telefono_1":               tel1.strip() or "0",
                    "telefono_2":               tel2.strip() or "0",
                    "direccion":                direccion.strip(),
                    "apellido_1":               apellido1.strip(),
                    "apellido_2":               apellido2.strip(),
                    "nombre_hijo":              nombre.strip(),
                    "fecha_nacimiento":         fecha_nac.isoformat() if fecha_nac else "",
                    "peso":                     v_peso,
                    "sexo":                     sexo,
                    "prematuro":                "VERDADERO" if prematuro else "FALSO",
                    "transfundido":             "VERDADERO" if transfundido else "FALSO",
                    "informacion_completa":     "VERDADERO" if info_completa else "FALSO",
                    "muestra_adecuada":         "VERDADERO" if muestra_adec else "FALSO",
                    "destino_muestra":          destino,
                    "tipo_muestra":             tipo_muestra1,
                    "fecha_toma_muestra":       fecha_muestra1.isoformat() if fecha_muestra1 else "",
                    "muestra_rechazada":        "VERDADERO" if m_rechazada else "FALSO",
                    "fecha_toma_rechazada":     fecha_rechaz.isoformat() if fecha_rechaz else "",
                    "tipo_vinculacion":         tipo_vinc,
                    "contador":                 "0",
                })
                guardar_registro(row)
                st.success(f"✅ Tarjeta **#{row['id']}** — Ficha **{ficha}** guardada. "
                           f"Cuando lleguen los resultados búscala por No. de Ficha.")

    # ══════════════════════════════════════════════════════════════════════════
    # MODO B — CARGAR RESULTADOS (buscar por ficha → completar TSH)
    # ══════════════════════════════════════════════════════════════════════════
    else:
        st.markdown("## 🔬 Carga de Resultados de Laboratorio")
        st.caption("Busca el registro por No. de Ficha y agrega los resultados de TSH.")

        # ── Buscador ──────────────────────────────────────────────────────────
        col_busq, col_btn = st.columns([3, 1])
        with col_busq:
            ficha_buscar = st.text_input("No. de Ficha:", placeholder="369980", key="busq_ficha")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            buscar = st.button("🔍  Buscar", key="btn_buscar", use_container_width=True)

        # ── Resultado de la búsqueda ──────────────────────────────────────────
        reg = None
        if buscar or st.session_state.get("reg_encontrado"):
            if buscar:
                reg = buscar_por_ficha(ficha_buscar)
                st.session_state["reg_encontrado"] = reg.to_dict() if reg is not None else None
            elif st.session_state.get("reg_encontrado"):
                import pandas as _pd
                reg = _pd.Series(st.session_state["reg_encontrado"])

            if reg is None:
                st.error(f"No se encontró ningún registro con la ficha **{ficha_buscar}**.")
            else:
                # ── Tarjeta resumen del paciente ──────────────────────────────
                st.markdown('<div class="form-section">👤  Paciente encontrado</div>', unsafe_allow_html=True)
                ci1, ci2, ci3, ci4 = st.columns(4)
                ci1.metric("Ficha", reg.get("ficha_id", "—"))
                ci2.metric("Paciente", f"{reg.get('apellido_1','')} {reg.get('apellido_2','')}")
                ci3.metric("Fecha nacimiento", reg.get("fecha_nacimiento", "—"))
                ci4.metric("Institución", reg.get("institucion", "—"))

                ci5, ci6, ci7, ci8 = st.columns(4)
                ci5.metric("Ciudad", reg.get("ciudad", "—"))
                ci6.metric("ARS", reg.get("ars", "—"))
                ci7.metric("Tipo muestra", reg.get("tipo_muestra", "—"))
                ci8.metric("Fecha toma", reg.get("fecha_toma_muestra", "—"))

                # Estado actual del registro
                tsh1_actual = reg.get("tsh_neonatal", "").strip()
                tsh2_actual = reg.get("resultado_muestra_2", "").strip()
                ya_tiene_tsh1 = tsh1_actual not in ("", "0")
                ya_tiene_tsh2 = tsh2_actual not in ("", "0")

                if ya_tiene_tsh1:
                    st.info(f"ℹ️  Este registro ya tiene TSH1 = **{tsh1_actual} µIU/mL**"
                            + (f" y TSH2 = **{tsh2_actual} µIU/mL**" if ya_tiene_tsh2 else "")
                            + ". Puedes corregir los valores abajo.")

                st.markdown("---")

                # ── Formulario de resultados ──────────────────────────────────
                st.markdown('<div class="form-section">🔬  Resultado — Muestra 1</div>', unsafe_allow_html=True)

                r1, r2, r3 = st.columns(3)
                with r1:
                    fecha_result1 = st.date_input(
                        "★ Fecha de resultado",
                        value=pd.to_datetime(reg.get("fecha_resultado") or None, errors="coerce"),
                        min_value=date(2000, 1, 1), max_value=date.today(),
                        key="r_fres1",
                    )
                with r2:
                    tsh1_str = st.text_input(
                        "★ Resultado TSH 1 (µIU/mL)",
                        value=tsh1_actual if ya_tiene_tsh1 else "",
                        placeholder="7.2", key="r_tsh1",
                    )
                with r3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    # Preview en tiempo real
                    if tsh1_str.strip():
                        try:
                            v_preview = float(tsh1_str.replace(",", "."))
                            if v_preview >= TSH_CORTE:
                                st.warning(f"⚠️ TSH1 = {v_preview} — requiere 2ª muestra")
                            else:
                                st.success(f"✅ TSH1 = {v_preview} — dentro del rango normal")
                        except ValueError:
                            pass

                # Calcular si necesita muestra 2
                tsh1_num = None
                if tsh1_str.strip():
                    try:
                        tsh1_num = float(tsh1_str.replace(",", "."))
                    except ValueError:
                        pass

                necesita_m2 = tsh1_num is not None and tsh1_num >= TSH_CORTE

                # ── Muestra 2 (solo si TSH1 ≥ 15) ────────────────────────────
                ficha2 = tipo_m2 = fecha_m2 = f_res2 = tsh2_str = ""
                if necesita_m2:
                    st.markdown(
                        f'<div class="tsh-alert">⚠️ TSH1 = <strong>{tsh1_num} µIU/mL</strong> ≥ {TSH_CORTE} — '
                        f'Se requiere 2ª muestra de confirmación.</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown('<div class="form-section">🔁  Resultado — Muestra 2</div>', unsafe_allow_html=True)

                    m2a, m2b, m2c = st.columns(3)
                    with m2a:
                        ficha2  = st.text_input("No. Ficha 2",
                                                value=reg.get("ficha_id_2", ""), key="r_f2")
                        tipo_m2 = st.selectbox("★ Tipo muestra 2",
                                               ["Seleccionar...", "CORDON", "TALON", "VENA"],
                                               key="r_tm2")
                    with m2b:
                        fecha_m2 = st.date_input("★ Fecha toma muestra 2",
                                                 value=pd.to_datetime(reg.get("fecha_toma_muestra_2") or None, errors="coerce"),
                                                 min_value=date(2000, 1, 1), max_value=date.today(),
                                                 key="r_fm2")
                        f_res2   = st.date_input("★ Fecha resultado 2",
                                                 value=pd.to_datetime(reg.get("fecha_resultado_muestra_2") or None, errors="coerce"),
                                                 min_value=date(2000, 1, 1), max_value=date.today(),
                                                 key="r_fr2")
                    with m2c:
                        tsh2_str = st.text_input("★ Resultado TSH 2 (µIU/mL)",
                                                 value=tsh2_actual if ya_tiene_tsh2 else "",
                                                 placeholder="18.5", key="r_tsh2")

                    # Preview TSH2
                    if tsh2_str.strip():
                        try:
                            tsh2_preview = float(tsh2_str.replace(",", "."))
                            if tsh2_preview >= TSH_CORTE:
                                st.error(f"🚨 TSH2 = {tsh2_preview} µIU/mL — "
                                         f"**HIPOTIROIDISMO CONFIRMADO**. Se debe notificar al paciente y a la IRS.")
                            else:
                                st.success(f"✅ TSH2 = {tsh2_preview} µIU/mL — Segunda muestra normal.")
                        except ValueError:
                            pass

                # ── SMS si es positivo confirmado ─────────────────────────────
                v_tsh2_final = None
                if tsh2_str.strip():
                    try:
                        v_tsh2_final = float(tsh2_str.replace(",", "."))
                    except ValueError:
                        pass

                confirmado = necesita_m2 and v_tsh2_final is not None and v_tsh2_final >= TSH_CORTE

                if confirmado:
                    st.markdown('<div class="form-section">📱  Notificación SMS</div>', unsafe_allow_html=True)
                    tel_reg    = reg.get("telefono_1", "") or reg.get("telefono_2", "")
                    ars_reg    = reg.get("ars", "su EPS")
                    nombre_reg = reg.get("nombre_hijo", "")

                    sms_col1, sms_col2 = st.columns(2)
                    with sms_col1:
                        notif_paciente = st.checkbox("Notificar al paciente/acudiente", key="r_notif_pac")
                        if notif_paciente:
                            tel_pac = st.text_input("Teléfono paciente",
                                                    value=tel_reg, key="r_tel_pac")
                            msg_pac = st.text_area("Mensaje paciente",
                                value=f"Alerta: El resultado del tamizaje de hipotiroidismo de {nombre_reg} "
                                      f"es POSITIVO (TSH: {tsh2_str} µIU/mL). "
                                      f"Contacte a {ars_reg} para iniciar tratamiento urgente.",
                                height=90, key="r_msg_pac")
                    with sms_col2:
                        notif_irs = st.checkbox("Notificar a la IRS", key="r_notif_irs")
                        if notif_irs:
                            tel_irs = st.text_input("Teléfono IRS", key="r_tel_irs")
                            msg_irs = st.text_area("Mensaje IRS",
                                value=f"Caso confirmado — Ficha {reg.get('ficha_id','')}: "
                                      f"Paciente {reg.get('apellido_1','')} {reg.get('apellido_2','')}, "
                                      f"Ciudad: {reg.get('ciudad','')}, TSH: {tsh2_str} µIU/mL. "
                                      f"ARS: {ars_reg}. Requiere seguimiento urgente.",
                                height=90, key="r_msg_irs")

                    sms_test = st.checkbox("🧪 Modo de prueba (no envía realmente)", value=True, key="r_sms_test")

                # ── Botón guardar resultados ──────────────────────────────────
                st.markdown("---")
                if st.button("💾  Guardar Resultados", type="primary", key="btn_guardar_res"):
                    errors = []

                    # Fecha resultado 1
                    if fecha_result1 is None:
                        errors.append("Fecha resultado 1 es obligatoria")

                    # TSH 1
                    v_tsh1, e = val_tsh(tsh1_str, "TSH 1")
                    if e: errors.append(e)

                    # Muestra 2
                    v_tsh2 = None
                    if necesita_m2:
                        v_tsh2, e = val_tsh(tsh2_str, "TSH 2")
                        if e: errors.append(e)
                        if not tipo_m2 or tipo_m2 == "Seleccionar...":
                            errors.append("Tipo de muestra 2 es obligatorio")
                        if fecha_m2 is None:
                            errors.append("Fecha toma muestra 2 es obligatoria")
                        if f_res2 is None:
                            errors.append("Fecha resultado 2 es obligatoria")

                    if errors:
                        st.error(f"**{len(errors)} error(es):**")
                        for e in errors:
                            st.markdown(f"- {e}")
                    else:
                        # Campos a actualizar
                        campos_actualizar = {
                            "fecha_resultado":      fecha_result1.isoformat() if fecha_result1 else "",
                            "tsh_neonatal":         v_tsh1,
                        }
                        if necesita_m2 and v_tsh2 is not None:
                            campos_actualizar.update({
                                "ficha_id_2":               ficha2.strip() or "0",
                                "tipo_muestra_2":           tipo_m2,
                                "fecha_toma_muestra_2":     fecha_m2.isoformat() if fecha_m2 else "",
                                "fecha_resultado_muestra_2":f_res2.isoformat() if f_res2 else "",
                                "resultado_muestra_2":      v_tsh2,
                                "contador":                 "1",
                            })

                        actualizar_registro(int(reg["id"]), campos_actualizar)
                        st.session_state["reg_encontrado"] = None

                        if confirmado:
                            st.error(f"🚨 **CASO POSITIVO CONFIRMADO** — Ficha {reg.get('ficha_id')}")
                        else:
                            st.success(f"✅ Resultados guardados para Ficha **{reg.get('ficha_id')}**."
                                       + (" Caso cerrado como normal." if not necesita_m2 else ""))

                        sms_log = st.session_state.setdefault("sms_log", [])
                        if confirmado:
                            if st.session_state.get("r_notif_pac") and st.session_state.get("r_tel_pac"):
                                ok, status = enviar_sms(
                                    st.session_state["r_tel_pac"],
                                    st.session_state.get("r_msg_pac", ""),
                                    st.session_state.get("r_sms_test", True),
                                )
                                sms_log.append({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                                "id_caso": reg["id"], "destino": "Paciente",
                                                "telefono": st.session_state["r_tel_pac"], "status": status})
                                (st.success if ok else st.error)(f"📱 Paciente: {status}")

                            if st.session_state.get("r_notif_irs") and st.session_state.get("r_tel_irs"):
                                ok, status = enviar_sms(
                                    st.session_state["r_tel_irs"],
                                    st.session_state.get("r_msg_irs", ""),
                                    st.session_state.get("r_sms_test", True),
                                )
                                sms_log.append({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                                "id_caso": reg["id"], "destino": "IRS",
                                                "telefono": st.session_state["r_tel_irs"], "status": status})
                                (st.success if ok else st.error)(f"🏥 IRS: {status}")

    # ── Historial SMS de la sesión ────────────────────────────────────────────
    if st.session_state.get("sms_log"):
        with st.expander("📋  Historial de SMS enviados en esta sesión"):
            st.dataframe(pd.DataFrame(st.session_state["sms_log"]), use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — DASHBOARD
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

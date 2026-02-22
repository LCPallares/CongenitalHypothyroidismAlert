# pages/3_🚨_Alertas.py
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.constantes import CSS, TSH_CORTE, CSV_REGISTROS

st.set_page_config(page_title="Alertas", page_icon="🚨", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.title("🚨 Casos Confirmados y Alertas SMS")


# ── SMS (solo esta página lo necesita) ───────────────────────────────────────
def enviar_sms(telefono: str, mensaje: str, test_mode: bool = True) -> tuple[bool, str]:
    if not telefono.strip():
        return False, "Teléfono vacío"
    if not telefono.startswith("+"):
        telefono = "+57" + telefono.strip()
    if test_mode:
        return True, f"[SIMULADO] → {telefono}: {mensaje[:60]}..."
    try:
        from twilio.rest import Client
        sid   = st.secrets["twilio"]["account_sid"]
        token = st.secrets["twilio"]["auth_token"]
        from_ = st.secrets["twilio"]["from_phone_number"]
        msg   = Client(sid, token).messages.create(body=mensaje, from_=from_, to=telefono)
        return True, f"Enviado — SID: {msg.sid}"
    except KeyError:
        return False, "Faltan credenciales en st.secrets['twilio']"
    except Exception as e:
        return False, f"Error Twilio: {e}"


# ── Cargar datos ──────────────────────────────────────────────────────────────
@st.cache_data
def load_confirmados():
    try:
        df = pd.read_csv(CSV_REGISTROS, dtype=str).fillna("")
    except FileNotFoundError:
        return pd.DataFrame()
    df["tsh_neonatal"]       = pd.to_numeric(df["tsh_neonatal"], errors="coerce").fillna(0)
    df["resultado_muestra_2"]= pd.to_numeric(df["resultado_muestra_2"], errors="coerce").fillna(0)
    return df[(df["tsh_neonatal"] >= TSH_CORTE) & (df["resultado_muestra_2"] >= TSH_CORTE)].copy()


if st.button("🔄 Refrescar datos"):
    st.cache_data.clear()
    st.rerun()

confirmed_df = load_confirmados()

if confirmed_df.empty:
    st.info("No hay casos confirmados aún. Los casos aparecen aquí cuando TSH1 y TSH2 superan "
            f"el umbral de {TSH_CORTE} µIU/mL.")
    st.stop()

# ── Métricas ──────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("Total Confirmados", confirmed_df.shape[0])
c2.metric("TSH Promedio (2ª muestra)",
          f"{confirmed_df['resultado_muestra_2'].mean():.1f} mIU/L")
c3.metric("Instituciones afectadas",
          confirmed_df["institucion"].nunique() if "institucion" in confirmed_df.columns else "—")

st.markdown("---")

# ── SMS Individual ────────────────────────────────────────────────────────────
st.subheader("📱 Envío Individual")

col_sel, col_det = st.columns([1, 2])
with col_sel:
    opciones = confirmed_df.index.tolist()
    def fmt(x):
        r = confirmed_df.loc[x]
        return f"ID {r.get('id','?')} — {r.get('apellido_1','')} {r.get('apellido_2','')} — Ficha {r.get('ficha_id','')}"
    selected = st.selectbox("Seleccionar caso:", opciones, format_func=fmt)

fila = confirmed_df.loc[selected]
with col_det:
    d1, d2 = st.columns(2)
    with d1:
        st.write(f"**ID:** {fila.get('id','—')}")
        st.write(f"**TSH 1ª:** {fila.get('tsh_neonatal','—')} mIU/L")
        st.write(f"**TSH 2ª:** {fila.get('resultado_muestra_2','—')} mIU/L")
    with d2:
        st.write(f"**Ciudad:** {fila.get('ciudad','—')}")
        st.write(f"**ARS:** {fila.get('ars','—')}")
        st.write(f"**Institución:** {fila.get('institucion','—')}")

tel_pac_def = fila.get("telefono_1","") or fila.get("telefono_2","")
ars_fila    = fila.get("ars","su EPS")
tsh2_fila   = fila.get("resultado_muestra_2","—")

tel_ind     = st.text_input("Teléfono paciente/acudiente:", value=tel_pac_def,
                             placeholder="+573XXXXXXXXX", key="tel_ind")
tel_irs_ind = st.text_input("Teléfono IRS:", placeholder="+573XXXXXXXXX", key="tel_irs_ind")

msg_ind = st.text_area("Mensaje al paciente:",
    value=(f"Alerta: El tamizaje neonatal de "
           f"{fila.get('nombre_hijo','')} {fila.get('apellido_1','')} "
           f"es POSITIVO (TSH: {tsh2_fila} mIU/L). "
           f"Contacte a {ars_fila} para iniciar tratamiento urgente."),
    height=90, key="msg_ind")

msg_irs_ind = st.text_area("Mensaje a la IRS:",
    value=(f"Caso confirmado — ID {fila.get('id','—')}, "
           f"Ficha {fila.get('ficha_id','—')}, "
           f"Municipio {fila.get('nombre_municipio', fila.get('ciudad','—'))}, "
           f"TSH: {tsh2_fila} mIU/L. ARS: {ars_fila}. Requiere seguimiento urgente."),
    height=90, key="msg_irs_ind")

test_ind = st.checkbox("🧪 Modo prueba", value=True, key="test_ind")

btn1, btn2 = st.columns(2)
with btn1:
    if st.button("📤 Enviar SMS al Paciente", key="btn_pac"):
        if tel_ind:
            ok, status = enviar_sms(tel_ind, msg_ind, test_ind)
            (st.success if ok else st.error)(status)
            st.session_state.setdefault("sms_log", []).append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "id_caso": fila.get("id","—"), "destino": "Paciente",
                "telefono": tel_ind, "status": status,
            })
        else:
            st.warning("Ingresa un teléfono.")

with btn2:
    if st.button("🏥 Enviar SMS a la IRS", key="btn_irs"):
        if tel_irs_ind:
            ok, status = enviar_sms(tel_irs_ind, msg_irs_ind, test_ind)
            (st.success if ok else st.error)(status)
            st.session_state.setdefault("sms_log", []).append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "id_caso": fila.get("id","—"), "destino": "IRS",
                "telefono": tel_irs_ind, "status": status,
            })
        else:
            st.warning("Ingresa el teléfono de la IRS.")

st.markdown("---")

# ── SMS Masivo ────────────────────────────────────────────────────────────────
st.subheader("📡 Envío Masivo a Todos los Confirmados")

phone_col = next((c for c in ["telefono_1","telefono_2"] if c in confirmed_df.columns), None)
if not phone_col:
    st.warning("No se encontraron columnas de teléfono.")
else:
    n_con_tel = (confirmed_df[phone_col].str.strip().replace("0","") != "").sum()
    st.info(f"{n_con_tel} de {len(confirmed_df)} casos tienen teléfono disponible.")

    tmpl_pac = st.text_area(
        "Plantilla mensaje paciente — usa {tsh} y {ars}:",
        value="Alerta: El TSH neonatal de su hijo(a) es {tsh} mIU/L. Contacte a {ars} urgente.",
        height=75, key="tmpl_pac")
    tel_irs_mass = st.text_input("Teléfono IRS (único para todos):", key="irs_mass")
    tmpl_irs = st.text_area(
        "Plantilla mensaje IRS:",
        value="Caso confirmado: TSH {tsh} mIU/L — ARS {ars}. Requiere seguimiento.",
        height=75, key="tmpl_irs_msg")
    test_mass = st.checkbox("🧪 Modo prueba masivo", value=True, key="test_mass")

    if st.button("🚀 Enviar a Todos los Casos Confirmados", key="btn_mass"):
        log_mass = []
        bar  = st.progress(0)
        info = st.empty()
        sent, failed = 0, 0
        rows_list = list(confirmed_df.iterrows())

        for i, (_, row) in enumerate(rows_list):
            bar.progress((i + 1) / len(rows_list))
            info.text(f"Procesando {i+1}/{len(rows_list)}…")

            tel   = str(row.get(phone_col, "")).strip()
            tsh_v = str(row.get("resultado_muestra_2", ""))
            ars_v = str(row.get("ars", "su EPS"))

            if tel and tel not in ("nan", "0", ""):
                msg_p = tmpl_pac.replace("{tsh}", tsh_v).replace("{ars}", ars_v)
                ok, s = enviar_sms(tel, msg_p, test_mass)
                log_mass.append({"id": row.get("id","—"), "destino":"Paciente",
                                  "telefono": tel, "status": s})
                sent   += 1 if ok else 0
                failed += 0 if ok else 1

            if tel_irs_mass:
                msg_i = tmpl_irs.replace("{tsh}", tsh_v).replace("{ars}", ars_v)
                ok, s = enviar_sms(tel_irs_mass, msg_i, test_mass)
                log_mass.append({"id": row.get("id","—"), "destino":"IRS",
                                  "telefono": tel_irs_mass, "status": s})

        bar.progress(1.0)
        info.empty()
        st.success(f"✅ Completado: {sent} enviados, {failed} fallidos.")
        st.session_state.setdefault("sms_log", []).extend(log_mass)

st.markdown("---")

# ── Tabla + descarga ──────────────────────────────────────────────────────────
st.subheader("📋 Detalle de Casos Confirmados")
cols_show = [c for c in ["id","ficha_id","apellido_1","apellido_2","ciudad",
                          "departamento","sexo","fecha_nacimiento","peso",
                          "tsh_neonatal","resultado_muestra_2","ars","institucion"]
             if c in confirmed_df.columns]
st.dataframe(confirmed_df[cols_show], use_container_width=True, height=350)
st.download_button("⬇ Descargar CSV",
                   confirmed_df[cols_show].to_csv(index=False).encode(),
                   "casos_confirmados.csv", "text/csv")

# Gráfico distribución TSH confirmados
fig = px.histogram(confirmed_df, x="resultado_muestra_2", nbins=20,
                   title="Distribución TSH 2ª Muestra (Confirmados)",
                   labels={"resultado_muestra_2":"TSH 2ª (mIU/L)"},
                   color_discrete_sequence=["#FF4500"])
st.plotly_chart(fig, use_container_width=True)

# ── Log SMS ───────────────────────────────────────────────────────────────────
if st.session_state.get("sms_log"):
    st.markdown("---")
    with st.expander("📋 Historial de SMS"):
        log_df = pd.DataFrame(st.session_state["sms_log"])
        st.dataframe(log_df, use_container_width=True)
        st.download_button("⬇ Exportar log",
                           log_df.to_csv(index=False).encode(),
                           "sms_log.csv", "text/csv")

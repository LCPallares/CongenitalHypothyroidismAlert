# pages/1_📝_Formulario.py
import streamlit as st
import pandas as pd
from datetime import date, datetime

from utils.constantes import (
    CSS, TSH_CORTE,
    TIPOS_DOC, TIPOS_MUESTRA, TIPOS_VINC, DESTINOS, SEXOS,
    cargar_municipios, get_departamentos, get_municipios,
)
from utils.validaciones import val_tsh, val_peso
from utils.csv_helpers import (
    next_id, guardar_registro, actualizar_registro, buscar_por_ficha,
)
from utils.sms import enviar_sms

st.set_page_config(page_title="Formulario", page_icon="📝", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

st.title("📝 Ingreso de Datos")

# ── Cargar municipios una sola vez ────────────────────────────────────────────
@st.cache_data
def _municipios():
    return cargar_municipios()

df_mun = _municipios()
deptos = get_departamentos(df_mun)  # [{cod, nombre}, ...]

if df_mun.empty:
    st.warning("⚠️ No se encontró `municipios.csv`. Verifica que esté en la raíz del proyecto.")

modo = st.radio(
    "modo",
    ["📋  Registrar nueva tarjeta", "🔬  Cargar resultados de laboratorio"],
    horizontal=True,
    label_visibility="collapsed",
)
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# MODO A — NUEVA TARJETA
# ══════════════════════════════════════════════════════════════════════════════
if modo == "📋  Registrar nueva tarjeta":

    st.markdown("## 📋 Nueva Tarjeta de Tamizaje")
    st.caption("Ingrese los datos de la tarjeta física enviada por la IRS. ★ = obligatorio.")

    st.markdown('<div class="form-section">🏥  Institución / Acudiente</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        ficha        = st.text_input("★ No. de Ficha", placeholder="369980", key="n_ficha")
        fecha_ingreso= st.date_input("★ Fecha de Ingreso", value=None,
                                     min_value=date(2000, 1, 1), max_value=date.today(), key="n_fi")
        institucion  = st.text_input("★ Institución", placeholder="VICTORIA", key="n_inst")
    with c2:
        ars          = st.text_input("★ ARS / EPS", placeholder="MEDIMAS", key="n_ars")
        historia     = st.text_input("Historia Clínica", key="n_hist")
        tipo_doc     = st.selectbox("★ Tipo de Documento", TIPOS_DOC, key="n_tdoc")
    with c3:
        num_doc      = st.text_input("★ Número de Documento", key="n_ndoc")

        # ── Departamento (cascada) ──────────────────────────────────────────
        depto_nombres = ["Seleccionar..."] + [d["nombre"] for d in deptos]
        depto_sel_nombre = st.selectbox("★ Departamento", depto_nombres, key="n_depto")

        # Resolver código del departamento seleccionado
        cod_depto_sel = ""
        if depto_sel_nombre != "Seleccionar...":
            match = [d for d in deptos if d["nombre"] == depto_sel_nombre]
            cod_depto_sel = match[0]["cod"] if match else ""

        # ── Municipio (filtrado por departamento) ───────────────────────────
        municipios_depto = get_municipios(df_mun, cod_depto_sel)
        mun_nombres = ["Seleccionar..."] + [m["nombre"] for m in municipios_depto]
        mun_sel_nombre = st.selectbox(
            "★ Municipio",
            mun_nombres,
            key="n_municipio",
            disabled=(not cod_depto_sel),
            help="Primero selecciona un departamento" if not cod_depto_sel else "",
        )

        # Resolver código del municipio seleccionado
        cod_municipio_sel = ""
        if mun_sel_nombre != "Seleccionar...":
            match = [m for m in municipios_depto if m["nombre"] == mun_sel_nombre]
            cod_municipio_sel = match[0]["cod"] if match else ""

    c4, c5 = st.columns(2)
    with c4:
        tel1      = st.text_input("Teléfono 1", placeholder="3130000000", key="n_tel1")
        tipo_vinc = st.selectbox("★ Tipo de Vinculación", TIPOS_VINC, key="n_vinc")
    with c5:
        tel2      = st.text_input("Teléfono 2 (opcional)", key="n_tel2")
        direccion = st.text_input("Dirección", key="n_dir")

    st.markdown('<div class="form-section">👶  Datos del Recién Nacido</div>', unsafe_allow_html=True)
    c6, c7, c8 = st.columns(3)
    with c6:
        apellido1 = st.text_input("★ Primer Apellido", key="n_ap1")
        apellido2 = st.text_input("Segundo Apellido", key="n_ap2")
    with c7:
        nombre    = st.text_input("★ Nombre / Hijo(a) de", key="n_nom")
        fecha_nac = st.date_input("★ Fecha de Nacimiento", value=None,
                                  min_value=date(2000, 1, 1), max_value=date.today(), key="n_fnac")
    with c8:
        peso = st.text_input("★ Peso al nacer (g)", placeholder="2890", key="n_peso")
        sexo = st.selectbox("★ Sexo", SEXOS, key="n_sexo")

    c9, c10 = st.columns(2)
    with c9:
        prematuro    = st.checkbox("Prematuro", key="n_prem")
        transfundido = st.checkbox("Transfundido", key="n_trans")
    with c10:
        info_completa = st.checkbox("Información completa", key="n_info")
        muestra_adec  = st.checkbox("Muestra adecuada", key="n_madec")

    st.markdown('<div class="form-section">🔬  Datos de la Muestra</div>', unsafe_allow_html=True)
    st.caption("Solo se registra la toma. Los resultados se cargan después.")
    c11, c12 = st.columns(2)
    with c11:
        tipo_muestra1 = st.selectbox("★ Tipo de Muestra", TIPOS_MUESTRA, key="n_tm1")
        destino       = st.selectbox("★ Destino muestra", DESTINOS, key="n_dest")
    with c12:
        fecha_muestra1 = st.date_input("★ Fecha toma muestra", value=None,
                                       min_value=date(2000, 1, 1), max_value=date.today(), key="n_fm1")

    with st.expander("❌  Muestra rechazada (si aplica)"):
        m_rechazada  = st.checkbox("¿Hubo muestra rechazada?", key="n_mrech")
        fecha_rechaz = st.date_input("Fecha toma rechazada", value=None,
                                     min_value=date(2000, 1, 1), max_value=date.today(), key="n_frech")

    st.markdown("---")
    if st.button("💾  Guardar Tarjeta", type="primary", key="btn_guardar_nueva"):
        errors = []

        for val, label in [
            (ficha, "No. de Ficha"), (institucion, "Institución"), (ars, "ARS"),
            (num_doc, "Número Documento"), (ciudad, "Ciudad"),
            (apellido1, "Primer Apellido"), (nombre, "Nombre"),
        ]:
            if not val.strip():
                errors.append(f"**{label}** es obligatorio")

        for val, label in [
            (tipo_doc, "Tipo de Documento"),
            (sexo, "Sexo"), (tipo_vinc, "Tipo de Vinculación"),
            (tipo_muestra1, "Tipo de Muestra"), (destino, "Destino muestra"),
        ]:
            if not val or val == "Seleccionar...":
                errors.append(f"**{label}** es obligatorio")

        if depto_sel_nombre == "Seleccionar...":
            errors.append("**Departamento** es obligatorio")
        if mun_sel_nombre == "Seleccionar...":
            errors.append("**Municipio** es obligatorio")

        if fecha_ingreso is None:
            errors.append("**Fecha de Ingreso** es obligatoria")
        if fecha_nac is None:
            errors.append("**Fecha de Nacimiento** es obligatoria")
        if fecha_ingreso and fecha_nac:
            if fecha_nac > fecha_ingreso:
                errors.append("Fecha de nacimiento no puede ser posterior a la fecha de ingreso")
            if (date.today() - fecha_nac).days > 365:
                errors.append("Fecha de nacimiento inusual (más de 1 año atrás)")
        if fecha_muestra1 is None:
            errors.append("**Fecha toma muestra** es obligatoria")

        v_peso, e = val_peso(peso)
        if e: errors.append(e)

        if ficha.strip() and buscar_por_ficha(ficha) is not None:
            errors.append(f"Ya existe un registro con la ficha **{ficha}**. "
                          "Usa el modo 'Cargar resultados' para actualizarlo.")

        if errors:
            st.error(f"**{len(errors)} error(es):**")
            for e in errors:
                st.markdown(f"- {e}")
        else:
            from utils.constantes import FIELDNAMES
            row = {f: "" for f in FIELDNAMES}
            row.update({
                "id":                    next_id(),
                "ficha_id":              ficha.strip(),
                "fecha_ingreso":         fecha_ingreso.isoformat(),
                "institucion":           institucion.strip(),
                "ars":                   ars.strip(),
                "historia_clinica":      historia.strip(),
                "tipo_documento":        tipo_doc,
                "numero_documento":      num_doc.strip(),
                "cod_municipio":          cod_municipio_sel,
                "nombre_municipio":       mun_sel_nombre,
                "cod_departamento":       cod_depto_sel,
                "nombre_departamento":    depto_sel_nombre,
                "telefono_1":            tel1.strip() or "0",
                "telefono_2":            tel2.strip() or "0",
                "direccion":             direccion.strip(),
                "apellido_1":            apellido1.strip(),
                "apellido_2":            apellido2.strip(),
                "nombre_hijo":           nombre.strip(),
                "fecha_nacimiento":      fecha_nac.isoformat(),
                "peso":                  v_peso,
                "sexo":                  sexo,
                "prematuro":             "VERDADERO" if prematuro else "FALSO",
                "transfundido":          "VERDADERO" if transfundido else "FALSO",
                "informacion_completa":  "VERDADERO" if info_completa else "FALSO",
                "muestra_adecuada":      "VERDADERO" if muestra_adec else "FALSO",
                "destino_muestra":       destino,
                "tipo_muestra":          tipo_muestra1,
                "fecha_toma_muestra":    fecha_muestra1.isoformat(),
                "muestra_rechazada":     "VERDADERO" if m_rechazada else "FALSO",
                "fecha_toma_rechazada":  fecha_rechaz.isoformat() if fecha_rechaz else "",
                "tipo_vinculacion":      tipo_vinc,
                "contador":              "0",
            })
            guardar_registro(row)
            st.success(f"✅ Tarjeta **#{row['id']}** — Ficha **{ficha}** guardada correctamente.")

# ══════════════════════════════════════════════════════════════════════════════
# MODO B — CARGAR RESULTADOS
# ══════════════════════════════════════════════════════════════════════════════
else:
    st.markdown("## 🔬 Carga de Resultados de Laboratorio")
    st.caption("Busca el registro por No. de Ficha y agrega los resultados de TSH.")

    col_busq, col_btn = st.columns([3, 1])
    with col_busq:
        ficha_buscar = st.text_input("No. de Ficha:", placeholder="369980", key="busq_ficha")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        buscar = st.button("🔍  Buscar", key="btn_buscar", use_container_width=True)

    reg = None
    if buscar:
        reg = buscar_por_ficha(ficha_buscar)
        st.session_state["reg_encontrado"] = reg.to_dict() if reg is not None else None
    elif st.session_state.get("reg_encontrado"):
        reg = pd.Series(st.session_state["reg_encontrado"])

    if buscar and reg is None:
        st.error(f"No se encontró ningún registro con la ficha **{ficha_buscar}**.")

    if reg is not None:
        # ── Tarjeta resumen ───────────────────────────────────────────────────
        st.markdown('<div class="form-section">👤  Paciente encontrado</div>', unsafe_allow_html=True)
        ci1, ci2, ci3, ci4 = st.columns(4)
        ci1.metric("Ficha",           reg.get("ficha_id", "—"))
        ci2.metric("Paciente",        f"{reg.get('apellido_1','')} {reg.get('apellido_2','')}")
        ci3.metric("Fecha nacimiento", reg.get("fecha_nacimiento", "—"))
        ci4.metric("Institución",     reg.get("institucion", "—"))

        ci5, ci6, ci7, ci8 = st.columns(4)
        ci5.metric("Municipio",   reg.get("nombre_municipio", reg.get("ciudad", "—")))
        ci6.metric("Departamento",reg.get("nombre_departamento", reg.get("departamento", "—")))
        ci7.metric("ARS",         reg.get("ars", "—"))
        ci8.metric("Tipo muestra",reg.get("tipo_muestra", "—"))

        ci9, ci10 = st.columns(2)
        ci9.metric("Fecha toma",  reg.get("fecha_toma_muestra", "—"))

        tsh1_actual  = reg.get("tsh_neonatal", "").strip()
        tsh2_actual  = reg.get("resultado_muestra_2", "").strip()
        ya_tiene_tsh1 = tsh1_actual not in ("", "0")
        ya_tiene_tsh2 = tsh2_actual not in ("", "0")

        if ya_tiene_tsh1:
            st.info(f"ℹ️ Este registro ya tiene TSH1 = **{tsh1_actual} µIU/mL**"
                    + (f" y TSH2 = **{tsh2_actual} µIU/mL**" if ya_tiene_tsh2 else "")
                    + ". Puedes corregir los valores abajo.")
        st.markdown("---")

        # ── Resultado muestra 1 ───────────────────────────────────────────────
        st.markdown('<div class="form-section">🔬  Resultado — Muestra 1</div>', unsafe_allow_html=True)
        r1, r2, r3 = st.columns(3)
        with r1:
            fecha_result1 = st.date_input(
                "★ Fecha de resultado",
                value=pd.to_datetime(reg.get("fecha_resultado") or None, errors="coerce"),
                min_value=date(2000, 1, 1), max_value=date.today(), key="r_fres1",
            )
        with r2:
            tsh1_str = st.text_input(
                "★ Resultado TSH 1 (µIU/mL)",
                value=tsh1_actual if ya_tiene_tsh1 else "",
                placeholder="7.2", key="r_tsh1",
            )
        with r3:
            st.markdown("<br>", unsafe_allow_html=True)
            if tsh1_str.strip():
                try:
                    v_p = float(tsh1_str.replace(",", "."))
                    if v_p >= TSH_CORTE:
                        st.warning(f"⚠️ TSH1 = {v_p} — requiere 2ª muestra")
                    else:
                        st.success(f"✅ TSH1 = {v_p} — rango normal")
                except ValueError:
                    pass

        tsh1_num = None
        if tsh1_str.strip():
            try:
                tsh1_num = float(tsh1_str.replace(",", "."))
            except ValueError:
                pass

        necesita_m2 = tsh1_num is not None and tsh1_num >= TSH_CORTE

        # ── Resultado muestra 2 ───────────────────────────────────────────────
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
                ficha2  = st.text_input("No. Ficha 2", value=reg.get("ficha_id_2", ""), key="r_f2")
                tipo_m2 = st.selectbox("★ Tipo muestra 2", TIPOS_MUESTRA, key="r_tm2")
            with m2b:
                fecha_m2 = st.date_input(
                    "★ Fecha toma muestra 2",
                    value=pd.to_datetime(reg.get("fecha_toma_muestra_2") or None, errors="coerce"),
                    min_value=date(2000, 1, 1), max_value=date.today(), key="r_fm2",
                )
                f_res2 = st.date_input(
                    "★ Fecha resultado 2",
                    value=pd.to_datetime(reg.get("fecha_resultado_muestra_2") or None, errors="coerce"),
                    min_value=date(2000, 1, 1), max_value=date.today(), key="r_fr2",
                )
            with m2c:
                tsh2_str = st.text_input(
                    "★ Resultado TSH 2 (µIU/mL)",
                    value=tsh2_actual if ya_tiene_tsh2 else "",
                    placeholder="18.5", key="r_tsh2",
                )

            if tsh2_str.strip():
                try:
                    tsh2_preview = float(tsh2_str.replace(",", "."))
                    if tsh2_preview >= TSH_CORTE:
                        st.error(f"🚨 TSH2 = {tsh2_preview} µIU/mL — **HIPOTIROIDISMO CONFIRMADO**.")
                    else:
                        st.success(f"✅ TSH2 = {tsh2_preview} µIU/mL — Segunda muestra normal.")
                except ValueError:
                    pass

        # Evaluar si es confirmado
        v_tsh2_final = None
        if tsh2_str.strip():
            try:
                v_tsh2_final = float(tsh2_str.replace(",", "."))
            except ValueError:
                pass
        confirmado = necesita_m2 and v_tsh2_final is not None and v_tsh2_final >= TSH_CORTE

        # ── SMS ───────────────────────────────────────────────────────────────
        if confirmado:
            st.markdown('<div class="form-section">📱  Notificación SMS</div>', unsafe_allow_html=True)
            tel_reg    = reg.get("telefono_1", "") or reg.get("telefono_2", "")
            ars_reg    = reg.get("ars", "su EPS")
            nombre_reg = reg.get("nombre_hijo", "")

            sms_col1, sms_col2 = st.columns(2)
            with sms_col1:
                notif_pac = st.checkbox("Notificar al paciente/acudiente", key="r_notif_pac")
                if notif_pac:
                    st.text_input("Teléfono paciente", value=tel_reg, key="r_tel_pac")
                    st.text_area("Mensaje paciente",
                        value=f"Alerta: El resultado del tamizaje de {nombre_reg} es POSITIVO "
                              f"(TSH: {tsh2_str} µIU/mL). Contacte a {ars_reg} urgente.",
                        height=90, key="r_msg_pac")
            with sms_col2:
                notif_irs = st.checkbox("Notificar a la IRS", key="r_notif_irs")
                if notif_irs:
                    st.text_input("Teléfono IRS", key="r_tel_irs")
                    st.text_area("Mensaje IRS",
                        value=f"Caso confirmado — Ficha {reg.get('ficha_id','')}: "
                              f"{reg.get('apellido_1','')} {reg.get('apellido_2','')}, "
                              f"Municipio: {reg.get('nombre_municipio', reg.get('ciudad',''))}, "
                              f"TSH: {tsh2_str} µIU/mL. "
                              f"ARS: {ars_reg}. Requiere seguimiento urgente.",
                        height=90, key="r_msg_irs")
            st.checkbox("🧪 Modo de prueba (no envía realmente)", value=True, key="r_sms_test")

        # ── Guardar ───────────────────────────────────────────────────────────
        st.markdown("---")
        if st.button("💾  Guardar Resultados", type="primary", key="btn_guardar_res"):
            errors = []

            if fecha_result1 is None:
                errors.append("Fecha resultado 1 es obligatoria")
            v_tsh1, e = val_tsh(tsh1_str, "TSH 1")
            if e: errors.append(e)

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
                campos = {
                    "fecha_resultado": fecha_result1.isoformat() if fecha_result1 else "",
                    "tsh_neonatal":    v_tsh1,
                }
                if necesita_m2 and v_tsh2 is not None:
                    campos.update({
                        "ficha_id_2":                ficha2.strip() or "0",
                        "tipo_muestra_2":             tipo_m2,
                        "fecha_toma_muestra_2":       fecha_m2.isoformat() if fecha_m2 else "",
                        "fecha_resultado_muestra_2":  f_res2.isoformat() if f_res2 else "",
                        "resultado_muestra_2":         v_tsh2,
                        "contador":                   "1",
                    })

                actualizar_registro(int(reg["id"]), campos)
                st.session_state["reg_encontrado"] = None

                if confirmado:
                    st.error(f"🚨 **CASO POSITIVO CONFIRMADO** — Ficha {reg.get('ficha_id')}")
                else:
                    st.success(f"✅ Resultados guardados — Ficha **{reg.get('ficha_id')}**."
                               + (" Caso cerrado como normal." if not necesita_m2 else ""))

                # Envío SMS
                sms_log = st.session_state.setdefault("sms_log", [])
                if confirmado:
                    for dest_key, tel_key, msg_key, label in [
                        ("r_notif_pac", "r_tel_pac", "r_msg_pac", "Paciente"),
                        ("r_notif_irs", "r_tel_irs", "r_msg_irs", "IRS"),
                    ]:
                        if st.session_state.get(dest_key) and st.session_state.get(tel_key):
                            ok, status = enviar_sms(
                                st.session_state[tel_key],
                                st.session_state.get(msg_key, ""),
                                st.session_state.get("r_sms_test", True),
                            )
                            sms_log.append({
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "id_caso": reg["id"], "destino": label,
                                "telefono": st.session_state[tel_key], "status": status,
                            })
                            (st.success if ok else st.error)(f"{'📱' if label=='Paciente' else '🏥'} {label}: {status}")

# ── Historial SMS ─────────────────────────────────────────────────────────────
if st.session_state.get("sms_log"):
    with st.expander("📋  Historial de SMS enviados en esta sesión"):
        st.dataframe(pd.DataFrame(st.session_state["sms_log"]), use_container_width=True)

# utils/sms.py
# ─── Envío de SMS vía Twilio ──────────────────────────────────────────────────

import streamlit as st


def enviar_sms(telefono: str, mensaje: str, test_mode: bool = True) -> tuple[bool, str]:
    """
    Envía un SMS vía Twilio.
    - test_mode=True  → simula el envío sin llamar a la API
    - Credenciales en st.secrets["twilio"]

    Retorna (éxito: bool, estado: str)
    """
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

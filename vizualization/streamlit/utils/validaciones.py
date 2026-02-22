# utils/validaciones.py
# ─── Funciones de validación reutilizables ────────────────────────────────────

from datetime import datetime
from utils.constantes import TSH_MIN, TSH_MAX, PESO_MIN, PESO_MAX


def val_tsh(text, campo="TSH"):
    """Valida un valor de TSH. Retorna (float|None, error|None)."""
    if not str(text).strip():
        return None, f"{campo} es obligatorio"
    try:
        v = float(str(text).replace(",", "."))
    except ValueError:
        return None, f"{campo} debe ser un número"
    if v < TSH_MIN:
        return None, f"{campo} demasiado bajo (mín {TSH_MIN})"
    if v > TSH_MAX:
        return None, f"{campo} imposible (máx {TSH_MAX} µIU/mL)"
    return v, None


def val_peso(text):
    """Valida el peso en gramos. Retorna (float|None, error|None)."""
    if not str(text).strip():
        return None, "Peso es obligatorio"
    try:
        v = float(str(text).replace(",", "."))
    except ValueError:
        return None, "Peso debe ser un número"
    if v < PESO_MIN:
        return None, f"Peso muy bajo (mín {PESO_MIN} g)"
    if v > PESO_MAX:
        return None, f"Peso imposible (máx {PESO_MAX} g)"
    return v, None

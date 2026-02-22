# utils/csv_helpers.py
# ─── Operaciones CRUD sobre el CSV de registros ───────────────────────────────

import csv
import os

import pandas as pd

from utils.constantes import CSV_REGISTROS, FIELDNAMES


def leer_registros() -> pd.DataFrame:
    """Lee el CSV de registros. Retorna DataFrame vacío si no existe."""
    if not os.path.isfile(CSV_REGISTROS):
        return pd.DataFrame(columns=FIELDNAMES)
    return pd.read_csv(CSV_REGISTROS, dtype=str).fillna("")


def next_id() -> int:
    """Retorna el siguiente ID autoincremental."""
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
    """Agrega una fila nueva al CSV."""
    existe = os.path.isfile(CSV_REGISTROS)
    with open(CSV_REGISTROS, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not existe:
            w.writeheader()
        w.writerow(row)


def actualizar_registro(id_registro: int, campos: dict):
    """Actualiza campos específicos en la fila con el id dado."""
    df = leer_registros()
    mask = df["id"].astype(str) == str(id_registro)
    for col, val in campos.items():
        if col in df.columns:
            df.loc[mask, col] = str(val)
    df.to_csv(CSV_REGISTROS, index=False)


def buscar_por_ficha(ficha: str) -> pd.Series | None:
    """Retorna la fila cuyo ficha_id coincide, o None si no existe."""
    df = leer_registros()
    if df.empty:
        return None
    match = df[df["ficha_id"].str.strip() == ficha.strip()]
    if match.empty:
        return None
    return match.iloc[0]

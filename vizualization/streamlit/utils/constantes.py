# utils/constantes.py
# ─── Todas las constantes compartidas entre páginas ───────────────────────────

CSV_REGISTROS = "../../data/hipotiroidismo_registros.csv"

TSH_MIN   = 0.1
TSH_MAX   = 300.0
TSH_CORTE = 15.0
PESO_MIN  = 400
PESO_MAX  = 8000

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

TIPOS_DOC    = ["Seleccionar...", "CC", "CE", "PA", "RC", "TI"]
TIPOS_MUESTRA= ["Seleccionar...", "CORDON", "TALON", "VENA"]
TIPOS_VINC   = ["Seleccionar...", "CONTRIBUTIVO", "SUBSIDIADO",
                "VINCULADO", "PARTICULAR", "ESPECIAL"]
DESTINOS     = ["Seleccionar...", "ACEPTADA", "RECHAZADA"]
SEXOS        = ["Seleccionar...", "MASCULINO", "FEMENINO", "INDETERMINADO"]

# CSS compartido — se inyecta en cada página con inject_css()
CSS = """
<style>
[data-testid="metric-container"] {
    background: #0e1525;
    border: 1px solid #1e3050;
    border-radius: 10px;
    padding: 12px 16px;
}
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
.tsh-alert {
    background: #2d1f00;
    border: 1px solid #f39c12;
    border-radius: 8px;
    padding: 10px 16px;
    color: #f39c12;
    font-weight: 600;
    margin: 8px 0;
}
.success-box {
    background: #0d2a1a;
    border: 1px solid #27ae60;
    border-radius: 8px;
    padding: 10px 16px;
    color: #2ecc71;
    font-weight: 600;
}
</style>
"""

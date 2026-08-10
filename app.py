import datetime
import requests
import pandas as pd
import streamlit as st

# ==========================================
# CONFIGURACIÓN Y CONEXIÓN A GOOGLE SHEETS
# ==========================================
# URL de Apps Script de tu Hoja de Google "Historial DT1"
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzqanAiYz52enC0jrrB2sJldaYC-6JQ6QKN9pticGCu2s4NrBGDcAY1EReGzl6QaaTDbg/exec"

SPREADSHEET_ID = "18oxEW7CENFkAMWUgIJKlfeadtqhztfkf8JV7vQ1JoqU"

def guardar_registro_google_sheets(fecha, comida, glicemia, carbohidratos, dosis):
    """Envía los datos registrados directamente a la hoja de Google Sheets."""
    datos = {
        "fecha": str(fecha),
        "comida": comida,
        "glicemia": int(glicemia),
        "carbohidratos": float(carbohidratos),
        "dosis": float(dosis),
    }

    try:
        response = requests.post(WEBHOOK_URL, json=datos, timeout=8)
        if response.status_code == 200:
            return True
        else:
            st.error(f"Error al guardar en la hoja (Código HTTP {response.status_code})")
            return False
    except Exception as e:
        st.error(f"No se pudo conectar con Google Sheets: {e}")
        return False


# ==========================================
# INTERFAZ DE LA APLICACIÓN (STREAMLIT)
# ==========================================
st.set_page_config(
    page_title="Control DT1 - Calculadora de Insulina",
    page_icon="🩸",
    layout="centered",
)

st.title("🩸 Control de Diabetes Tipo 1")
st.subheader("Calculadora de Dosis de Insulina y Registro")

# Inicializar sesión para historial local en la pantalla
if "historial" not in st.session_state:
    st.session_state.historial = []

# --- PARÁMETROS DEL USUARIO ---
with st.sidebar:
    st.header("⚙️ Configuración Personal")
    target_glicemia = st.number_input(
        "Glicemia Objetivo (mg/dL)", value=100, step=5
    )
    ratio_ch = st.number_input(
        "Ratio de Carbohidratos (g / Unidad)",
        value=10.0,
        step=0.5,
        help="Gramos de carbohidratos cubiertos por 1 Unidad de insulina",
    )
    factor_sensibilidad = st.number_input(
        "Factor de Sensibilidad (ISF)",
        value=50.0,
        step=5.0,
        help="Cuánto reduce 1 Unidad de insulina tu glicemia en mg/dL",
    )

st.divider()

# --- FORMULARIO DE ENTRADA ---
st.header("📝 Nuevo Registro")

col1, col2 = st.columns(2)

with col1:
    fecha_hora = st.datetime_input("Fecha y Hora", datetime.datetime.now())
    comida_opciones = ["Desayuno", "Almuerzo", "Cena", "Colación", "Otro"]
    comida = st.selectbox("Tipo de Comida", comida_opciones)

with col2:
    glicemia = st.number_input(
        "Glicemia Actual (mg/dL)", min_value=20, max_value=600, value=120
    )
    carbohidratos = st.number_input(
        "Carbohidratos Totales (g)", min_value=0.0, max_value=300.0, value=30.0
    )

# --- CÁLCULO DE DOSIS ---
dosis_comida = carbohidratos / ratio_ch if ratio_ch > 0 else 0
correccion = (
    (glicemia - target_glicemia) / factor_sensibilidad
    if factor_sensibilidad > 0
    else 0
)

# Evitar correcciones negativas si la glicemia está por debajo del objetivo
if correccion < 0:
    correccion = 0

dosis_total = round(dosis_comida + correccion, 1)

st.markdown("---")
st.markdown(f"### 💉 Dosis Sugerida: **{dosis_total} Unidades**")
st.caption(
    f"• Insulina por Carbohidratos: {dosis_comida:.1f} U  |  • Corrección por Glicemia: {correccion:.1f} U"
)

# --- BOTÓN PARA GUARDAR ---
if st.button("💾 Calcular y Guardar en Google Sheets", type="primary", use_container_width=True):
    with st.spinner("Guardando en Google Sheets..."):
        exito = guardar_registro_google_sheets(
            fecha_hora.strftime("%Y-%m-%d %H:%M"),
            comida,
            glicemia,
            carbohidratos,
            dosis_total,
        )

    if exito:
        st.success("¡Registro guardado exitosamente en tu Google Sheet!")

        # Agregar al historial de la vista actual
        st.session_state.historial.append(
            {
                "Fecha": fecha_hora.strftime("%Y-%m-%d %H:%M"),
                "Comida": comida,
                "Glicemia": glicemia,
                "Carbohidratos (g)": carbohidratos,
                "Dosis (U)": dosis_total,
            }
        )

# --- HISTORIAL EN PANTALLA ---
if st.session_state.historial:
    st.divider()
    st.subheader("📊 Registros de la Sesión Actual")
    df = pd.DataFrame(st.session_state.historial)
    st.dataframe(df, use_container_width=True)

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

# Configuración de la página para dispositivos móviles
st.set_page_config(
    page_title="Mi Control DT1",
    page_icon="💉",
    layout="centered"
)

# Estructura de archivos locales para persistencia básica
DATA_FILE = "historial_dt1.csv"
CONFIG_FILE = "config_dt1.json"

# Configuración por defecto
DEFAULT_CONFIG = {
    "comidas": [
        {"nombre": "Desayuno", "inicio": 6, "fin": 11, "ratio": 10.0, "escalas": [{"min": 0, "max": 150, "dosis": 0.0}]},
        {"nombre": "Almuerzo", "inicio": 12, "fin": 17, "ratio": 15.0, "escalas": [{"min": 0, "max": 150, "dosis": 0.0}]},
        {"nombre": "Cena", "inicio": 19, "fin": 23, "ratio": 12.0, "escalas": [{"min": 0, "max": 140, "dosis": 0.0}]}
    ]
}

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG

def guardar_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)

def cargar_historial():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["Fecha", "Glicemia", "Carbohidratos", "Dosis_Total", "Detalle"])

def guardar_registro(glicemia, carbos, dosis, detalle):
    nuevo_registro = pd.DataFrame([{
        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Glicemia": glicemia,
        "Carbohidratos": carbos,
        "Dosis_Total": dosis,
        "Detalle": detalle
    }])
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df = pd.concat([nuevo_registro, df], ignore_index=True)
    else:
        df = nuevo_registro
    df.to_csv(DATA_FILE, index=False)

# Inicialización de estado
if "config" not in st.session_state:
    st.session_state.config = cargar_config()

# --- INTERFAZ ---
st.title("💉 Mi Control DT1")

pestana1, pestana2, pestana3 = st.tabs(["🧮 Calculadora", "📜 Historial", "⚙️ Configuración"])

# --- PESTAÑA 1: CALCULADORA ---
with pestana1:
    st.subheader("Cálculo de Dosis")
    
    hora_actual = datetime.now().hour
    comida_detectada = st.session_state.config["comidas"][0]
    for c in st.session_state.config["comidas"]:
        if c["inicio"] <= hora_actual <= c["fin"]:
            comida_detectada = c
            break

    st.info(f"Horario detectado: **{comida_detectada['nombre']}** (Ratio: 1U / {comida_detectada['ratio']}g CH)")

    col1, col2 = st.columns(2)
    with col1:
        glicemia = st.number_input("Glicemia (mg/dL)", min_value=0, max_value=600, value=120, step=1)
    with col2:
        carbos = st.number_input("Carbohidratos (g)", min_value=0, max_value=300, value=0, step=5)

    if st.button("Calcular Insulina", type="primary", use_container_width=True):
        # Corrección por escala
        corr = 0.0
        for e in comida_detectada["escalas"]:
            if e["min"] <= glicemia <= e["max"]:
                corr = e["dosis"]
                break
        
        # Bolus por comida
        bolus = carbos / comida_detectada["ratio"] if comida_detectada["ratio"] > 0 else 0
        total = round((corr + bolus) * 2) / 2  # Redondeo a medias unidades

        st.metric(label="Dosis Recomendada", value=f"{total} U")
        st.caption(f"Detalle: Corrección ({corr}U) + Comida ({round(bolus, 1)}U)")

        if st.button("Guardar en Historial", use_container_width=True):
            guardar_registro(glicemia, carbos, total, f"{comida_detectada['nombre']} - Corr: {corr}U, CH: {round(bolus, 1)}U")
            st.success("¡Registro guardado correctamente!")

# --- PESTAÑA 2: HISTORIAL ---
with pestana2:
    st.subheader("Historial de Mediciones")
    df_historial = cargar_historial()
    if not df_historial.empty:
        st.dataframe(df_historial, use_container_width=True)
    else:
        st.write("Aún no hay registros guardados.")

# --- PESTAÑA 3: CONFIGURACIÓN ---
with pestana3:
    st.subheader("Parámetros de Corrección y Ratios")
    
    for idx, c in enumerate(st.session_state.config["comidas"]):
        with st.expander(f"Configurar {c['nombre']}"):
            st.session_state.config["comidas"][idx]["ratio"] = st.number_input(
                f"Ratio para {c['nombre']} (g/U)", 
                min_value=1.0, 
                value=float(c["ratio"]), 
                key=f"ratio_{idx}"
            )
    
    if st.button("Guardar Cambios de Configuración"):
        guardar_config(st.session_state.config)
        st.success("Configuración guardada.")

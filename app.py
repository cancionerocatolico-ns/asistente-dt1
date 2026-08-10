import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import requests

# Configuración de la página
st.set_page_config(
    page_title="Mi Control DT1",
    page_icon="💉",
    layout="centered"
)

CONFIG_FILE = "config_dt1.json"
DATA_FILE = "historial_dt1.csv"

# --- BASE DE DATOS LOCAL RÁPIDA (Para alimentos sin empaque / caseros) ---
ALIMENTOS_CASEROS = [
    {"alimento": "Pan de molde", "porcion": "1 rebanada (25g)", "carbos": 12},
    {"alimento": "Pan Hallulla / Marraqueta", "porcion": "1/2 unidad (50g)", "carbos": 25},
    {"alimento": "Arroz cocido", "porcion": "1 taza (150g)", "carbos": 40},
    {"alimento": "Fideos cocidos", "porcion": "1 taza (150g)", "carbos": 42},
    {"alimento": "Papas cocidas", "porcion": "1 unidad mediana (150g)", "carbos": 26},
    {"alimento": "Manzana", "porcion": "1 unidad mediana (150g)", "carbos": 18},
    {"alimento": "Plátano", "porcion": "1 unidad mediana (120g)", "carbos": 23},
    {"alimento": "Avena", "porcion": "1/2 taza (40g)", "carbos": 24}
]

# Configuración por defecto con escalas/rangos fijos de glicemia
DEFAULT_CONFIG = {
    "comidas": [
        {
            "nombre": "Desayuno", "inicio": 6, "fin": 11, "ratio": 10.0,
            "escalas": [
                {"min": 0, "max": 130, "dosis": 0.0},
                {"min": 131, "max": 180, "dosis": 1.0},
                {"min": 181, "max": 230, "dosis": 2.0},
                {"min": 231, "max": 280, "dosis": 3.0},
                {"min": 281, "max": 999, "dosis": 4.0}
            ]
        },
        {
            "nombre": "Almuerzo", "inicio": 12, "fin": 17, "ratio": 15.0,
            "escalas": [
                {"min": 0, "max": 140, "dosis": 0.0},
                {"min": 141, "max": 190, "dosis": 1.0},
                {"min": 191, "max": 240, "dosis": 2.0},
                {"min": 241, "max": 999, "dosis": 3.0}
            ]
        },
        {
            "nombre": "Cena", "inicio": 18, "fin": 23, "ratio": 12.0,
            "escalas": [
                {"min": 0, "max": 130, "dosis": 0.0},
                {"min": 131, "max": 180, "dosis": 1.0},
                {"min": 181, "max": 230, "dosis": 2.0},
                {"min": 231, "max": 999, "dosis": 3.0}
            ]
        }
    ]
}

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def guardar_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)

# Consulta a Open Food Facts extrayendo información de porción
def buscar_open_food_facts(query):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=10"
    headers = {"User-Agent": "MiControlDT1App/1.0 (streamlit-app)"}
    
    for intento in range(2):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                datos = response.json()
                productos = []
                for p in datos.get("products", []):
                    nombre = p.get("product_name", "Producto sin nombre")
                    marca = p.get("brands", "")
                    
                    nutriments = p.get("nutriments", {})
                    carbos_100g = float(nutriments.get("carbohydrates_100g", 0.0) or 0.0)
                    carbos_porcion = nutriments.get("carbohydrates_serving")
                    carbos_porcion = float(carbos_porcion) if carbos_porcion is not None else None
                    
                    serving_size = p.get("serving_size", "No especificada")
                    
                    nombre_completo = f"{nombre} ({marca})" if marca else nombre
                    productos.append({
                        "nombre": nombre_completo,
                        "carbos_100g": carbos_100g,
                        "carbos_porcion": carbos_porcion,
                        "serving_size": serving_size
                    })
                return productos
        except requests.exceptions.Timeout:
            if intento == 1:
                st.warning("⏱️ El servidor tardó en responder. Intenta buscar de nuevo.")
        except Exception:
            st.error("⚠️ Error de conexión al consultar el servidor.")
            break
    return []

if "config" not in st.session_state:
    st.session_state.config = cargar_config()

if "plato" not in st.session_state:
    st.session_state.plato = []

st.title("💉 Mi Control DT1")

pestana1, pestana2, pestana3, pestana4 = st.tabs(["🧮 Calculadora", "🥗 Alimentos", "📜 Historial", "⚙️ Configuración"])

# --- PESTAÑA 1: CALCULADORA ---
with pestana1:
    st.subheader("Cálculo de Dosis")
    
    hora_actual = datetime.now().hour
    comida_sugerida_idx = 0
    for idx, c in enumerate(st.session_state.config["comidas"]):
        if c["inicio"] <= hora_actual <= c["fin"]:
            comida_sugerida_idx = idx
            break

    nombres_comidas = [c["nombre"] for c in st.session_state.config["comidas"]]
    comida_sel_nombre = st.selectbox("Comida actual:", nombres_comidas, index=comida_sugerida_idx)
    comida_actual = next(c for c in st.session_state.config["comidas"] if c["nombre"] == comida_sel_nombre)

    st.caption(f"Ratio activo: **1U por cada {comida_actual['ratio']}g CH**")

    carbos_desde_plato = sum([item["total_carbos"] for item in st.session_state.plato])

    col1, col2 = st.columns(2)
    with col1:
        glicemia = st.number_input("Glicemia actual (mg/dL)", min_value=20, max_value=600, value=120, step=1)
    with col2:
        carbos = st.number_input("Carbohidratos totales (g)", min_value=0, max_value=300, value=int(round(carbos_desde_plato)), step=1)

    if st.session_state.plato:
        st.info(f"🛒 Carbohidratos del plato activo: **{round(carbos_desde_plato, 1)}g**")

    paso_dosis = st.radio("Redondeo del lápiz (pasos de):", [0.5, 1.0], horizontal=True)

    if st.button("Calcular Dosis Total", type="primary", use_container_width=True):
        dosis_correccion = 0.0
        rango_encontrado = None
        for e in comida_actual["escalas"]:
            if e["min"] <= glicemia <= e["max"]:
                dosis_correccion = float(e["dosis"])
                rango_encontrado = f"{e['min']} - {e['max']} mg/dL"
                break

        dosis_comida = carbos / comida_actual["ratio"] if comida_actual["ratio"] > 0 else 0.0
        total_exacto = dosis_correccion + dosis_comida
        total_redondeado = round(total_exacto / paso_dosis) * paso_dosis

        st.markdown("---")
        st.metric(label="Dosis Sugerida", value=f"{total_redondeado:.1f} U")
        
        st.write("**Detalle del Cálculo:**")
        if rango_encontrado:
            st.write(f"- Corrección por glicemia (Rango `{rango_encontrado}`): **+{dosis_correccion} U**")
        else:
            st.write(f"- Corrección por glicemia: **+0.0 U** (Glicemia fuera de rangos)")

        st.write(f"- Bolus por comida ({carbos}g / {comida_actual['ratio']}): **+{dosis_comida:.2f} U**")
        st.write(f"- Dosis exacta sin redondear: `{total_exacto:.2f} U`")

# --- PESTAÑA 2: BUSCADOR DE ALIMENTOS Y PORCIONES ---
with pestana2:
    st.subheader("Buscador de Alimentos y Porciones")
    
    origen = st.radio("Fuente de datos:", ["Alimentos Caseros / Básicos", "Búsqueda En Línea (Marcas/Marcados)"], horizontal=True)
    
    if origen == "Alimentos Caseros / Básicos":
        df_caseros = pd.DataFrame(ALIMENTOS_CASEROS)
        sel = st.selectbox("Selecciona alimento:", df_caseros["alimento"].tolist())
        item = df_caseros[df_caseros["alimento"] == sel].iloc[0]
        
        st.caption(f"Porción estándar: **{item['porcion']}** = **{item['carbos']}g CH**")
        cant_porciones = st.number_input("Cantidad de porciones:", min_value=0.25, max_value=10.0, value=1.0, step=0.25)
        total_ch = round(item['carbos'] * cant_porciones, 1)
        
        if st.button("Añadir al Plato"):
            st.session_state.plato.append({
                "alimento": item["alimento"],
                "detalle": f"{cant_porciones} porción(es)",
                "total_carbos": total_ch
            })
            st.success(f"Añadido {item['alimento']} ({total_ch}g CH)")

    else:
        busqueda = st.text_input("Buscar alimento o marca:")
        if busqueda:
            resultados = buscar_open_food_facts(busqueda)
            if resultados:
                opciones = [r["nombre"] for r in resultados]
                prod_sel = st.selectbox("Resultados encontrados:", opciones)
                info_prod = next(r for r in resultados if r["nombre"] == prod_sel)
                
                st.markdown("---")
                st.write(f"**Porción declarada por fabricante:** `{info_prod['serving_size']}`")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("CH por 100g / 100ml", f"{info_prod['carbos_100g']}g")
                with col_b:
                    ch_porc_str = f"{info_prod['carbos_porcion']}g" if info_prod['carbos_porcion'] is not None else "No especificado"
                    st.metric("CH por Porción", ch_porc_str)

                modo_calculo = st.radio("Calcular por:", ["Gramos / ml exactos", "Número de porciones"], horizontal=True)
                
                if modo_calculo == "Gramos / ml exactos":
                    gramos = st.number_input("Cantidad en gramos/ml:", min_value=1, max_value=1000, value=100, step=10)
                    total_ch = round((info_prod["carbos_100g"] * gramos) / 100.0, 1)
                    detalle_txt = f"{gramos}g/ml"
                else:
                    if info_prod['carbos_porcion'] is not None:
                        n_porciones = st.number_input("Cantidad de porciones:", min_value=0.25, max_value=10.0, value=1.0, step=0.25)
                        total_ch = round(info_prod['carbos_porcion'] * n_porciones, 1)
                        detalle_txt = f"{n_porciones} porción(es) ({info_prod['serving_size']})"
                    else:
                        st.warning("Este producto no tiene registrada la cantidad de CH por porción. Utiliza el cálculo por gramos.")
                        total_ch = 0
                        detalle_txt = ""

                if total_ch > 0 and st.button("Añadir al Plato"):
                    st.session_state.plato.append({
                        "alimento": info_prod["nombre"],
                        "detalle": detalle_txt,
                        "total_carbos": total_ch
                    })
                    st.success(f"Añadido {info_prod['nombre']} ({total_ch}g CH)")

    if st.session_state.plato:
        st.markdown("---")
        st.write("### 🍽️ Plato Actual")
        df_plato = pd.DataFrame(st.session_state.plato)
        st.dataframe(df_plato, use_container_width=True)
        st.write(f"**Total Carbohidratos del plato:** {round(sum(df_plato['total_carbos']), 1)}g")
        
        if st.button("Vaciar Plato"):
            st.session_state.plato = []
            st.rerun()

# --- PESTAÑA 3: HISTORIAL ---
with pestana3:
    st.subheader("Historial")
    if os.path.exists(DATA_FILE):
        st.dataframe(pd.read_csv(DATA_FILE), use_container_width=True)
    else:
        st.info("Aún no hay registros.")

# --- PESTAÑA 4: CONFIGURACIÓN DE RANGOS ---
with pestana4:
    st.subheader("Configuración de Rangos de Glicemia y Ratios")
    
    for ci, c in enumerate(st.session_state.config["comidas"]):
        with st.expander(f"Configurar Ratios y Rangos para {c['nombre']}"):
            st.session_state.config["comidas"][ci]["ratio"] = st.number_input(
                f"Ratio de CH (g por 1U)", min_value=1.0, value=float(c["ratio"]), key=f"conf_ratio_{ci}"
            )
            
            st.write("**Rangos de Glicemia y Dosis de Corrección:**")
            escalas = c["escalas"]
            for ei, e in enumerate(escalas):
                col_min, col_max, col_dos, col_del = st.columns([3, 3, 3, 1])
                with col_min:
                    e["min"] = st.number_input("Min", value=int(e["min"]), key=f"min_{ci}_{ei}")
                with col_max:
                    e["max"] = st.number_input("Max", value=int(e["max"]), key=f"max_{ci}_{ei}")
                with col_dos:
                    e["dosis"] = st.number_input("Dosis (U)", value=float(e["dosis"]), step=0.5, key=f"dos_{ci}_{ei}")
                with col_del:
                    if st.button("✕", key=f"del_{ci}_{ei}"):
                        c["escalas"].pop(ei)
                        st.rerun()
            
            if st.button(f"+ Añadir Rango a {c['nombre']}", key=f"add_rango_{ci}"):
                c["escalas"].append({"min": 0, "max": 0, "dosis": 0.0})
                st.rerun()

    if st.button("Guardar Cambios de Configuración", type="primary"):
        guardar_config(st.session_state.config)
        st.success("Configuración actualizada.")

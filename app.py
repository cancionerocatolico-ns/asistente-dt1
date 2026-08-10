import json
import os
from datetime import datetime

import pandas as pd
import pytz
import requests
import streamlit as st
from PIL import Image
from pyzbar.pyzbar import decode

# Configuración de la página
st.set_page_config(
    page_title="Mi Control DT1",
    page_icon="💉",
    layout="centered",
    initial_sidebar_state="collapsed",
)

CONFIG_FILE = "config_dt1.json"
USDA_API_KEY = st.secrets.get("USDA_API_KEY", "")

# --- CONEXIÓN A GOOGLE SHEETS VÍA APPS SCRIPT ---
WEBHOOK_URL = st.secrets.get(
    "WEBHOOK_URL",
    "https://script.google.com/macros/s/AKfycbzqanAiYz52enC0jrrB2sJldaYC-6JQ6QKN9pticGCu2s4NrBGDcAY1EReGzl6QaaTDbg/exec",
)


def obtener_fecha_local():
    """Devuelve la fecha y hora actual ajustada a la zona horaria local."""
    try:
        tz = pytz.timezone("America/Santiago")
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M")


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
            obtener_historial_google_sheets.clear()
            return True
        else:
            st.error(f"Error al guardar en la hoja (Código HTTP {response.status_code})")
            return False
    except Exception as e:
        st.error(f"No se pudo conectar con Google Sheets: {e}")
        return False


@st.cache_data(ttl=60, show_spinner=False)
def obtener_historial_google_sheets():
    """Lee todos los registros desde la hoja de Google Sheets (Optimizada con Caché)."""
    try:
        response = requests.get(WEBHOOK_URL, timeout=8)
        if response.status_code == 200:
            datos = response.json()
            return pd.DataFrame(datos)
    except Exception:
        pass
    return pd.DataFrame()


def borrar_historial_google_sheets():
    """Limpia todos los datos guardados en la hoja de Google Sheets."""
    try:
        response = requests.post(WEBHOOK_URL, json={"action": "clear"}, timeout=8)
        if response.status_code == 200:
            obtener_historial_google_sheets.clear()
            return True
    except Exception as e:
        st.error(f"Error al intentar borrar: {e}")
    return False


# --- TRADUCTOR GRATUITO ---
def traducir_a_espanol(texto):
    if not texto:
        return texto
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=es&dt=t&q={requests.utils.quote(texto)}"
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            return res.json()[0][0][0]
    except Exception:
        pass
    return texto


ALIMENTOS_CASEROS = [
    {"alimento": "Pan de molde", "porcion": "1 rebanada (25g)", "carbos": 12},
    {"alimento": "Pan Hallulla / Marraqueta", "porcion": "1/2 unidad (50g)", "carbos": 25},
    {"alimento": "Arroz cocido", "porcion": "1 taza (150g)", "carbos": 40},
    {"alimento": "Fideos cocidos", "porcion": "1 taza (150g)", "carbos": 42},
    {"alimento": "Papas cocidas", "porcion": "1 unidad mediana (150g)", "carbos": 26},
    {"alimento": "Manzana", "porcion": "1 unidad mediana (150g)", "carbos": 18},
    {"alimento": "Plátano", "porcion": "1 unidad mediana (120g)", "carbos": 23},
    {"alimento": "Avena", "porcion": "1/2 taza (40g)", "carbos": 24},
    {"alimento": "Galletas integrales", "porcion": "3 unidades (30g)", "carbos": 15},
    {"alimento": "Yogurt batido", "porcion": "1 pote (120g)", "carbos": 10},
]

DEFAULT_CONFIG = {
    "comidas": [
        {
            "nombre": "Desayuno",
            "inicio": 6,
            "fin": 11,
            "ratio": 10.0,
            "escalas": [
                {"min": 0, "max": 130, "dosis": 0.0},
                {"min": 131, "max": 180, "dosis": 1.0},
                {"min": 181, "max": 230, "dosis": 2.0},
                {"min": 231, "max": 280, "dosis": 3.0},
                {"min": 281, "max": 999, "dosis": 4.0},
            ],
        },
        {
            "nombre": "Almuerzo",
            "inicio": 12,
            "fin": 17,
            "ratio": 15.0,
            "escalas": [
                {"min": 0, "max": 140, "dosis": 0.0},
                {"min": 141, "max": 190, "dosis": 1.0},
                {"min": 191, "max": 240, "dosis": 2.0},
                {"min": 241, "max": 999, "dosis": 3.0},
            ],
        },
        {
            "nombre": "Cena",
            "inicio": 18,
            "fin": 23,
            "ratio": 12.0,
            "escalas": [
                {"min": 0, "max": 130, "dosis": 0.0},
                {"min": 131, "max": 180, "dosis": 1.0},
                {"min": 181, "max": 230, "dosis": 2.0},
                {"min": 231, "max": 999, "dosis": 3.0},
            ],
        },
        {
            "nombre": "Colación",
            "inicio": 0,
            "fin": 23,
            "ratio": 15.0,
            "escalas": [
                {"min": 0, "max": 150, "dosis": 0.0},
                {"min": 151, "max": 200, "dosis": 1.0},
                {"min": 201, "max": 999, "dosis": 2.0},
            ],
        },
    ]
}


def cargar_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                # Asegurar que existan las colaciones en la config si se usaba una versión anterior
                nombres = [c["nombre"] for c in cfg.get("comidas", [])]
                if "Colación" not in nombres:
                    cfg["comidas"].append(DEFAULT_CONFIG["comidas"][3])
                return cfg
        except Exception:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG


def guardar_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)


def buscar_open_food_facts(query):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=8"
    headers = {"User-Agent": "MiControlDT1App/1.0 (streamlit-app)"}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            datos = response.json()
            productos = []
            for p in datos.get("products", []):
                nombre = p.get("product_name", "Sin nombre")
                marca = p.get("brands", "")
                nutriments = p.get("nutriments", {})
                carbos_100g = float(nutriments.get("carbohydrates_100g", 0.0) or 0.0)
                carbos_porcion = nutriments.get("carbohydrates_serving")
                carbos_porcion = (
                    float(carbos_porcion) if carbos_porcion is not None else None
                )
                serving_size = p.get("serving_size", "No especificada")

                nombre_completo = f"{nombre} ({marca})" if marca else nombre
                productos.append(
                    {
                        "nombre": nombre_completo,
                        "carbos_100g": carbos_100g,
                        "carbos_porcion": carbos_porcion,
                        "serving_size": serving_size,
                    }
                )
            return productos
    except Exception:
        pass
    return []


def buscar_usda(query):
    if not USDA_API_KEY:
        st.error("⚠️ Falta configurar la API Key de USDA en los Secrets de Streamlit.")
        return []

    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={USDA_API_KEY}&query={query}&pageSize=8"
    try:
        response = requests.get(url, timeout=8)
        if response.status_code == 200:
            datos = response.json()
            productos = []
            for item in datos.get("foods", []):
                nombre_original = item.get("description", "Sin nombre")
                nombre_es = traducir_a_espanol(nombre_original)

                carbos_100g = 0.0
                for nut in item.get("foodNutrients", []):
                    if nut.get("nutrientId") == 1005 or "Carbohydrate" in nut.get("nutrientName", ""):
                        carbos_100g = float(nut.get("value", 0.0))
                        break

                serving_size_val = item.get("servingSize")
                serving_unit = item.get("servingSizeUnit", "g")

                if serving_size_val:
                    serving_size = f"{serving_size_val} {serving_unit}"
                    carbos_porcion = round((carbos_100g * serving_size_val) / 100.0, 1)
                else:
                    serving_size = "100g (Estándar)"
                    carbos_porcion = carbos_100g

                productos.append(
                    {
                        "nombre": f"🇺🇸 {nombre_es}",
                        "carbos_100g": carbos_100g,
                        "carbos_porcion": carbos_porcion,
                        "serving_size": serving_size,
                    }
                )
            return productos
        elif response.status_code == 403:
            st.error("❌ La API Key de USDA es inválida o expiró.")
    except Exception:
        pass
    return []


if "config" not in st.session_state:
    st.session_state.config = cargar_config()

if "plato" not in st.session_state:
    st.session_state.plato = []

st.title("💉 Mi Control DT1")

pestana1, pestana2, pestana3, pestana4 = st.tabs(
    ["🧮 Calculadora", "🥗 Alimentos", "📜 Historial", "⚙️ Configuración"]
)

# --- PESTAÑA 1: CALCULADORA ---
with pestana1:
    st.subheader("Cálculo de Dosis")

    hora_actual = datetime.now().hour
    comida_sugerida_idx = 0
    for idx, c in enumerate(st.session_state.config["comidas"]):
        if c["nombre"] != "Colación" and c["inicio"] <= hora_actual <= c["fin"]:
            comida_sugerida_idx = idx
            break

    nombres_comidas = [c["nombre"] for c in st.session_state.config["comidas"]]
    comida_sel_nombre = st.selectbox(
        "Comida o Momento actual:", nombres_comidas, index=comida_sugerida_idx
    )
    comida_actual = next(
        c for c in st.session_state.config["comidas"] if c["nombre"] == comida_sel_nombre
    )

    st.caption(f"Ratio activo: **1U por cada {comida_actual['ratio']}g CH**")

    carbos_desde_plato = sum([item["total_carbos"] for item in st.session_state.plato])

    col1, col2 = st.columns([1, 1])
    with col1:
        glicemia = st.number_input(
            "Glicemia actual (mg/dL)", min_value=20, max_value=600, value=120, step=1
        )
    with col2:
        carbos = st.number_input(
            "Carbohidratos totales (g)",
            min_value=0,
            max_value=300,
            value=int(round(carbos_desde_plato)),
            step=1,
        )

    if st.session_state.plato:
        st.info(f"🛒 Carbohidratos del plato activo: **{round(carbos_desde_plato, 1)}g**")

    paso_dosis = st.radio("Redondeo de dosis (pasos de):", [0.5, 1.0], horizontal=True)

    if st.button("Calcular Dosis Total y Guardar", type="primary", use_container_width=True):
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
        st.metric(label="Dosis Sugerida Final", value=f"{total_redondeado:.1f} U")

        st.write("**Detalle del Cálculo:**")
        if rango_encontrado:
            st.write(f"- Corrección por glicemia (Rango `{rango_encontrado}`): **+{dosis_correccion} U**")
        else:
            st.write("- Corrección por glicemia: **+0.0 U** (Glicemia fuera de rangos)")

        st.write(f"- Bolus por comida ({carbos}g / {comida_actual['ratio']}): **+{dosis_comida:.2f} U**")
        st.write(f"- Dosis exacta sin redondear: `{total_exacto:.2f} U`")

        fecha_str = obtener_fecha_local()

        with st.spinner("Guardando en Google Sheets..."):
            exito = guardar_registro_google_sheets(
                fecha_str, comida_sel_nombre, glicemia, carbos, total_redondeado
            )

        if exito:
            st.success("✅ Registro respaldado exitosamente en Google Sheets.")

    # --- SECCIÓN PARA REGISTRO DE INSULINA BASAL ---
    st.markdown("---")
    with st.expander("🌙 Registrar Insulina Basal (Lenta / Dosis Diaria)"):
        col_b1, col_b2 = st.columns([2, 1])
        with col_b1:
            dosis_basal = st.number_input(
                "Unidades de Insulina Basal:", min_value=1.0, max_value=100.0, value=15.0, step=1.0
            )
        with col_b2:
            if st.button("Guardar Basal", use_container_width=True):
                fecha_str = obtener_fecha_local()
                with st.spinner("Guardando basal..."):
                    exito = guardar_registro_google_sheets(
                        fecha_str, "Insulina Basal", 0, 0, dosis_basal
                    )
                if exito:
                    st.success("✅ Dosis basal guardada.")

# --- PESTAÑA 2: BUSCADOR DE ALIMENTOS ---
with pestana2:
    st.subheader("Buscador de Alimentos")

    origen = st.radio(
        "Fuente de datos:",
        [
            "Tabla Rápida Casera",
            "USDA (Traducida al Español)",
            "Open Food Facts (Marcas/Empaquetados)",
            "📷 Escanear Código de Barras",
        ],
        horizontal=False,
    )

    if origen == "Tabla Rápida Casera":
        df_caseros = pd.DataFrame(ALIMENTOS_CASEROS)
        sel = st.selectbox("Selecciona alimento:", df_caseros["alimento"].tolist())
        item = df_caseros[df_caseros["alimento"] == sel].iloc[0]

        st.caption(f"Porción estándar: **{item['porcion']}** = **{item['carbos']}g CH**")
        cant_porciones = st.number_input(
            "Cantidad de porciones:", min_value=0.25, max_value=10.0, value=1.0, step=0.25
        )
        total_ch = round(item["carbos"] * cant_porciones, 1)

        if st.button("Añadir al Plato", use_container_width=True):
            st.session_state.plato.append(
                {
                    "alimento": item["alimento"],
                    "detalle": f"{cant_porciones} porción(es)",
                    "total_carbos": total_ch,
                }
            )
            st.success(f"Añadido {item['alimento']} ({total_ch}g CH)")

    elif origen == "📷 Escanear Código de Barras":
        st.info("💡 **Consejo de escaneo:** Asegúrate de enfocar con buena iluminación y mantener firme la cámara.")
        foto = st.camera_input("Enfoca el código de barras del producto")
        
        if foto:
            try:
                imagen = Image.open(foto)
                codigos = decode(imagen)
                if codigos:
                    codigo_barras = codigos[0].data.decode("utf-8")
                    st.success(f"📱 Código detectado: `{codigo_barras}`")

                    url = f"https://world.openfoodfacts.org/api/v0/product/{codigo_barras}.json"
                    headers = {"User-Agent": "MiControlDT1App/1.0 (streamlit-app)"}
                    res = requests.get(url, headers=headers, timeout=8)

                    if res.status_code == 200 and res.json().get("status") == 1:
                        producto = res.json()["product"]
                        nombre_prod = producto.get("product_name", "Producto sin nombre")
                        marca_prod = producto.get("brands", "")
                        nombre_completo = f"{nombre_prod} ({marca_prod})" if marca_prod else nombre_prod

                        nutriments = producto.get("nutriments", {})
                        carbos_100g = float(nutriments.get("carbohydrates_100g", 0.0) or 0.0)

                        st.write(f"**Alimento:** {nombre_completo}")
                        st.metric("Carbohidratos por 100g", f"{carbos_100g}g")

                        gramos = st.number_input(
                            "Gramos/ml a consumir:", min_value=1, max_value=1000, value=100, step=10
                        )
                        total_ch = round((carbos_100g * gramos) / 100.0, 1)

                        if st.button("Añadir al Plato", use_container_width=True):
                            st.session_state.plato.append(
                                {
                                    "alimento": nombre_completo,
                                    "detalle": f"{gramos}g/ml",
                                    "total_carbos": total_ch,
                                }
                            )
                            st.success(f"Añadido {nombre_completo} ({total_ch}g CH)")
                    else:
                        st.warning("⚠️ Producto no encontrado en la base de datos pública.")
                        st.write("Puedes ingresar la información manualmente a continuación:")
                        
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            nombre_manual = st.text_input("Nombre del alimento:", value="Producto Escaneado")
                        with col_m2:
                            carbos_manual = st.number_input("Carbohidratos calculados (g):", min_value=0.0, value=10.0, step=1.0)
                            
                        if st.button("Añadir Alimento Manualmente", use_container_width=True):
                            st.session_state.plato.append(
                                {
                                    "alimento": nombre_manual,
                                    "detalle": "Entrada Manual",
                                    "total_carbos": carbos_manual,
                                }
                            )
                            st.success(f"Añadido {nombre_manual} ({carbos_manual}g CH)")

                else:
                    st.warning("⚠️ No se detectó código de barras. Intenta tomar la foto con más luz o enfocar más cerca.")
            except Exception as e:
                st.error(f"Error al procesar la imagen: {e}")

    else:
        busqueda = st.text_input("Buscar alimento:")
        if busqueda:
            with st.spinner("Buscando alimentos..."):
                if "USDA" in origen:
                    resultados = buscar_usda(busqueda)
                else:
                    resultados = buscar_open_food_facts(busqueda)

            if resultados:
                opciones = [r["nombre"] for r in resultados]
                prod_sel = st.selectbox("Resultados encontrados:", opciones)
                info_prod = next(r for r in resultados if r["nombre"] == prod_sel)

                st.markdown("---")
                st.write(f"**Porción referencial:** `{info_prod['serving_size']}`")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("CH por 100g / 100ml", f"{info_prod['carbos_100g']}g")
                with col_b:
                    ch_p = (
                        f"{info_prod['carbos_porcion']}g"
                        if info_prod["carbos_porcion"] is not None
                        else "N/A"
                    )
                    st.metric("CH por Porción", ch_p)

                modo_calculo = st.radio(
                    "Calcular por:",
                    ["Gramos / ml exactos", "Número de porciones"],
                    horizontal=True,
                )

                if modo_calculo == "Gramos / ml exactos":
                    gramos = st.number_input(
                        "Cantidad en gramos/ml:", min_value=1, max_value=1000, value=100, step=10
                    )
                    total_ch = round((info_prod["carbos_100g"] * gramos) / 100.0, 1)
                    detalle_txt = f"{gramos}g/ml"
                else:
                    if info_prod["carbos_porcion"] is not None:
                        n_porciones = st.number_input(
                            "Cantidad de porciones:",
                            min_value=0.25,
                            max_value=10.0,
                            value=1.0,
                            step=0.25,
                        )
                        total_ch = round(info_prod["carbos_porcion"] * n_porciones, 1)
                        detalle_txt = f"{n_porciones} porción(es) ({info_prod['serving_size']})"
                    else:
                        st.warning("Sin datos por porción. Utiliza gramos exactos.")
                        total_ch = 0
                        detalle_txt = ""

                if total_ch > 0 and st.button("Añadir al Plato", use_container_width=True):
                    st.session_state.plato.append(
                        {
                            "alimento": info_prod["nombre"],
                            "detalle": detalle_txt,
                            "total_carbos": total_ch,
                        }
                    )
                    st.success(f"Añadido {info_prod['nombre']} ({total_ch}g CH)")
            else:
                st.warning("No se encontraron resultados.")

    if st.session_state.plato:
        st.markdown("---")
        st.write("### 🍽️ Plato Actual")
        df_plato = pd.DataFrame(st.session_state.plato)
        st.dataframe(df_plato, use_container_width=True)
        st.write(f"**Total Carbohidratos acumulados:** {round(sum(df_plato['total_carbos']), 1)}g")

        if st.button("Vaciar Plato", use_container_width=True):
            st.session_state.plato = []
            st.rerun()

# --- PESTAÑA 3: HISTORIAL DESDE GOOGLE SHEETS ---
with pestana3:
    st.subheader("Historial de Mediciones (Google Sheets)")

    with st.spinner("Cargando historial desde Google Sheets..."):
        df_historial = obtener_historial_google_sheets()

    if not df_historial.empty and "Fecha" in df_historial.columns:
        
        df_historial["Fecha_dt"] = pd.to_datetime(df_historial["Fecha"], errors="coerce")

        # FILTRO POR FECHAS
        st.write("🔍 **Filtrar por Fecha:**")
        fechas_validas = df_historial["Fecha_dt"].dropna()
        min_f = fechas_validas.min().date() if not fechas_validas.empty else datetime.now().date()
        max_f = fechas_validas.max().date() if not fechas_validas.empty else datetime.now().date()

        f_inicio, f_fin = st.date_input("Rango:", value=(min_f, max_f))

        mask = (df_historial["Fecha_dt"].dt.date >= f_inicio) & (
            df_historial["Fecha_dt"].dt.date <= f_fin
        )
        df_filtrado = df_historial.loc[mask].copy()

        # GRÁFICO SEGURO DE GLICEMIA
        st.write("📈 **Tendencia de Glicemia (mg/dL):**")
        try:
            df_grafico = df_filtrado[df_filtrado["Comida"] != "Insulina Basal"].copy()
            if not df_grafico.empty:
                df_grafico["Glicemia"] = pd.to_numeric(df_grafico["Glicemia"], errors="coerce")
                df_grafico = df_grafico[df_grafico["Glicemia"] > 0]
                if not df_grafico.empty:
                    df_chart = df_grafico.set_index("Fecha")[["Glicemia"]]
                    st.line_chart(df_chart)
                else:
                    st.caption("Sin datos numéricos de glicemia en el rango seleccionado.")
            else:
                st.caption("No hay registros de glicemia para graficar en este periodo.")
        except Exception:
            st.caption("No se pudo renderizar el gráfico con los datos actuales.")

        st.dataframe(
            df_filtrado.drop(columns=["Fecha_dt"], errors="ignore"), use_container_width=True
        )

        st.markdown("---")
        col_d1, col_d2 = st.columns(2)

        with col_d1:
            csv_data = df_filtrado.drop(columns=["Fecha_dt"], errors="ignore").to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Descargar Historial (CSV)",
                data=csv_data,
                file_name=f"historial_dt1_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col_d2:
            if st.button("🗑️ Borrar Historial en Google Sheets", type="secondary", use_container_width=True):
                st.session_state.confirmar_borrado = True

        if st.session_state.get("confirmar_borrado", False):
            st.warning("⚠️ ¿Estás seguro de que deseas vaciar toda la hoja en Google Sheets?")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("Sí, Eliminar Definitivamente", type="primary", use_container_width=True):
                    if borrar_historial_google_sheets():
                        st.session_state.confirmar_borrado = False
                        st.success("Historial eliminado correctamente de Google Sheets.")
                        st.rerun()
                    else:
                        st.error("No se pudo borrar la hoja.")
            with col_b2:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state.confirmar_borrado = False
                    st.rerun()
    else:
        st.info("No hay registros guardados en Google Sheets por el momento.")

# --- PESTAÑA 4: CONFIGURACIÓN ---
with pestana4:
    st.subheader("Configuración de Rangos y Ratios")
    for ci, c in enumerate(st.session_state.config["comidas"]):
        with st.expander(f"⚙️ Configurar Ratios y Rangos para {c['nombre']}"):
            st.session_state.config["comidas"][ci]["ratio"] = st.number_input(
                f"Ratio de CH (g por 1U)",
                min_value=1.0,
                value=float(c["ratio"]),
                key=f"conf_ratio_{ci}",
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
                    e["dosis"] = st.number_input(
                        "Dosis (U)", value=float(e["dosis"]), step=0.5, key=f"dos_{ci}_{ei}"
                    )
                with col_del:
                    if st.button("✕", key=f"del_{ci}_{ei}"):
                        c["escalas"].pop(ei)
                        st.rerun()
            if st.button(f"+ Añadir Rango a {c['nombre']}", key=f"add_rango_{ci}"):
                c["escalas"].append({"min": 0, "max": 0, "dosis": 0.0})
                st.rerun()

    if st.button("Guardar Cambios de Configuración", type="primary", use_container_width=True):
        guardar_config(st.session_state.config)
        st.success("Configuración actualizada con éxito.")

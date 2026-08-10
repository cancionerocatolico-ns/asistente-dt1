import streamlit as st
import requests

# Configuración de la página
st.set_page_config(page_title="Buscador de Alimentos USDA", page_icon="🥗", layout="wide")

# ==============================================================================
# OBTENCIÓN SEGURA DE LA API KEY
# Streamlit busca la clave en st.secrets (configurado en Streamlit Cloud o en .streamlit/secrets.toml)
# ==============================================================================
USDA_API_KEY = st.secrets.get("USDA_API_KEY", "")

# URL base de la API de USDA FoodData Central
BASE_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

st.title("🥗 Buscador Nutricional USDA")
st.write("Consulta la información nutricional de alimentos utilizando la base de datos de USDA.")

# Comprobación de seguridad: verificar si la API Key está presente
if not USDA_API_KEY:
    st.error("⚠️ No se encontró la API Key de USDA. Asegúrate de configurarla en `st.secrets` o en `.streamlit/secrets.toml`.")
    st.stop()

# Campo de entrada para el usuario
query = st.text_input("Ingresa un alimento en inglés (ej: 'apple', 'chicken breast', 'rice'):", value="apple")

if st.button("Buscar Alimento", type="primary"):
    if query.strip():
        params = {
            "api_key": USDA_API_KEY,
            "query": query,
            "pageSize": 5
        }
        
        with st.spinner("Buscando en USDA FoodData Central..."):
            try:
                response = requests.get(BASE_URL, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    foods = data.get("foods", [])
                    
                    if foods:
                        st.success(f"Se encontraron {len(foods)} resultados para '{query}':")
                        
                        for food in foods:
                            with st.expander(f"📌 {food.get('description', 'Sin descripción')}"):
                                st.write(f"**Categoría:** {food.get('foodCategory', 'N/A')}")
                                st.write(f"**ID de Alimento (FDC ID):** {food.get('fdcId')}")
                                
                                # Muestra los nutrientes principales si están disponibles
                                nutrients = food.get("foodNutrients", [])
                                if nutrients:
                                    st.subheader("Nutrientes principales (por 100g):")
                                    
                                    # Creamos una lista limpia con nombre, valor y unidad
                                    nutr_data = []
                                    for n in nutrients:
                                        name = n.get("nutrientName")
                                        val = n.get("value")
                                        unit = n.get("unitName")
                                        if name and val is not None:
                                            nutr_data.append({
                                                "Nutriente": name,
                                                "Cantidad": f"{val} {unit}"
                                            })
                                    
                                    st.table(nutr_data[:10])  # Mostrar los primeros 10 nutrientes
                    else:
                        st.warning("No se encontraron alimentos con ese nombre. Intenta con otro término en inglés.")
                elif response.status_code == 403:
                    st.error("❌ Error 403: La API Key ingresada no es válida o ha sido revocada.")
                else:
                    st.error(f"Error al consultar la API (Código HTTP {response.status_code}).")
            
            except requests.exceptions.RequestException as e:
                st.error(f"Error de conexión: {e}")
    else:
        st.info("Por favor escribe un término de búsqueda.")

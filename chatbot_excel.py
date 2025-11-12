import streamlit as st
import pandas as pd
import re
import requests
import json

# =============================
# CONFIGURACIÓN DE LA PÁGINA
# =============================
st.set_page_config(
    page_title="Catálogo SMC Inteligente",
    page_icon="🤖",
    layout="wide"
)

# =============================
# CARGA DE DATOS
# =============================
@st.cache_data
def cargar_datos():
    return pd.read_excel("productos.xlsx")

df = cargar_datos()

# =============================
# FUNCIÓN DE BÚSQUEDA INTELIGENTE (GROQ)
# =============================
def buscar_producto_groq(pregunta):
    """
    Envía la consulta del usuario a Groq para interpretación semántica
    y devuelve una lista de coincidencias reales del Excel.
    """
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {st.secrets['GROQ_API_KEY']}",
        "Content-Type": "application/json"
    }

    # Creamos un contexto para que el modelo entienda el tipo de datos
    prompt = f"""
Eres un asistente experto en productos neumáticos de SMC.
El usuario hará una pregunta o escribirá un nombre parcial.
Tu tarea es devolver las palabras clave o fragmentos relevantes
para buscar dentro del Excel de productos.

Pregunta del usuario: {pregunta}

Responde SOLO con una lista corta de palabras clave o códigos posibles separados por comas.
Ejemplo de respuesta: manguera, 12mm, TU1208
"""

    data = {
        "model": "mixtral-8x7b-32768",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(data))
        result = response.json()
        keywords = result["choices"][0]["message"]["content"]
        palabras = [p.strip().upper() for p in re.split(r"[,\n]", keywords) if p.strip()]

        # Buscar coincidencias en el Excel
        resultados = df[df["DESCRIPCION"].str.upper().str.contains("|".join(palabras), na=False) |
                        df["CODIGO SMC"].str.upper().str.contains("|".join(palabras), na=False)]

        if not resultados.empty:
            return resultados[["CODIGO SMC", "DESCRIPCION", "CANTIDAD(und)", "T.ENTREGA"]]
        else:
            return None
    except Exception as e:
        st.error(f"Error al conectarse con Groq: {e}")
        return None

# =============================
# INTERFAZ DE CHAT
# =============================

st.markdown("<h1 style='text-align:center;'>🤖 Catálogo SMC Inteligente</h1>", unsafe_allow_html=True)
st.write("💬 Pregúntame por cualquier producto: código, medida o descripción parcial.")

if "historial" not in st.session_state:
    st.session_state.historial = []

entrada = st.chat_input("🔍 Escribe el producto que necesitas...")

if entrada:
    resultados = buscar_producto_groq(entrada)
    st.session_state.historial.append(("Tú", entrada, resultados))

for remitente, consulta, resultados in st.session_state.historial:
    st.chat_message("user").write(f"🗣️ {consulta}")
    if resultados is not None and not resultados.empty:
        with st.chat_message("assistant"):
            st.dataframe(resultados, use_container_width=True, hide_index=True)
    else:
        st.chat_message("assistant").write("No encontré coincidencias exactas 🤔. Intenta con otra descripción o código.")
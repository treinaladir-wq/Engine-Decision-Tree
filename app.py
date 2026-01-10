import streamlit as st
import pandas as pd
import google.generativeai as genai
from supabase import create_client

# 1. Configuração de Estilo (Cores Neutras)
st.set_page_config(page_title="Engine Decision Tree", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    .stButton>button { background-color: #2D3436; color: white; border-radius: 8px; }
    .stButton>button:hover { background-color: #636E72; color: white; }
    h1, h2, h3 { color: #2D3436; }
    </style>
    """, unsafe_allow_html=True)

# 2. Conexão Segura com as Chaves (Secrets)
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_KEY"]
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Erro: Configure as chaves no painel do Streamlit Cloud.")

# --- INTERFACE ---
st.title("📂 Engine Decision Tree")

tab1, tab2 = st.tabs(["🎮 Navegação", "⚙️ Admin"])

with tab1:
    st.info("O fluxo aparecerá aqui após ser alimentado no painel Admin.")
    # A lógica de botões será processada aqui lendo o banco de dados

with tab2:
    st.subheader("Alimentar Sistema")
    upload = st.file_uploader("Suba a imagem do fluxograma", type=["png", "jpg"])
    
    if upload and st.button("Processar com IA"):
        st.write("IA lendo imagem... (Simulação)")
        # Aqui entra a chamada da API do Gemini para salvar no Supabase

    st.divider()
    st.subheader("Relatórios (BI)")
    if st.button("Gerar Log de Teste"):
        supabase.table("logs").insert({"no_nome": "Teste", "escolha": "Início"}).execute()
        st.success("Log salvo no banco!")

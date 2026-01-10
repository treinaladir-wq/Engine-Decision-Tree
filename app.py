import streamlit as st
import pandas as pd
import google.generativeai as genai
from supabase import create_client
import json

# --- 1. DESIGN DARK MODE ---
st.set_page_config(page_title="Engine Decision Tree", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton>button { 
        width: 100%; border-radius: 8px; height: 3.5em; 
        background-color: #262730; color: white; border: 1px solid #4B4B4B; 
    }
    .stButton>button:hover { border-color: #FF4B4B; color: #FF4B4B; }
    .instruction-card { 
        background-color: #161B22; padding: 25px; border-radius: 10px; 
        border: 1px solid #30363D; text-align: center; margin-bottom: 20px; 
    }
    h1, h2, h3, p, label { color: #F5F5F5 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES E MODELO ---
try:
    # Carrega chaves dos Secrets
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    gemini_key = st.secrets["GEMINI_KEY"]
    admin_pw = st.secrets["ADMIN_PASSWORD"]

    supabase = create_client(url, key)
    
    # Configuração da IA - Forçando modelo 2.0 para evitar erro 404
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    st.error(f"⚠️ Erro de Configuração: {e}")
    st.stop()

# --- 3. INTERFACE ---
st.title("📂 Engine Decision Tree")
tab1, tab2 = st.tabs(["🎮 Navegação", "⚙️ Admin"])

with tab1:
    try:
        res = supabase.table("fluxos").select("*").execute()
        if not res.data:
            st.info("Sistema vazio. Configure o fluxograma no Painel Admin.")
        else:
            fluxo = {item['id']: item for item in res.data}
            if 'step' not in st.session_state:
                st.session_state.step = res.data[0]['id']
            
            atual = fluxo.get(st.session_state.step)
            if atual:
                st.markdown(f"<div class='instruction-card'><h2>{atual['pergunta']}</h2></div>", unsafe_allow_html=True)
                opcoes = atual.get('opcoes', {})
                cols = st.columns(len(opcoes) if opcoes else 1)
                for i, (texto, destino) in enumerate(opcoes.items()):
                    if cols[i].button(texto):
                        supabase.table("logs").insert({"no_nome": atual['pergunta'], "escolha": texto}).execute()
                        st.session_state.step = destino
                        st.rerun()
                if st.button("⬅️ Reiniciar Fluxo"):
                    st.session_state.step = res.data[0]['id']
                    st.rerun()
    except:
        st.write("A carregar base de dados...")

with tab2:
    st.subheader("🔐 Painel de Controlo")
    senha_inserida = st.text_input("Palavra-passe de Administrador", type="password")
    
    if senha_inserida == admin_pw:
        st.success("Acesso Autorizado")
        st.divider()
        
        arquivo = st.file_uploader("Suba a imagem do fluxograma", type=["png", "jpg", "jpeg"])
        
        if arquivo and st.button("🤖 Processar com Inteligência Artificial"):
            with st.spinner("A IA está a interpretar o fluxograma..."):
                try:
                    # Converte imagem para formato compatível
                    img_parts = [{"mime_type": arquivo.type, "data": arquivo.getvalue()}]
                    
                    prompt = """Analise a imagem e gere um JSON puro (lista de objetos).
                    Formato: [{"id": "nome", "pergunta": "texto", "opcoes": {"Botão": "id_destino"}}]
                    Não inclua explicações ou blocos de código markdown."""
                    
                    # Chamada do modelo 2.0
                    response = model.generate_content([prompt, img_parts[0]])
                    
                    # Limpeza do texto para JSON
                    raw_text = response.text.replace('```json', '').replace('```', '').strip()
                    dados = json.loads(raw_text)
                    
                    # Limpa fluxos antigos e guarda os novos
                    supabase.table("fluxos").delete().neq("id", "reset").execute()
                    for item in dados:
                        supabase.table("fluxos").upsert(item).execute()
                        
                    st.success("✅ Sistema atualizado! Vá à aba Navegação.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro no processamento: {e}")
                    st.info("Verifique se a imagem é clara ou tente o modelo Gemini Pro se o erro 404 persistir.")
        
        if st.button("🗑️ Resetar Histórico de BI (Logs)"):
            supabase.table("logs").delete().neq("id", 0).execute()
            st.warning("Todos os logs foram apagados.")
            
    elif senha_inserida != "":
        st.error("Palavra-passe incorreta.")

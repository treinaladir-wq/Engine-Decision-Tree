import streamlit as st
import pandas as pd
import google.generativeai as genai
from supabase import create_client
import json

# --- ESTILO DARK PROFISSIONAL ---
st.set_page_config(page_title="Engine Decision Tree", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #262730; color: white; border: 1px solid #4B4B4B; }
    .stButton>button:hover { border-color: #FF4B4B; color: #FF4B4B; }
    .instruction-card { background-color: #161B22; padding: 20px; border-radius: 10px; border: 1px solid #30363D; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÕES ---
url, key, gemini_key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"], st.secrets["GEMINI_KEY"]
supabase = create_client(url, key)
genai.configure(api_key=gemini_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- INTERFACE ---
st.title("📂 Engine Decision Tree")
tab1, tab2 = st.tabs(["🎮 Navegação", "⚙️ Admin"])

with tab1:
    res = supabase.table("fluxos").select("*").execute()
    if not res.data:
        st.info("Nenhum fluxo encontrado. Vá em Admin e suba uma imagem.")
    else:
        fluxo = {item['id']: item for item in res.data}
        if 'step' not in st.session_state: st.session_state.step = res.data[0]['id']
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
            if st.button("⬅️ Reiniciar"):
                st.session_state.step = res.data[0]['id']
                st.rerun()

with tab2:
    st.subheader("🔐 Área do Administrador")
    senha = st.text_input("Senha", type="password")
    if senha == st.secrets["ADMIN_PASSWORD"]:
        st.success("Acesso liberado!")
        arquivo = st.file_uploader("Suba a imagem do fluxograma", type=["png", "jpg", "jpeg"])
        if arquivo and st.button("🤖 Processar com IA"):
            with st.spinner("Lendo imagem e gerando lógica..."):
                try:
                    # 1. PREPARAÇÃO DA IMAGEM (A correção do erro está aqui)
                    bytes_data = arquivo.getvalue()
                    image_parts = [{"mime_type": arquivo.type, "data": bytes_data}]
                    
                    # 2. PROMPT REFORÇADO
                    prompt = """Analise este fluxograma e transforme em JSON. 
                    Retorne ESTRITAMENTE o código JSON puro, sem textos extras ou explicações.
                    Formato: [{"id": "nome", "pergunta": "texto", "opcoes": {"Botão": "id_destino"}}]"""
                    
                    # 3. CHAMADA DA IA
                    resposta = model.generate_content([prompt, image_parts[0]])
                    
                    # 4. LIMPEZA E SALVAMENTO
                    texto_ia = resposta.text.replace('```json', '').replace('```', '').strip()
                    dados_ia = json.loads(texto_ia)
                    
                    for item in dados_ia:
                        supabase.table("fluxos").upsert(item).execute()
                        
                    st.success("✅ Fluxograma carregado com sucesso!")
                except Exception as e:
                    st.error(f"Erro detalhado: {e}")
            with st.spinner("Lendo imagem..."):
                resposta = model.generate_content(["Transforme este fluxograma em um JSON (lista de objetos com 'id', 'pergunta', 'opcoes' como dicionário texto:id_destino). Retorne apenas o JSON puro.", arquivo])
                limpo = resposta.text.replace('```json', '').replace('```', '').strip()
                for item in json.loads(limpo): supabase.table("fluxos").upsert(item).execute()
                st.success("Fluxo atualizado!")

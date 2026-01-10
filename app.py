import streamlit as st
import pandas as pd
import google.generativeai as genai
from supabase import create_client
import json

# --- 1. CONFIGURAÇÃO DE DESIGN (DARK MODE) ---
st.set_page_config(page_title="Engine Decision Tree", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton>button { 
        width: 100%; border-radius: 5px; height: 3em; 
        background-color: #262730; color: white; border: 1px solid #4B4B4B; 
    }
    .stButton>button:hover { border-color: #FF4B4B; color: #FF4B4B; }
    .instruction-card { 
        background-color: #161B22; padding: 25px; border-radius: 10px; 
        border: 1px solid #30363D; text-align: center; margin-bottom: 20px; 
    }
    h1, h2, h3, p, label { color: #F5F5F5 !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #0E1117; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES (SECRETS) ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    gemini_key = st.secrets["GEMINI_KEY"]
    admin_password = st.secrets["ADMIN_PASSWORD"]

    supabase = create_client(url, key)
    genai.configure(api_key=gemini_key)
    # Usando o nome estável do modelo para evitar erros 404
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Erro ao carregar Secrets: {e}")
    st.stop()

# --- 3. INTERFACE PRINCIPAL ---
st.title("📂 Engine Decision Tree")
tab1, tab2 = st.tabs(["🎮 Navegação", "⚙️ Admin"])

with tab1:
    try:
        res = supabase.table("fluxos").select("*").execute()
        if not res.data:
            st.info("O sistema está vazio. Vá em Admin para carregar um fluxograma.")
        else:
            fluxo = {item['id']: item for item in res.data}
            
            # Inicializa o estado do passo atual
            if 'step' not in st.session_state:
                st.session_state.step = res.data[0]['id']
            
            atual = fluxo.get(st.session_state.step)
            
            if atual:
                st.markdown(f"<div class='instruction-card'><h2>{atual['pergunta']}</h2></div>", unsafe_allow_html=True)
                
                opcoes = atual.get('opcoes', {})
                cols = st.columns(len(opcoes) if opcoes else 1)
                
                for i, (texto, destino) in enumerate(opcoes.items()):
                    if cols[i].button(texto):
                        # Salva Log no Supabase para o BI
                        supabase.table("logs").insert({
                            "no_nome": atual['pergunta'], 
                            "escolha": texto
                        }).execute()
                        
                        st.session_state.step = destino
                        st.rerun()
                
                if st.button("⬅️ Reiniciar Fluxo"):
                    st.session_state.step = res.data[0]['id']
                    st.rerun()
    except Exception as e:
        st.error(f"Erro na navegação: {e}")

with tab2:
    st.subheader("🔐 Área Restrita")
    senha = st.text_input("Digite a senha de administrador", type="password")
    
    if senha == admin_password:
        st.success("Acesso Liberado")
        st.divider()
        
        arquivo = st.file_uploader("Suba a imagem do fluxograma (PNG ou JPG)", type=["png", "jpg", "jpeg"])
        
        if arquivo and st.button("🤖 Processar Fluxograma com IA"):
            with st.spinner("A IA está analisando a imagem..."):
                try:
                    # Preparação da imagem para o Gemini
                    image_data = arquivo.getvalue()
                    image_parts = [
                        {
                            "mime_type": arquivo.type,
                            "data": image_data
                        }
                    ]
                    
                    prompt = """Analise este fluxograma e extraia a lógica de decisão.
                    Retorne ESTRITAMENTE um código JSON (uma lista de objetos).
                    Cada objeto deve ter:
                    - 'id': um nome único para o nó.
                    - 'pergunta': o texto da pergunta ou instrução.
                    - 'opcoes': um dicionário onde a chave é o texto do botão e o valor é o 'id' do próximo nó.
                    Exemplo: [{"id": "inicio", "pergunta": "Ligar motor?", "opcoes": {"Sim": "passo2", "Não": "fim"}}]
                    Não adicione textos explicativos, retorne apenas o JSON."""
                    
                    # Chamada da IA
                    response = model.generate_content([prompt, image_parts[0]])
                    
                    # Limpeza de possíveis marcações Markdown da IA
                    json_clean = response.text.replace('```json', '').replace('```', '').strip()
                    dados_ia = json.loads(json_clean)
                    
                    # Limpa o banco antes de subir o novo (opcional, dependendo da sua estratégia)
                    # supabase.table("fluxos").delete().neq("id", "0").execute()
                    
                    # Salva no banco de dados
                    for item in dados_ia:
                        supabase.table("fluxos").upsert(item).execute()
                    
                    st.success("✅ Fluxograma processado e banco atualizado!")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"Erro detalhado: {e}")
                    st.info("Dica: Tente usar uma imagem mais nítida ou verifique sua GEMINI_KEY.")
        
        if st.button("🗑️ Limpar Todos os Dados (Reset)"):
            supabase.table("fluxos").delete().neq("id", "xyz").execute()
            st.warning("Banco de dados de fluxos limpo.")
            
    elif senha != "":
        st.error("Senha incorreta.")

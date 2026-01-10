import streamlit as st
import pandas as pd
from supabase import create_client
import json

# --- 1. CONFIGURAÇÃO DE DESIGN ---
st.set_page_config(page_title="Engine Decision Tree", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #262730; color: white; border: 1px solid #4B4B4B; }
    .stButton>button:hover { border-color: #00FFAA; color: #00FFAA; }
    .instruction-card { background-color: #161B22; padding: 25px; border-radius: 12px; border: 1px solid #30363D; text-align: center; margin-bottom: 20px; }
    h1, h2, h3, p, label { color: #F5F5F5 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
admin_pw = st.secrets["ADMIN_PASSWORD"]
supabase = create_client(url, key)

# --- 3. INTERFACE ---
st.title("📂 Engine Decision Tree")
tab1, tab2 = st.tabs(["🎮 Navegação", "⚙️ Admin (Planilha)"])

with tab1:
    res = supabase.table("fluxos").select("*").execute()
    if not res.data:
        st.info("Nenhum fluxo carregado. Vá em Admin.")
    else:
        # Organiza os dados. O primeiro ID da planilha será o início.
        fluxo = {str(item['id']): item for item in res.data}
        if 'step' not in st.session_state:
            st.session_state.step = str(res.data[0]['id'])
        
        atual = fluxo.get(st.session_state.step)
        if atual:
            st.markdown(f"<div class='instruction-card'><h2>{atual['pergunta']}</h2></div>", unsafe_allow_html=True)
            
            opcoes = atual['opcoes']
            if isinstance(opcoes, str):
                opcoes = json.loads(opcoes)
            
            cols = st.columns(len(opcoes) if opcoes else 1)
            for i, (texto, destino) in enumerate(opcoes.items()):
                if cols[i].button(texto):
                    # Registro para o BI
                    supabase.table("logs").insert({"no_nome": atual['pergunta'], "escolha": texto}).execute()
                    st.session_state.step = str(destino)
                    st.rerun()
            
            if st.button("⬅️ Reiniciar"):
                st.session_state.step = str(res.data[0]['id'])
                st.rerun()

with tab2:
    st.subheader("🔐 Gestão de Fluxograma")
    senha = st.text_input("Senha", type="password")
    
    if senha == admin_pw:
        st.write("### Importar Planilha")
        st.caption("Formato esperado: ID | Pergunta | Botão 1 | botão_destino | Botão 2 | botão2_destino ...")
        
        arquivo_csv = st.file_uploader("Suba seu arquivo CSV", type=["csv"])
        
        if arquivo_csv:
            df = pd.read_csv(arquivo_csv).fillna("") # Preenche vazios para não dar erro
            st.write("Prévia da Planilha:", df.head())
            
            if st.button("🚀 Atualizar Sistema"):
                try:
                    # Limpa o banco atual antes de subir o novo
                    supabase.table("fluxos").delete().neq("id", "reset_all").execute()
                    
                    for _, row in df.iterrows():
                        dict_opcoes = {}
                        # Lógica para capturar pares de colunas (Botão X e Destino X)
                        # Começa da 3ª coluna (índice 2) e pula de 2 em 2
                        for i in range(2, len(df.columns), 2):
                            nome_botao = row.iloc[i]
                            destino = row.iloc[i+1] if (i+1) < len(df.columns) else ""
                            
                            if nome_botao and destino: # Só adiciona se ambos estiverem preenchidos
                                dict_opcoes[str(nome_botao)] = str(destino)
                        
                        supabase.table("fluxos").insert({
                            "id": str(row['id']),
                            "pergunta": row['pergunta'],
                            "opcoes": dict_opcoes
                        }).execute()
                    
                    st.success("✅ Sistema atualizado com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao processar planilha: {e}")

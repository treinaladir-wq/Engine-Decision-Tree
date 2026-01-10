import streamlit as st
import pandas as pd
from supabase import create_client
import json

# --- 1. CONFIGURAÇÃO DE DESIGN ---
st.set_page_config(page_title="Admin - Engine Decision Tree", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #262730; color: white; border: 1px solid #4B4B4B; }
    .stButton>button:hover { border-color: #00FFAA; color: #00FFAA; }
    .instruction-card { background-color: #161B22; padding: 25px; border-radius: 12px; border: 1px solid #30363D; text-align: center; margin-bottom: 20px; }
    h1, h2, h3, p, label { color: #F5F5F5 !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: #0E1117; }
    /* Estilo para a tabela de gestão */
    .theme-row { padding: 10px; border-bottom: 1px solid #30363D; display: flex; justify-content: space-between; align-items: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
admin_pw = st.secrets["ADMIN_PASSWORD"]
supabase = create_client(url, key)

# --- 3. INTERFACE ---
st.title("📂 Sistema de Apoio ao Atendimento")
tab1, tab2 = st.tabs(["🎮 Navegação", "⚙️ Painel de Gestão"])

with tab1:
    res_temas = supabase.table("fluxos").select("tema").execute()
    todos_temas = sorted(list(set([item['tema'] for item in res_temas.data]))) if res_temas.data else []

    if not todos_temas:
        st.info("Nenhum fluxograma cadastrado no sistema.")
    else:
        tema_selecionado = st.selectbox("Selecione o Guia de Atendimento:", todos_temas)
        res = supabase.table("fluxos").select("*").eq("tema", tema_selecionado).execute()
        
        if res.data:
            fluxo = {str(item['id']): item for item in res.data}
            if 'last_tema' not in st.session_state or st.session_state.last_tema != tema_selecionado:
                st.session_state.step = str(res.data[0]['id'])
                st.session_state.last_tema = tema_selecionado
            
            atual = fluxo.get(st.session_state.step)
            if atual:
                st.markdown(f"<div class='instruction-card'><h3>{tema_selecionado}</h3><h2>{atual['pergunta']}</h2></div>", unsafe_allow_html=True)
                opcoes = atual['opcoes']
                if isinstance(opcoes, str): opcoes = json.loads(opcoes)
                
                cols = st.columns(len(opcoes) if opcoes else 1)
                for i, (texto, destino) in enumerate(opcoes.items()):
                    if cols[i].button(texto, key=f"nav_{i}"):
                        supabase.table("logs").insert({"no_nome": f"[{tema_selecionado}] {atual['pergunta']}", "escolha": texto}).execute()
                        st.session_state.step = str(destino)
                        st.rerun()
                if st.button("⬅️ Reiniciar"):
                    st.session_state.step = str(res.data[0]['id'])
                    st.rerun()

with tab2:
    st.subheader("🔐 Gestão do Sistema")
    senha = st.text_input("Senha", type="password")
    
    if senha == admin_pw:
        # --- SEÇÃO 1: UPLOAD ---
        st.write("### 📤 Subir ou Substituir Tema")
        col1, col2 = st.columns([1, 2])
        with col1:
            novo_tema = st.text_input("Nome do Tema")
        with col2:
            arquivo_csv = st.file_uploader("CSV (ID | Pergunta | Botão 1 | Destino 1...)", type=["csv"])
        
        if arquivo_csv and novo_tema:
            if st.button(f"Salvar/Atualizar '{novo_tema}'"):
                df = pd.read_csv(arquivo_csv).fillna("")
                supabase.table("fluxos").delete().eq("tema", novo_tema).execute()
                for _, row in df.iterrows():
                    dict_opcoes = {}
                    for i in range(2, len(df.columns), 2):
                        nome_botao = row.iloc[i]
                        destino = row.iloc[i+1] if (i+1) < len(df.columns) else ""
                        if nome_botao and destino: dict_opcoes[str(nome_botao)] = str(destino)
                    supabase.table("fluxos").insert({"id": str(row['id']), "pergunta": row['pergunta'], "tema": novo_tema, "opcoes": dict_opcoes}).execute()
                st.success(f"Tema '{novo_tema}' salvo!")
                st.rerun()

        st.divider()

        # --- SEÇÃO 2: GERENCIAR TEMAS EXISTENTES ---
        st.write("### 📂 Temas Ativos no Banco")
        res_gestao = supabase.table("fluxos").select("tema").execute()
        temas_existentes = sorted(list(set([item['tema'] for item in res_gestao.data]))) if res_gestao.data else []
        
        if not temas_existentes:
            st.write("Nenhum arquivo encontrado.")
        else:
            for t in temas_existentes:
                col_nome, col_btn = st.columns([4, 1])
                col_nome.write(f"📁 **{t}**")
                if col_btn.button("Excluir", key=f"del_{t}"):
                    supabase.table("fluxos").delete().eq("tema", t).execute()
                    st.warning(f"Tema '{t}' removido.")
                    st.rerun()

        st.divider()
        if st.button("🗑️ Limpar Todos os Logs de BI"):
            supabase.table("logs").delete().neq("id", 0).execute()
            st.success("Histórico limpo.")

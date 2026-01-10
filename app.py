import streamlit as st
import pandas as pd
from supabase import create_client
import json

# --- 1. CONFIGURAÇÃO DE DESIGN ---
st.set_page_config(page_title="Suporte Técnico - Decision Tree", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #262730; color: white; border: 1px solid #4B4B4B; }
    .stButton>button:hover { border-color: #00FFAA; color: #00FFAA; }
    .instruction-card { background-color: #161B22; padding: 25px; border-radius: 12px; border: 1px solid #30363D; text-align: center; margin-bottom: 20px; }
    .error-card { background-color: #442222; padding: 15px; border-radius: 10px; border: 1px solid #FF4B4B; text-align: center; color: white; margin-bottom: 15px; }
    h1, h2, h3, p, label { color: #F5F5F5 !important; }
    .stSelectbox label { color: #00FFAA !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
admin_pw = st.secrets["ADMIN_PASSWORD"]
supabase = create_client(url, key)

# --- 3. INTERFACE ---
st.title("📂 Guia de Atendimento Dinâmico")
tab1, tab2 = st.tabs(["🎮 Navegação", "⚙️ Gestão"])

with tab1:
    # Busca temas para o seletor
    res_temas = supabase.table("fluxos").select("tema").execute()
    todos_temas = sorted(list(set([item['tema'] for item in res_temas.data]))) if res_temas.data else []

    if not todos_temas:
        st.info("Nenhum guia disponível. Use a aba Gestão para importar arquivos.")
    else:
        # --- BUSCA E FILTRO ---
        search_query = st.text_input("🔍 Pesquisar por tema (ex: Motor, Garantia...)", "").lower()
        temas_filtrados = [t for t in todos_temas if search_query in t.lower()]
        
        if not temas_filtrados:
            st.warning("Nenhum tema encontrado com esse nome.")
        else:
            tema_selecionado = st.selectbox("Selecione o Fluxograma:", temas_filtrados)
            
            # Busca dados do tema selecionado
            res = supabase.table("fluxos").select("*").eq("tema", tema_selecionado).execute()
            
            if res.data:
                fluxo = {str(item['id']): item for item in res.data}
                
                # Reset automático ao trocar de tema
                if 'last_tema' not in st.session_state or st.session_state.last_tema != tema_selecionado:
                    st.session_state.step = str(res.data[0]['id'])
                    st.session_state.last_tema = tema_selecionado
                
                atual = fluxo.get(st.session_state.step)
                
                if atual:
                    st.markdown(f"<div class='instruction-card'><h3>{tema_selecionado}</h3><h2>{atual['pergunta']}</h2></div>", unsafe_allow_html=True)
                    
                    opcoes = atual.get('opcoes', {})
                    if isinstance(opcoes, str): opcoes = json.loads(opcoes)
                    
                    if opcoes:
                        cols = st.columns(len(opcoes))
                        for i, (texto, destino) in enumerate(opcoes.items()):
                            if cols[i].button(texto, key=f"btn_{i}"):
                                # Verificação de Destino
                                if str(destino) in fluxo:
                                    # LOG PARA BI (Enviando tema para métricas)
                                    supabase.table("logs").insert({
                                        "tema": tema_selecionado,
                                        "pergunta": atual['pergunta'],
                                        "escolha": texto
                                    }).execute()
                                    
                                    st.session_state.step = str(destino)
                                    st.rerun()
                                else:
                                    st.session_state.erro_dest = f"ID '{destino}' não existe neste arquivo."
                    
                    # Alerta de erro de destino
                    if 'erro_dest' in st.session_state:
                        st.markdown(f"<div class='error-card'>⚠️ Erro na Planilha: {st.session_state.erro_dest}</div>", unsafe_allow_html=True)
                        if st.button("Voltar ao início"):
                            del st.session_state.erro_dest
                            st.session_state.step = str(res.data[0]['id'])
                            st.rerun()

                    st.divider()
                    if st.button("⬅️ Reiniciar Fluxo"):
                        st.session_state.step = str(res.data[0]['id'])
                        if 'erro_dest' in st.session_state: del st.session_state.erro_dest
                        st.rerun()

with tab2:
    st.subheader("🔐 Gestão Administrativa")
    senha = st.text_input("Senha", type="password")
    
    if senha == admin_pw:
        st.write("### 📤 Importar CSV")
        col_t, col_f = st.columns([1, 1])
        with col_t:
            n_tema = st.text_input("Nome do Tema")
        with col_f:
            arq = st.file_uploader("Upload", type=["csv"])
        
        if arq and n_tema and st.button("Salvar Guia"):
            try:
                df = pd.read_csv(arq, sep=None, engine='python').fillna("")
                supabase.table("fluxos").delete().eq("tema", n_tema).execute()
                for _, row in df.iterrows():
                    opts = {}
                    for i in range(2, len(df.columns), 2):
                        b_txt = str(row.iloc[i]).strip()
                        b_dest = str(row.iloc[i+1]).strip()
                        if b_txt and b_dest: opts[b_txt] = b_dest
                    
                    supabase.table("fluxos").insert({
                        "id": str(row['id']), "pergunta": str(row['pergunta']),
                        "tema": n_tema, "opcoes": opts
                    }).execute()
                st.success(f"'{n_tema}' atualizado!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

        st.divider()
        st.write("### 📂 Temas Ativos")
        res_g = supabase.table("fluxos").select("tema").execute()
        temas_g = sorted(list(set([item['tema'] for item in res_g.data]))) if res_g.data else []
        for t in temas_g:
            c1, c2 = st.columns([4, 1])
            c1.write(f"📁 {t}")
            if c2.button("Eliminar", key=f"del_{t}"):
                supabase.table("fluxos").delete().eq("tema", t).execute()
                st.rerun()

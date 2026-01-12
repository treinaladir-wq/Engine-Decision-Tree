import streamlit as st
import pandas as pd
from supabase import create_client
import json

# --- 1. CONFIGURAÇÃO DE DESIGN ---
st.set_page_config(page_title="Portal de Apoio ao Atendimento", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #262730; color: white; border: 1px solid #4B4B4B; }
    .stButton>button:hover { border-color: #00FFAA; color: #00FFAA; }
    .instruction-card { background-color: #161B22; padding: 25px; border-radius: 12px; border: 1px solid #30363D; text-align: center; margin-bottom: 20px; }
    .tag-card { background-color: #1c2128; padding: 15px; border-radius: 8px; border-left: 5px solid #00FFAA; margin-bottom: 10px; }
    .error-card { background-color: #442222; padding: 15px; border-radius: 10px; border: 1px solid #FF4B4B; text-align: center; color: white; margin-bottom: 15px; }
    h1, h2, h3, p, label { color: #F5F5F5 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    admin_pw = st.secrets["ADMIN_PASSWORD"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Erro nas credenciais. Verifique os Secrets do Streamlit.")

# --- 3. INTERFACE PRINCIPAL ---
st.title("📂 Sistema de Apoio e Procedimentos")
tab_fluxo, tab_tags, tab_gestao = st.tabs(["🎮 Fluxogramas", "🏷️ Book de Tags", "⚙️ Gestão"])

# --- ABA 1: FLUXOGRAMAS (DECISION TREE) ---
with tab_fluxo:
    res_temas = supabase.table("fluxos").select("tema").execute()
    todos_temas = sorted(list(set([item['tema'] for item in res_temas.data]))) if res_temas.data else []

    if not todos_temas:
        st.info("Nenhum fluxograma disponível. Use a aba Gestão.")
    else:
        search_query = st.text_input("🔍 Pesquisar guia (ex: Motor, Garantia...)", "").lower()
        temas_filtrados = [t for t in todos_temas if search_query in t.lower()]
        
        if temas_filtrados:
            tema_selecionado = st.selectbox("Selecione o Fluxograma:", temas_filtrados)
            
            # Busca dados do tema
            res = supabase.table("fluxos").select("*").eq("tema", tema_selecionado).execute()
            if res.data:
                fluxo = {str(item['id']): item for item in res.data}
                
                if 'step' not in st.session_state or st.session_state.get('last_tema') != tema_selecionado:
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
                                if str(destino) in fluxo:
                                    st.session_state.step = str(destino)
                                    st.rerun()
                                else:
                                    st.session_state.erro_dest = f"ID '{destino}' inexistente."
                    
                    if st.button("⬅️ Reiniciar Fluxo"):
                        st.session_state.step = str(res.data[0]['id'])
                        st.rerun()

# --- ABA 2: BOOK DE TAGS ---
with tab_tags:
    st.header("🏷️ Consulta de Tags")
    busca_tag = st.text_input("Pesquisar por Tag ou Tema:").lower()
    
    # Busca na tabela book_tags do Supabase
    res_tags = supabase.table("book_tags").select("*").execute()
    
    if res_tags.data:
        df_tags = pd.DataFrame(res_tags.data)
        if busca_tag:
            # Filtra por TAG ou Tema (mas o usuário só vê TAG, Time e Resumo)
            filtro = df_tags[
                df_tags['TAG'].str.lower().str.contains(busca_tag, na=False) | 
                df_tags['Tema'].str.lower().str.contains(busca_tag, na=False)
            ]
            
            if not filtro.empty:
                for _, row in filtro.iterrows():
                    with st.container():
                        st.markdown(f"""
                        <div class='tag-card'>
                            <strong>TAG:</strong> {row['TAG']} <br>
                            <strong>TIME:</strong> {row['Time']} <br>
                            <p style='margin-top:10px;'>{row['Resumo']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.button(f"Copiar {row['TAG']}", key=f"copy_{row['TAG']}", on_click=lambda t=row['TAG']: st.write(f"Copiado: {t}"))
            else:
                st.warning("Nenhuma tag encontrada.")
    else:
        st.info("O Book de Tags está vazio. Vá em Gestão e suba o arquivo.")

# --- ABA 3: GESTÃO (ATUALIZAÇÃO DE BASES) ---
with tab_gestao:
    st.subheader("🔐 Área Administrativa")
    senha = st.text_input("Senha de Acesso", type="password")
    
    if senha == admin_pw:
        st.divider()
        
        # --- UPLOAD BOOK DE TAGS ---
        st.write("### 📤 Atualizar Book de Tags")
        st.info("O arquivo deve conter as colunas: TAG, Tema, Time, Resumo")
        arq_tag = st.file_uploader("Arquivo CSV/Excel das Tags", type=["csv", "xlsx"])
        
        if arq_tag and st.button("Salvar Novo Book de Tags"):
            try:
                df_new = pd.read_csv(arq_tag) if arq_tag.name.endswith('.csv') else pd.read_excel(arq_tag)
                # Limpa e Insere
                supabase.table("book_tags").delete().neq("TAG", "000").execute()
                supabase.table("book_tags").insert(df_new.to_dict(orient='records')).execute()
                st.success("Book de Tags atualizado com sucesso!")
            except Exception as e:
                st.error(f"Erro no upload: {e}")

        st.divider()
        
        # --- UPLOAD FLUXOGRAMA ---
        st.write("### 📤 Novo Fluxograma")
        n_tema = st.text_input("Nome do Tema (ex: Mecânica)")
        arq_fluxo = st.file_uploader("Arquivo CSV do Fluxo", type=["csv"])
        
        if arq_fluxo and n_tema and st.button("Salvar Fluxograma"):
            try:
                df = pd.read_csv(arq_fluxo, sep=None, engine='python').fillna("")
                supabase.table("fluxos").delete().eq("tema", n_tema).execute()
                for _, row in df.iterrows():
                    opts = {}
                    for i in range(2, len(df.columns), 2):
                        b_txt, b_dest = str(row.iloc[i]).strip(), str(row.iloc[i+1]).strip()
                        if b_txt and b_dest: opts[b_txt] = b_dest
                    supabase.table("fluxos").insert({"id": str(row['id']), "pergunta": str(row['pergunta']), "tema": n_tema, "opcoes": opts}).execute()
                st.success(f"Fluxo '{n_tema}' atualizado!")
            except Exception as e:
                st.error(f"Erro: {e}")

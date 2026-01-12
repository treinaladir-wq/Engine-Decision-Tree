import streamlit as st
import pandas as pd
from supabase import create_client
import json

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="Portal de Apoio ao Atendimento", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #262730; color: white; border: 1px solid #4B4B4B; }
    .stButton>button:hover { border-color: #00FFAA; color: #00FFAA; }
    .instruction-card { background-color: #161B22; padding: 25px; border-radius: 12px; border: 1px solid #30363D; text-align: center; margin-bottom: 20px; }
    .tag-card { background-color: #1c2128; padding: 15px; border-radius: 8px; border-left: 5px solid #00FFAA; margin-bottom: 10px; }
    h1, h2, h3, p, label { color: #F5F5F5 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES (SUPABASE) ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    admin_pw = st.secrets["ADMIN_PASSWORD"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Erro nas credenciais do Supabase. Verifique os Secrets.")

# --- 3. NAVEGAÇÃO POR ABAS ---
tab_fluxo, tab_tags, tab_n2, tab_gestao = st.tabs(["🎮 Fluxogramas", "🏷️ Tags CRM", "🚀 Book N2", "⚙️ Gestão"])

# --- ABA 1: FLUXOGRAMAS ---
with tab_fluxo:
    res_temas = supabase.table("fluxos").select("tema").execute()
    todos_temas = sorted(list(set([item['tema'] for item in res_temas.data]))) if res_temas.data else []

    if not todos_temas:
        st.info("Nenhum fluxograma disponível. Use a aba Gestão para subir um CSV.")
    else:
        busca_fluxo = st.text_input("🔍 Pesquisar guia:", "").lower()
        temas_filtrados = [t for t in todos_temas if busca_fluxo in t.lower()]
        
        if temas_filtrados:
            tema_selecionado = st.selectbox("Selecione o Fluxograma:", temas_filtrados)
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
                                st.session_state.step = str(destino)
                                st.rerun()
                    if st.button("⬅️ Reiniciar Fluxo"):
                        st.session_state.step = str(res.data[0]['id'])
                        st.rerun()

# --- ABA 2: BOOK DE TAGS ---
with tab_tags:
    st.header("🏷️ Consulta de Tags CRM")
    busca_tag = st.text_input("Pesquise por Tag ou Tema:", key="search_tags").lower()
    res_t = supabase.table("book_tags").select("*").execute()
    if res_t.data:
        df_tags = pd.DataFrame(res_t.data)
        if busca_tag:
            filt = df_tags[df_tags['TAG'].str.lower().str.contains(busca_tag, na=False) | 
                           df_tags['Tema'].str.lower().str.contains(busca_tag, na=False)]
            for _, row in filt.iterrows():
                st.markdown(f"<div class='tag-card'><strong>TAG:</strong> {row['TAG']} | <strong>TIME:</strong> {row['Time']}<br>{row['Resumo']}</div>", unsafe_allow_html=True)
                st.code(row['TAG'], language="text")

# --- ABA 3: BOOK N2 ---
with tab_n2:
    st.header("🚀 Book N2 / Escalonamento")
    busca_n2 = st.text_input("Pesquise por Tag, Resumo ou Orientação:", key="search_n2").lower()
    res_n = supabase.table("book_n2").select("*").execute()
    if res_n.data:
        df_n2 = pd.DataFrame(res_n.data)
        if busca_n2:
            filt_n2 = df_n2[
                df_n2['Tag'].str.lower().str.contains(busca_n2, na=False) | 
                df_n2['Resumo'].str.lower().str.contains(busca_n2, na=False) |
                df_n2['Orientação completa'].str.lower().str.contains(busca_n2, na=False)
            ]
            for _, row in filt_n2.iterrows():
                with st.expander(f"📌 Tag: {row['Tag']} | N2: {row['N2 / Não Resolvido']}"):
                    st.markdown(f"**Resumo:** {row['Resumo']}")
                    st.markdown(f"**Orientação Completa:**\n{row['Orientação completa']}")
                    st.markdown(f"**Fonte:** {row['Fonte']}")
                    st.code(row['Tag'], language="text")

# --- ABA 4: GESTÃO (COM CORREÇÃO DE CÉLULAS VAZIAS) ---
with tab_gestao:
    st.subheader("🔐 Painel de Controle")
    senha = st.text_input("Senha de Acesso", type="password")
    
    if senha == admin_pw:
        st.divider()
        modo_upload = st.radio("Selecione o que deseja atualizar:", ["Tags CRM", "Book N2", "Novo Fluxograma"])
        
        if modo_upload == "Tags CRM":
            arq = st.file_uploader("Suba a planilha de Tags", type=["csv", "xlsx"])
            if arq and st.button("Salvar Tags"):
                try:
                    df = pd.read_csv(arq) if arq.name.endswith('.csv') else pd.read_excel(arq)
                    df = df.fillna("") # CORREÇÃO: Remove valores nulos (NaN)
                    df.columns = [c.strip() for c in df.columns]
                    supabase.table("book_tags").delete().neq("id", -1).execute()
                    supabase.table("book_tags").insert(df.to_dict(orient='records')).execute()
                    st.success("Base de Tags atualizada!")
                except Exception as e: st.error(f"Erro: {e}")

        elif modo_upload == "Book N2":
            arq = st.file_uploader("Suba a planilha de N2", type=["csv", "xlsx"])
            if arq and st.button("Salvar N2"):
                try:
                    df = pd.read_csv(arq) if arq.name.endswith('.csv') else pd.read_excel(arq)
                    df = df.fillna("") # CORREÇÃO: Remove valores nulos (NaN)
                    df.columns = [c.strip() for c in df.columns]
                    supabase.table("book_n2").delete().neq("id", -1).execute()
                    supabase.table("book_n2").insert(df.to_dict(orient='records')).execute()
                    st.success("Base N2 atualizada!")
                except Exception as e: st.error(f"Erro: {e}")

        elif modo_upload == "Novo Fluxograma":
            nome_tema = st.text_input("Nome do Tema")
            arq = st.file_uploader("Suba o CSV do Fluxo", type=["csv"])
            if arq and nome_tema and st.button("Salvar Fluxo"):
                try:
                    df = pd.read_csv(arq, sep=None, engine='python').fillna("") # CORREÇÃO: fillna aqui também
                    supabase.table("fluxos").delete().eq("tema", nome_tema).execute()
                    for _, row in df.iterrows():
                        opts = {}
                        for i in range(2, len(df.columns), 2):
                            txt, dest = str(row.iloc[i]).strip(), str(row.iloc[i+1]).strip()
                            if txt and dest: opts[txt] = dest
                        supabase.table("fluxos").insert({"id": str(row['id']), "pergunta": str(row['pergunta']), "tema": nome_tema, "opcoes": opts}).execute()
                    st.success(f"Fluxograma '{nome_tema}' disponível!")
                except Exception as e: st.error(f"Erro: {e}")

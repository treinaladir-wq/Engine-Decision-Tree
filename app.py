import streamlit as st
import pandas as pd
from supabase import create_client
import json

# --- 1. CONFIGURAÇÃO DE DESIGN ---
st.set_page_config(page_title="Atendimento Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #262730; color: white; border: 1px solid #4B4B4B; }
    .stButton>button:hover { border-color: #FF4B4B; color: #FF4B4B; }
    .instruction-card { background-color: #161B22; padding: 25px; border-radius: 12px; border: 1px solid #30363D; text-align: center; margin-bottom: 20px; }
    .error-card { background-color: #442222; padding: 15px; border-radius: 10px; border: 1px solid #FF4B4B; text-align: center; color: white; }
    h1, h2, h3, p, label { color: #F5F5F5 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
admin_pw = st.secrets["ADMIN_PASSWORD"]
supabase = create_client(url, key)

# --- 3. INTERFACE ---
st.title("📂 Sistema de Apoio ao Atendimento")
tab1, tab2 = st.tabs(["🎮 Navegação", "⚙️ Gestão de Temas"])

with tab1:
    res_temas = supabase.table("fluxos").select("tema").execute()
    todos_temas = sorted(list(set([item['tema'] for item in res_temas.data]))) if res_temas.data else []

    if not todos_temas:
        st.info("Nenhum guia disponível. Vá na aba Gestão.")
    else:
        tema_selecionado = st.selectbox("Selecione o Guia:", todos_temas)
        
        # Busca apenas os dados do tema selecionado
        res = supabase.table("fluxos").select("*").eq("tema", tema_selecionado).execute()
        
        if res.data:
            # Criamos o dicionário do fluxo LOCAL para este tema
            fluxo = {str(item['id']): item for item in res.data}
            
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
                        if cols[i].button(texto, key=f"nav_{i}"):
                            # --- VERIFICAÇÃO DE ERRO: O DESTINO EXISTE? ---
                            if str(destino) in fluxo:
                                # Log para BI
                                supabase.table("logs").insert({
                                    "no_nome": f"[{tema_selecionado}] {atual['pergunta']}", 
                                    "escolha": texto
                                }).execute()
                                
                                st.session_state.step = str(destino)
                                st.rerun()
                            else:
                                st.session_state.erro_destino = f"O destino '{destino}' não foi encontrado neste fluxograma."
                
                # Exibe erro se o destino não existir
                if 'erro_destino' in st.session_state:
                    st.markdown(f"<div class='error-card'>⚠️ {st.session_state.erro_destino}</div>", unsafe_allow_html=True)
                    if st.button("Tentar outro caminho"):
                        del st.session_state.erro_destino
                        st.rerun()

                st.divider()
                if st.button("⬅️ Reiniciar"):
                    st.session_state.step = str(res.data[0]['id'])
                    if 'erro_destino' in st.session_state: del st.session_state.erro_destino
                    st.rerun()

with tab2:
    st.subheader("🔐 Painel Administrativo")
    senha = st.text_input("Senha", type="password")
    
    if senha == admin_pw:
        st.write("### 📤 Importar/Atualizar Fluxo")
        novo_tema = st.text_input("Nome do Tema")
        arquivo_csv = st.file_uploader("Arquivo CSV", type=["csv"])
        
        if arquivo_csv and novo_tema:
            if st.button(f"Salvar '{novo_tema}'"):
                try:
                    df = pd.read_csv(arquivo_csv, sep=None, engine='python').fillna("")
                    
                    # 1. Remove apenas o tema antigo (evita conflito de IDs entre temas)
                    supabase.table("fluxos").delete().eq("tema", novo_tema).execute()
                    
                    # 2. Insere os novos dados
                    for _, row in df.iterrows():
                        dict_opcoes = {}
                        for i in range(2, len(df.columns), 2):
                            nome = str(row.iloc[i]).strip()
                            dest = str(row.iloc[i+1]).strip()
                            if nome and dest: dict_opcoes[nome] = dest

                        # Usamos insert porque já deletamos o tema acima
                        supabase.table("fluxos").insert({
                            "id": str(row['id']),
                            "pergunta": str(row['pergunta']),
                            "tema": str(novo_tema),
                            "opcoes": dict_opcoes
                        }).execute()
                    
                    st.success(f"✅ Tema '{novo_tema}' atualizado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

        st.divider()
        st.write("### 📂 Gerenciar Temas")
        res_g = supabase.table("fluxos").select("tema").execute()
        temas = sorted(list(set([item['tema'] for item in res_g.data]))) if res_g.data else []
        for t in temas:
            c1, c2 = st.columns([4, 1])
            c1.write(f"📁 {t}")
            if c2.button("Excluir", key=f"del_{t}"):
                supabase.table("fluxos").delete().eq("tema", t).execute()
                st.rerun()

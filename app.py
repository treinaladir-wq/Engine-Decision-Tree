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
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    admin_pw = st.secrets["ADMIN_PASSWORD"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"Erro ao carregar configurações: {e}")
    st.stop()

# --- 3. INTERFACE ---
st.title("📂 Sistema de Apoio ao Atendimento")
tab1, tab2 = st.tabs(["🎮 Navegação", "⚙️ Painel de Gestão"])

with tab1:
    try:
        # Busca temas únicos
        res_temas = supabase.table("fluxos").select("tema").execute()
        todos_temas = sorted(list(set([item['tema'] for item in res_temas.data]))) if res_temas.data else []

        if not todos_temas:
            st.info("Nenhum guia disponível. Vá na aba Gestão e suba um CSV.")
        else:
            tema_selecionado = st.selectbox("Selecione o Guia:", todos_temas)
            
            # Busca dados do tema
            res = supabase.table("fluxos").select("*").eq("tema", tema_selecionado).execute()
            
            if res.data:
                fluxo = {str(item['id']): item for item in res.data}
                
                # Resetar passo se mudar o tema
                if 'last_tema' not in st.session_state or st.session_state.last_tema != tema_selecionado:
                    st.session_state.step = str(res.data[0]['id'])
                    st.session_state.last_tema = tema_selecionado
                
                atual = fluxo.get(st.session_state.step)
                
                if atual:
                    st.markdown(f"<div class='instruction-card'><h3>{tema_selecionado}</h3><h2>{atual['pergunta']}</h2></div>", unsafe_allow_html=True)
                    
                    opcoes = atual.get('opcoes', {})
                    if isinstance(opcoes, str):
                        opcoes = json.loads(opcoes)
                    
                    if opcoes:
                        cols = st.columns(len(opcoes))
                        for i, (texto, destino) in enumerate(opcoes.items()):
                            if cols[i].button(texto, key=f"nav_{i}"):
                                # Registro de Log para BI
                                try:
                                    supabase.table("logs").insert({
                                        "no_nome": f"[{tema_selecionado}] {atual['pergunta']}", 
                                        "escolha": texto
                                    }).execute()
                                except: pass # Se der erro no log, não trava o app
                                
                                st.session_state.step = str(destino)
                                st.rerun()
                    
                    st.divider()
                    if st.button("⬅️ Reiniciar este Guia"):
                        st.session_state.step = str(res.data[0]['id'])
                        st.rerun()
    except Exception as e:
        st.error(f"Erro ao carregar fluxo: {e}")

with tab2:
    st.subheader("🔐 Gestão do Sistema")
    senha = st.text_input("Senha", type="password")
    
    if senha == admin_pw:
        st.write("### 📤 Importar Novo Fluxo")
        novo_tema = st.text_input("Nome do Tema (Ex: Ar-Condicionado)")
        arquivo_csv = st.file_uploader("Arquivo CSV", type=["csv"])
        
        if arquivo_csv and novo_tema:
            if st.button(f"Salvar/Atualizar '{novo_tema}'"):
                try:
                    df = pd.read_csv(arquivo_csv, sep=None, engine='python').fillna("") # Auto-detecta separador (, ou ;)
                    
                    with st.spinner("Limpando versão antiga e salvando nova..."):
                        # 1. Apaga registros antigos deste tema
                        supabase.table("fluxos").delete().eq("tema", novo_tema).execute()
                        
                        # 2. Insere novos registros
                        for _, row in df.iterrows():
                            dict_opcoes = {}
                            # Captura pares de colunas (Botão e Destino)
                            for i in range(2, len(df.columns), 2):
                                try:
                                    nome_botao = str(row.iloc[i]).strip()
                                    destino = str(row.iloc[i+1]).strip()
                                    if nome_botao and destino:
                                        dict_opcoes[nome_botao] = destino
                                except:
                                    continue # Pula se a coluna estiver incompleta

                            dados_insercao = {
                                "id": str(row['id']),
                                "pergunta": str(row['pergunta']),
                                "tema": str(novo_tema),
                                "opcoes": dict_opcoes # Envia como dicionário para coluna JSONB
                            }
                            
                            supabase.table("fluxos").insert(dados_insercao).execute()
                    
                    st.success(f"✅ Tema '{novo_tema}' atualizado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar no banco de dados!")
                    st.code(f"Detalhes técnicos: {str(e)}")
                    st.info("Verifique se as colunas 'id', 'pergunta', 'tema' (TEXT) e 'opcoes' (JSONB) existem no Supabase.")

        st.divider()
        st.write("### 📂 Gerenciar Temas Existentes")
        res_gestao = supabase.table("fluxos").select("tema").execute()
        temas_existentes = sorted(list(set([item['tema'] for item in res_gestao.data]))) if res_gestao.data else []
        
        if temas_existentes:
            for t in temas_existentes:
                c1, c2 = st.columns([4, 1])
                c1.write(f"📁 **{t}**")
                if c2.button("Excluir", key=f"del_{t}"):
                    supabase.table("fluxos").delete().eq("tema", t).execute()
                    st.rerun()
        else:
            st.write("Nenhum guia encontrado no banco.")

        st.divider()
        if st.button("🗑️ Limpar Todos os Logs de BI"):
            supabase.table("logs").delete().neq("id", 0).execute()
            st.success("Histórico apagado.")

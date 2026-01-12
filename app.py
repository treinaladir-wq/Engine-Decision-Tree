import streamlit as st
import pandas as pd
from supabase import create_client
import json
from datetime import datetime
import io

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="Portal CNX - Apoio ao Atendimento", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    
    /* Botões do Hub */
    .stButton>button { width: 100%; border-radius: 12px; height: 4.5em; background-color: #161B22; color: white; border: 1px solid #30363D; font-size: 18px; transition: 0.3s; }
    .stButton>button:hover { border-color: #00FFAA; color: #00FFAA; background-color: #1c2128; transform: translateY(-2px); }
    
    /* Cards e Containers */
    .login-box { background-color: #161B22; padding: 40px; border-radius: 15px; border: 1px solid #30363D; text-align: center; max-width: 500px; margin: auto; }
    .hub-card { background-color: #1c2128; padding: 25px; border-radius: 12px; text-align: center; border: 1px solid #30363D; margin-bottom: 15px; min-height: 180px; }
    .instruction-card { background-color: #161B22; padding: 25px; border-radius: 12px; border: 1px solid #30363D; text-align: center; margin-bottom: 20px; }
    
    /* Tags e N2 Cards */
    .tag-card { background-color: #1c2128; padding: 15px; border-radius: 8px; border-left: 5px solid #00FFAA; margin-bottom: 10px; }
    .n2-card { background-color: #1c2128; padding: 15px; border-radius: 8px; border-left: 5px solid #FF4B4B; margin-bottom: 10px; }
    
    h1, h2, h3 { text-align: center; color: #F5F5F5 !important; }
    label { color: #F5F5F5 !important; }
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
    st.stop()

# --- 3. FUNÇÕES DE APOIO ---
def registrar_log(termo, aba):
    if termo and len(termo) > 2:
        email = st.session_state.get('user_email', 'n/a')
        try:
            supabase.table("logs_pesquisa").insert({
                "usuario_email": email, 
                "termo_pesquisado": termo, 
                "aba_utilizada": aba
            }).execute()
        except:
            pass

# --- 4. ESTADO DA SESSÃO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = "Hub"

# --- 5. TELA DE LOGIN ---
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.title("🛡️ Portal CNX")
    st.write("Identifique-se para acessar as ferramentas de apoio.")
    email_input = st.text_input("E-mail corporativo:", placeholder="exemplo@empresa.com")
    if st.button("Entrar no Sistema"):
        if "@" in email_input and "." in email_input:
            st.session_state.user_email = email_input
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Por favor, insira um e-mail válido.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 6. HEADER E LOGOUT (Sidebar) ---
with st.sidebar:
    st.markdown(f"👤 **Logado como:**\n`{st.session_state.user_email}`")
    st.divider()
    if st.button("🚪 Sair / Trocar Usuário"):
        st.session_state.logged_in = False
        st.session_state.pagina_atual = "Hub"
        st.rerun()

# --- 7. NAVEGAÇÃO (HUB OU PÁGINAS) ---

# --- TELA INICIAL (HUB) ---
if st.session_state.pagina_atual == "Hub":
    st.markdown("<h1 style='font-size: 40px;'>Central de Apoio CNX</h1>", unsafe_allow_html=True)
    st.markdown("<h3>Selecione a ferramenta de consulta</h3><br>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='hub-card'><h2>🎮</h2><h3>Guias</h3><p>Fluxogramas interativos para tomada de decisão.</p></div>", unsafe_allow_html=True)
        if st.button("Acessar Fluxos"):
            st.session_state.pagina_atual = "Fluxos"
            st.rerun()
    with c2:
        st.markdown("<div class='hub-card'><h2>🏷️</h2><h3>Tags</h3><p>Pesquisa rápida de TAGS e Temas do CRM.</p></div>", unsafe_allow_html=True)
        if st.button("Consultar Tags"):
            st.session_state.pagina_atual = "Tags"
            st.rerun()
    with c3:
        st.markdown("<div class='hub-card'><h2>🚀</h2><h3>N2</h3><p>Orientação técnica e regras de escalonamento.</p></div>", unsafe_allow_html=True)
        if st.button("Consultar N2"):
            st.session_state.pagina_atual = "N2"
            st.rerun()

    st.markdown("<br><br><br><hr>", unsafe_allow_html=True)
    if st.button("⚙️ Painel de Gestão (Administrativo)"):
        st.session_state.pagina_atual = "Gestao"
        st.rerun()

# --- PÁGINA: FLUXOGRAMAS ---
elif st.session_state.pagina_atual == "Fluxos":
    if st.button("⬅️ Voltar ao Menu"): st.session_state.pagina_atual = "Hub"; st.rerun()
    st.header("🎮 Fluxogramas de Atendimento")
    
    res_temas = supabase.table("fluxos").select("tema").execute()
    todos_temas = sorted(list(set([item['tema'] for item in res_temas.data]))) if res_temas.data else []
    
    if todos_temas:
        tema_sel = st.selectbox("Escolha um guia:", todos_temas)
        res = supabase.table("fluxos").select("*").eq("tema", tema_sel).execute()
        if res.data:
            fluxo = {str(item['id']): item for item in res.data}
            if 'step' not in st.session_state or st.session_state.get('last_tema') != tema_sel:
                st.session_state.step = str(res.data[0]['id'])
                st.session_state.last_tema = tema_sel
            
            atual = fluxo.get(st.session_state.step)
            if atual:
                st.markdown(f"<div class='instruction-card'><h2>{atual['pergunta']}</h2></div>", unsafe_allow_html=True)
                opts = atual.get('opcoes', {})
                if isinstance(opts, str): opts = json.loads(opts)
                cols = st.columns(len(opts)) if opts else [st.container()]
                for i, (texto, destino) in enumerate(opts.items()):
                    if cols[i].button(texto, key=f"f_{i}"):
                        st.session_state.step = str(destino); st.rerun()
                if st.button("🔄 Reiniciar Guia"):
                    st.session_state.step = str(res.data[0]['id']); st.rerun()

# --- PÁGINA: TAGS CRM ---
elif st.session_state.pagina_atual == "Tags":
    if st.button("⬅️ Voltar ao Menu"): st.session_state.pagina_atual = "Hub"; st.rerun()
    st.header("🏷️ Consulta de Tags CRM")
    busca_tag = st.text_input("Busca por Tag ou Tema (Ex: Estorno):").lower()
    
    if busca_tag:
        registrar_log(busca_tag, "Tags")
        res_t = supabase.table("book_tags").select("*").execute()
        if res_t.data:
            df = pd.DataFrame(res_t.data)
            filt = df[df['TAG'].str.lower().str.contains(busca_tag, na=False) | df['Tema'].str.lower().str.contains(busca_tag, na=False)]
            for _, r in filt.iterrows():
                st.markdown(f"<div class='tag-card'><strong>{r['TAG']}</strong> | {r['Time']}<br>{r['Resumo']}</div>", unsafe_allow_html=True)
                st.code(r['TAG'], language="text")

# --- PÁGINA: BOOK N2 ---
elif st.session_state.pagina_atual == "N2":
    if st.button("⬅️ Voltar ao Menu"): st.session_state.pagina_atual = "Hub"; st.rerun()
    st.header("🚀 Book N2 / Escalonamento")
    busca_n2 = st.text_input("Busca por Tag, Resumo ou Orientação:").lower()
    
    if busca_n2:
        registrar_log(busca_n2, "N2")
        res_n = supabase.table("book_n2").select("*").execute()
        if res_n.data:
            dfn = pd.DataFrame(res_n.data)
            filt_n = dfn[dfn['Tag'].str.lower().str.contains(busca_n2, na=False) | 
                         dfn['Resumo'].str.lower().str.contains(busca_n2, na=False) |
                         dfn['Orientação completa'].str.lower().str.contains(busca_n2, na=False)]
            for _, r in filt_n.iterrows():
                with st.expander(f"📌 Tag: {r['Tag']} | N2: {r['N2 / Não Resolvido']}"):
                    st.write(f"**Orientação:** {r['Orientação completa']}")
                    st.caption(f"Fonte: {r['Fonte']}")
                    st.code(r['Tag'], language="text")

# --- PÁGINA: GESTÃO ---
elif st.session_state.pagina_atual == "Gestao":
    if st.button("⬅️ Voltar ao Menu"): st.session_state.pagina_atual = "Hub"; st.rerun()
    st.header("⚙️ Painel de Gestão")
    
    if st.text_input("Senha Admin", type="password") == admin_pw:
        m_admin = st.selectbox("Ação:", ["Logs de Pesquisa", "Atualizar Bases"])
        
        if m_admin == "Logs de Pesquisa":
            res_l = supabase.table("logs_pesquisa").select("*").order("data_hora", desc=True).limit(1000).execute()
            if res_l.data:
                df_l = pd.DataFrame(res_l.data)
                st.dataframe(df_l, use_container_width=True)
                
                # Exportar Excel
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as ex:
                    df_l.to_excel(ex, index=False)
                st.download_button("📥 Baixar Relatório (Excel)", data=buf.getvalue(), file_name="logs_atendimento.xlsx")
        
        elif m_admin == "Atualizar Bases":
            tipo = st.radio("Base:", ["Tags CRM", "Book N2"])
            arq = st.file_uploader("Suba o arquivo (CSV/Excel)", type=["csv", "xlsx"])
            if arq and st.button("Confirmar Upload"):
                df_up = pd.read_csv(arq) if arq.name.endswith('.csv') else pd.read_excel(arq)
                tabela = "book_tags" if tipo == "Tags CRM" else "book_n2"
                supabase.table(tabela).delete().neq("id", -1).execute()
                supabase.table(tabela).insert(df_up.to_dict(orient='records')).execute()
                st.success("Base atualizada com sucesso!")

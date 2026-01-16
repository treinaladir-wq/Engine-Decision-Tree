import streamlit as st
import pandas as pd
from supabase import create_client
import json
from datetime import datetime
import io
import plotly.express as px

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="Portal CNX - Inteligência e Apoio", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton>button { width: 100%; border-radius: 12px; height: 4.5em; background-color: #161B22; color: white; border: 1px solid #30363D; font-size: 18px; transition: 0.3s; }
    .stButton>button:hover { border-color: #00FFAA !important; color: #00FFAA !important; background-color: #1c2128; transform: translateY(-2px); }
    .login-box { background-color: #161B22; padding: 40px; border-radius: 15px; border: 1px solid #30363D; text-align: center; max-width: 500px; margin: auto; }
    .hub-card { background-color: #1c2128; padding: 25px; border-radius: 12px; text-align: center; border: 1px solid #30363D; margin-bottom: 5px; min-height: 150px; }
    .instruction-card { background-color: #161B22; padding: 25px; border-radius: 12px; border: 1px solid #30363D; text-align: center; margin-bottom: 20px; }
    .tag-card { background-color: #1c2128; padding: 15px; border-radius: 8px; border-left: 5px solid #00FFAA; margin-bottom: 10px; }
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
    st.error("Erro nas credenciais do Supabase.")
    st.stop()

# --- 3. FUNÇÕES DE APOIO ---
def registrar_log(termo, aba):
    if termo and len(str(termo)) > 1:
        email = st.session_state.get('user_email', 'n/a')
        try:
            supabase.table("logs_pesquisa").insert({
                "usuario_email": email, "termo_pesquisado": termo, "aba_utilizada": aba
            }).execute()
        except: pass

# --- 4. ESTADO DA SESSÃO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = "Hub"

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
            st.error("Insira um e-mail válido.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.markdown(f"👤 **Usuário:**\n`{st.session_state.user_email}`")
    st.divider()
    if st.button("🚪 Sair"):
        st.session_state.logged_in = False
        st.session_state.pagina_atual = "Hub"
        st.rerun()

# --- 7. NAVEGAÇÃO ---

if st.session_state.pagina_atual == "Hub":
    st.markdown("<h1 style='font-size: 40px;'>Central de Apoio CNX</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='hub-card'><h2>🎮</h2><h3>Guias</h3></div>", unsafe_allow_html=True)
        if st.button("Abrir Fluxogramas"): st.session_state.pagina_atual = "Fluxos"; st.rerun()
    with c2:
        st.markdown("<div class='hub-card'><h2>🏷️</h2><h3>Tags</h3></div>", unsafe_allow_html=True)
        if st.button("Abrir Book de Tags"): st.session_state.pagina_atual = "Tags"; st.rerun()
    with c3:
        st.markdown("<div class='hub-card'><h2>🚀</h2><h3>N2</h3></div>", unsafe_allow_html=True)
        if st.button("Abrir Book N2"): st.session_state.pagina_atual = "N2"; st.rerun()
    st.markdown("<br><hr>", unsafe_allow_html=True)
    if st.button("⚙️ Painel de Gestão e BI"): st.session_state.pagina_atual = "Gestao"; st.rerun()

elif st.session_state.pagina_atual == "Fluxos":
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    res_temas = supabase.table("fluxos").select("tema").execute()
    todos_temas = sorted(list(set([item['tema'] for item in res_temas.data]))) if res_temas.data else []
    if todos_temas:
        tema_sel = st.selectbox("Escolha um tema:", todos_temas)
        res = supabase.table("fluxos").select("*").eq("tema", tema_sel).execute()
        if res.data:
            fluxo = {str(item['id']): item for item in res.data}
            if 'step' not in st.session_state or st.session_state.get('last_tema') != tema_sel:
                st.session_state.step = str(res.data[0]['id']); st.session_state.last_tema = tema_sel
            atual = fluxo.get(st.session_state.step)
            if atual:
                st.markdown(f"<div class='instruction-card'><h2>{atual['pergunta']}</h2></div>", unsafe_allow_html=True)
                opts = atual.get('opcoes', {})
                if isinstance(opts, str): opts = json.loads(opts)
                cols = st.columns(len(opts)) if opts else [st.container()]
                for i, (texto, destino) in enumerate(opts.items()):
                    if cols[i].button(texto, key=f"f_{i}"):
                        st.session_state.step = str(destino); st.rerun()
                if st.button("🔄 Reiniciar"): st.session_state.step = str(res.data[0]['id']); st.rerun()

elif st.session_state.pagina_atual == "Tags":
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    busca_tag = st.text_input("Busca por Tag ou Tema:").lower()
    if busca_tag:
        registrar_log(busca_tag, "Tags")
        res_t = supabase.table("book_tags").select("*").execute()
        if res_t.data:
            df = pd.DataFrame(res_t.data)
            filt = df[df['TAG'].str.lower().str.contains(busca_tag, na=False) | df['Tema'].str.lower().str.contains(busca_tag, na=False)]
            for _, r in filt.iterrows():
                st.markdown(f"<div class='tag-card'><strong>{r['TAG']}</strong> | {r['Time']}<br>{r['Resumo']}</div>", unsafe_allow_html=True)
                st.code(r['TAG'], language="text")

elif st.session_state.pagina_atual == "N2":
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    busca_n2 = st.text_input("Busca Tag, Resumo ou Orientação:").lower()
    if busca_n2:
        registrar_log(busca_n2, "N2")
        res_n = supabase.table("book_n2").select("*").execute()
        if res_n.data:
            dfn = pd.DataFrame(res_n.data)
            filt_n = dfn[dfn['Tag'].str.lower().str.contains(busca_n2, na=False) | dfn['Resumo'].str.lower().str.contains(busca_n2, na=False) | dfn['Orientação completa'].str.lower().str.contains(busca_n2, na=False)]
            for _, r in filt_n.iterrows():
                with st.expander(f"📌 Tag: {r['Tag']} | N2: {r['N2 / Não Resolvido']}"):
                    st.write(f"**Orientação:** {r['Orientação completa']}")
                    st.code(r['Tag'], language="text")

elif st.session_state.pagina_atual == "Gestao":
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    if st.text_input("Senha Admin", type="password") == admin_pw:
        m_admin = st.selectbox("Ação:", ["Dashboard e Logs", "Atualizar Bases", "Gerenciar Fluxos"])
        
        if m_admin == "Dashboard e Logs":
            res_l = supabase.table("logs_pesquisa").select("*").order("data_hora", desc=True).execute()
            if res_l.data:
                df_l = pd.DataFrame(res_l.data)
                df_l['data_hora'] = pd.to_datetime(df_l['data_hora'])
                st.subheader("📊 BI - Inteligência de Busca")
                c1, c2 = st.columns(2)
                with c1:
                    st.plotly_chart(px.bar(df_l['termo_pesquisado'].value_counts().nlargest(10).reset_index(), x='count', y='termo_pesquisado', orientation='h', title="Top 10 Buscas"), use_container_width=True)
                with c2:
                    st.plotly_chart(px.pie(df_l, names='aba_utilizada', title="Uso por Categoria"), use_container_width=True)
                
                # --- EXPORTAÇÃO DETALHADA ---
                st.divider()
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_exp = df_l.copy()
                    df_exp['data_hora'] = df_exp['data_hora'].dt.strftime('%d/%m/%Y %H:%M:%S')
                    df_exp.to_excel(writer, index=False, sheet_name='Logs')
                st.download_button("📥 Baixar Relatório Detalhado (Excel)", data=output.getvalue(), file_name="logs_detalhados_cnx.xlsx")
            else: st.info("Sem logs.")

        elif m_admin == "Gerenciar Fluxos":
            res_f = supabase.table("fluxos").select("tema").execute()
            temas = sorted(list(set([item['tema'] for item in res_f.data]))) if res_f.data else []
            if temas:
                t_ex = st.selectbox("Tema para APAGAR:", temas)
                if st.checkbox(f"Confirmar exclusão de {t_ex}") and st.button("🔥 Excluir"):
                    supabase.table("fluxos").delete().eq("tema", t_ex).execute(); st.rerun()

        elif m_admin == "Atualizar Bases":
            tipo = st.radio("Base:", ["Tags CRM", "Book N2", "Fluxogramas"])
            arq = st.file_uploader("Suba o arquivo", type=["csv", "xlsx"])
            if arq and st.button("Confirmar Upload"):
                df_up = pd.read_csv(arq) if arq.name.endswith('.csv') else pd.read_excel(arq)
                if tipo == "Fluxogramas":
                    n_f = st.text_input("Nome do Tema")
                    if n_f:
                        supabase.table("fluxos").delete().eq("tema", n_f).execute()
                        for _, row in df_up.iterrows():
                            opts = {}
                            for i in range(2, len(df_up.columns), 2):
                                txt, dest = str(row.iloc[i]).strip(), str(row.iloc[i+1]).strip()
                                if txt and dest: opts[txt] = dest
                            supabase.table("fluxos").insert({"id": str(row['id']), "pergunta": str(row['pergunta']), "tema": n_f, "opcoes": opts}).execute()
                        st.success("Fluxo Atualizado!")
                else:
                    tabela = "book_tags" if tipo == "Tags CRM" else "book_n2"
                    supabase.table(tabela).delete().neq("id", -1).execute()
                    supabase.table(tabela).insert(df_up.to_dict(orient='records')).execute()
                    st.success("Base Atualizada!")
                

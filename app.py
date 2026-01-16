import streamlit as st
import pandas as pd
from supabase import create_client
import json
from datetime import datetime
import io
import plotly.express as px

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="Portal CNX - Inteligência de Apoio", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton>button { width: 100%; border-radius: 12px; height: 4.5em; background-color: #161B22; color: white; border: 1px solid #30363D; font-size: 18px; transition: 0.3s; font-weight: bold; }
    .stButton>button:hover { border-color: #00FFAA !important; color: #00FFAA !important; background-color: #1c2128; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,255,170,0.2); }
    .login-box { background-color: #161B22; padding: 40px; border-radius: 15px; border: 1px solid #30363D; text-align: center; max-width: 500px; margin: auto; }
    .hub-card { background-color: #1c2128; padding: 25px; border-radius: 12px; text-align: center; border: 1px solid #30363D; margin-bottom: 5px; min-height: 150px; display: flex; flex-direction: column; justify-content: center; }
    .instruction-card { background-color: #161B22; padding: 30px; border-radius: 12px; border: 1px solid #30363D; text-align: center; margin-bottom: 25px; border-left: 8px solid #00FFAA; }
    .tag-result { background-color: #1c2128; padding: 20px; border-radius: 10px; border: 1px solid #30363D; border-left: 5px solid #00FFAA; margin-bottom: 15px; }
    h1, h2, h3 { text-align: center; color: #F5F5F5 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES ---
try:
    URL, KEY, ADMIN_PW = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"], st.secrets["ADMIN_PASSWORD"]
    supabase = create_client(URL, KEY)
except:
    st.error("Erro de conexão com o Banco de Dados."); st.stop()

# --- 3. LOGS ---
def registrar_log(termo, aba, passo="n/a", completou=False):
    email = st.session_state.get('user_email', 'n/a')
    payload = {"usuario_email": email, "termo_pesquisado": termo, "aba_utilizada": aba, "passo_fluxo": passo, "completou": completou}
    try:
        supabase.table("logs_pesquisa").insert(payload).execute()
    except: pass

# --- 4. LOGIN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = "Hub"

if not st.session_state.logged_in:
    st.markdown("<br><div class='login-box'><h1>🛡️ Portal CNX</h1>", unsafe_allow_html=True)
    email_in = st.text_input("E-mail corporativo:")
    if st.button("Acessar Portal") and "@" in email_in:
        st.session_state.user_email = email_in; st.session_state.logged_in = True; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True); st.stop()

# --- 5. NAVEGAÇÃO ---
with st.sidebar:
    st.write(f"👤 {st.session_state.user_email}")
    if st.button("Sair"): st.session_state.logged_in = False; st.rerun()

if st.session_state.pagina_atual == "Hub":
    st.markdown("<h1>Central de Inteligência CNX</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='hub-card'><h2>🎮</h2><h3>Fluxos</h3></div>", unsafe_allow_html=True)
        if st.button("Abrir Guias"): st.session_state.pagina_atual = "Fluxos"; st.rerun()
    with c2:
        st.markdown("<div class='hub-card'><h2>🏷️</h2><h3>Tags</h3></div>", unsafe_allow_html=True)
        if st.button("Abrir Tags"): st.session_state.pagina_atual = "Tags"; st.rerun()
    with c3:
        st.markdown("<div class='hub-card'><h2>🚀</h2><h3>N2</h3></div>", unsafe_allow_html=True)
        if st.button("Abrir N2"): st.session_state.pagina_atual = "N2"; st.rerun()
    st.divider()
    if st.button("⚙️ GESTÃO E BI"): st.session_state.pagina_atual = "Gestao"; st.rerun()

# --- FLUXOS ---
elif st.session_state.pagina_atual == "Fluxos":
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    res = supabase.table("fluxos").select("tema").execute()
    temas = sorted(list(set([i['tema'] for i in res.data]))) if res.data else []
    if temas:
        sel = st.selectbox("Selecione o Guia:", temas)
        f_res = supabase.table("fluxos").select("*").eq("tema", sel).execute()
        if f_res.data:
            fluxo = {str(i['id']): i for i in f_res.data}
            if 'step' not in st.session_state or st.session_state.get('last_tema') != sel:
                st.session_state.step = str(f_res.data[0]['id']); st.session_state.last_tema = sel
            no = fluxo.get(st.session_state.step)
            if no:
                opts = no.get('opcoes', {})
                if isinstance(opts, str): opts = json.loads(opts)
                registrar_log(sel, "Fluxos", no['pergunta'], len(opts) == 0)
                st.markdown(f"<div class='instruction-card'><h2>{no['pergunta']}</h2></div>", unsafe_allow_html=True)
                cols = st.columns(len(opts)) if opts else [st.container()]
                for i, (txt, dest) in enumerate(opts.items()):
                    if cols[i].button(txt, key=f"f_{i}"): st.session_state.step = str(dest); st.rerun()
                if st.button("🔄 Reiniciar"): st.session_state.step = str(f_res.data[0]['id']); st.rerun()

# --- BOOKS (BUSCA DIFERENCIADA) ---
elif st.session_state.pagina_atual in ["Tags", "N2"]:
    aba = st.session_state.pagina_atual
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    query = st.text_input(f"Pesquisar em {aba}:").strip().lower()
    if query:
        registrar_log(query, aba)
        tab = "book_tags" if aba == "Tags" else "book_n2"
        res = supabase.table(tab).select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(query).any(), axis=1)
            filt = df[mask]
            
            for _, r in filt.iterrows():
                titulo = r.get('TAG', r.get('Tag', r.get('Assunto', 'Resultado')))
                
                # SE FOR N2: USA EXPANDER (RECOLHIDO)
                if aba == "N2":
                    with st.expander(f"📍 {titulo}", expanded=False):
                        for c in [col for col in df.columns if col.lower() not in ['id', 'created_at']]:
                            if str(r[c]).lower() != "nan": st.write(f"**{c}:** {r[c]}")
                
                # SE FOR TAGS: MANTÉM CARD ABERTO
                else:
                    st.markdown(f"<div class='tag-result'><h3>🏷️ {titulo}</h3>", unsafe_allow_html=True)
                    for c in [col for col in df.columns if col.lower() not in ['id', 'created_at', 'tag', 'tag']]:
                        if str(r[c]).lower() != "nan": st.write(f"**{c}:** {r[c]}")
                    st.code(titulo, language="text")
                    st.markdown("</div>", unsafe_allow_html=True)

# --- GESTÃO E BI ---
elif st.session_state.pagina_atual == "Gestao":
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    if st.text_input("Senha Admin:", type="password") == ADMIN_PW:
        g_tab = st.tabs(["📊 Dashboard", "📥 Relatórios", "🚀 Upload", "🔥 Fluxos"])
        logs = supabase.table("logs_pesquisa").select("*").order("data_hora", desc=True).execute()
        df_l = pd.DataFrame(logs.data) if logs.data else pd.DataFrame()

        with g_tab[0]: # BI
            if not df_l.empty:
                c1, c2 = st.columns(2)
                c1.plotly_chart(px.pie(df_l, names='aba_utilizada', title="Uso por Categoria"), use_container_width=True)
                top = df_l[df_l['aba_utilizada'] != 'Fluxos']['termo_pesquisado'].value_counts().nlargest(10).reset_index()
                c2.plotly_chart(px.bar(top, x='count', y='termo_pesquisado', orientation='h', title="Top 10 Buscas"), use_container_width=True)

        with g_tab[1]: # EXCEL
            if not df_l.empty:
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                    df_l[df_l['aba_utilizada'] != 'Fluxos'].to_excel(wr, index=False, sheet_name='Pesquisas')
                    df_l[df_l['aba_utilizada'] == 'Fluxos'].to_excel(wr, index=False, sheet_name='Jornada_Fluxos')
                st.download_button("📥 Baixar Relatório", data=out.getvalue(), file_name="bi_cnx.xlsx")

        with g_tab[2]: # UPLOAD
            tipo = st.radio("Base:", ["Tags CRM", "Book N2", "Fluxogramas"])
            arq = st.file_uploader("Arquivo")
            if arq and st.button("Salvar"):
                df_u = pd.read_csv(arq) if arq.name.endswith('.csv') else pd.read_excel(arq)
                if tipo == "Fluxogramas":
                    nome = st.text_input("Nome do Tema:")
                    if nome:
                        supabase.table("fluxos").delete().eq("tema", nome).execute()
                        for _, row in df_u.iterrows():
                            opts = {str(row.iloc[i]): str(row.iloc[i+1]) for i in range(2, len(df_u.columns)-1, 2) if str(row.iloc[i]) != "nan"}
                            supabase.table("fluxos").insert({"id": str(row['id']), "pergunta": str(row['pergunta']), "tema": nome, "opcoes": opts}).execute()
                        st.success("Fluxo Atualizado!")
                else:
                    target = "book_tags" if tipo == "Tags CRM" else "book_n2"
                    supabase.table(target).delete().neq("id", -1).execute()
                    supabase.table(target).insert(df_u.to_dict(orient='records')).execute()
                    st.success("Base atualizada!")

        with g_tab[3]: # GERENCIAR FLUXOS
            temas_del = sorted(list(set([i['tema'] for i in supabase.table("fluxos").select("tema").execute().data])))
            ex = st.selectbox("Excluir tema:", temas_del)
            if st.button("🔥 Confirmar Exclusão"):
                supabase.table("fluxos").delete().eq("tema", ex).execute(); st.rerun()

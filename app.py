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
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES ---
try:
    url, key, admin_pw = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"], st.secrets["ADMIN_PASSWORD"]
    supabase = create_client(url, key)
except:
    st.error("Erro nas credenciais do Supabase."); st.stop()

# --- 3. FUNÇÕES DE APOIO ---
def registrar_log(termo, aba, passo="n/a", completou=False):
    email = st.session_state.get('user_email', 'n/a')
    try:
        supabase.table("logs_pesquisa").insert({
            "usuario_email": email, "termo_pesquisado": termo, 
            "aba_utilizada": aba, "passo_fluxo": passo, "completou": completou
        }).execute()
    except: pass

# --- 4. ESTADO DA SESSÃO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = "Hub"

# --- 5. TELA DE LOGIN ---
if not st.session_state.logged_in:
    st.markdown("<br><br><div class='login-box'><h1>🛡️ Portal CNX</h1>", unsafe_allow_html=True)
    email_i = st.text_input("E-mail corporativo:")
    if st.button("Entrar") and "@" in email_i:
        st.session_state.user_email = email_i; st.session_state.logged_in = True; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True); st.stop()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.markdown(f"👤 **Logado:**\n`{st.session_state.user_email}`")
    if st.button("🚪 Sair"):
        st.session_state.logged_in = False; st.session_state.pagina_atual = "Hub"; st.rerun()

# --- 7. NAVEGAÇÃO ---

if st.session_state.pagina_atual == "Hub":
    st.markdown("<h1>Central de Apoio CNX</h1>", unsafe_allow_html=True)
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
    if st.button("⚙️ Gestão e Dashboard de BI"): st.session_state.pagina_atual = "Gestao"; st.rerun()

elif st.session_state.pagina_atual == "Fluxos":
    if st.button("⬅️ Voltar ao Menu"): st.session_state.pagina_atual = "Hub"; st.rerun()
    res_f = supabase.table("fluxos").select("tema").execute()
    temas = sorted(list(set([i['tema'] for i in res_f.data]))) if res_f.data else []
    if temas:
        tema_sel = st.selectbox("Selecione o Guia:", temas)
        res = supabase.table("fluxos").select("*").eq("tema", tema_sel).execute()
        if res.data:
            fluxo = {str(i['id']): i for i in res.data}
            if 'step' not in st.session_state or st.session_state.get('last_tema') != tema_sel:
                st.session_state.step = str(res.data[0]['id']); st.session_state.last_tema = tema_sel
            
            atual = fluxo.get(st.session_state.step)
            if atual:
                opts = atual.get('opcoes', {})
                if isinstance(opts, str): opts = json.loads(opts)
                is_final = len(opts) == 0
                registrar_log(tema_sel, "Fluxos", atual['pergunta'], is_final)
                
                st.markdown(f"<div class='instruction-card'><h2>{atual['pergunta']}</h2></div>", unsafe_allow_html=True)
                cols = st.columns(len(opts)) if opts else [st.container()]
                for i, (txt, dest) in enumerate(opts.items()):
                    if cols[i].button(txt, key=f"btn_{i}"):
                        st.session_state.step = str(dest); st.rerun()
                if st.button("🔄 Reiniciar Guia"): st.session_state.step = str(res.data[0]['id']); st.rerun()

elif st.session_state.pagina_atual in ["Tags", "N2"]:
    aba = st.session_state.pagina_atual
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    busca = st.text_input(f"Pesquisar em {aba}:").lower()
    if busca:
        registrar_log(busca, aba)
        tabela = "book_tags" if aba == "Tags" else "book_n2"
        res = supabase.table(tabela).select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            filt = df[df.apply(lambda row: busca in row.astype(str).str.lower().values, axis=1)]
            for _, r in filt.iterrows():
                st.markdown(f"<div class='tag-card'><strong>{r.get('TAG', r.get('Tag'))}</strong><br>{r.get('Resumo', r.get('Orientação completa', ''))}</div>", unsafe_allow_html=True)
                st.code(r.get('TAG', r.get('Tag')), language="text")

elif st.session_state.pagina_atual == "Gestao":
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    if st.text_input("Senha Admin", type="password") == admin_pw:
        m = st.selectbox("Escolha uma Ação:", ["BI e Funil de Fluxos", "Atualizar Bases", "Gerenciar Fluxos"])
        
        if m == "BI e Funil de Fluxos":
            logs = supabase.table("logs_pesquisa").select("*").order("data_hora", desc=True).execute()
            if logs.data:
                df = pd.DataFrame(logs.data)
                
                # --- TRAVA DE SEGURANÇA PARA COLUNAS NOVAS ---
                for col in ['passo_fluxo', 'completou', 'termo_pesquisado', 'usuario_email', 'aba_utilizada']:
                    if col not in df.columns: df[col] = "n/a"
                
                df['data_hora'] = pd.to_datetime(df['data_hora'])
                st.subheader("📊 Performance e Funil")
                df_f = df[df['aba_utilizada'] == 'Fluxos']
                
                c1, c2 = st.columns(2)
                with c1:
                    if not df_f.empty:
                        df_ab = df_f[df_f['passo_fluxo'] != "n/a"]
                        if not df_ab.empty:
                            abandonos = df_ab[df_ab['completou'] == False]['passo_fluxo'].value_counts().nlargest(5).reset_index()
                            st.plotly_chart(px.bar(abandonos, x='count', y='passo_fluxo', orientation='h', title="Top 5 Pontos de Abandono", color_discrete_sequence=['#FF4B4B']), use_container_width=True)
                with c2:
                    if not df_f.empty and 'completou' in df_f.columns:
                        conclusao = df_f.groupby('termo_pesquisado')['completou'].value_counts(normalize=True).unstack().fillna(0)
                        if True in conclusao.columns:
                            st.plotly_chart(px.bar(conclusao, y=True, title="Taxa de Conclusão por Tema (%)"), use_container_width=True)

                st.divider()
                st.subheader("📥 Extração Detalhada")
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_temp = df.copy()
                    df_temp['data_hora'] = df_temp['data_hora'].dt.strftime('%d/%m/%Y %H:%M')
                    df_temp[df_temp['aba_utilizada'] != 'Fluxos'][['data_hora', 'usuario_email', 'aba_utilizada', 'termo_pesquisado']].to_excel(writer, index=False, sheet_name='Pesquisas_Gerais')
                    
                    df_fx = df_temp[df_temp['aba_utilizada'] == 'Fluxos'][['data_hora', 'usuario_email', 'termo_pesquisado', 'passo_fluxo', 'completou']]
                    df_fx.columns = ['Data/Hora', 'Usuário', 'Tema do Fluxo', 'Último Passo', 'Completou?']
                    df_fx.to_excel(writer, index=False, sheet_name='Jornada_Fluxos')
                st.download_button("Baixar Relatório Detalhado (Excel)", data=output.getvalue(), file_name=f"relatorio_cnx_{datetime.now().strftime('%d_%m')}.xlsx")

        elif m == "Gerenciar Fluxos":
            res_f = supabase.table("fluxos").select("tema").execute()
            temas = sorted(list(set([i['tema'] for i in res_f.data]))) if res_f.data else []
            t_ex = st.selectbox("Selecione o tema para excluir:", temas)
            if st.checkbox(f"Confirmar remoção de: {t_ex}") and st.button("🔥 Excluir"):
                supabase.table("fluxos").delete().eq("tema", t_ex).execute(); st.rerun()

        elif m == "Atualizar Bases":
            tipo = st.radio("Escolha a base:", ["Tags CRM", "Book N2", "Fluxogramas"])
            arq = st.file_uploader("Suba o arquivo", type=["csv", "xlsx"])
            if arq and st.button("Salvar no Banco"):
                df_up = pd.read_csv(arq) if arq.name.endswith('.csv') else pd.read_excel(arq)
                if tipo == "Fluxogramas":
                    n_f = st.text_input("Nome do Tema:")
                    if n_f:
                        supabase.table("fluxos").delete().eq("tema", n_f).execute()
                        for _, row in df_up.iterrows():
                            opts = {}
                            for i in range(2, len(df_up.columns), 2):
                                if i+1 < len(df_up.columns):
                                    txt, dest = str(row.iloc[i]).strip(), str(row.iloc[i+1]).strip()
                                    if txt and dest and txt != "nan": opts[txt] = dest
                            supabase.table("fluxos").insert({"id": str(row['id']), "pergunta": str(row['pergunta']), "tema": n_f, "opcoes": opts}).execute()
                        st.success(f"Fluxo '{n_f}' atualizado!")
                else:
                    tabela = "book_tags" if tipo == "Tags CRM" else "book_n2"
                    supabase.table(tabela).delete().neq("id", -1).execute()
                    supabase.table(tabela).insert(df_up.to_dict(orient='records')).execute()
                    st.success("Base atualizada!")

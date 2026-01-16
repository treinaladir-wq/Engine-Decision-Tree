import streamlit as st
import pandas as pd
from supabase import create_client
import json
from datetime import datetime
import io
import plotly.express as px

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="Portal CNX - BI & Apoio", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #161B22; color: white; border: 1px solid #30363D; font-size: 16px; transition: 0.3s; }
    .stButton>button:hover { border-color: #00FFAA !important; color: #00FFAA !important; background-color: #1c2128; }
    .login-box { background-color: #161B22; padding: 40px; border-radius: 15px; border: 1px solid #30363D; text-align: center; max-width: 500px; margin: auto; }
    .hub-card { background-color: #1c2128; padding: 25px; border-radius: 12px; text-align: center; border: 1px solid #30363D; margin-bottom: 5px; }
    .tag-card { background-color: #1c2128; padding: 15px; border-radius: 8px; border-left: 5px solid #00FFAA; margin-bottom: 10px; }
    h1, h2, h3 { text-align: center; color: #F5F5F5 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES ---
try:
    url, key, admin_pw = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"], st.secrets["ADMIN_PASSWORD"]
    supabase = create_client(url, key)
except:
    st.error("Erro nas credenciais."); st.stop()

# --- 3. FUNÇÕES DE APOIO (REFORÇADA) ---
def registrar_log(termo, aba, passo="n/a", completou=False):
    email = st.session_state.get('user_email', 'n/a')
    # Preparamos o dicionário de dados
    dados = {
        "usuario_email": email, 
        "termo_pesquisado": termo, 
        "aba_utilizada": aba
    }
    # Só adicionamos as colunas novas se estivermos na aba de Fluxos
    if aba == "Fluxos":
        dados["passo_fluxo"] = passo
        dados["completou"] = completou
        
    try:
        supabase.table("logs_pesquisa").insert(dados).execute()
    except Exception as e:
        # Se der erro por falta de coluna, tenta gravar apenas o básico
        try:
            dados_basicos = {"usuario_email": email, "termo_pesquisado": termo, "aba_utilizada": aba}
            supabase.table("logs_pesquisa").insert(dados_basicos).execute()
        except:
            pass

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

# --- 6. NAVEGAÇÃO ---
with st.sidebar:
    st.write(f"👤 {st.session_state.user_email}")
    if st.button("Sair"): st.session_state.logged_in = False; st.rerun()

if st.session_state.pagina_atual == "Hub":
    st.markdown("<h1>Central de Apoio CNX</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: 
        st.markdown("<div class='hub-card'><h2>🎮</h2><h3>Guias</h3></div>", unsafe_allow_html=True)
        if st.button("Fluxogramas"): st.session_state.pagina_atual = "Fluxos"; st.rerun()
    with c2: 
        st.markdown("<div class='hub-card'><h2>🏷️</h2><h3>Tags</h3></div>", unsafe_allow_html=True)
        if st.button("Book de Tags"): st.session_state.pagina_atual = "Tags"; st.rerun()
    with c3: 
        st.markdown("<div class='hub-card'><h2>🚀</h2><h3>N2</h3></div>", unsafe_allow_html=True)
        if st.button("Book N2"): st.session_state.pagina_atual = "N2"; st.rerun()
    st.divider()
    if st.button("⚙️ Gestão e BI"): st.session_state.pagina_atual = "Gestao"; st.rerun()

elif st.session_state.pagina_atual == "Fluxos":
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
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
                registrar_log(tema_sel, "Fluxos", atual['pergunta'], len(opts) == 0)
                st.markdown(f"<div style='background:#161B22; padding:30px; border-radius:12px; text-align:center;'><h2>{atual['pergunta']}</h2></div>", unsafe_allow_html=True)
                cols = st.columns(len(opts)) if opts else [st.container()]
                for i, (txt, dest) in enumerate(opts.items()):
                    if cols[i].button(txt, key=f"b_{i}"):
                        st.session_state.step = str(dest); st.rerun()
                if st.button("🔄 Reiniciar"): st.session_state.step = str(res.data[0]['id']); st.rerun()

elif st.session_state.pagina_atual in ["Tags", "N2"]:
    aba = st.session_state.pagina_atual
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    busca = st.text_input(f"Buscar em {aba}:").lower()
    if busca:
        registrar_log(busca, aba)
        tabela = "book_tags" if aba == "Tags" else "book_n2"
        res = supabase.table(tabela).select("*").execute()
        df = pd.DataFrame(res.data)
        filt = df[df.apply(lambda row: busca in row.astype(str).str.lower().values, axis=1)]
        for _, r in filt.iterrows():
            st.markdown(f"<div class='tag-card'><strong>{r.get('TAG', r.get('Tag'))}</strong><br>{r.get('Resumo', r.get('Orientação completa', ''))}</div>", unsafe_allow_html=True)
            st.code(r.get('TAG', r.get('Tag')), language="text")

elif st.session_state.pagina_atual == "Gestao":
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    if st.text_input("Senha Admin", type="password") == admin_pw:
        m = st.selectbox("Ação:", ["Dashboard Geral", "Atualizar Bases", "Gerenciar Fluxos"])
        
        if m == "Dashboard Geral":
            logs = supabase.table("logs_pesquisa").select("*").order("data_hora", desc=True).execute()
            if logs.data:
                df = pd.DataFrame(logs.data)
                # Garante colunas mínimas
                for c in ['aba_utilizada', 'termo_pesquisado', 'passo_fluxo', 'completou']:
                    if c not in df.columns: df[c] = "n/a"
                
                st.subheader("📊 BI - Resumo de Utilização")
                
                # Gráfico 1: Uso por Aba (Tags, N2 ou Fluxos)
                st.plotly_chart(px.pie(df, names='aba_utilizada', title="Volume por Categoria"), use_container_width=True)
                
                # Gráfico 2: Top 10 Termos pesquisados (Tags/N2)
                df_b = df[df['aba_utilizada'] != 'Fluxos']
                if not df_b.empty:
                    st.plotly_chart(px.bar(df_b['termo_pesquisado'].value_counts().nlargest(10).reset_index(), 
                                         x='count', y='termo_pesquisado', orientation='h', title="Termos mais buscados"), use_container_width=True)

                st.divider()
                # Exportação
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Logs_Completos')
                st.download_button("📥 Baixar Excel", data=output.getvalue(), file_name="relatorio.xlsx")
            else:
                st.info("Nenhum dado de log encontrado no banco.")
        
        elif m == "Gerenciar Fluxos":
            res_f = supabase.table("fluxos").select("tema").execute()
            temas = sorted(list(set([i['tema'] for i in res_f.data]))) if res_f.data else []
            t_ex = st.selectbox("Excluir tema:", temas)
            if st.checkbox("Confirmar exclusão") and st.button("Excluir"):
                supabase.table("fluxos").delete().eq("tema", t_ex).execute(); st.rerun()

        elif m == "Atualizar Bases":
            tipo = st.radio("Base:", ["Tags CRM", "Book N2", "Fluxogramas"])
            arq = st.file_uploader("Arquivo", type=["csv", "xlsx"])
            if arq and st.button("Salvar"):
                df_up = pd.read_csv(arq) if arq.name.endswith('.csv') else pd.read_excel(arq)
                if tipo == "Fluxogramas":
                    n_f = st.text_input("Tema:")
                    if n_f:
                        supabase.table("fluxos").delete().eq("tema", n_f).execute()
                        for _, row in df_up.iterrows():
                            opts = {}
                            for i in range(2, len(df_up.columns), 2):
                                if i+1 < len(df_up.columns):
                                    txt, dest = str(row.iloc[i]).strip(), str(row.iloc[i+1]).strip()
                                    if txt and dest and txt != "nan": opts[txt] = dest
                            supabase.table("fluxos").insert({"id": str(row['id']), "pergunta": str(row['pergunta']), "tema": n_f, "opcoes": opts}).execute()
                        st.success("Fluxo Atualizado!")
                else:
                    tabela = "book_tags" if tipo == "Tags CRM" else "book_n2"
                    supabase.table(tabela).delete().neq("id", -1).execute()
                    supabase.table(tabela).insert(df_up.to_dict(orient='records')).execute()
                    st.success("Base atualizada!")

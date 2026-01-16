import streamlit as st
import pandas as pd
from supabase import create_client
import json
from datetime import datetime
import io
import plotly.express as px

# --- 1. CONFIGURAÇÃO DE INTERFACE (ESTILO WILL BANK) ---
st.set_page_config(page_title="Portal CNX - Inteligência de Apoio", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Importando fonte similar à do Will bank */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

    * { font-family: 'Poppins', sans-serif; }

    /* Fundo escuro levemente azulado, como no app */
    .stApp { background-color: #000000; color: #FFFFFF; }

    /* Botões Principais Estilo Will */
    .stButton>button { 
        width: 100%; 
        border-radius: 16px; 
        height: 4.5em; 
        background-color: #fbd737; /* Amarelo Will */
        color: #000000 !important; /* Texto Preto para contraste */
        border: none; 
        font-size: 18px; 
        transition: all 0.3s ease; 
        font-weight: 700;
        box-shadow: 0px 4px 15px rgba(251, 215, 55, 0.1);
    }
    .stButton>button:hover { 
        background-color: #ffea00; 
        transform: translateY(-3px); 
        box-shadow: 0px 6px 20px rgba(251, 215, 55, 0.3);
    }

    /* Cards do Hub */
    .hub-card { 
        background-color: #1a1a1a; 
        padding: 25px; 
        border-radius: 24px; /* Mais arredondado */
        text-align: center; 
        border: 1px solid #333333; 
        margin-bottom: 5px; 
        min-height: 160px; 
        display: flex; 
        flex-direction: column; 
        justify-content: center;
        transition: 0.3s;
    }
    .hub-card:hover { border-color: #fbd737; }
    .hub-card h3 { color: #fbd737 !important; margin-top: 10px; }

    /* Inputs e Filtros */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 12px !important;
        border: 1px solid #333 !important;
        background-color: #1a1a1a !important;
        color: white !important;
    }

    /* Tabela de Tags */
    .stDataFrame { 
        border: 1px solid #333; 
        border-radius: 16px; 
        overflow: hidden; 
    }

    /* Login Box */
    .login-box { 
        background-color: #1a1a1a; 
        padding: 50px; 
        border-radius: 30px; 
        border: 2px solid #fbd737; 
        text-align: center; 
        max-width: 500px; 
        margin: auto; 
    }
    
    h1 { font-weight: 700; letter-spacing: -1px; color: #FFFFFF !important; }
    
    /* Linha divisória amarela */
    hr { border: 0; height: 1px; background: linear-gradient(to right, transparent, #fbd737, transparent); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES ---
try:
    URL, KEY, ADMIN_PW = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"], st.secrets["ADMIN_PASSWORD"]
    supabase = create_client(URL, KEY)
except:
    st.error("Erro de conexão."); st.stop()

# --- 3. LOGS (VERSÃO BLINDADA) ---
def registrar_log(termo, aba, passo="n/a", completou=False):
    email = st.session_state.get('user_email', 'n/a')
    log_data = {
        "usuario_email": email, 
        "termo_pesquisado": str(termo), 
        "aba_utilizada": str(aba), 
        "passo_fluxo": str(passo)
        # Remova temporariamente a linha do 'completou' se o erro persistir
    }
    # ... resto da função

# --- 4. ESTADO E LOGIN ---
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

# --- HUB PRINCIPAL ---
if st.session_state.pagina_atual == "Hub":
    st.markdown("<h1>Central de Inteligência CNX</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='hub-card'><h2>🎮</h2><h3>Experiência CX</h3></div>", unsafe_allow_html=True)
        if st.button("Abrir Guias"): st.session_state.pagina_atual = "Experiencia CX"; st.rerun()
    with c2:
        st.markdown("<div class='hub-card'><h2>🏷️</h2><h3>Book de Tags</h3></div>", unsafe_allow_html=True)
        if st.button("Consultar Tags"): st.session_state.pagina_atual = "Book de Tags"; st.rerun()
    with c3:
        st.markdown("<div class='hub-card'><h2>🚀</h2><h3>Book N2</h3></div>", unsafe_allow_html=True)
        if st.button("Regras de Escalonamento"): st.session_state.pagina_atual = "Book N2"; st.rerun()
    st.divider()
    if st.button("⚙️ GESTÃO E BI"): st.session_state.pagina_atual = "Gestao"; st.rerun()

# --- BOOK DE TAGS ---
elif st.session_state.pagina_atual == "Book de Tags":
    if st.button("⬅️ Voltar ao Hub"): st.session_state.pagina_atual = "Hub"; st.rerun()
    st.title("🏷️ Book de Tags CRM")
    
    res = supabase.table("book_tags").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        col_tag = 'TAG' if 'TAG' in df.columns else 'Tag'
        
        def get_tipo(t):
            return str(t).split()[0].replace("-","").replace("_","").capitalize() if t and str(t)!='nan' else "Outros"
        df['Tipo_Auto'] = df[col_tag].apply(get_tipo)

        st.markdown("<div class='filter-area'>", unsafe_allow_html=True)
        f1, f2 = st.columns(2)
        with f1:
            times = ["Todos"] + sorted(df['Time'].unique().tolist()) if 'Time' in df.columns else ["Todos"]
            sel_time = st.selectbox("Filtrar por Time:", times)
        with f2:
            tipos = ["Todos", "Problema", "Dúvida", "Reclamação", "Solicitação"]
            sel_tipo = st.selectbox("Tipo de Tag:", tipos)
        
        query = st.text_input("🔍 Busca rápida por palavra-chave:").strip().lower()
        st.markdown("</div>", unsafe_allow_html=True)

        filt = df.copy()
        if sel_time != "Todos": filt = filt[filt['Time'] == sel_time]
        if sel_tipo != "Todos": filt = filt[filt['Tipo_Auto'] == sel_tipo]
        if query:
            registrar_log(query, "Book de Tags")
            mask = filt.apply(lambda r: r.astype(str).str.lower().str.contains(query).any(), axis=1)
            filt = filt[mask]

        if not filt.empty:
            col_resumo = 'Resumo' if 'Resumo' in df.columns else (df.columns[2] if len(df.columns) > 2 else df.columns[-1])
            col_time = 'Time' if 'Time' in df.columns else 'Time Responsável'

            tab_display = filt[[col_tag, col_time, col_resumo]].copy()
            tab_display.columns = ["Nome da Tag", "Time Responsável", "Resumo"]

            st.dataframe(tab_display, use_container_width=True, hide_index=True,
                column_config={
                    "Nome da Tag": st.column_config.TextColumn("🏷️ Nome da Tag", width="medium"),
                    "Time Responsável": st.column_config.TextColumn("👥 Time", width="small"),
                    "Resumo": st.column_config.TextColumn("📝 Resumo/Orientação", width="large"),
                })
            
            if len(filt) <= 10:
                st.info("💡 Clique abaixo para copiar a tag rapidamente:")
                for _, r in filt.iterrows(): st.code(r[col_tag], language="text")
        else:
            st.warning("Nenhuma tag encontrada.")
    else:
        st.error("Base de Tags não carregada.")

# --- BOOK N2 ---
elif st.session_state.pagina_atual == "Book N2":
    if st.button("⬅️ Voltar ao Hub"): st.session_state.pagina_atual = "Hub"; st.rerun()
    st.title("🚀 Book N2")
    q_n2 = st.text_input("Pesquisar Regra N2 (digite qualquer termo):").strip().lower()
    res = supabase.table("book_n2").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        if q_n2:
            registrar_log(q_n2, "Book N2")
            mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(q_n2, na=False).any(), axis=1)
            filt_n2 = df[mask]
        else:
            filt_n2 = df

        if not filt_n2.empty:
            for _, r in filt_n2.iterrows():
                titulo = r.get('Assunto', r.get('Tag', r.get('TAG', 'Regra N2')))
                time_resp = r.get('Time', 'N2')
                with st.expander(f"📍 {titulo} | {time_resp}"):
                    for c in [col for col in df.columns if col.lower() not in ['id', 'created_at']]:
                        valor = str(r[c])
                        if valor.lower() != "nan" and valor.strip() != "": st.write(f"**{c}:** {valor}")
        else:
            st.warning("Nenhum resultado encontrado.")
    else:
        st.error("Base N2 não carregada.")

# --- EXPERIÊNCIA CX (FLUXOS) ---
elif st.session_state.pagina_atual == "Experiencia CX":
    if st.button("⬅️ Voltar ao Hub"): st.session_state.pagina_atual = "Hub"; st.rerun()
    st.title("🎮 Experiência CX")
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
                registrar_log(sel, "Experiência CX", no['pergunta'], len(opts) == 0)
                st.markdown(f"<div style='background:#161B22; padding:30px; border-radius:12px; text-align:center;'><h2>{no['pergunta']}</h2></div>", unsafe_allow_html=True)
                cols = st.columns(len(opts)) if opts else [st.container()]
                for i, (txt, dest) in enumerate(opts.items()):
                    if cols[i].button(txt, key=f"f_{i}"): st.session_state.step = str(dest); st.rerun()
                if st.button("🔄 Reiniciar"): st.session_state.step = str(f_res.data[0]['id']); st.rerun()

# --- GESTÃO E RELATÓRIOS ---
elif st.session_state.pagina_atual == "Gestao":
    if st.button("⬅️ Voltar ao Hub"): st.session_state.pagina_atual = "Hub"; st.rerun()
    if st.text_input("Senha Admin:", type="password") == ADMIN_PW:
        g_tab = st.tabs(["📊 Dashboard", "📥 Relatórios", "🚀 Upload", "🔥 Fluxos"])
        
        with g_tab[0]: # DASHBOARD
            logs_res = supabase.table("logs_pesquisa").select("*").order("data_hora", desc=True).execute()
            if logs_res.data:
                df_l = pd.DataFrame(logs_res.data)
                c1, c2 = st.columns(2)
                c1.plotly_chart(px.pie(df_l, names='aba_utilizada', title="Uso por Categoria"), use_container_width=True)
                df_buscas = df_l[df_l['aba_utilizada'] != 'Experiência CX']
                if not df_buscas.empty:
                    top = df_buscas['termo_pesquisado'].value_counts().nlargest(10).reset_index()
                    c2.plotly_chart(px.bar(top, x='count', y='termo_pesquisado', orientation='h', title="Top 10 Buscas"), use_container_width=True)

        with g_tab[1]: # ABA DE RELATÓRIOS
            st.subheader("📥 Exportação de Relatórios")
    
    # Busca os dados brutos no Supabase
            res = supabase.table("logs_pesquisa").select("*").order("data_hora", desc=True).execute()
    
            if res.data:
                    df_base = pd.DataFrame(res.data)
        # Formata a data para o padrão brasileiro
                df_base['data_hora'] = pd.to_datetime(df_base['data_hora']).dt.strftime('%d/%m/%Y %H:%M')

                c1, c2 = st.columns(2)

        # --- BOTÃO 1: BUSCAS MANUAIS (TAGS E N2) ---
            with c1:
            st.markdown("#### 🏷️ Book de Tags & Book N2")
            # Filtra tudo que contém 'Tags' ou 'N2' no nome da aba
            df_manuais = df_base[df_base['aba_utilizada'].str.contains('Tags|N2', case=False, na=False)]
            
            if not df_manuais.empty:
                # Seleciona apenas as colunas relevantes para buscas
                df_manuais_out = df_manuais[['data_hora', 'usuario_email', 'aba_utilizada', 'termo_pesquisado']].copy()
                df_manuais_out.columns = ['Data/Hora', 'Usuário', 'Onde Buscou', 'Termo Pesquisado']
                
                output_m = io.BytesIO()
                with pd.ExcelWriter(output_m, engine='xlsxwriter') as writer:
                    df_manuais_out.to_excel(writer, index=False, sheet_name='Buscas_Manuais')
                
                st.download_button(
                    label="📥 Baixar Relatório Tags e N2",
                    data=output_m.getvalue(),
                    file_name=f"RELATORIO_BUSCAS_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Sem dados de buscas para exportar.")

        # --- BOTÃO 2: EXPERIÊNCIA CX (FLUXOS) ---
            with c2:
                st.markdown("#### 🎮 Experiência CX (Fluxos)")
            # Filtra tudo que contém 'Experiencia' ou 'Fluxo'
                df_fluxos = df_base[df_base['aba_utilizada'].str.contains('Experiencia|Fluxo', case=False, na=False)]
            
            if not df_fluxos.empty:
                # Conforme solicitado: Data/Hora e qual Fluxo utilizou (termo_pesquisado guarda o nome do fluxo)
                df_fluxos_out = df_fluxos[['data_hora', 'usuario_email', 'termo_pesquisado']].copy()
                df_fluxos_out.columns = ['Data/Hora', 'Usuário', 'Fluxo Utilizado']
                
                output_f = io.BytesIO()
                with pd.ExcelWriter(output_f, engine='xlsxwriter') as writer:
                    df_fluxos_out.to_excel(writer, index=False, sheet_name='Uso_Fluxogramas')
                
                st.download_button(
                    label="📥 Baixar Relatório de Fluxos",
                    data=output_f.getvalue(),
                    file_name=f"RELATORIO_FLUXOS_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Sem dados de fluxos para exportar.")

    else:
        st.warning("O banco de dados de logs está vazio.")

        with g_tab[2]: # UPLOAD
            tipo = st.radio("Base:", ["Tags CRM", "Book N2", "Fluxogramas"])
            arq = st.file_uploader("Arquivo", type=['csv', 'xlsx'])
            if arq and st.button("Salvar Dados"):
                df_u = pd.read_csv(arq) if arq.name.endswith('.csv') else pd.read_excel(arq)
                if tipo == "Fluxogramas":
                    nome_tema = st.text_input("Nome do tema:")
                    if nome_tema:
                        supabase.table("fluxos").delete().eq("tema", nome_tema).execute()
                        for _, row in df_u.iterrows():
                            opts = {str(row.iloc[i]): str(row.iloc[i+1]) for i in range(2, len(df_u.columns)-1, 2) if str(row.iloc[i]) != "nan"}
                            supabase.table("fluxos").insert({"id": str(row['id']), "pergunta": str(row['pergunta']), "tema": nome_tema, "opcoes": opts}).execute()
                        st.success("Fluxo Atualizado!")
                else:
                    target = "book_tags" if tipo == "Tags CRM" else "book_n2"
                    supabase.table(target).delete().neq("id", -1).execute()
                    supabase.table(target).insert(df_u.to_dict(orient='records')).execute()
                    st.success(f"Base de {tipo} atualizada!")

        with g_tab[3]: # GERENCIAR FLUXOS
            res_f = supabase.table("fluxos").select("tema").execute()
            temas_lista = sorted(list(set([i['tema'] for i in res_f.data]))) if res_f.data else []
            if temas_lista:
                tema_del = st.selectbox("Selecione para excluir:", temas_lista)
                if st.button("🔥 Excluir Tema"):
                    supabase.table("fluxos").delete().eq("tema", tema_del).execute()
                    st.success("Removido."); st.rerun()

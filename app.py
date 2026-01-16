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
    .stButton>button:hover { border-color: #00FFAA !important; color: #00FFAA !important; background-color: #1c2128; transform: translateY(-2px); }
    .login-box { background-color: #161B22; padding: 40px; border-radius: 15px; border: 1px solid #30363D; text-align: center; max-width: 500px; margin: auto; }
    .hub-card { background-color: #1c2128; padding: 25px; border-radius: 12px; text-align: center; border: 1px solid #30363D; margin-bottom: 5px; min-height: 150px; display: flex; flex-direction: column; justify-content: center; }
    .tag-result { background-color: #1c2128; padding: 20px; border-radius: 10px; border: 1px solid #30363D; border-left: 5px solid #00FFAA; margin-bottom: 15px; }
    .filter-area { background-color: #161B22; padding: 20px; border-radius: 12px; border: 1px solid #30363D; margin-bottom: 20px; }
    h1, h2, h3 { text-align: center; color: #F5F5F5 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES ---
try:
    URL, KEY, ADMIN_PW = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"], st.secrets["ADMIN_PASSWORD"]
    supabase = create_client(URL, KEY)
except:
    st.error("Erro de conexão."); st.stop()

# --- 3. LOGS ---
def registrar_log(termo, aba, passo="n/a", completou=False):
    email = st.session_state.get('user_email', 'n/a')
    try:
        supabase.table("logs_pesquisa").insert({"usuario_email": email, "termo_pesquisado": termo, "aba_utilizada": aba, "passo_fluxo": passo, "completou": completou}).execute()
    except: pass

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

# --- BOOK DE TAGS (FORMATO TABELA: TAG | TIME | RESUMO) ---
elif st.session_state.pagina_atual == "Tags":
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    st.title("🏷️ Book de Tags CRM")
    
    res = supabase.table("book_tags").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        
        # Identifica a coluna da Tag (suporta 'TAG' ou 'Tag')
        col_tag = 'TAG' if 'TAG' in df.columns else 'Tag'
        
        # Lógica de extração do tipo pela primeira palavra (para o filtro)
        def get_tipo(t):
            return str(t).split()[0].replace("-","").replace("_","").capitalize() if t and str(t)!='nan' else "Outros"
        df['Tipo_Auto'] = df[col_tag].apply(get_tipo)

        # --- ÁREA DE FILTROS ---
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

        # --- APLICAÇÃO DOS FILTROS ---
        filt = df.copy()
        if sel_time != "Todos": filt = filt[filt['Time'] == sel_time]
        if sel_tipo != "Todos": filt = filt[filt['Tipo_Auto'] == sel_tipo]
        if query:
            registrar_log(query, "Tags")
            # Busca o termo em qualquer coluna do DataFrame filtrado
            mask = filt.apply(lambda r: r.astype(str).str.lower().str.contains(query).any(), axis=1)
            filt = filt[mask]

        # --- EXIBIÇÃO EM FORMATO DE TABELA ORGANIZADA ---
        if not filt.empty:
            # Selecionamos e renomeamos apenas as colunas solicitadas para a tabela
            # Nota: Ajuste os nomes abaixo ('Resumo', 'Time') conforme os nomes exatos no seu Excel
            col_resumo = 'Resumo' if 'Resumo' in df.columns else (df.columns[2] if len(df.columns) > 2 else df.columns[-1])
            col_time = 'Time' if 'Time' in df.columns else 'Time Responsável'

            tab_display = filt[[col_tag, col_time, col_resumo]].copy()
            tab_display.columns = ["Nome da Tag", "Time Responsável", "Resumo"]

            # Exibe a tabela com largura total
            st.dataframe(
                tab_display, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Nome da Tag": st.column_config.TextColumn("🏷️ Nome da Tag", width="medium"),
                    "Time Responsável": st.column_config.TextColumn("👥 Time", width="small"),
                    "Resumo": st.column_config.TextColumn("📝 Resumo/Orientação", width="large"),
                }
            )
            
            # Atalho para copiar: Mostra as tags em formato de código abaixo da tabela se houver poucas selecionadas
            if len(filt) <= 10:
                st.info("💡 Clique abaixo para copiar a tag rapidamente:")
                for _, r in filt.iterrows():
                    st.code(r[col_tag], language="text")
        else:
            st.warning("Nenhuma tag encontrada com esses filtros.")
    else:
        st.error("Base de Tags não carregada.")

# --- BOOK N2 (BUSCA CORRIGIDA + ACORDEÃO) ---
elif st.session_state.pagina_atual == "N2":
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    st.title("🚀 Book N2")
    
    # Campo de busca com trim (remove espaços extras)
    q_n2 = st.text_input("Pesquisar Regra N2 (digite qualquer termo):").strip().lower()
    
    res = supabase.table("book_n2").select("*").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        
        # Filtro de Busca Robusto
        if q_n2:
            registrar_log(q_n2, "N2")
            # Procura em todas as colunas, convertendo tudo para string e minúsculo
            mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(q_n2, na=False).any(), axis=1)
            filt_n2 = df[mask]
        else:
            filt_n2 = df

        if not filt_n2.empty:
            st.write(f"Exibindo {len(filt_n2)} resultados:")
            for _, r in filt_n2.iterrows():
                # Tenta identificar o melhor título para o acordeão
                titulo = r.get('Assunto', r.get('Tag', r.get('TAG', 'Regra de Escalonamento')))
                time_resp = r.get('Time', r.get('Time Responsável', 'N2'))
                
                with st.expander(f"📍 {titulo} | {time_resp}"):
                    # Exibe todas as colunas que não sejam IDs técnicos
                    for c in [col for col in df.columns if col.lower() not in ['id', 'created_at']]:
                        valor = str(r[c])
                        if valor.lower() != "nan" and valor.strip() != "":
                            st.write(f"**{c}:** {valor}")
        else:
            st.warning(f"Nenhum resultado encontrado para '{q_n2}'.")
    else:
        st.error("A base de dados N2 está vazia ou não pôde ser carregada.")
        
# --- FLUXOS E GESTÃO (MANTIDOS) ---
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
                st.markdown(f"<div style='background:#161B22; padding:30px; border-radius:12px; text-align:center;'><h2>{no['pergunta']}</h2></div>", unsafe_allow_html=True)
                cols = st.columns(len(opts)) if opts else [st.container()]
                for i, (txt, dest) in enumerate(opts.items()):
                    if cols[i].button(txt, key=f"f_{i}"): st.session_state.step = str(dest); st.rerun()
                if st.button("🔄 Reiniciar"): st.session_state.step = str(f_res.data[0]['id']); st.rerun()

elif st.session_state.pagina_atual == "Gestao":
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    if st.text_input("Senha Admin:", type="password") == ADMIN_PW:
        g_tab = st.tabs(["📊 Dashboard", "📥 Relatórios", "🚀 Upload", "🔥 Fluxos"])
        logs = supabase.table("logs_pesquisa").select("*").order("data_hora", desc=True).execute()
        df_l = pd.DataFrame(logs.data) if logs.data else pd.DataFrame()
        with g_tab[0]: # BI
            logs_res = supabase.table("logs_pesquisa").select("*").order("data_hora", desc=True).execute()
            if logs_res.data:
                df_l = pd.DataFrame(logs_res.data)
            if not df_l.empty:
                c1, c2 = st.columns(2)
                c1.plotly_chart(px.pie(df_l, names='aba_utilizada', title="Uso por Categoria"), use_container_width=True)
                top = df_l[df_l['aba_utilizada'] != 'Fluxos']['termo_pesquisado'].value_counts().nlargest(10).reset_index()
                c2.plotly_chart(px.bar(top, x='count', y='termo_pesquisado', orientation='h', title="Top 10 Buscas"), use_container_width=True)
                # --- BLOCO DE EXPORTAÇÃO DETALHADA (Adicionar na aba Gestao) ---
st.subheader("📥 Extração de Dados para Auditoria")

# 1. Recupera todos os logs do banco de dados
logs_res = supabase.table("logs_pesquisa").select("*").order("data_hora", desc=True).execute()

if logs_res.data:
    df_l = pd.DataFrame(logs_res.data)
    
    # Tratamento de datas e colunas
    df_l['data_hora'] = pd.to_datetime(df_l['data_hora']).dt.strftime('%d/%m/%Y %H:%M')
    
    # Preparação do arquivo Excel em memória
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        # ABA 1: PESQUISAS (Tags e N2)
        # Filtra apenas o que foi buscado nos manuais
        df_pesquisas = df_l[df_l['aba_utilizada'].isin(['Tags', 'N2'])]
        if not df_pesquisas.empty:
            df_pesquisas = df_pesquisas[['data_hora', 'usuario_email', 'aba_utilizada', 'termo_pesquisado']]
            df_pesquisas.columns = ['Data/Hora', 'Usuário', 'Onde Buscou', 'Termo Pesquisado']
            df_pesquisas.to_excel(writer, index=False, sheet_name='Buscas_Manuais')
        
        # ABA 2: JORNADA FLUXOS
        # Filtra apenas o comportamento nos guias de decisão
        df_fluxos = df_l[df_l['aba_utilizada'] == 'Fluxos']
        if not df_fluxos.empty:
            df_fluxos = df_fluxos[['data_hora', 'usuario_email', 'termo_pesquisado', 'passo_fluxo', 'completou']]
            df_fluxos.columns = ['Data/Hora', 'Usuário', 'Nome do Fluxo', 'Último Passo Lido', 'Chegou ao Fim?']
            df_fluxos.to_excel(writer, index=False, sheet_name='Uso_Fluxogramas')

    # Botão de Download
    st.info("O arquivo contém abas separadas para buscas manuais e uso de fluxogramas.")
    st.download_button(
        label="📥 Baixar Relatório Excel Detalhado",
        data=output.getvalue(),
        file_name=f"LOGS_USO_CNX_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("Não existem registros de log para exportar no momento.")
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

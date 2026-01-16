import streamlit as st
import pandas as pd
from supabase import create_client
import json
from datetime import datetime
import io
import plotly.express as px

# --- 1. CONFIGURAÇÃO DE INTERFACE (UI/UX) ---
st.set_page_config(page_title="Portal CNX - Inteligência de Apoio", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    /* Botões do Hub e Navegação */
    .stButton>button { width: 100%; border-radius: 12px; height: 4.5em; background-color: #161B22; color: white; border: 1px solid #30363D; font-size: 18px; transition: 0.3s; font-weight: bold; }
    .stButton>button:hover { border-color: #00FFAA !important; color: #00FFAA !important; background-color: #1c2128; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,255,170,0.2); }
    /* Cards de Login e Instruções */
    .login-box { background-color: #161B22; padding: 40px; border-radius: 15px; border: 1px solid #30363D; text-align: center; max-width: 500px; margin: auto; }
    .hub-card { background-color: #1c2128; padding: 25px; border-radius: 12px; text-align: center; border: 1px solid #30363D; margin-bottom: 5px; min-height: 150px; display: flex; flex-direction: column; justify-content: center; }
    .instruction-card { background-color: #161B22; padding: 30px; border-radius: 12px; border: 1px solid #30363D; text-align: center; margin-bottom: 25px; border-left: 8px solid #00FFAA; }
    /* Cards de Busca (Tags e N2) */
    .tag-result { background-color: #1c2128; padding: 20px; border-radius: 10px; border: 1px solid #30363D; border-left: 5px solid #00FFAA; margin-bottom: 15px; }
    h1, h2, h3 { text-align: center; color: #F5F5F5 !important; }
    .stExpander { background-color: #161B22 !important; border: 1px solid #30363D !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES E SEGURANÇA ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    ADMIN_PW = st.secrets["ADMIN_PASSWORD"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error(f"Erro de Conexão: {e}")
    st.stop()

# --- 3. MOTOR DE LOGS (RASTREAMENTO COMPLETO) ---
def registrar_log(termo, aba, passo="n/a", completou=False):
    email = st.session_state.get('user_email', 'n/a')
    payload = {
        "usuario_email": email,
        "termo_pesquisado": termo,
        "aba_utilizada": aba,
        "passo_fluxo": passo,
        "completou": completou,
        "data_hora": datetime.now().isoformat()
    }
    try:
        supabase.table("logs_pesquisa").insert(payload).execute()
    except:
        # Fallback para colunas básicas se as novas falharem
        try:
            basic_payload = {"usuario_email": email, "termo_pesquisado": termo, "aba_utilizada": aba}
            supabase.table("logs_pesquisa").insert(basic_payload).execute()
        except: pass

# --- 4. CONTROLE DE ESTADO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = "Hub"

# --- 5. TELA DE ACESSO ---
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.title("🛡️ Portal CNX")
    st.write("Acesso restrito a colaboradores.")
    email_input = st.text_input("E-mail corporativo:", placeholder="seu.nome@empresa.com")
    if st.button("Entrar no Portal"):
        if "@" in email_input and "." in email_input:
            st.session_state.user_email = email_input
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Por favor, insira um e-mail válido.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 6. BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.markdown(f"### 👤 Usuário\n`{st.session_state.user_email}`")
    st.divider()
    if st.button("🚪 Encerrar Sessão"):
        st.session_state.logged_in = False
        st.session_state.pagina_atual = "Hub"
        st.rerun()

# --- 7. NAVEGAÇÃO PRINCIPAL ---

# --- HUB CENTRAL ---
if st.session_state.pagina_atual == "Hub":
    st.markdown("<h1 style='font-size: 42px; margin-bottom: 40px;'>Central de Inteligência CNX</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='hub-card'><h2>🎮</h2><h3>Guias de Decisão</h3><p style='color:#888;'>Fluxogramas Interativos</p></div>", unsafe_allow_html=True)
        if st.button("Abrir Fluxos"): 
            st.session_state.pagina_atual = "Fluxos"; st.rerun()
            
    with col2:
        st.markdown("<div class='hub-card'><h2>🏷️</h2><h3>Book de Tags</h3><p style='color:#888;'>Consulta de Tags CRM</p></div>", unsafe_allow_html=True)
        if st.button("Consultar Tags"): 
            st.session_state.pagina_atual = "Tags"; st.rerun()
            
    with col3:
        st.markdown("<div class='hub-card'><h2>🚀</h2><h3>Book N2</h3><p style='color:#888;'>Regras de Escalonamento</p></div>", unsafe_allow_html=True)
        if st.button("Ver Regras N2"): 
            st.session_state.pagina_atual = "N2"; st.rerun()

    st.markdown("<br><br><hr style='border-color: #30363D;'>", unsafe_allow_html=True)
    if st.button("⚙️ PAINEL DE GESTÃO, BI E PESQUISA DE PROCEDIMENTOS"):
        st.session_state.pagina_atual = "Gestao"; st.rerun()

# --- PÁGINA: FLUXOS INTERATIVOS ---
elif st.session_state.pagina_atual == "Fluxos":
    if st.button("⬅️ Voltar ao Hub Principal"): st.session_state.pagina_atual = "Hub"; st.rerun()
    
    res_temas = supabase.table("fluxos").select("tema").execute()
    temas_disponiveis = sorted(list(set([item['tema'] for item in res_temas.data]))) if res_temas.data else []
    
    if temas_disponiveis:
        tema_selecionado = st.selectbox("Escolha o fluxo de atendimento:", temas_disponiveis)
        res = supabase.table("fluxos").select("*").eq("tema", tema_selecionado).execute()
        
        if res.data:
            dict_fluxo = {str(item['id']): item for item in res.data}
            # Inicializa ou reinicia se trocar de tema
            if 'step' not in st.session_state or st.session_state.get('last_tema') != tema_selecionado:
                st.session_state.step = str(res.data[0]['id'])
                st.session_state.last_tema = tema_selecionado
            
            no_atual = dict_fluxo.get(st.session_state.step)
            if no_atual:
                opcoes = no_atual.get('opcoes', {})
                if isinstance(opcoes, str): opcoes = json.loads(opcoes)
                
                # Registro de Log com métrica de conclusão
                is_final = len(opcoes) == 0
                registrar_log(tema_selecionado, "Fluxos", no_atual['pergunta'], is_final)
                
                st.markdown(f"<div class='instruction-card'><h2>{no_atual['pergunta']}</h2></div>", unsafe_allow_html=True)
                
                # Renderiza botões de opção
                if opcoes:
                    cols = st.columns(len(opcoes))
                    for idx, (texto, destino) in enumerate(opcoes.items()):
                        if cols[idx].button(texto, key=f"btn_{idx}"):
                            st.session_state.step = str(destino)
                            st.rerun()
                
                if st.button("🔄 Reiniciar Atendimento"):
                    st.session_state.step = str(res.data[0]['id'])
                    st.rerun()
    else:
        st.info("Nenhum fluxo cadastrado no sistema.")

# --- PÁGINAS: TAGS E N2 (BUSCA UNIVERSAL) ---
elif st.session_state.pagina_atual in ["Tags", "N2"]:
    origem = st.session_state.pagina_atual
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    
    st.title(f"🔍 Consulta: {origem}")
    query = st.text_input(f"Pesquisar em {origem} (Qualquer termo):").strip().lower()
    
    if query:
        registrar_log(query, origem)
        tabela = "book_tags" if origem == "Tags" else "book_n2"
        res_busca = supabase.table(tabela).select("*").execute()
        
        if res_busca.data:
            df_busca = pd.DataFrame(res_busca.data)
            # Busca em todas as colunas
            mask = df_busca.apply(lambda row: row.astype(str).str.lower().str.contains(query).any(), axis=1)
            resultados = df_busca[mask]
            
            if not resultados.empty:
                st.success(f"{len(resultados)} resultados encontrados.")
                for _, linha in resultados.iterrows():
                    with st.container():
                        st.markdown("<div class='tag-result'>", unsafe_allow_html=True)
                        colunas_uteis = [c for c in df_busca.columns if c.lower() not in ['id', 'created_at']]
                        
                        # Destaque para a TAG principal (se existir)
                        tag_principal = linha.get('TAG', linha.get('Tag', ''))
                        if tag_principal:
                            st.subheader(f"🏷️ {tag_principal}")
                        
                        for col in colunas_uteis:
                            valor = str(linha[col])
                            if valor.lower() != "nan" and valor.strip():
                                st.write(f"**{col}:** {valor}")
                        
                        if tag_principal:
                            st.code(tag_principal, language="text")
                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.warning("Nenhum registro corresponde à sua busca.")

# --- PÁGINA: GESTÃO, BI E EXPORTAÇÃO ---
elif st.session_state.pagina_atual == "Gestao":
    if st.button("⬅️ Voltar"): st.session_state.pagina_atual = "Hub"; st.rerun()
    
    senha = st.text_input("Chave de Acesso Admin:", type="password")
    if senha == ADMIN_PW:
        aba_gestao = st.tabs(["📊 Dashboard de BI", "📥 Exportação de Dados", "🚀 Atualizar Bases", "🔥 Gerenciar Fluxos"])
        
        # ABA BI
        with aba_gestao[0]:
            logs_res = supabase.table("logs_pesquisa").select("*").order("data_hora", desc=True).execute()
            if logs_res.data:
                df_l = pd.DataFrame(logs_res.data)
                df_l['data_hora'] = pd.to_datetime(df_l['data_hora'])
                
                # Garante colunas para não quebrar gráficos
                for c in ['aba_utilizada', 'termo_pesquisado', 'passo_fluxo', 'completou']:
                    if c not in df_l.columns: df_l[c] = "n/a"

                c1, c2 = st.columns(2)
                with c1:
                    st.plotly_chart(px.pie(df_l, names='aba_utilizada', title="Uso por Categoria", hole=0.4), use_container_width=True)
                with c2:
                    top_buscas = df_l[df_l['aba_utilizada'] != 'Fluxos']['termo_pesquisado'].value_counts().nlargest(10).reset_index()
                    st.plotly_chart(px.bar(top_buscas, x='count', y='termo_pesquisado', orientation='h', title="Top 10 Buscas Realizadas"), use_container_width=True)
                
                st.divider()
                st.subheader("📉 Funil de Fluxogramas (Pontos de Desistência)")
                df_f = df_l[df_l['aba_utilizada'] == 'Fluxos']
                if not df_f.empty:
                    abandonos = df_f[df_f['completou'] == False]['passo_fluxo'].value_counts().nlargest(8).reset_index()
                    st.plotly_chart(px.bar(abandonos, x='count', y='passo_fluxo', orientation='h', title="Onde os atendentes mais param", color_discrete_sequence=['#FF4B4B']), use_container_width=True)
            else:
                st.info("Sem dados de log para exibir no momento.")

        # ABA EXPORTAÇÃO
        with aba_gestao[1]:
            st.subheader("Relatórios Detalhados")
            if logs_res.data:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Aba 1: Buscas Gerais
                    df_gen = df_l[df_l['aba_utilizada'] != 'Fluxos'][['data_hora', 'usuario_email', 'aba_utilizada', 'termo_pesquisado']]
                    df_gen.to_excel(writer, index=False, sheet_name='Pesquisas_Tags_N2')
                    
                    # Aba 2: Jornada nos Fluxos
                    df_fluxo_exp = df_l[df_l['aba_utilizada'] == 'Fluxos'][['data_hora', 'usuario_email', 'termo_pesquisado', 'passo_fluxo', 'completou']]
                    df_fluxo_exp.columns = ['Data_Hora', 'Usuario', 'Tema_Fluxo', 'Ultimo_Passo', 'Concluido']
                    df_fluxo_exp.to_excel(writer, index=False, sheet_name='Jornada_Fluxos')
                
                st.download_button("📥 Baixar Excel Detalhado (Abas Separadas)", data=output.getvalue(), file_name=f"bi_cnx_{datetime.now().strftime('%d_%m')}.xlsx")
            else:
                st.warning("Não há dados para exportar.")

        # ABA ATUALIZAR
        with aba_gestao[2]:
            base_tipo = st.radio("Selecione a base:", ["Tags CRM", "Book N2", "Fluxogramas"])
            file = st.file_uploader("Upload do arquivo (CSV ou Excel)", type=["csv", "xlsx"])
            if file and st.button("Confirmar Atualização"):
                df_up = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
                if base_tipo == "Fluxogramas":
                    tema_nome = st.text_input("Nome do Tema para este fluxo:")
                    if tema_nome:
                        supabase.table("fluxos").delete().eq("tema", tema_nome).execute()
                        for _, row in df_up.iterrows():
                            opts = {}
                            for i in range(2, len(df_up.columns), 2):
                                if i+1 < len(df_up.columns):
                                    t, d = str(row.iloc[i]), str(row.iloc[i+1])
                                    if t != "nan" and d != "nan": opts[t] = d
                            supabase.table("fluxos").insert({"id": str(row['id']), "pergunta": str(row['pergunta']), "tema": tema_nome, "opcoes": opts}).execute()
                        st.success(f"Fluxo {tema_nome} carregado!")
                else:
                    target = "book_tags" if base_tipo == "Tags CRM" else "book_n2"
                    supabase.table(target).delete().neq("id", -1).execute()
                    supabase.table(target).insert(df_up.to_dict(orient='records')).execute()
                    st.success(f"Base de {base_tipo} atualizada com sucesso!")

        # ABA GERENCIAR
        with aba_gestao[3]:
            res_del = supabase.table("fluxos").select("tema").execute()
            temas_del = sorted(list(set([i['tema'] for i in res_del.data]))) if res_del.data else []
            tema_excluir = st.selectbox("Escolha um tema para APAGAR:", temas_del)
            if st.checkbox(f"Confirmar exclusão definitiva do fluxo: {tema_excluir}"):
                if st.button("🔥 Excluir Fluxo"):
                    supabase.table("fluxos").delete().eq("tema", tema_excluir).execute()
                    st.rerun()
    elif senha:
        st.error("Chave de acesso incorreta.")

# --- PRÓXIMO PASSO ---
# Deseja que eu adicione agora a aba de "Procedure Research" para pesquisa de PDFs e manuais?

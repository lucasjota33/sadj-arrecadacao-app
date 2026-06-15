import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import Increment
import pandas as pd

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Campanha de Arrecadação - SADJ", page_icon="logo.png", layout="wide")

# --- ESTILO VISUAL INSTITUCIONAL ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --azul-marinho: #0B2545;
        --azul-medio: #13315C;
        --caqui: #8B7355;
        --dourado: #C9A961;
        --verde-oliva: #1B5E20;
        --papel: #F7F5F0;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3 {
        font-family: 'Oswald', sans-serif;
        letter-spacing: 0.5px;
        color: var(--azul-marinho);
    }

    h1 {
        text-transform: uppercase;
        border-bottom: 4px solid var(--caqui);
        padding-bottom: 0.4rem;
    }

    /* Cards de métrica */
    .sadj-card {
        background: linear-gradient(135deg, var(--azul-marinho) 0%, var(--azul-medio) 100%);
        border-left: 6px solid var(--caqui);
        border-radius: 8px;
        padding: 1.1rem 1.4rem;
        color: var(--papel);
        box-shadow: 0 2px 8px rgba(11, 37, 69, 0.15);
    }
    .sadj-card .label {
        font-family: 'Oswald', sans-serif;
        text-transform: uppercase;
        font-size: 0.78rem;
        letter-spacing: 1.5px;
        opacity: 0.75;
        margin-bottom: 0.2rem;
    }
    .sadj-card .value {
        font-size: 1.9rem;
        font-weight: 700;
        line-height: 1.1;
    }
    .sadj-card .sub {
        font-size: 0.85rem;
        opacity: 0.85;
        margin-top: 0.3rem;
    }

    /* Card de status (meta atingida / faltam X kg) */
    .sadj-status-ok {
        background: var(--verde-oliva);
        color: var(--papel);
        border-left: 6px solid var(--dourado);
    }
    .sadj-status-pending {
        background: var(--azul-medio);
        color: var(--papel);
        border-left: 6px solid var(--caqui);
    }

    /* Pódio de destaque */
    .sadj-podio {
        background: linear-gradient(135deg, var(--dourado) 0%, #B8954A 100%);
        border-radius: 10px;
        padding: 1.2rem 1.6rem;
        color: var(--azul-marinho);
        display: flex;
        align-items: center;
        gap: 1rem;
        box-shadow: 0 3px 10px rgba(201, 169, 97, 0.35);
    }
    .sadj-podio .medalha {
        font-size: 2.4rem;
        line-height: 1;
    }
    .sadj-podio .texto .titulo {
        font-family: 'Oswald', sans-serif;
        text-transform: uppercase;
        font-size: 0.78rem;
        letter-spacing: 1.5px;
        opacity: 0.8;
    }
    .sadj-podio .texto .nomes {
        font-size: 1.25rem;
        font-weight: 700;
    }

    /* Barra de progresso customizada */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, var(--azul-marinho), var(--caqui));
    }

    /* Cabeçalho de seção com divisor */
    .sadj-section-title {
        font-family: 'Oswald', sans-serif;
        text-transform: uppercase;
        font-size: 1rem;
        letter-spacing: 1.5px;
        color: var(--azul-medio);
        border-left: 4px solid var(--caqui);
        padding-left: 0.6rem;
        margin: 1.6rem 0 0.8rem 0;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: var(--azul-marinho);
    }
    section[data-testid="stSidebar"] * {
        color: var(--papel) !important;
    }
    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
        color: #0B2545 !important;
        background-color: var(--papel) !important;
    }

    /* DataFrame */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 2. INICIALIZAÇÃO DO FIREBASE (FIRESTORE) - cacheado como recurso singleton
@st.cache_resource
def get_db():
    if not firebase_admin._apps:
        firebase_creds = dict(st.secrets["textkey"])
        cred = credentials.Certificate(firebase_creds)
        firebase_admin.initialize_app(cred)
    return firestore.client()

try:
    db = get_db()
except Exception:
    st.error("Erro ao conectar ao Banco de Dados. Verifique os Secrets do Streamlit.")
    st.stop()


# 3. FUNÇÕES DE BANCO DE DADOS (com cache para reduzir leituras no Firestore)

@st.cache_data(ttl=120, show_spinner=False)
def buscar_cadetes():
    """Retorna um DataFrame com todos os cadetes cadastrados. Cache de 2 min."""
    docs = db.collection("cadetes").stream()
    lista_cadetes = []
    for doc in docs:
        dados = doc.to_dict()
        dados["id"] = doc.id
        lista_cadetes.append(dados)
    return pd.DataFrame(lista_cadetes)


@st.cache_data(ttl=60, show_spinner=False)
def buscar_arrecadacoes(mes_ano):
    """Retorna um DataFrame com as arrecadações do mês selecionado. Cache de 1 min."""
    docs = (
        db.collection("arrecadacoes").where("mes_ano", "==", mes_ano).stream()
    )
    lista_arrecadacoes = []
    for doc in docs:
        dados = doc.to_dict()
        lista_arrecadacoes.append(dados)
    return pd.DataFrame(lista_arrecadacoes)


def salvar_cadete(nome, turma, pelotao):
    """Salva um novo cadete no banco."""
    doc_ref = db.collection("cadetes").document()
    doc_ref.set(
        {
            "nome": nome,
            "turma": turma,
            "pelotao": pelotao,
        }
    )
    # Invalida caches afetados
    buscar_cadetes.clear()


def deletar_cadete(id_cadete):
    """Remove um cadete do banco de dados."""
    db.collection("cadetes").document(id_cadete).delete()
    buscar_cadetes.clear()


def salvar_doacao(id_cadete, mes_ano, arroz, feijao, macarrao):
    """Soma a nova doação de forma atômica via Increment, evitando race conditions
    quando múltiplos usuários lançam doações ao mesmo tempo."""
    doc_id = f"{id_cadete}_{mes_ano}"
    doc_ref = db.collection("arrecadacoes").document(doc_id)
    total = arroz + feijao + macarrao

    doc_ref.set(
        {
            "id_cadete": id_cadete,
            "mes_ano": mes_ano,
            "kg_arroz": Increment(arroz),
            "kg_feijao": Increment(feijao),
            "kg_macarrao": Increment(macarrao),
            "kg_total": Increment(total),
        },
        merge=True,
    )
    # Invalida cache do mês afetado
    buscar_arrecadacoes.clear()


# 4. CONTROLE DE ACESSO (AUTENTICAÇÃO)
st.sidebar.image("logo.png", use_container_width=True)
st.sidebar.header("🔑 Área Administrativa")
senha_input = st.sidebar.text_input("Digite a senha:", type="password")

SENHA_ADMIN = st.secrets.get("admin_password", "SADJ2026")

is_admin = False
if senha_input == SENHA_ADMIN:
    is_admin = True
    st.sidebar.success("Acesso Admin Liberado!")
elif senha_input != "":
    st.sidebar.error("Senha Incorreta.")

# Seleção do Mês de Referência (Global para visualização)
st.sidebar.markdown("---")
st.sidebar.header("📅 Consulta de Resultados")
meses_disponiveis = [
    "Junho 2026",
    "Julho 2026",
    "Agosto 2026",
    "Setembro 2026",
    "Outubro 2026",
    "Novembro 2026",
    "Dezembro 2026",
]
mes_selecionado = st.sidebar.selectbox("Visualizar dados do mês:", meses_disponiveis)

# Botão manual para forçar atualização dos dados (limpa o cache)
if st.sidebar.button("🔄 Atualizar dados agora"):
    buscar_cadetes.clear()
    buscar_arrecadacoes.clear()
    st.rerun()

# Navegação do App
if is_admin:
    menu = st.sidebar.radio(
        "Navegação:", ["Painel de Liderança", "Lançar Doação", "Gerenciar Cadetes"]
    )
else:
    menu = "Painel de Liderança"

# 5. RENDERIZAÇÃO DAS TELAS

# --- TELA 1: PAINEL DE LIDERANÇA ---
if menu == "Painel de Liderança":
    st.title(f"🏆 Arrecadação de Alimentos SADJ")
    st.caption(f"Campanha de referência: **{mes_selecionado}**")

    df_cadetes = buscar_cadetes()
    df_doacoes = buscar_arrecadacoes(mes_selecionado)

    if df_cadetes.empty:
        st.warning(
            "Nenhum cadete cadastrado no sistema ainda. Acesse como Admin para cadastrar."
        )
    else:
        if df_doacoes.empty:
            df_doacoes = pd.DataFrame(
                columns=[
                    "id_cadete",
                    "kg_arroz",
                    "kg_feijao",
                    "kg_macarrao",
                    "kg_total",
                ]
            )

        df_principal = pd.merge(
            df_cadetes,
            df_doacoes,
            left_on="id",
            right_on="id_cadete",
            how="left",
        )

        # --- CORREÇÃO DO ERRO KeyError ---
        # Garante que todas as colunas existam, mesmo nos registros antigos do Firebase
        colunas_pesos = ["kg_arroz", "kg_feijao", "kg_macarrao", "kg_total"]
        for col in colunas_pesos:
            if col not in df_principal.columns:
                df_principal[col] = 0.0

        # Preenche os valores nulos (quem não doou nada ainda) com zero
        df_principal[colunas_pesos] = df_principal[colunas_pesos].fillna(0.0)
        # ---------------------------------

        # Meta Individual: Mínimo 7kg no total E 2kg de cada tipo básico (vetorizado)
        cumpriu = (
            (df_principal["kg_total"] >= 7.0)
            & (df_principal["kg_arroz"] >= 2.0)
            & (df_principal["kg_feijao"] >= 2.0)
            & (df_principal["kg_macarrao"] >= 2.0)
        )
        df_principal["Meta Individual"] = cumpriu.map({True: "Cumprida", False: "Pendente"})

        total_geral_cfo = df_principal["kg_total"].sum()
        meta_cfo = 800.0
        porcentagem_meta = min(total_geral_cfo / meta_cfo, 1.0)

        st.markdown('<div class="sadj-section-title">📊 Progresso da Meta Geral do CFO</div>', unsafe_allow_html=True)

        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            st.markdown(
                f"""
                <div class="sadj-card">
                    <div class="label">Total Arrecadado</div>
                    <div class="value">{total_geral_cfo:.2f} kg</div>
                    <div class="sub">Meta geral: {meta_cfo:.0f} kg &nbsp;•&nbsp; {porcentagem_meta*100:.1f}% concluído</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_meta2:
            if total_geral_cfo >= meta_cfo:
                st.markdown(
                    """
                    <div class="sadj-card sadj-status-ok">
                        <div class="label">Status da Meta</div>
                        <div class="value">🎉 Atingida!</div>
                        <div class="sub">+1 Folga liberada para todo o CFO.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class="sadj-card sadj-status-pending">
                        <div class="label">Status da Meta</div>
                        <div class="value">Em andamento</div>
                        <div class="sub">Faltam {(meta_cfo - total_geral_cfo):.2f} kg para a folga geral.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.progress(porcentagem_meta)

        st.markdown('<div class="sadj-section-title">🔍 Filtrar Ranking</div>', unsafe_allow_html=True)
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            turmas = ["Todas"] + sorted(df_principal["turma"].unique().tolist())
            filtro_turma = st.selectbox("Filtrar por Turma:", turmas)
        with col_f2:
            pelotoes = ["Todos"] + sorted(df_principal["pelotao"].unique().tolist())
            filtro_pelotao = st.selectbox("Filtrar por Pelotão:", pelotoes)

        df_filtrado = df_principal
        if filtro_turma != "Todas":
            df_filtrado = df_filtrado[df_filtrado["turma"] == filtro_turma]
        if filtro_pelotao != "Todos":
            df_filtrado = df_filtrado[df_filtrado["pelotao"] == filtro_pelotao]

        df_filtrado = df_filtrado.sort_values(by="kg_total", ascending=False)

        df_exibicao = df_filtrado[
            [
                "nome",
                "turma",
                "pelotao",
                "kg_arroz",
                "kg_feijao",
                "kg_macarrao",
                "kg_total",
                "Meta Individual",
            ]
        ]
        df_exibicao.columns = [
            "Nome do Cadete",
            "Turma",
            "Pelotão",
            "Arroz",
            "Feijão",
            "Macarrão",
            "Total",
            "Status Meta",
        ]

        st.markdown('<div class="sadj-section-title">📋 Ranking de Cadetes</div>', unsafe_allow_html=True)
        st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

        st.markdown('<div class="sadj-section-title">⭐ Destaque da Consulta Atual</div>', unsafe_allow_html=True)

        if not df_filtrado.empty and df_filtrado["kg_total"].max() > 0:
            maior_peso = df_filtrado["kg_total"].max()
            destaques = df_filtrado[df_filtrado["kg_total"] == maior_peso]["nome"].tolist()
            st.markdown(
                f"""
                <div class="sadj-podio">
                    <div class="medalha">🥇</div>
                    <div class="texto">
                        <div class="titulo">Maior arrecadação do grupo filtrado</div>
                        <div class="nomes">{', '.join(destaques)} — {maior_peso:.2f} kg</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Nenhuma doação registrada para o grupo filtrado.")

# --- TELA 2: LANÇAR DOAÇÃO (ADMIN) ---
elif menu == "Lançar Doação" and is_admin:
    st.title("📝 Registro de Entrada de Alimentos")
    st.caption("Lançamento cumulativo — a pesagem informada é somada ao total já registrado no mês.")
    st.markdown("<br>", unsafe_allow_html=True)

    df_cadetes = buscar_cadetes()

    if df_cadetes.empty:
        st.error("Não há cadetes cadastrados. Vá na aba 'Gerenciar Cadetes' primeiro.")
    else:
        df_cadetes = df_cadetes.copy()
        df_cadetes["selecao"] = (
            df_cadetes["nome"] + " (" + df_cadetes["turma"] + " - " + df_cadetes["pelotao"] + ")"
        )

        with st.form("form_registro_alimento"):
            cadete_selecionado = st.selectbox("Selecione o Cadete:", df_cadetes["selecao"].tolist())

            # Seletor de mês independente para o formulário
            mes_doacao = st.selectbox("Mês de Referência da Doação:", meses_disponiveis)

            id_cadete = df_cadetes[df_cadetes["selecao"] == cadete_selecionado]["id"].values[0]

            col1, col2 = st.columns(2)
            with col1:
                arroz = st.number_input("Arroz (kg):", min_value=0.0, step=0.5, format="%.2f")
                macarrao = st.number_input("Macarrão (kg):", min_value=0.0, step=0.5, format="%.2f")
            with col2:
                feijao = st.number_input("Feijão (kg):", min_value=0.0, step=0.5, format="%.2f")

            enviar_doacao = st.form_submit_button("Somar Pesagem")

            if enviar_doacao:
                # Verifica se a soma total lançada não é zero
                if arroz + feijao + macarrao == 0:
                    st.warning("Insira um valor maior que zero para registrar a doação.")
                else:
                    salvar_doacao(id_cadete, mes_doacao, arroz, feijao, macarrao)
                    st.success(
                        f"Sucesso! Dados adicionados para {cadete_selecionado.split('(')[0].strip()} no mês de {mes_doacao}."
                    )

# --- TELA 3: GERENCIAR CADETES (ADMIN) ---
elif menu == "Gerenciar Cadetes" and is_admin:
    st.title("👤 Gerenciamento de Cadetes")

    tab1, tab2 = st.tabs(["➕ Cadastrar Cadete", "❌ Remover Cadete"])

    with tab1:
        with st.form("form_cadastro_cadete", clear_on_submit=True):
            nome_guerra = st.text_input("Nome de Guerra / Nome Completo:").strip()

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                turma = st.selectbox("Turma (Ano):", ["1º Ano", "2º Ano", "3º Ano", "4º Ano"])
            with col_c2:
                pelotao = st.selectbox(
                    "Pelotão:",
                    ["1º Pel", "2º Pel", "3º Pel", "4º Pel", "5º Pel", "6º Pel", "7º Pel", "8º Pel"],
                )

            enviar_cadete = st.form_submit_button("Cadastrar Cadete")

            if enviar_cadete:
                if nome_guerra == "":
                    st.error("O campo de nome não pode ficar em branco.")
                else:
                    salvar_cadete(nome_guerra, turma, pelotao)
                    st.success(f"Cadete '{nome_guerra}' cadastrado com sucesso!")

    with tab2:
        df_cadetes_remover = buscar_cadetes()
        if df_cadetes_remover.empty:
            st.info("Não há cadetes cadastrados para remover.")
        else:
            df_cadetes_remover = df_cadetes_remover.copy()
            df_cadetes_remover["selecao"] = (
                df_cadetes_remover["nome"] + " (" + df_cadetes_remover["turma"] + ")"
            )

            with st.form("form_remover_cadete"):
                cadete_remover = st.selectbox(
                    "Selecione o Cadete que deseja excluir:",
                    df_cadetes_remover["selecao"].tolist(),
                )

                id_cadete_remover = df_cadetes_remover[
                    df_cadetes_remover["selecao"] == cadete_remover
                ]["id"].values[0]

                confirmar_remocao = st.form_submit_button("Remover Cadete Definitivamente", type="primary")

                if confirmar_remocao:
                    deletar_cadete(id_cadete_remover)
                    st.success(f"{cadete_remover.split('(')[0].strip()} foi removido do sistema.")
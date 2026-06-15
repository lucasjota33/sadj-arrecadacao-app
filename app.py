import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Campanha de Arrecadação - SADJ", layout="wide")

# 2. INICIALIZAÇÃO DO FIREBASE (FIRESTORE)
# Utiliza st.secrets para conectar com segurança sem expor chaves no código
if not firebase_admin._apps:
    try:
        firebase_creds = dict(st.secrets["textkey"])
        cred = credentials.Certificate(firebase_creds)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(
            "Erro ao conectar ao Banco de Dados. Verifique os Secrets do Streamlit."
        )
        st.stop()

db = firestore.client()


# 3. FUNÇÕES DE BANCO DE DADOS
def buscar_cadetes():
    """Retorna um DataFrame com todos os cadetes cadastrados."""
    docs = db.collection("cadetes").stream()
    lista_cadetes = []
    for doc in docs:
        dados = doc.to_dict()
        dados["id"] = doc.id
        lista_cadetes.append(dados)
    return pd.DataFrame(lista_cadetes)


def buscar_arrecadacoes(mes_ano):
    """Retorna um DataFrame com as arrecadações do mês selecionado."""
    docs = (
        db.collection("arrecadacoes").where("mes_ano", "==", mes_ano).stream()
    )
    lista_arrecadacoes = []
    for doc in docs:
        dados = doc.to_dict()
        lista_arrecadacoes.append(dados)
    return pd.DataFrame(lista_arrecadacoes)


def salvar_cadete(nome, turma, companhia, pelotao):
    """Salva um novo cadete no banco."""
    doc_ref = db.collection("cadetes").document()
    doc_ref.set(
        {
            "nome": nome,
            "turma": turma,
            "companhia": companhia,
            "pelotao": pelotao,
        }
    )


def salvar_doacao(id_cadete, mes_ano, arroz, feijao, macarrao):
    """Registra ou atualiza a doação de um cadete para o mês específico."""
    doc_id = f"{id_cadete}_{mes_ano}"
    doc_ref = db.collection("arrecadacoes").document(doc_id)

    total = arroz + feijao + macarrao

    doc_ref.set(
        {
            "id_cadete": id_cadete,
            "mes_ano": mes_ano,
            "kg_arroz": arroz,
            "kg_feijao": feijao,
            "kg_macarrao": macarrao,
            "kg_total": total,
        }
    )


# 4. CONTROLE DE ACESSO (AUTENTICAÇÃO)
st.sidebar.header("🔑 Área Administrativa")
senha_input = st.sidebar.text_input("Digite a senha master:", type="password")

# Define a senha padrão (pode ser alterada via st.secrets para maior segurança)
SENHA_ADMIN = st.secrets.get("admin_password", "SADJ2026")

is_admin = False
if senha_input == SENHA_ADMIN:
    is_admin = True
    st.sidebar.success("Acesso Admin Liberado!")
elif senha_input != "":
    st.sidebar.error("Senha Incorreta.")

# Seleção do Mês de Referência (Global)
st.sidebar.markdown("---")
st.sidebar.header("📅 Período de Consulta")
meses_disponiveis = ["Junho 2026", "Julho 2026", "Agosto 2026"]
mes_selecionado = st.sidebar.selectbox("Escolha o mês:", meses_disponiveis)

# Navegação do App
if is_admin:
    menu = st.sidebar.radio(
        "Navegação:", ["Painel de Liderança", "Lançar Doação", "Cadastrar Cadete"]
    )
else:
    menu = "Painel de Liderança"

# 5. RENDERIZAÇÃO DAS TELAS

# --- TELA 1: PAINEL DE LIDERANÇA ---
if menu == "Painel de Liderança":
    st.title(f"🏆 Arrecadação de alimentos SADJ - {mes_selecionado}")

    # Buscar dados das duas coleções
    df_cadetes = buscar_cadetes()
    df_doacoes = buscar_arrecadacoes(mes_selecionado)

    if df_cadetes.empty:
        st.warning(
            "Nenhum cadete cadastrado no sistema ainda. Acesse como Admin para cadastrar."
        )
    else:
        # Se não houver doações, cria um DataFrame vazio com a estrutura correta para o merge
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

        # Junta os dados dos cadetes com as doações do mês corrente
        df_principal = pd.merge(
            df_cadetes,
            df_doacoes,
            left_on="id",
            right_on="id_cadete",
            how="left",
        )
        # Preenche os valores nulos (quem não doou nada ainda) com zero
        df_principal[
            ["kg_arroz", "kg_feijao", "kg_macarrao", "kg_total"]
        ] = df_principal[
            ["kg_arroz", "kg_feijao", "kg_macarrao", "kg_total"]
        ].fillna(
            0.0
        )

        # Cálculo da Meta Individual (Mínimo 7kg no total E 2kg de cada tipo)
        df_principal["Meta Individual"] = df_principal.apply(
            lambda r: "Cumprida (1 Folga)"
            if (
                r["kg_total"] >= 7.0
                and r["kg_arroz"] >= 2.0
                and r["kg_feijao"] >= 2.0
                and r["kg_macarrao"] >= 2.0
            )
            else "Pendente",
            axis=1,
        )

        # Métrica Geral do CFO (Meta Coletiva)
        total_geral_cfo = df_principal["kg_total"].sum()
        meta_cfo = 800.0

        st.subheader("📊 Progresso Meta Geral do CFO (800 kg)")
        porcentagem_meta = min(total_geral_cfo / meta_cfo, 1.0)
        st.progress(porcentagem_meta)

        col_meta1, col_meta2 = st.columns(2)
        col_meta1.metric("Total Arrecadado (CFO)", f"{total_geral_cfo:.2f} kg")
        if total_geral_cfo >= meta_cfo:
            col_meta2.success("🎉 META GERAL ATINGIDA! +1 Folga para todo o CFO!")
        else:
            col_meta2.info(
                f"Faltam {(meta_cfo - total_geral_cfo):.2f} kg para a folga geral."
            )

        st.markdown("---")

        # Filtros de Visualização Dinâmicos
        st.subheader("🔍 Filtrar Rankings")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            turmas = ["Todas"] + sorted(df_principal["turma"].unique().tolist())
            filtro_turma = st.selectbox("Filtrar por Turma:", turmas)
        with col_f2:
            cias = ["Todas"] + sorted(
                df_principal["companhia"].unique().tolist()
            )
            filtro_cia = st.selectbox("Filtrar por Companhia:", cias)
        with col_f3:
            pelotoes = ["Todos"] + sorted(
                df_principal["pelotao"].unique().tolist()
            )
            filtro_pelotao = st.selectbox("Filtrar por Pelotão:", pelotoes)

        # Aplicar filtros ao DataFrame que será exibido
        df_filtrado = df_principal.copy()
        if filtro_turma != "Todas":
            df_filtrado = df_filtrado[df_filtrado["turma"] == filtro_turma]
        if filtro_cia != "Todas":
            df_filtrado = df_filtrado[df_filtrado["companhia"] == filtro_cia]
        if filtro_pelotao != "Todos":
            df_filtrado = df_filtrado[df_filtrado["pelotao"] == filtro_pelotao]

        # Ordenar pelo maior volume total doado
        df_filtrado = df_filtrado.sort_values(by="kg_total", ascending=False)

        # Formatar tabela para exibição pública limpa
        df_exibicao = df_filtrado[
            [
                "nome",
                "turma",
                "companhia",
                "pelotao",
                "kg_arroz",
                "kg_feijao",
                "kg_macarrao",
                "kg_total",
                "Meta Individual",
            ]
        ].copy()
        df_exibicao.columns = [
            "Nome do Cadete",
            "Turma",
            "Companhia",
            "Pelotão",
            "Arroz (kg)",
            "Feijão (kg)",
            "Macarrão (kg)",
            "Total (kg)",
            "Status Meta",
        ]

        st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

        # Identificação automática de Destaques
        st.markdown("---")
        st.subheader("⭐ Destaques Atuais da Consulta")

        if not df_filtrado.empty and df_filtrado["kg_total"].max() > 0:
            maior_peso = df_filtrado["kg_total"].max()
            destaques = df_filtrado[df_filtrado["kg_total"] == maior_peso][
                "nome"
            ].tolist()
            st.success(
                f"🥇 **Destaque do grupo filtrado:** {', '.join(destaques)} com {maior_peso:.2f} kg!"
            )
        else:
            st.info("Nenhuma doação registrada para o grupo filtrado.")

# --- TELA 2: LANÇAR DOAÇÃO (ADMIN) ---
elif menu == "Lançar Doação" and is_admin:
    st.title("📝 Registro de Entrada de Alimentos")
    st.caption(f"Inserindo dados para o período: {mes_selecionado}")

    df_cadetes = buscar_cadetes()

    if df_cadetes.empty:
        st.error(
            "Não há cadetes cadastrados. Vá na aba 'Cadastrar Cadete' primeiro."
        )
    else:
        # Cria uma linha combinada para seleção fácil no formulário
        df_cadetes["selecao"] = (
            df_cadetes["nome"]
            + " ("
            + df_cadetes["turma"]
            + " - "
            + df_cadetes["pelotao"]
            + ")"
        )

        with st.form("form_registro_alimento"):
            cadete_selecionado = st.selectbox(
                "Selecione o Cadete:", df_cadetes["selecao"].tolist()
            )

            # Extrair o ID correspondente ao cadete selecionado
            id_cadete = df_cadetes[df_cadetes["selecao"] == cadete_selecionado][
                "id"
            ].values[0]

            col1, col2, col3 = st.columns(3)
            with col1:
                arroz = st.number_input(
                    "Quantidade de Arroz (kg):",
                    min_value=0.0,
                    step=0.5,
                    format="%.2f",
                )
            with col2:
                feijao = st.number_input(
                    "Quantidade de Feijão (kg):",
                    min_value=0.0,
                    step=0.5,
                    format="%.2f",
                )
            with col3:
                macarrao = st.number_input(
                    "Quantidade de Macarrão (kg):",
                    min_value=0.0,
                    step=0.5,
                    format="%.2f",
                )

            enviar_doacao = st.form_submit_button("Registrar / Atualizar Pesagem")

            if enviar_doacao:
                salvar_doacao(id_cadete, mes_selecionado, arroz, feijao, macarrao)
                st.success(
                    f"Sucesso! Dados salvos para {cadete_selecionado.split('(')[0].strip()} no mês {mes_selecionado}."
                )

# --- TELA 3: CADASTRAR CADETE (ADMIN) ---
elif menu == "Cadastrar Cadete" and is_admin:
    st.title("👤 Cadastro de Novos Cadetes")

    with st.form("form_cadastro_cadete", clear_on_submit=True):
        nome_guerra = st.text_input(
            "Nome de Guerra / Nome Completo do Cadete:"
        ).strip()

        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            turma = st.selectbox(
                "Turma (Ano):", ["1º Ano", "2º Ano", "3º Ano", "4º Ano"]
            )
        with col_c2:
            companhia = st.selectbox("Companhia:", ["1ª Cia", "2ª Cia", "3ª Cia"])
        with col_c3:
            pelotao = st.selectbox(
                "Pelotão:", ["1º Pel", "2º Pel", "3º Pel", "4º Pel"]
            )

        enviar_cadete = st.form_submit_button("Cadastrar Cadete")

        if enviar_cadete:
            if nome_guerra == "":
                st.error("O campo de nome não pode ficar em branco.")
            else:
                salvar_cadete(nome_guerra, turma, companhia, pelotao)
                st.success(f"Cadete '{nome_guerra}' cadastrado com sucesso!")
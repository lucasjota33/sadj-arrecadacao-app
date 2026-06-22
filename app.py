import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import Increment
import pandas as pd
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# 1. CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Campanha de Arrecadação - SADJ",
    page_icon="logo.png",
    layout="wide",
)

# ─────────────────────────────────────────────
# 2. FIREBASE
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
# 3. FUNÇÕES DE BANCO DE DADOS
# ─────────────────────────────────────────────

@st.cache_data(ttl=120, show_spinner=False)
def buscar_cadetes():
    docs = db.collection("cadetes").stream()
    lista = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        lista.append(d)
    return pd.DataFrame(lista)


@st.cache_data(ttl=60, show_spinner=False)
def buscar_arrecadacoes(mes_ano):
    docs = db.collection("arrecadacoes").where("mes_ano", "==", mes_ano).stream()
    lista = []
    for doc in docs:
        lista.append(doc.to_dict())
    return pd.DataFrame(lista)


@st.cache_data(ttl=30, show_spinner=False)
def buscar_historico(mes_ano):
    """Retorna o histórico de lançamentos do mês, ordenado do mais recente."""
    docs = (
        db.collection("historico")
        .where("mes_ano", "==", mes_ano)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(200)
        .stream()
    )
    lista = []
    for doc in docs:
        lista.append(doc.to_dict())
    return pd.DataFrame(lista)


def salvar_cadete(nome, turma, pelotao):
    doc_ref = db.collection("cadetes").document()
    doc_ref.set({"nome": nome, "turma": turma, "pelotao": pelotao})
    buscar_cadetes.clear()


def deletar_cadete(id_cadete):
    db.collection("cadetes").document(id_cadete).delete()
    buscar_cadetes.clear()


def _registrar_historico(id_cadete, nome_cadete, mes_ano, arroz, feijao, macarrao, tipo_operacao):
    """Grava um registro de auditoria na coleção 'historico'."""
    db.collection("historico").document().set({
        "id_cadete": id_cadete,
        "nome_cadete": nome_cadete,
        "mes_ano": mes_ano,
        "kg_arroz": arroz,
        "kg_feijao": feijao,
        "kg_macarrao": macarrao,
        "kg_total": arroz + feijao + macarrao,
        "tipo": tipo_operacao,   # "lançamento" ou "correção"
        "timestamp": datetime.now(timezone.utc),
    })
    buscar_historico.clear()


def salvar_doacao(id_cadete, nome_cadete, mes_ano, arroz, feijao, macarrao):
    """Soma a nova doação de forma atômica via Increment e registra histórico."""
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
    _registrar_historico(id_cadete, nome_cadete, mes_ano, arroz, feijao, macarrao, "lançamento")
    buscar_arrecadacoes.clear()


def corrigir_doacao(id_cadete, nome_cadete, mes_ano, arroz, feijao, macarrao):
    """Sobrescreve os valores do cadete no mês (não soma — corrige) e registra histórico."""
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
    _registrar_historico(id_cadete, nome_cadete, mes_ano, arroz, feijao, macarrao, "correção")
    buscar_arrecadacoes.clear()


# ─────────────────────────────────────────────
# 4. SIDEBAR / CONTROLE DE ACESSO
# ─────────────────────────────────────────────
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

st.sidebar.markdown("---")
st.sidebar.header("📅 Consulta de Resultados")
meses_disponiveis = [
    "Junho 2026", "Julho 2026", "Agosto 2026", "Setembro 2026",
    "Outubro 2026", "Novembro 2026", "Dezembro 2026",
]
mes_selecionado = st.sidebar.selectbox("Visualizar dados do mês:", meses_disponiveis)

if st.sidebar.button("🔄 Atualizar dados agora"):
    buscar_cadetes.clear()
    buscar_arrecadacoes.clear()
    buscar_historico.clear()
    st.rerun()

if is_admin:
    menu = st.sidebar.radio(
        "Navegação:",
        ["Painel de Liderança", "Lançar Doação", "Corrigir Doação", "Histórico", "Gerenciar Cadetes"],
    )
else:
    menu = "Painel de Liderança"


# ─────────────────────────────────────────────
# 5. HELPERS
# ─────────────────────────────────────────────
def montar_df_principal(mes_ano):
    df_cadetes = buscar_cadetes()
    df_doacoes = buscar_arrecadacoes(mes_ano)

    if df_doacoes.empty:
        df_doacoes = pd.DataFrame(
            columns=["id_cadete", "kg_arroz", "kg_feijao", "kg_macarrao", "kg_total"]
        )

    df = pd.merge(df_cadetes, df_doacoes, left_on="id", right_on="id_cadete", how="left")

    colunas_pesos = ["kg_arroz", "kg_feijao", "kg_macarrao", "kg_total"]
    for col in colunas_pesos:
        if col not in df.columns:
            df[col] = 0.0
    df[colunas_pesos] = df[colunas_pesos].fillna(0.0)

    cumpriu = (
        (df["kg_total"] >= 7.0)
        & (df["kg_arroz"] >= 2.0)
        & (df["kg_feijao"] >= 2.0)
        & (df["kg_macarrao"] >= 2.0)
    )
    df["Meta Individual"] = cumpriu.map({True: "✅ Cumprida", False: "⏳ Pendente"})
    return df


def lider_de_grupo(df, coluna_grupo):
    idx = df.groupby(coluna_grupo)["kg_total"].idxmax()
    return df.loc[idx, [coluna_grupo, "nome", "kg_total", "Meta Individual"]].reset_index(drop=True)


# ─────────────────────────────────────────────
# 6. TELA 1 — PAINEL DE LIDERANÇA
# ─────────────────────────────────────────────
if menu == "Painel de Liderança":
    st.title(f"🏆 Arrecadação de Alimentos SADJ — {mes_selecionado}")
    st.caption("Campanha SADJ · Alimentos: Arroz, Feijão e Macarrão")

    df_cadetes = buscar_cadetes()

    if df_cadetes.empty:
        st.warning("Nenhum cadete cadastrado no sistema ainda. Acesse como Admin para cadastrar.")
    else:
        df = montar_df_principal(mes_selecionado)
        df_com_doacao = df[df["kg_total"] > 0]

        # ── KPIs ─────────────────────────────────────────────────────
        total_geral = df["kg_total"].sum()
        meta_cfo = 800.0
        pct = min(total_geral / meta_cfo, 1.0)
        total_cadetes = len(df)
        meta_cumprida_count = (df["Meta Individual"] == "✅ Cumprida").sum()
        participantes = (df["kg_total"] > 0).sum()

        st.subheader("📊 Visão Geral da Campanha")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Arrecadado", f"{total_geral:.1f} kg", f"meta: {meta_cfo:.0f} kg")
        c2.metric("Metas Individuais Cumpridas", f"{meta_cumprida_count}", f"de {total_cadetes} cadetes")
        c3.metric("Cadetes Participantes", f"{participantes}", f"{total_cadetes - participantes} sem doação")
        c4.metric("Progresso da Meta Geral", f"{pct*100:.1f}%", f"faltam {max(meta_cfo - total_geral, 0):.1f} kg")

        st.progress(pct)

        if total_geral >= meta_cfo:
            st.success("🎉 META GERAL DO CFO ATINGIDA! +1 Folga Geral para todos os cadetes!")
        else:
            st.info(f"Faltam **{max(meta_cfo - total_geral, 0):.1f} kg** para a meta de 800 kg e a folga geral.")

        st.markdown("---")

        # ── BUSCA DE STATUS INDIVIDUAL ────────────────────────────────
        st.subheader("🔎 Consulta de Status Individual")
        busca_nome = st.text_input("Digite o nome (ou parte do nome) do cadete:", placeholder="Ex: Silva")

        if busca_nome.strip():
            resultado = df[df["nome"].str.contains(busca_nome.strip(), case=False, na=False)]
            if resultado.empty:
                st.warning("Nenhum cadete encontrado com esse nome.")
            else:
                for _, r in resultado.iterrows():
                    with st.container(border=True):
                        col_a, col_b = st.columns([2, 1])
                        with col_a:
                            st.markdown(f"**{r['nome']}** — {r['turma']} · {r['pelotao']}")
                            st.caption(f"Status da meta individual: {r['Meta Individual']}")

                            # Progresso por tipo de alimento
                            c_arroz, c_feijao, c_mac = st.columns(3)
                            c_arroz.metric("🌾 Arroz", f"{r['kg_arroz']:.1f} kg",
                                           delta=f"{r['kg_arroz'] - 2:.1f} kg da meta de 2 kg",
                                           delta_color="normal")
                            c_feijao.metric("🫘 Feijão", f"{r['kg_feijao']:.1f} kg",
                                            delta=f"{r['kg_feijao'] - 2:.1f} kg da meta de 2 kg",
                                            delta_color="normal")
                            c_mac.metric("🍝 Macarrão", f"{r['kg_macarrao']:.1f} kg",
                                         delta=f"{r['kg_macarrao'] - 2:.1f} kg da meta de 2 kg",
                                         delta_color="normal")

                        with col_b:
                            st.metric("Total doado", f"{r['kg_total']:.2f} kg")
                            falta_meta = max(7.0 - r["kg_total"], 0)
                            if falta_meta > 0:
                                st.caption(f"Faltam **{falta_meta:.2f} kg** para a meta de 7 kg.")
                            else:
                                st.caption("✅ Meta de 7 kg atingida!")

                            # Verifica se é destaque do pelotão
                            if not df_com_doacao.empty:
                                max_pel = df_com_doacao[df_com_doacao["pelotao"] == r["pelotao"]]["kg_total"].max()
                                max_turma = df_com_doacao[df_com_doacao["turma"] == r["turma"]]["kg_total"].max()
                                if r["kg_total"] == max_pel and r["kg_total"] > 0:
                                    st.success(f"🎖️ Destaque do {r['pelotao']}!")
                                if r["kg_total"] == max_turma and r["kg_total"] > 0:
                                    st.success(f"🎗️ Destaque da {r['turma']}!")

        st.markdown("---")

        # ── MAIOR DOADOR DO CFO ───────────────────────────────────────
        st.subheader("🥇 Maior Doador do CFO")
        if df_com_doacao.empty:
            st.info("Nenhuma doação registrada ainda.")
        else:
            maior_total = df_com_doacao["kg_total"].max()
            top_cfo = df_com_doacao[df_com_doacao["kg_total"] == maior_total]
            for _, row in top_cfo.iterrows():
                st.success(
                    f"🏅 **{row['nome']}** ({row['turma']} · {row['pelotao']}) "
                    f"— **{row['kg_total']:.2f} kg** no total  |  "
                    f"Arroz: {row['kg_arroz']:.1f} kg · Feijão: {row['kg_feijao']:.1f} kg · Macarrão: {row['kg_macarrao']:.1f} kg"
                )

        st.markdown("---")

        # ── DESTAQUES POR PELOTÃO E TURMA ────────────────────────────
        col_pel, col_turma = st.columns(2)
        with col_pel:
            st.subheader("🎖️ Destaque por Pelotão")
            st.caption("+1 Folga para o maior arrecadador de cada pelotão")
            if df_com_doacao.empty:
                st.info("Nenhuma doação registrada ainda.")
            else:
                lp = lider_de_grupo(df_com_doacao, "pelotao").sort_values("pelotao")
                lp.columns = ["Pelotão", "Cadete Destaque", "Total (kg)", "Meta Individual"]
                lp["Total (kg)"] = lp["Total (kg)"].map("{:.2f}".format)
                st.dataframe(lp, use_container_width=True, hide_index=True)

        with col_turma:
            st.subheader("🎗️ Destaque por Turma")
            st.caption("+1 Folga para o maior arrecadador de cada turma")
            if df_com_doacao.empty:
                st.info("Nenhuma doação registrada ainda.")
            else:
                lt = lider_de_grupo(df_com_doacao, "turma").sort_values("turma")
                lt.columns = ["Turma", "Cadete Destaque", "Total (kg)", "Meta Individual"]
                lt["Total (kg)"] = lt["Total (kg)"].map("{:.2f}".format)
                st.dataframe(lt, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── GRÁFICOS DE BARRAS ────────────────────────────────────────
        st.subheader("📊 Arrecadação por Pelotão e Turma")
        gc1, gc2 = st.columns(2)

        with gc1:
            st.caption("Por Pelotão")
            graf_pel = (
                df.groupby("pelotao")[["kg_arroz", "kg_feijao", "kg_macarrao"]]
                .sum()
                .rename(columns={"kg_arroz": "Arroz", "kg_feijao": "Feijão", "kg_macarrao": "Macarrão"})
                .sort_index()
            )
            st.bar_chart(graf_pel, use_container_width=True)

        with gc2:
            st.caption("Por Turma")
            graf_turma = (
                df.groupby("turma")[["kg_arroz", "kg_feijao", "kg_macarrao"]]
                .sum()
                .rename(columns={"kg_arroz": "Arroz", "kg_feijao": "Feijão", "kg_macarrao": "Macarrão"})
                .sort_index()
            )
            st.bar_chart(graf_turma, use_container_width=True)

        st.markdown("---")

        # ── RANKING COMPLETO ──────────────────────────────────────────
        st.subheader("📋 Ranking Completo de Cadetes")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            turmas = ["Todas"] + sorted(df["turma"].unique().tolist())
            filtro_turma = st.selectbox("Filtrar por Turma:", turmas)
        with col_f2:
            pelotoes = ["Todos"] + sorted(df["pelotao"].unique().tolist())
            filtro_pelotao = st.selectbox("Filtrar por Pelotão:", pelotoes)

        df_filtrado = df.copy()
        if filtro_turma != "Todas":
            df_filtrado = df_filtrado[df_filtrado["turma"] == filtro_turma]
        if filtro_pelotao != "Todos":
            df_filtrado = df_filtrado[df_filtrado["pelotao"] == filtro_pelotao]

        df_filtrado = df_filtrado.sort_values("kg_total", ascending=False)
        df_exibicao = df_filtrado[
            ["nome", "turma", "pelotao", "kg_arroz", "kg_feijao", "kg_macarrao", "kg_total", "Meta Individual"]
        ].copy()
        df_exibicao.columns = [
            "Nome do Cadete", "Turma", "Pelotão",
            "Arroz (kg)", "Feijão (kg)", "Macarrão (kg)", "Total (kg)", "Status Meta",
        ]
        for col in ["Arroz (kg)", "Feijão (kg)", "Macarrão (kg)", "Total (kg)"]:
            df_exibicao[col] = df_exibicao[col].map("{:.2f}".format)
        st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── RESUMOS POR GRUPO ─────────────────────────────────────────
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.subheader("📈 Resumo por Pelotão")
            resumo_pel = (
                df.groupby("pelotao")
                .agg(
                    Total=("kg_total", "sum"),
                    Participantes=("kg_total", lambda x: (x > 0).sum()),
                    Cadetes=("nome", "count"),
                    Metas_Cumpridas=("Meta Individual", lambda x: (x == "✅ Cumprida").sum()),
                )
                .reset_index()
                .sort_values("Total", ascending=False)
            )
            resumo_pel.columns = ["Pelotão", "Total (kg)", "Participantes", "Cadetes", "Metas Cumpridas"]
            resumo_pel["Total (kg)"] = resumo_pel["Total (kg)"].map("{:.2f}".format)
            st.dataframe(resumo_pel, use_container_width=True, hide_index=True)

        with res_col2:
            st.subheader("📈 Resumo por Turma")
            resumo_turma = (
                df.groupby("turma")
                .agg(
                    Total=("kg_total", "sum"),
                    Participantes=("kg_total", lambda x: (x > 0).sum()),
                    Cadetes=("nome", "count"),
                    Metas_Cumpridas=("Meta Individual", lambda x: (x == "✅ Cumprida").sum()),
                )
                .reset_index()
                .sort_values("Total", ascending=False)
            )
            resumo_turma.columns = ["Turma", "Total (kg)", "Participantes", "Cadetes", "Metas Cumpridas"]
            resumo_turma["Total (kg)"] = resumo_turma["Total (kg)"].map("{:.2f}".format)
            st.dataframe(resumo_turma, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# 7. TELA 2 — LANÇAR DOAÇÃO (ADMIN)
# ─────────────────────────────────────────────
elif menu == "Lançar Doação" and is_admin:
    st.title("📝 Registro de Entrada de Alimentos")
    st.info("💡 A nova pesagem será **somada** ao volume que o cadete já doou neste mês. Para corrigir um valor, use a tela **Corrigir Doação**.")

    df_cadetes = buscar_cadetes()
    if df_cadetes.empty:
        st.error("Não há cadetes cadastrados. Vá na aba 'Gerenciar Cadetes' primeiro.")
    else:
        df_cadetes = df_cadetes.copy()
        df_cadetes["selecao"] = (
            df_cadetes["nome"] + " (" + df_cadetes["turma"] + " - " + df_cadetes["pelotao"] + ")"
        )
        df_cadetes_sorted = df_cadetes.sort_values("nome")

        with st.form("form_registro_alimento"):
            cadete_selecionado = st.selectbox("Selecione o Cadete:", df_cadetes_sorted["selecao"].tolist())
            mes_doacao = st.selectbox("Mês de Referência da Doação:", meses_disponiveis)
            id_cadete = df_cadetes[df_cadetes["selecao"] == cadete_selecionado]["id"].values[0]
            nome_cadete = cadete_selecionado.split("(")[0].strip()

            col1, col2 = st.columns(2)
            with col1:
                arroz = st.number_input("Arroz (kg):", min_value=0.0, max_value=50.0, step=0.5, format="%.2f")
                macarrao = st.number_input("Macarrão (kg):", min_value=0.0, max_value=50.0, step=0.5, format="%.2f")
            with col2:
                feijao = st.number_input("Feijão (kg):", min_value=0.0, max_value=50.0, step=0.5, format="%.2f")

            enviar_doacao = st.form_submit_button("➕ Somar Pesagem")

            if enviar_doacao:
                if arroz + feijao + macarrao == 0:
                    st.warning("Insira um valor maior que zero para registrar a doação.")
                else:
                    salvar_doacao(id_cadete, nome_cadete, mes_doacao, arroz, feijao, macarrao)
                    st.success(f"Sucesso! Pesagem somada para **{nome_cadete}** em {mes_doacao}.")


# ─────────────────────────────────────────────
# 8. TELA 3 — CORRIGIR DOAÇÃO (ADMIN)
# ─────────────────────────────────────────────
elif menu == "Corrigir Doação" and is_admin:
    st.title("✏️ Correção de Doação")
    st.warning(
        "⚠️ Esta tela **substitui** o total do cadete no mês pelos valores informados abaixo. "
        "Use apenas para corrigir erros de lançamento. A operação fica registrada no histórico."
    )

    df_cadetes = buscar_cadetes()
    if df_cadetes.empty:
        st.error("Não há cadetes cadastrados.")
    else:
        df_cadetes = df_cadetes.copy()
        df_cadetes["selecao"] = (
            df_cadetes["nome"] + " (" + df_cadetes["turma"] + " - " + df_cadetes["pelotao"] + ")"
        )
        df_cadetes_sorted = df_cadetes.sort_values("nome")

        cadete_selecionado = st.selectbox(
            "Selecione o Cadete:", df_cadetes_sorted["selecao"].tolist(), key="sel_corr"
        )
        mes_correcao = st.selectbox("Mês de Referência:", meses_disponiveis, key="mes_corr")

        id_cadete = df_cadetes[df_cadetes["selecao"] == cadete_selecionado]["id"].values[0]
        nome_cadete = cadete_selecionado.split("(")[0].strip()

        # Mostra valores atuais antes de editar
        df_atual = buscar_arrecadacoes(mes_correcao)
        registro_atual = df_atual[df_atual["id_cadete"] == id_cadete] if not df_atual.empty else pd.DataFrame()

        if not registro_atual.empty:
            r = registro_atual.iloc[0]
            st.info(
                f"📦 Valores atuais para **{nome_cadete}** em {mes_correcao}: "
                f"Arroz: **{r.get('kg_arroz', 0):.2f} kg** · "
                f"Feijão: **{r.get('kg_feijao', 0):.2f} kg** · "
                f"Macarrão: **{r.get('kg_macarrao', 0):.2f} kg** · "
                f"Total: **{r.get('kg_total', 0):.2f} kg**"
            )
            val_arroz = float(r.get("kg_arroz", 0))
            val_feijao = float(r.get("kg_feijao", 0))
            val_mac = float(r.get("kg_macarrao", 0))
        else:
            st.info(f"Nenhum registro encontrado para **{nome_cadete}** em {mes_correcao}. Será criado um novo.")
            val_arroz, val_feijao, val_mac = 0.0, 0.0, 0.0

        with st.form("form_correcao"):
            st.markdown("**Informe os valores CORRETOS (totais, não o delta):**")
            col1, col2 = st.columns(2)
            with col1:
                novo_arroz = st.number_input("Arroz correto (kg):", min_value=0.0, max_value=200.0,
                                             value=val_arroz, step=0.5, format="%.2f")
                novo_mac = st.number_input("Macarrão correto (kg):", min_value=0.0, max_value=200.0,
                                           value=val_mac, step=0.5, format="%.2f")
            with col2:
                novo_feijao = st.number_input("Feijão correto (kg):", min_value=0.0, max_value=200.0,
                                              value=val_feijao, step=0.5, format="%.2f")

            confirmar = st.form_submit_button("✅ Confirmar Correção", type="primary")

            if confirmar:
                corrigir_doacao(id_cadete, nome_cadete, mes_correcao, novo_arroz, novo_feijao, novo_mac)
                st.success(
                    f"Correção aplicada para **{nome_cadete}** em {mes_correcao}. "
                    f"Novo total: {novo_arroz + novo_feijao + novo_mac:.2f} kg."
                )


# ─────────────────────────────────────────────
# 9. TELA 4 — HISTÓRICO (ADMIN)
# ─────────────────────────────────────────────
elif menu == "Histórico" and is_admin:
    st.title("📜 Histórico de Lançamentos")
    st.caption("Registro de todas as operações realizadas, em ordem cronológica decrescente.")

    mes_hist = st.selectbox("Selecionar mês:", meses_disponiveis, key="mes_hist")
    df_hist = buscar_historico(mes_hist)

    if df_hist.empty:
        st.info("Nenhum lançamento registrado para este mês ainda.")
    else:
        # Filtra por nome se quiser
        busca_hist = st.text_input("Filtrar por cadete:", placeholder="Digite parte do nome...")
        if busca_hist.strip():
            df_hist = df_hist[df_hist["nome_cadete"].str.contains(busca_hist.strip(), case=False, na=False)]

        df_exib = df_hist[["timestamp", "nome_cadete", "tipo", "kg_arroz", "kg_feijao", "kg_macarrao", "kg_total"]].copy()

        # Converte timestamp UTC para horário de Brasília (UTC-3)
        df_exib["timestamp"] = pd.to_datetime(df_exib["timestamp"], utc=True).dt.tz_convert("America/Sao_Paulo").dt.strftime("%d/%m/%Y %H:%M:%S")

        df_exib.columns = ["Data/Hora (BRT)", "Cadete", "Operação", "Arroz (kg)", "Feijão (kg)", "Macarrão (kg)", "Total (kg)"]
        for col in ["Arroz (kg)", "Feijão (kg)", "Macarrão (kg)", "Total (kg)"]:
            df_exib[col] = df_exib[col].map("{:.2f}".format)

        st.dataframe(df_exib, use_container_width=True, hide_index=True)
        st.caption(f"{len(df_exib)} registros exibidos.")


# ─────────────────────────────────────────────
# 10. TELA 5 — GERENCIAR CADETES (ADMIN)
# ─────────────────────────────────────────────
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
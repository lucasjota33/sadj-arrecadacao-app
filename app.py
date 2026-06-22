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
# CSS — ESTILO PAINEL ESCURO TIPO GARMIN
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Reset e fundo geral */
html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif;
    background-color: #1a1f2e !important;
    color: #e8eaf0 !important;
}

/* Sidebar escura */
section[data-testid="stSidebar"] {
    background-color: #111520 !important;
    border-right: 1px solid #2a3045 !important;
}
section[data-testid="stSidebar"] * { color: #c8ccd8 !important; }
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #1e2438 !important;
    color: #e8eaf0 !important;
    border: 1px solid #3a4060 !important;
}

/* Títulos */
h1 { font-size: 1.5rem !important; font-weight: 700 !important;
     color: #ffffff !important; letter-spacing: -0.3px; margin-bottom: 2px !important; }
h2 { font-size: 1rem !important; font-weight: 600 !important;
     color: #8b92a8 !important; text-transform: uppercase; letter-spacing: 1px; }
h3 { font-size: 0.8rem !important; font-weight: 500 !important;
     color: #6b7280 !important; text-transform: uppercase; letter-spacing: 1.2px; }

/* Remove borda padrão dos st.metric */
[data-testid="metric-container"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}

/* Cards principais (wrapper HTML customizado) */
.g-card {
    background: #1e2438;
    border: 1px solid #2a3350;
    border-radius: 14px;
    padding: 18px 20px 16px 20px;
    position: relative;
    overflow: hidden;
    height: 100%;
    min-height: 130px;
}
.g-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent, #4c8ef7);
    border-radius: 14px 14px 0 0;
}
.g-card .g-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.3px;
    color: #6b7a99;
    margin-bottom: 8px;
}
.g-card .g-value {
    font-size: 2.1rem;
    font-weight: 800;
    color: #ffffff;
    line-height: 1;
    margin-bottom: 6px;
}
.g-card .g-value.green  { color: #34d399; }
.g-card .g-value.yellow { color: #fbbf24; }
.g-card .g-value.blue   { color: #60a5fa; }
.g-card .g-value.orange { color: #fb923c; }
.g-card .g-sub {
    font-size: 0.75rem;
    color: #6b7a99;
    margin-top: 2px;
}
.g-card .g-icon {
    position: absolute;
    top: 16px; right: 18px;
    font-size: 1.6rem;
    opacity: 0.18;
}

/* Card de destaque (ouro) */
.g-card-gold {
    background: linear-gradient(135deg, #2a2210 0%, #1e2438 60%);
    border: 1px solid #5a4a1a;
}
.g-card-gold::before { background: #fbbf24; }

/* Card de meta atingida (verde) */
.g-card-green {
    background: linear-gradient(135deg, #0d2a1a 0%, #1e2438 60%);
    border: 1px solid #1a5a32;
}
.g-card-green::before { background: #34d399; }

/* Barra de progresso custom */
.g-progress-wrap {
    background: #2a3045;
    border-radius: 99px;
    height: 10px;
    width: 100%;
    margin: 10px 0 6px 0;
    overflow: hidden;
}
.g-progress-bar {
    height: 10px;
    border-radius: 99px;
    background: linear-gradient(90deg, #4c8ef7 0%, #34d399 100%);
    transition: width 0.4s ease;
}

/* Barra de progresso por alimento */
.g-mini-bar-wrap {
    background: #2a3045;
    border-radius: 99px;
    height: 6px;
    width: 100%;
    margin: 4px 0 10px 0;
    overflow: hidden;
}
.g-mini-bar { height: 6px; border-radius: 99px; }

/* Grid de cards de destaque (pelotão/turma) */
.g-leader-card {
    background: #1e2438;
    border: 1px solid #2a3350;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.g-leader-card .rank {
    font-size: 1.2rem;
    font-weight: 800;
    color: #fbbf24;
    min-width: 30px;
}
.g-leader-card .info { flex: 1; }
.g-leader-card .info .name {
    font-size: 0.9rem;
    font-weight: 600;
    color: #e8eaf0;
}
.g-leader-card .info .sub {
    font-size: 0.72rem;
    color: #6b7a99;
    margin-top: 2px;
}
.g-leader-card .kg {
    font-size: 1.1rem;
    font-weight: 700;
    color: #60a5fa;
    white-space: nowrap;
}
.g-leader-card .badge {
    font-size: 0.6rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 99px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.badge-ok   { background: #064e3b; color: #34d399; }
.badge-pend { background: #1e2438; color: #6b7a99; border: 1px solid #3a4060; }

/* Seção título */
.g-section {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #4b5470;
    margin: 28px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #2a3045;
}

/* Card de status individual */
.g-status-card {
    background: #1e2438;
    border: 1px solid #2a3350;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
}
.g-status-card .s-name {
    font-size: 1rem;
    font-weight: 700;
    color: #ffffff;
}
.g-status-card .s-sub {
    font-size: 0.72rem;
    color: #6b7a99;
    margin-bottom: 12px;
}
.g-status-card .s-foods {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 10px;
    margin-bottom: 10px;
}
.g-food-item .f-label {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #6b7a99;
    margin-bottom: 3px;
}
.g-food-item .f-val {
    font-size: 1.05rem;
    font-weight: 700;
    color: #e8eaf0;
}
.g-food-item .f-delta {
    font-size: 0.68rem;
    margin-top: 1px;
}
.f-delta.pos { color: #34d399; }
.f-delta.neg { color: #f87171; }

/* Ocultar elementos padrão do Streamlit que não queremos */
.stProgress { display: none; }
footer { display: none !important; }
#MainMenu { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }

/* Dataframe escuro */
[data-testid="stDataFrame"] iframe {
    filter: invert(1) hue-rotate(180deg);
    border-radius: 8px;
}

/* Inputs e selects no conteúdo */
.stTextInput input, .stSelectbox > div > div, .stNumberInput input {
    background-color: #1e2438 !important;
    color: #e8eaf0 !important;
    border: 1px solid #3a4060 !important;
    border-radius: 8px !important;
}
.stForm { border-color: #2a3045 !important; background: #1e2438 !important; border-radius: 12px !important; }
.stAlert { border-radius: 10px !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: #111520 !important; border-radius: 8px; }
.stTabs [data-baseweb="tab"] { color: #6b7a99 !important; }
.stTabs [aria-selected="true"] { color: #60a5fa !important; }

/* Botões */
.stButton > button {
    background: #2a3a6a !important;
    color: #e8eaf0 !important;
    border: 1px solid #3a4f8a !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stButton > button:hover { background: #3a4f8a !important; }
</style>
""", unsafe_allow_html=True)

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
# 3. BANCO DE DADOS
# ─────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def buscar_cadetes():
    docs = db.collection("cadetes").stream()
    lista = []
    for doc in docs:
        d = doc.to_dict(); d["id"] = doc.id; lista.append(d)
    return pd.DataFrame(lista)

@st.cache_data(ttl=60, show_spinner=False)
def buscar_arrecadacoes(mes_ano):
    docs = db.collection("arrecadacoes").where("mes_ano", "==", mes_ano).stream()
    lista = []
    for doc in docs: lista.append(doc.to_dict())
    return pd.DataFrame(lista)

@st.cache_data(ttl=30, show_spinner=False)
def buscar_historico(mes_ano):
    docs = (
        db.collection("historico")
        .where("mes_ano", "==", mes_ano)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(200).stream()
    )
    lista = []
    for doc in docs: lista.append(doc.to_dict())
    return pd.DataFrame(lista)

def salvar_cadete(nome, turma, pelotao):
    db.collection("cadetes").document().set({"nome": nome, "turma": turma, "pelotao": pelotao})
    buscar_cadetes.clear()

def deletar_cadete(id_cadete):
    db.collection("cadetes").document(id_cadete).delete()
    buscar_cadetes.clear()

def _registrar_historico(id_cadete, nome_cadete, mes_ano, arroz, feijao, macarrao, tipo):
    db.collection("historico").document().set({
        "id_cadete": id_cadete, "nome_cadete": nome_cadete, "mes_ano": mes_ano,
        "kg_arroz": arroz, "kg_feijao": feijao, "kg_macarrao": macarrao,
        "kg_total": arroz + feijao + macarrao, "tipo": tipo,
        "timestamp": datetime.now(timezone.utc),
    })
    buscar_historico.clear()

def salvar_doacao(id_cadete, nome_cadete, mes_ano, arroz, feijao, macarrao):
    doc_id = f"{id_cadete}_{mes_ano}"
    total = arroz + feijao + macarrao
    db.collection("arrecadacoes").document(doc_id).set({
        "id_cadete": id_cadete, "mes_ano": mes_ano,
        "kg_arroz": Increment(arroz), "kg_feijao": Increment(feijao),
        "kg_macarrao": Increment(macarrao), "kg_total": Increment(total),
    }, merge=True)
    _registrar_historico(id_cadete, nome_cadete, mes_ano, arroz, feijao, macarrao, "lançamento")
    buscar_arrecadacoes.clear()

def corrigir_doacao(id_cadete, nome_cadete, mes_ano, arroz, feijao, macarrao):
    doc_id = f"{id_cadete}_{mes_ano}"
    total = arroz + feijao + macarrao
    db.collection("arrecadacoes").document(doc_id).set({
        "id_cadete": id_cadete, "mes_ano": mes_ano,
        "kg_arroz": arroz, "kg_feijao": feijao,
        "kg_macarrao": macarrao, "kg_total": total,
    })
    _registrar_historico(id_cadete, nome_cadete, mes_ano, arroz, feijao, macarrao, "correção")
    buscar_arrecadacoes.clear()

# ─────────────────────────────────────────────
# 4. SIDEBAR
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
st.sidebar.header("📅 Mês de Referência")
meses_disponiveis = ["Junho 2026","Julho 2026","Agosto 2026","Setembro 2026",
                     "Outubro 2026","Novembro 2026","Dezembro 2026"]
mes_selecionado = st.sidebar.selectbox("Visualizar dados do mês:", meses_disponiveis)

if st.sidebar.button("🔄 Atualizar agora"):
    buscar_cadetes.clear(); buscar_arrecadacoes.clear(); buscar_historico.clear()
    st.rerun()

if is_admin:
    menu = st.sidebar.radio("Navegação:",
        ["Painel de Liderança","Lançar Doação","Corrigir Doação","Histórico","Gerenciar Cadetes"])
else:
    menu = "Painel de Liderança"

# ─────────────────────────────────────────────
# 5. HELPERS
# ─────────────────────────────────────────────
def montar_df_principal(mes_ano):
    df_c = buscar_cadetes()
    df_d = buscar_arrecadacoes(mes_ano)
    if df_d.empty:
        df_d = pd.DataFrame(columns=["id_cadete","kg_arroz","kg_feijao","kg_macarrao","kg_total"])
    df = pd.merge(df_c, df_d, left_on="id", right_on="id_cadete", how="left")
    for col in ["kg_arroz","kg_feijao","kg_macarrao","kg_total"]:
        if col not in df.columns: df[col] = 0.0
    df[["kg_arroz","kg_feijao","kg_macarrao","kg_total"]] = \
        df[["kg_arroz","kg_feijao","kg_macarrao","kg_total"]].fillna(0.0)
    cumpriu = ((df["kg_total"]>=7.0)&(df["kg_arroz"]>=2.0)
               &(df["kg_feijao"]>=2.0)&(df["kg_macarrao"]>=2.0))
    df["Meta Individual"] = cumpriu.map({True:"✅ Cumprida", False:"⏳ Pendente"})
    return df

def lider_de_grupo(df, col_grupo):
    idx = df.groupby(col_grupo)["kg_total"].idxmax()
    return df.loc[idx, [col_grupo,"nome","kg_total","Meta Individual"]].reset_index(drop=True)

def barra_html(pct, color="#4c8ef7", height=10):
    w = min(pct * 100, 100)
    return f"""<div class="g-progress-wrap" style="height:{height}px">
        <div class="g-progress-bar" style="width:{w}%;height:{height}px;background:{color}"></div>
    </div>"""

def mini_barra(kg, meta, color):
    pct = min(kg / meta, 1.0) if meta > 0 else 0
    return f"""<div class="g-mini-bar-wrap">
        <div class="g-mini-bar" style="width:{pct*100:.0f}%;background:{color}"></div>
    </div>"""

# ─────────────────────────────────────────────
# 6. PAINEL DE LIDERANÇA
# ─────────────────────────────────────────────
if menu == "Painel de Liderança":

    # Cabeçalho
    st.markdown(f"""
    <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:4px">
        <span style="font-size:1.5rem;font-weight:800;color:#fff">🏆 Campanha SADJ</span>
        <span style="font-size:0.8rem;font-weight:500;color:#4b5470;text-transform:uppercase;
              letter-spacing:1.2px">{mes_selecionado}</span>
    </div>
    <div style="font-size:0.75rem;color:#4b5470;margin-bottom:24px">
        Arroz · Feijão · Macarrão &nbsp;|&nbsp; Meta Geral: 800 kg &nbsp;|&nbsp; Período: 08 a 25 de junho
    </div>
    """, unsafe_allow_html=True)

    df_cadetes = buscar_cadetes()
    if df_cadetes.empty:
        st.warning("Nenhum cadete cadastrado. Acesse como Admin para cadastrar.")
        st.stop()

    df = montar_df_principal(mes_selecionado)
    df_com_doacao = df[df["kg_total"] > 0]

    total_geral    = df["kg_total"].sum()
    meta_cfo       = 800.0
    pct_meta       = min(total_geral / meta_cfo, 1.0)
    total_cadetes  = len(df)
    metas_ok       = (df["Meta Individual"] == "✅ Cumprida").sum()
    participantes  = (df["kg_total"] > 0).sum()
    sem_doacao     = total_cadetes - participantes
    faltam         = max(meta_cfo - total_geral, 0)

    # ── ROW 1: 4 cards KPI ──────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(f"""
        <div class="g-card" style="--accent:#4c8ef7">
            <div class="g-icon">⚖️</div>
            <div class="g-label">Total Arrecadado</div>
            <div class="g-value blue">{total_geral:.1f}<span style="font-size:1rem;font-weight:500;color:#4b6a99"> kg</span></div>
            {barra_html(pct_meta, "#4c8ef7", 7)}
            <div class="g-sub">{pct_meta*100:.1f}% da meta de {meta_cfo:.0f} kg</div>
        </div>""", unsafe_allow_html=True)

    with k2:
        cor_meta = "#34d399" if metas_ok == total_cadetes else "#fbbf24"
        st.markdown(f"""
        <div class="g-card" style="--accent:{cor_meta}">
            <div class="g-icon">🎯</div>
            <div class="g-label">Metas Individuais</div>
            <div class="g-value" style="color:{cor_meta}">{metas_ok}<span style="font-size:1rem;font-weight:400;color:#4b6a99"> / {total_cadetes}</span></div>
            {barra_html(metas_ok/total_cadetes if total_cadetes else 0, cor_meta, 7)}
            <div class="g-sub">{total_cadetes - metas_ok} cadetes ainda sem meta cumprida</div>
        </div>""", unsafe_allow_html=True)

    with k3:
        pct_part = participantes / total_cadetes if total_cadetes else 0
        st.markdown(f"""
        <div class="g-card" style="--accent:#a78bfa">
            <div class="g-icon">👥</div>
            <div class="g-label">Participantes</div>
            <div class="g-value" style="color:#a78bfa">{participantes}<span style="font-size:1rem;font-weight:400;color:#4b6a99"> / {total_cadetes}</span></div>
            {barra_html(pct_part, "#a78bfa", 7)}
            <div class="g-sub">{sem_doacao} cadetes ainda sem nenhuma doação</div>
        </div>""", unsafe_allow_html=True)

    with k4:
        if faltam == 0:
            st.markdown(f"""
            <div class="g-card g-card-green" style="--accent:#34d399">
                <div class="g-icon">🎉</div>
                <div class="g-label">Meta Geral do CFO</div>
                <div class="g-value green">Atingida!</div>
                <div class="g-sub" style="color:#34d399">+1 Folga geral para todos!</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="g-card" style="--accent:#fb923c">
                <div class="g-icon">🏁</div>
                <div class="g-label">Faltam para 800 kg</div>
                <div class="g-value orange">{faltam:.1f}<span style="font-size:1rem;font-weight:500;color:#4b6a99"> kg</span></div>
                {barra_html(pct_meta, "#fb923c", 7)}
                <div class="g-sub">Folga geral ao atingir a meta</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── ROW 2: cards de alimentos ────────────────────────────────────
    total_arroz   = df["kg_arroz"].sum()
    total_feijao  = df["kg_feijao"].sum()
    total_mac     = df["kg_macarrao"].sum()
    meta_unit     = meta_cfo / 3  # distribuição proporcional indicativa

    st.markdown('<div class="g-section">Composição da Arrecadação</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)

    for col, label, icon, kg, color in [
        (f1, "Arroz",    "🌾", total_arroz,  "#fbbf24"),
        (f2, "Feijão",   "🫘", total_feijao, "#fb923c"),
        (f3, "Macarrão", "🍝", total_mac,    "#a78bfa"),
    ]:
        with col:
            st.markdown(f"""
            <div class="g-card" style="--accent:{color};min-height:110px">
                <div class="g-icon">{icon}</div>
                <div class="g-label">{label}</div>
                <div class="g-value" style="color:{color};font-size:1.7rem">{kg:.1f}<span style="font-size:0.9rem;font-weight:500;color:#4b6a99"> kg</span></div>
                {barra_html(kg/total_geral if total_geral else 0, color, 5)}
                <div class="g-sub">{kg/total_geral*100:.1f}% do total arrecadado</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── BUSCA INDIVIDUAL ─────────────────────────────────────────────
    st.markdown('<div class="g-section">🔎 Consulta de Status Individual</div>', unsafe_allow_html=True)
    busca_nome = st.text_input("", placeholder="Digite o nome ou parte do nome do cadete...", label_visibility="collapsed")

    if busca_nome.strip():
        resultado = df[df["nome"].str.contains(busca_nome.strip(), case=False, na=False)]
        if resultado.empty:
            st.warning("Nenhum cadete encontrado com esse nome.")
        else:
            for _, r in resultado.iterrows():
                # Destaque de pelotão/turma
                is_dest_pel = is_dest_turma = False
                if not df_com_doacao.empty and r["kg_total"] > 0:
                    is_dest_pel   = r["kg_total"] == df_com_doacao[df_com_doacao["pelotao"]==r["pelotao"]]["kg_total"].max()
                    is_dest_turma = r["kg_total"] == df_com_doacao[df_com_doacao["turma"]==r["turma"]]["kg_total"].max()

                badges = ""
                if is_dest_pel:   badges += '<span style="background:#1a3a5a;color:#60a5fa;font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:99px;margin-left:6px">🎖️ DEST. PELOTÃO</span>'
                if is_dest_turma: badges += '<span style="background:#2a1a4a;color:#a78bfa;font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:99px;margin-left:6px">🎗️ DEST. TURMA</span>'

                pct_total = min(r["kg_total"] / 7.0, 1.0)
                falta_ind = max(7.0 - r["kg_total"], 0)

                d_arroz = r["kg_arroz"] - 2.0
                d_feijao = r["kg_feijao"] - 2.0
                d_mac = r["kg_macarrao"] - 2.0

                def delta_span(v):
                    sinal = "+" if v >= 0 else ""
                    cls = "pos" if v >= 0 else "neg"
                    return f'<span class="f-delta {cls}">{sinal}{v:.1f} kg vs meta</span>'

                st.markdown(f"""
                <div class="g-status-card">
                    <div style="display:flex;align-items:center;margin-bottom:4px">
                        <span class="s-name">{r['nome']}</span>{badges}
                    </div>
                    <div class="s-sub">{r['turma']} &nbsp;·&nbsp; {r['pelotao']} &nbsp;·&nbsp; {r['Meta Individual']}</div>
                    <div class="s-foods">
                        <div class="g-food-item">
                            <div class="f-label">🌾 Arroz</div>
                            <div class="f-val">{r['kg_arroz']:.1f} kg</div>
                            {mini_barra(r['kg_arroz'], 2.0, "#fbbf24")}
                            {delta_span(d_arroz)}
                        </div>
                        <div class="g-food-item">
                            <div class="f-label">🫘 Feijão</div>
                            <div class="f-val">{r['kg_feijao']:.1f} kg</div>
                            {mini_barra(r['kg_feijao'], 2.0, "#fb923c")}
                            {delta_span(d_feijao)}
                        </div>
                        <div class="g-food-item">
                            <div class="f-label">🍝 Macarrão</div>
                            <div class="f-val">{r['kg_macarrao']:.1f} kg</div>
                            {mini_barra(r['kg_macarrao'], 2.0, "#a78bfa")}
                            {delta_span(d_mac)}
                        </div>
                    </div>
                    <div style="display:flex;align-items:center;gap:12px">
                        <div style="flex:1">
                            {barra_html(pct_total, "#34d399" if falta_ind==0 else "#4c8ef7", 8)}
                        </div>
                        <div style="font-size:0.75rem;color:#6b7a99;white-space:nowrap">
                            {"✅ Meta de 7 kg atingida!" if falta_ind==0 else f"Faltam <b style='color:#60a5fa'>{falta_ind:.1f} kg</b> para os 7 kg"}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ── MAIOR DOADOR DO CFO ──────────────────────────────────────────
    st.markdown('<div class="g-section">🥇 Maior Doador do CFO</div>', unsafe_allow_html=True)

    if df_com_doacao.empty:
        st.info("Nenhuma doação registrada ainda.")
    else:
        maior_total = df_com_doacao["kg_total"].max()
        top_cfo = df_com_doacao[df_com_doacao["kg_total"] == maior_total]
        for _, row in top_cfo.iterrows():
            st.markdown(f"""
            <div class="g-card g-card-gold" style="min-height:90px;--accent:#fbbf24">
                <div class="g-icon" style="font-size:2rem;opacity:0.3">🏅</div>
                <div style="display:flex;align-items:center;gap:16px">
                    <div style="font-size:2rem">🥇</div>
                    <div>
                        <div style="font-size:1.05rem;font-weight:700;color:#fff">{row['nome']}</div>
                        <div style="font-size:0.75rem;color:#9b8a50;margin-top:2px">{row['turma']} · {row['pelotao']}</div>
                        <div style="font-size:0.72rem;color:#6b7a99;margin-top:4px">
                            🌾 {row['kg_arroz']:.1f} kg &nbsp;·&nbsp; 🫘 {row['kg_feijao']:.1f} kg &nbsp;·&nbsp; 🍝 {row['kg_macarrao']:.1f} kg
                        </div>
                    </div>
                    <div style="margin-left:auto;text-align:right">
                        <div style="font-size:2rem;font-weight:800;color:#fbbf24">{row['kg_total']:.1f}</div>
                        <div style="font-size:0.75rem;color:#9b8a50">kg no total</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── DESTAQUES POR PELOTÃO E TURMA ────────────────────────────────
    col_pel, col_turma = st.columns(2)

    with col_pel:
        st.markdown('<div class="g-section">🎖️ Destaque por Pelotão <span style="font-weight:400;color:#4b5470">+1 Folga</span></div>', unsafe_allow_html=True)
        if df_com_doacao.empty:
            st.info("Nenhuma doação registrada ainda.")
        else:
            lp = lider_de_grupo(df_com_doacao, "pelotao").sort_values("pelotao")
            for _, row in lp.iterrows():
                badge_cls = "badge-ok" if row["Meta Individual"] == "✅ Cumprida" else "badge-pend"
                badge_txt = "Meta ✓" if row["Meta Individual"] == "✅ Cumprida" else "Pendente"
                st.markdown(f"""
                <div class="g-leader-card">
                    <div class="rank">🎖</div>
                    <div class="info">
                        <div class="name">{row['nome']}</div>
                        <div class="sub">{row['pelotao']}</div>
                    </div>
                    <span class="badge {badge_cls}">{badge_txt}</span>
                    <div class="kg">{row['kg_total']:.1f} kg</div>
                </div>
                """, unsafe_allow_html=True)

    with col_turma:
        st.markdown('<div class="g-section">🎗️ Destaque por Turma <span style="font-weight:400;color:#4b5470">+1 Folga</span></div>', unsafe_allow_html=True)
        if df_com_doacao.empty:
            st.info("Nenhuma doação registrada ainda.")
        else:
            lt = lider_de_grupo(df_com_doacao, "turma").sort_values("turma")
            for _, row in lt.iterrows():
                badge_cls = "badge-ok" if row["Meta Individual"] == "✅ Cumprida" else "badge-pend"
                badge_txt = "Meta ✓" if row["Meta Individual"] == "✅ Cumprida" else "Pendente"
                st.markdown(f"""
                <div class="g-leader-card">
                    <div class="rank">🎗</div>
                    <div class="info">
                        <div class="name">{row['nome']}</div>
                        <div class="sub">{row['turma']}</div>
                    </div>
                    <span class="badge {badge_cls}">{badge_txt}</span>
                    <div class="kg">{row['kg_total']:.1f} kg</div>
                </div>
                """, unsafe_allow_html=True)

    # ── GRÁFICOS ─────────────────────────────────────────────────────
    st.markdown('<div class="g-section">📊 Arrecadação por Grupo</div>', unsafe_allow_html=True)
    gc1, gc2 = st.columns(2)

    with gc1:
        st.caption("Por Pelotão")
        graf_pel = (df.groupby("pelotao")[["kg_arroz","kg_feijao","kg_macarrao"]].sum()
                    .rename(columns={"kg_arroz":"Arroz","kg_feijao":"Feijão","kg_macarrao":"Macarrão"})
                    .sort_index())
        st.bar_chart(graf_pel, use_container_width=True)

    with gc2:
        st.caption("Por Turma")
        graf_turma = (df.groupby("turma")[["kg_arroz","kg_feijao","kg_macarrao"]].sum()
                      .rename(columns={"kg_arroz":"Arroz","kg_feijao":"Feijão","kg_macarrao":"Macarrão"})
                      .sort_index())
        st.bar_chart(graf_turma, use_container_width=True)

    # ── RANKING COMPLETO ─────────────────────────────────────────────
    st.markdown('<div class="g-section">📋 Ranking Completo</div>', unsafe_allow_html=True)
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
    df_exibicao = df_filtrado[["nome","turma","pelotao","kg_arroz","kg_feijao","kg_macarrao","kg_total","Meta Individual"]].copy()
    df_exibicao.columns = ["Nome do Cadete","Turma","Pelotão","Arroz (kg)","Feijão (kg)","Macarrão (kg)","Total (kg)","Status Meta"]
    for col in ["Arroz (kg)","Feijão (kg)","Macarrão (kg)","Total (kg)"]:
        df_exibicao[col] = df_exibicao[col].map("{:.2f}".format)
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

    # ── RESUMOS ──────────────────────────────────────────────────────
    st.markdown('<div class="g-section">📈 Resumo por Grupo</div>', unsafe_allow_html=True)
    res1, res2 = st.columns(2)

    with res1:
        st.caption("Por Pelotão")
        rp = (df.groupby("pelotao").agg(
            Total=("kg_total","sum"), Participantes=("kg_total", lambda x:(x>0).sum()),
            Cadetes=("nome","count"), Metas=("Meta Individual", lambda x:(x=="✅ Cumprida").sum())
        ).reset_index().sort_values("Total", ascending=False))
        rp.columns = ["Pelotão","Total (kg)","Participantes","Cadetes","Metas Cumpridas"]
        rp["Total (kg)"] = rp["Total (kg)"].map("{:.2f}".format)
        st.dataframe(rp, use_container_width=True, hide_index=True)

    with res2:
        st.caption("Por Turma")
        rt = (df.groupby("turma").agg(
            Total=("kg_total","sum"), Participantes=("kg_total", lambda x:(x>0).sum()),
            Cadetes=("nome","count"), Metas=("Meta Individual", lambda x:(x=="✅ Cumprida").sum())
        ).reset_index().sort_values("Total", ascending=False))
        rt.columns = ["Turma","Total (kg)","Participantes","Cadetes","Metas Cumpridas"]
        rt["Total (kg)"] = rt["Total (kg)"].map("{:.2f}".format)
        st.dataframe(rt, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# 7. LANÇAR DOAÇÃO
# ─────────────────────────────────────────────
elif menu == "Lançar Doação" and is_admin:
    st.title("📝 Registro de Entrada de Alimentos")
    st.info("💡 A nova pesagem será **somada** ao volume já registrado. Para corrigir, use **Corrigir Doação**.")
    df_cadetes = buscar_cadetes()
    if df_cadetes.empty:
        st.error("Não há cadetes cadastrados.")
    else:
        df_cadetes = df_cadetes.copy()
        df_cadetes["selecao"] = df_cadetes["nome"] + " (" + df_cadetes["turma"] + " - " + df_cadetes["pelotao"] + ")"
        df_cadetes_sorted = df_cadetes.sort_values("nome")
        with st.form("form_lancamento"):
            cadete_sel = st.selectbox("Cadete:", df_cadetes_sorted["selecao"].tolist())
            mes_doacao = st.selectbox("Mês:", meses_disponiveis)
            id_cadete  = df_cadetes[df_cadetes["selecao"]==cadete_sel]["id"].values[0]
            nome_cadete = cadete_sel.split("(")[0].strip()
            c1, c2 = st.columns(2)
            with c1:
                arroz    = st.number_input("Arroz (kg):",    min_value=0.0, max_value=50.0, step=0.5, format="%.2f")
                macarrao = st.number_input("Macarrão (kg):", min_value=0.0, max_value=50.0, step=0.5, format="%.2f")
            with c2:
                feijao   = st.number_input("Feijão (kg):",   min_value=0.0, max_value=50.0, step=0.5, format="%.2f")
            if st.form_submit_button("➕ Somar Pesagem"):
                if arroz + feijao + macarrao == 0:
                    st.warning("Insira um valor maior que zero.")
                else:
                    salvar_doacao(id_cadete, nome_cadete, mes_doacao, arroz, feijao, macarrao)
                    st.success(f"Pesagem somada para **{nome_cadete}** em {mes_doacao}.")


# ─────────────────────────────────────────────
# 8. CORRIGIR DOAÇÃO
# ─────────────────────────────────────────────
elif menu == "Corrigir Doação" and is_admin:
    st.title("✏️ Correção de Doação")
    st.warning("⚠️ Esta tela **substitui** o total do cadete pelos valores informados. Operação registrada no histórico.")
    df_cadetes = buscar_cadetes()
    if df_cadetes.empty:
        st.error("Não há cadetes cadastrados.")
    else:
        df_cadetes = df_cadetes.copy()
        df_cadetes["selecao"] = df_cadetes["nome"] + " (" + df_cadetes["turma"] + " - " + df_cadetes["pelotao"] + ")"
        cadete_sel  = st.selectbox("Cadete:", df_cadetes.sort_values("nome")["selecao"].tolist(), key="sel_corr")
        mes_corr    = st.selectbox("Mês:", meses_disponiveis, key="mes_corr")
        id_cadete   = df_cadetes[df_cadetes["selecao"]==cadete_sel]["id"].values[0]
        nome_cadete = cadete_sel.split("(")[0].strip()
        df_atual    = buscar_arrecadacoes(mes_corr)
        reg         = df_atual[df_atual["id_cadete"]==id_cadete] if not df_atual.empty else pd.DataFrame()
        if not reg.empty:
            r = reg.iloc[0]
            st.info(f"Valores atuais — Arroz: **{r.get('kg_arroz',0):.2f}** · Feijão: **{r.get('kg_feijao',0):.2f}** · Macarrão: **{r.get('kg_macarrao',0):.2f}** kg")
            va, vf, vm = float(r.get("kg_arroz",0)), float(r.get("kg_feijao",0)), float(r.get("kg_macarrao",0))
        else:
            st.info("Nenhum registro encontrado. Será criado um novo.")
            va = vf = vm = 0.0
        with st.form("form_correcao"):
            st.markdown("**Valores CORRETOS (totais):**")
            c1, c2 = st.columns(2)
            with c1:
                na = st.number_input("Arroz (kg):",    min_value=0.0, max_value=200.0, value=va, step=0.5, format="%.2f")
                nm = st.number_input("Macarrão (kg):", min_value=0.0, max_value=200.0, value=vm, step=0.5, format="%.2f")
            with c2:
                nf = st.number_input("Feijão (kg):",   min_value=0.0, max_value=200.0, value=vf, step=0.5, format="%.2f")
            if st.form_submit_button("✅ Confirmar Correção", type="primary"):
                corrigir_doacao(id_cadete, nome_cadete, mes_corr, na, nf, nm)
                st.success(f"Correção aplicada. Novo total: {na+nf+nm:.2f} kg.")


# ─────────────────────────────────────────────
# 9. HISTÓRICO
# ─────────────────────────────────────────────
elif menu == "Histórico" and is_admin:
    st.title("📜 Histórico de Lançamentos")
    st.caption("Todas as operações em ordem cronológica decrescente.")
    mes_hist = st.selectbox("Mês:", meses_disponiveis, key="mes_hist")
    df_hist  = buscar_historico(mes_hist)
    if df_hist.empty:
        st.info("Nenhum lançamento registrado para este mês.")
    else:
        busca = st.text_input("Filtrar por cadete:", placeholder="Digite parte do nome...")
        if busca.strip():
            df_hist = df_hist[df_hist["nome_cadete"].str.contains(busca.strip(), case=False, na=False)]
        df_e = df_hist[["timestamp","nome_cadete","tipo","kg_arroz","kg_feijao","kg_macarrao","kg_total"]].copy()
        df_e["timestamp"] = pd.to_datetime(df_e["timestamp"], utc=True).dt.tz_convert("America/Sao_Paulo").dt.strftime("%d/%m/%Y %H:%M:%S")
        df_e.columns = ["Data/Hora (BRT)","Cadete","Operação","Arroz (kg)","Feijão (kg)","Macarrão (kg)","Total (kg)"]
        for col in ["Arroz (kg)","Feijão (kg)","Macarrão (kg)","Total (kg)"]:
            df_e[col] = df_e[col].map("{:.2f}".format)
        st.dataframe(df_e, use_container_width=True, hide_index=True)
        st.caption(f"{len(df_e)} registros exibidos.")


# ─────────────────────────────────────────────
# 10. GERENCIAR CADETES
# ─────────────────────────────────────────────
elif menu == "Gerenciar Cadetes" and is_admin:
    st.title("👤 Gerenciamento de Cadetes")
    tab1, tab2 = st.tabs(["➕ Cadastrar Cadete","❌ Remover Cadete"])
    with tab1:
        with st.form("form_cadastro", clear_on_submit=True):
            nome = st.text_input("Nome de Guerra / Nome Completo:").strip()
            c1, c2 = st.columns(2)
            with c1: turma   = st.selectbox("Turma:", ["1º Ano","2º Ano","3º Ano","4º Ano"])
            with c2: pelotao = st.selectbox("Pelotão:", ["1º Pel","2º Pel","3º Pel","4º Pel","5º Pel","6º Pel","7º Pel","8º Pel"])
            if st.form_submit_button("Cadastrar Cadete"):
                if not nome: st.error("Nome não pode ficar em branco.")
                else:
                    salvar_cadete(nome, turma, pelotao)
                    st.success(f"Cadete '{nome}' cadastrado!")
    with tab2:
        df_rem = buscar_cadetes()
        if df_rem.empty:
            st.info("Não há cadetes para remover.")
        else:
            df_rem = df_rem.copy()
            df_rem["selecao"] = df_rem["nome"] + " (" + df_rem["turma"] + ")"
            with st.form("form_remover"):
                cadete_rem = st.selectbox("Cadete a remover:", df_rem["selecao"].tolist())
                id_rem = df_rem[df_rem["selecao"]==cadete_rem]["id"].values[0]
                if st.form_submit_button("Remover Definitivamente", type="primary"):
                    deletar_cadete(id_rem)
                    st.success(f"{cadete_rem.split('(')[0].strip()} removido.")
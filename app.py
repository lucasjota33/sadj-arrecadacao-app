import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import Increment
import pandas as pd
from datetime import datetime, timezone
import base64

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

# ─────────────────────────────────────────────
# 1. CONFIGURAÇÃO DA PÁGINA & SESSÃO
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Campanha de Arrecadação - SADJ",
    page_icon="logo.png",
    layout="wide",
)

if "cadete_logado" not in st.session_state:
    st.session_state.cadete_logado = None

# ─────────────────────────────────────────────
# CSS — ESTILO PAINEL CLARO
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Reset e fundo geral */
html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif;
    background-color: #f8f9fa !important;
    color: #1f2937 !important;
}

/* Sidebar clara */
section[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e5e7eb !important;
}
section[data-testid="stSidebar"] * { color: #374151 !important; }
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #ffffff !important;
    color: #1f2937 !important;
    border: 1px solid #d1d5db !important;
}

/* Títulos */
h1 { font-size: 1.5rem !important; font-weight: 700 !important;
     color: #111827 !important; letter-spacing: -0.3px; margin-bottom: 2px !important; }
h2 { font-size: 1rem !important; font-weight: 600 !important;
     color: #4b5563 !important; text-transform: uppercase; letter-spacing: 1px; }
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
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 18px 20px 16px 20px;
    position: relative;
    overflow: hidden;
    height: 100%;
    min-height: 130px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.g-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent, #3b82f6);
    border-radius: 14px 14px 0 0;
}
.g-card .g-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.3px;
    color: #6b7280;
    margin-bottom: 8px;
}
.g-card .g-value {
    font-size: 2.1rem;
    font-weight: 800;
    color: #111827;
    line-height: 1;
    margin-bottom: 6px;
}
.g-card .g-value.green  { color: #059669; }
.g-card .g-value.yellow { color: #d97706; }
.g-card .g-value.blue   { color: #2563eb; }
.g-card .g-value.orange { color: #ea580c; }
.g-card .g-sub {
    font-size: 0.75rem;
    color: #6b7280;
    margin-top: 2px;
}
.g-card .g-icon {
    position: absolute;
    top: 16px; right: 18px;
    font-size: 1.6rem;
    opacity: 0.1;
    color: #111827;
}

/* Card de destaque (ouro) */
.g-card-gold {
    background: linear-gradient(135deg, #fffbeb 0%, #ffffff 60%);
    border: 1px solid #fde68a;
}
.g-card-gold::before { background: #f59e0b; }

/* Card de meta atingida (verde) */
.g-card-green {
    background: linear-gradient(135deg, #ecfdf5 0%, #ffffff 60%);
    border: 1px solid #a7f3d0;
}
.g-card-green::before { background: #10b981; }

/* Barra de progresso custom */
.g-progress-wrap {
    background: #f3f4f6;
    border-radius: 99px;
    height: 10px;
    width: 100%;
    margin: 10px 0 6px 0;
    overflow: hidden;
}
.g-progress-bar {
    height: 10px;
    border-radius: 99px;
    background: linear-gradient(90deg, #3b82f6 0%, #10b981 100%);
    transition: width 0.4s ease;
}

/* Barra de progresso por alimento */
.g-mini-bar-wrap {
    background: #f3f4f6;
    border-radius: 99px;
    height: 6px;
    width: 100%;
    margin: 4px 0 10px 0;
    overflow: hidden;
}
.g-mini-bar { height: 6px; border-radius: 99px; }

/* Grid de cards de destaque (pelotão/turma) */
.g-leader-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.g-leader-card .rank {
    font-size: 1.2rem;
    font-weight: 800;
    color: #f59e0b;
    min-width: 30px;
}
.g-leader-card .info { flex: 1; }
.g-leader-card .info .name {
    font-size: 0.9rem;
    font-weight: 700;
    color: #111827;
}
.g-leader-card .info .sub {
    font-size: 0.72rem;
    color: #6b7280;
    margin-top: 2px;
}
.g-leader-card .kg {
    font-size: 1.1rem;
    font-weight: 700;
    color: #2563eb;
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
.badge-ok   { background: #d1fae5; color: #065f46; }
.badge-pend { background: #f3f4f6; color: #4b5563; border: 1px solid #d1d5db; }

/* Seção título */
.g-section {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #4b5563;
    margin: 28px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #e5e7eb;
}

/* Card de status individual */
.g-status-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.g-status-card .s-name {
    font-size: 1rem;
    font-weight: 700;
    color: #111827;
}
.g-status-card .s-sub {
    font-size: 0.72rem;
    color: #6b7280;
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
    color: #6b7280;
    margin-bottom: 3px;
}
.g-food-item .f-val {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1f2937;
}
.g-food-item .f-delta {
    font-size: 0.68rem;
    margin-top: 1px;
}
.f-delta.pos { color: #059669; }
.f-delta.neg { color: #dc2626; }

/* Ocultar elementos padrão do Streamlit que não queremos */
.stProgress { display: none; }
footer { display: none !important; }
#MainMenu { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }

/* Inputs e selects no conteúdo */
.stTextInput input, .stSelectbox > div > div, .stNumberInput input {
    background-color: #ffffff !important;
    color: #1f2937 !important;
    border: 1px solid #d1d5db !important;
    border-radius: 8px !important;
}
.stForm { border-color: #e5e7eb !important; background: #ffffff !important; border-radius: 12px !important; }
.stAlert { border-radius: 10px !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: #f8f9fa !important; border-radius: 8px; }
.stTabs [data-baseweb="tab"] { color: #4b5563 !important; }
.stTabs [aria-selected="true"] { color: #2563eb !important; font-weight: 600 !important; }

/* Botões */
.stButton > button {
    background: #ffffff !important;
    color: #1f2937 !important;
    border: 1px solid #d1d5db !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stButton > button:hover { background: #f3f4f6 !important; border-color: #9ca3af !important; }
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

@st.cache_data(ttl=60, show_spinner=False)
def buscar_folgas(mes_gozo):
    docs = db.collection("folgas").where("mes_gozo", "==", mes_gozo).stream()
    lista = []
    for doc in docs: lista.append(doc.to_dict())
    return pd.DataFrame(lista)

@st.cache_data(ttl=60, show_spinner=False)
def buscar_status_mes(mes_ano):
    doc = db.collection("meses_status").document(mes_ano).get()
    if not doc.exists:
        return False
    return doc.to_dict().get("encerrado", False)

def set_status_mes(mes_ano, encerrado):
    db.collection("meses_status").document(mes_ano).set({
        "mes_ano": mes_ano,
        "encerrado": encerrado,
        "updated_at": datetime.now(timezone.utc),
    }, merge=True)


def salvar_cadete(nome, turma, pelotao, senha=None):
    doc_data = {"nome": nome, "turma": turma, "pelotao": pelotao}
    if senha: doc_data["senha"] = senha
    db.collection("cadetes").document().set(doc_data)
    buscar_cadetes.clear()

def deletar_cadete(id_cadete):
    # 1. Deletar cadete
    db.collection("cadetes").document(id_cadete).delete()
    
    # 2. Buscar e deletar folgas associadas ao cadete
    folgas_docs = db.collection("folgas").where("id_cadete", "==", id_cadete).stream()
    for doc in folgas_docs:
        db.collection("folgas").document(doc.id).delete()
        
    buscar_cadetes.clear()
    buscar_folgas.clear()

def atualizar_senha_cadete(id_cadete, senha):
    db.collection("cadetes").document(id_cadete).update({"senha": senha})
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

def salvar_datas_folga(id_cadete, nome_cadete, turma, pelotao, mes_gozo, datas_list):
    doc_id = f"{id_cadete}_{mes_gozo}"
    datas_str = [d.strftime("%d/%m/%Y") for d in datas_list if d is not None]
    db.collection("folgas").document(doc_id).set({
        "id_cadete": id_cadete,
        "nome": nome_cadete,
        "turma": turma,
        "pelotao": pelotao,
        "mes_gozo": mes_gozo,
        "datas": datas_str,
        "timestamp": datetime.now(timezone.utc)
    })
    buscar_folgas.clear()


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
    buscar_cadetes.clear(); buscar_arrecadacoes.clear(); buscar_historico.clear(); buscar_folgas.clear(); buscar_status_mes.clear()
    st.rerun()

if is_admin:
    st.sidebar.markdown("### 📌 Status da Arrecadação")
    mes_status_selecionado = st.sidebar.selectbox("Mês para controle:", meses_disponiveis, key="mes_status")
    status_encerrado = buscar_status_mes(mes_status_selecionado)
    if status_encerrado:
        st.sidebar.success(f"Arrecadação de {mes_status_selecionado} está encerrada.")
        if st.sidebar.button("🔄 Retomar arrecadação", key="btn_reabrir"):
            set_status_mes(mes_status_selecionado, False)
            buscar_status_mes.clear()
            st.experimental_rerun()
    else:
        st.sidebar.info(f"Arrecadação de {mes_status_selecionado} está aberta.")
        if st.sidebar.button("✅ Encerrar arrecadação", key="btn_encerrar"):
            set_status_mes(mes_status_selecionado, True)
            buscar_status_mes.clear()
            st.experimental_rerun()

    menu = st.sidebar.radio("Navegação:",
        ["Painel de Liderança", "Minhas Folgas", "Lançar Doação", "Corrigir Doação", "Relatório de Folgas", "Histórico", "Gerenciar Cadetes"])
else:
    menu = st.sidebar.radio("Navegação:", ["Painel de Liderança", "Minhas Folgas"])

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

def calcular_folgas_cadete(id_cadete, mes_gozo):
    """Calcula as folgas de um cadete baseando-se no mês anterior ao mes_gozo"""
    try:
        idx = meses_disponiveis.index(mes_gozo)
    except ValueError:
        return 0, ["Mês selecionado inválido."]
        
    if idx == 0:
        return 0, ["Nenhuma campanha anterior a este mês para gerar folgas."]
    
    mes_arrecadacao = meses_disponiveis[idx - 1]
    df = montar_df_principal(mes_arrecadacao)
    
    if df.empty: return 0, ["Sem dados na campanha anterior."]
    
    cad = df[df["id"] == id_cadete]
    if cad.empty: return 0, ["Cadete não encontrado na campanha anterior."]
    r = cad.iloc[0]

    qtd_folgas = 0
    motivos = []

    # 1. Meta Individual
    if r["Meta Individual"] == "✅ Cumprida":
        qtd_folgas += 1
        motivos.append("✅ Meta Individual (+1)")

    # 2. Meta Geral
    if df["kg_total"].sum() > 800:
        qtd_folgas += 1
        motivos.append("🎉 Meta Geral do CFO (+1)")

    # 3. Destaques
    df_com_doacao = df[df["kg_total"] > 0]
    if r["kg_total"] > 0:
        if r["kg_total"] == df_com_doacao[df_com_doacao["pelotao"] == r["pelotao"]]["kg_total"].max():
            qtd_folgas += 1
            motivos.append("🎖️ Destaque do Pelotão (+1)")
        if r["kg_total"] == df_com_doacao[df_com_doacao["turma"] == r["turma"]]["kg_total"].max():
            qtd_folgas += 1
            motivos.append("🎗️ Destaque da Turma (+1)")

    return qtd_folgas, motivos

def lider_de_grupo(df, col_grupo):
    idx = df.groupby(col_grupo)["kg_total"].idxmax()
    return df.loc[idx, [col_grupo,"nome","kg_total","Meta Individual"]].reset_index(drop=True)

def barra_html(pct, color="#3b82f6", height=10):
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

    st.markdown(f"""
    <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:4px">
        <span style="font-size:1.5rem;font-weight:800;color:#111827">🏆 Campanha SADJ</span>
        <span style="font-size:0.8rem;font-weight:500;color:#6b7280;text-transform:uppercase;
              letter-spacing:1.2px">{mes_selecionado}</span>
    </div>
    <div style="font-size:0.75rem;color:#6b7280;margin-bottom:24px">
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

    # ── ROW 1: 4 cards KPI
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(f"""
        <div class="g-card" style="--accent:#3b82f6">
            <div class="g-icon">⚖️</div>
            <div class="g-label">Total Arrecadado</div>
            <div class="g-value blue">{total_geral:.1f}<span style="font-size:1rem;font-weight:500;color:#6b7280"> kg</span></div>
            {barra_html(pct_meta, "#3b82f6", 7)}
            <div class="g-sub">{pct_meta*100:.1f}% da meta de {meta_cfo:.0f} kg</div>
        </div>""", unsafe_allow_html=True)

    with k2:
        cor_meta = "#10b981" if metas_ok == total_cadetes else "#f59e0b"
        st.markdown(f"""
        <div class="g-card" style="--accent:{cor_meta}">
            <div class="g-icon">🎯</div>
            <div class="g-label">Metas Individuais</div>
            <div class="g-value" style="color:{cor_meta}">{metas_ok}<span style="font-size:1rem;font-weight:400;color:#6b7280"> / {total_cadetes}</span></div>
            {barra_html(metas_ok/total_cadetes if total_cadetes else 0, cor_meta, 7)}
            <div class="g-sub">{total_cadetes - metas_ok} cadetes ainda sem meta cumprida</div>
        </div>""", unsafe_allow_html=True)

    with k3:
        pct_part = participantes / total_cadetes if total_cadetes else 0
        st.markdown(f"""
        <div class="g-card" style="--accent:#8b5cf6">
            <div class="g-icon">👥</div>
            <div class="g-label">Participantes</div>
            <div class="g-value" style="color:#8b5cf6">{participantes}<span style="font-size:1rem;font-weight:400;color:#6b7280"> / {total_cadetes}</span></div>
            {barra_html(pct_part, "#8b5cf6", 7)}
            <div class="g-sub">{sem_doacao} cadetes ainda sem nenhuma doação</div>
        </div>""", unsafe_allow_html=True)

    with k4:
        if faltam == 0:
            st.markdown(f"""
            <div class="g-card g-card-green" style="--accent:#10b981">
                <div class="g-icon">🎉</div>
                <div class="g-label">Meta Geral do CFO</div>
                <div class="g-value green">Atingida!</div>
                <div class="g-sub" style="color:#059669">+1 Folga geral para todos!</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="g-card" style="--accent:#f97316">
                <div class="g-icon">🏁</div>
                <div class="g-label">Faltam para 800 kg</div>
                <div class="g-value orange">{faltam:.1f}<span style="font-size:1rem;font-weight:500;color:#6b7280"> kg</span></div>
                {barra_html(pct_meta, "#f97316", 7)}
                <div class="g-sub">Folga geral ao atingir a meta</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── ROW 2: cards de alimentos
    total_arroz   = df["kg_arroz"].sum()
    total_feijao  = df["kg_feijao"].sum()
    total_mac     = df["kg_macarrao"].sum()

    st.markdown('<div class="g-section">Composição da Arrecadação</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)

    for col, label, icon, kg, color in [
        (f1, "Arroz",    "🌾", total_arroz,  "#f59e0b"),
        (f2, "Feijão",   "🫘", total_feijao, "#f97316"),
        (f3, "Macarrão", "🍝", total_mac,    "#8b5cf6"),
    ]:
        with col:
            st.markdown(f"""
            <div class="g-card" style="--accent:{color};min-height:110px">
                <div class="g-icon">{icon}</div>
                <div class="g-label">{label}</div>
                <div class="g-value" style="color:{color};font-size:1.7rem">{kg:.1f}<span style="font-size:0.9rem;font-weight:500;color:#6b7280"> kg</span></div>
                {barra_html(kg/total_geral if total_geral else 0, color, 5)}
                <div class="g-sub">{kg/total_geral*100:.1f}% do total arrecadado</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── BUSCA INDIVIDUAL
    st.markdown('<div class="g-section">🔎 Consulta de Status Individual</div>', unsafe_allow_html=True)
    busca_nome = st.text_input("", placeholder="Digite o nome ou parte do nome do cadete...", label_visibility="collapsed")

    if busca_nome.strip():
        resultado = df[df["nome"].str.contains(busca_nome.strip(), case=False, na=False)]
        if resultado.empty:
            st.warning("Nenhum cadete encontrado com esse nome.")
        else:
            for _, r in resultado.iterrows():
                is_dest_pel = is_dest_turma = False
                if not df_com_doacao.empty and r["kg_total"] > 0:
                    is_dest_pel   = r["kg_total"] == df_com_doacao[df_com_doacao["pelotao"]==r["pelotao"]]["kg_total"].max()
                    is_dest_turma = r["kg_total"] == df_com_doacao[df_com_doacao["turma"]==r["turma"]]["kg_total"].max()

                badges = ""
                if is_dest_pel:   badges += '<span style="background:#dbeafe;color:#1e3a8a;font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:99px;margin-left:6px">🎖️ DEST. PELOTÃO</span>'
                if is_dest_turma: badges += '<span style="background:#f3e8ff;color:#581c87;font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:99px;margin-left:6px">🎗️ DEST. TURMA</span>'

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
                            {mini_barra(r['kg_arroz'], 2.0, "#f59e0b")}
                            {delta_span(d_arroz)}
                        </div>
                        <div class="g-food-item">
                            <div class="f-label">🫘 Feijão</div>
                            <div class="f-val">{r['kg_feijao']:.1f} kg</div>
                            {mini_barra(r['kg_feijao'], 2.0, "#f97316")}
                            {delta_span(d_feijao)}
                        </div>
                        <div class="g-food-item">
                            <div class="f-label">🍝 Macarrão</div>
                            <div class="f-val">{r['kg_macarrao']:.1f} kg</div>
                            {mini_barra(r['kg_macarrao'], 2.0, "#8b5cf6")}
                            {delta_span(d_mac)}
                        </div>
                    </div>
                    <div style="display:flex;align-items:center;gap:12px">
                        <div style="flex:1">
                            {barra_html(pct_total, "#10b981" if falta_ind==0 else "#3b82f6", 8)}
                        </div>
                        <div style="font-size:0.75rem;color:#6b7280;white-space:nowrap">
                            {"✅ Meta de 7 kg atingida!" if falta_ind==0 else f"Faltam <b style='color:#3b82f6'>{falta_ind:.1f} kg</b> para os 7 kg"}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ── MAIOR DOADOR DO CFO
    st.markdown('<div class="g-section">🥇 Maior Doador do CFO</div>', unsafe_allow_html=True)

    if df_com_doacao.empty:
        st.info("Nenhuma doação registrada ainda.")
    else:
        maior_total = df_com_doacao["kg_total"].max()
        top_cfo = df_com_doacao[df_com_doacao["kg_total"] == maior_total]
        for _, row in top_cfo.iterrows():
            st.markdown(f"""
            <div class="g-card g-card-gold" style="min-height:90px;--accent:#f59e0b">
                <div class="g-icon" style="font-size:2rem;opacity:0.1">🏅</div>
                <div style="display:flex;align-items:center;gap:16px">
                    <div style="font-size:2rem">🥇</div>
                    <div>
                        <div style="font-size:1.05rem;font-weight:700;color:#111827">{row['nome']}</div>
                        <div style="font-size:0.75rem;color:#b45309;margin-top:2px">{row['turma']} · {row['pelotao']}</div>
                        <div style="font-size:0.72rem;color:#6b7280;margin-top:4px">
                            🌾 {row['kg_arroz']:.1f} kg &nbsp;·&nbsp; 🫘 {row['kg_feijao']:.1f} kg &nbsp;·&nbsp; 🍝 {row['kg_macarrao']:.1f} kg
                        </div>
                    </div>
                    <div style="margin-left:auto;text-align:right">
                        <div style="font-size:2rem;font-weight:800;color:#f59e0b">{row['kg_total']:.1f}</div>
                        <div style="font-size:0.75rem;color:#b45309">kg no total</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── DESTAQUES POR PELOTÃO E TURMA
    col_pel, col_turma = st.columns(2)

    with col_pel:
        st.markdown('<div class="g-section">🎖️ Destaque por Pelotão <span style="font-weight:400;color:#6b7280">+1 Folga</span></div>', unsafe_allow_html=True)
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
        st.markdown('<div class="g-section">🎗️ Destaque por Turma <span style="font-weight:400;color:#6b7280">+1 Folga</span></div>', unsafe_allow_html=True)
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

    # ── GRÁFICOS
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

    # ── RANKING COMPLETO
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

    # ── RESUMOS
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
# 7. MINHAS FOLGAS (CADETES)
# ─────────────────────────────────────────────
elif menu == "Minhas Folgas":
    st.title("🏖️ Gerenciador de Folgas")
    st.caption("Verifique suas metas atingidas e agende os dias de folga no calendário.")

    df_cadetes = buscar_cadetes()
    
    if st.session_state.cadete_logado is None:
        opcoes = ["-- Selecione seu nome --", "➕ SOU NOVO E QUERO ME CADASTRAR"]
        
        if not df_cadetes.empty:
            df_cadetes["selecao"] = df_cadetes["nome"] + " (" + df_cadetes["turma"] + " - " + df_cadetes["pelotao"] + ")"
            opcoes += df_cadetes.sort_values("nome")["selecao"].tolist()

        escolha = st.selectbox("Quem é você?", opcoes)

        if escolha == "➕ SOU NOVO E QUERO ME CADASTRAR":
            with st.form("form_novo_cadete"):
                nome_novo = st.text_input("Nome de Guerra / Nome Completo:").strip()
                c1, c2 = st.columns(2)
                with c1: turma_novo = st.selectbox("Turma:", ["1º Ano","2º Ano","3º Ano","4º Ano"])
                with c2: pelotao_novo = st.selectbox("Pelotão:", ["1º Pel","2º Pel","3º Pel","4º Pel","5º Pel","6º Pel","7º Pel","8º Pel"])
                senha_nova = st.text_input("Crie uma senha de acesso:", type="password")
                
                if st.form_submit_button("Cadastrar e Acessar"):
                    if not nome_novo or not senha_nova:
                        st.error("Preencha todos os campos, incluindo a senha.")
                    else:
                        salvar_cadete(nome_novo, turma_novo, pelotao_novo, senha_nova)
                        st.success("Conta criada! Selecione seu nome na lista para fazer login.")
                        st.rerun()

        elif escolha != "-- Selecione seu nome --":
            cadete_row = df_cadetes[df_cadetes["selecao"] == escolha].iloc[0]
            senha_db = cadete_row.get("senha", None)

            if pd.isna(senha_db) or not senha_db:
                st.warning("Você ainda não tem uma senha cadastrada.")
                nova_senha = st.text_input("Crie uma senha de acesso agora:", type="password")
                if st.button("Salvar Senha e Entrar"):
                    if nova_senha:
                        atualizar_senha_cadete(cadete_row["id"], nova_senha)
                        st.session_state.cadete_logado = cadete_row["id"]
                        st.rerun()
                    else:
                        st.error("A senha não pode ser vazia.")
            else:
                senha_digitada = st.text_input("Digite sua senha:", type="password")
                if st.button("Entrar"):
                    if senha_digitada == senha_db:
                        st.session_state.cadete_logado = cadete_row["id"]
                        st.rerun()
                    else:
                        st.error("Senha Incorreta!")
    
    else: # Cadete logado
        cad_logado_row = df_cadetes[df_cadetes["id"] == st.session_state.cadete_logado].iloc[0]
        st.success(f"Logado como: **{cad_logado_row['nome']}**")
        if st.button("Sair (Logout)"):
            st.session_state.cadete_logado = None
            st.rerun()
        
        st.markdown("---")
        
        # Só permite agendar nos meses a partir de Julho (pois Junho foi a doação base)
        meses_gozo_permitidos = meses_disponiveis[1:] 
        mes_gozo = st.selectbox(
            "Selecione o mês para gozar as folgas (referentes à campanha do mês anterior):", 
            meses_gozo_permitidos
        )
        
        qtd_folgas, motivos = calcular_folgas_cadete(st.session_state.cadete_logado, mes_gozo)
        
        if qtd_folgas == 0:
            st.info(f"Você não obteve folgas disponíveis para gozar em {mes_gozo}.")
            for m in motivos: st.write(f"- {m}")
        else:
            st.markdown(f"### 🎉 Você conquistou **{qtd_folgas}** folga(s) para usar em {mes_gozo}!")
            for m in motivos:
                st.markdown(f"- {m}")
            
            mes_arrecadacao = meses_disponiveis[meses_disponiveis.index(mes_gozo) - 1]
            if not buscar_status_mes(mes_arrecadacao):
                st.warning(f"A arrecadação de {mes_arrecadacao} ainda não foi encerrada pela administração.")
                st.info("Quando o mês for encerrado, você poderá agendar suas folgas para o mês selecionado.")
            else:
                st.markdown("#### Agende suas folgas abaixo:")
                df_folgas_db = buscar_folgas(mes_gozo)
                folgas_ja_salvas = []
                if not df_folgas_db.empty:
                    registro = df_folgas_db[df_folgas_db["id_cadete"] == st.session_state.cadete_logado]
                    if not registro.empty:
                        folgas_ja_salvas = registro.iloc[0].get("datas", [])
                
                with st.form("form_agendar_folgas"):
                    col_datas = st.columns(min(qtd_folgas, 4))
                    datas_selecionadas = []
                    
                    for i in range(qtd_folgas):
                        with col_datas[i % 4]: # Evita quebrar layout se houver mais de 4 folgas
                            try:
                                val_padrao = datetime.strptime(folgas_ja_salvas[i], "%d/%m/%Y").date() if i < len(folgas_ja_salvas) else None
                            except:
                                val_padrao = None
                            d = st.date_input(f"Data da Folga {i+1}", value=val_padrao, format="DD/MM/YYYY")
                            datas_selecionadas.append(d)
                    
                    if st.form_submit_button("Salvar Datas", type="primary"):
                        salvar_datas_folga(
                            st.session_state.cadete_logado, 
                            cad_logado_row['nome'], 
                            cad_logado_row['turma'], 
                            cad_logado_row['pelotao'], 
                            mes_gozo, 
                            datas_selecionadas
                        )
                        st.success("Suas folgas foram agendadas com sucesso!")


# ─────────────────────────────────────────────
# 8. RELATÓRIO DE FOLGAS (ADMIN)
# ─────────────────────────────────────────────
elif menu == "Relatório de Folgas" and is_admin:
    st.title("🖨️ Relatório de Folgas Agendadas")
    st.info("Aqui você visualiza e gerencia todas as folgas marcadas pelos cadetes.")
    
    mes_relatorio = st.selectbox("Selecione o mês de gozo:", meses_disponiveis)
    df_f = buscar_folgas(mes_relatorio)
    
    if df_f.empty:
        st.warning("Nenhuma folga agendada para este mês ainda.")
    else:
        df_export = df_f[["nome", "turma", "pelotao", "datas"]].copy()
        df_export.columns = ["Cadete", "Turma", "Pelotão", "Datas Agendadas"]
        df_export["Datas Agendadas"] = df_export["Datas Agendadas"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
        df_export = df_export.sort_values(by=["Turma", "Pelotão", "Cadete"])
        
        st.dataframe(df_export, use_container_width=True, hide_index=True)
        
        st.markdown("### Exportar Dados")
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            csv = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar como CSV (Excel)",
                data=csv,
                file_name=f"folgas_{mes_relatorio}.csv",
                mime="text/csv",
            )
            
        with col_exp2:
            if FPDF is None:
                st.error("Para habilitar o PDF, rode 'pip install fpdf' e reinicie o app.")
            else:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(190, 10, txt=f"Relatorio de Folgas - {mes_relatorio}", ln=True, align='C')
                pdf.ln(10)
                
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(60, 8, "Cadete", 1)
                pdf.cell(30, 8, "Turma", 1)
                pdf.cell(30, 8, "Pelotao", 1)
                pdf.cell(70, 8, "Datas", 1)
                pdf.ln()
                
                pdf.set_font("Arial", '', 9)
                for _, row in df_export.iterrows():
                    # Tratar caracteres especiais para o PDF padrao
                    nome_str = str(row['Cadete']).encode('latin-1', 'replace').decode('latin-1')
                    turma_str = str(row['Turma']).encode('latin-1', 'replace').decode('latin-1')
                    pel_str = str(row['Pelotão']).encode('latin-1', 'replace').decode('latin-1')
                    dt_str = str(row['Datas Agendadas']).encode('latin-1', 'replace').decode('latin-1')
                    
                    pdf.cell(60, 8, nome_str, 1)
                    pdf.cell(30, 8, turma_str, 1)
                    pdf.cell(30, 8, pel_str, 1)
                    pdf.cell(70, 8, dt_str, 1)
                    pdf.ln()
                
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.download_button(
                    label="📄 Baixar como PDF",
                    data=pdf_bytes,
                    file_name=f"folgas_{mes_relatorio}.pdf",
                    mime="application/pdf"
                )

        # SEÇÃO PARA DELETAR FOLGA
        st.markdown("---")
        st.markdown("### 🗑️ Remover Registro de Folga")
        df_f_del = df_f.copy()
        df_f_del["selecao"] = df_f_del["nome"] + " (" + df_f_del["turma"] + " - " + df_f_del["pelotao"] + ")"
        
        with st.form("form_deletar_folga"):
            st.warning("Isto fará o cadete perder as datas marcadas e ele precisará agendar novamente.")
            folga_a_remover = st.selectbox("Selecione o registro para apagar:", df_f_del["selecao"].tolist())
            
            if st.form_submit_button("Deletar Registro", type="primary"):
                id_cad_del = df_f_del[df_f_del["selecao"] == folga_a_remover].iloc[0]["id_cadete"]
                db.collection("folgas").document(f"{id_cad_del}_{mes_relatorio}").delete()
                buscar_folgas.clear()
                st.success(f"Registro de folga de {folga_a_remover.split('(')[0].strip()} removido com sucesso!")
                st.rerun()

# ─────────────────────────────────────────────
# 9. LANÇAR DOAÇÃO
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
# 10. CORRIGIR DOAÇÃO
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
# 11. HISTÓRICO
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
# 12. GERENCIAR CADETES
# ─────────────────────────────────────────────
elif menu == "Gerenciar Cadetes" and is_admin:
    st.title("👤 Gerenciamento de Cadetes")
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Cadete", "❌ Remover Cadete", "🔑 Resetar Senha"])
    
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
                st.warning("⚠️ Atenção: Remover um cadete apagará TODOS os registros de folga atrelados a ele permanentemente.")
                cadete_rem = st.selectbox("Cadete a remover:", df_rem["selecao"].tolist())
                id_rem = df_rem[df_rem["selecao"]==cadete_rem]["id"].values[0]
                if st.form_submit_button("Remover Definitivamente", type="primary"):
                    deletar_cadete(id_rem)
                    st.success(f"{cadete_rem.split('(')[0].strip()} removido e suas folgas foram apagadas.")
                    
    with tab3:
        df_senha = buscar_cadetes()
        if df_senha.empty:
            st.info("Não há cadetes cadastrados.")
        else:
            df_senha = df_senha.copy()
            df_senha["selecao"] = df_senha["nome"] + " (" + df_senha["turma"] + " - " + df_senha["pelotao"] + ")"
            with st.form("form_reset_senha"):
                st.warning("Ao criar ou resetar a senha, o cadete perderá a senha anterior e precisará usar a nova.")
                cadete_reset = st.selectbox("Cadete:", df_senha.sort_values("nome")["selecao"].tolist())
                nova_senha_admin = st.text_input("Definir nova senha para este cadete:", type="password")
                
                if st.form_submit_button("Atualizar Senha"):
                    if nova_senha_admin:
                        id_reset = df_senha[df_senha["selecao"]==cadete_reset]["id"].values[0]
                        atualizar_senha_cadete(id_reset, nova_senha_admin)
                        st.success(f"A senha de {cadete_reset.split('(')[0].strip()} foi atualizada.")
                    else:
                        st.error("A nova senha não pode ser vazia.")
import streamlit as st
from openai import OpenAI
import json
from datetime import datetime
import pandas as pd
import re
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client, Client
import os

# --- SISTEMA DE MEMORIA LOCAL ---
DATA_FILE = "crysis_data.json"

def cargar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"empleados": [], "historial_sesiones": []}

def guardar_datos():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "empleados": st.session_state.empleados,
            "historial_sesiones": st.session_state.historial_sesiones
        }, f, ensure_ascii=False, indent=4)
# ─────────────────────────────────────────
# 1. CONFIGURACIÓN
# ─────────────────────────────────────────
st.set_page_config(
    page_title="CRYSIS | Intelligence Unit",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────
# 2. TEMA OSCURO TÁCTICO-PREMIUM
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── BASE ── */
html, body, [class*="css"], .stApp {
    background-color: #07090F !important;
    color: #C8D0E0 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* Ocultar decoración de Streamlit */
header[data-testid="stHeader"] { background: #07090F !important; border-bottom: 1px solid #1A2035; }
.stDeployButton { display: none; }
#MainMenu { display: none; }
footer { display: none !important; }

/* ── TÍTULO ── */
.crysis-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 3.2rem;
    font-weight: 700;
    letter-spacing: 0.35em;
    color: #E8EDF5;
    text-align: center;
    margin-bottom: 0;
    text-shadow: 0 0 40px rgba(79, 142, 247, 0.25);
}
.crysis-subtitle {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.45em;
    color: #4F8EF7;
    text-align: center;
    margin-top: 4px;
    margin-bottom: 28px;
}
.crysis-divider {
    border: none;
    border-top: 1px solid #1A2035;
    margin: 0 0 32px 0;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: #0C1020;
    border-bottom: 1px solid #1A2035;
    border-radius: 0;
    padding: 0 8px;
}
.stTabs [data-baseweb="tab"] {
    height: 48px;
    padding: 0 24px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    color: #4A5568;
    border-radius: 0;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    transition: all 0.2s;
}
.stTabs [data-baseweb="tab"]:hover { color: #8B9CC8; }
.stTabs [aria-selected="true"] {
    color: #4F8EF7 !important;
    background: transparent !important;
    border-bottom: 2px solid #4F8EF7 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: transparent;
    padding: 24px 0 0 0;
}

/* ── METRIC CARDS ── */
.metric-card {
    background: #0C1020;
    border: 1px solid #1A2035;
    border-radius: 6px;
    padding: 22px 24px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: #4F8EF7;
}
.metric-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.2em;
    color: #4F8EF7;
    margin-bottom: 8px;
}
.metric-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #E8EDF5;
    line-height: 1;
}
.metric-sub {
    font-size: 0.75rem;
    color: #4A5568;
    margin-top: 6px;
}

/* ── BRIEFING BOX ── */
.briefing-box {
    background: #0C1020;
    border: 1px solid #1A2035;
    border-left: 3px solid #4F8EF7;
    padding: 24px 28px;
    border-radius: 4px;
    margin-bottom: 24px;
}
.briefing-box h4 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    color: #4F8EF7;
    margin-bottom: 16px;
}
.briefing-box p { color: #8B9CC8; font-size: 0.88rem; margin-bottom: 8px; }
.briefing-box b { color: #C8D0E0; }

/* ── TABLA ── */
.stDataFrame, .stTable { background: #0C1020 !important; }
thead tr th {
    background: #111827 !important;
    color: #4F8EF7 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.15em !important;
}
tbody tr td { color: #C8D0E0 !important; font-size: 0.85rem !important; }
tbody tr:hover td { background: #111827 !important; }

/* ── FORM / INPUT ── */
.stTextInput input, .stSelectbox > div > div, .stTextArea textarea {
    background: #0C1020 !important;
    border: 1px solid #1A2035 !important;
    color: #C8D0E0 !important;
    border-radius: 4px !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #4F8EF7 !important;
    box-shadow: 0 0 0 2px rgba(79,142,247,0.1) !important;
}
label, .stSelectbox label { color: #4A5568 !important; font-size: 0.78rem !important; letter-spacing: 0.05em !important; }

/* ── BOTONES ── */
.stButton > button {
    background: #4F8EF7 !important;
    color: #07090F !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.7rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.15em !important;
    border: none !important;
    border-radius: 3px !important;
    padding: 12px 28px !important;
    transition: all 0.2s !important;
    width: auto;
}
.stButton > button:hover {
    background: #3A7AE4 !important;
    box-shadow: 0 0 20px rgba(79,142,247,0.3) !important;
    transform: translateY(-1px);
}

/* ── CHAT ── */
.stChatMessage {
    background: #0C1020 !important;
    border: 1px solid #1A2035 !important;
    border-radius: 4px !important;
    margin-bottom: 8px !important;
}
.stChatInputContainer {
    background: #0C1020 !important;
    border: 1px solid #1A2035 !important;
    border-radius: 4px !important;
}
.stChatInputContainer textarea { background: transparent !important; color: #C8D0E0 !important; }

/* ── EXPANDER ── */
.stExpander {
    background: #0C1020 !important;
    border: 1px solid #1A2035 !important;
    border-radius: 4px !important;
}
.stExpander summary { color: #8B9CC8 !important; }

/* ── SPINNER ── */
.stSpinner { color: #4F8EF7 !important; }

/* ── SECTION HEADERS ── */
.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.25em;
    color: #4F8EF7;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #1A2035;
}

/* ── BOTÓN ELIMINAR ── */
[data-testid="stButton"] button[kind="secondary"],
button[title^="Eliminar"] {
    background: transparent !important;
    color: #EF4444 !important;
    border: 1px solid #EF444433 !important;
    padding: 4px 10px !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.05em !important;
}
[data-testid="stButton"] button[kind="secondary"]:hover {
    background: #EF444415 !important;
    border-color: #EF4444 !important;
    box-shadow: none !important;
    transform: none !important;
}
.status-bar {
    background: #0C1020;
    border: 1px solid #1A2035;
    border-left: 3px solid #22D3A5;
    padding: 10px 18px;
    border-radius: 3px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.12em;
    color: #22D3A5;
    margin-bottom: 20px;
}

/* ── AGENT FORM ── */
.agent-form-box {
    background: #0C1020;
    border: 1px solid #1A2035;
    border-radius: 6px;
    padding: 24px;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #07090F; }
::-webkit-scrollbar-thumb { background: #1A2035; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

st.header("Registro de Personal Operativo")

with st.form("nuevo_agente", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        nombre = st.text_input("Nombre Completo del Agente")
        departamento = st.selectbox("Departamento", ["Inteligencia", "Táctico", "Logística", "Ciberseguridad"])
    
    with col2:
        rango = st.text_input("Rango / Designación")
    
    enviar = st.form_submit_button("Añadir a la Unidad")

    if enviar:
        if nombre and rango:
            # Llamamos a la función para guardar en Supabase
            try:
                res = guardar_agente(nombre, departamento, rango)
                st.success(f"✅ Agente {nombre} dado de alta en la base de datos.")
            except Exception as e:
                st.error(f"❌ Error al conectar con CRYSIS_DB: {e}")
        else:
            st.warning("⚠️ Por favor, rellena los campos obligatorios.")

# ─────────────────────────────────────────
# 3. DATOS DE CONTEXTO
# ─────────────────────────────────────────
INSTRUCCION_ORTOGRAFIA = " Escribe siempre en español correcto, sin faltas de ortografía ni errores gramaticales. Nunca uses acotaciones entre paréntesis para describir acciones o estados de ánimo (como '(Con tono severo)' o '(Mirando fijamente)'). Solo diálogo puro."

CONTEXTOS_MISION = {
    "OPERACION: FRONTERA": {
        "contexto": "Tensiones militares en el paralelo 38. La República de Krasnovia ha desplegado artillería pesada.",
        "perfil_sujeto": "Ministro Volkov. Burócrata de la vieja escuela, nacionalista y altamente sensible a las amenazas de sanción.",
        "objetivo": "Evitar la escalada bélica sin comprometer la soberanía de los aliados.",
        "prompt": "Eres el Ministro de Defensa de Krasnovia. Hostil y burocrático. Solo diálogo directo." + INSTRUCCION_ORTOGRAFIA
    },
    "OPERACION: BLACKOUT": {
        "contexto": "Ataque masivo al sistema eléctrico nacional. El 40% del país está a oscuras.",
        "perfil_sujeto": "'Shadow'. Hacker mercenario. No tiene ideología, solo interés económico.",
        "objetivo": "Ganar tiempo para que los técnicos localicen el origen del exploit y reducir el rescate.",
        "prompt": "Eres Shadow, hacker de elite. Solo texto directo. Sin emociones." + INSTRUCCION_ORTOGRAFIA
    },
    "OPERACION: EXTRACCION": {
        "contexto": "Robo a banco fallido. 3 civiles retenidos en la bóveda principal.",
        "perfil_sujeto": "Sujeto inestable, bajo presión extrema, posible historial de pánico.",
        "objetivo": "Estabilizar emocionalmente al sujeto y asegurar la liberación de al menos un rehén.",
        "prompt": "Eres un secuestrador acorralado. Gritas, estás nervioso. Solo diálogo crudo." + INSTRUCCION_ORTOGRAFIA
    }
}

PLOTLY_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='DM Sans', color='#8B9CC8', size=12),
    margin=dict(l=16, r=16, t=40, b=16),
)
AXIS_STYLE = dict(gridcolor='#1A2035', zeroline=False, color='#4A5568', linecolor='#1A2035')

# ─────────────────────────────────────────
# 4. PERSISTENCIA Y REINICIO
# ─────────────────────────────────────────
datos_guardados = cargar_datos()

if "empleados" not in st.session_state: 
    st.session_state.empleados = datos_guardados["empleados"]
if "historial_sesiones" not in st.session_state: 
    st.session_state.historial_sesiones = datos_guardados["historial_sesiones"]
if "mensajes" not in st.session_state: st.session_state.mensajes = []
if "evaluacion_actual" not in st.session_state: st.session_state.evaluacion_actual = None
if "mision_iniciada" not in st.session_state: st.session_state.mision_iniciada = False

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_API_KEY = None

# ─────────────────────────────────────────
# 5. HEADER
# ─────────────────────────────────────────
st.markdown("<div class='crysis-title'>CRYSIS</div>", unsafe_allow_html=True)
st.markdown("<div class='crysis-subtitle'>ADVANCED NEGOTIATION PROTOCOL · INTELLIGENCE UNIT</div>", unsafe_allow_html=True)
st.markdown("<hr class='crysis-divider'>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 6. TABS
# ─────────────────────────────────────────
t1, t2, t3, t4, t5 = st.tabs(["ESTADÍSTICAS", "PERSONAL", "EXPEDIENTES", "SIMULADOR", "LABORATORIO VIP"])

# (Aquí añadimos la restricción temporal para probarlo, simulando que eres Enterprise)
plan_actual = "COMANDO"

# ══════════════════════════════════════════
# TAB 1: ESTADÍSTICAS CON GRÁFICOS REALES
# ══════════════════════════════════════════
with t1:
    hist = st.session_state.historial_sesiones
    empleados = st.session_state.empleados

    # ── KPI CARDS ──
    total_agentes = len(empleados)
    total_ops = len(hist)
    media_global = int(sum(s["Nota"] for s in hist) / len(hist)) if hist else 0
    mejor_nota = max((s["Nota"] for s in hist), default=0)

    # Métricas avanzadas
    ops_exitosas = sum(1 for s in hist if s["Nota"] >= 70)
    tasa_exito = int((ops_exitosas / total_ops) * 100) if total_ops else 0

    # Agentes aptos para conflicto real (media personal >= 70)
    agentes_aptos = 0
    if empleados and hist:
        df_temp = pd.DataFrame(hist)
        for emp in empleados:
            sesiones_emp = df_temp[df_temp["Agente"] == emp["Nombre"]]
            if len(sesiones_emp) > 0 and sesiones_emp["Nota"].mean() >= 70:
                agentes_aptos += 1

    # Escenario más difícil
    escenario_dificil = "N/A"
    if hist:
        df_temp = pd.DataFrame(hist)
        avg_esc = df_temp.groupby("Escenario")["Nota"].mean()
        esc_raw = avg_esc.idxmin()
        escenario_dificil = esc_raw.replace("OPERACION: ", "")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        aptos_color = "#22D3A5" if agentes_aptos > 0 else "#EF4444"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">APTOS PARA CONFLICTO REAL</div>
            <div class="metric-value" style="color:{aptos_color}">{agentes_aptos:02d}<span style="font-size:1rem"> / {total_agentes:02d}</span></div>
            <div class="metric-sub">Agentes con media ≥ 70%</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        exito_color = "#22D3A5" if tasa_exito >= 60 else ("#F59E0B" if tasa_exito >= 30 else "#EF4444")
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">TASA DE ÉXITO</div>
            <div class="metric-value" style="color:{exito_color}">{tasa_exito}<span style="font-size:1rem">%</span></div>
            <div class="metric-sub">{ops_exitosas} de {total_ops} operaciones superadas</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        color = "#22D3A5" if media_global >= 70 else ("#F59E0B" if media_global >= 40 else "#EF4444")
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">RENDIMIENTO MEDIO</div>
            <div class="metric-value" style="color:{color}">{media_global}<span style="font-size:1rem">%</span></div>
            <div class="metric-sub">Puntuación global del equipo</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">ESCENARIO MÁS DIFÍCIL</div>
            <div class="metric-value" style="font-size:1.2rem; color:#F59E0B;">{escenario_dificil}</div>
            <div class="metric-sub">Menor media de puntuación</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not hist:
        st.markdown("""
        <div style="text-align:center; padding: 60px; color: #2A3550; font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; letter-spacing: 0.2em;">
            SIN DATOS OPERACIONALES — INICIAR SIMULADOR PARA REGISTRAR SESIONES
        </div>""", unsafe_allow_html=True)
    else:
        df = pd.DataFrame(hist)

        col_left, col_right = st.columns(2, gap="medium")

        # ── GRÁFICO 1: Rendimiento por agente (barras horizontales) ──
        with col_left:
            st.markdown("<div class='section-label'>RENDIMIENTO POR AGENTE</div>", unsafe_allow_html=True)
            avg_by_agent = df.groupby("Agente")["Nota"].mean().reset_index()
            avg_by_agent.columns = ["Agente", "Media"]
            avg_by_agent["Media"] = avg_by_agent["Media"].round(1)

            fig1 = go.Figure(go.Bar(
                x=avg_by_agent["Media"],
                y=avg_by_agent["Agente"],
                orientation='h',
                marker=dict(
                    color=avg_by_agent["Media"],
                    colorscale=[[0, '#EF4444'], [0.5, '#F59E0B'], [1, '#22D3A5']],
                    cmin=0, cmax=100,
                    line=dict(width=0)
                ),
                text=[f"{v}%" for v in avg_by_agent["Media"]],
                textposition='outside',
                textfont=dict(color='#8B9CC8', size=11)
            ))
            fig1.update_layout(**PLOTLY_THEME, height=max(180, len(avg_by_agent) * 52), showlegend=False)
            fig1.update_xaxes(**AXIS_STYLE, range=[0, 110])
            fig1.update_yaxes(**AXIS_STYLE)
            st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

        # ── GRÁFICO 2: Donut por escenario ──
        with col_right:
            st.markdown("<div class='section-label'>DISTRIBUCIÓN POR ESCENARIO</div>", unsafe_allow_html=True)
            esc_count = df["Escenario"].value_counts().reset_index()
            esc_count.columns = ["Escenario", "Count"]
            # Acortar nombres
            esc_count["Escenario"] = esc_count["Escenario"].str.replace("OPERACION: ", "", regex=False)

            fig2 = go.Figure(go.Pie(
                labels=esc_count["Escenario"],
                values=esc_count["Count"],
                hole=0.65,
                marker=dict(colors=['#4F8EF7', '#22D3A5', '#F59E0B'], line=dict(width=0)),
                textinfo='label+percent',
                textfont=dict(size=11, color='#C8D0E0'),
                insidetextorientation='radial',
            ))
            fig2.add_annotation(
                text=f"<b>{total_ops}</b><br><span style='font-size:10px'>OPS</span>",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=18, color='#E8EDF5', family='IBM Plex Mono')
            )
            fig2.update_layout(**PLOTLY_THEME, height=280, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        # ── GRÁFICO 3: Evolución temporal ──
        st.markdown("<div class='section-label'>EVOLUCIÓN TEMPORAL DE RENDIMIENTO</div>", unsafe_allow_html=True)
        df["Fecha_dt"] = pd.to_datetime(df["Fecha"])
        df_sorted = df.sort_values("Fecha_dt")

        fig3 = go.Figure()
        colors_agents = ['#4F8EF7', '#22D3A5', '#F59E0B', '#EF4444', '#A78BFA']
        for idx, agente in enumerate(df_sorted["Agente"].unique()):
            df_ag = df_sorted[df_sorted["Agente"] == agente]
            color = colors_agents[idx % len(colors_agents)]
            modo = 'lines+markers' if len(df_ag) > 1 else 'markers'
            fig3.add_trace(go.Scatter(
                x=df_ag["Fecha_dt"],
                y=df_ag["Nota"],
                mode=modo,
                name=agente,
                line=dict(width=2, color=color),
                marker=dict(size=10, color=color, line=dict(width=2, color='#07090F')),
                text=[f"{v}%" for v in df_ag["Nota"]],
                textposition="top center",
                textfont=dict(color=color, size=11),
                hovertemplate=f"<b>{agente}</b><br>Nota: %{{y}}%<br>Fecha: %{{x|%d %b %Y %H:%M}}<extra></extra>"
            ))
        fig3.add_hline(y=70, line_dash="dot", line_color="#22D3A5", opacity=0.4,
                       annotation_text="UMBRAL OPERATIVO (70)", annotation_font_color="#22D3A5",
                       annotation_font_size=10)
        fig3.update_layout(
            **PLOTLY_THEME,
            height=260,
            legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color='#8B9CC8', size=11)),
        )
        fig3.update_xaxes(**AXIS_STYLE, tickformat="%d %b\n%Y")
        fig3.update_yaxes(**AXIS_STYLE, range=[0, 110])
        if len(df) == 1:
            st.caption("⚠ Se necesitan al menos 2 operaciones para trazar la línea de evolución. Mostrando puntos individuales.")
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

        # ── GRÁFICO 4: Histograma de distribución de notas ──
        st.markdown("<div class='section-label'>DISTRIBUCIÓN DE PUNTUACIONES</div>", unsafe_allow_html=True)
        fig4 = go.Figure(go.Histogram(
            x=df["Nota"],
            nbinsx=10,
            marker=dict(color='#4F8EF7', line=dict(color='#07090F', width=1)),
        ))
        fig4.update_layout(**PLOTLY_THEME, height=200, bargap=0.08)
        fig4.update_xaxes(**AXIS_STYLE, title="Puntuación", range=[0, 100])
        fig4.update_yaxes(**AXIS_STYLE, title="Frecuencia")
        st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════
# TAB 2: PERSONAL (antes FUERZA LABORAL)
# ══════════════════════════════════════════
with t2:
    col_l, col_r = st.columns([2, 1], gap="large")

    with col_l:
        st.markdown("<div class='section-label'>UNIDAD OPERATIVA</div>", unsafe_allow_html=True)
        if st.session_state.empleados:
            st.markdown("""
            <div style="display:grid; grid-template-columns:3fr 3fr 2fr 1fr;
                        padding:8px 12px; border-bottom:1px solid #1A2035; margin-bottom:4px;">
                <span style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;letter-spacing:0.15em;color:#4F8EF7;">NOMBRE</span>
                <span style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;letter-spacing:0.15em;color:#4F8EF7;">DEPARTAMENTO</span>
                <span style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;letter-spacing:0.15em;color:#4F8EF7;">RANGO</span>
                <span></span>
            </div>""", unsafe_allow_html=True)
            for i, emp in enumerate(st.session_state.empleados):
                c_name, c_dept, c_rank, c_btn = st.columns([3, 3, 2, 1])
                c_name.markdown(f"<div style='padding:8px 12px; color:#C8D0E0; font-size:0.88rem;'>{emp['Nombre']}</div>", unsafe_allow_html=True)
                c_dept.markdown(f"<div style='padding:8px 12px; color:#8B9CC8; font-size:0.85rem;'>{emp['Departamento']}</div>", unsafe_allow_html=True)
                c_rank.markdown(f"<div style='padding:8px 12px; color:#4A5568; font-size:0.78rem; font-family:IBM Plex Mono,monospace;'>{emp['Rango']}</div>", unsafe_allow_html=True)
                if c_btn.button("✕", key=f"del_{i}", help=f"Eliminar a {emp['Nombre']}"):
                    st.session_state.empleados.pop(i)
                    guardar_datos()
                    st.rerun()
        else:
            st.markdown("""
            <div style="padding: 40px; text-align: center; color: #2A3550;
                        font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; letter-spacing: 0.2em;">
                SIN PERSONAL REGISTRADO
            </div>""", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='section-label'>REGISTRAR AGENTE</div>", unsafe_allow_html=True)
        st.markdown("<div class='agent-form-box'>", unsafe_allow_html=True)
        with st.form("reg"):
            n = st.text_input("Nombre completo")
            d = st.text_input("Departamento")
            r_emp = st.text_input("Rango / Cargo")
            submitted = st.form_submit_button("REGISTRAR →", use_container_width=True)
            if submitted and n:
                st.session_state.empleados.append({"Nombre": n, "Departamento": d, "Rango": r_emp})
                guardar_datos()
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════
# TAB 3: EXPEDIENTES
# ══════════════════════════════════════════
with t3:
    st.markdown("<div class='section-label'>ARCHIVO DE OPERACIONES</div>", unsafe_allow_html=True)
    if st.session_state.historial_sesiones:
        for e in st.session_state.empleados:
            sesiones_idx = [(i, s) for i, s in enumerate(st.session_state.historial_sesiones) if s["Agente"] == e["Nombre"]]
            if sesiones_idx:
                avg = int(sum(s["Nota"] for _, s in sesiones_idx) / len(sesiones_idx))
                with st.expander(f"⬡  {e['Nombre'].upper()}  ·  {len(sesiones_idx)} OPS  ·  MEDIA: {avg}%"):
                    for i, s in sesiones_idx:
                        nota_color = "#22D3A5" if s["Nota"] >= 70 else ("#F59E0B" if s["Nota"] >= 40 else "#EF4444")
                        col_info, col_score, col_del = st.columns([6, 2, 1])
                        with col_info:
                            st.markdown(f"""
                            <div style="padding: 10px 0 4px 0;">
                                <span style="font-family:'IBM Plex Mono',monospace; font-size:0.65rem;
                                             color:#4A5568; letter-spacing:0.1em;">{s['Fecha']}</span><br>
                                <span style="color:#C8D0E0; font-size:0.9rem;">{s['Escenario']}</span>
                            </div>""", unsafe_allow_html=True)
                        with col_score:
                            st.markdown(f"""
                            <div style="padding:10px 0; text-align:right;">
                                <span style="font-family:'IBM Plex Mono',monospace; font-size:1.3rem;
                                             font-weight:700; color:{nota_color};">{s['Nota']}%</span>
                            </div>""", unsafe_allow_html=True)
                        with col_del:
                            if st.button("✕", key=f"del_ses_{i}", help="Eliminar este expediente"):
                                st.session_state.historial_sesiones.pop(i)
                                st.rerun()
                        with st.expander(f"Ver informe — {s['Escenario']}", expanded=False):
                            st.markdown(s["Evaluacion"])
                        st.markdown("<hr style='border-color:#1A2035; margin:8px 0;'>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="padding:60px; text-align:center; color:#2A3550;
                    font-family:'IBM Plex Mono',monospace; font-size:0.7rem; letter-spacing:0.2em;">
            SIN EXPEDIENTES — COMPLETAR AL MENOS UNA OPERACIÓN
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════
# TAB 4: SIMULADOR
# ══════════════════════════════════════════
with t4:
    if not st.session_state.mision_iniciada:
        # ── FASE 0: CONFIGURACIÓN ──
        st.markdown("<div class='section-label'>CONFIGURACIÓN DE OPERACIÓN</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        ag_lista = [e["Nombre"] for e in st.session_state.empleados] if st.session_state.empleados else ["INVITADO"]
        ag_sel = c1.selectbox("Asignar Agente:", ag_lista)
        es_sel = c2.selectbox("Seleccionar Escenario:", list(CONTEXTOS_MISION.keys()))

        info = CONTEXTOS_MISION[es_sel]
        st.markdown(f"""
        <div class="briefing-box">
            <h4>📄 BRIEFING OPERATIVO</h4>
            <p><b>Contexto:</b> {info['contexto']}</p>
            <p><b>Perfil del Sujeto:</b> {info['perfil_sujeto']}</p>
            <p><b>Objetivo Primario:</b> {info['objetivo']}</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("INICIAR PROTOCOLO DE CONTACTO →", use_container_width=True):
            st.session_state.mision_iniciada = True
            st.session_state.mensajes = []
            st.session_state.agente_activo = ag_sel
            st.session_state.escenario_activo = es_sel
            st.rerun()

    elif st.session_state.evaluacion_actual:
        # ── FASE 2: DEBRIEFING ──
        st.markdown("<div class='section-label'>DEBRIEFING — INFORME DE RENDIMIENTO</div>", unsafe_allow_html=True)
        st.markdown(st.session_state.evaluacion_actual)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("CERRAR OPERACIÓN Y VOLVER A BASE →", use_container_width=True):
            st.session_state.mision_iniciada = False
            st.session_state.evaluacion_actual = None
            st.session_state.mensajes = []
            st.rerun()

    else:
        # ── FASE 1: INTERVENCIÓN ──
        st.markdown(f"""
        <div class="status-bar">
            ◉ OPERACIÓN ACTIVA: {st.session_state.escenario_activo}  ·  AGENTE: {st.session_state.agente_activo.upper()}
        </div>""", unsafe_allow_html=True)

        for m in st.session_state.mensajes:
            label = "AGENTE" if m["role"] == "user" else "OBJETIVO"
            bg = "#0F1829" if m["role"] == "user" else "#0C1020"
            border = "#4F8EF7" if m["role"] == "user" else "#EF4444"
            align = "flex-end" if m["role"] == "user" else "flex-start"
            st.markdown(f"""
            <div style="display:flex; justify-content:{align}; margin-bottom:12px;">
                <div style="max-width:78%; background:{bg}; border:1px solid {border}22;
                            border-left: 3px solid {border}; border-radius:4px; padding:14px 18px;">
                    <div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem;
                                letter-spacing:0.18em; color:{border}; margin-bottom:8px;">{label}</div>
                    <div style="color:#C8D0E0; font-size:0.9rem; line-height:1.6;">{m['content']}</div>
                </div>
            </div>""", unsafe_allow_html=True)

        if prompt := st.chat_input("Introduzca directiva de negociación..."):
            st.session_state.mensajes.append({"role": "user", "content": prompt})
            st.rerun()

        if st.session_state.mensajes and st.session_state.mensajes[-1]["role"] == "user":
            if GROQ_API_KEY:
                client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": CONTEXTOS_MISION[st.session_state.escenario_activo]["prompt"]}] + st.session_state.mensajes
                ).choices[0].message.content
                st.session_state.mensajes.append({"role": "assistant", "content": res})
                st.rerun()

        if len(st.session_state.mensajes) > 0:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🛑 FINALIZAR Y GENERAR INFORME OPERACIONAL →", use_container_width=True):
                with st.spinner("Procesando análisis psicolingüístico y táctico..."):
                    client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                    escenario = st.session_state.escenario_activo
                    info = CONTEXTOS_MISION[escenario]
                    hist_txt = "\n".join([
                        f"{'NEGOCIADOR (agente a evaluar)' if m['role'] == 'user' else 'OBJETIVO (personaje IA, NO evaluar)'}: {m['content']}"
                        for m in st.session_state.mensajes
                    ])

                    eval_prompt = f"""Eres un evaluador de élite en técnicas de negociación de crisis. Tu análisis debe ser ESTRICTO, directo y sin condescendencia.

CONTEXTO DE LA OPERACIÓN:
- Escenario: {escenario}
- Situación: {info['contexto']}
- Perfil del objetivo: {info['perfil_sujeto']}
- Objetivo de la misión: {info['objetivo']}

IMPORTANTE: Evalúa ÚNICAMENTE al NEGOCIADOR (agente a evaluar). Ignora completamente las respuestas del OBJETIVO (personaje IA).

TRANSCRIPCIÓN:
{hist_txt}

Genera un informe con exactamente esta estructura. Sé implacable: si algo está mal, dilo sin suavizarlo.

**ANÁLISIS DE LENGUAJE**
Evalúa el tono, nivel de agresividad, uso de empatía real vs. empatía fingida, y seguridad en cada intervención del negociador. Señala frases concretas que fueron un error o un acierto.

**TÁCTICAS EMPLEADAS**
¿Usó espejeo, etiquetas emocionales, pausas estratégicas, anclaje, preguntas calibradas? ¿Las usó correctamente o de forma torpe? Sé específico.

**ERRORES CRÍTICOS**
Lista los errores que pusieron en riesgo la misión. Si no negoció bien, dilo. No suavices nada. Mínimo 2 errores concretos aunque la negociación haya ido bien.

**VEREDICTO DEL EVALUADOR**
Una valoración directa y dura: ¿está este agente preparado para una operación real? ¿Qué debe trabajar de forma urgente?

**PUNTUACIÓN FINAL: XX/100**
(Sé exigente. Una negociación mediocre no supera el 50. Solo una ejecución técnica impecable supera el 80.)"""

                    informe = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": eval_prompt}]
                    ).choices[0].message.content

                    try:
                        # Busca patrón "XX/100" o "PUNTUACIÓN FINAL: XX"
                        match = re.search(r'PUNTUACI[OÓ]N FINAL[^\d]*(\d+)\s*\/?\s*100', informe, re.IGNORECASE)
                        if match:
                            nota = min(int(match.group(1)), 100)
                        else:
                            # fallback: primer número seguido de /100
                            match2 = re.search(r'(\d+)\s*/\s*100', informe)
                            nota = min(int(match2.group(1)), 100) if match2 else 50
                    except:
                        nota = 50

                    st.session_state.evaluacion_actual = informe
                    st.session_state.historial_sesiones.append({
                        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Agente": st.session_state.agente_activo,
                        "Escenario": st.session_state.escenario_activo,
                        "Nota": nota,
                        "Evaluacion": informe
                    })
                    guardar_datos()
                    st.rerun()

# ══════════════════════════════════════════
# TAB 5: LABORATORIO VIP (AJUSTES DEL SISTEMA)
# ══════════════════════════════════════════
with t5:
    st.markdown("<div class='section-label'>SISTEMA Y CONTROL DE MEMORIA</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="briefing-box" style="border-left-color: #EF4444;">
        <h4 style="color: #EF4444;">⚠ ADVERTENCIA DE PROTOCOLO</h4>
        <p>Esta acción ejecutará un purgado completo de la memoria local. Todos los agentes registrados y el historial de simulaciones serán eliminados de forma irreversible.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("☣️ PURGAR TODOS LOS DATOS DEL SISTEMA", use_container_width=True):
            st.session_state.empleados = []
            st.session_state.historial_sesiones = []
            guardar_datos()
            st.rerun()

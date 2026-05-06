import streamlit as st
from openai import OpenAI
import json
from datetime import datetime, timedelta
import pandas as pd
import re
import plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
import random
from fpdf import FPDF
from supabase import create_client, Client
import base64

# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────
COMANDANTE_SUPREMO = "CRYSIS"
LINKS_PAGO = {
    "Enterprise": "https://crysisanalitics.lemonsqueezy.com/checkout/buy/d864d72e-5ff1-4bac-966d-eafc555c5bd2",
    "Pro":        "https://crysisanalitics.lemonsqueezy.com/checkout/buy/1dba647d-e120-4816-9ea0-a25492650825",
    "Individual": "https://crysisanalitics.lemonsqueezy.com/checkout/buy/adfd50b4-b2e5-40fb-9ece-30717f8828ba"
}

NIVELES_DIFICULTAD = {
    "RECRUIT": {
        "label": "RECRUIT",
        "desc": "Sujeto cooperativo. Ideal para entrenamiento inicial.",
        "color": "#00E5A0",
        "modificador": (
            " El sujeto está dispuesto a negociar y responde de forma predecible."
            " Usa un tono moderadamente hostil pero cede ante argumentos razonables."
            " El operador tiene margen de error."
        )
    },
    "OPERATIVE": {
        "label": "OPERATIVE",
        "desc": "Sujeto calculador. Requiere técnica real.",
        "color": "#FFB020",
        "modificador": (
            " El sujeto es inteligente y difícil. No cede fácilmente, detecta manipulaciones"
            " obvias y contraataca verbalmente. Exige argumentos precisos y uso correcto de"
            " técnicas de negociación."
        )
    },
    "ELITE": {
        "label": "ELITE",
        "desc": "Sujeto extremo. Sin margen de error.",
        "color": "#FF3A4A",
        "modificador": (
            " El sujeto es extremadamente hostil, paranoico y errático. Detecta cualquier"
            " debilidad táctica, interrumpe, amenaza y cambia de postura sin previo aviso."
            " Solo la negociación de élite logrará resultados."
        )
    }
}

INSTRUCCION_ORTOGRAFIA = (
    " Escribe en español correcto. Nunca uses acotaciones entre paréntesis. Solo diálogo."
)

CONTEXTOS_MISION = {
    "OPERACION: FRONTERA": {
        "contexto": "Tensiones militares en el paralelo 38.",
        "perfil_sujeto": "Ministro Volkov.",
        "objetivo": "Evitar la escalada bélica y conseguir que el ministro acepte abrir un canal diplomático.",
        "prompt": "Eres el Ministro de Defensa de Krasnovia. Hostil y burocrático. Solo diálogo directo." + INSTRUCCION_ORTOGRAFIA
    },
    "OPERACION: BLACKOUT": {
        "contexto": "Ataque masivo al sistema eléctrico nacional. Rescate exigido.",
        "perfil_sujeto": "'Shadow'. Hacker mercenario. Frío y calculador.",
        "objetivo": "Ganar tiempo para localizar el origen del ataque y conseguir que Shadow revele pistas sobre su ubicación.",
        "prompt": "Eres Shadow, hacker de elite acorralado. Solo texto directo. Sin emociones." + INSTRUCCION_ORTOGRAFIA
    },
    "OPERACION: EXTRACCION": {
        "contexto": "Robo a banco fallido. 3 civiles retenidos.",
        "perfil_sujeto": "Sujeto inestable, bajo presión extrema.",
        "objetivo": "Conseguir la liberación de al menos un rehén y establecer un canal de comunicación estable con el sujeto.",
        "prompt": "Eres un secuestrador acorralado. Gritas, estás nervioso. Solo diálogo crudo." + INSTRUCCION_ORTOGRAFIA
    }
}

PLOTLY_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='JetBrains Mono', color='#8B9CC8', size=11),
    margin=dict(l=16, r=16, t=40, b=16)
)


# ─────────────────────────────────────────
# SUPABASE
# ─────────────────────────────────────────
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"].strip().rstrip("/")
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_supabase()

def cargar_datos():
    try:
        response = supabase.table("crysis_data").select("memoria").eq("id", "main").execute()
        if response.data:
            datos = response.data[0]["memoria"]
            if "escenarios_custom" not in datos:
                datos["escenarios_custom"] = {}
            datos["empleados"] = [e for e in datos.get("empleados", []) if "Rol" in e]
            return datos
    except Exception as e:
        st.error(f"Error al conectar con Base de Datos Central: {e}")
    return {"empleados": [], "historial_sesiones": [], "escenarios_custom": {}}

def guardar_datos():
    try:
        datos_actualizados = {
            "empleados": st.session_state.empleados,
            "historial_sesiones": st.session_state.historial_sesiones,
            "escenarios_custom": st.session_state.escenarios_custom
        }
        supabase.table("crysis_data").update(
            {"memoria": datos_actualizados}
        ).eq("id", "main").execute()
    except Exception as e:
        st.error(f"Fallo crítico al sincronizar: {e}")


# ─────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────
def enviar_correo_2fa(destinatario, codigo):
    try:
        remitente = st.secrets["SMTP_EMAIL"]
        password  = st.secrets["SMTP_PASS"]
        msg = MIMEText(
            f"Tu código de autorización táctica para CRYSIS es: {codigo}\n\n"
            "Si no has solicitado este acceso, reporta una brecha de seguridad inmediatamente."
        )
        msg['Subject'] = 'CRYSIS | Código de Acceso 2FA'
        msg['From']    = "CRYSIS Security <no-reply@comando-crysis.net>"
        msg['To']      = destinatario
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False

def sanitizar_texto(texto):
    if not isinstance(texto, str):
        texto = str(texto)
    texto = (texto
             .replace('**', '').replace('*', '-')
             .replace('•', '-').replace('✅', '[V]').replace('❌', '[X]'))
    return texto.encode('latin-1', 'replace').decode('latin-1')

def generar_pdf_dossier(sesion):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.set_text_color(79, 142, 247)
    pdf.cell(0, 10, "CRYSIS | INTELLIGENCE UNIT", ln=True, align='C')
    pdf.set_font("Arial", 'B', 11); pdf.set_text_color(239, 68, 68)
    pdf.cell(0, 8, "DOSSIER OPERACIONAL CLASIFICADO", ln=True, align='C'); pdf.ln(5)
    campos = [
        ("OPERADOR",   sesion.get("Agente", "N/A").upper()),
        ("FECHA",      sesion.get("Fecha", "N/A")),
        ("PROTOCOLO",  sesion.get("Escenario", "N/A")),
        ("DIFICULTAD", sesion.get("Dificultad", "N/A")),
        ("RESULTADO",  "OBJETIVO CUMPLIDO" if sesion.get("ObjetivoCumplido") else "FINALIZADO MANUALMENTE"),
        ("EVALUACION", f"{sesion.get('Nota', 0)}/100"),
    ]
    for label, valor in campos:
        pdf.set_font("Arial", 'B', 10); pdf.set_text_color(0, 0, 0)
        pdf.cell(45, 8, f"{label}:", border=1)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 8, sanitizar_texto(valor), border=1, ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12); pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "1. INFORME DE EVALUACION TACTICA", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, sanitizar_texto(sesion.get("Evaluacion", ""))); pdf.ln(5)
    if "Transcripcion" in sesion:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "2. REGISTRO DE COMUNICACIONES", ln=True); pdf.ln(2)
        for msg in sesion["Transcripcion"]:
            ag = "OPERADOR" if msg["role"] == "user" else "OBJETIVO"
            pdf.set_text_color(79, 142, 247) if msg["role"] == "user" else pdf.set_text_color(239, 68, 68)
            pdf.set_font("Arial", 'B', 10); pdf.cell(0, 6, f"{ag}:", ln=True)
            pdf.set_text_color(50, 50, 50); pdf.set_font("Arial", '', 10)
            pdf.multi_cell(0, 6, sanitizar_texto(msg["content"])); pdf.ln(2)
    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else out


# ─────────────────────────────────────────
# DETECCIÓN AUTOMÁTICA DE OBJETIVO
# ─────────────────────────────────────────
def verificar_objetivo_cumplido(client, escenario_info, mensajes):
    """
    Llama a la IA como árbitro para decidir si el objetivo de la misión
    se ha cumplido según la transcripción actual.
    Devuelve True/False.
    """
    if len(mensajes) < 4:   # mínimo 2 intercambios antes de verificar
        return False
    hist_txt = "\n".join([
        f"{'OPERADOR' if m['role'] == 'user' else 'SUJETO'}: {m['content']}"
        for m in mensajes
    ])
    arbitro_prompt = (
        f"Eres un árbitro de simulación táctica. "
        f"El objetivo de esta misión es: {escenario_info['objetivo']}\n\n"
        f"TRANSCRIPCION ACTUAL:\n{hist_txt}\n\n"
        "Analiza únicamente si el OPERADOR ha logrado el objetivo descrito. "
        "Responde EXCLUSIVAMENTE con una sola palabra: SI o NO."
    )
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": arbitro_prompt}],
            max_tokens=5,
            temperature=0.0
        )
        respuesta = res.choices[0].message.content.strip().upper()
        return respuesta.startswith("SI") or respuesta == "SÍ"
    except:
        return False


# ─────────────────────────────────────────
# CSS GLOBAL
# ─────────────────────────────────────────
st.set_page_config(
    page_title="CRYSIS | Intelligence Unit",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Rajdhani:wght@400;500;600;700&display=swap');

:root {
  --bg:       #05070F;
  --bg2:      #080C18;
  --bg3:      #0C1020;
  --bg4:      #101528;
  --border:   #141C2E;
  --border2:  #1C2640;
  --border3:  #263250;
  --blue:     #4A8FFF;
  --blue-dim: rgba(74,143,255,0.10);
  --blue-glow:rgba(74,143,255,0.22);
  --green:    #00E5A0;
  --red:      #FF3A4A;
  --amber:    #FFB020;
  --text:     #8A9CBC;
  --text-hi:  #D8E8FF;
  --text-lo:  #2A3A55;
  --mono:     'JetBrains Mono', monospace;
  --sans:     'Rajdhani', sans-serif;
  --r:        3px;
}

html, body, [class*="css"], .stApp {
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: var(--sans) !important;
}
header[data-testid="stHeader"],
.stDeployButton, #MainMenu, footer,
section[data-testid="stSidebar"] { display: none !important; }

/* scanlines */
.stApp::before {
  content:''; position:fixed; inset:0; pointer-events:none; z-index:9999;
  background: repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,0.04) 3px,rgba(0,0,0,0.04) 4px);
}

/* ── INPUTS ── */
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
  background: var(--bg3) !important; border: 1px solid var(--border2) !important;
  color: var(--text-hi) !important; border-radius: var(--r) !important;
  font-family: var(--mono) !important; font-size: 0.82rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--blue) !important;
  box-shadow: 0 0 0 2px var(--blue-dim), 0 0 16px var(--blue-glow) !important;
}
.stTextInput label, .stTextArea label, .stSelectbox label,
.stRadio label span, [data-testid="stWidgetLabel"] {
  font-family: var(--mono) !important; font-size: 0.58rem !important;
  letter-spacing: 0.22em !important; color: var(--blue) !important;
  text-transform: uppercase !important;
}

/* ── BUTTONS ── */
.stButton > button {
  background: transparent !important; color: var(--blue) !important;
  font-family: var(--mono) !important; font-size: 0.62rem !important;
  font-weight: 600 !important; letter-spacing: 0.18em !important;
  border: 1px solid var(--border3) !important; border-radius: var(--r) !important;
  padding: 10px 22px !important; transition: all 0.18s !important;
  text-transform: uppercase !important;
}
.stButton > button:hover {
  background: var(--blue-dim) !important; border-color: var(--blue) !important;
  box-shadow: 0 0 20px var(--blue-glow) !important; color: var(--text-hi) !important;
}
.stButton > button[kind="primary"] {
  background: var(--blue) !important; color: var(--bg) !important;
  border-color: var(--blue) !important; font-weight: 700 !important;
}
.stButton > button[kind="primary"]:hover {
  background: #6AABFF !important; box-shadow: 0 0 30px var(--blue-glow) !important;
}
.stButton > button[kind="secondary"] {
  border-color: var(--border2) !important; color: var(--text-lo) !important;
}
.stButton > button[kind="secondary"]:hover {
  border-color: var(--red) !important; color: var(--red) !important;
  background: rgba(255,58,74,0.08) !important;
}
.stButton > button[disabled] {
  background: transparent !important; color: var(--text-lo) !important;
  border-color: var(--border) !important; box-shadow: none !important;
}

/* ── CHAT ── */
.stChatInputContainer {
  background: var(--bg2) !important; border: 1px solid var(--border2) !important;
  border-radius: var(--r) !important;
}
.stChatInputContainer textarea { font-family: var(--mono) !important; color: var(--text-hi) !important; }

/* ── EXPANDER ── */
.streamlit-expanderHeader {
  background: var(--bg2) !important; border: 1px solid var(--border) !important;
  border-radius: var(--r) !important; font-family: var(--mono) !important;
  font-size: 0.62rem !important; letter-spacing: 0.14em !important;
  color: var(--text) !important;
}
.streamlit-expanderContent {
  background: var(--bg2) !important; border: 1px solid var(--border) !important;
  border-top: none !important;
}

/* ── PROGRESS ── */
.stProgress > div > div > div {
  background: linear-gradient(90deg, var(--blue), var(--green)) !important;
  box-shadow: 0 0 10px var(--blue-glow) !important;
}

/* ── RADIO ── */
.stRadio [data-testid="stMarkdownContainer"] p { font-family: var(--mono) !important; font-size:0.72rem !important; }

/* ── ALERTS ── */
div[data-testid="stAlert"] {
  border-radius: var(--r) !important; font-family: var(--mono) !important; font-size: 0.75rem !important;
}
hr { border-color: var(--border2) !important; }

/* ──────────────────────────
   COMPONENTES PROPIOS
────────────────────────── */
.crysis-topbar {
  display:flex; align-items:center; justify-content:space-between;
  padding:14px 0; border-bottom:1px solid var(--border2); margin-bottom:28px; position:relative;
}
.crysis-topbar::after {
  content:''; position:absolute; bottom:-1px; left:0;
  width:60px; height:1px; background:var(--blue); box-shadow:0 0 8px var(--blue);
}
.topbar-logo { font-family:var(--mono); font-size:1rem; font-weight:700; letter-spacing:0.45em; color:var(--text-hi); }
.topbar-breadcrumb { font-family:var(--mono); font-size:0.58rem; letter-spacing:0.25em; color:var(--text-lo); margin-top:4px; }
.topbar-user { font-family:var(--mono); font-size:0.55rem; letter-spacing:0.2em; color:var(--blue); text-align:right; }

.section-hd { margin-bottom:28px; padding-bottom:16px; border-bottom:1px solid var(--border2); }
.section-code { font-family:var(--mono); font-size:0.5rem; letter-spacing:0.35em; color:var(--text-lo); margin-bottom:6px; }
.section-title { font-family:var(--sans); font-size:1.5rem; font-weight:700; color:var(--text-hi); letter-spacing:0.02em; }
.lbl { font-family:var(--mono); font-size:0.55rem; letter-spacing:0.25em; color:var(--blue);
       margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid var(--border); display:block; }

/* MÓDULOS DEL MENÚ */
.mod {
  background:var(--bg2); border:1px solid var(--border); border-radius:var(--r);
  padding:28px 24px; position:relative; overflow:hidden;
  transition:border-color 0.2s, transform 0.2s, box-shadow 0.2s;
}
.mod:hover { border-color:var(--border3); transform:translateY(-2px); box-shadow:0 8px 40px rgba(0,0,0,0.5); }
.mod-accent { position:absolute; top:0; left:0; width:3px; height:100%; }
.mod-code { font-family:var(--mono); font-size:0.5rem; letter-spacing:0.3em; color:var(--text-lo); margin-bottom:14px; }
.mod-title { font-family:var(--sans); font-size:1rem; font-weight:700; color:var(--text-hi); margin-bottom:6px; }
.mod-desc { font-family:var(--mono); font-size:0.6rem; color:var(--text-lo); line-height:1.7; }
.mod-stat { margin-top:20px; padding-top:14px; border-top:1px solid var(--border);
            font-family:var(--mono); font-size:0.52rem; letter-spacing:0.2em; color:var(--text-lo); }
.mod-stat b { font-size:1.4rem; font-weight:700; display:block; margin-bottom:2px; }

/* MÉTRICA CARD */
.mc { background:var(--bg2); border:1px solid var(--border); border-radius:var(--r);
      padding:22px; position:relative; overflow:hidden; }
.mc::before { content:''; position:absolute; top:0; left:0; width:3px; height:100%; background:var(--blue); }
.mc-lbl { font-family:var(--mono); font-size:0.52rem; letter-spacing:0.22em; color:var(--blue); margin-bottom:10px; }
.mc-val { font-family:var(--mono); font-size:1.8rem; font-weight:700; color:var(--text-hi); line-height:1; }

/* BRIEFING */
.briefing {
  background:var(--bg2); border:1px solid var(--border2); border-left:3px solid var(--blue);
  padding:18px 22px; border-radius:var(--r); margin-bottom:20px;
}
.briefing h4 { font-family:var(--mono); font-size:0.55rem; letter-spacing:0.22em; color:var(--blue); margin-bottom:10px; }
.briefing p  { font-family:var(--sans); font-size:0.9rem; color:var(--text); margin:4px 0; }
.briefing b  { color:var(--text-hi); }

/* STATUS BAR */
.status-bar {
  background:var(--bg2); border:1px solid var(--border); border-left:3px solid var(--green);
  padding:10px 18px; border-radius:var(--r); font-family:var(--mono);
  font-size:0.6rem; letter-spacing:0.12em; color:var(--green); margin-bottom:18px;
}

/* OBJETIVO CUMPLIDO BANNER */
.obj-cumplido {
  background: linear-gradient(90deg, rgba(0,229,160,0.08), rgba(0,229,160,0.02));
  border:1px solid var(--green); border-left:4px solid var(--green);
  padding:18px 24px; border-radius:var(--r); margin-bottom:20px;
  animation: pulse-green 2s ease-in-out infinite;
}
@keyframes pulse-green {
  0%,100% { box-shadow: 0 0 10px rgba(0,229,160,0.1); }
  50%      { box-shadow: 0 0 25px rgba(0,229,160,0.3); }
}
.obj-cumplido-title { font-family:var(--mono); font-size:0.65rem; letter-spacing:0.25em; color:var(--green); margin-bottom:6px; }
.obj-cumplido-desc  { font-family:var(--sans); font-size:0.95rem; color:var(--text); }

/* DIFICULTAD CHIPS */
.diff-chip {
  display:inline-block; font-family:var(--mono); font-size:0.58rem; font-weight:600;
  letter-spacing:0.18em; padding:5px 14px; border-radius:var(--r);
  border:1px solid; margin-right:4px; cursor:pointer; transition:all 0.15s;
}

/* OBJETIVO CARD en simulador */
.obj-card {
  display:flex; gap:0; background:var(--bg2); border:1px solid var(--border2);
  border-left:3px solid var(--amber); border-radius:var(--r);
  padding:14px 20px; margin-bottom:18px; flex-wrap:wrap;
}
.obj-field { flex:1; min-width:120px; padding-right:16px; }
.obj-field-lbl { font-family:var(--mono); font-size:0.48rem; letter-spacing:0.2em; color:var(--amber); margin-bottom:3px; }
.obj-field-val { font-family:var(--sans); font-size:0.88rem; color:var(--text); }

/* CHAT MESSAGES */
.msg-wrap-user { display:flex; justify-content:flex-end; margin-bottom:12px; }
.msg-wrap-bot  { display:flex; justify-content:flex-start; margin-bottom:12px; }
.msg-bubble {
  max-width:76%; padding:14px 18px; border-radius:var(--r);
  font-family:var(--sans); font-size:0.92rem; line-height:1.65; color:var(--text);
}
.msg-bubble-user { background:#0D1525; border:1px solid rgba(74,143,255,0.18); border-left:3px solid var(--blue); }
.msg-bubble-bot  { background:#0A0E18; border:1px solid rgba(255,58,74,0.18);   border-left:3px solid var(--red); }
.msg-label { font-family:var(--mono); font-size:0.5rem; letter-spacing:0.22em; margin-bottom:8px; }
.msg-label-user { color:var(--blue); }
.msg-label-bot  { color:var(--red); }

/* COUNTER BADGE */
.turn-counter {
  font-family:var(--mono); font-size:0.55rem; letter-spacing:0.2em; color:var(--text-lo);
  text-align:right; margin-bottom:10px;
}

/* ONBOARDING OVERLAY */
.onboard {
  background:var(--bg2); border:1px solid var(--border3); border-radius:var(--r);
  padding:32px 36px; margin-bottom:28px;
  background: linear-gradient(135deg, var(--bg2) 0%, var(--bg3) 100%);
}
.onboard-title { font-family:var(--mono); font-size:0.62rem; letter-spacing:0.3em; color:var(--blue); margin-bottom:16px; }
.onboard-step {
  display:flex; gap:16px; align-items:flex-start; padding:12px 0;
  border-bottom:1px solid var(--border);
}
.onboard-num {
  font-family:var(--mono); font-size:0.65rem; font-weight:700; color:var(--bg);
  background:var(--blue); width:24px; height:24px; border-radius:50%;
  display:flex; align-items:center; justify-content:center; flex-shrink:0;
}
.onboard-text { font-family:var(--sans); font-size:0.9rem; color:var(--text); padding-top:2px; }
.onboard-text b { color:var(--text-hi); }

/* PLAN BADGE */
.plan-badge {
  display:inline-block; font-family:var(--mono); font-size:0.52rem; letter-spacing:0.15em;
  padding:3px 10px; border-radius:var(--r); border:1px solid var(--border3);
  color:var(--blue); background:var(--blue-dim); margin-left:8px; vertical-align:middle;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# ESTADOS DE SESIÓN
# ─────────────────────────────────────────
datos_guardados = cargar_datos()
defaults = {
    "empleados":           datos_guardados["empleados"],
    "historial_sesiones":  datos_guardados["historial_sesiones"],
    "escenarios_custom":   datos_guardados.get("escenarios_custom", {}),
    "mensajes":            [],
    "evaluacion_actual":   None,
    "mision_iniciada":     False,
    "tarjeta_objetivo":    None,
    "usuario_actual":      None,
    "login_step":          1,
    "pantalla_actual":     "menu",
    "login_modo":          "acceso",
    "dificultad_activa":   "OPERATIVE",
    "objetivo_cumplido":   False,
    "onboarding_visto":    False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_API_KEY = None


# ─────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────
token_invitacion = st.query_params.get("invite", None)
empresa_invitada = None
if token_invitacion:
    try:
        empresa_invitada = base64.urlsafe_b64decode(token_invitacion.encode()).decode()
    except:
        pass

if st.session_state.usuario_actual is None:

    # ── FLUJO INVITACIÓN ──────────────────────
    if empresa_invitada:
        st.markdown(f"""
        <div style="text-align:center;padding:60px 0 30px 0;">
          <div class="topbar-logo">CRYSIS</div>
          <div style="font-family:var(--mono);font-size:0.55rem;letter-spacing:0.3em;color:var(--blue);margin-top:8px;">
            ALISTAMIENTO · {empresa_invitada.upper()}
          </div>
        </div>""", unsafe_allow_html=True)
        _, c2, _ = st.columns([1, 2, 1])
        with c2:
            empresa_obj = next((e for e in st.session_state.empleados
                                if e["Rol"] == "Empresa" and e["Nombre"] == empresa_invitada), None)
            if empresa_obj:
                agentes_actuales = len([e for e in st.session_state.empleados
                                        if e.get("Empresa") == empresa_invitada and e.get("Rol") == "Agente"])
                plan_emp = empresa_obj.get("Plan", "Gratis")
                limite   = 9999 if plan_emp == "Enterprise" else (15 if plan_emp == "Pro" else 0)
                if agentes_actuales >= limite:
                    st.error("ACCESO DENEGADO: Cuota de agentes alcanzada o sin licencia corporativa.")
                    st.stop()
            with st.form("reg_agente"):
                st.markdown("<span class='lbl'>SOLICITUD DE CREDENCIALES</span>", unsafe_allow_html=True)
                n     = st.text_input("Identificador de Agente")
                email = st.text_input("Correo Corporativo")
                d     = st.text_input("Unidad / Departamento")
                p     = st.text_input("Contraseña", type="password")
                if st.form_submit_button("REGISTRAR", use_container_width=True):
                    if n and p and email:
                        if any(e["Nombre"] == n and e.get("Empresa") == empresa_invitada
                               for e in st.session_state.empleados):
                            st.warning("ID ya registrado en esta corporación.")
                        else:
                            nuevo = {"Nombre": n, "Email": email, "Departamento": d,
                                     "Rol": "Agente", "Empresa": empresa_invitada,
                                     "Password": p, "2FA_Verificado": True}
                            st.session_state.empleados.append(nuevo)
                            guardar_datos()
                            st.session_state.registro_completado = True
                            st.query_params.clear(); st.rerun()
        st.stop()

    if st.session_state.get("registro_completado"):
        st.success("Acreditación procesada. Identifícate para acceder.")
        st.session_state.registro_completado = False

    # ── PANTALLA LOGIN PRINCIPAL ───────────────
    col_brand, col_form = st.columns([1, 1])

    with col_brand:
        st.markdown("""
        <div style="padding:70px 36px 70px 8px; min-height:80vh; display:flex;
                    flex-direction:column; justify-content:space-between;
                    border-right:1px solid var(--border2);">
          <div>
            <div class="topbar-logo" style="font-size:3rem;letter-spacing:0.5em;margin-bottom:8px;">CRYSIS</div>
            <div style="font-family:var(--mono);font-size:0.52rem;letter-spacing:0.4em;color:var(--blue);margin-bottom:32px;">INTELLIGENCE UNIT</div>
            <div style="width:40px;height:2px;background:var(--blue);margin-bottom:24px;box-shadow:0 0 8px var(--blue);"></div>
            <div style="font-family:var(--mono);font-size:0.62rem;color:var(--text-lo);line-height:1.9;">
              Plataforma de simulación táctica avanzada para entrenamiento en negociación,
              desescalada y comunicación bajo presión extrema.
            </div>
          </div>
          <div>
            <div style="font-family:var(--mono);font-size:0.58rem;color:var(--green);letter-spacing:0.15em;">
              ● SISTEMA OPERATIVO
            </div>
            <div style="font-family:var(--mono);font-size:0.48rem;color:var(--text-lo);margin-top:8px;letter-spacing:0.2em;">
              v3.0.0 · CLASIFICADO
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

    with col_form:
        st.markdown("<div style='padding:60px 8px 60px 36px;'>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("ACCESO", key="modo_acc", use_container_width=True,
                         type="primary" if st.session_state.login_modo == "acceso" else "secondary"):
                st.session_state.login_modo = "acceso"; st.rerun()
        with c2:
            if st.button("REGISTRO", key="modo_reg", use_container_width=True,
                         type="primary" if st.session_state.login_modo == "registro" else "secondary"):
                st.session_state.login_modo = "registro"; st.rerun()

        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)

        # MODO ACCESO
        if st.session_state.login_modo == "acceso":
            if st.session_state.login_step == 1:
                with st.form("login_form"):
                    st.markdown("<span class='lbl'>IDENTIFICACIÓN DE OPERADOR</span>", unsafe_allow_html=True)
                    u_id   = st.text_input("ID Operativo")
                    u_pass = st.text_input("Contraseña", type="password")
                    if st.form_submit_button("INICIAR SESIÓN SEGURA", use_container_width=True):
                        agente = next((e for e in st.session_state.empleados
                                       if e["Nombre"] == u_id and e.get("Password") == u_pass), None)
                        if agente:
                            expiro = False
                            if "Expiracion" in agente:
                                if datetime.now() > datetime.strptime(agente["Expiracion"], "%Y-%m-%d"):
                                    expiro = True
                            if expiro:
                                st.error(f"ACCESO DENEGADO: Licencia expirada el {agente['Expiracion']}.")
                            elif agente.get("2FA_Verificado") or agente["Nombre"] == COMANDANTE_SUPREMO:
                                st.session_state.usuario_actual = agente
                                st.session_state.pantalla_actual = "menu"; st.rerun()
                            else:
                                st.session_state["2fa_code"]   = str(random.randint(100000, 999999))
                                st.session_state["2fa_agente"] = agente
                                st.session_state.login_step = 2; st.rerun()
                        else:
                            st.error("Identificación fallida.")

            elif st.session_state.login_step == 2:
                correo_dest = st.session_state["2fa_agente"].get("Email", "")
                if "correo_enviado" not in st.session_state:
                    if enviar_correo_2fa(correo_dest, st.session_state["2fa_code"]):
                        st.success(f"Código enviado a: {correo_dest}")
                    else:
                        st.error("Fallo en el sistema de correo seguro.")
                    st.session_state["correo_enviado"] = True
                with st.form("2fa_form"):
                    st.markdown("<span class='lbl'>VERIFICACIÓN 2FA</span>", unsafe_allow_html=True)
                    st.info("Autenticación de dos factores (solo primera vez).")
                    u_code = st.text_input("Código de 6 dígitos")
                    cA, cB = st.columns(2)
                    if cA.form_submit_button("VERIFICAR", use_container_width=True):
                        if u_code == st.session_state["2fa_code"]:
                            st.session_state["2fa_agente"]["2FA_Verificado"] = True
                            guardar_datos()
                            st.session_state.usuario_actual = st.session_state["2fa_agente"]
                            st.session_state.pantalla_actual = "menu"
                            st.session_state.login_step = 1
                            del st.session_state["correo_enviado"]; st.rerun()
                        else:
                            st.error("Código incorrecto.")
                    if cB.form_submit_button("CANCELAR", use_container_width=True):
                        st.session_state.login_step = 1
                        del st.session_state["correo_enviado"]; st.rerun()

        # MODO REGISTRO
        else:
            if st.session_state.get("mostrar_pago"):
                info = st.session_state.mostrar_pago
                st.success("Cuenta creada. Completa el pago para activar tu plan.")
                st.markdown(f"""
                <div style="background:var(--bg3);border:1px solid var(--amber);
                            border-left:3px solid var(--amber);padding:18px;border-radius:var(--r);margin-bottom:14px;">
                  <div style="font-family:var(--mono);font-size:0.55rem;letter-spacing:0.2em;color:var(--amber);margin-bottom:8px;">ACTIVACIÓN PENDIENTE</div>
                  <p style="color:var(--text);font-size:0.85rem;margin-bottom:12px;">
                    Cuenta <b style='color:var(--text-hi)'>{info['id']}</b> creada en Nivel BASE.
                  </p>
                  <a href="{info['link']}" target="_blank"
                     style="display:inline-block;background:var(--amber);color:#060810;
                            font-family:var(--mono);font-weight:700;font-size:0.62rem;
                            letter-spacing:0.1em;padding:10px 18px;border-radius:var(--r);text-decoration:none;">
                    IR AL PAGO — {info['plan']}
                  </a>
                </div>""", unsafe_allow_html=True)
                if st.button("ENTRAR CON NIVEL BASE", use_container_width=True):
                    st.session_state.usuario_actual = info["usuario"]
                    st.session_state.pantalla_actual = "menu"
                    del st.session_state.mostrar_pago; st.rerun()
            else:
                st.markdown("<span class='lbl'>SELECCIONAR NIVEL DE ACCESO</span>", unsafe_allow_html=True)
                if "plan_sel_reg" not in st.session_state:
                    st.session_state.plan_sel_reg = "BASE"

                planes = [
                    ("BASE",       "0 €",      "1 usuario · 1 op/mes",       False, "Gratis"),
                    ("OPERADOR",   "29 €/mes",  "Individual · ilimitado",     False, "Individual"),
                    ("ESCUADRON",  "89 €/mes",  "15 agentes · corporativo",   True,  "Pro"),
                    ("COMANDANCIA","199 €/mes", "Ilimitado · enterprise",     True,  "Enterprise"),
                ]
                p1, p2 = st.columns(2)
                for i, (nombre, precio, desc, corp, plan_key) in enumerate(planes):
                    col = p1 if i % 2 == 0 else p2
                    with col:
                        sel = st.session_state.plan_sel_reg == nombre
                        bc  = "#FFB020" if plan_key == "Enterprise" and sel else ("#4A8FFF" if sel else "#1C2640")
                        bg  = "rgba(255,176,32,0.07)" if plan_key == "Enterprise" and sel else ("var(--blue-dim)" if sel else "var(--bg3)")
                        st.markdown(f"""
                        <div style="border:1px solid {bc};background:{bg};
                                    padding:12px 14px;border-radius:var(--r);margin-bottom:6px;">
                          <div style="font-family:var(--mono);font-size:0.6rem;letter-spacing:0.15em;color:var(--text-hi);">{nombre}</div>
                          <div style="font-size:0.82rem;color:{'#FFB020' if plan_key=='Enterprise' else 'var(--blue)'};font-weight:700;margin-top:3px;">{precio}</div>
                          <div style="font-family:var(--mono);font-size:0.5rem;color:var(--text-lo);margin-top:3px;">{desc}</div>
                        </div>""", unsafe_allow_html=True)
                        if st.button(f"Seleccionar {nombre}", key=f"plan_{nombre}", use_container_width=True):
                            st.session_state.plan_sel_reg = nombre; st.rerun()

                plan_sel     = st.session_state.plan_sel_reg
                es_corp      = plan_sel in ["ESCUADRON", "COMANDANCIA"]
                es_pago      = plan_sel != "BASE"
                st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
                with st.form("registro_form"):
                    st.markdown("<span class='lbl'>DATOS DE ACCESO</span>", unsafe_allow_html=True)
                    lbl_id = "Identificador de la Entidad" if es_corp else "Alias Operativo"
                    n      = st.text_input(lbl_id)
                    email  = st.text_input("Correo de Contacto")
                    p      = st.text_input("Contraseña", type="password")
                    lbl_btn = "CREAR CUENTA E IR AL PAGO" if es_pago else "CREAR CUENTA Y ENTRAR"
                    if st.form_submit_button(lbl_btn, use_container_width=True):
                        if n and p and email:
                            emp_dest = n if es_corp else "Independiente"
                            if any(e["Nombre"] == n and e.get("Empresa", "Independiente") == emp_dest
                                   for e in st.session_state.empleados):
                                st.warning("Ya existe una cuenta con ese identificador.")
                            else:
                                if es_corp:
                                    nuevo_u = {"Nombre": n, "Email": email, "Departamento": "Administración",
                                               "Rol": "Empresa", "Plan": "Gratis", "Empresa": n,
                                               "Password": p, "2FA_Verificado": True}
                                else:
                                    nuevo_u = {"Nombre": n, "Email": email, "Rol": "Individual",
                                               "Plan": "Gratis", "Empresa": n,
                                               "Password": p, "2FA_Verificado": True}
                                st.session_state.empleados.append(nuevo_u); guardar_datos()
                                if es_pago:
                                    lk_map = {"OPERADOR": ("Individual", "OPERADOR (29€/mes)"),
                                              "ESCUADRON": ("Pro", "ESCUADRON (89€/mes)"),
                                              "COMANDANCIA": ("Enterprise", "COMANDANCIA (199€/mes)")}
                                    lk_key, lk_name = lk_map.get(plan_sel, ("Individual", plan_sel))
                                    st.session_state.mostrar_pago = {
                                        "id": n, "link": LINKS_PAGO[lk_key],
                                        "plan": lk_name, "usuario": nuevo_u}
                                    st.rerun()
                                else:
                                    st.session_state.usuario_actual = nuevo_u
                                    st.session_state.pantalla_actual = "menu"; st.rerun()
                        else:
                            st.warning("Rellena todos los campos.")

        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────
# PERMISOS
# ─────────────────────────────────────────
u = st.session_state.usuario_actual

if u["Nombre"] == COMANDANTE_SUPREMO:
    es_empresa = True; mi_plan = "Enterprise"; empresa_actual = u["Nombre"]
else:
    es_empresa    = u.get("Rol") == "Empresa"
    empresa_actual = u.get("Empresa", u["Nombre"])
    if u.get("Rol") == "Agente":
        emp_obj = next((e for e in st.session_state.empleados
                        if e["Rol"] == "Empresa" and e["Nombre"] == empresa_actual), None)
        mi_plan = emp_obj.get("Plan", "Pro") if emp_obj else "Pro"
    else:
        mi_plan = u.get("Plan", "Gratis")

if u["Nombre"] == COMANDANTE_SUPREMO:
    historial_visible   = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]
    agentes_de_mi_empresa = [u["Nombre"]]
elif es_empresa:
    agentes_de_mi_empresa = [e["Nombre"] for e in st.session_state.empleados
                              if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"]
    historial_visible   = [s for s in st.session_state.historial_sesiones
                            if s["Agente"] in agentes_de_mi_empresa
                            and s.get("Tipo_Mision") != "Personal"]
else:
    historial_visible     = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]
    agentes_de_mi_empresa = [u["Nombre"]]

mis_escenarios = {
    k: v for k, v in st.session_state.escenarios_custom.items()
    if v.get("Creador") == empresa_actual or u["Nombre"] == COMANDANTE_SUPREMO
}
TODAS_LAS_MISIONES = {**CONTEXTOS_MISION, **mis_escenarios}


# ─────────────────────────────────────────
# HELPER: ir a pantalla
# ─────────────────────────────────────────
def ir_a(pantalla):
    st.session_state.pantalla_actual = pantalla
    st.rerun()


# ─────────────────────────────────────────
# TOPBAR
# ─────────────────────────────────────────
NOMBRES_PANTALLA = {
    "menu": "", "estadisticas": "ESTADÍSTICAS", "personal": "PERSONAL",
    "expedientes": "EXPEDIENTES", "simulador": "SIMULADOR",
    "sintesis": "SÍNTESIS IA", "admin": "CONSOLA OMEGA"
}
pantalla = st.session_state.pantalla_actual
breadcrumb = f"/ {NOMBRES_PANTALLA[pantalla]}" if pantalla != "menu" else ""
rol_label  = (
    "OMNISCIENCIA GLOBAL" if u["Nombre"] == COMANDANTE_SUPREMO
    else (f"SUPERVISOR [{mi_plan.upper()}]" if es_empresa
          else f"OPERADOR · {empresa_actual.upper()}")
)

col_top, col_btns = st.columns([7, 1])
with col_top:
    st.markdown(f"""
    <div class="crysis-topbar">
      <div>
        <div class="topbar-logo">CRYSIS <span style="font-size:0.65rem;color:var(--text-lo);font-weight:400;">{breadcrumb}</span></div>
        <div class="topbar-breadcrumb">{rol_label} · {u['Nombre'].upper()}
          <span class="plan-badge">{mi_plan.upper()}</span>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)
with col_btns:
    st.markdown("<div style='padding-top:14px;display:flex;flex-direction:column;gap:6px;'>", unsafe_allow_html=True)
    if pantalla != "menu":
        if st.button("← MENÚ", key="btn_menu"):
            ir_a("menu")
    if st.button("SALIR", key="btn_logout", type="secondary"):
        st.session_state.usuario_actual  = None
        st.session_state.login_step      = 1
        st.session_state.pantalla_actual = "menu"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# PANTALLA: MENÚ
# ═══════════════════════════════════════════
if pantalla == "menu":
    total_ops    = len(historial_visible)
    media_global = int(sum(s["Nota"] for s in historial_visible) / total_ops) if total_ops else 0
    ops_exitosas = sum(1 for s in historial_visible if s["Nota"] >= 80)
    tasa_exito   = int((ops_exitosas / total_ops) * 100) if total_ops else 0
    hora_actual  = datetime.now().strftime("%H:%M") + " · " + datetime.now().strftime("%d.%m.%Y")

    # ONBOARDING (solo si no se ha visto)
    if not st.session_state.onboarding_visto and total_ops == 0:
        st.markdown(f"""
        <div class="onboard">
          <div class="onboard-title">// BIENVENIDO AL SISTEMA CRYSIS</div>
          <div class="onboard-step">
            <div class="onboard-num">1</div>
            <div class="onboard-text">Ve al módulo <b>SIMULADOR TÁCTICO</b> y elige un escenario de negociación.</div>
          </div>
          <div class="onboard-step">
            <div class="onboard-num">2</div>
            <div class="onboard-text">Selecciona el <b>nivel de dificultad</b>: RECRUIT para empezar, ELITE para el reto máximo.</div>
          </div>
          <div class="onboard-step">
            <div class="onboard-num">3</div>
            <div class="onboard-text">Negocia con el sujeto IA. El sistema detectará <b>automáticamente</b> si cumples el objetivo.</div>
          </div>
          <div class="onboard-step" style="border-bottom:none;">
            <div class="onboard-num">4</div>
            <div class="onboard-text">Recibe un <b>informe táctico detallado</b> y descarga tu dossier en PDF.</div>
          </div>
        </div>""", unsafe_allow_html=True)
        if st.button("ENTENDIDO — CERRAR BRIEFING INICIAL", use_container_width=True):
            st.session_state.onboarding_visto = True; st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align:center;padding:32px 0 36px 0;">
      <div style="font-family:var(--mono);font-size:0.5rem;letter-spacing:0.4em;color:var(--blue);margin-bottom:10px;">CUARTEL GENERAL</div>
      <div style="font-family:var(--sans);font-size:2.2rem;font-weight:700;color:var(--text-hi);margin-bottom:4px;">
        Bienvenido, {u['Nombre'].upper()}
      </div>
      <div style="font-family:var(--mono);font-size:0.58rem;letter-spacing:0.25em;color:var(--text-lo);">
        {hora_actual} · SISTEMA OPERATIVO
      </div>
    </div>""", unsafe_allow_html=True)

    mes_actual = datetime.now().strftime("%Y-%m")
    ops_mes    = len([s for s in historial_visible if str(s.get("Fecha","")).startswith(mes_actual)])

    c1, c2, c3 = st.columns(3)
    mods = [
        (c1, "primary",  "#4A8FFF", "MOD-01 / ESTADÍSTICAS", "Análisis de Rendimiento",
         "Métricas globales, histórico de desempeño y comparativa por operador.",
         f"RENDIMIENTO MEDIO", f"{media_global}%", "goto_stats", "estadisticas"),
        (c2, "danger",   "#FF3A4A", "MOD-02 / DESPLIEGUE",   "Simulador Táctico",
         "Inicia una operación de negociación táctica en tiempo real con objetivo IA.",
         "OPS ESTE MES", str(ops_mes), "goto_sim", "simulador"),
        (c3, "neutral",  "#4A8FFF", "MOD-03 / EXPEDIENTES",  "Archivo Operacional",
         "Consulta y descarga de dossiers con transcripciones completas.",
         "TOTAL EXPEDIENTES", str(total_ops), "goto_exp", "expedientes"),
    ]
    for col, tipo, accent, code, title, desc, stat_lbl, stat_val, key, dest in mods:
        with col:
            st.markdown(f"""
            <div class="mod">
              <div class="mod-accent" style="background:{accent};box-shadow:0 0 8px {accent}44;"></div>
              <div class="mod-code">{code}</div>
              <div class="mod-title">{title}</div>
              <div class="mod-desc">{desc}</div>
              <div class="mod-stat"><b style="color:{accent};">{stat_val}</b>{stat_lbl}</div>
            </div>""", unsafe_allow_html=True)
            if st.button(f"ACCEDER", key=key, use_container_width=True):
                ir_a(dest)

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
    c4, c5 = st.columns(2) if u["Nombre"] != COMANDANTE_SUPREMO else st.columns(3)
    agentes_activos = len([e for e in st.session_state.empleados
                           if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"])
    with c4:
        st.markdown(f"""
        <div class="mod">
          <div class="mod-accent" style="background:var(--border3);"></div>
          <div class="mod-code">MOD-04 / PERSONAL</div>
          <div class="mod-title">Gestión de Operadores</div>
          <div class="mod-desc">Reclutamiento, control de accesos y ajustes de cuenta.</div>
          <div class="mod-stat"><b style="color:var(--text-hi);">{agentes_activos}</b>AGENTES ACTIVOS</div>
        </div>""", unsafe_allow_html=True)
        if st.button("ACCEDER", key="goto_pers", use_container_width=True): ir_a("personal")
    with c5:
        esc_creados = len(mis_escenarios)
        st.markdown(f"""
        <div class="mod">
          <div class="mod-accent" style="background:var(--amber);box-shadow:0 0 8px rgba(255,176,32,0.3);"></div>
          <div class="mod-code">MOD-05 / SÍNTESIS IA</div>
          <div class="mod-title">Generación de Escenarios</div>
          <div class="mod-desc">Motor IA para crear simulaciones personalizadas a tu contexto operativo.</div>
          <div class="mod-stat"><b style="color:var(--amber);">{esc_creados}</b>ESCENARIOS ACTIVOS</div>
        </div>""", unsafe_allow_html=True)
        if st.button("ACCEDER", key="goto_sint", use_container_width=True): ir_a("sintesis")

    if u["Nombre"] == COMANDANTE_SUPREMO:
        mrr = sum({"Enterprise":199,"Pro":89,"Individual":29,"Gratis":0}.get(e.get("Plan","Gratis"),0)
                  for e in st.session_state.empleados)
        # c5 already defined as third column in this branch
        cols6 = st.columns(3)
        with cols6[2]:
            st.markdown(f"""
            <div class="mod">
              <div class="mod-accent" style="background:var(--red);"></div>
              <div class="mod-code">MOD-06 / OMEGA</div>
              <div class="mod-title">Consola Omega</div>
              <div class="mod-desc">Panel de control global. Gestión de usuarios, planes y métricas SaaS.</div>
              <div class="mod-stat"><b style="color:var(--red);">{mrr}€</b>MRR ESTIMADO</div>
            </div>""", unsafe_allow_html=True)
            if st.button("ACCEDER", key="goto_admin", use_container_width=True): ir_a("admin")

    st.stop()


# ═══════════════════════════════════════════
# PANTALLA: ESTADÍSTICAS
# ═══════════════════════════════════════════
elif pantalla == "estadisticas":
    st.markdown("""<div class="section-hd">
      <div class="section-code">MOD-01</div>
      <div class="section-title">Análisis de Rendimiento</div>
    </div>""", unsafe_allow_html=True)

    total_ops    = len(historial_visible)
    media_global = int(sum(s["Nota"] for s in historial_visible) / total_ops) if total_ops else 0
    ops_exitosas = sum(1 for s in historial_visible if s["Nota"] >= 80)
    tasa_exito   = int((ops_exitosas / total_ops) * 100) if total_ops else 0
    obj_cumplidos = sum(1 for s in historial_visible if s.get("ObjetivoCumplido"))

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"""<div class="mc"><div class="mc-lbl">RENDIMIENTO MEDIO</div>
      <div class="mc-val" style="color:{'var(--green)' if media_global>=70 else 'var(--red)'};">{media_global}%</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="mc"><div class="mc-lbl">TASA EXCELENCIA</div>
      <div class="mc-val" style="color:{'var(--green)' if tasa_exito>=50 else 'var(--red)'};">{tasa_exito}%</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="mc"><div class="mc-lbl">MISIONES TOTALES</div>
      <div class="mc-val" style="color:var(--blue);">{total_ops}</div></div>""", unsafe_allow_html=True)
    c4.markdown(f"""<div class="mc" style="--accent:var(--green);"><div class="mc-lbl">OBJ. CUMPLIDOS (AUTO)</div>
      <div class="mc-val" style="color:var(--green);">{obj_cumplidos}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if not historial_visible:
        st.markdown("<div style='text-align:center;padding:60px;color:var(--text-lo);font-family:var(--mono);'>SIN REGISTROS OPERACIONALES</div>", unsafe_allow_html=True)
    else:
        df = pd.DataFrame(historial_visible)
        df["Nota"] = pd.to_numeric(df["Nota"])
        cl, cr = st.columns(2, gap="medium")
        with cl:
            st.markdown("<span class='lbl'>DISTRIBUCIÓN DE ESCENARIOS</span>", unsafe_allow_html=True)
            esc_c = df["Escenario"].value_counts().reset_index()
            esc_c.columns = ["Escenario", "Count"]
            fig = go.Figure(go.Pie(
                labels=esc_c["Escenario"], values=esc_c["Count"], hole=0.65,
                marker=dict(colors=['#4A8FFF','#00E5A0','#FFB020','#FF3A4A'])
            ))
            fig.update_layout(**PLOTLY_THEME, height=280, showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with cr:
            if es_empresa:
                st.markdown("<span class='lbl'>EVALUACIÓN POR OPERADOR</span>", unsafe_allow_html=True)
                avg = df.groupby("Agente")["Nota"].mean().reset_index()
                fig2 = go.Figure(go.Bar(x=avg["Nota"], y=avg["Agente"], orientation='h',
                                        marker=dict(color='#4A8FFF')))
                fig2.update_layout(**PLOTLY_THEME, height=280)
            else:
                st.markdown("<span class='lbl'>HISTÓRICO DE DESEMPEÑO</span>", unsafe_allow_html=True)
                df["Fecha_dt"] = pd.to_datetime(df["Fecha"])
                df_s = df.sort_values("Fecha_dt")
                fig2 = go.Figure(go.Scatter(
                    x=df_s["Fecha_dt"], y=df_s["Nota"],
                    mode='lines+markers', line=dict(color='#4A8FFF', width=2),
                    marker=dict(size=6)
                ))
                fig2.add_hline(y=80, line_dash="dot", line_color="#00E5A0", annotation_text="80%")
                fig2.update_layout(**PLOTLY_THEME, height=280)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        # Distribución por dificultad
        if "Dificultad" in df.columns:
            st.markdown("<span class='lbl'>DISTRIBUCIÓN POR DIFICULTAD</span>", unsafe_allow_html=True)
            diff_data = df.groupby("Dificultad")["Nota"].agg(["mean","count"]).reset_index()
            colors_diff = {"RECRUIT": "#00E5A0", "OPERATIVE": "#FFB020", "ELITE": "#FF3A4A"}
            fig3 = go.Figure()
            for _, row in diff_data.iterrows():
                fig3.add_bar(
                    x=[row["Dificultad"]], y=[row["mean"]],
                    marker_color=colors_diff.get(row["Dificultad"], "#4A8FFF"),
                    name=row["Dificultad"],
                    text=[f"{int(row['mean'])}% ({int(row['count'])} ops)"],
                    textposition="auto"
                )
            fig3.update_layout(**PLOTLY_THEME, height=220, showlegend=False)
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})


# ═══════════════════════════════════════════
# PANTALLA: PERSONAL
# ═══════════════════════════════════════════
elif pantalla == "personal":
    st.markdown("""<div class="section-hd">
      <div class="section-code">MOD-04</div>
      <div class="section-title">Gestión de Operadores</div>
    </div>""", unsafe_allow_html=True)

    if es_empresa:
        st.markdown("<span class='lbl'>ENLACE SEGURO DE RECLUTAMIENTO</span>", unsafe_allow_html=True)
        if mi_plan in ["Pro","Enterprise"] or u["Nombre"] == COMANDANTE_SUPREMO:
            token_cifrado = base64.urlsafe_b64encode(empresa_actual.encode()).decode()
            enlace = f"https://crysis.streamlit.app/?invite={token_cifrado}"
            st.info("Comparte este enlace con tus agentes para incorporación automática.")
            st.code(enlace, language="html")
        else:
            st.warning("Tu licencia no permite escuadrones. Actualiza a ESCUADRON o COMANDANCIA.")
        st.markdown("<br><span class='lbl'>PLANTILLA OPERATIVA</span>", unsafe_allow_html=True)
        agentes_mios = [e for e in st.session_state.empleados
                        if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"]
        if agentes_mios:
            for ag in agentes_mios:
                st.markdown(f"**{ag['Nombre']}** · {ag.get('Departamento','—')} · {ag['Email']}")
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("REVOCAR ACCESO"):
                ag_borrar = st.selectbox("Operador:", [a["Nombre"] for a in agentes_mios])
                if st.button("REVOCAR CREDENCIALES", type="primary"):
                    st.session_state.empleados = [e for e in st.session_state.empleados if e["Nombre"] != ag_borrar]
                    guardar_datos(); st.success(f"Operador {ag_borrar} revocado."); st.rerun()
        else:
            st.markdown("<span style='color:var(--text-lo);font-family:var(--mono);font-size:0.7rem;'>Sin agentes activos.</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="briefing"><h4>DATOS DEL OPERADOR</h4>
          <p><b>ID:</b> {u['Nombre']} &nbsp;|&nbsp; <b>Unidad:</b> {empresa_actual} &nbsp;|&nbsp; <b>Plan:</b> {mi_plan}</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br><span class='lbl'>AJUSTES DE CUENTA</span>", unsafe_allow_html=True)
    with st.expander("CAMBIAR CONTRASEÑA"):
        nueva_pass = st.text_input("Nueva Contraseña", type="password")
        if st.button("ACTUALIZAR"):
            if nueva_pass:
                for e in st.session_state.empleados:
                    if e["Nombre"] == u["Nombre"]: e["Password"] = nueva_pass
                st.session_state.usuario_actual["Password"] = nueva_pass
                guardar_datos(); st.success("Contraseña actualizada.")
            else: st.warning("Introduce una contraseña válida.")

    if u["Nombre"] != COMANDANTE_SUPREMO:
        st.markdown("<br><span class='lbl'>SUSCRIPCIÓN</span>", unsafe_allow_html=True)
        cp1, cp2, cp3 = st.columns(3)
        for col, (nombre, precio, desc, plan_key) in zip(
            [cp1, cp2, cp3],
            [("OPERADOR","29€/mes","Individual","Individual"),
             ("ESCUADRON","89€/mes","15 agentes","Pro"),
             ("COMANDANCIA","199€/mes","Ilimitado","Enterprise")]
        ):
            with col:
                ac = "#FFB020" if plan_key=="Enterprise" else "var(--blue)"
                st.markdown(f"""<div class="mc" style="{'border-left-color:var(--amber);' if plan_key=='Enterprise' else ''}">
                  <div class="mc-lbl">{nombre}</div>
                  <div class="mc-val" style="font-size:1.2rem;color:{ac};">{precio}</div>
                  <div style="font-family:var(--mono);font-size:0.52rem;color:var(--text-lo);margin-top:8px;">{desc}</div>
                </div>""", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                if mi_plan == plan_key: st.success("Plan activo")
                else:
                    link = LINKS_PAGO.get("Enterprise" if plan_key=="Enterprise" else ("Pro" if plan_key=="Pro" else "Individual"))
                    st.markdown(f'<a href="{link}" target="_blank"><button style="background:var(--blue);color:var(--bg);font-family:var(--mono);font-weight:700;border:none;padding:10px;border-radius:var(--r);cursor:pointer;width:100%;font-size:0.62rem;letter-spacing:0.1em;">ACTIVAR</button></a>', unsafe_allow_html=True)

    st.markdown("<br><span class='lbl'>ZONA DE RIESGO</span>", unsafe_allow_html=True)
    if st.button("ELIMINAR MI CUENTA DEFINITIVAMENTE", type="primary"):
        if es_empresa:
            st.session_state.empleados = [e for e in st.session_state.empleados if e.get("Empresa") != u["Nombre"]]
        else:
            st.session_state.empleados = [e for e in st.session_state.empleados if e["Nombre"] != u["Nombre"]]
        st.session_state.usuario_actual = None; guardar_datos(); st.rerun()


# ═══════════════════════════════════════════
# PANTALLA: EXPEDIENTES
# ═══════════════════════════════════════════
elif pantalla == "expedientes":
    st.markdown("""<div class="section-hd">
      <div class="section-code">MOD-03</div>
      <div class="section-title">Archivo Operacional</div>
    </div>""", unsafe_allow_html=True)

    if historial_visible:
        df_hist = pd.DataFrame(historial_visible)
        df_hist["Nota"] = pd.to_numeric(df_hist["Nota"])
        for agente, df_ag in df_hist.groupby("Agente"):
            media_ag = int(df_ag["Nota"].mean())
            with st.expander(f"OPERADOR: {agente.upper()}  —  MEDIA: {media_ag}%", expanded=False):
                for escenario, df_op in df_ag.groupby("Escenario"):
                    media_op  = int(df_op["Nota"].mean())
                    lbl_esc   = escenario.replace("OPERACION: ", "")
                    with st.expander(f"{lbl_esc}  —  Media: {media_op}%", expanded=True):
                        for _, s in df_op.sort_values("Fecha", ascending=False).iterrows():
                            nota = s["Nota"]
                            c_nota = "#00E5A0" if nota >= 80 else ("#FFB020" if nota >= 50 else "#FF3A4A")
                            modo   = "PRIVADO" if s.get("Tipo_Mision") == "Personal" else "OFICIAL"
                            diff   = s.get("Dificultad", "—")
                            diff_c = {"RECRUIT":"#00E5A0","OPERATIVE":"#FFB020","ELITE":"#FF3A4A"}.get(diff, "var(--text-lo)")
                            obj_badge = (
                                '<span style="font-family:var(--mono);font-size:0.5rem;letter-spacing:0.12em;'
                                'color:var(--green);background:rgba(0,229,160,0.1);'
                                'border:1px solid var(--green);padding:2px 8px;border-radius:var(--r);">✓ OBJETIVO CUMPLIDO</span>'
                                if s.get("ObjetivoCumplido") else ""
                            )
                            st.markdown(f"""
                            <div style="border-bottom:1px solid var(--border);padding:14px 0;margin-bottom:14px;">
                              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:6px;">
                                <span style="color:var(--text-lo);font-size:0.75rem;font-family:var(--mono);">{s['Fecha']} · {modo}</span>
                                <div style="display:flex;align-items:center;gap:10px;">
                                  <span style="font-family:var(--mono);font-size:0.58rem;color:{diff_c};">{diff}</span>
                                  {obj_badge}
                                  <span style="font-family:var(--mono);color:{c_nota};font-weight:700;">{nota}%</span>
                                </div>
                              </div>
                              <div style="font-size:0.87rem;color:var(--text);margin-bottom:10px;">{s['Evaluacion'][:300]}...</div>
                            </div>""", unsafe_allow_html=True)
                            st.download_button(
                                label="EXTRAER DOSSIER PDF",
                                data=generar_pdf_dossier(s),
                                file_name=f"CRYSIS_{s['Agente']}_{s['Fecha'][:10]}.pdf",
                                mime="application/pdf",
                                key=f"pdf_{s['Agente']}_{s['Fecha']}"
                            )
                            if es_empresa and mi_plan == "Enterprise" and "Transcripcion" in s:
                                st.markdown("<br><span style='color:var(--amber);font-size:0.62rem;font-family:var(--mono);'>AUDITORÍA DE COMUNICACIONES</span>", unsafe_allow_html=True)
                                for tr in s["Transcripcion"]:
                                    ag_tr = "OPERADOR" if tr["role"] == "user" else "SUJETO"
                                    colr  = "var(--blue)" if tr["role"] == "user" else "var(--red)"
                                    st.markdown(f"<div style='font-size:0.8rem;margin-bottom:4px;'><b style='color:{colr}'>{ag_tr}:</b> <span style='color:var(--text-lo)'>{tr['content']}</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center;padding:60px;color:var(--text-lo);font-family:var(--mono);'>DIRECTORIO VACÍO</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# PANTALLA: SIMULADOR
# ═══════════════════════════════════════════
elif pantalla == "simulador":
    st.markdown("""<div class="section-hd">
      <div class="section-code">MOD-02</div>
      <div class="section-title">Simulador Táctico</div>
    </div>""", unsafe_allow_html=True)

    # ── FASE 1: CONFIGURACIÓN ──────────────────────────────────────────
    if not st.session_state.mision_iniciada:

        c1, c2 = st.columns(2)
        if es_empresa:
            ag_sel = c1.selectbox("Asignar Operador:", agentes_de_mi_empresa)
        else:
            ag_sel = u["Nombre"]
            c1.markdown(f"""<div style="padding:8px 0;font-family:var(--mono);font-size:0.75rem;color:var(--text-hi);">
              <span style="color:var(--blue);font-size:0.52rem;display:block;margin-bottom:4px;">OPERADOR</span>
              {ag_sel}
            </div>""", unsafe_allow_html=True)

        es_sel = c2.selectbox("Protocolo de Operación:", list(TODAS_LAS_MISIONES.keys()))

        # SELECTOR DE DIFICULTAD
        st.markdown("<br><span class='lbl'>NIVEL DE DIFICULTAD</span>", unsafe_allow_html=True)
        dc1, dc2, dc3 = st.columns(3)
        for col, (key, info_d) in zip([dc1, dc2, dc3], NIVELES_DIFICULTAD.items()):
            with col:
                sel = st.session_state.dificultad_activa == key
                border_c = info_d["color"] if sel else "var(--border2)"
                bg_c     = f"rgba({','.join(str(int(info_d['color'].lstrip('#')[i:i+2],16)) for i in (0,2,4))},0.1)" if sel else "var(--bg3)"
                glow     = f"0 0 16px rgba({','.join(str(int(info_d['color'].lstrip('#')[i:i+2],16)) for i in (0,2,4))},0.2)" if sel else "none"
                st.markdown(f"""
                <div style="border:1px solid {border_c};background:{bg_c};padding:16px;
                            border-radius:var(--r);margin-bottom:8px;box-shadow:{glow};transition:all 0.2s;">
                  <div style="font-family:var(--mono);font-size:0.65rem;font-weight:700;
                              letter-spacing:0.18em;color:{info_d['color']};margin-bottom:4px;">{key}</div>
                  <div style="font-family:var(--mono);font-size:0.55rem;color:var(--text-lo);line-height:1.5;">{info_d['desc']}</div>
                </div>""", unsafe_allow_html=True)
                if st.button(f"{'✓ ACTIVO' if sel else 'SELECCIONAR'}", key=f"diff_{key}", use_container_width=True,
                             type="primary" if sel else "secondary"):
                    st.session_state.dificultad_activa = key; st.rerun()

        # BRIEFING
        info = TODAS_LAS_MISIONES[es_sel]
        diff_info = NIVELES_DIFICULTAD[st.session_state.dificultad_activa]
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""<div class="briefing">
          <h4>// REPORTE DE SITUACIÓN</h4>
          <p><b>Contexto:</b> {info['contexto']}</p>
          <p><b>Objetivo:</b> {info['objetivo']}</p>
          <p><b>Sujeto:</b> {info['perfil_sujeto']}</p>
          <p><b>Dificultad activa:</b> <span style="color:{diff_info['color']};font-weight:700;">{diff_info['label']}</span> — {diff_info['desc']}</p>
        </div>""", unsafe_allow_html=True)

        if u.get("Rol") == "Agente":
            tipo_despliegue = st.radio(
                "Privacidad:",
                ["Misión Oficial (Auditable por el Mando)", "Entrenamiento Privado (Oculto en expediente)"],
                horizontal=True
            )
            tipo_mision_val = "Corporativa" if "Oficial" in tipo_despliegue else "Personal"
        else:
            tipo_mision_val = "Personal"

        # Control cuota
        mes_actual   = datetime.now().strftime("%Y-%m")
        ops_este_mes = len([s for s in st.session_state.historial_sesiones
                            if s["Agente"] == (ag_sel if es_empresa else u["Nombre"])
                            and str(s.get("Fecha","")).startswith(mes_actual)])
        bloquear = False
        if mi_plan == "Gratis" and ops_este_mes >= 1:
            bloquear = True; st.error("CUOTA BASE SUPERADA: 1 operación/mes en Nivel BASE.")
        elif mi_plan == "Pro" and ops_este_mes >= 3:
            bloquear = True; st.error("CUOTA ESCUADRON SUPERADA: 3 operaciones/mes por agente.")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚡ INICIAR ENLACE DE COMUNICACIÓN", use_container_width=True, disabled=bloquear, type="primary"):
            if GROQ_API_KEY:
                with st.spinner("Estableciendo conexión segura..."):
                    try:
                        client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                        json_prompt = (f"Genera para {info['perfil_sujeto']} EXCLUSIVAMENTE JSON con 3 claves: "
                                       "'Nombre_Completo', 'Familia', 'Estado_Mental'.")
                        res = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role":"user","content":json_prompt}],
                            response_format={"type":"json_object"}
                        ).choices[0].message.content
                        st.session_state.tarjeta_objetivo = json.loads(res)
                    except:
                        st.session_state.tarjeta_objetivo = {
                            "Nombre_Completo": "Desconocido",
                            "Familia": "Clasificado",
                            "Estado_Mental": "Inestable"
                        }
            st.session_state.mision_iniciada    = True
            st.session_state.mensajes           = []
            st.session_state.agente_activo      = ag_sel if es_empresa else u["Nombre"]
            st.session_state.escenario_activo   = es_sel
            st.session_state.tipo_mision_actual = tipo_mision_val
            st.session_state.objetivo_cumplido  = False
            st.rerun()

    # ── FASE 2: EVALUACIÓN MOSTRADA ───────────────────────────────────
    elif st.session_state.evaluacion_actual:
        nota_actual = 0
        m = re.search(r'PUNTUACI[OÓ]N FINAL[^\d]*(\d+)', st.session_state.evaluacion_actual, re.IGNORECASE)
        if m: nota_actual = int(m.group(1))
        c_nota = "#00E5A0" if nota_actual >= 80 else ("#FFB020" if nota_actual >= 50 else "#FF3A4A")

        if st.session_state.objetivo_cumplido:
            st.markdown("""<div class="obj-cumplido">
              <div class="obj-cumplido-title">// OBJETIVO CUMPLIDO — MISIÓN COMPLETADA</div>
              <div class="obj-cumplido-desc">El sistema detectó que el operador alcanzó la directiva de la misión.</div>
            </div>""", unsafe_allow_html=True)

        st.markdown(f"""<div class="mc" style="margin-bottom:20px;">
          <div class="mc-lbl">PUNTUACIÓN FINAL</div>
          <div class="mc-val" style="color:{c_nota};font-size:3rem;">{nota_actual}<span style="font-size:1rem;color:var(--text-lo);">/100</span></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<span class='lbl'>INFORME DE EVALUACIÓN TÁCTICA</span>", unsafe_allow_html=True)
        st.markdown(st.session_state.evaluacion_actual)

        st.markdown("<br>", unsafe_allow_html=True)
        cend1, cend2 = st.columns(2)
        with cend1:
            if st.button("← VOLVER AL MENÚ", use_container_width=True, type="primary"):
                st.session_state.mision_iniciada  = False
                st.session_state.evaluacion_actual = None
                st.session_state.mensajes          = []
                st.session_state.tarjeta_objetivo  = None
                st.session_state.objetivo_cumplido = False
                st.session_state.pantalla_actual   = "menu"; st.rerun()
        with cend2:
            ultima = st.session_state.historial_sesiones[-1]
            st.download_button(
                label="DESCARGAR DOSSIER PDF",
                data=generar_pdf_dossier(ultima),
                file_name=f"CRYSIS_{ultima['Agente']}_Report.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    # ── FASE 3: SIMULACIÓN ACTIVA ─────────────────────────────────────
    else:
        esc_activo  = st.session_state.escenario_activo
        info        = TODAS_LAS_MISIONES[esc_activo]
        diff_key    = st.session_state.get("dificultad_activa", "OPERATIVE")
        diff_info   = NIVELES_DIFICULTAD[diff_key]
        n_turnos    = len([m for m in st.session_state.mensajes if m["role"] == "user"])

        # Status bar
        st.markdown(f"""<div class="status-bar">
          ● ENLACE ACTIVO · {esc_activo} · OPERADOR: {st.session_state.agente_activo.upper()}
          &nbsp;&nbsp;|&nbsp;&nbsp;
          <span style="color:{diff_info['color']};">{diff_info['label']}</span>
          &nbsp;&nbsp;|&nbsp;&nbsp;
          TURNO {n_turnos}
        </div>""", unsafe_allow_html=True)

        # BANNER: objetivo cumplido automáticamente
        if st.session_state.objetivo_cumplido:
            st.markdown("""<div class="obj-cumplido">
              <div class="obj-cumplido-title">// OBJETIVO DETECTADO COMO CUMPLIDO</div>
              <div class="obj-cumplido-desc">
                El sistema ha detectado que has alcanzado la directiva de la misión.
                Puedes continuar la conversación o solicitar la evaluación final.
              </div>
            </div>""", unsafe_allow_html=True)

        # Tarjeta de objetivo
        if st.session_state.tarjeta_objetivo:
            t = st.session_state.tarjeta_objetivo
            st.markdown(f"""<div class="obj-card">
              <div class="obj-field">
                <div class="obj-field-lbl">IDENTIFICACIÓN</div>
                <div class="obj-field-val">{t.get('Nombre_Completo','N/A')}</div>
              </div>
              <div class="obj-field">
                <div class="obj-field-lbl">VÍNCULOS</div>
                <div class="obj-field-val">{t.get('Familia','N/A')}</div>
              </div>
              <div class="obj-field">
                <div class="obj-field-lbl">ESTADO CLÍNICO</div>
                <div class="obj-field-val">{t.get('Estado_Mental','N/A')}</div>
              </div>
              <div class="obj-field">
                <div class="obj-field-lbl">DIRECTIVA</div>
                <div class="obj-field-val" style="font-size:0.78rem;color:var(--text-lo);">{info['objetivo']}</div>
              </div>
            </div>""", unsafe_allow_html=True)

        # Contador de turnos
        st.markdown(f"""<div class="turn-counter">TURNO {n_turnos} · {len(st.session_state.mensajes)} MENSAJES</div>""", unsafe_allow_html=True)

        # Mensajes
        for m in st.session_state.mensajes:
            if m["role"] == "user":
                st.markdown(f"""<div class="msg-wrap-user">
                  <div class="msg-bubble msg-bubble-user">
                    <div class="msg-label msg-label-user">OPERADOR</div>
                    {m['content']}
                  </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="msg-wrap-bot">
                  <div class="msg-bubble msg-bubble-bot">
                    <div class="msg-label msg-label-bot">SUJETO</div>
                    {m['content']}
                  </div>
                </div>""", unsafe_allow_html=True)

        # Chat input
        if prompt := st.chat_input("Introduce tu directiva de respuesta..."):
            st.session_state.mensajes.append({"role": "user", "content": prompt}); st.rerun()

        # Respuesta IA + detección de objetivo
        if st.session_state.mensajes and st.session_state.mensajes[-1]["role"] == "user":
            if GROQ_API_KEY:
                client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                base_prompt = TODAS_LAS_MISIONES[esc_activo]["prompt"] + diff_info["modificador"]
                if st.session_state.tarjeta_objetivo:
                    t = st.session_state.tarjeta_objetivo
                    base_prompt += (f"\n\n[Tu nombre es {t.get('Nombre_Completo')}. "
                                    f"Familia: {t.get('Familia')}. Estado: {t.get('Estado_Mental')}.]")
                with st.spinner(""):
                    respuesta = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role":"system","content":base_prompt}] + st.session_state.mensajes
                    ).choices[0].message.content
                st.session_state.mensajes.append({"role": "assistant", "content": respuesta})

                # Detección automática de objetivo (sin bloquear si falla)
                if not st.session_state.objetivo_cumplido:
                    cumplido = verificar_objetivo_cumplido(client, info, st.session_state.mensajes)
                    if cumplido:
                        st.session_state.objetivo_cumplido = True

                st.rerun()

        # Botones de control (siempre visibles)
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        col_ev, col_ab = st.columns([3, 1])

        with col_ab:
            if st.button("✕ ROMPER ENLACE", type="secondary", use_container_width=True):
                st.session_state.mision_iniciada   = False
                st.session_state.mensajes          = []
                st.session_state.tarjeta_objetivo  = None
                st.session_state.objetivo_cumplido = False
                st.rerun()

        with col_ev:
            label_eval = "★ SOLICITAR EVALUACIÓN TÁCTICA" if not st.session_state.objetivo_cumplido else "★ OBJETIVO CUMPLIDO — SOLICITAR EVALUACIÓN"
            eval_disabled = len(st.session_state.mensajes) == 0
            if st.button(label_eval, use_container_width=True, disabled=eval_disabled, type="primary"):
                with st.spinner("Procesando auditoría lingüística..."):
                    client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                    hist_txt = "\n".join([
                        f"{'OPERADOR' if m['role']=='user' else 'SUJETO'}: {m['content']}"
                        for m in st.session_state.mensajes
                    ])
                    bonus_obj = (
                        "\n\nNOTA ADICIONAL: El sistema ha detectado que el OPERADOR ha cumplido el objetivo principal."
                        " Añade hasta 10 puntos de bonificación si la táctica utilizada fue limpia y profesional."
                        if st.session_state.objetivo_cumplido else ""
                    )
                    eval_prompt = f"""Eres un Analista de Inteligencia y Negociación Táctica altamente estricto.
Evalúa el desempeño del OPERADOR en el escenario: {esc_activo}.
Situación: {info['contexto']}
Objetivo: {info['objetivo']}
Dificultad: {diff_key}

TRANSCRIPCION:
{hist_txt}
{bonus_obj}

REGLAS DE EVALUACIÓN:
1. NO regales puntuación por cortesía básica.
2. 80-100 SOLO si hay control absoluto, técnicas avanzadas y resolución impecable.
3. 50-79 para trabajo correcto sin técnicas profesionales.
4. 0-49 si cede, es manipulado, usa lenguaje amenazante o rompe protocolos.
5. Nivel ELITE requiere criterio más estricto que RECRUIT.

ESTRUCTURA OBLIGATORIA:
## ANÁLISIS DE LENGUAJE
## TÁCTICAS EMPLEADAS
## ERRORES CRÍTICOS
## VEREDICTO FINAL
## CÓMO MEJORAR

PUNTUACION FINAL: XX/100"""

                    informe = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role":"user","content":eval_prompt}]
                    ).choices[0].message.content

                    try:
                        match = re.search(r'PUNTUACI[OÓ]N FINAL[^\d]*(\d+)', informe, re.IGNORECASE)
                        nota = min(int(match.group(1)), 100) if match else 50
                    except:
                        nota = 50

                    st.session_state.evaluacion_actual = informe
                    st.session_state.historial_sesiones.append({
                        "Fecha":          datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Agente":         st.session_state.agente_activo,
                        "Escenario":      esc_activo,
                        "Dificultad":     diff_key,
                        "Nota":           nota,
                        "Evaluacion":     informe,
                        "Transcripcion":  st.session_state.mensajes,
                        "Tipo_Mision":    st.session_state.tipo_mision_actual,
                        "ObjetivoCumplido": st.session_state.objetivo_cumplido
                    })
                    guardar_datos(); st.rerun()


# ═══════════════════════════════════════════
# PANTALLA: SÍNTESIS IA
# ═══════════════════════════════════════════
elif pantalla == "sintesis":
    st.markdown("""<div class="section-hd">
      <div class="section-code">MOD-05</div>
      <div class="section-title">Generación de Escenarios</div>
    </div>""", unsafe_allow_html=True)

    col_izq, col_der = st.columns([2, 1], gap="large")
    with col_izq:
        creados = len(mis_escenarios)
        if mis_escenarios:
            st.markdown("<span class='lbl'>ESCENARIOS ACTIVOS</span>", unsafe_allow_html=True)
            for nombre_esc, datos_esc in mis_escenarios.items():
                ce1, ce2 = st.columns([4, 1])
                ce1.markdown(f"""<div style="font-family:var(--sans);font-size:0.9rem;color:var(--text-hi);padding:6px 0;">{nombre_esc}</div>""", unsafe_allow_html=True)
                if ce2.button("ELIMINAR", key=f"del_{nombre_esc}", type="secondary"):
                    del st.session_state.escenarios_custom[nombre_esc]; guardar_datos(); st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("<span class='lbl'>NUEVA SIMULACIÓN</span>", unsafe_allow_html=True)
        if mi_plan == "Gratis" and u["Nombre"] != COMANDANTE_SUPREMO:
            st.error("RESTRICCIÓN: El Nivel BASE no tiene acceso a IA Generativa.")
        else:
            limite = 9999 if u["Nombre"] == COMANDANTE_SUPREMO else (3 if mi_plan == "Individual" else 1)
            if creados >= limite:
                st.error(f"CUOTA ALCANZADA ({creados}/{limite}). Elimina un escenario para crear otro.")
            else:
                idea_prompt = st.text_area(
                    "Describe el entorno táctico:",
                    placeholder="Ej: Negociación con un director de RRHH que quiere despedir a un empleado clave...",
                    height=110
                )
                if st.button("GENERAR ESCENARIO", use_container_width=True, type="primary"):
                    if idea_prompt and GROQ_API_KEY:
                        with st.spinner("Sintetizando escenario..."):
                            try:
                                client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                                res = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[
                                        {"role":"system","content":"Devuelve JSON: {'nombre_op':'OPERACION: [NOMBRE]','contexto':'...','perfil_sujeto':'...','objetivo':'Descripción clara y verificable del objetivo que el operador debe lograr.','prompt':'...'}"},
                                        {"role":"user","content":idea_prompt}
                                    ],
                                    response_format={"type":"json_object"}
                                ).choices[0].message.content
                                nuevo_esc = json.loads(res)
                                nuevo_esc["prompt"] += INSTRUCCION_ORTOGRAFIA
                                st.session_state.escenarios_custom[nuevo_esc["nombre_op"]] = {
                                    "contexto":      nuevo_esc["contexto"],
                                    "perfil_sujeto": nuevo_esc["perfil_sujeto"],
                                    "objetivo":      nuevo_esc["objetivo"],
                                    "prompt":        nuevo_esc["prompt"],
                                    "Creador":       empresa_actual
                                }
                                guardar_datos()
                                st.success(f"Protocolo '{nuevo_esc['nombre_op']}' creado.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fallo del motor IA: {e}")
                    elif not idea_prompt:
                        st.warning("Escribe los parámetros base.")
                    else:
                        st.error("API no configurada.")

    with col_der:
        st.markdown("<span class='lbl'>NIVELES DE ACCESO IA</span>", unsafe_allow_html=True)
        for nombre, precio, desc, color in [
            ("BASE",        "0€",      "Sin acceso a IA generativa",   "var(--text-lo)"),
            ("OPERADOR",    "29€/mes", "Hasta 3 escenarios propios",    "var(--blue)"),
            ("ESCUADRON",   "89€/mes", "Hasta 1 escenario compartido",  "var(--blue)"),
            ("COMANDANCIA", "199€/mes","Escenarios ilimitados",         "var(--amber)"),
        ]:
            es_actual = (
                (nombre == "BASE" and mi_plan == "Gratis") or
                (nombre == "OPERADOR" and mi_plan == "Individual") or
                (nombre == "ESCUADRON" and mi_plan == "Pro") or
                (nombre == "COMANDANCIA" and mi_plan == "Enterprise")
            )
            st.markdown(f"""
            <div style="background:{'var(--blue-dim)' if es_actual else 'var(--bg3)'};
                        border:1px solid {'var(--blue)' if es_actual else 'var(--border)'};
                        border-left:3px solid {color};
                        padding:14px 16px;border-radius:var(--r);margin-bottom:8px;">
              <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                <span style="font-family:var(--mono);font-size:0.62rem;color:var(--text-hi);">{nombre}</span>
                <span style="font-family:var(--mono);font-size:0.65rem;color:{color};font-weight:700;">{precio}</span>
              </div>
              <div style="font-family:var(--mono);font-size:0.52rem;color:var(--text-lo);">{desc}</div>
              {'<div style="font-family:var(--mono);font-size:0.5rem;color:var(--blue);margin-top:6px;">● PLAN ACTIVO</div>' if es_actual else ''}
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# PANTALLA: ADMIN OMEGA
# ═══════════════════════════════════════════
elif pantalla == "admin" and u["Nombre"] == COMANDANTE_SUPREMO:
    st.markdown("""<div class="section-hd">
      <div class="section-code">MOD-06</div>
      <div class="section-title">Consola Omega — Administración Global</div>
    </div>""", unsafe_allow_html=True)

    clientes_corp  = [e for e in st.session_state.empleados if e["Rol"] == "Empresa"]
    clientes_indiv = [e for e in st.session_state.empleados if e["Rol"] == "Individual"]
    total_enterprise = len([c for c in clientes_corp + clientes_indiv if c.get("Plan") == "Enterprise"])
    total_pro        = len([c for c in clientes_corp + clientes_indiv if c.get("Plan") == "Pro"])
    total_indiv      = len([c for c in clientes_corp + clientes_indiv if c.get("Plan") == "Individual"])
    mrr              = total_enterprise * 199 + total_pro * 89 + total_indiv * 29
    total_agentes    = len([e for e in st.session_state.empleados if e["Rol"] == "Agente"])

    cm1, cm2, cm3, cm4 = st.columns(4)
    cm1.markdown(f"""<div class="mc" style="border-left-color:var(--amber);">
      <div class="mc-lbl" style="color:var(--amber);">MRR ESTIMADO</div>
      <div class="mc-val">{mrr}€</div>
    </div>""", unsafe_allow_html=True)
    cm2.markdown(f"""<div class="mc"><div class="mc-lbl">CUENTAS DE PAGO</div>
      <div class="mc-val">{total_enterprise+total_pro+total_indiv}</div></div>""", unsafe_allow_html=True)
    cm3.markdown(f"""<div class="mc"><div class="mc-lbl">AGENTES</div>
      <div class="mc-val">{total_agentes}</div></div>""", unsafe_allow_html=True)
    cm4.markdown(f"""<div class="mc"><div class="mc-lbl">SESIONES TOTALES</div>
      <div class="mc-val">{len(st.session_state.historial_sesiones)}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    ca1, ca2 = st.columns(2, gap="large")

    with ca1:
        with st.expander("DIRECTORIO GLOBAL DE USUARIOS"):
            for i, usr in enumerate(st.session_state.empleados):
                if usr["Nombre"] != COMANDANTE_SUPREMO:
                    cu1, cu2 = st.columns([4, 1])
                    cu1.markdown(f"**{usr['Nombre']}** · {usr['Rol']} · {usr.get('Plan','—')} · {usr['Email']}")
                    if cu2.button("PURGAR", key=f"del_g_{usr['Nombre']}_{i}", type="secondary"):
                        st.session_state.empleados = [e for e in st.session_state.empleados if e["Nombre"] != usr["Nombre"]]
                        guardar_datos(); st.rerun()

        with st.expander("DIRECTORIO DE ESCENARIOS"):
            if not st.session_state.escenarios_custom:
                st.markdown("<span style='color:var(--text-lo);font-family:var(--mono);font-size:0.7rem;'>Sin escenarios personalizados.</span>", unsafe_allow_html=True)
            for n_esc, d_esc in st.session_state.escenarios_custom.items():
                ce1, ce2 = st.columns([4, 1])
                ce1.markdown(f"**{n_esc}** · Creador: {d_esc.get('Creador','—')}")
                if ce2.button("ELIMINAR", key=f"del_g_esc_{n_esc}", type="secondary"):
                    del st.session_state.escenarios_custom[n_esc]; guardar_datos(); st.rerun()

    with ca2:
        with st.expander("EMITIR CREDENCIAL DE CORTESÍA", expanded=True):
            with st.form("admin_create"):
                new_n    = st.text_input("ID / Entidad")
                new_em   = st.text_input("Correo")
                new_pw   = st.text_input("Contraseña", type="password")
                new_rol  = st.selectbox("Rol", ["Individual","Empresa"])
                new_plan = st.selectbox("Plan", ["Gratis","Individual","Pro","Enterprise"])
                expira   = st.checkbox("Licencia temporal (30 días)")
                if st.form_submit_button("GENERAR ACCESO", use_container_width=True):
                    if new_n and new_em and new_pw:
                        if any(e["Nombre"] == new_n for e in st.session_state.empleados):
                            st.warning("ID ya registrado.")
                        else:
                            nuevo_u = {"Nombre":new_n,"Email":new_em,"Rol":new_rol,"Plan":new_plan,
                                       "Empresa":new_n,"Password":new_pw,"2FA_Verificado":True}
                            if new_rol == "Empresa": nuevo_u["Departamento"] = "Administración"
                            if expira: nuevo_u["Expiracion"] = (datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d")
                            st.session_state.empleados.append(nuevo_u); guardar_datos()
                            st.success(f"Cuenta '{new_n}' creada."); st.rerun()
                    else: st.warning("Rellena todos los campos.")

        with st.expander("ACTIVAR / CAMBIAR PLAN", expanded=True):
            usuarios_no_admin = [e for e in st.session_state.empleados if e["Nombre"] != COMANDANTE_SUPREMO]
            if usuarios_no_admin:
                with st.form("admin_upgrade"):
                    opciones = [f"{e['Nombre']} [{e.get('Rol','?')} · {e.get('Plan','—')}]" for e in usuarios_no_admin]
                    sel_idx = st.selectbox("Usuario:", range(len(opciones)), format_func=lambda i: opciones[i])
                    nuevo_plan_upg = st.selectbox("Nuevo Plan:", ["Gratis","Individual","Pro","Enterprise"])
                    nueva_exp2     = st.checkbox("Añadir expiración (30 días)")
                    if st.form_submit_button("APLICAR PLAN", use_container_width=True):
                        usr_obj = usuarios_no_admin[sel_idx]
                        fe = (datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d") if nueva_exp2 else None
                        for e in st.session_state.empleados:
                            if e["Nombre"] == usr_obj["Nombre"]:
                                e["Plan"] = nuevo_plan_upg
                                if fe: e["Expiracion"] = fe
                                elif "Expiracion" in e: del e["Expiracion"]
                        guardar_datos(); st.success(f"Plan de '{usr_obj['Nombre']}' actualizado."); st.rerun()

    st.markdown("<br><span class='lbl'>ZONA DE PELIGRO</span>", unsafe_allow_html=True)
    if st.button("FORMATEAR PLATAFORMA COMPLETA", type="primary"):
        st.session_state.empleados          = []
        st.session_state.historial_sesiones = []
        st.session_state.escenarios_custom  = {}
        st.session_state.usuario_actual     = None
        guardar_datos(); st.rerun()

import streamlit as st
from cryptography.fernet import Fernet
from openai import OpenAI
import json
from datetime import datetime, timedelta
import pandas as pd
import re
import plotly.express as px
import plotly.graph_objects as go
import os
import smtplib
from email.mime.text import MIMEText
import random
from fpdf import FPDF
from supabase import create_client, Client
import base64

# ─────────────────────────────────────────
# CONFIGURACIÓN DE SUPERUSUARIO
# ─────────────────────────────────────────
COMANDANTE_SUPREMO = "CRYSIS"
LINKS_PAGO = {
    "OPERADOR":    "https://crysisanalitics.lemonsqueezy.com/checkout/buy/1dba647d-e120-4816-9ea0-a25492650825",
    "ELITE":       "https://crysisanalitics.lemonsqueezy.com/checkout/buy/PLACEHOLDER_ELITE",
    "ESCUADRON":   "https://crysisanalitics.lemonsqueezy.com/checkout/buy/d864d72e-5ff1-4bac-966d-eafc555c5bd2",
    "COMANDANCIA": "https://crysisanalitics.lemonsqueezy.com/checkout/buy/adfd50b4-b2e5-40fb-9ece-30717f8828ba",
}

PLANES_INFO = {
    "BASE":        {"precio": "0€",     "desc": "Individual · 1 op/mes · sin IA",        "ops": 1,     "escenarios": 0,     "agentes": 0,     "elite": False},
    "OPERADOR":    {"precio": "19€/mes","desc": "Individual · 10 ops/mes · 3 escenarios", "ops": 10,    "escenarios": 3,     "agentes": 0,     "elite": False},
    "ELITE":       {"precio": "49€/mes","desc": "Individual · ilimitado · IA sin límite", "ops": 99999, "escenarios": 99999, "agentes": 0,     "elite": True},
    "ESCUADRON":   {"precio": "89€/mes","desc": "Equipo · ilimitado · 15 agentes",        "ops": 99999, "escenarios": 99999, "agentes": 15,    "elite": True},
    "COMANDANCIA": {"precio": "199€/mes","desc": "Enterprise · ilimitado · ∞ agentes",   "ops": 99999, "escenarios": 99999, "agentes": 99999, "elite": True},
}

DIFICULTADES = {
    "RECRUIT":  {"nivel": 1, "color": "#00D4A0", "var": "--green",  "desc": "Sujeto cooperativo. Cede ante argumentos básicos.",
                 "instruccion": "Eres cooperativo, respondes con relativa facilidad, cedes ante argumentos razonables, tono neutro o incluso amigable. No opones resistencia fuerte."},
    "OPERATOR": {"nivel": 2, "color": "#4F8EF7", "var": "--blue",   "desc": "Sujeto resistente. Exige justificaciones, desconfía.",
                 "instruccion": "Eres moderadamente resistente. Exiges justificaciones claras, desconfías de las intenciones del interlocutor, pero puedes ceder si los argumentos son sólidos."},
    "VETERAN":  {"nivel": 3, "color": "#F0A500", "var": "--amber",  "desc": "Sujeto hostil. Agresivo, manipulador, raramente cede.",
                 "instruccion": "Eres hostil y agresivo. Usas tácticas de presión psicológica, manipulación emocional y rara vez cedes. Contradices argumentos y pones a prueba al interlocutor constantemente."},
    "NIGHTMARE":{"nivel": 4, "color": "#E8394A", "var": "--red",    "desc": "Casi impenetrable. Amenazas veladas, silencio, manipulación avanzada.",
                 "instruccion": "Eres extremadamente hostil e impenetrable. Usas silencios prolongados, amenazas veladas, manipulación psicológica avanzada y contradices absolutamente todo. Ceder es casi imposible. Solo capitulas ante una negociación perfecta y sostenida."},
}

@st.cache_resource
def init_supabase():
    url: str = st.secrets["SUPABASE_URL"].strip().rstrip("/")
    key: str = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_supabase()

# 🔐 MOTOR DE CIFRADO
def obtener_fernet():
    return Fernet(st.secrets["ENCRYPTION_KEY"])

def cifrar_memoria(datos_dict):
    f = obtener_fernet()
    datos_json = json.dumps(datos_dict)
    return f.encrypt(datos_json.encode()).decode()

def descifrar_memoria(texto_cifrado):
    f = obtener_fernet()
    try:
        decodificado = f.decrypt(texto_cifrado.encode()).decode()
        return json.loads(decodificado)
    except:
        return None

def cargar_datos():
    try:
        response = supabase.table("crysis_data").select("memoria").eq("id", "main").execute()
        if response.data:
            contenido = response.data[0]["memoria"]
            # Intentamos descifrar. Si falla (porque son datos viejos sin cifrar), cargamos normal.
            datos = descifrar_memoria(contenido)
            if datos is None: datos = contenido if isinstance(contenido, dict) else {"empleados": [], "historial_sesiones": [], "escenarios_custom": {}}
            
            if "escenarios_custom" not in datos: datos["escenarios_custom"] = {}
            datos["empleados"] = [e for e in datos.get("empleados", []) if "Rol" in e]
            return datos
    except Exception as e:
        st.error(f"Error al conectar con Base de Datos: {e}")
    return {"empleados": [], "historial_sesiones": [], "escenarios_custom": {}}

def guardar_datos():
    try:
        datos_actualizados = {
            "empleados": st.session_state.empleados,
            "historial_sesiones": st.session_state.historial_sesiones,
            "escenarios_custom": st.session_state.escenarios_custom
        }
        # Ciframos antes de enviar a Supabase
        memoria_cifrada = cifrar_memoria(datos_actualizados)
        supabase.table("crysis_data").update({"memoria": memoria_cifrada}).eq("id", "main").execute()
    except Exception as e:
        st.error(f"Fallo crítico al sincronizar: {e}")

def enviar_correo_2fa(destinatario, codigo):
    try:
        remitente = st.secrets["SMTP_EMAIL"]
        password  = st.secrets["SMTP_PASS"]
        msg = MIMEText(f"Tu código de autorización táctica para CRYSIS es: {codigo}\n\nSi no has solicitado este acceso, reporta una brecha de seguridad inmediatamente.")
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

def enviar_correo_reset(destinatario, nueva_pass):
    try:
        remitente = st.secrets["SMTP_EMAIL"]
        password  = st.secrets["SMTP_PASS"]
        msg = MIMEText(f"Tu nueva contraseña temporal para CRYSIS es: {nueva_pass}\n\nCámbiala en Ajustes de Cuenta tras acceder.")
        msg['Subject'] = 'CRYSIS | Recuperación de Contraseña'
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
    if not isinstance(texto, str): texto = str(texto)
    texto = texto.replace('**','').replace('*','-').replace('•','-').replace('✅','[V]').replace('❌','[X]')
    return texto.encode('latin-1','replace').decode('latin-1')

def generar_pdf_dossier(sesion):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial",'B',16); pdf.set_text_color(79,142,247)
    pdf.cell(0,10,"CRYSIS | INTELLIGENCE UNIT",ln=True,align='C')
    pdf.set_font("Arial",'B',11); pdf.set_text_color(239,68,68)
    pdf.cell(0,8,"DOSSIER OPERACIONAL CLASIFICADO",ln=True,align='C'); pdf.ln(5)
    pdf.set_font("Arial",'B',10); pdf.set_text_color(0,0,0)
    pdf.cell(45,8,"OPERADOR:",border=1); pdf.set_font("Arial",'',10); pdf.cell(0,8,sanitizar_texto(sesion.get("Agente","N/A").upper()),border=1,ln=True)
    pdf.set_font("Arial",'B',10); pdf.cell(45,8,"FECHA:",border=1); pdf.set_font("Arial",'',10); pdf.cell(0,8,sanitizar_texto(sesion.get("Fecha","N/A")),border=1,ln=True)
    pdf.set_font("Arial",'B',10); pdf.cell(45,8,"PROTOCOLO:",border=1); pdf.set_font("Arial",'',10); pdf.cell(0,8,sanitizar_texto(sesion.get("Escenario","N/A")),border=1,ln=True)
    pdf.set_font("Arial",'B',10); pdf.cell(45,8,"DIFICULTAD:",border=1); pdf.set_font("Arial",'',10); pdf.cell(0,8,sanitizar_texto(sesion.get("Dificultad","N/A")),border=1,ln=True)
    pdf.set_font("Arial",'B',10); pdf.cell(45,8,"EVALUACION FINAL:",border=1); pdf.set_font("Arial",'B',10); pdf.cell(0,8,f"{sesion.get('Nota',0)}/100",border=1,ln=True); pdf.ln(10)
    pdf.set_text_color(0,0,0); pdf.set_font("Arial",'B',12)
    pdf.cell(0,8,"1. INFORME DE EVALUACION TACTICA",ln=True); pdf.set_font("Arial",'',10)
    pdf.multi_cell(0,6,sanitizar_texto(sesion.get("Evaluacion",""))); pdf.ln(5)
    if "Transcripcion" in sesion:
        pdf.set_font("Arial",'B',12); pdf.cell(0,8,"2. REGISTRO DE COMUNICACIONES",ln=True); pdf.ln(2)
        for msg in sesion["Transcripcion"]:
            ag = "OPERADOR" if msg["role"] == "user" else "OBJETIVO"
            if msg["role"] == "user": pdf.set_text_color(79,142,247)
            else: pdf.set_text_color(239,68,68)
            pdf.set_font("Arial",'B',10); pdf.cell(0,6,f"{ag}:",ln=True)
            pdf.set_text_color(50,50,50); pdf.set_font("Arial",'',10)
            pdf.multi_cell(0,6,sanitizar_texto(msg["content"])); pdf.ln(2)
    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else out

# ─────────────────────────────────────────
# CONFIG Y CSS GLOBAL
# ─────────────────────────────────────────
st.set_page_config(page_title="CRYSIS | Intelligence Unit", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Syne:wght@400;600;700;800&display=swap');

:root {
  --bg:       #060810;
  --bg2:      #0B0E1A;
  --bg3:      #101525;
  --border:   #18213A;
  --border2:  #243050;
  --blue:     #4F8EF7;
  --blue-dim: rgba(79,142,247,0.12);
  --green:    #00D4A0;
  --red:      #E8394A;
  --amber:    #F0A500;
  --text:     #B8C4DC;
  --text-hi:  #E2EAF8;
  --text-lo:  #3A4A6A;
  --mono:     'Share Tech Mono', monospace;
  --sans:     'Syne', sans-serif;
}

html, body, [class*="css"], .stApp {
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: var(--sans) !important;
}
header[data-testid="stHeader"] { background: var(--bg) !important; border-bottom: 1px solid var(--border); }
.stDeployButton, #MainMenu, footer { display: none !important; }

.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px);
  pointer-events: none;
  z-index: 9999;
}

/* ── BRAND ── */
.brand-wordmark {
  font-family: var(--mono);
  font-size: 4rem;
  letter-spacing: 0.3em;
  color: var(--text-hi);
  line-height: 1;
  margin-bottom: 12px;
  text-shadow: 0 0 60px rgba(79,142,247,0.2);
}
.brand-sub { font-family: var(--mono); font-size: 0.55rem; letter-spacing: 0.4em; color: var(--blue); margin-bottom: 40px; }
.brand-line { width: 40px; height: 2px; background: var(--blue); margin-bottom: 24px; }
.brand-desc { font-size: 0.78rem; color: var(--text-lo); line-height: 1.7; letter-spacing: 0.02em; font-family: var(--mono); }

/* ── TOPBAR ── */
.topbar { display: flex; align-items: center; justify-content: space-between; padding: 16px 0 12px 0; border-bottom: 1px solid var(--border); margin-bottom: 0; }
.topbar-brand { font-family: var(--mono); font-size: 1.1rem; letter-spacing: 0.3em; color: var(--text-hi); }
.topbar-meta  { font-family: var(--mono); font-size: 0.55rem; letter-spacing: 0.2em; color: var(--text-lo); margin-top: 3px; }

/* ── CABECERA DEL MENÚ ── */
.dashboard-header { margin-bottom: 44px; }
.dashboard-greeting { font-size: 2rem; font-weight: 700; color: var(--text-hi); margin-bottom: 2px; }
.dashboard-meta { font-family: var(--mono); font-size: 0.6rem; letter-spacing: 0.15em; color: var(--text-lo); margin-bottom: 16px; }
.dashboard-status {
    display: flex; gap: 32px; font-family: var(--mono); font-size: 0.5rem;
    letter-spacing: 0.15em; color: var(--blue); text-transform: uppercase;
    border-top: 1px solid var(--border); padding-top: 14px;
}

/* ── TARJETAS DEL MENÚ (ESTILO B + D SIN EMOJIS) ── */
.card-wrapper {
    position: relative;
    margin-bottom: 20px;
}
.dashboard-card {
    position: relative;
    display: flex;
    align-items: center;
    gap: 20px;
    background: linear-gradient(135deg, #0B0E1A 0%, #0F1425 100%);
    border: 1px solid var(--border);
    border-radius: 2px;
    padding: 24px;
    text-decoration: none !important;
    transition: all 0.2s ease;
    height: 140px;
    cursor: pointer;
    overflow: hidden;
}
.dashboard-card:hover {
    border-color: var(--border2);
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    transform: translateY(-3px);
}
/* Círculo de color (indicador geométrico) */
.dashboard-card::before {
    content: '';
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--border);
    transition: background 0.2s ease;
    flex-shrink: 0;
}
.dashboard-card:hover::before {
    background: var(--blue);
}
.dashboard-card-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.dashboard-card-title {
    font-family: var(--mono);
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--text-hi);
    text-transform: uppercase;
    margin-bottom: 8px;
}
.dashboard-card-metric {
    font-family: var(--mono);
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--blue);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* Botón invisible encima de la tarjeta */
.card-wrapper button {
    position: absolute !important;
    inset: 0 !important;
    width: 100% !important;
    height: 100% !important;
    opacity: 0 !important;
    z-index: 10 !important;
    cursor: pointer !important;
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
}
/* Oculta el texto del botón */
.card-wrapper button p, .card-wrapper button span {
    display: none !important;
}

/* ── SECTION HEADERS ── */
.section-header { padding: 28px 0 24px 0; border-bottom: 1px solid var(--border); margin-bottom: 32px; display: flex; align-items: flex-end; justify-content: space-between; }
.section-title { font-size: 1.4rem; font-weight: 700; color: var(--text-hi); letter-spacing: 0.02em; }
.section-code  { font-family: var(--mono); font-size: 0.52rem; letter-spacing: 0.3em; color: var(--text-lo); margin-bottom: 4px; }

/* ── METRICS ── */
.metric-card { background: var(--bg2); border: 1px solid var(--border); border-radius: 2px; padding: 24px; position: relative; overflow: hidden; }
.metric-card::before { content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: var(--blue); }
.metric-label { font-family: var(--mono); font-size: 0.52rem; letter-spacing: 0.22em; color: var(--blue); margin-bottom: 10px; }
.metric-value { font-family: var(--mono); font-size: 2rem; font-weight: 700; color: var(--text-hi); line-height: 1; }

/* ── BRIEFING / STATUS ── */
.briefing-box { background: var(--bg2); border: 1px solid var(--border); border-left: 3px solid var(--blue); padding: 20px 24px; border-radius: 2px; margin-bottom: 20px; }
.briefing-box h4 { font-family: var(--mono); font-size: 0.58rem; letter-spacing: 0.2em; color: var(--blue); margin-bottom: 12px; }
.section-label { font-family: var(--mono); font-size: 0.55rem; letter-spacing: 0.25em; color: var(--blue); margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.status-bar { background: var(--bg2); border: 1px solid var(--border); border-left: 3px solid var(--green); padding: 10px 18px; border-radius: 2px; font-family: var(--mono); font-size: 0.62rem; letter-spacing: 0.12em; color: var(--green); margin-bottom: 20px; }

/* ── DIFFICULTY CARDS ── */
.diff-card { border: 2px solid var(--border); border-radius: 2px; padding: 14px 16px; cursor: pointer; transition: all 0.2s; background: var(--bg3); text-align: center; }
.diff-card:hover { transform: translateY(-2px); }
.diff-card.selected { background: rgba(79,142,247,0.08); }
.diff-name  { font-family: var(--mono); font-size: 0.7rem; letter-spacing: 0.18em; font-weight: 700; }
.diff-desc  { font-family: var(--mono); font-size: 0.52rem; color: var(--text-lo); margin-top: 6px; line-height: 1.5; }

/* ── INPUTS ── */
.stTextInput input, .stSelectbox > div > div, .stTextArea textarea {
  background: var(--bg3) !important; border: 1px solid var(--border2) !important;
  color: var(--text) !important; border-radius: 2px !important; font-family: var(--sans) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--blue) !important; box-shadow: 0 0 0 2px rgba(79,142,247,0.08) !important; }
.stTextInput label, .stTextArea label, .stSelectbox label { color: var(--text-lo) !important; font-family: var(--mono) !important; font-size: 0.62rem !important; letter-spacing: 0.15em !important; }

/* ── BUTTONS ── */
.stButton > button {
  background: var(--blue) !important; color: var(--bg) !important;
  font-family: var(--mono) !important; font-size: 0.65rem !important; font-weight: 700 !important;
  letter-spacing: 0.2em !important; border: none !important; border-radius: 2px !important;
  padding: 12px 28px !important; transition: all 0.2s !important;
}
.stButton > button:hover { background: #3A7AE4 !important; box-shadow: 0 0 24px rgba(79,142,247,0.25) !important; transform: translateY(-1px); }
[data-testid="stButton"] button[disabled] { background: var(--border) !important; color: var(--text-lo) !important; box-shadow: none !important; }
button[kind="secondary"] { background: transparent !important; border: 1px solid var(--border2) !important; color: var(--text) !important; }
button[kind="secondary"]:hover { border-color: var(--blue) !important; color: var(--text-hi) !important; background: var(--blue-dim) !important; }

/* ── LOGIN TABS ── */
.login-tab-active { background: var(--blue) !important; color: var(--bg) !important; border: none !important; }
.login-tab-inactive { background: transparent !important; color: var(--text-lo) !important; border: 1px solid var(--border) !important; }

/* ── AUTH TIERS ── */
.auth-tier { background: var(--bg3); border: 1px solid var(--border); border-left: 3px solid var(--border2); padding: 20px; border-radius: 2px; transition: border-color 0.2s; margin-bottom: 8px; }
.auth-tier:hover { border-left-color: var(--blue); }
.auth-tier.elite { border-left-color: var(--amber); }
.tier-spec { font-size: 0.75rem; color: #8B9CC8; margin-bottom: 6px; display: flex; align-items: center; }
.tier-spec::before { content: '—'; margin-right: 8px; color: var(--blue); font-size: 0.6rem; }

/* ── ALERT/INFO BOXES ── */
.alert-box { background: #0D1020; border: 1px solid var(--border); border-left: 3px solid var(--blue); padding: 14px 18px; border-radius: 2px; margin-bottom: 16px; font-family: var(--mono); font-size: 0.62rem; color: var(--text-lo); line-height: 1.6; }
.alert-box.warning { border-left-color: var(--amber); }
.alert-box.error   { border-left-color: var(--red); background: #120808; }

/* ── FORGOT PASSWORD ── */
.link-btn { background: none; border: none; color: var(--text-lo); font-family: var(--mono); font-size: 0.58rem; letter-spacing: 0.1em; cursor: pointer; padding: 0; text-decoration: underline; transition: color 0.15s; }
.link-btn:hover { color: var(--blue); }

/* ── PLAN SELECTOR ── */
.plan-card { border: 1px solid var(--border); background: var(--bg3); border-radius: 2px; padding: 12px 14px; margin-bottom: 4px; cursor: pointer; transition: all 0.15s; }
.plan-card:hover { border-color: var(--border2); }
.plan-card.selected-plan { border-color: var(--blue); background: rgba(79,142,247,0.08); }
.plan-card.selected-plan.elite-plan { border-color: var(--amber); background: rgba(240,165,0,0.08); }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--blue); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# DATOS BASE
# ─────────────────────────────────────────
INSTRUCCION_ORTOGRAFIA = " Escribe en español correcto. Nunca uses acotaciones entre paréntesis. Solo diálogo."
CONTEXTOS_MISION = {
    "OPERACION: FRONTERA":   {"contexto": "Tensiones militares en el paralelo 38.", "perfil_sujeto": "Ministro Volkov.", "objetivo": "Evitar la escalada bélica.", "prompt": "Eres el Ministro de Defensa de Krasnovia. Hostil y burocrático. Solo diálogo directo." + INSTRUCCION_ORTOGRAFIA},
    "OPERACION: BLACKOUT":   {"contexto": "Ataque masivo al sistema eléctrico nacional. Rescate exigido.", "perfil_sujeto": "'Shadow'. Hacker mercenario. Frío y calculador.", "objetivo": "Ganar tiempo para localizar el origen del ataque.", "prompt": "Eres Shadow, hacker de elite acorralado. Solo texto directo. Sin emociones." + INSTRUCCION_ORTOGRAFIA},
    "OPERACION: EXTRACCION": {"contexto": "Robo a banco fallido. 3 civiles retenidos.", "perfil_sujeto": "Sujeto inestable, bajo presión extrema.", "objetivo": "Asegurar la liberación de rehenes.", "prompt": "Eres un secuestrador acorralado. Gritas, estás nervioso. Solo diálogo crudo." + INSTRUCCION_ORTOGRAFIA},
}
PLOTLY_THEME = dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family='Syne', color='#8B9CC8', size=12), margin=dict(l=16,r=16,t=40,b=16))
AXIS_STYLE   = dict(gridcolor='#1A2035', zeroline=False, color='#4A5568', linecolor='#1A2035')

# ─────────────────────────────────────────
# ESTADOS
# ─────────────────────────────────────────
datos_guardados = cargar_datos()
if "empleados"          not in st.session_state: st.session_state.empleados          = datos_guardados["empleados"]
if "historial_sesiones" not in st.session_state: st.session_state.historial_sesiones = datos_guardados["historial_sesiones"]
if "escenarios_custom"  not in st.session_state: st.session_state.escenarios_custom  = datos_guardados.get("escenarios_custom", {})
if "mensajes"           not in st.session_state: st.session_state.mensajes            = []
if "evaluacion_actual"  not in st.session_state: st.session_state.evaluacion_actual  = None
if "mision_iniciada"    not in st.session_state: st.session_state.mision_iniciada    = False
if "tarjeta_objetivo"   not in st.session_state: st.session_state.tarjeta_objetivo   = None
if "usuario_actual"     not in st.session_state: st.session_state.usuario_actual     = None
if "login_step"         not in st.session_state: st.session_state.login_step         = 1
if "pantalla_actual"    not in st.session_state: st.session_state.pantalla_actual    = "menu"
if "login_modo"         not in st.session_state: st.session_state.login_modo         = "acceso"
if "dificultad_actual"  not in st.session_state: st.session_state.dificultad_actual  = "OPERATOR"
if "login_subpantalla"  not in st.session_state: st.session_state.login_subpantalla  = "main"

try:    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except: GROQ_API_KEY = None


# ─────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────
token_invitacion = st.query_params.get("invite", None)
empresa_invitada = None
if token_invitacion:
    try: empresa_invitada = base64.urlsafe_b64decode(token_invitacion.encode()).decode()
    except: pass

if st.session_state.usuario_actual is None:

    # ── FLUJO INVITACIÓN ──
    if empresa_invitada:
        st.markdown(f"""
        <div style="text-align:center; padding: 60px 0 30px 0;">
            <div class="brand-wordmark">CRYSIS</div>
            <div class="brand-sub">ALISTAMIENTO ACTIVO · {empresa_invitada.upper()}</div>
        </div>
        """, unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            empresa_obj = next((e for e in st.session_state.empleados if e["Rol"] == "Empresa" and e["Nombre"] == empresa_invitada), None)
            if empresa_obj:
                # El comandante supremo nunca tiene límite de agentes
                if empresa_obj["Nombre"] != COMANDANTE_SUPREMO:
                    agentes_actuales = len([e for e in st.session_state.empleados if e.get("Empresa") == empresa_invitada and e.get("Rol") == "Agente"])
                    plan_emp = empresa_obj.get("Plan", "BASE")
                    limite_agentes = PLANES_INFO.get(plan_emp, {}).get("agentes", 0)
                    if agentes_actuales >= limite_agentes:
                        st.error("ACCESO DENEGADO: Esta unidad no posee licencia corporativa activa o ha alcanzado su límite de efectivos.")
                        st.stop()
            with st.form("reg_agente"):
                st.markdown("<div class='section-label'>SOLICITUD DE CREDENCIALES DE AGENTE</div>", unsafe_allow_html=True)
                n     = st.text_input("Identificador de Agente (ID)")
                email = st.text_input("Correo Corporativo")
                d     = st.text_input("Unidad / Departamento")
                p     = st.text_input("Establecer Clave de Acceso", type="password")
                if st.form_submit_button("REGISTRAR CREDENCIALES", use_container_width=True):
                    if n and p and email:
                        if any(e["Nombre"] == n and e.get("Empresa") == empresa_invitada for e in st.session_state.empleados):
                            st.warning("Este ID ya está registrado en esta corporación.")
                        elif any(e["Nombre"] == n and e.get("Password") == p for e in st.session_state.empleados):
                            st.warning("ID ya en uso. Utiliza una contraseña diferente.")
                        else:
                            nuevo_agente = {"Nombre": n, "Email": email, "Departamento": d, "Rol": "Agente", "Empresa": empresa_invitada, "Password": p, "2FA_Verificado": True}
                            st.session_state.empleados.append(nuevo_agente); guardar_datos()
                            st.session_state.registro_completado = True
                            st.query_params.clear(); st.rerun()
        st.stop()

    if st.session_state.get("registro_completado"):
        st.success("Acreditación procesada. Identifícate en el portal de acceso.")
        st.session_state.registro_completado = False

    # ── LAYOUT PRINCIPAL LOGIN ──
    col_brand, col_form = st.columns([1, 1])

    with col_brand:
        st.markdown("""
        <div style="padding: 80px 40px 80px 20px; min-height: 80vh; display: flex; flex-direction: column; justify-content: space-between; border-right: 1px solid #18213A;">
            <div>
                <div class="brand-wordmark">CRYSIS</div>
                <div class="brand-sub">INTELLIGENCE UNIT</div>
                <div class="brand-line"></div>
                <div class="brand-desc">
                    Plataforma de simulación táctica avanzada para el entrenamiento en negociación,
                    desescalada y comunicación bajo presión extrema.
                </div>
            </div>
            <div>
                <div style="font-family:var(--mono); font-size:0.5rem; letter-spacing:0.3em; color:#18213A; margin-bottom:8px;">ESTADO DEL SISTEMA</div>
                <div style="font-family:var(--mono); font-size:0.58rem; color:#00D4A0; letter-spacing:0.15em;">● OPERATIVO · ACCESO SEGURO</div>
                <div style="margin-top:16px; font-family:var(--mono); font-size:0.48rem; letter-spacing:0.25em; color:#18213A;">v3.1.0 · CLASIFICADO</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_form:
        st.markdown("<div style='padding: 60px 20px 60px 40px;'>", unsafe_allow_html=True)

        if st.session_state.login_subpantalla == "forgot":
            st.markdown("<div class='section-label'>RECUPERACION DE ACCESO</div>", unsafe_allow_html=True)
            st.markdown("""
            <div class="alert-box">
                Introduce tu ID de operador y el correo registrado. Si coinciden, recibirás una contraseña temporal por correo.
            </div>
            """, unsafe_allow_html=True)
            with st.form("forgot_form"):
                r_id    = st.text_input("ID Operativo")
                r_email = st.text_input("Correo Registrado")
                col_f1, col_f2 = st.columns(2)
                enviar = col_f1.form_submit_button("ENVIAR CLAVE TEMPORAL", use_container_width=True)
                volver = col_f2.form_submit_button("VOLVER", use_container_width=True)
                if enviar:
                    agente_r = next((e for e in st.session_state.empleados
                                     if e["Nombre"] == r_id and e.get("Email","").lower() == r_email.lower()), None)
                    if agente_r:
                        nueva_pass = str(random.randint(100000, 999999))
                        ok = enviar_correo_reset(r_email, nueva_pass)
                        if ok:
                            for e in st.session_state.empleados:
                                if e["Nombre"] == r_id:
                                    e["Password"] = nueva_pass
                            guardar_datos()
                            st.success(f"Clave temporal enviada a {r_email}. Cámbiala tras acceder.")
                        else:
                            st.error("Error al enviar el correo. Contacta con soporte.")
                    else:
                        st.error("No se encontró ninguna cuenta con ese ID y correo.")
                if volver:
                    st.session_state.login_subpantalla = "main"; st.rerun()

        else:
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                if st.button("ACCESO", key="modo_acceso", use_container_width=True,
                             type="primary" if st.session_state.login_modo == "acceso" else "secondary"):
                    st.session_state.login_modo = "acceso"; st.rerun()
            with col_t2:
                if st.button("REGISTRO", key="modo_registro", use_container_width=True,
                             type="primary" if st.session_state.login_modo == "registro" else "secondary"):
                    st.session_state.login_modo = "registro"; st.rerun()

            st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)

            if st.session_state.login_modo == "acceso":
                if st.session_state.login_step == 1:
                    with st.form("login_form"):
                        st.markdown("<div class='section-label'>IDENTIFICACIÓN DE OPERADOR</div>", unsafe_allow_html=True)
                        u_id   = st.text_input("ID Operativo")
                        u_pass = st.text_input("Clave de Seguridad", type="password")
                        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                        submitted = st.form_submit_button("INICIAR SESIÓN SEGURA", use_container_width=True)
                        if submitted:
                            agente = next((e for e in st.session_state.empleados if e["Nombre"] == u_id and e.get("Password") == u_pass), None)
                            if agente:
                                expiro = False
                                if "Expiracion" in agente:
                                    fecha_exp = datetime.strptime(agente["Expiracion"], "%Y-%m-%d")
                                    if datetime.now() > fecha_exp: expiro = True
                                if expiro:
                                    st.error(f"ACCESO DENEGADO: Licencia expirada el {agente['Expiracion']}.")
                                else:
                                    if agente.get("2FA_Verificado", False) == True or agente["Nombre"] == COMANDANTE_SUPREMO:
                                        st.session_state.usuario_actual = agente; st.session_state.pantalla_actual = "menu"; st.rerun()
                                    else:
                                        st.session_state["2fa_code"]   = str(random.randint(100000, 999999))
                                        st.session_state["2fa_agente"] = agente
                                        st.session_state.login_step = 2; st.rerun()
                            else:
                                st.error("ID o contraseña incorrectos. Verifica tus credenciales.")

                    st.markdown("<div style='margin-top:12px; text-align:right;'>", unsafe_allow_html=True)
                    if st.button("¿Olvidaste tu contraseña?", key="btn_forgot"):
                        st.session_state.login_subpantalla = "forgot"; st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

                elif st.session_state.login_step == 2:
                    correo_dest = st.session_state["2fa_agente"].get("Email", "Desconocido")
                    if "correo_enviado" not in st.session_state:
                        exito = enviar_correo_2fa(correo_dest, st.session_state["2fa_code"])
                        if exito: st.success(f"Código enviado a: {correo_dest}")
                        else:     st.error("Fallo en el sistema de correo seguro.")
                        st.session_state["correo_enviado"] = True
                    with st.form("2fa_form"):
                        st.markdown("<div class='section-label'>VERIFICACION DE DISPOSITIVO</div>", unsafe_allow_html=True)
                        st.markdown("""<div class="alert-box">Autenticación de dos factores requerida la primera vez. Revisa tu correo.</div>""", unsafe_allow_html=True)
                        u_code = st.text_input("Código de 6 dígitos")
                        colA, colB = st.columns(2)
                        if colA.form_submit_button("VERIFICAR", use_container_width=True):
                            if u_code == st.session_state["2fa_code"]:
                                st.session_state["2fa_agente"]["2FA_Verificado"] = True; guardar_datos()
                                st.session_state.usuario_actual = st.session_state["2fa_agente"]
                                st.session_state.pantalla_actual = "menu"
                                st.session_state.login_step = 1; del st.session_state["correo_enviado"]; st.rerun()
                            else: st.error("Código incorrecto.")
                        if colB.form_submit_button("CANCELAR", use_container_width=True):
                            st.session_state.login_step = 1; del st.session_state["correo_enviado"]; st.rerun()

            else:
                if st.session_state.get("mostrar_pago"):
                    info_pago = st.session_state.mostrar_pago
                    st.markdown(f"""
                    <div style="background:var(--bg3); border:1px solid var(--amber); border-left:3px solid var(--amber); padding:20px; border-radius:2px; margin-bottom:16px;">
                        <div style="font-family:var(--mono); font-size:0.58rem; letter-spacing:0.2em; color:var(--amber); margin-bottom:10px;">ACTIVACION DE PLAN PENDIENTE</div>
                        <p style="color:var(--text); font-size:0.82rem; margin-bottom:14px;">Cuenta <b style='color:var(--text-hi)'>{info_pago['id']}</b> creada. Tras el pago, tu plan se activará en máximo 24h.</p>
                        <a href="{info_pago['link']}" target="_blank" style="display:inline-block; background:var(--amber); color:#060810; font-family:var(--mono); font-weight:700; font-size:0.65rem; letter-spacing:0.1em; padding:10px 20px; border-radius:2px; text-decoration:none;">IR AL PAGO — {info_pago['plan']}</a>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("ENTRAR CON NIVEL BASE", use_container_width=True):
                        st.session_state.usuario_actual = info_pago["usuario"]
                        st.session_state.pantalla_actual = "menu"
                        del st.session_state.mostrar_pago; st.rerun()
                else:
                    st.markdown("<div class='section-label'>SELECCIONAR NIVEL DE ACCESO</div>", unsafe_allow_html=True)

                    if "plan_sel_reg" not in st.session_state: st.session_state.plan_sel_reg = "BASE"

                    planes_registro = [
                        ("BASE",        "0€",     "1 op/mes · sin IA",           False),
                        ("OPERADOR",    "19€/mes", "10 ops/mes · 3 escenarios",   False),
                        ("ELITE",       "49€/mes", "Ilimitado · IA sin límite",   True),
                        ("ESCUADRON",   "89€/mes", "Equipo · 15 agentes",         True),
                        ("COMANDANCIA", "199€/mes","Enterprise · agentes ∞",      True),
                    ]

                    col1, col2 = st.columns(2)
                    for i, (nombre, precio, desc, elite) in enumerate(planes_registro):
                        col = col1 if i % 2 == 0 else col2
                        with col:
                            is_sel     = st.session_state.plan_sel_reg == nombre
                            border_col = "#F0A500" if elite and is_sel else ("#4F8EF7" if is_sel else "#18213A")
                            bg_col     = "rgba(240,165,0,0.08)" if elite and is_sel else ("rgba(79,142,247,0.1)" if is_sel else "#101525")
                            check      = "✓ " if is_sel else ""
                            st.markdown(f"""
                            <div style="border:1px solid {border_col}; background:{bg_col}; padding:10px 14px; border-radius:2px; margin-bottom:4px;">
                                <div style="font-family:var(--mono); font-size:0.6rem; letter-spacing:0.15em; color:var(--text-hi);">{check}{nombre}</div>
                                <div style="font-size:0.85rem; color:{'#F0A500' if elite else '#4F8EF7'}; font-weight:700; margin-top:3px;">{precio}</div>
                                <div style="font-family:var(--mono); font-size:0.5rem; color:var(--text-lo); margin-top:3px;">{desc}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button(f"Seleccionar", key=f"plan_reg_{nombre}", use_container_width=True):
                                st.session_state.plan_sel_reg = nombre; st.rerun()

                    plan_sel       = st.session_state.plan_sel_reg
                    es_corporativo = plan_sel in ["ESCUADRON", "COMANDANCIA"]
                    es_pago        = plan_sel != "BASE"

                    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
                    with st.form("registro_form"):
                        st.markdown("<div class='section-label'>DATOS DE ACCESO</div>", unsafe_allow_html=True)
                        lbl_id = "Nombre de la Entidad / Empresa" if es_corporativo else "Alias / ID Personal"
                        n      = st.text_input(lbl_id)
                        email  = st.text_input("Correo de Contacto")
                        p      = st.text_input("Contraseña", type="password")
                        if es_corporativo:
                            st.markdown("""<div class="alert-box">Las cuentas corporativas pueden añadir agentes mediante enlace de invitación.</div>""", unsafe_allow_html=True)
                        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
                        acepta_tyc = st.checkbox(
                            "He leído y acepto los [Términos y Condiciones](/terminos) y la [Política de Privacidad](/privacidad)",
                            key="check_tyc"
                        )
                        acepta_rgpd = st.checkbox(
                            "Consiento el tratamiento de mis datos personales conforme al RGPD (UE) 2016/679",
                            key="check_rgpd"
                        )
                        acepta_comms = st.checkbox(
                            "Acepto recibir comunicaciones comerciales (opcional)",
                            key="check_comms"
                        )
                        lbl_btn = "CREAR CUENTA E IR AL PAGO" if es_pago else "CREAR CUENTA Y ENTRAR"
                        if st.form_submit_button(lbl_btn, use_container_width=True):
                            if not acepta_tyc or not acepta_rgpd:
                                st.error("Debes aceptar los Términos y la Política de Privacidad para continuar.")
                            elif n and p and email:
                                empresa_destino = n if es_corporativo else "Independiente"
                                if any(e["Nombre"] == n and e.get("Empresa", "Independiente") == empresa_destino for e in st.session_state.empleados):
                                    st.warning("Ya existe una cuenta con ese identificador.")
                                else:
                                    if es_corporativo:
                                        nuevo_usuario = {"Nombre": n, "Email": email, "Departamento": "Administración", "Rol": "Empresa", "Plan": "BASE", "Empresa": n, "Password": p, "2FA_Verificado": True}
                                    else:
                                        nuevo_usuario = {"Nombre": n, "Email": email, "Rol": "Individual", "Plan": "BASE", "Empresa": n, "Password": p, "2FA_Verificado": True}
                                    st.session_state.empleados.append(nuevo_usuario); guardar_datos()
                                    if es_pago:
                                        link_pago   = LINKS_PAGO.get(plan_sel, "#")
                                        nombre_plan = f"{plan_sel} ({PLANES_INFO[plan_sel]['precio']})"
                                        st.session_state.mostrar_pago = {"id": n, "link": link_pago, "plan": nombre_plan, "usuario": nuevo_usuario}
                                        st.rerun()
                                    else:
                                        st.session_state.usuario_actual = nuevo_usuario
                                        st.session_state.pantalla_actual = "menu"; st.rerun()
                            else:
                                st.warning("Rellena todos los campos para continuar.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()   # fin del login

# ═══════════════════════════════════════════
# MANEJADOR DE NAVEGACIÓN POR TARJETAS (COLÓCALO AQUÍ)
# ═══════════════════════════════════════════
menu_destino = st.query_params.get("menu", None)
if menu_destino and st.session_state.usuario_actual is not None:
    st.session_state.pantalla_actual = menu_destino
    st.query_params.clear()
    st.rerun()

# ─────────────────────────────────────────
# RESOLUCIÓN DE PERMISOS (BLINDAJE DE PRIVACIDAD)
# ─────────────────────────────────────────
u = st.session_state.usuario_actual

if u["Nombre"] == COMANDANTE_SUPREMO:
    es_empresa     = True
    mi_plan        = "COMANDANCIA"
    empresa_actual = u["Nombre"]
    # 🛡️ PRIVACIDAD RADICAL: El Admin NO ve expedientes de empresas. Solo los suyos de prueba.
    historial_visible     = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]
    agentes_de_mi_empresa = [u["Nombre"]]
else:
    es_empresa     = u.get("Rol") == "Empresa"
    empresa_actual = u.get("Empresa", u["Nombre"])
    if u.get("Rol") == "Agente":
        empresa_obj = next((e for e in st.session_state.empleados if e["Rol"] == "Empresa" and e["Nombre"] == empresa_actual), None)
        mi_plan = empresa_obj.get("Plan", "ESCUADRON") if empresa_obj else "ESCUADRON"
    else:
        mi_plan = u.get("Plan", "BASE")

# Normalizar planes legacy (Líneas 725-726 de tu código original)
_legacy = {"Gratis": "BASE", "Individual": "OPERADOR", "Pro": "ESCUADRON", "Enterprise": "COMANDANCIA"}
mi_plan = _legacy.get(mi_plan, mi_plan)

# Límites de cuota (Línea 728 de tu código original)
ops_limite      = PLANES_INFO.get(mi_plan, {}).get("ops", 1)
escenarios_lim  = PLANES_INFO.get(mi_plan, {}).get("escenarios", 0)
agentes_lim     = PLANES_INFO.get(mi_plan, {}).get("agentes", 0)

# 🛡️ LÓGICA DE VISIBILIDAD PARA CLIENTES Y AGENTES
if u["Nombre"] != COMANDANTE_SUPREMO:
    if es_empresa:
        agentes_de_mi_empresa = [e["Nombre"] for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"]
        # La empresa ve a sus agentes y SOLO misiones OFICIALES (Corporativas)
        historial_visible = [s for s in st.session_state.historial_sesiones if s["Agente"] in agentes_de_mi_empresa and s.get("Tipo_Mision") == "Corporativa"]
    else:
        # El agente o cuenta individual solo ve sus propias misiones
        historial_visible = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]
        agentes_de_mi_empresa = [u["Nombre"]]

# Carga de escenarios disponibles
mis_escenarios = {k: v for k, v in st.session_state.escenarios_custom.items() 
                  if v.get("Creador") == empresa_actual or u["Nombre"] == COMANDANTE_SUPREMO}
TODAS_LAS_MISIONES = {**CONTEXTOS_MISION, **mis_escenarios}

# ─────────────────────────────────────────
# TOPBAR (oculta en el menú)
# ─────────────────────────────────────────
if st.session_state.pantalla_actual != "menu":
    rol_label = ("OMNISCIENCIA GLOBAL" if u["Nombre"] == COMANDANTE_SUPREMO
                 else (f"SUPERVISION [{mi_plan}]" if es_empresa
                       else f"OPERADOR · {empresa_actual.upper()} [{mi_plan}]"))
    col_top1, col_top2 = st.columns([8, 1])
    with col_top1:
        pantalla = st.session_state.pantalla_actual
        nombres_pantalla = {"estadisticas": "ESTADÍSTICAS", "personal": "AGENTES", "expedientes": "EXPEDIENTES",
                            "simulador": "SIMULADOR", "sintesis": "SÍNTESIS IA", "admin": "ADMINISTRACIÓN", "cuenta": "CUENTA"}
        back_label = f"/ {nombres_pantalla.get(pantalla, pantalla.upper())}" if pantalla != "menu" else ""
        st.markdown(f"""
        <div class="topbar">
            <div>
                <div class="topbar-brand">CRYSIS {back_label}</div>
                <div class="topbar-meta">{rol_label} · ID: {u['Nombre'].upper()}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_top2:
        st.markdown("<br>", unsafe_allow_html=True)
        if pantalla != "menu":
            if st.button("← MENÚ", key="btn_menu"): st.session_state.pantalla_actual = "menu"; st.rerun()
        if st.button("SALIR", key="btn_logout", type="secondary"):
            st.session_state.usuario_actual = None; st.session_state.login_step = 1; st.session_state.pantalla_actual = "menu"; st.rerun()

def ir_a(p):
    st.session_state.pantalla_actual = p; st.rerun()
# ─────────────────────────────────────────
# MENÚ PRINCIPAL — TARJETAS CON COLOR, SIN BOTONES, SIN RECARGAR SESIÓN
# ─────────────────────────────────────────
if st.session_state.pantalla_actual == "menu":
    ahora = datetime.now()
    fecha_str = ahora.strftime("%H.%M - %d.%m.%Y")
    st.markdown(f"""
    <div class="dashboard-header">
        <div class="dashboard-greeting">Bienvenido, {u['Nombre'].upper()}</div>
        <div class="dashboard-meta">{fecha_str} · SISTEMA OPERATIVO</div>
        <div class="dashboard-status">
            <span>SYSTEM STATUS: SECURE</span>
            <span>GLOBAL NETWORK: OPTIMIZED</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Métricas reales
    total_ops    = len(historial_visible)
    media_global = int(sum(s["Nota"] for s in historial_visible) / total_ops) if total_ops > 0 else 0
    mes_actual   = datetime.now().strftime("%Y-%m")
    ops_mes      = len([s for s in historial_visible if str(s.get("Fecha","")).startswith(mes_actual)])
    agentes_act  = len([e for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"])
    esc_creados  = len(mis_escenarios)

    # Métrica de la tarjeta "CUENTA"
    metrica_cuenta = f"{u['Nombre'].upper()} · {mi_plan}"

    # Métrica de agentes (solo empresas)
    metrica_agentes = f"AGENTES ACTIVOS {agentes_act}"

    _precios = {"COMANDANCIA":199,"ESCUADRON":89,"ELITE":49,"OPERADOR":19,"BASE":0,
                "Enterprise":199,"Pro":89,"Individual":19,"Gratis":0}
    mrr = sum(_precios.get(_legacy.get(e.get("Plan","BASE"), e.get("Plan","BASE")), 0)
              for e in st.session_state.empleados)

    # ---- Construcción de la lista de tarjetas ----
    tarjetas = [
        ("estadisticas", "ANÁLISIS DE RENDIMIENTO",  f"RENDIMIENTO MEDIO {media_global}%",         "#4F8EF7"),
        ("simulador",    "SIMULADOR TÁCTICO",         f"OPERACIONES ACTIVAS ESTE MES {ops_mes}",     "#00D4A0"),
        ("expedientes",  "HISTORIAL DE EXPEDIENTES",  f"EXPEDIENTES TOTALES {total_ops}",            "#F0A500"),
    ]

    # Tarjeta "TU CUENTA" para todos
    tarjetas.append(("cuenta", "TU CUENTA", metrica_cuenta, "#6B7280"))

    # Tarjeta "GESTIÓN DE AGENTES" solo para empresas
    if es_empresa:
        tarjetas.append(("personal", "GESTIÓN DE AGENTES", metrica_agentes, "#E8394A"))

    # Tarjeta de escenarios (siempre)
    tarjetas.append(("sintesis", "GENERACIÓN DE ESCENARIOS", f"ESCENARIOS ACTIVOS {esc_creados}", "#A855F7"))

    # Consola Omega solo para el comandante supremo
    if u["Nombre"] == COMANDANTE_SUPREMO:
        tarjetas.append(("admin", "CONSOLA OMEGA", f"ESTIMATED VALUE {mrr} EUR", "#F59E0B"))

    # Grid de tarjetas (3 columnas)
    for fila in range(0, len(tarjetas), 3):
        cols = st.columns(3)
        for i, (destino, titulo, metrica, color) in enumerate(tarjetas[fila:fila+3]):
            with cols[i]:
                st.markdown(f'<div class="card-wrapper" style="--card-color: {color};">', unsafe_allow_html=True)
                if st.button(f"**{titulo}**\n\n{metrica}", key=f"btn_{destino}", use_container_width=True):
                    st.session_state.pantalla_actual = destino
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # CSS (el mismo que ya tenías, lo conservamos)
    st.markdown("""
    <style>
    .card-wrapper {
        position: relative;
        margin-bottom: 20px;
        padding-left: 28px;
    }
    .card-wrapper button {
        background: linear-gradient(135deg, #0B0E1A 0%, #0F1425 100%) !important;
        border: 1px solid #18213A !important;
        border-left: 4px solid var(--card-color, #4F8EF7) !important;
        border-radius: 2px !important;
        padding: 18px 16px !important;
        text-align: left !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        transition: all 0.2s ease !important;
    }
    .card-wrapper:hover button {
        background: linear-gradient(135deg, #111530 0%, #131A30 100%) !important;
        border-color: var(--card-color) !important;
        border-left-width: 6px !important;
        box-shadow: 0 0 25px var(--card-color), 0 0 60px var(--card-color), 0 8px 24px rgba(0,0,0,0.5) !important;
        transform: translateY(-4px) !important;
    }
    .card-wrapper::before {
        content: '';
        position: absolute;
        left: 8px;
        top: 24px;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: var(--card-color);
        z-index: 2;
        transition: box-shadow 0.2s ease;
    }
    .card-wrapper:hover::before {
        box-shadow: 0 0 18px var(--card-color), 0 0 36px var(--card-color);
    }
    </style>
    """, unsafe_allow_html=True)

    st.stop()
# ESTADÍSTICAS
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "estadisticas":
    st.markdown("<div class='section-header'><div><div class='section-code'>MOD-01</div><div class='section-title'>Análisis de Rendimiento</div></div></div>", unsafe_allow_html=True)

    total_ops    = len(historial_visible)
    media_global = int(sum(s["Nota"] for s in historial_visible) / total_ops) if total_ops > 0 else 0
    ops_exitosas = sum(1 for s in historial_visible if s["Nota"] >= 80)
    tasa_exito   = int((ops_exitosas / total_ops) * 100) if total_ops > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""<div class="metric-card"><div class="metric-label">RENDIMIENTO MEDIO</div><div class="metric-value" style="color:{'#00D4A0' if media_global>=70 else '#E8394A'}">{media_global}%</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="metric-card"><div class="metric-label">TASA DE EXCELENCIA</div><div class="metric-value" style="color:{'#00D4A0' if tasa_exito>=50 else '#E8394A'}">{tasa_exito}%</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="metric-card"><div class="metric-label">MISIONES COMPLETADAS</div><div class="metric-value" style="color:#4F8EF7">{total_ops}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if not historial_visible:
        st.markdown("<div style='text-align:center; padding:60px; color:#18213A; font-family:var(--mono); letter-spacing:0.2em;'>SIN REGISTROS OPERACIONALES</div>", unsafe_allow_html=True)
    else:
        df = pd.DataFrame(historial_visible)
        df["Nota"] = pd.to_numeric(df["Nota"])
        col_left, col_right = st.columns(2, gap="medium")
        with col_left:
            st.markdown("<div class='section-label'>DISTRIBUCIÓN DE ESCENARIOS</div>", unsafe_allow_html=True)
            esc_count = df["Escenario"].value_counts().reset_index()
            esc_count.columns = ["Escenario","Count"]
            fig2 = go.Figure(go.Pie(labels=esc_count["Escenario"], values=esc_count["Count"], hole=0.65,
                                    marker=dict(colors=['#4F8EF7','#00D4A0','#F0A500'])))
            fig2.update_layout(**PLOTLY_THEME, height=280, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        with col_right:
            if es_empresa:
                st.markdown("<div class='section-label'>EVALUACIÓN POR OPERADOR</div>", unsafe_allow_html=True)
                avg_agent = df.groupby("Agente")["Nota"].mean().reset_index()
                fig3 = go.Figure(go.Bar(x=avg_agent["Nota"], y=avg_agent["Agente"], orientation='h', marker=dict(color='#4F8EF7')))
                fig3.update_layout(**PLOTLY_THEME, height=280)
            else:
                st.markdown("<div class='section-label'>HISTÓRICO DE DESEMPEÑO</div>", unsafe_allow_html=True)
                df["Fecha_dt"] = pd.to_datetime(df["Fecha"])
                df_sorted = df.sort_values("Fecha_dt")
                fig3 = go.Figure(go.Scatter(x=df_sorted["Fecha_dt"], y=df_sorted["Nota"],
                                            mode='lines+markers', line=dict(color='#4F8EF7')))
                fig3.add_hline(y=80, line_dash="dot", line_color="#00D4A0")
                fig3.update_layout(**PLOTLY_THEME, height=280)
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────
# PERSONAL
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "personal":
    st.markdown("<div class='section-header'><div><div class='section-code'>AGENTES</div><div class='section-title'>Gestión de Operadores</div></div></div>", unsafe_allow_html=True)

    if es_empresa:
        st.markdown("<div class='section-label'>ENLACE SEGURO DE RECLUTAMIENTO</div>", unsafe_allow_html=True)
        if agentes_lim > 0 or u["Nombre"] == COMANDANTE_SUPREMO:
            token_cifrado   = base64.urlsafe_b64encode(empresa_actual.encode()).decode()
            URL_BASE_APP    = "https://crysis.streamlit.app/"
            enlace_completo = f"{URL_BASE_APP}?invite={token_cifrado}"
            st.markdown("""<div class="alert-box">Comparte este enlace con tus agentes para que se incorporen automáticamente a tu unidad.</div>""", unsafe_allow_html=True)
            st.code(enlace_completo, language="html")
        else:
            st.markdown("""<div class="alert-box warning">Tu nivel de licencia no permite la formación de escuadrones. Actualiza a ESCUADRON o COMANDANCIA.</div>""", unsafe_allow_html=True)

        st.markdown("<br><div class='section-label'>PLANTILLA OPERATIVA ACTIVA</div>", unsafe_allow_html=True)
        agentes_mios = [e for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"]
        if agentes_mios:
            for ag in agentes_mios:
                col_ag1, col_ag2 = st.columns([4, 1])
                with col_ag1:
                    st.markdown(f"""
                    <div style="background:var(--bg2); border:1px solid var(--border); border-radius:2px; padding:12px 16px; margin-bottom:6px;">
                        <span style="color:var(--text-hi); font-weight:600;">{ag['Nombre']}</span>
                        <span style="color:var(--text-lo); font-family:var(--mono); font-size:0.6rem; margin-left:12px;">
                            {ag.get('Departamento','—')} · {ag['Email']}
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("REVOCAR ACCESO DE PERSONAL"):
                ag_a_borrar = st.selectbox("Operador a revocar:", [a['Nombre'] for a in agentes_mios])
                if st.button("REVOCAR CREDENCIALES", type="primary"):
                    st.session_state.empleados = [e for e in st.session_state.empleados if e['Nombre'] != ag_a_borrar]
                    guardar_datos(); st.success(f"Operador {ag_a_borrar} revocado."); st.rerun()
        else:
            st.markdown("<div style='color:var(--text-lo); font-family:var(--mono); font-size:0.65rem; padding:20px 0;'>No hay agentes activos en esta unidad.</div>", unsafe_allow_html=True)
    else:
        st.info("Esta sección solo está disponible para cuentas de empresa.")

# ─────────────────────────────────────────
# EXPEDIENTES
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "expedientes":
    st.markdown("<div class='section-header'><div><div class='section-code'>MOD-03</div><div class='section-title'>Archivo Operacional</div></div></div>", unsafe_allow_html=True)

    if historial_visible:
        df_hist = pd.DataFrame(historial_visible)
        df_hist["Nota"] = pd.to_numeric(df_hist["Nota"])
        for agente, df_agente in df_hist.groupby("Agente"):
            media_agente = int(df_agente["Nota"].mean())
            with st.expander(f"OPERADOR: {agente.upper()}  —  MÉTRICA GLOBAL: {media_agente}%", expanded=False):
                st.markdown("<br>", unsafe_allow_html=True)
                for escenario, df_op in df_agente.groupby("Escenario"):
                    media_op = int(df_op["Nota"].mean())
                    lbl_esc  = escenario.replace("OPERACION: ","")
                    with st.expander(f"{lbl_esc}  —  Evaluación Media: {media_op}%", expanded=True):
                        for _, s in df_op.sort_values("Fecha", ascending=False).iterrows():
                            nota_ind   = s['Nota']
                            c_nota     = "#00D4A0" if nota_ind >= 80 else ("#F0A500" if nota_ind >= 50 else "#E8394A")
                            modo_badge = "PRIVADO" if s.get("Tipo_Mision") == "Personal" else "OFICIAL"
                            dif_badge  = s.get("Dificultad", "—")
                            dif_color  = DIFICULTADES.get(dif_badge, {}).get("color", "#3A4A6A")
                            puede_borrar = (s["Agente"] == u["Nombre"]) or (u["Nombre"] == COMANDANTE_SUPREMO)

                            st.markdown(f"""
                            <div style="border-bottom: 1px solid #18213A; padding: 12px 0; margin-bottom: 12px;">
                            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                                <span style="color:#3A4A6A; font-size:0.8rem; font-family:var(--mono);">
                                    {s['Fecha']} · {modo_badge} · 
                                    <span style="color:{dif_color};">{dif_badge}</span>
                                </span>
                                <span style="font-family:var(--mono); color:{c_nota}; font-weight:700;">{nota_ind}%</span>
                            </div>
                            <div style="font-size:0.85rem; color:#B8C4DC; margin-bottom:10px;">{s['Evaluacion']}</div>
                            """, unsafe_allow_html=True)

                            col_pdf, col_del = st.columns([3, 1])
                            with col_pdf:
                                st.download_button(
                                    label="EXTRAER DOSSIER PDF",
                                    data=generar_pdf_dossier(s),
                                    file_name=f"CRYSIS_{s['Agente']}_{s['Fecha'][:10]}.pdf",
                                    mime="application/pdf",
                                    key=f"pdf_{s['Agente']}_{s['Fecha']}"
                                )
                            with col_del:
                                if puede_borrar:
                                    confirm_key = f"confirm_del_{s['Agente']}_{s['Fecha']}"
                                    input_key   = f"input_del_{s['Agente']}_{s['Fecha']}"
                                    if not st.session_state.get(confirm_key, False):
                                        if st.button("ELIMINAR", key=f"btn_del_{s['Agente']}_{s['Fecha']}", type="secondary", use_container_width=True):
                                            st.session_state[confirm_key] = True; st.rerun()
                                    else:
                                        st.markdown("""
                                        <div style="background:#1A0A0A; border:1px solid #E8394A; border-left:3px solid #E8394A;
                                                    padding:10px 12px; border-radius:2px; margin-bottom:6px;">
                                            <div style="font-family:var(--mono); font-size:0.5rem; letter-spacing:0.2em;
                                                        color:#E8394A; margin-bottom:6px;">CONFIRMACIÓN REQUERIDA</div>
                                            <div style="font-family:var(--mono); font-size:0.52rem; color:#3A4A6A; line-height:1.5;">
                                                Escribe <b style="color:#B8C4DC;">CONFIRMAR BORRADO</b> y pulsa ejecutar.
                                            </div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                        texto_confirmacion = st.text_input("", key=input_key, placeholder="CONFIRMAR BORRADO", label_visibility="collapsed")
                                        col_conf, col_canc = st.columns(2)
                                        with col_conf:
                                            if st.button("EJECUTAR", key=f"exec_del_{s['Agente']}_{s['Fecha']}", use_container_width=True):
                                                if texto_confirmacion.strip().upper() == "CONFIRMAR BORRADO":
                                                    st.session_state.historial_sesiones = [
                                                        ses for ses in st.session_state.historial_sesiones
                                                        if not (ses["Agente"] == s["Agente"] and ses["Fecha"] == s["Fecha"])
                                                    ]
                                                    guardar_datos(); del st.session_state[confirm_key]; st.rerun()
                                                else: st.error("Frase incorrecta.")
                                        with col_canc:
                                            if st.button("CANCELAR", key=f"canc_del_{s['Agente']}_{s['Fecha']}", use_container_width=True, type="secondary"):
                                                del st.session_state[confirm_key]; st.rerun()

                            if es_empresa and mi_plan == "COMANDANCIA" and "Transcripcion" in s:
                                st.markdown("<br><span style='color:#F0A500; font-size:0.65rem; font-family:var(--mono); letter-spacing:0.1em;'>AUDITORÍA DE COMUNICACIONES</span>", unsafe_allow_html=True)
                                for tr in s["Transcripcion"]:
                                    ag_tr = "OPERADOR" if tr["role"] == "user" else "SUJETO"
                                    colr  = "#4F8EF7" if tr["role"] == "user" else "#E8394A"
                                    st.markdown(f"<div style='font-size:0.8rem; margin-bottom:4px;'><b style='color:{colr}'>{ag_tr}:</b> <span style='color:#3A4A6A'>{tr['content']}</span></div>", unsafe_allow_html=True)

                            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center; padding:60px; color:#18213A; font-family:var(--mono);'>DIRECTORIO VACÍO</div>", unsafe_allow_html=True)
# ─────────────────────────────────────────
# CUENTA (información personal / corporativa)
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "cuenta":
    st.markdown("<div class='section-header'><div><div class='section-code'>CUENTA</div><div class='section-title'>Tu Cuenta</div></div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-label'>ACREDITACIÓN CONFIRMADA</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class="briefing-box"><h4>DATOS DE LA CUENTA</h4>
    <p><b>Identificador:</b> {u['Nombre']} &nbsp;|&nbsp; <b>Unidad:</b> {empresa_actual} &nbsp;|&nbsp; <b>Plan:</b> {mi_plan}</p>
    <p><b>Email:</b> {u.get('Email','—')}</p>
    </div>""", unsafe_allow_html=True)

    # --- Cambiar Correo Electrónico ---
    st.markdown("<br><div class='section-label'>CAMBIAR CORREO ELECTRÓNICO</div>", unsafe_allow_html=True)
    with st.expander("ACTUALIZAR DIRECCIÓN DE CORREO"):
        nuevo_email = st.text_input("Nuevo Correo Electrónico", key="nuevo_email_cuenta")
        if st.button("GUARDAR NUEVO CORREO", key="btn_guardar_email"):
            if not nuevo_email:
                st.warning("Introduce una dirección de correo válida.")
            elif nuevo_email == u.get("Email", ""):
                st.info("El nuevo correo es idéntico al actual.")
            else:
                # Actualizar en la lista de empleados
                for e in st.session_state.empleados:
                    if e["Nombre"] == u["Nombre"] and e.get("Empresa") == u.get("Empresa"):
                        e["Email"] = nuevo_email
                # Actualizar en el usuario actual
                st.session_state.usuario_actual["Email"] = nuevo_email
                guardar_datos()
                st.success(f"Correo actualizado a: {nuevo_email}")

    # --- Cambiar Contraseña ---
    st.markdown("<br><div class='section-label'>CAMBIAR CONTRASEÑA</div>", unsafe_allow_html=True)
    with st.expander("ACTUALIZAR CLAVE DE ACCESO"):
        nueva_pass = st.text_input("Nueva Contraseña", type="password", key="nueva_pass_cuenta")
        confirmar  = st.text_input("Confirmar Contraseña", type="password", key="confirmar_pass_cuenta")
        if st.button("ACTUALIZAR CONTRASEÑA", key="btn_cambiar_pass"):
            if not nueva_pass:
                st.warning("Introduce una contraseña.")
            elif nueva_pass != confirmar:
                st.error("Las contraseñas no coinciden.")
            else:
                for e in st.session_state.empleados:
                    if e["Nombre"] == u["Nombre"] and e.get("Empresa") == u.get("Empresa"):
                        e["Password"] = nueva_pass
                st.session_state.usuario_actual["Password"] = nueva_pass
                guardar_datos()
                st.success("Contraseña actualizada correctamente.")

    # --- Gestión de Suscripción (si no eres comandante supremo) ---
    if u["Nombre"] != COMANDANTE_SUPREMO:
        st.markdown("<br><div class='section-label'>GESTIÓN DE SUSCRIPCIÓN</div>", unsafe_allow_html=True)
        planes_suscripcion = [
            ("OPERADOR",    "19€/mes",  "10 ops/mes · 3 esc.", "OPERADOR"),
            ("ELITE",       "49€/mes",  "Ilimitado · IA ∞",    "ELITE"),
            ("ESCUADRON",   "89€/mes",  "Equipo · 15 agentes", "ESCUADRON"),
            ("COMANDANCIA", "199€/mes", "Enterprise · ∞",      "COMANDANCIA"),
        ]
        cols_plan = st.columns(4)
        for col, (nombre, precio, desc, plan_key) in zip(cols_plan, planes_suscripcion):
            with col:
                es_elite_p = plan_key in ["ELITE","ESCUADRON","COMANDANCIA"]
                color_p    = "#F0A500" if es_elite_p else "#4F8EF7"
                activo     = mi_plan == plan_key
                border_col = "#00D4A0" if activo else ("#F0A500" if es_elite_p else "var(--border)")
                st.markdown(f"""<div class="metric-card" style="border-left-color:{border_col}; {'border-color:#00D4A020;' if activo else ''}">
                    <div class="metric-label">{nombre}</div>
                    <div class="metric-value" style="font-size:1.1rem; color:{color_p};">{precio}</div>
                    <div style="font-family:var(--mono); font-size:0.52rem; color:#3A4A6A; margin-top:8px;">{desc}</div>
                    {'<div style="font-family:var(--mono); font-size:0.52rem; color:#00D4A0; margin-top:10px;">● ACTIVO</div>' if activo else ''}
                </div>""", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                if not activo:
                    link = LINKS_PAGO.get(plan_key, "#")
                    st.markdown(f'<a href="{link}" target="_blank"><button style="background:#4F8EF7;color:#060810;font-family:var(--mono);font-weight:700;border:none;padding:10px;border-radius:2px;cursor:pointer;width:100%;font-size:0.6rem;letter-spacing:0.1em;">ACTIVAR</button></a>', unsafe_allow_html=True)

    # --- Zona de Peligro (Eliminar cuenta) ---
    st.markdown("<br><div class='section-label'>ZONA DE RIESGO</div>", unsafe_allow_html=True)
    st.markdown("""<div class="alert-box error">Esta acción es irreversible. Se eliminarán todos los datos asociados a tu cuenta.</div>""", unsafe_allow_html=True)
    if st.button("ELIMINAR MI CUENTA DEFINITIVAMENTE", type="primary", key="btn_eliminar_cuenta"):
        if es_empresa:
            st.session_state.empleados = [e for e in st.session_state.empleados if e.get("Empresa") != u["Nombre"]]
        else:
            st.session_state.empleados = [e for e in st.session_state.empleados if e["Nombre"] != u["Nombre"]]
        st.session_state.usuario_actual = None
        guardar_datos()
        st.rerun()

# ─────────────────────────────────────────
# SIMULADOR TÁCTICO
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "simulador":
    st.markdown("<div class='section-header'><div><div class='section-code'>MOD-02</div><div class='section-title'>Simulador Táctico</div></div></div>", unsafe_allow_html=True)

    if not st.session_state.mision_iniciada:
        c1, c2 = st.columns(2)
        if es_empresa:
            ag_sel = c1.selectbox("Asignar Operador:", agentes_de_mi_empresa)
            if ag_sel is None: ag_sel = u["Nombre"]
        else:
            ag_sel = c1.text_input("Operador:", value=u["Nombre"], disabled=True)

        es_sel = c2.selectbox("Seleccionar Protocolo:", list(TODAS_LAS_MISIONES.keys()))

        st.markdown("<br><div class='section-label'>NIVEL DE DIFICULTAD</div>", unsafe_allow_html=True)
        d_cols = st.columns(4)
        for i, (d_nombre, d_data) in enumerate(DIFICULTADES.items()):
            with d_cols[i]:
                is_sel_d  = st.session_state.dificultad_actual == d_nombre
                border_d  = d_data["color"] if is_sel_d else "#18213A"
                bg_d      = f"rgba({','.join(str(int(d_data['color'].lstrip('#')[j:j+2],16)) for j in (0,2,4))},0.12)" if is_sel_d else "#101525"
                st.markdown(f"""
                <div class="diff-card {'selected' if is_sel_d else ''}" style="border-color:{border_d}; background:{bg_d};">
                    <div class="diff-name" style="color:{d_data['color']};">{d_nombre}</div>
                    <div style="font-family:var(--mono); font-size:0.5rem; color:{d_data['color']}; opacity:0.7; margin-top:2px; letter-spacing:0.12em;">LVL {d_data['nivel']}</div>
                    <div class="diff-desc">{d_data['desc']}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"{'▶ ' if is_sel_d else ''}{d_nombre}", key=f"diff_{d_nombre}", use_container_width=True):
                    st.session_state.dificultad_actual = d_nombre; st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        if u.get("Rol") == "Agente":
            tipo_despliegue = st.radio(
                "Nivel de Privacidad:",
                ["Misión Oficial (Auditable por el Mando)", "Entrenamiento Privado (Oculto en expediente corporativo)"],
                horizontal=True
            )
            tipo_mision_val = "Corporativa" if "Oficial" in tipo_despliegue else "Personal"
        else:
            tipo_mision_val = "Personal"

        info = TODAS_LAS_MISIONES[es_sel]
        dif_activa = st.session_state.dificultad_actual
        dif_color  = DIFICULTADES[dif_activa]["color"]
        st.markdown(f"""
        <div class="briefing-box">
            <h4>REPORTE DE SITUACIÓN</h4>
            <p><b>Contexto:</b> {info['contexto']}</p>
            <p><b>Perfil del objetivo:</b> {info['perfil_sujeto']}</p>
            <p><b>Directiva:</b> {info['objetivo']}</p>
            <p><b>Dificultad:</b> <span style="color:{dif_color}; font-family:var(--mono); font-weight:700;">{dif_activa} (Nivel {DIFICULTADES[dif_activa]['nivel']})</span></p>
        </div>
        """, unsafe_allow_html=True)

        mes_actual   = datetime.now().strftime("%Y-%m")
        ops_este_mes = len([s for s in st.session_state.historial_sesiones
                            if s["Agente"] == ag_sel and str(s.get("Fecha","")).startswith(mes_actual)])

        bloquear_inicio = False
        if mi_plan != "COMANDANCIA" and u["Nombre"] != COMANDANTE_SUPREMO:
            if ops_este_mes >= ops_limite:
                bloquear_inicio = True
                st.markdown(f"""<div class="alert-box error">AUTORIZACIÓN DENEGADA: Cuota mensual superada ({ops_este_mes}/{ops_limite} ops). Actualiza tu plan.</div>""", unsafe_allow_html=True)

        if st.button("INICIAR ENLACE DE COMUNICACIÓN", use_container_width=True, disabled=bloquear_inicio):
            if GROQ_API_KEY:
                with st.spinner("Estableciendo conexión segura..."):
                    try:
                        client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                        json_prompt = f"Genera para {info['perfil_sujeto']} EXCLUSIVAMENTE JSON PLANO con 3 claves: 'Nombre_Completo', 'Familia', 'Estado_Mental'."
                        res = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role":"user","content": json_prompt}],
                            response_format={"type":"json_object"}
                        ).choices[0].message.content
                        st.session_state.tarjeta_objetivo = json.loads(res)
                    except:
                        st.session_state.tarjeta_objetivo = {"Nombre_Completo":"Desconocido","Familia":"Clasificado","Estado_Mental":"Inestable"}
            st.session_state.mision_iniciada    = True
            st.session_state.mensajes           = []
            st.session_state.agente_activo      = ag_sel
            st.session_state.escenario_activo   = es_sel
            st.session_state.tipo_mision_actual = tipo_mision_val
            st.session_state.dificultad_sesion  = dif_activa
            st.rerun()

    elif st.session_state.evaluacion_actual:
        st.markdown("<div class='section-label'>INFORME DE EVALUACIÓN TÁCTICA</div>", unsafe_allow_html=True)
        st.markdown(st.session_state.evaluacion_actual)
        st.markdown("<br>", unsafe_allow_html=True)
        col_end1, col_end2 = st.columns(2)
        with col_end1:
            if st.button("ARCHIVAR INFORME Y VOLVER AL MENÚ", use_container_width=True):
                st.session_state.mision_iniciada   = False
                st.session_state.evaluacion_actual = None
                st.session_state.mensajes          = []
                st.session_state.tarjeta_objetivo  = None
                st.session_state.pantalla_actual   = "menu"
                st.rerun()
        with col_end2:
            ultima_sesion = st.session_state.historial_sesiones[-1]
            st.download_button(
                label="DESCARGAR DOSSIER PDF",
                data=generar_pdf_dossier(ultima_sesion),
                file_name=f"CRYSIS_{ultima_sesion['Agente']}_Report.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    else:
        dif_sesion  = st.session_state.get("dificultad_sesion", "OPERATOR")
        dif_color_s = DIFICULTADES.get(dif_sesion, {}).get("color","#4F8EF7")
        st.markdown(f"""
        <div class='status-bar'>
            ● LÍNEA SEGURA ACTIVA: {st.session_state.escenario_activo} — 
            OPERADOR: {st.session_state.agente_activo.upper()} — 
            <span style="color:{dif_color_s};">DIFICULTAD: {dif_sesion}</span>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.tarjeta_objetivo:
            t = st.session_state.tarjeta_objetivo
            st.markdown(f"""<div style="display:flex; gap:15px; background:#0B0E1A; border:1px solid #18213A; border-left:3px solid #F0A500; border-radius:2px; padding:14px 20px; margin-bottom:20px;">
                <div style="flex:1;"><div style="color:#F0A500; font-size:0.52rem; font-family:var(--mono); letter-spacing:0.2em; margin-bottom:4px;">IDENTIFICACIÓN</div><div style="color:#E2EAF8;">{str(t.get('Nombre_Completo','N/A'))}</div></div>
                <div style="flex:1;"><div style="color:#F0A500; font-size:0.52rem; font-family:var(--mono); letter-spacing:0.2em; margin-bottom:4px;">VÍNCULOS</div><div style="color:#B8C4DC; font-size:0.88rem;">{str(t.get('Familia','N/A'))}</div></div>
                <div style="flex:1;"><div style="color:#F0A500; font-size:0.52rem; font-family:var(--mono); letter-spacing:0.2em; margin-bottom:4px;">ESTADO CLÍNICO</div><div style="color:#B8C4DC; font-size:0.88rem;">{str(t.get('Estado_Mental','N/A'))}</div></div>
            </div>""", unsafe_allow_html=True)

        for m in st.session_state.mensajes:
            label  = "TÚ" if m["role"] == "user" else "SUJETO"
            bg     = "#0D1424" if m["role"] == "user" else "#0B0E1A"
            border = "#4F8EF7" if m["role"] == "user" else "#E8394A"
            align  = "flex-end" if m["role"] == "user" else "flex-start"
            st.markdown(f"""<div style="display:flex; justify-content:{align}; margin-bottom:12px;">
            <div style="max-width:78%; background:{bg}; border:1px solid {border}22; border-left:3px solid {border}; border-radius:2px; padding:14px 18px;">
                <div style="font-family:var(--mono); font-size:0.52rem; letter-spacing:0.22em; color:{border}; margin-bottom:8px;">{label}</div>
                <div style="color:#B8C4DC; font-size:0.9rem; line-height:1.6;">{m['content']}</div>
            </div></div>""", unsafe_allow_html=True)

        if prompt := st.chat_input("Introduce tu mensaje al sujeto..."):
            st.session_state.mensajes.append({"role":"user","content":prompt}); st.rerun()

        if st.session_state.mensajes and st.session_state.mensajes[-1]["role"] == "user":
            if GROQ_API_KEY:
                client      = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                escenario_a = st.session_state.escenario_activo
                base_prompt = TODAS_LAS_MISIONES[escenario_a]["prompt"]
                dif_instruc = DIFICULTADES.get(dif_sesion, {}).get("instruccion","")
                base_prompt += f"\n\n[NIVEL DE DIFICULTAD: {dif_sesion}. {dif_instruc}]"
                if st.session_state.tarjeta_objetivo:
                    t2 = st.session_state.tarjeta_objetivo
                    base_prompt += f"\n\n[Tu nombre es {t2.get('Nombre_Completo')}. Familia: {t2.get('Familia')}. Estado: {t2.get('Estado_Mental')}.]"
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role":"system","content": base_prompt}] + st.session_state.mensajes
                ).choices[0].message.content
                st.session_state.mensajes.append({"role":"assistant","content":res}); st.rerun()

        col_end, col_abort = st.columns([3, 1])
        with col_abort:
            if st.button("ROMPER ENLACE", type="secondary", use_container_width=True):
                st.session_state.mision_iniciada  = False
                st.session_state.mensajes         = []
                st.session_state.tarjeta_objetivo = None
                st.rerun()
        with col_end:
            if len(st.session_state.mensajes) > 0:
                if st.button("SOLICITAR EVALUACIÓN TÁCTICA", use_container_width=True):
                    with st.spinner("Procesando auditoría lingüística..."):
                        client    = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                        escenario = st.session_state.escenario_activo
                        info_ev   = TODAS_LAS_MISIONES[escenario]
                        dif_ev    = st.session_state.get("dificultad_sesion","OPERATOR")
                        dif_nivel = DIFICULTADES.get(dif_ev,{}).get("nivel",2)
                        hist_txt  = "\n".join([f"{'OPERADOR' if m['role']=='user' else 'SUJETO'}: {m['content']}" for m in st.session_state.mensajes])
                        umbral_excelente = {1:85, 2:80, 3:70, 4:60}.get(dif_nivel, 80)
                        umbral_correcto  = {1:65, 2:55, 3:45, 4:35}.get(dif_nivel, 55)
                        eval_prompt = f"""Eres un Analista de Inteligencia y Negociación Táctica altamente estricto.
Evalúa el desempeño del OPERADOR en el escenario: {escenario}.
Situación: {info_ev['contexto']}.
Dificultad seleccionada: {dif_ev} (Nivel {dif_nivel}/4).
AJUSTE POR DIFICULTAD:
- En nivel {dif_ev}, una puntuación de {umbral_excelente} o más es EXCELENTE.
- Una puntuación de {umbral_correcto}-{umbral_excelente-1} es CORRECTA pero mejorable.
- Por debajo de {umbral_correcto} es INSUFICIENTE.
TRANSCRIPCION: {hist_txt}
REGLAS: NO regales puntuación. Evalúa: control de situación, desescalada, resistencia a manipulación, lenguaje estratégico.
Penaliza: ceder sin contrapartida, lenguaje amenazante, pérdida de control emocional.
Estructura: ANÁLISIS DE LENGUAJE / TÁCTICAS EMPLEADAS / ERRORES CRÍTICOS / VEREDICTO / CÓMO MEJORAR
PUNTUACIÓN FINAL: XX/100"""
                        informe = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role":"user","content":eval_prompt}]
                        ).choices[0].message.content
                        try:
                            match = re.search(r'PUNTUACI[OÓ]N FINAL[^\d]*(\d+)\s*\/?\s*100', informe, re.IGNORECASE)
                            nota  = min(int(match.group(1)), 100) if match else (
                                min(int(re.search(r'(\d+)\s*/\s*100', informe).group(1)), 100)
                                if re.search(r'(\d+)\s*/\s*100', informe) else 50)
                        except:
                            nota = 50
                        st.session_state.evaluacion_actual = informe
                        st.session_state.historial_sesiones.append({
                            "Fecha":        datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "Agente":       st.session_state.agente_activo,
                            "Escenario":    escenario,
                            "Nota":         nota,
                            "Evaluacion":   informe,
                            "Transcripcion": st.session_state.mensajes,
                            "Tipo_Mision":  st.session_state.tipo_mision_actual,
                            "Dificultad":   dif_ev,
                        })
                        guardar_datos(); st.rerun()

# ─────────────────────────────────────────
# SÍNTESIS IA
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "sintesis":
    st.markdown("<div class='section-header'><div><div class='section-code'>MOD-05</div><div class='section-title'>Generación de Escenarios</div></div></div>", unsafe_allow_html=True)

    col_izq, col_der = st.columns([2, 1], gap="large")
    with col_izq:
        creados = len(mis_escenarios)
        if mis_escenarios:
            st.markdown("<div class='section-label'>ESCENARIOS ACTIVOS</div>", unsafe_allow_html=True)
            for nombre_esc, datos_esc in mis_escenarios.items():
                c_esc1, c_esc2 = st.columns([3, 1])
                c_esc1.markdown(f"""
                <div style="background:var(--bg2); border:1px solid var(--border); border-radius:2px; padding:10px 14px; margin-bottom:4px;">
                    <span style="color:var(--text-hi); font-size:0.85rem;">{nombre_esc}</span>
                    <span style="color:var(--text-lo); font-family:var(--mono); font-size:0.55rem; margin-left:8px;">Creador: {datos_esc.get('Creador','—')}</span>
                </div>
                """, unsafe_allow_html=True)
                if c_esc2.button("ELIMINAR", key=f"del_{nombre_esc}", type="secondary"):
                    del st.session_state.escenarios_custom[nombre_esc]; guardar_datos(); st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("<div class='section-label'>NUEVA SIMULACIÓN</div>", unsafe_allow_html=True)

        if mi_plan == "BASE" and u["Nombre"] != COMANDANTE_SUPREMO:
            st.markdown("""<div class="alert-box error">RESTRICCIÓN: El nivel BASE no permite el uso de IA Generativa. Actualiza tu plan para desbloquear esta función.</div>""", unsafe_allow_html=True)
        else:
            limite_esc = 99999 if u["Nombre"] == COMANDANTE_SUPREMO else escenarios_lim
            if limite_esc != 99999 and creados >= limite_esc:
                st.markdown(f"""<div class="alert-box warning">CUOTA ALCANZADA ({creados}/{limite_esc} escenarios). Elimina uno existente para crear otro.</div>""", unsafe_allow_html=True)
            else:
                idea_prompt = st.text_area("Describe el entorno táctico y el tipo de sujeto:", height=100,
                                           placeholder="Ej: Un ejecutivo corrupto atrapado en una negociación empresarial. Arrogante y calculador...")
                if st.button("GENERAR NUEVA SIMULACIÓN", use_container_width=True):
                    if idea_prompt and GROQ_API_KEY:
                        with st.spinner("Enlazando con el motor de IA..."):
                            try:
                                client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                                res = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[
                                        {"role":"system","content":"Devuelve JSON: {'nombre_op': 'OPERACION: [NOMBRE]', 'contexto': '...', 'perfil_sujeto': '...', 'objetivo': '...', 'prompt': '...'}"},
                                        {"role":"user","content": idea_prompt}
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
                                guardar_datos(); st.success(f"Protocolo {nuevo_esc['nombre_op']} creado y activado."); st.rerun()
                            except Exception as e:
                                st.error(f"Fallo del Motor IA: {e}")
                    elif not idea_prompt:
                        st.warning("Describe los parámetros del escenario.")

    with col_der:
        st.markdown("<div class='section-label'>NIVELES DE ACCESO IA</div>", unsafe_allow_html=True)
        planes_der = [
            ("BASE",        "0€",     False, ["Sin acceso a IA generativa", "1 op/mes"]),
            ("OPERADOR",    "19€/mes", False, ["3 escenarios propios", "10 ops/mes"]),
            ("ELITE",       "49€/mes", True,  ["Escenarios ilimitados", "Ops ilimitadas"]),
            ("ESCUADRON",   "89€/mes", True,  ["15 agentes · IA ∞", "Ops ilimitadas"]),
            ("COMANDANCIA", "199€/mes",True,  ["Agentes ∞ · IA ∞", "Ops ilimitadas"]),
        ]
        for nombre, precio, elite, specs in planes_der:
            activo = mi_plan == nombre
            color  = "#F0A500" if elite else "#4F8EF7"
            border = "#00D4A0" if activo else ("#F0A500" if elite else "var(--border2)")
            st.markdown(f"""
            <div class="auth-tier {'elite' if elite else ''}" style="border-left-color:{border};">
                <div style="display:flex;justify-content:space-between;margin-bottom:8px;border-bottom:1px solid #18213A;padding-bottom:6px;">
                    <span style="font-family:var(--mono);font-size:0.65rem;color:{'#00D4A0' if activo else 'var(--text-hi)'};">
                        {'● ' if activo else ''}{nombre}
                    </span>
                    <span style="font-family:var(--mono);font-size:0.75rem;color:{color};">{precio}</span>
                </div>
                {''.join(f'<div class="tier-spec">{s}</div>' for s in specs)}
            </div>
            """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# ADMIN — CONSOLA OMEGA
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "admin" and u["Nombre"] == COMANDANTE_SUPREMO:
    st.markdown("<div class='section-header'><div><div class='section-code'>MOD-06</div><div class='section-title'>Consola Omega — Administración Global</div></div></div>", unsafe_allow_html=True)

    _precio_plan = {"COMANDANCIA":199,"ESCUADRON":89,"ELITE":49,"OPERADOR":19,"BASE":0,
                    "Enterprise":199,"Pro":89,"Individual":19,"Gratis":0}

    clientes_corporativos = [e for e in st.session_state.empleados if e["Rol"] == "Empresa"]
    clientes_individuales = [e for e in st.session_state.empleados if e["Rol"] == "Individual"]
    todos_clientes        = clientes_corporativos + clientes_individuales
    total_enterprise = len([c for c in todos_clientes if _legacy.get(c.get("Plan","BASE"),c.get("Plan","BASE")) == "COMANDANCIA"])
    total_escuadron  = len([c for c in todos_clientes if _legacy.get(c.get("Plan","BASE"),c.get("Plan","BASE")) == "ESCUADRON"])
    total_elite      = len([c for c in todos_clientes if _legacy.get(c.get("Plan","BASE"),c.get("Plan","BASE")) == "ELITE"])
    total_operador   = len([c for c in todos_clientes if _legacy.get(c.get("Plan","BASE"),c.get("Plan","BASE")) == "OPERADOR"])
    mrr_estimado     = (total_enterprise*199) + (total_escuadron*89) + (total_elite*49) + (total_operador*19)
    total_agentes    = len([e for e in st.session_state.empleados if e["Rol"] == "Agente"])

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.markdown(f"""<div class="metric-card" style="border-left-color:#F0A500;"><div class="metric-label" style="color:#F0A500;">MRR ESTIMADO</div><div class="metric-value">{mrr_estimado}€</div></div>""", unsafe_allow_html=True)
    col_m2.markdown(f"""<div class="metric-card"><div class="metric-label">CUENTAS DE PAGO</div><div class="metric-value">{total_enterprise+total_escuadron+total_elite+total_operador}</div></div>""", unsafe_allow_html=True)
    col_m3.markdown(f"""<div class="metric-card"><div class="metric-label">AGENTES DESPLEGADOS</div><div class="metric-value">{total_agentes}</div></div>""", unsafe_allow_html=True)
    col_m4.markdown(f"""<div class="metric-card"><div class="metric-label">SESIONES TOTALES</div><div class="metric-value">{len(st.session_state.historial_sesiones)}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_adm1, col_adm2 = st.columns(2, gap="large")

    with col_adm1:
        with st.expander("DIRECTORIO GLOBAL DE USUARIOS", expanded=False):
            for i, usr in enumerate(st.session_state.empleados):
                if usr["Nombre"] != COMANDANTE_SUPREMO:
                    c_u1, c_u2 = st.columns([4, 1])
                    plan_disp = _legacy.get(usr.get("Plan","BASE"), usr.get("Plan","BASE"))
                    c_u1.markdown(f"**{usr['Nombre']}** | {usr['Rol']} | {usr['Email']} | Plan: {plan_disp}")
                    if c_u2.button("PURGAR", key=f"del_g_{usr['Nombre']}_{i}", type="secondary"):
                        st.session_state.empleados = [e for e in st.session_state.empleados
                                                       if not (e["Nombre"] == usr["Nombre"] and e.get("Rol") == usr.get("Rol") and e.get("Empresa") == usr.get("Empresa"))]
                        guardar_datos(); st.rerun()

        with st.expander("DIRECTORIO GLOBAL DE ESCENARIOS", expanded=False):
            if not st.session_state.escenarios_custom:
                st.markdown("Sin escenarios personalizados.")
            for n_esc, d_esc in list(st.session_state.escenarios_custom.items()):
                c_e1, c_e2 = st.columns([4, 1])
                c_e1.markdown(f"**{n_esc}** | Creador: {d_esc.get('Creador','—')}")
                if c_e2.button("ELIMINAR", key=f"del_g_esc_{n_esc}", type="secondary"):
                    del st.session_state.escenarios_custom[n_esc]; guardar_datos(); st.rerun()

    with col_adm2:
        with st.expander("EMITIR CREDENCIAL DE CORTESÍA", expanded=True):
            with st.form("admin_create_user"):
                new_n     = st.text_input("ID / Entidad",   key="admin_new_n")
                new_email = st.text_input("Correo",          key="admin_new_email")
                new_pass  = st.text_input("Contraseña", type="password", key="admin_new_pass")
                new_rol   = st.selectbox("Rol", ["Individual","Empresa"], key="admin_new_rol")
                new_plan  = st.selectbox("Plan", ["BASE","OPERADOR","ELITE","ESCUADRON","COMANDANCIA"], key="admin_new_plan")
                expira    = st.checkbox("Licencia temporal (30 días)", value=False, key="admin_expira")
                if st.form_submit_button("GENERAR ACCESO", use_container_width=True):
                    if new_n and new_email and new_pass:
                        if any(e["Nombre"] == new_n for e in st.session_state.empleados):
                            st.warning("ID ya registrado.")
                        else:
                            fecha_exp_str = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d") if expira else None
                            nuevo_u = {"Nombre": new_n, "Email": new_email, "Rol": new_rol,
                                       "Plan": new_plan, "Empresa": new_n, "Password": new_pass, "2FA_Verificado": True}
                            if new_rol == "Empresa": nuevo_u["Departamento"] = "Administración"
                            if fecha_exp_str: nuevo_u["Expiracion"] = fecha_exp_str
                            st.session_state.empleados.append(nuevo_u); guardar_datos()
                            st.success(f"Cuenta '{new_n}' creada."); st.rerun()
                    else:
                        st.warning("Rellena todos los campos.")

        with st.expander("ACTIVAR / CAMBIAR PLAN", expanded=True):
            usuarios_no_admin = [e for e in st.session_state.empleados if e["Nombre"] != COMANDANTE_SUPREMO]
            if usuarios_no_admin:
                opciones_labels = [
                    f"{e['Nombre']} [{e.get('Rol','?')}] — {_legacy.get(e.get('Plan','BASE'), e.get('Plan','BASE'))}"
                    for e in usuarios_no_admin
                ]
                sel_idx = st.selectbox("Usuario:", range(len(opciones_labels)),
                                       format_func=lambda i: opciones_labels[i], key="admin_sel_usuario_v2")
                nuevo_plan_upg = st.selectbox("Nuevo Plan:", ["BASE","OPERADOR","ELITE","ESCUADRON","COMANDANCIA"],
                                              key="admin_nuevo_plan_v2")
                nueva_exp2 = st.checkbox("Añadir expiración (30 días)", value=False, key="admin_exp_check_v2")
                if st.button("APLICAR PLAN", use_container_width=True, key="btn_aplicar_plan_v2"):
                    usuario_obj    = usuarios_no_admin[sel_idx]
                    nombre_target  = usuario_obj["Nombre"]
                    rol_target     = usuario_obj.get("Rol")
                    empresa_target = usuario_obj.get("Empresa")
                    fe = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d") if nueva_exp2 else None
                    actualizado = False
                    for e in st.session_state.empleados:
                        if (e["Nombre"] == nombre_target and e.get("Rol") == rol_target and e.get("Empresa") == empresa_target):
                            e["Plan"] = nuevo_plan_upg
                            if fe: e["Expiracion"] = fe
                            elif "Expiracion" in e: del e["Expiracion"]
                            actualizado = True; break
                    if actualizado:
                        guardar_datos()
                        st.success(f"Plan de '{nombre_target}' actualizado a {nuevo_plan_upg}."); st.rerun()
                    else:
                        st.error("No se encontró el usuario.")
            else:
                st.info("No hay usuarios registrados.")

    st.markdown("<br><div class='section-label'>ZONA DE PELIGRO</div>", unsafe_allow_html=True)
    st.markdown("""<div class="alert-box error">Esta acción destruirá todos los datos de la plataforma de forma irreversible.</div>""", unsafe_allow_html=True)
    if st.button("FORMATEAR PLATAFORMA COMPLETA", use_container_width=True, key="btn_formatear"):
        st.session_state.empleados          = []
        st.session_state.historial_sesiones = []
        st.session_state.escenarios_custom  = {}
        st.session_state.usuario_actual     = None
        guardar_datos(); st.rerun()

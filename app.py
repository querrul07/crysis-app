import streamlit as st
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
    "Enterprise": "https://crysisanalitics.lemonsqueezy.com/checkout/buy/d864d72e-5ff1-4bac-966d-eafc555c5bd2",
    "Pro": "https://crysisanalitics.lemonsqueezy.com/checkout/buy/1dba647d-e120-4816-9ea0-a25492650825",
    "Individual": "https://crysisanalitics.lemonsqueezy.com/checkout/buy/adfd50b4-b2e5-40fb-9ece-30717f8828ba"
}

@st.cache_resource
def init_supabase():
    url: str = st.secrets["SUPABASE_URL"].strip().rstrip("/")
    key: str = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_supabase()

def cargar_datos():
    try:
        response = supabase.table("crysis_data").select("memoria").eq("id", "main").execute()
        if response.data:
            datos = response.data[0]["memoria"]
            if "escenarios_custom" not in datos: datos["escenarios_custom"] = {}
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
        supabase.table("crysis_data").update({"memoria": datos_actualizados}).eq("id", "main").execute()
    except Exception as e:
        st.error(f"Fallo crítico al sincronizar: {e}")

def enviar_correo_2fa(destinatario, codigo):
    try:
        remitente = st.secrets["SMTP_EMAIL"]
        password = st.secrets["SMTP_PASS"]
        msg = MIMEText(f"Tu código de autorización táctica para CRYSIS es: {codigo}\n\nSi no has solicitado este acceso, reporta una brecha de seguridad inmediatamente.")
        msg['Subject'] = 'CRYSIS | Código de Acceso 2FA'
        msg['From'] = "CRYSIS Security <no-reply@comando-crysis.net>"
        msg['To'] = destinatario
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
    texto = texto.replace('**', '').replace('*', '-').replace('•', '-').replace('✅', '[V]').replace('❌', '[X]')
    return texto.encode('latin-1', 'replace').decode('latin-1')

def generar_pdf_dossier(sesion):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.set_text_color(79, 142, 247)
    pdf.cell(0, 10, "CRYSIS | INTELLIGENCE UNIT", ln=True, align='C')
    pdf.set_font("Arial", 'B', 11); pdf.set_text_color(239, 68, 68)
    pdf.cell(0, 8, "DOSSIER OPERACIONAL CLASIFICADO", ln=True, align='C'); pdf.ln(5)
    pdf.set_font("Arial", 'B', 10); pdf.set_text_color(0, 0, 0)
    pdf.cell(45, 8, "OPERADOR:", border=1); pdf.set_font("Arial", '', 10); pdf.cell(0, 8, sanitizar_texto(sesion.get("Agente", "N/A").upper()), border=1, ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(45, 8, "FECHA:", border=1); pdf.set_font("Arial", '', 10); pdf.cell(0, 8, sanitizar_texto(sesion.get("Fecha", "N/A")), border=1, ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(45, 8, "PROTOCOLO:", border=1); pdf.set_font("Arial", '', 10); pdf.cell(0, 8, sanitizar_texto(sesion.get("Escenario", "N/A")), border=1, ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(45, 8, "EVALUACION FINAL:", border=1); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 8, f"{sesion.get('Nota', 0)}/100", border=1, ln=True); pdf.ln(10)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "1. INFORME DE EVALUACION TACTICA", ln=True); pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, sanitizar_texto(sesion.get("Evaluacion", ""))); pdf.ln(5)
    if "Transcripcion" in sesion:
        pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, "2. REGISTRO DE COMUNICACIONES", ln=True); pdf.ln(2)
        for msg in sesion["Transcripcion"]:
            ag = "OPERADOR" if msg["role"] == "user" else "OBJETIVO"
            if msg["role"] == "user": pdf.set_text_color(79, 142, 247)
            else: pdf.set_text_color(239, 68, 68)
            pdf.set_font("Arial", 'B', 10); pdf.cell(0, 6, f"{ag}:", ln=True); pdf.set_text_color(50, 50, 50); pdf.set_font("Arial", '', 10)
            pdf.multi_cell(0, 6, sanitizar_texto(msg["content"])); pdf.ln(2)
    out = pdf.output(dest='S')
    return out.encode('latin-1') if type(out) == str else out

# ─────────────────────────────────────────
# CONFIG Y CSS
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

/* ── SCANLINE OVERLAY ── */
.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px);
  pointer-events: none;
  z-index: 9999;
}

/* ── LOGIN SCREEN ── */
.login-shell {
  min-height: 92vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}
.login-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  max-width: 900px;
  width: 100%;
  border: 1px solid var(--border2);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}
.login-brand {
  background: linear-gradient(160deg, #070C1F 0%, #0A1230 100%);
  padding: 60px 48px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  overflow: hidden;
  border-right: 1px solid var(--border2);
}
.login-brand::before {
  content: '';
  position: absolute;
  top: -60px; right: -60px;
  width: 300px; height: 300px;
  border-radius: 50%;
  border: 1px solid rgba(79,142,247,0.08);
  box-shadow: inset 0 0 60px rgba(79,142,247,0.04);
}
.login-brand::after {
  content: '';
  position: absolute;
  bottom: -40px; left: -40px;
  width: 200px; height: 200px;
  border-radius: 50%;
  border: 1px solid rgba(79,142,247,0.05);
}
.brand-wordmark {
  font-family: var(--mono);
  font-size: 4rem;
  letter-spacing: 0.3em;
  color: var(--text-hi);
  line-height: 1;
  margin-bottom: 12px;
  text-shadow: 0 0 60px rgba(79,142,247,0.2);
}
.brand-sub {
  font-family: var(--mono);
  font-size: 0.55rem;
  letter-spacing: 0.4em;
  color: var(--blue);
  margin-bottom: 40px;
}
.brand-line { width: 40px; height: 2px; background: var(--blue); margin-bottom: 24px; }
.brand-desc {
  font-size: 0.78rem;
  color: var(--text-lo);
  line-height: 1.7;
  letter-spacing: 0.02em;
  font-family: var(--mono);
}
.brand-version {
  font-family: var(--mono);
  font-size: 0.5rem;
  letter-spacing: 0.25em;
  color: var(--text-lo);
}
.login-form-panel {
  background: var(--bg2);
  padding: 52px 44px;
}
.login-mode-toggle {
  display: flex;
  margin-bottom: 36px;
  border-bottom: 1px solid var(--border);
}
.mode-btn {
  font-family: var(--mono);
  font-size: 0.62rem;
  letter-spacing: 0.2em;
  padding: 10px 20px;
  cursor: pointer;
  color: var(--text-lo);
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  background: none;
  border-top: none;
  border-left: none;
  border-right: none;
  margin-bottom: -1px;
}
.mode-btn.active { color: var(--blue); border-bottom-color: var(--blue); }
.form-label {
  font-family: var(--mono);
  font-size: 0.55rem;
  letter-spacing: 0.25em;
  color: var(--blue);
  margin-bottom: 6px;
  display: block;
}
.tier-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 24px; }
.tier-card {
  border: 1px solid var(--border);
  padding: 14px 16px;
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg3);
  position: relative;
}
.tier-card:hover { border-color: var(--blue); }
.tier-card.selected { border-color: var(--blue); background: var(--blue-dim); }
.tier-card.elite.selected { border-color: var(--amber); background: rgba(240,165,0,0.08); }
.tier-name { font-family: var(--mono); font-size: 0.6rem; letter-spacing: 0.15em; color: var(--text-hi); }
.tier-price { font-size: 0.75rem; color: var(--blue); font-weight: 700; margin-top: 4px; }
.tier-card.elite .tier-price { color: var(--amber); }

/* ── TOPBAR ── */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0 12px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0;
}
.topbar-brand { font-family: var(--mono); font-size: 1.1rem; letter-spacing: 0.3em; color: var(--text-hi); }
.topbar-meta { font-family: var(--mono); font-size: 0.55rem; letter-spacing: 0.2em; color: var(--text-lo); margin-top: 3px; }
.topbar-right { display: flex; align-items: center; gap: 20px; }
.back-btn {
  font-family: var(--mono);
  font-size: 0.58rem;
  letter-spacing: 0.2em;
  color: var(--text-lo);
  cursor: pointer;
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: 2px;
  transition: all 0.15s;
  background: none;
  text-decoration: none;
}
.back-btn:hover { color: var(--text-hi); border-color: var(--border2); }

/* ── COMMAND CENTER MENU ── */
.hq-header {
  padding: 56px 0 40px 0;
  text-align: center;
}
.hq-label {
  font-family: var(--mono);
  font-size: 0.55rem;
  letter-spacing: 0.4em;
  color: var(--blue);
  margin-bottom: 12px;
}
.hq-greeting {
  font-size: 2.4rem;
  font-weight: 800;
  color: var(--text-hi);
  letter-spacing: -0.01em;
  margin-bottom: 6px;
}
.hq-date {
  font-family: var(--mono);
  font-size: 0.6rem;
  letter-spacing: 0.25em;
  color: var(--text-lo);
}
.module-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 0 0 16px 0; }
.module-grid-bottom { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 40px; }
.module-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 32px 28px;
  position: relative;
  overflow: hidden;
  transition: all 0.25s;
  cursor: pointer;
  text-decoration: none;
  display: block;
}
.module-card:hover { border-color: var(--border2); background: var(--bg3); transform: translateY(-2px); box-shadow: 0 8px 40px rgba(0,0,0,0.4); }
.module-card.primary:hover { border-color: var(--blue); box-shadow: 0 8px 40px rgba(79,142,247,0.1); }
.module-card.danger:hover { border-color: var(--red); box-shadow: 0 8px 40px rgba(232,57,74,0.1); }
.module-card.gold:hover { border-color: var(--amber); box-shadow: 0 8px 40px rgba(240,165,0,0.1); }
.module-accent {
  position: absolute;
  top: 0; left: 0;
  width: 3px; height: 100%;
  background: var(--border2);
  transition: background 0.25s;
}
.module-card.primary .module-accent { background: var(--blue); }
.module-card.danger .module-accent { background: var(--red); }
.module-card.gold .module-accent { background: var(--amber); }
.module-code {
  font-family: var(--mono);
  font-size: 0.52rem;
  letter-spacing: 0.3em;
  color: var(--text-lo);
  margin-bottom: 18px;
}
.module-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-hi);
  letter-spacing: 0.02em;
  margin-bottom: 8px;
}
.module-desc {
  font-family: var(--mono);
  font-size: 0.62rem;
  color: var(--text-lo);
  line-height: 1.6;
  letter-spacing: 0.05em;
}
.module-stat {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.module-stat-value {
  font-family: var(--mono);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-hi);
}
.module-stat-label {
  font-family: var(--mono);
  font-size: 0.5rem;
  letter-spacing: 0.2em;
  color: var(--text-lo);
}
.module-card.primary .module-stat-value { color: var(--blue); }
.module-card.danger .module-stat-value { color: var(--red); }
.module-card.gold .module-stat-value { color: var(--amber); }

/* ── SECTION HEADER ── */
.section-header {
  padding: 28px 0 24px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 32px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}
.section-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-hi);
  letter-spacing: 0.02em;
}
.section-code {
  font-family: var(--mono);
  font-size: 0.52rem;
  letter-spacing: 0.3em;
  color: var(--text-lo);
  margin-bottom: 4px;
}

/* ── METRIC CARDS ── */
.metric-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 24px;
  position: relative;
  overflow: hidden;
}
.metric-card::before { content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: var(--blue); }
.metric-label { font-family: var(--mono); font-size: 0.52rem; letter-spacing: 0.22em; color: var(--blue); margin-bottom: 10px; }
.metric-value { font-family: var(--mono); font-size: 2rem; font-weight: 700; color: var(--text-hi); line-height: 1; }

/* ── MISC ── */
.briefing-box { background: var(--bg2); border: 1px solid var(--border); border-left: 3px solid var(--blue); padding: 20px 24px; border-radius: 2px; margin-bottom: 20px; }
.briefing-box h4 { font-family: var(--mono); font-size: 0.58rem; letter-spacing: 0.2em; color: var(--blue); margin-bottom: 12px; }
.section-label { font-family: var(--mono); font-size: 0.55rem; letter-spacing: 0.25em; color: var(--blue); margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.status-bar { background: var(--bg2); border: 1px solid var(--border); border-left: 3px solid var(--green); padding: 10px 18px; border-radius: 2px; font-family: var(--mono); font-size: 0.62rem; letter-spacing: 0.12em; color: var(--green); margin-bottom: 20px; }

/* ── INPUTS ── */
.stTextInput input, .stSelectbox > div > div, .stTextArea textarea {
  background: var(--bg3) !important; border: 1px solid var(--border2) !important;
  color: var(--text) !important; border-radius: 2px !important; font-family: var(--sans) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--blue) !important; box-shadow: 0 0 0 2px rgba(79,142,247,0.08) !important; }
.stButton > button {
  background: var(--blue) !important; color: var(--bg) !important;
  font-family: var(--mono) !important; font-size: 0.65rem !important; font-weight: 700 !important;
  letter-spacing: 0.2em !important; border: none !important; border-radius: 2px !important;
  padding: 12px 28px !important; transition: all 0.2s !important;
}
.stButton > button:hover { background: #3A7AE4 !important; box-shadow: 0 0 24px rgba(79,142,247,0.25) !important; transform: translateY(-1px); }
[data-testid="stButton"] button[disabled] { background: var(--border) !important; color: var(--text-lo) !important; box-shadow: none !important; }

/* ── PLAN CARDS ── */
.auth-matrix { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 28px; }
.auth-tier { background: var(--bg3); border: 1px solid var(--border); border-left: 3px solid var(--border2); padding: 20px; border-radius: 2px; transition: border-color 0.2s; }
.auth-tier:hover { border-left-color: var(--blue); }
.auth-tier.elite { border-left-color: var(--amber); }
.tier-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
.tier-spec { font-size: 0.75rem; color: #8B9CC8; margin-bottom: 6px; display: flex; align-items: center; }
.tier-spec::before { content: '—'; margin-right: 8px; color: var(--blue); font-size: 0.6rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# DATOS BASE
# ─────────────────────────────────────────
INSTRUCCION_ORTOGRAFIA = " Escribe en español correcto. Nunca uses acotaciones entre paréntesis. Solo diálogo."
CONTEXTOS_MISION = {
    "OPERACION: FRONTERA": {"contexto": "Tensiones militares en el paralelo 38.", "perfil_sujeto": "Ministro Volkov.", "objetivo": "Evitar la escalada bélica.", "prompt": "Eres el Ministro de Defensa de Krasnovia. Hostil y burocrático. Solo diálogo directo." + INSTRUCCION_ORTOGRAFIA},
    "OPERACION: BLACKOUT": {"contexto": "Ataque masivo al sistema eléctrico nacional. Rescate exigido.", "perfil_sujeto": "'Shadow'. Hacker mercenario. Frío y calculador.", "objetivo": "Ganar tiempo para localizar el origen del ataque.", "prompt": "Eres Shadow, hacker de elite acorralado. Solo texto directo. Sin emociones." + INSTRUCCION_ORTOGRAFIA},
    "OPERACION: EXTRACCION": {"contexto": "Robo a banco fallido. 3 civiles retenidos.", "perfil_sujeto": "Sujeto inestable, bajo presión extrema.", "objetivo": "Asegurar la liberación de rehenes.", "prompt": "Eres un secuestrador acorralado. Gritas, estás nervioso. Solo diálogo crudo." + INSTRUCCION_ORTOGRAFIA}
}
PLOTLY_THEME = dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family='Syne', color='#8B9CC8', size=12), margin=dict(l=16, r=16, t=40, b=16))
AXIS_STYLE = dict(gridcolor='#1A2035', zeroline=False, color='#4A5568', linecolor='#1A2035')

# ─────────────────────────────────────────
# CARGA DE MEMORIA Y ESTADOS
# ─────────────────────────────────────────
datos_guardados = cargar_datos()
if "empleados" not in st.session_state: st.session_state.empleados = datos_guardados["empleados"]
if "historial_sesiones" not in st.session_state: st.session_state.historial_sesiones = datos_guardados["historial_sesiones"]
if "escenarios_custom" not in st.session_state: st.session_state.escenarios_custom = datos_guardados.get("escenarios_custom", {})
if "mensajes" not in st.session_state: st.session_state.mensajes = []
if "evaluacion_actual" not in st.session_state: st.session_state.evaluacion_actual = None
if "mision_iniciada" not in st.session_state: st.session_state.mision_iniciada = False
if "tarjeta_objetivo" not in st.session_state: st.session_state.tarjeta_objetivo = None
if "usuario_actual" not in st.session_state: st.session_state.usuario_actual = None
if "login_step" not in st.session_state: st.session_state.login_step = 1
if "pantalla_actual" not in st.session_state: st.session_state.pantalla_actual = "menu"
if "login_modo" not in st.session_state: st.session_state.login_modo = "acceso"

try: GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except: GROQ_API_KEY = None

# ─────────────────────────────────────────
# LOGIN REDISEÑADO
# ─────────────────────────────────────────
token_invitacion = st.query_params.get("invite", None)
empresa_invitada = None
if token_invitacion:
    try: empresa_invitada = base64.urlsafe_b64decode(token_invitacion.encode()).decode()
    except: pass

if st.session_state.usuario_actual is None:

    # ── FLUJO INVITACIÓN (agente de empresa) ──────────────────────────
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
                agentes_actuales = len([e for e in st.session_state.empleados if e.get("Empresa") == empresa_invitada and e.get("Rol") == "Agente"])
                plan_emp = empresa_obj.get("Plan", "Gratis")
                limite_agentes = 9999 if plan_emp == "Enterprise" else (15 if plan_emp == "Pro" else 0)
                if agentes_actuales >= limite_agentes:
                    st.error("ACCESO DENEGADO: Esta unidad no posee licencia corporativa activa o ha alcanzado su límite de efectivos.")
                    st.stop()
            with st.form("reg_agente"):
                st.markdown("<div class='section-label'>SOLICITUD DE CREDENCIALES DE AGENTE</div>", unsafe_allow_html=True)
                n = st.text_input("Identificador de Agente (ID)")
                email = st.text_input("Correo Corporativo")
                d = st.text_input("Unidad / Departamento")
                p = st.text_input("Establecer Clave de Acceso", type="password")
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

    # ── PANTALLA DE LOGIN PRINCIPAL ───────────────────────────────────
    if st.session_state.get("registro_completado"):
        st.success("Acreditación procesada. Identifícate en el portal de acceso.")
        st.session_state.registro_completado = False

    # Layout split: brand | form
    col_brand, col_form = st.columns([1, 1])

    with col_brand:
        st.markdown("""
        <div style="padding: 80px 40px 80px 20px; min-height: 80vh; display: flex; flex-direction: column; justify-content: space-between; border-right: 1px solid #18213A;">
            <div>
                <div class="brand-wordmark">CRYSIS</div>
                <div class="brand-sub">INTELLIGENCE UNIT</div>
                <div class="brand-line"></div>
                <div class="brand-desc">
                    Plataforma de simulación táctica avanzada para el entrenamiento en negociación, desescalada y comunicación bajo presión extrema.
                </div>
            </div>
            <div>
                <div style="font-family:var(--mono); font-size:0.5rem; letter-spacing:0.3em; color:#18213A; margin-bottom:8px;">ESTADO DEL SISTEMA</div>
                <div style="font-family:var(--mono); font-size:0.58rem; color:#00D4A0; letter-spacing:0.15em;">OPERATIVO · ACCESO SEGURO</div>
                <div style="margin-top:16px; font-family:var(--mono); font-size:0.48rem; letter-spacing:0.25em; color:#18213A;">v2.4.1 · CLASIFICADO</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_form:
        st.markdown("<div style='padding: 60px 20px 60px 40px;'>", unsafe_allow_html=True)

        # Toggle ACCESO / REGISTRO
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

        # ── MODO ACCESO ─────────────────────────────────────
        if st.session_state.login_modo == "acceso":
            if st.session_state.login_step == 1:
                with st.form("login_form"):
                    st.markdown("<div class='section-label'>IDENTIFICACIÓN DE OPERADOR</div>", unsafe_allow_html=True)
                    u_id = st.text_input("ID Operativo")
                    u_pass = st.text_input("Clave de Seguridad", type="password")
                    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                    if st.form_submit_button("INICIAR SESION SEGURA", use_container_width=True):
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
                                    st.session_state["2fa_code"] = str(random.randint(100000, 999999))
                                    st.session_state["2fa_agente"] = agente
                                    st.session_state.login_step = 2; st.rerun()
                        else:
                            st.error("Identificación fallida. Verifica tu ID o contraseña.")

            elif st.session_state.login_step == 2:
                correo_dest = st.session_state["2fa_agente"].get("Email", "Desconocido")
                if "correo_enviado" not in st.session_state:
                    exito = enviar_correo_2fa(correo_dest, st.session_state["2fa_code"])
                    if exito: st.success(f"Código enviado a: {correo_dest}")
                    else: st.error("Fallo en el sistema de correo seguro.")
                    st.session_state["correo_enviado"] = True
                with st.form("2fa_form"):
                    st.markdown("<div class='section-label'>VERIFICACION DE DISPOSITIVO</div>", unsafe_allow_html=True)
                    st.info("Autenticación de dos factores requerida (solo primera vez).")
                    u_code = st.text_input("Código de Validación")
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

        # ── MODO REGISTRO ────────────────────────────────────
        else:
            if st.session_state.get("mostrar_pago"):
                info_pago = st.session_state.mostrar_pago
                st.success(f"Cuenta creada con Nivel BASE. Completa el pago para activar tu plan.")
                st.markdown(f"""
                <div style="background:var(--bg3); border:1px solid var(--amber); border-left:3px solid var(--amber); padding:20px; border-radius:2px; margin-bottom:16px;">
                    <div style="font-family:var(--mono); font-size:0.58rem; letter-spacing:0.2em; color:var(--amber); margin-bottom:10px;">ACTIVACION DE PLAN PENDIENTE</div>
                    <p style="color:var(--text); font-size:0.82rem; margin-bottom:14px;">Cuenta <b style='color:var(--text-hi)'>{info_pago['id']}</b> creada con Nivel BASE. Tras el pago, el administrador activará tu plan en máximo 24h.</p>
                    <a href="{info_pago['link']}" target="_blank" style="display:inline-block; background:var(--amber); color:#060810; font-family:var(--mono); font-weight:700; font-size:0.65rem; letter-spacing:0.1em; padding:10px 20px; border-radius:2px; text-decoration:none;">IR AL PAGO — {info_pago['plan']}</a>
                </div>
                """, unsafe_allow_html=True)
                if st.button("ENTRAR CON NIVEL BASE", use_container_width=True):
                    st.session_state.usuario_actual = info_pago["usuario"]
                    st.session_state.pantalla_actual = "menu"
                    del st.session_state.mostrar_pago; st.rerun()
            else:
                # Selector de plan visual
                st.markdown("<div class='section-label'>SELECCIONAR NIVEL DE ACCESO</div>", unsafe_allow_html=True)
                planes = [
                    ("BASE", "0 €", "1 usuario · 1 op/mes", False, False),
                    ("OPERADOR", "29 €/mes", "Individual · ilimitado", False, False),
                    ("ESCUADRON", "89 €/mes", "15 agentes · corporativo", True, False),
                    ("COMANDANCIA", "199 €/mes", "Ilimitado · enterprise", True, True),
                ]
                if "plan_sel_reg" not in st.session_state: st.session_state.plan_sel_reg = "BASE"

                col1, col2 = st.columns(2)
                for i, (nombre, precio, desc, corp, elite) in enumerate(planes):
                    col = col1 if i % 2 == 0 else col2
                    with col:
                        is_sel = st.session_state.plan_sel_reg == nombre
                        border_col = "#F0A500" if elite and is_sel else ("#4F8EF7" if is_sel else "#18213A")
                        bg_col = "rgba(240,165,0,0.08)" if elite and is_sel else ("rgba(79,142,247,0.1)" if is_sel else "#101525")
                        st.markdown(f"""
                        <div style="border:1px solid {border_col}; background:{bg_col}; padding:14px 16px; border-radius:2px; margin-bottom:8px; cursor:pointer;">
                            <div style="font-family:var(--mono); font-size:0.6rem; letter-spacing:0.15em; color:var(--text-hi);">{nombre}</div>
                            <div style="font-size:0.85rem; color:{'#F0A500' if elite else '#4F8EF7'}; font-weight:700; margin-top:4px;">{precio}</div>
                            <div style="font-family:var(--mono); font-size:0.52rem; color:var(--text-lo); margin-top:4px;">{desc}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"Seleccionar {nombre}", key=f"plan_{nombre}", use_container_width=True):
                            st.session_state.plan_sel_reg = nombre; st.rerun()

                plan_sel = st.session_state.plan_sel_reg
                es_corporativo = plan_sel in ["ESCUADRON", "COMANDANCIA"]
                es_pago = plan_sel != "BASE"

                st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
                with st.form("registro_form"):
                    st.markdown("<div class='section-label'>DATOS DE ACCESO</div>", unsafe_allow_html=True)
                    lbl_id = "Identificador de la Entidad (Empresa)" if es_corporativo else "Identificador Personal (Alias)"
                    n = st.text_input(lbl_id)
                    email = st.text_input("Correo de Contacto")
                    p = st.text_input("Clave Maestra", type="password")
                    lbl_btn = "CREAR CUENTA E IR AL PAGO" if es_pago else "CREAR CUENTA Y ENTRAR"
                    if st.form_submit_button(lbl_btn, use_container_width=True):
                        if n and p and email:
                            empresa_destino = n if es_corporativo else "Independiente"
                            if any(e["Nombre"] == n and e.get("Empresa", "Independiente") == empresa_destino for e in st.session_state.empleados):
                                st.warning("Ya existe una cuenta con ese identificador.")
                            elif any(e["Nombre"] == n and e.get("Password") == p for e in st.session_state.empleados):
                                st.warning("ID ya en uso con esa contraseña. Usa una contraseña diferente.")
                            else:
                                if es_corporativo:
                                    nuevo_usuario = {"Nombre": n, "Email": email, "Departamento": "Administración", "Rol": "Empresa", "Plan": "Gratis", "Empresa": n, "Password": p, "2FA_Verificado": True}
                                else:
                                    nuevo_usuario = {"Nombre": n, "Email": email, "Rol": "Individual", "Plan": "Gratis", "Empresa": n, "Password": p, "2FA_Verificado": True}
                                st.session_state.empleados.append(nuevo_usuario); guardar_datos()
                                if es_pago:
                                    if "OPERADOR" in plan_sel: link_pago = LINKS_PAGO["Individual"]; nombre_plan = "OPERADOR (29€/mes)"
                                    elif "ESCUADRON" in plan_sel: link_pago = LINKS_PAGO["Pro"]; nombre_plan = "ESCUADRON (89€/mes)"
                                    else: link_pago = LINKS_PAGO["Enterprise"]; nombre_plan = "COMANDANCIA (199€/mes)"
                                    st.session_state.mostrar_pago = {"id": n, "link": link_pago, "plan": nombre_plan, "usuario": nuevo_usuario}
                                    st.rerun()
                                else:
                                    st.session_state.usuario_actual = nuevo_usuario
                                    st.session_state.pantalla_actual = "menu"; st.rerun()
                        else:
                            st.warning("Información incompleta. Rellena todos los campos.")

        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# ─────────────────────────────────────────
# RESOLUCIÓN DE PERMISOS
# ─────────────────────────────────────────
u = st.session_state.usuario_actual

if u["Nombre"] == COMANDANTE_SUPREMO:
    es_empresa = True; mi_plan = "Enterprise"; empresa_actual = u["Nombre"]
else:
    es_empresa = u.get("Rol") == "Empresa"
    empresa_actual = u.get("Empresa", u["Nombre"])
    if u.get("Rol") == "Agente":
        empresa_obj = next((e for e in st.session_state.empleados if e["Rol"] == "Empresa" and e["Nombre"] == empresa_actual), None)
        mi_plan = empresa_obj.get("Plan", "Pro") if empresa_obj else "Pro"
    else: mi_plan = u.get("Plan", "Gratis")

if u["Nombre"] == COMANDANTE_SUPREMO:
    historial_visible = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]
    agentes_de_mi_empresa = [u["Nombre"]]
elif es_empresa:
    agentes_de_mi_empresa = [e["Nombre"] for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"]
    historial_visible = [s for s in st.session_state.historial_sesiones if s["Agente"] in agentes_de_mi_empresa and s.get("Tipo_Mision", "Corporativa") != "Personal"]
else:
    historial_visible = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]
    agentes_de_mi_empresa = [u["Nombre"]]

mis_escenarios = {k: v for k, v in st.session_state.escenarios_custom.items() if v.get("Creador") == empresa_actual or u["Nombre"] == COMANDANTE_SUPREMO}
TODAS_LAS_MISIONES = {**CONTEXTOS_MISION, **mis_escenarios}

# ─────────────────────────────────────────
# TOPBAR (siempre visible cuando logueado)
# ─────────────────────────────────────────
rol_label = "OMNISCIENCIA GLOBAL" if u["Nombre"] == COMANDANTE_SUPREMO else (f"SUPERVISION [{mi_plan.upper()}]" if es_empresa else f"OPERADOR · {empresa_actual.upper()} [{mi_plan.upper()}]")

col_top1, col_top2 = st.columns([8, 1])
with col_top1:
    back_label = ""
    pantalla = st.session_state.pantalla_actual
    if pantalla != "menu":
        nombres_pantalla = {"estadisticas": "ESTADISTICAS", "personal": "PERSONAL", "expedientes": "EXPEDIENTES", "simulador": "SIMULADOR", "sintesis": "SINTESIS IA", "admin": "ADMINISTRACION"}
        back_label = f"/ {nombres_pantalla.get(pantalla, pantalla.upper())}"
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
        if st.button("MENU", key="btn_menu"): st.session_state.pantalla_actual = "menu"; st.rerun()
    if st.button("SALIR", key="btn_logout", type="secondary"):
        st.session_state.usuario_actual = None; st.session_state.login_step = 1; st.session_state.pantalla_actual = "menu"; st.rerun()

# ─────────────────────────────────────────
# PANTALLA PRINCIPAL: MENU VISUAL
# ─────────────────────────────────────────
def ir_a(pantalla):
    st.session_state.pantalla_actual = pantalla
    st.rerun()

if st.session_state.pantalla_actual == "menu":
    total_ops = len(historial_visible)
    media_global = int(sum(s["Nota"] for s in historial_visible) / total_ops) if total_ops > 0 else 0
    ops_exitosas = sum(1 for s in historial_visible if s["Nota"] >= 80)
    tasa_exito = int((ops_exitosas / total_ops) * 100) if total_ops > 0 else 0
    hora_actual = datetime.now().strftime("%H:%M") + " · " + datetime.now().strftime("%d.%m.%Y")

    st.markdown(f"""
    <div class="hq-header">
        <div class="hq-label">CUARTEL GENERAL</div>
        <div class="hq-greeting">Bienvenido, {u['Nombre'].upper()}</div>
        <div class="hq-date">{hora_actual} · SISTEMA OPERATIVO</div>
    </div>
    """, unsafe_allow_html=True)

    # Fila superior de 3 módulos
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("""
        <div class="module-card primary">
            <div class="module-accent"></div>
            <div class="module-code">MOD-01 / ESTADISTICAS</div>
            <div class="module-title">Analisis de Rendimiento</div>
            <div class="module-desc">Métricas globales, histórico de desempeño y distribución de escenarios por operador.</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"<div style='font-family:var(--mono); font-size:0.55rem; letter-spacing:0.2em; color:#3A4A6A; margin-top:-8px; margin-bottom:4px;'>RENDIMIENTO MEDIO · {media_global}%</div>", unsafe_allow_html=True)
        if st.button("ACCEDER A ESTADISTICAS", key="goto_stats", use_container_width=True): ir_a("estadisticas")

    with c2:
        st.markdown("""
        <div class="module-card danger">
            <div class="module-accent"></div>
            <div class="module-code">MOD-02 / DESPLIEGUE</div>
            <div class="module-title">Simulador Tactico</div>
            <div class="module-desc">Inicia una operación de negociación táctica en tiempo real con objetivo generado por IA.</div>
        </div>
        """, unsafe_allow_html=True)
        mes_actual = datetime.now().strftime("%Y-%m")
        ops_mes = len([s for s in historial_visible if str(s.get("Fecha","")).startswith(mes_actual)])
        st.markdown(f"<div style='font-family:var(--mono); font-size:0.55rem; letter-spacing:0.2em; color:#3A4A6A; margin-top:-8px; margin-bottom:4px;'>OPERACIONES ESTE MES · {ops_mes}</div>", unsafe_allow_html=True)
        if st.button("INICIAR DESPLIEGUE", key="goto_sim", use_container_width=True): ir_a("simulador")

    with c3:
        st.markdown("""
        <div class="module-card">
            <div class="module-accent"></div>
            <div class="module-code">MOD-03 / EXPEDIENTES</div>
            <div class="module-title">Archivo Operacional</div>
            <div class="module-desc">Consulta y descarga de dossiers de sesiones anteriores con transcripciones completas.</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"<div style='font-family:var(--mono); font-size:0.55rem; letter-spacing:0.2em; color:#3A4A6A; margin-top:-8px; margin-bottom:4px;'>EXPEDIENTES TOTALES · {total_ops}</div>", unsafe_allow_html=True)
        if st.button("VER EXPEDIENTES", key="goto_exp", use_container_width=True): ir_a("expedientes")

    # Fila inferior de 2 módulos (o 3 para admin)
    if u["Nombre"] == COMANDANTE_SUPREMO:
        c4, c5, c6 = st.columns(3)
    else:
        c4, c5 = st.columns(2)

    with c4:
        st.markdown("""
        <div class="module-card">
            <div class="module-accent"></div>
            <div class="module-code">MOD-04 / PERSONAL</div>
            <div class="module-title">Gestion de Operadores</div>
            <div class="module-desc">Reclutamiento de agentes, control de accesos, enlace cifrado y ajustes de cuenta.</div>
        </div>
        """, unsafe_allow_html=True)
        agentes_activos = len([e for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"])
        st.markdown(f"<div style='font-family:var(--mono); font-size:0.55rem; letter-spacing:0.2em; color:#3A4A6A; margin-top:-8px; margin-bottom:4px;'>AGENTES ACTIVOS · {agentes_activos}</div>", unsafe_allow_html=True)
        if st.button("GESTIONAR PERSONAL", key="goto_pers", use_container_width=True): ir_a("personal")

    with c5:
        st.markdown("""
        <div class="module-card gold">
            <div class="module-accent"></div>
            <div class="module-code">MOD-05 / SINTESIS</div>
            <div class="module-title">Generacion de Escenarios</div>
            <div class="module-desc">Motor de inteligencia artificial para crear simulaciones personalizadas adaptadas a tu contexto operativo.</div>
        </div>
        """, unsafe_allow_html=True)
        escenarios_creados = len(mis_escenarios)
        st.markdown(f"<div style='font-family:var(--mono); font-size:0.55rem; letter-spacing:0.2em; color:#3A4A6A; margin-top:-8px; margin-bottom:4px;'>ESCENARIOS ACTIVOS · {escenarios_creados}</div>", unsafe_allow_html=True)
        if st.button("ACCEDER A SINTESIS", key="goto_sint", use_container_width=True): ir_a("sintesis")

    if u["Nombre"] == COMANDANTE_SUPREMO:
        with c6:
            total_clientes = len([e for e in st.session_state.empleados if e["Nombre"] != COMANDANTE_SUPREMO])
            mrr = sum({"Enterprise":199,"Pro":89,"Individual":29,"Gratis":0}.get(e.get("Plan","Gratis"),0) for e in st.session_state.empleados)
            st.markdown("""
            <div class="module-card" style="border-left-color: #E8394A;">
                <div class="module-accent" style="background:#E8394A;"></div>
                <div class="module-code">MOD-06 / ADMIN</div>
                <div class="module-title">Consola Omega</div>
                <div class="module-desc">Panel de control global. Gestion de usuarios, planes y métricas SaaS en tiempo real.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"<div style='font-family:var(--mono); font-size:0.55rem; letter-spacing:0.2em; color:#3A4A6A; margin-top:-8px; margin-bottom:4px;'>MRR ESTIMADO · {mrr}€</div>", unsafe_allow_html=True)
            if st.button("CONSOLA OMEGA", key="goto_admin", use_container_width=True): ir_a("admin")

    st.stop()

# ─────────────────────────────────────────
# PANTALLA: ESTADISTICAS
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "estadisticas":
    st.markdown("<div class='section-header'><div><div class='section-code'>MOD-01</div><div class='section-title'>Analisis de Rendimiento</div></div></div>", unsafe_allow_html=True)

    total_ops = len(historial_visible)
    media_global = int(sum(s["Nota"] for s in historial_visible) / total_ops) if total_ops > 0 else 0
    ops_exitosas = sum(1 for s in historial_visible if s["Nota"] >= 80)
    tasa_exito = int((ops_exitosas / total_ops) * 100) if total_ops > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""<div class="metric-card"><div class="metric-label">RENDIMIENTO MEDIO</div><div class="metric-value" style="color:{'#00D4A0' if media_global >= 70 else '#E8394A'}">{media_global}%</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="metric-card"><div class="metric-label">TASA DE EXCELENCIA</div><div class="metric-value" style="color:{'#00D4A0' if tasa_exito >= 50 else '#E8394A'}">{tasa_exito}%</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="metric-card"><div class="metric-label">MISIONES COMPLETADAS</div><div class="metric-value" style="color:#4F8EF7">{total_ops}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if not historial_visible:
        st.markdown("<div style='text-align:center; padding:60px; color:#18213A; font-family:var(--mono); letter-spacing:0.2em;'>SIN REGISTROS OPERACIONALES</div>", unsafe_allow_html=True)
    else:
        df = pd.DataFrame(historial_visible)
        df["Nota"] = pd.to_numeric(df["Nota"])
        col_left, col_right = st.columns(2, gap="medium")
        with col_left:
            st.markdown("<div class='section-label'>DISTRIBUCION DE ESCENARIOS</div>", unsafe_allow_html=True)
            esc_count = df["Escenario"].value_counts().reset_index()
            esc_count.columns = ["Escenario", "Count"]
            fig2 = go.Figure(go.Pie(labels=esc_count["Escenario"], values=esc_count["Count"], hole=0.65, marker=dict(colors=['#4F8EF7','#00D4A0','#F0A500'])))
            fig2.update_layout(**PLOTLY_THEME, height=280, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        with col_right:
            if es_empresa:
                st.markdown("<div class='section-label'>EVALUACION POR OPERADOR</div>", unsafe_allow_html=True)
                avg_agent = df.groupby("Agente")["Nota"].mean().reset_index()
                fig3 = go.Figure(go.Bar(x=avg_agent["Nota"], y=avg_agent["Agente"], orientation='h', marker=dict(color='#4F8EF7')))
                fig3.update_layout(**PLOTLY_THEME, height=280)
            else:
                st.markdown("<div class='section-label'>HISTORICO DE DESEMPENO</div>", unsafe_allow_html=True)
                df["Fecha_dt"] = pd.to_datetime(df["Fecha"])
                df_sorted = df.sort_values("Fecha_dt")
                fig3 = go.Figure(go.Scatter(x=df_sorted["Fecha_dt"], y=df_sorted["Nota"], mode='lines+markers', line=dict(color='#4F8EF7')))
                fig3.add_hline(y=80, line_dash="dot", line_color="#00D4A0")
                fig3.update_layout(**PLOTLY_THEME, height=280)
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────
# PANTALLA: PERSONAL
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "personal":
    st.markdown("<div class='section-header'><div><div class='section-code'>MOD-04</div><div class='section-title'>Gestion de Operadores</div></div></div>", unsafe_allow_html=True)

    if es_empresa:
        st.markdown("<div class='section-label'>ENLACE SEGURO DE RECLUTAMIENTO</div>", unsafe_allow_html=True)
        if mi_plan in ["Pro", "Enterprise"] or u["Nombre"] == COMANDANTE_SUPREMO:
            token_cifrado = base64.urlsafe_b64encode(empresa_actual.encode()).decode()
            URL_BASE_APP = "https://crysis.streamlit.app/"
            enlace_completo = f"{URL_BASE_APP}?invite={token_cifrado}"
            st.info("Comparte este enlace con tus agentes para que se incorporen automáticamente a tu unidad.")
            st.code(enlace_completo, language="html")
        else:
            st.warning("Tu nivel de licencia no permite la formación de escuadrones. Actualiza a ESCUADRON o COMANDANCIA.")

        st.markdown("<br><div class='section-label'>PLANTILLA OPERATIVA ACTIVA</div>", unsafe_allow_html=True)
        agentes_mios = [e for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"]
        if agentes_mios:
            for ag in agentes_mios:
                st.markdown(f"**{ag['Nombre']}** | Unidad: {ag.get('Departamento','—')} | Contacto: {ag['Email']}")
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("REVOCAR ACCESO DE PERSONAL"):
                ag_a_borrar = st.selectbox("Operador a revocar:", [a['Nombre'] for a in agentes_mios])
                if st.button("REVOCAR CREDENCIALES", type="primary"):
                    st.session_state.empleados = [e for e in st.session_state.empleados if e['Nombre'] != ag_a_borrar]
                    guardar_datos(); st.success(f"Operador {ag_a_borrar} revocado."); st.rerun()
        else:
            st.markdown("No hay agentes activos en esta unidad.")
    else:
        st.markdown("<div class='section-label'>ACREDITACION CONFIRMADA</div>", unsafe_allow_html=True)
        st.markdown(f"""<div class="briefing-box"><h4>DATOS DEL OPERADOR</h4><p><b>Identificador:</b> {u['Nombre']} | <b>Unidad:</b> {empresa_actual} | <b>Plan:</b> {mi_plan}</p></div>""", unsafe_allow_html=True)

    st.markdown("<br><div class='section-label'>AJUSTES DE CUENTA</div>", unsafe_allow_html=True)
    with st.expander("CAMBIAR CLAVE DE ACCESO"):
        nueva_pass = st.text_input("Nueva Contraseña", type="password")
        if st.button("ACTUALIZAR CONTRASENA"):
            if nueva_pass:
                for e in st.session_state.empleados:
                    if e["Nombre"] == u["Nombre"]: e["Password"] = nueva_pass
                st.session_state.usuario_actual["Password"] = nueva_pass
                guardar_datos(); st.success("Contraseña actualizada.")
            else: st.warning("Introduce una contraseña válida.")

    if u["Nombre"] != COMANDANTE_SUPREMO:
        st.markdown("<br><div class='section-label'>GESTION DE SUSCRIPCION</div>", unsafe_allow_html=True)
        col_p1, col_p2, col_p3 = st.columns(3)
        planes_info = [("OPERADOR", "29€/mes", "Individual", "Individual"), ("ESCUADRON", "89€/mes", "15 agentes", "Pro"), ("COMANDANCIA", "199€/mes", "Ilimitado", "Enterprise")]
        for col, (nombre, precio, desc, plan_key) in zip([col_p1, col_p2, col_p3], planes_info):
            with col:
                st.markdown(f"""<div class="metric-card" style="{'border-left-color:#F0A500' if plan_key=='Enterprise' else ''}"><div class="metric-label">{nombre}</div><div class="metric-value" style="font-size:1.2rem; color:{'#F0A500' if plan_key=='Enterprise' else '#4F8EF7'}">{precio}</div><div style="font-family:var(--mono); font-size:0.55rem; color:#3A4A6A; margin-top:8px;">{desc}</div></div>""", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                if mi_plan == plan_key: st.success("Plan activo")
                else:
                    link = LINKS_PAGO.get("Enterprise" if plan_key=="Enterprise" else ("Pro" if plan_key=="Pro" else "Individual"))
                    st.markdown(f'<a href="{link}" target="_blank"><button style="background:#4F8EF7;color:#060810;font-family:var(--mono);font-weight:700;border:none;padding:10px;border-radius:2px;cursor:pointer;width:100%;font-size:0.65rem;letter-spacing:0.1em;">ACTIVAR</button></a>', unsafe_allow_html=True)

    st.markdown("<br><div class='section-label'>ZONA DE RIESGO</div>", unsafe_allow_html=True)
    if st.button("ELIMINAR MI CUENTA DEFINITIVAMENTE", type="primary"):
        if es_empresa: st.session_state.empleados = [e for e in st.session_state.empleados if e.get("Empresa") != u["Nombre"]]
        else: st.session_state.empleados = [e for e in st.session_state.empleados if e["Nombre"] != u["Nombre"]]
        st.session_state.usuario_actual = None; guardar_datos(); st.rerun()

# ─────────────────────────────────────────
# PANTALLA: EXPEDIENTES
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "expedientes":
    st.markdown("<div class='section-header'><div><div class='section-code'>MOD-03</div><div class='section-title'>Archivo Operacional</div></div></div>", unsafe_allow_html=True)
    if historial_visible:
        df_hist = pd.DataFrame(historial_visible)
        df_hist["Nota"] = pd.to_numeric(df_hist["Nota"])
        for agente, df_agente in df_hist.groupby("Agente"):
            media_agente = int(df_agente["Nota"].mean())
            with st.expander(f"OPERADOR: {agente.upper()}  —  METRICA GLOBAL: {media_agente}%", expanded=False):
                st.markdown("<br>", unsafe_allow_html=True)
                for escenario, df_op in df_agente.groupby("Escenario"):
                    media_op = int(df_op["Nota"].mean())
                    lbl_esc = escenario.replace("OPERACION: ", "")
                    with st.expander(f"{lbl_esc}  —  Evaluacion Media: {media_op}%", expanded=True):
                        for _, s in df_op.sort_values("Fecha", ascending=False).iterrows():
                            nota_ind = s['Nota']
                            c_nota = "#00D4A0" if nota_ind >= 80 else ("#F0A500" if nota_ind >= 50 else "#E8394A")
                            modo_badge = "PRIVADO" if s.get("Tipo_Mision") == "Personal" else "OFICIAL"
                            st.markdown(f"""<div style="border-bottom: 1px solid #18213A; padding: 12px 0; margin-bottom: 12px;">
                            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                                <span style="color:#3A4A6A; font-size:0.8rem; font-family:var(--mono);">{s['Fecha']} · {modo_badge}</span>
                                <span style="font-family:var(--mono); color:{c_nota}; font-weight:700;">{nota_ind}%</span>
                            </div>
                            <div style="font-size:0.85rem; color:#B8C4DC; margin-bottom:10px;">{s['Evaluacion']}</div>""", unsafe_allow_html=True)
                            st.download_button(label="EXTRAER DOSSIER PDF", data=generar_pdf_dossier(s), file_name=f"CRYSIS_{s['Agente']}_{s['Fecha'][:10]}.pdf", mime="application/pdf", key=f"pdf_{s['Agente']}_{s['Fecha']}")
                            if es_empresa and mi_plan == "Enterprise" and "Transcripcion" in s:
                                st.markdown("<br><span style='color:#F0A500; font-size:0.65rem; font-family:var(--mono); letter-spacing:0.1em;'>AUDITORIA DE COMUNICACIONES</span>", unsafe_allow_html=True)
                                for tr in s["Transcripcion"]:
                                    ag_tr = "OPERADOR" if tr["role"] == "user" else "SUJETO"
                                    colr = "#4F8EF7" if tr["role"] == "user" else "#E8394A"
                                    st.markdown(f"<div style='font-size:0.8rem; margin-bottom:4px;'><b style='color:{colr}'>{ag_tr}:</b> <span style='color:#3A4A6A'>{tr['content']}</span></div>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center; padding:60px; color:#18213A; font-family:var(--mono);'>DIRECTORIO VACIO</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# PANTALLA: SIMULADOR
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "simulador":
    st.markdown("<div class='section-header'><div><div class='section-code'>MOD-02</div><div class='section-title'>Simulador Tactico</div></div></div>", unsafe_allow_html=True)

    if not st.session_state.mision_iniciada:
        c1, c2 = st.columns(2)
        ag_sel = c1.selectbox("Asignar Operador:", agentes_de_mi_empresa) if es_empresa else c1.text_input("Operador:", value=u["Nombre"], disabled=True)
        if ag_sel is None and es_empresa: ag_sel = u["Nombre"]
        es_sel = c2.selectbox("Seleccionar Protocolo:", list(TODAS_LAS_MISIONES.keys()))

        if u.get("Rol") == "Agente":
            st.markdown("<br>", unsafe_allow_html=True)
            tipo_despliegue = st.radio("Nivel de Privacidad:", ["Mision Oficial (Auditable por el Mando)", "Entrenamiento Privado (Oculto en expediente corporativo)"], horizontal=True)
            tipo_mision_val = "Corporativa" if "Oficial" in tipo_despliegue else "Personal"
        else: tipo_mision_val = "Personal"

        info = TODAS_LAS_MISIONES[es_sel]
        st.markdown(f"""<div class="briefing-box"><h4>REPORTE DE SITUACION</h4><p><b>Contexto:</b> {info['contexto']}</p><p><b>Perfil:</b> {info['perfil_sujeto']}</p><p><b>Directiva:</b> {info['objetivo']}</p></div>""", unsafe_allow_html=True)

        mes_actual = datetime.now().strftime("%Y-%m")
        ops_este_mes = len([s for s in st.session_state.historial_sesiones if s["Agente"] == ag_sel and str(s.get("Fecha", "")).startswith(mes_actual)])

        bloquear_inicio = False
        if mi_plan == "Gratis" and ops_este_mes >= 1:
            bloquear_inicio = True; st.error("AUTORIZACION DENEGADA: Cuota del Nivel BASE superada.")
        elif mi_plan == "Pro" and ops_este_mes >= 3:
            bloquear_inicio = True; st.error(f"AUTORIZACION DENEGADA: Cuota del Nivel ESCUADRON superada para {ag_sel}.")

        if st.button("INICIAR ENLACE DE COMUNICACION", use_container_width=True, disabled=bloquear_inicio):
            if GROQ_API_KEY:
                with st.spinner("Estableciendo conexión segura..."):
                    try:
                        client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                        json_prompt = f"Genera para {info['perfil_sujeto']} EXCLUSIVAMENTE JSON PLANO con 3 claves: 'Nombre_Completo', 'Familia', 'Estado_Mental'."
                        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": json_prompt}], response_format={"type": "json_object"}).choices[0].message.content
                        st.session_state.tarjeta_objetivo = json.loads(res)
                    except: st.session_state.tarjeta_objetivo = {"Nombre_Completo": "Desconocido", "Familia": "Clasificado", "Estado_Mental": "Inestable"}
            st.session_state.mision_iniciada = True; st.session_state.mensajes = []; st.session_state.agente_activo = ag_sel; st.session_state.escenario_activo = es_sel; st.session_state.tipo_mision_actual = tipo_mision_val; st.rerun()

    elif st.session_state.evaluacion_actual:
        st.markdown("<div class='section-label'>INFORME DE EVALUACION TACTICA</div>", unsafe_allow_html=True)
        st.markdown(st.session_state.evaluacion_actual)
        st.markdown("<br>", unsafe_allow_html=True)
        col_end1, col_end2 = st.columns(2)
        with col_end1:
            if st.button("ARCHIVAR INFORME Y VOLVER AL MENU", use_container_width=True):
                st.session_state.mision_iniciada = False; st.session_state.evaluacion_actual = None; st.session_state.mensajes = []; st.session_state.tarjeta_objetivo = None; st.session_state.pantalla_actual = "menu"; st.rerun()
        with col_end2:
            ultima_sesion = st.session_state.historial_sesiones[-1]
            st.download_button(label="DESCARGAR DOSSIER PDF", data=generar_pdf_dossier(ultima_sesion), file_name=f"CRYSIS_{ultima_sesion['Agente']}_Report.pdf", mime="application/pdf", use_container_width=True)

    else:
        st.markdown(f"<div class='status-bar'>LINEA SEGURA ACTIVA: {st.session_state.escenario_activo} — OPERADOR: {st.session_state.agente_activo.upper()}</div>", unsafe_allow_html=True)
        if st.session_state.tarjeta_objetivo:
            t = st.session_state.tarjeta_objetivo
            st.markdown(f"""<div style="display:flex; gap:15px; background:#0B0E1A; border:1px solid #18213A; border-left:3px solid #F0A500; border-radius:2px; padding:14px 20px; margin-bottom:20px;">
                <div style="flex:1;"><div style="color:#F0A500; font-size:0.52rem; font-family:var(--mono); letter-spacing:0.2em; margin-bottom:4px;">IDENTIFICACION</div><div style="color:#E2EAF8;">{str(t.get('Nombre_Completo','N/A'))}</div></div>
                <div style="flex:1;"><div style="color:#F0A500; font-size:0.52rem; font-family:var(--mono); letter-spacing:0.2em; margin-bottom:4px;">VINCULOS</div><div style="color:#B8C4DC; font-size:0.88rem;">{str(t.get('Familia','N/A'))}</div></div>
                <div style="flex:1;"><div style="color:#F0A500; font-size:0.52rem; font-family:var(--mono); letter-spacing:0.2em; margin-bottom:4px;">ESTADO CLINICO</div><div style="color:#B8C4DC; font-size:0.88rem;">{str(t.get('Estado_Mental','N/A'))}</div></div>
            </div>""", unsafe_allow_html=True)

        for m in st.session_state.mensajes:
            label = "TU" if m["role"] == "user" else "SUJETO"
            bg = "#0D1424" if m["role"] == "user" else "#0B0E1A"
            border = "#4F8EF7" if m["role"] == "user" else "#E8394A"
            align = "flex-end" if m["role"] == "user" else "flex-start"
            st.markdown(f"""<div style="display:flex; justify-content:{align}; margin-bottom:12px;"><div style="max-width:78%; background:{bg}; border:1px solid {border}22; border-left:3px solid {border}; border-radius:2px; padding:14px 18px;"><div style="font-family:var(--mono); font-size:0.52rem; letter-spacing:0.22em; color:{border}; margin-bottom:8px;">{label}</div><div style="color:#B8C4DC; font-size:0.9rem; line-height:1.6;">{m['content']}</div></div></div>""", unsafe_allow_html=True)

        if prompt := st.chat_input("Introduzca directiva de respuesta..."):
            st.session_state.mensajes.append({"role": "user", "content": prompt}); st.rerun()

        if st.session_state.mensajes and st.session_state.mensajes[-1]["role"] == "user":
            if GROQ_API_KEY:
                client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                base_prompt = TODAS_LAS_MISIONES[st.session_state.escenario_activo]["prompt"]
                if st.session_state.tarjeta_objetivo: base_prompt += f"\n\n[Tu nombre es {st.session_state.tarjeta_objetivo.get('Nombre_Completo')}. Familia: {st.session_state.tarjeta_objetivo.get('Familia')}. Estado: {st.session_state.tarjeta_objetivo.get('Estado_Mental')}.]"
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": base_prompt}] + st.session_state.mensajes).choices[0].message.content
                st.session_state.mensajes.append({"role": "assistant", "content": res}); st.rerun()

        col_end, col_abort = st.columns([3, 1])
        with col_abort:
            if st.button("ROMPER ENLACE", type="secondary", use_container_width=True):
                st.session_state.mision_iniciada = False; st.session_state.mensajes = []; st.session_state.tarjeta_objetivo = None; st.rerun()
        with col_end:
            if len(st.session_state.mensajes) > 0:
                if st.button("SOLICITAR EVALUACION TACTICA", use_container_width=True):
                    with st.spinner("Procesando auditoria lingüística..."):
                        client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                        escenario = st.session_state.escenario_activo
                        info = TODAS_LAS_MISIONES[escenario]
                        hist_txt = "\n".join([f"{'OPERADOR' if m['role']=='user' else 'SUJETO'}: {m['content']}" for m in st.session_state.mensajes])
                        eval_prompt = f"""Eres un Analista de Inteligencia y Negociación Táctica altamente estricto.
                        Evalúa el desempeño del OPERADOR en el escenario: {escenario}. Situación: {info['contexto']}.
                        TRANSCRIPCION:\n{hist_txt}\n
                        REGLAS:
                        1. NO regales puntuación por cortesía básica.
                        2. 80-100 SOLO si hay control absoluto, técnicas avanzadas y resolución impecable.
                        3. 50-70 para trabajo correcto sin técnicas profesionales.
                        4. 0-49 si cede, es manipulado, usa lenguaje amenazante o rompe protocolos.
                        Estructura: ANALISIS DE LENGUAJE / TACTICAS EMPLEADAS / ERRORES CRITICOS / VEREDICTO / COMO MEJORAR
                        PUNTUACION FINAL: XX/100"""
                        informe = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": eval_prompt}]).choices[0].message.content
                        try:
                            match = re.search(r'PUNTUACI[OÓ]N FINAL[^\d]*(\d+)\s*\/?\s*100', informe, re.IGNORECASE)
                            nota = min(int(match.group(1)), 100) if match else (min(int(re.search(r'(\d+)\s*/\s*100', informe).group(1)), 100) if re.search(r'(\d+)\s*/\s*100', informe) else 50)
                        except: nota = 50
                        st.session_state.evaluacion_actual = informe
                        st.session_state.historial_sesiones.append({"Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "Agente": st.session_state.agente_activo, "Escenario": escenario, "Nota": nota, "Evaluacion": informe, "Transcripcion": st.session_state.mensajes, "Tipo_Mision": st.session_state.tipo_mision_actual})
                        guardar_datos(); st.rerun()

# ─────────────────────────────────────────
# PANTALLA: SINTESIS IA
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "sintesis":
    st.markdown("<div class='section-header'><div><div class='section-code'>MOD-05</div><div class='section-title'>Generacion de Escenarios</div></div></div>", unsafe_allow_html=True)

    col_izq, col_der = st.columns([2, 1], gap="large")
    with col_izq:
        creados = len(mis_escenarios)
        if mis_escenarios:
            st.markdown("<div class='section-label'>ESCENARIOS ACTIVOS</div>", unsafe_allow_html=True)
            for nombre_esc, datos_esc in mis_escenarios.items():
                c_esc1, c_esc2 = st.columns([3, 1])
                c_esc1.markdown(f"<span style='color:#B8C4DC;'>{nombre_esc}</span>", unsafe_allow_html=True)
                if c_esc2.button("ELIMINAR", key=f"del_{nombre_esc}", type="secondary"):
                    del st.session_state.escenarios_custom[nombre_esc]; guardar_datos(); st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("<div class='section-label'>NUEVA SIMULACION</div>", unsafe_allow_html=True)
        if mi_plan == "Gratis" and u["Nombre"] != COMANDANTE_SUPREMO:
            st.error("RESTRICCION: El Nivel BASE no posee autorización para el uso de IA Generativa.")
            st.button("GENERAR NUEVA SIMULACION", disabled=True)
        else:
            limite_escenarios = 9999 if u["Nombre"] == COMANDANTE_SUPREMO else (3 if mi_plan == "Individual" else 1)
            if creados >= limite_escenarios:
                st.error(f"CUOTA DE SINTESIS ALCANZADA ({creados}/{limite_escenarios}). Elimina uno existente para crear otro.")
                st.button("GENERAR NUEVA SIMULACION", disabled=True)
            else:
                idea_prompt = st.text_area("Describe los parámetros del entorno táctico:", height=100)
                if st.button("GENERAR NUEVA SIMULACION", use_container_width=True):
                    if idea_prompt and GROQ_API_KEY:
                        with st.spinner("Enlazando con el motor de IA..."):
                            try:
                                client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": "Devuelve JSON: {'nombre_op': 'OPERACION: [NOMBRE]', 'contexto': '...', 'perfil_sujeto': '...', 'objetivo': '...', 'prompt': '...'}"}, {"role": "user", "content": idea_prompt}], response_format={"type": "json_object"}).choices[0].message.content
                                nuevo_esc = json.loads(res)
                                nuevo_esc["prompt"] += INSTRUCCION_ORTOGRAFIA
                                st.session_state.escenarios_custom[nuevo_esc["nombre_op"]] = {"contexto": nuevo_esc["contexto"], "perfil_sujeto": nuevo_esc["perfil_sujeto"], "objetivo": nuevo_esc["objetivo"], "prompt": nuevo_esc["prompt"], "Creador": empresa_actual}
                                guardar_datos(); st.success(f"Protocolo {nuevo_esc['nombre_op']} configurado."); st.rerun()
                            except Exception as e: st.error(f"Fallo del Motor IA: {e}")
                    elif not idea_prompt: st.warning("Escribe los parámetros base.")

    with col_der:
        st.markdown("<div class='section-label'>NIVELES DE ACCESO IA</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="auth-matrix" style="grid-template-columns:1fr;">
            <div class="auth-tier"><div class="tier-header"><span class="tier-name" style="font-family:var(--mono); font-size:0.65rem; color:#E2EAF8;">BASE</span><span style="font-family:var(--mono); font-size:0.75rem; color:#3A4A6A;">0€</span></div><div class="tier-spec">Sin acceso a IA generativa</div></div>
            <div class="auth-tier"><div class="tier-header"><span class="tier-name" style="font-family:var(--mono); font-size:0.65rem; color:#E2EAF8;">OPERADOR</span><span style="font-family:var(--mono); font-size:0.75rem; color:#4F8EF7;">29€</span></div><div class="tier-spec">3 escenarios propios</div></div>
            <div class="auth-tier elite"><div class="tier-header"><span class="tier-name" style="font-family:var(--mono); font-size:0.65rem; color:#E2EAF8;">COMANDANCIA</span><span style="font-family:var(--mono); font-size:0.75rem; color:#F0A500;">199€</span></div><div class="tier-spec">Escenarios ilimitados</div></div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# PANTALLA: ADMIN (OMEGA)
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "admin" and u["Nombre"] == COMANDANTE_SUPREMO:
    st.markdown("<div class='section-header'><div><div class='section-code'>MOD-06</div><div class='section-title'>Consola Omega — Administracion Global</div></div></div>", unsafe_allow_html=True)

    clientes_corporativos = [e for e in st.session_state.empleados if e["Rol"] == "Empresa"]
    clientes_individuales = [e for e in st.session_state.empleados if e["Rol"] == "Individual"]
    todos_clientes = clientes_corporativos + clientes_individuales
    total_enterprise = len([c for c in todos_clientes if c.get("Plan") == "Enterprise"])
    total_pro = len([c for c in todos_clientes if c.get("Plan") == "Pro"])
    total_indiv = len([c for c in todos_clientes if c.get("Plan") == "Individual"])
    mrr_estimado = (total_enterprise * 199) + (total_pro * 89) + (total_indiv * 29)
    total_agentes = len([e for e in st.session_state.empleados if e["Rol"] == "Agente"])

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.markdown(f"""<div class="metric-card" style="border-left-color:#F0A500;"><div class="metric-label" style="color:#F0A500;">MRR ESTIMADO</div><div class="metric-value">{mrr_estimado}€</div></div>""", unsafe_allow_html=True)
    col_m2.markdown(f"""<div class="metric-card"><div class="metric-label">CUENTAS DE PAGO</div><div class="metric-value">{total_enterprise + total_pro + total_indiv}</div></div>""", unsafe_allow_html=True)
    col_m3.markdown(f"""<div class="metric-card"><div class="metric-label">AGENTES DESPLEGADOS</div><div class="metric-value">{total_agentes}</div></div>""", unsafe_allow_html=True)
    col_m4.markdown(f"""<div class="metric-card"><div class="metric-label">SESIONES TOTALES</div><div class="metric-value">{len(st.session_state.historial_sesiones)}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_adm1, col_adm2 = st.columns(2, gap="large")

    with col_adm1:
        with st.expander("DIRECTORIO GLOBAL DE USUARIOS", expanded=False):
            for i, usr in enumerate(st.session_state.empleados):
                if usr["Nombre"] != COMANDANTE_SUPREMO:
                    c_u1, c_u2 = st.columns([4, 1])
                    c_u1.markdown(f"**{usr['Nombre']}** | {usr['Rol']} | {usr['Email']} | Plan: {usr.get('Plan','—')}")
                    if c_u2.button("PURGAR", key=f"del_g_{usr['Nombre']}_{i}", type="secondary"):
                        st.session_state.empleados = [e for e in st.session_state.empleados if e["Nombre"] != usr["Nombre"]]
                        guardar_datos(); st.rerun()

        with st.expander("DIRECTORIO GLOBAL DE ESCENARIOS", expanded=False):
            if not st.session_state.escenarios_custom: st.markdown("Sin escenarios personalizados.")
            for n_esc, d_esc in st.session_state.escenarios_custom.items():
                c_e1, c_e2 = st.columns([4, 1])
                c_e1.markdown(f"**{n_esc}** | Creador: {d_esc.get('Creador','—')}")
                if c_e2.button("ELIMINAR", key=f"del_g_esc_{n_esc}", type="secondary"):
                    del st.session_state.escenarios_custom[n_esc]; guardar_datos(); st.rerun()

    with col_adm2:
        with st.expander("EMITIR CREDENCIAL DE CORTESIA", expanded=True):
            with st.form("admin_create_user"):
                new_n = st.text_input("ID / Entidad")
                new_email = st.text_input("Correo")
                new_pass = st.text_input("Contraseña", type="password")
                new_rol = st.selectbox("Rol", ["Individual", "Empresa"])
                new_plan = st.selectbox("Plan", ["Gratis", "Individual", "Pro", "Enterprise"])
                expira = st.checkbox("Licencia temporal (30 dias)", value=False)
                if st.form_submit_button("GENERAR ACCESO", use_container_width=True):
                    if new_n and new_email and new_pass:
                        if any(e["Nombre"] == new_n for e in st.session_state.empleados): st.warning("ID ya registrado.")
                        else:
                            fecha_exp_str = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d") if expira else None
                            nuevo_u = {"Nombre": new_n, "Email": new_email, "Rol": new_rol, "Plan": new_plan, "Empresa": new_n, "Password": new_pass, "2FA_Verificado": True}
                            if new_rol == "Empresa": nuevo_u["Departamento"] = "Administración"
                            if fecha_exp_str: nuevo_u["Expiracion"] = fecha_exp_str
                            st.session_state.empleados.append(nuevo_u); guardar_datos(); st.success(f"Cuenta '{new_n}' creada."); st.rerun()
                    else: st.warning("Rellena todos los campos.")

        with st.expander("ACTIVAR / CAMBIAR PLAN", expanded=True):
            usuarios_no_admin = [e for e in st.session_state.empleados if e["Nombre"] != COMANDANTE_SUPREMO]
            if usuarios_no_admin:
                opciones_labels = [f"{e['Nombre']} [{e.get('Rol','?')}] — Plan actual: {e.get('Plan','Gratis')}" for e in usuarios_no_admin]
                sel_idx = st.selectbox("Usuario:", range(len(opciones_labels)), format_func=lambda i: opciones_labels[i], key="admin_sel_usuario")
                nuevo_plan_upg = st.selectbox("Nuevo Plan:", ["Gratis", "Individual", "Pro", "Enterprise"], key="admin_nuevo_plan")
                nueva_exp2 = st.checkbox("Añadir expiración (30 dias)", value=False, key="admin_exp_check")
                if st.button("APLICAR PLAN", use_container_width=True, key="btn_aplicar_plan"):
                    usuario_obj = usuarios_no_admin[sel_idx]
                    nombre_target = usuario_obj["Nombre"]
                    rol_target = usuario_obj.get("Rol")
                    empresa_target = usuario_obj.get("Empresa")
                    fe = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d") if nueva_exp2 else None
                    actualizado = False
                    for e in st.session_state.empleados:
                        if e["Nombre"] == nombre_target and e.get("Rol") == rol_target and e.get("Empresa") == empresa_target:
                            e["Plan"] = nuevo_plan_upg
                            if fe: e["Expiracion"] = fe
                            elif "Expiracion" in e: del e["Expiracion"]
                            actualizado = True
                            break
                    if actualizado:
                        guardar_datos()
                        st.success(f"Plan de '{nombre_target}' actualizado a {nuevo_plan_upg}.")
                        st.rerun()
                    else:
                        st.error("No se encontró el usuario. Recarga la página.")
            else:
                st.info("No hay usuarios registrados.")
    st.markdown("<br><div class='section-label'>ZONA DE PELIGRO</div>", unsafe_allow_html=True)
    if st.button("FORMATEAR PLATAFORMA COMPLETA", use_container_width=True):
        st.session_state.empleados = []; st.session_state.historial_sesiones = []; st.session_state.escenarios_custom = {}
        st.session_state.usuario_actual = None; guardar_datos(); st.rerun()

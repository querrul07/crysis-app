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
import urllib.parse

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
    "BASE":        {"precio": "0€",    "desc": "Individual · 1 op/mes · sin IA",     "ops": 1,    "escenarios": 0,    "agentes": 0,    "elite": False},
    "OPERADOR":    {"precio": "19€/mes","desc": "Individual · 10 ops/mes · 3 escenarios","ops": 10, "escenarios": 3,  "agentes": 0,    "elite": False},
    "ELITE":       {"precio": "49€/mes","desc": "Individual · ilimitado · IA sin límite","ops": 99999,"escenarios": 99999,"agentes": 0, "elite": True},
    "ESCUADRON":   {"precio": "89€/mes","desc": "Equipo · ilimitado · 15 agentes",    "ops": 99999,"escenarios": 99999,"agentes": 15,   "elite": True},
    "COMANDANCIA": {"precio": "199€/mes","desc": "Enterprise · ilimitado · ∞ agentes","ops": 99999,"escenarios": 99999,"agentes": 99999,"elite": True},
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

# ─────────────────────────────────────────
# CONTEXTO POR PAÍS/REGIÓN PARA IMÁGENES
# ─────────────────────────────────────────
ESCENARIO_IMAGEN_CONTEXTO = {
    "OPERACION: FRONTERA": {
        "region": "Eastern Europe, Soviet-era architecture, Krasnovia military zone",
        "estilo": "grayscale with green tint, cold war military aesthetic",
        "lugares": "military border checkpoint, watchtowers, barbed wire, snow-covered mountains, armored vehicles, Soviet-style bunkers",
    },
    "OPERACION: BLACKOUT": {
        "region": "Western European city, modern urban infrastructure",
        "estilo": "dark cyberpunk, emergency lighting, power outage aesthetic",
        "lugares": "server room, electrical grid substation, dark city skyline, emergency generators, control room monitors",
    },
    "OPERACION: EXTRACCION": {
        "region": "Mediterranean city center, Southern European urban environment",
        "estilo": "tense urban daylight, police cordon, tactical photography",
        "lugares": "bank building facade, urban street, police perimeter, civilian crowds, tactical vehicles, rooftop snipers",
    },
}

# ─────────────────────────────────────────
# PROMPTS SERVICIOS DE INTELIGENCIA
# ─────────────────────────────────────────
INTEL_PROMPTS = {
    "OPERACION: FRONTERA": """Eres el Analista Jefe de la Unidad de Inteligencia táctica (SIGINT/HUMINT) que apoya al operador en campo.
Tu misión: dar contexto sobre la situación en la frontera del paralelo 38 con Krasnovia, el perfil del Ministro Volkov, y posibles palancas de negociación.

REGLAS CRÍTICAS:
- Tienes información PARCIAL e IMPERFECTA. A veces tus datos son incompletos, desactualizados o directamente incorrectos.
- Cuando no sepas algo, dilo con frases como: "inteligencia no confirmada", "fuente no verificada", "dato de hace 6 meses".
- Nunca inventes datos con certeza total. El operador debe saber que puede haber errores.
- Responde SOLO a lo que te pregunten. No des información no solicitada.
- Tono: militar, conciso, frío. Solo texto directo. Sin emociones ni acotaciones entre paréntesis.
- Escribe en español correcto.""",

    "OPERACION: BLACKOUT": """Eres el Analista de Ciberinteligencia que apoya al operador en el caso del hacker Shadow.
Tu misión: aportar datos técnicos sobre el ataque, el perfil psicológico de Shadow, y vulnerabilidades que el operador puede explotar.

REGLAS CRÍTICAS:
- Tu información sobre Shadow es FRAGMENTADA. Solo tienes datos de operaciones anteriores, no de esta.
- Algunos datos técnicos pueden estar desactualizados o ser deliberadamente falsos (Shadow es experto en desinformación).
- Advierte siempre cuando un dato no está verificado.
- Responde SOLO a lo que te pregunten. Sin información no solicitada.
- Tono: técnico, seco, conciso. Solo texto directo.
- Escribe en español correcto.""",

    "OPERACION: EXTRACCION": """Eres el Coordinador de Inteligencia táctica que apoya al negociador en la situación de rehenes.
Tu misión: aportar datos sobre el secuestrador, el estado de los rehenes, el perímetro policial y posibles motivaciones.

REGLAS CRÍTICAS:
- Tienes acceso LIMITADO al interior del banco. Tu información llega con retraso y puede estar desactualizada.
- Los datos psicológicos del secuestrador son inferencias, no certezas.
- Advierte siempre el nivel de confianza de cada dato: ALTO / MEDIO / BAJO.
- Responde SOLO a lo que te pregunten.
- Tono: urgente pero controlado, conciso. Solo texto directo.
- Escribe en español correcto.""",
}

INTEL_PROMPT_DEFAULT = """Eres un Analista de Inteligencia táctica que apoya al operador en campo.
Tu misión: dar contexto sobre la operación activa, perfiles de sujetos y datos relevantes para la negociación.

REGLAS CRÍTICAS:
- Tu información es PARCIAL e IMPERFECTA. Nunca tienes el cuadro completo.
- Indica siempre el nivel de confianza: ALTO / MEDIO / BAJO.
- Cuando no sepas algo, dilo claramente.
- Responde SOLO a lo que te pregunten.
- Tono: militar, conciso, frío. Solo texto directo.
- Escribe en español correcto."""

# Planes con acceso a Servicios de Inteligencia
PLANES_CON_INTEL = {"ELITE", "ESCUADRON", "COMANDANCIA"}

# ─────────────────────────────────────────
# SUPABASE
# ─────────────────────────────────────────
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

# ─────────────────────────────────────────
# GENERACIÓN DE IMÁGENES — POLLINATIONS
# ─────────────────────────────────────────
def generar_url_imagen_intel(escenario, consulta_usuario, seed):
    ctx = ESCENARIO_IMAGEN_CONTEXTO.get(escenario, {
        "region": "classified military zone",
        "estilo": "grayscale tactical photography",
        "lugares": "tactical location, classified environment",
    })
    prompt = (
        f"intelligence satellite photograph or reconnaissance image, "
        f"{ctx['region']}, {ctx['lugares']}, "
        f"related to: {consulta_usuario[:100]}, "
        f"{ctx['estilo']}, "
        f"photorealistic, high detail, cinematic lighting, no text, no watermark, no people faces"
    )
    prompt_encoded = urllib.parse.quote(prompt)
    return (
        f"https://image.pollinations.ai/prompt/{prompt_encoded}"
        f"?width=800&height=450&nologo=true&seed={seed}&model=flux"
    )

def es_peticion_imagen_intel(texto):
    keywords = [
        "imagen", "foto", "fotografía", "fotografia", "satélite", "satelite",
        "reconocimiento", "visual", "muéstrame", "muestrame", "ver", "mapa",
        "plano", "vista", "captura", "snapshot", "intel visual", "imágenes",
        "fotografía aérea", "vista aérea", "show me", "mostrar"
    ]
    texto_lower = texto.lower()
    return any(k in texto_lower for k in keywords)

# ─────────────────────────────────────────
# PDF
# ─────────────────────────────────────────
def sanitizar_texto(texto):
    if not isinstance(texto, str): texto = str(texto)
    
    # 1. Traducción táctica de caracteres problemáticos comunes
    reemplazos = {
        '“': '"', '”': '"', '‘': "'", '’': "'", 
        '—': '-', '–': '-', '…': '...', 
        '•': '-', '✅': '[V]', '❌': '[X]',
        '€': 'EUR', '\u200b': '', '\ufeff': ''
    }
    for mal, bien in reemplazos.items():
        texto = texto.replace(mal, bien)
        
    texto = texto.replace('**', '').replace('*', '-')
    
    # 2. Purga nuclear: Forzamos latin-1 y ELIMINAMOS lo que no encaje (como emojis ocultos)
    # Usar 'ignore' en lugar de 'replace' evita que se cuelen símbolos extraños
    return texto.encode('latin-1', 'ignore').decode('latin-1')

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
    if sesion.get("Evaluacion_Intel"):
        pdf.set_font("Arial",'B',12); pdf.set_text_color(240,165,0)
        pdf.cell(0,8,"2. ANALISIS DE USO DE SERVICIOS DE INTELIGENCIA",ln=True)
        pdf.set_text_color(0,0,0); pdf.set_font("Arial",'',10)
        pdf.multi_cell(0,6,sanitizar_texto(sesion.get("Evaluacion_Intel",""))); pdf.ln(5)
        seccion_trans = "3"
    else:
        seccion_trans = "2"
    if "Transcripcion" in sesion:
        pdf.set_font("Arial",'B',12); pdf.set_text_color(0,0,0)
        pdf.cell(0,8,f"{seccion_trans}. REGISTRO DE COMUNICACIONES — CANAL PRINCIPAL",ln=True); pdf.ln(2)
        for msg in sesion["Transcripcion"]:
            ag = "OPERADOR" if msg["role"] == "user" else "OBJETIVO"
            if msg["role"] == "user": pdf.set_text_color(79,142,247)
            else: pdf.set_text_color(239,68,68)
            pdf.set_font("Arial",'B',10); pdf.cell(0,6,f"{ag}:",ln=True)
            pdf.set_text_color(50,50,50); pdf.set_font("Arial",'',10)
            pdf.multi_cell(0,6,sanitizar_texto(msg["content"])); pdf.ln(2)
    if sesion.get("Transcripcion_Intel"):
        sig_sec = str(int(seccion_trans) + 1)
        pdf.add_page()
        pdf.set_font("Arial",'B',12); pdf.set_text_color(240,165,0)
        pdf.cell(0,8,f"{sig_sec}. REGISTRO DE COMUNICACIONES — CANAL INTELIGENCIA",ln=True); pdf.ln(2)
        for msg in sesion["Transcripcion_Intel"]:
            ag = "OPERADOR" if msg["role"] == "user" else "INTEL"
            if msg["role"] == "user": pdf.set_text_color(240,165,0)
            else: pdf.set_text_color(130,90,200)
            pdf.set_font("Arial",'B',10); pdf.cell(0,6,f"{ag}:",ln=True)
            pdf.set_text_color(50,50,50); pdf.set_font("Arial",'',10)
            pdf.multi_cell(0,6,sanitizar_texto(msg["content"])); pdf.ln(2)
    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else out

# ─────────────────────────────────────────
# CONFIG Y CSS — REDISEÑADO
# ─────────────────────────────────────────
st.set_page_config(page_title="CRYSIS | Intelligence Unit", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Syne:wght@400;600;700;800&display=swap');

:root {
  --bg:       #060810;
  --bg2:      #0B0E1A;
  --bg3:      #101525;
  --bg4:      #141930;
  --border:   #18213A;
  --border2:  #243050;
  --blue:     #4F8EF7;
  --blue-dim: rgba(79,142,247,0.12);
  --green:    #00D4A0;
  --red:      #E8394A;
  --amber:    #F0A500;
  --purple:   #9B59B6;
  --text:     #C4CEDF;
  --text-hi:  #E8F0FA;
  --text-lo:  #3A4A6A;
  --text-mid: #7A8DAA;
  --mono:     'Share Tech Mono', monospace;
  --sans:     'Syne', sans-serif;
  --radius:   4px;
}

html, body, [class*="css"], .stApp {
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: var(--sans) !important;
  font-size: 15px !important;
}
header[data-testid="stHeader"] { background: var(--bg) !important; border-bottom: 1px solid var(--border); }
.stDeployButton, #MainMenu, footer { display: none !important; }

.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.025) 2px, rgba(0,0,0,0.025) 4px);
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
  margin-bottom: 14px;
  text-shadow: 0 0 60px rgba(79,142,247,0.2);
}
.brand-sub {
  font-family: var(--mono);
  font-size: 0.65rem;
  letter-spacing: 0.4em;
  color: var(--blue);
  margin-bottom: 44px;
}
.brand-line { width: 40px; height: 2px; background: var(--blue); margin-bottom: 28px; }
.brand-desc {
  font-size: 0.85rem;
  color: var(--text-mid);
  line-height: 1.8;
  letter-spacing: 0.01em;
  font-family: var(--mono);
}

/* ── TOPBAR ── */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 0 14px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0;
}
.topbar-brand { font-family: var(--mono); font-size: 1.15rem; letter-spacing: 0.3em; color: var(--text-hi); }
.topbar-meta  { font-family: var(--mono); font-size: 0.65rem; letter-spacing: 0.18em; color: var(--text-mid); margin-top: 4px; }

/* ── HQ HEADER ── */
.hq-header { padding: 60px 0 44px 0; text-align: center; }
.hq-label    { font-family: var(--mono); font-size: 0.65rem; letter-spacing: 0.4em; color: var(--blue); margin-bottom: 14px; }
.hq-greeting { font-size: 2.6rem; font-weight: 800; color: var(--text-hi); letter-spacing: -0.01em; margin-bottom: 8px; }
.hq-date     { font-family: var(--mono); font-size: 0.7rem; letter-spacing: 0.22em; color: var(--text-mid); }

/* ── MODULE CARDS ── */
.module-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 28px 26px 24px 26px;
  position: relative;
  overflow: hidden;
  transition: all 0.25s;
  height: 100%;
}
.module-card:hover {
  border-color: var(--border2);
  background: var(--bg3);
  transform: translateY(-3px);
  box-shadow: 0 12px 48px rgba(0,0,0,0.45);
}
.module-card.primary:hover { border-color: var(--blue);  box-shadow: 0 12px 48px rgba(79,142,247,0.12); }
.module-card.danger:hover  { border-color: var(--red);   box-shadow: 0 12px 48px rgba(232,57,74,0.12); }
.module-card.gold:hover    { border-color: var(--amber); box-shadow: 0 12px 48px rgba(240,165,0,0.12); }
.module-accent { position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: var(--border2); }
.module-card.primary .module-accent { background: var(--blue); }
.module-card.danger  .module-accent { background: var(--red); }
.module-card.gold    .module-accent { background: var(--amber); }
.module-code  { font-family: var(--mono); font-size: 0.6rem; letter-spacing: 0.28em; color: var(--text-lo); margin-bottom: 14px; }
.module-title { font-size: 1.1rem; font-weight: 700; color: var(--text-hi); letter-spacing: 0.01em; margin-bottom: 10px; }
.module-desc  { font-family: var(--mono); font-size: 0.7rem; color: var(--text-mid); line-height: 1.7; letter-spacing: 0.03em; }

/* ── SECTION HEADERS ── */
.section-header {
  padding: 32px 0 28px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 36px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}
.section-title { font-size: 1.5rem; font-weight: 700; color: var(--text-hi); letter-spacing: 0.01em; }
.section-code  { font-family: var(--mono); font-size: 0.6rem; letter-spacing: 0.28em; color: var(--text-lo); margin-bottom: 6px; }

/* ── LABELS ── */
.section-label {
  font-family: var(--mono);
  font-size: 0.62rem;
  letter-spacing: 0.22em;
  color: var(--blue);
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}

/* ── METRIC CARDS ── */
.metric-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px 22px;
  position: relative;
  overflow: hidden;
}
.metric-card::before { content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: var(--blue); }
.metric-label { font-family: var(--mono); font-size: 0.6rem; letter-spacing: 0.2em; color: var(--blue); margin-bottom: 12px; }
.metric-value { font-family: var(--mono); font-size: 2.2rem; font-weight: 700; color: var(--text-hi); line-height: 1; }

/* ── BRIEFING BOX ── */
.briefing-box {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--blue);
  padding: 22px 26px;
  border-radius: var(--radius);
  margin-bottom: 22px;
}
.briefing-box h4 {
  font-family: var(--mono);
  font-size: 0.65rem;
  letter-spacing: 0.2em;
  color: var(--blue);
  margin-bottom: 14px;
}
.briefing-box p {
  font-size: 0.92rem;
  color: var(--text);
  line-height: 1.7;
  margin-bottom: 6px;
}

/* ── STATUS BAR ── */
.status-bar {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--green);
  padding: 12px 20px;
  border-radius: var(--radius);
  font-family: var(--mono);
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  color: var(--green);
  margin-bottom: 22px;
}

/* ── INTEL CHANNEL ── */
.intel-header {
  background: #0D0A18;
  border: 1px solid #2A1A4A;
  border-left: 3px solid #F0A500;
  border-radius: var(--radius);
  padding: 12px 20px;
  font-family: var(--mono);
  font-size: 0.68rem;
  letter-spacing: 0.16em;
  color: #F0A500;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.intel-dot {
  width: 8px; height: 8px;
  background: #F0A500;
  border-radius: 50%;
  display: inline-block;
  animation: pulse-amber 1.8s infinite;
  flex-shrink: 0;
}
@keyframes pulse-amber {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.intel-badge {
  background: rgba(240,165,0,0.08);
  border: 1px solid rgba(240,165,0,0.3);
  border-radius: 2px;
  padding: 3px 10px;
  font-family: var(--mono);
  font-size: 0.55rem;
  letter-spacing: 0.16em;
  color: #F0A500;
  margin-left: auto;
}
.intel-image-container {
  border: 1px solid #2A1A4A;
  border-left: 3px solid #F0A500;
  background: #0D0A18;
  padding: 10px 14px;
  margin: 10px 0;
  border-radius: var(--radius);
}
.intel-image-label {
  font-family: var(--mono);
  font-size: 0.55rem;
  letter-spacing: 0.24em;
  color: #F0A500;
  margin-bottom: 8px;
}

/* ── CHAT COLUMNS LAYOUT ── */
.sim-col-header {
  font-family: var(--mono);
  font-size: 0.65rem;
  letter-spacing: 0.22em;
  padding: 10px 16px;
  border-radius: var(--radius) var(--radius) 0 0;
  margin-bottom: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.sim-col-header.principal {
  background: rgba(79,142,247,0.08);
  border: 1px solid rgba(79,142,247,0.25);
  border-bottom: none;
  color: #4F8EF7;
}
.sim-col-header.intel {
  background: rgba(240,165,0,0.08);
  border: 1px solid rgba(240,165,0,0.25);
  border-bottom: none;
  color: #F0A500;
}
.sim-chat-box {
  border-radius: 0 0 var(--radius) var(--radius);
  padding: 16px;
  min-height: 440px;
  max-height: 540px;
  overflow-y: auto;
}
.sim-chat-box.principal {
  background: #080C18;
  border: 1px solid rgba(79,142,247,0.2);
  border-top: none;
}
.sim-chat-box.intel {
  background: #09060F;
  border: 1px solid rgba(240,165,0,0.2);
  border-top: none;
}

/* ── DIFF CARDS ── */
.diff-card {
  border: 2px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg3);
  text-align: center;
}
.diff-card:hover { transform: translateY(-2px); }
.diff-card.selected { background: rgba(79,142,247,0.08); }
.diff-name  { font-family: var(--mono); font-size: 0.78rem; letter-spacing: 0.16em; font-weight: 700; }
.diff-desc  { font-family: var(--mono); font-size: 0.6rem; color: var(--text-mid); margin-top: 8px; line-height: 1.5; }

/* ── INPUTS ── */
.stTextInput input, .stSelectbox > div > div, .stTextArea textarea {
  background: var(--bg3) !important;
  border: 1px solid var(--border2) !important;
  color: var(--text) !important;
  border-radius: var(--radius) !important;
  font-family: var(--sans) !important;
  font-size: 0.92rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--blue) !important;
  box-shadow: 0 0 0 2px rgba(79,142,247,0.1) !important;
}
label, .stSelectbox label, .stTextInput label, .stTextArea label {
  color: var(--text-mid) !important;
  font-size: 0.82rem !important;
  font-family: var(--mono) !important;
  letter-spacing: 0.08em !important;
}

/* ── BUTTONS ── */
.stButton > button {
  background: var(--blue) !important;
  color: var(--bg) !important;
  font-family: var(--mono) !important;
  font-size: 0.7rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.18em !important;
  border: none !important;
  border-radius: var(--radius) !important;
  padding: 13px 28px !important;
  transition: all 0.2s !important;
}
.stButton > button:hover {
  background: #3A7AE4 !important;
  box-shadow: 0 0 28px rgba(79,142,247,0.28) !important;
  transform: translateY(-1px);
}
[data-testid="stButton"] button[disabled] {
  background: var(--border) !important;
  color: var(--text-lo) !important;
  box-shadow: none !important;
}

/* ── AUTH TIERS ── */
.auth-tier {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-left: 3px solid var(--border2);
  padding: 18px 20px;
  border-radius: var(--radius);
  transition: border-color 0.2s;
  margin-bottom: 10px;
}
.auth-tier:hover { border-left-color: var(--blue); }
.auth-tier.elite { border-left-color: var(--amber); }
.tier-spec {
  font-size: 0.78rem;
  color: var(--text-mid);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
}
.tier-spec::before { content: '—'; margin-right: 10px; color: var(--blue); font-size: 0.65rem; }

/* ── EXPEDIENTE CARD ── */
.exp-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 22px;
  margin-bottom: 14px;
  transition: border-color 0.2s;
}
.exp-card:hover { border-color: var(--border2); }

/* ── INTEL THUMBNAIL ── */
.intel-thumb-wrap {
  display: inline-block;
  cursor: pointer;
}
.intel-thumb-wrap img {
  width: 250px;
  height: auto;
  border-radius: var(--radius);
  border: 1px solid rgba(240,165,0,0.3);
  transition: transform 0.2s;
}
.intel-thumb-wrap img:hover { transform: scale(1.03); }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

/* ── MISC ── */
.stExpander { border: 1px solid var(--border) !important; border-radius: var(--radius) !important; background: var(--bg2) !important; }
.stExpander summary { font-size: 0.88rem !important; color: var(--text) !important; }
div[data-testid="stRadio"] label { font-size: 0.85rem !important; }
div[data-testid="stCheckbox"] label { font-size: 0.85rem !important; }
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
PLOTLY_THEME = dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family='Syne', color='#8B9CC8', size=13), margin=dict(l=16,r=16,t=40,b=16))
AXIS_STYLE   = dict(gridcolor='#1A2035', zeroline=False, color='#4A5568', linecolor='#1A2035')

# ─────────────────────────────────────────
# CARGA DE MEMORIA Y ESTADOS
# ─────────────────────────────────────────
datos_guardados = cargar_datos()
if "empleados"          not in st.session_state: st.session_state.empleados          = datos_guardados["empleados"]
if "historial_sesiones" not in st.session_state: st.session_state.historial_sesiones = datos_guardados["historial_sesiones"]
if "escenarios_custom"  not in st.session_state: st.session_state.escenarios_custom  = datos_guardados.get("escenarios_custom", {})
if "mensajes"           not in st.session_state: st.session_state.mensajes            = []
if "mensajes_intel"     not in st.session_state: st.session_state.mensajes_intel      = []
if "evaluacion_actual"  not in st.session_state: st.session_state.evaluacion_actual  = None
if "evaluacion_intel"   not in st.session_state: st.session_state.evaluacion_intel   = None
if "mision_iniciada"    not in st.session_state: st.session_state.mision_iniciada    = False
if "tarjeta_objetivo"   not in st.session_state: st.session_state.tarjeta_objetivo   = None
if "usuario_actual"     not in st.session_state: st.session_state.usuario_actual     = None
if "login_step"         not in st.session_state: st.session_state.login_step         = 1
if "pantalla_actual"    not in st.session_state: st.session_state.pantalla_actual    = "menu"
if "login_modo"         not in st.session_state: st.session_state.login_modo         = "acceso"
if "dificultad_actual"  not in st.session_state: st.session_state.dificultad_actual  = "OPERATOR"

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
                <div style="font-family:var(--mono); font-size:0.6rem; letter-spacing:0.28em; color:#18213A; margin-bottom:8px;">ESTADO DEL SISTEMA</div>
                <div style="font-family:var(--mono); font-size:0.68rem; color:#00D4A0; letter-spacing:0.14em;">OPERATIVO · ACCESO SEGURO</div>
                <div style="margin-top:16px; font-family:var(--mono); font-size:0.55rem; letter-spacing:0.24em; color:#18213A;">v3.1.0 · CLASIFICADO</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_form:
        st.markdown("<div style='padding: 60px 20px 60px 40px;'>", unsafe_allow_html=True)

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
                                    st.session_state["2fa_code"]  = str(random.randint(100000, 999999))
                                    st.session_state["2fa_agente"] = agente
                                    st.session_state.login_step = 2; st.rerun()
                        else:
                            st.error("Identificación fallida. Verifica tu ID o contraseña.")

            elif st.session_state.login_step == 2:
                correo_dest = st.session_state["2fa_agente"].get("Email", "Desconocido")
                if "correo_enviado" not in st.session_state:
                    exito = enviar_correo_2fa(correo_dest, st.session_state["2fa_code"])
                    if exito: st.success(f"Código enviado a: {correo_dest}")
                    else:     st.error("Fallo en el sistema de correo seguro.")
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

        else:
            if st.session_state.get("mostrar_pago"):
                info_pago = st.session_state.mostrar_pago
                st.markdown(f"""
                <div style="background:var(--bg3); border:1px solid var(--amber); border-left:3px solid var(--amber); padding:22px; border-radius:var(--radius); margin-bottom:18px;">
                    <div style="font-family:var(--mono); font-size:0.65rem; letter-spacing:0.18em; color:var(--amber); margin-bottom:12px;">ACTIVACION DE PLAN PENDIENTE</div>
                    <p style="color:var(--text); font-size:0.9rem; margin-bottom:16px;">Cuenta <b style='color:var(--text-hi)'>{info_pago['id']}</b> creada con Nivel BASE. Tras el pago, el administrador activará tu plan en máximo 24h.</p>
                    <a href="{info_pago['link']}" target="_blank" style="display:inline-block; background:var(--amber); color:#060810; font-family:var(--mono); font-weight:700; font-size:0.68rem; letter-spacing:0.1em; padding:12px 22px; border-radius:var(--radius); text-decoration:none;">IR AL PAGO — {info_pago['plan']}</a>
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
                    ("BASE",        "0€",      "Individual · 1 op/mes",            False),
                    ("OPERADOR",    "19€/mes", "Individual · 10 ops/mes · 3 esc.", False),
                    ("ELITE",       "49€/mes", "Individual · ilimitado · IA ∞",    True),
                    ("ESCUADRON",   "89€/mes", "Equipo · 15 agentes · ∞ ops",      True),
                    ("COMANDANCIA", "199€/mes","Enterprise · agentes ∞ · ops ∞",   True),
                ]

                col1, col2 = st.columns(2)
                for i, (nombre, precio, desc, elite) in enumerate(planes_registro):
                    col = col1 if i % 2 == 0 else col2
                    with col:
                        is_sel    = st.session_state.plan_sel_reg == nombre
                        border_col = "#F0A500" if elite and is_sel else ("#4F8EF7" if is_sel else "#18213A")
                        bg_col     = "rgba(240,165,0,0.08)" if elite and is_sel else ("rgba(79,142,247,0.1)" if is_sel else "#101525")
                        st.markdown(f"""
                        <div style="border:1px solid {border_col}; background:{bg_col}; padding:14px 16px; border-radius:var(--radius); margin-bottom:6px;">
                            <div style="font-family:var(--mono); font-size:0.68rem; letter-spacing:0.14em; color:var(--text-hi);">{nombre}</div>
                            <div style="font-size:0.95rem; color:{'#F0A500' if elite else '#4F8EF7'}; font-weight:700; margin-top:5px;">{precio}</div>
                            <div style="font-family:var(--mono); font-size:0.6rem; color:var(--text-mid); margin-top:5px;">{desc}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"Sel. {nombre}", key=f"plan_reg_{nombre}", use_container_width=True):
                            st.session_state.plan_sel_reg = nombre; st.rerun()

                plan_sel       = st.session_state.plan_sel_reg
                es_corporativo = plan_sel in ["ESCUADRON", "COMANDANCIA"]
                es_pago        = plan_sel != "BASE"

                st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
                with st.form("registro_form"):
                    st.markdown("<div class='section-label'>DATOS DE ACCESO</div>", unsafe_allow_html=True)
                    lbl_id = "Identificador de la Entidad (Empresa)" if es_corporativo else "Identificador Personal (Alias)"
                    n      = st.text_input(lbl_id)
                    email  = st.text_input("Correo de Contacto")
                    p      = st.text_input("Clave Maestra", type="password")
                    lbl_btn = "CREAR CUENTA E IR AL PAGO" if es_pago else "CREAR CUENTA Y ENTRAR"
                    if st.form_submit_button(lbl_btn, use_container_width=True):
                        if n and p and email:
                            empresa_destino = n if es_corporativo else "Independiente"
                            if any(e["Nombre"] == n and e.get("Empresa", "Independiente") == empresa_destino for e in st.session_state.empleados):
                                st.warning("Ya existe una cuenta con ese identificador.")
                            elif any(e["Nombre"] == n and e.get("Password") == p for e in st.session_state.empleados):
                                st.warning("ID ya en uso con esa contraseña.")
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
                            st.warning("Información incompleta. Rellena todos los campos.")

        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()

# ─────────────────────────────────────────
# RESOLUCIÓN DE PERMISOS
# ─────────────────────────────────────────
u = st.session_state.usuario_actual

if u["Nombre"] == COMANDANTE_SUPREMO:
    es_empresa    = True
    mi_plan       = "COMANDANCIA"
    empresa_actual = u["Nombre"]
else:
    es_empresa     = u.get("Rol") == "Empresa"
    empresa_actual = u.get("Empresa", u["Nombre"])
    if u.get("Rol") == "Agente":
        empresa_obj = next((e for e in st.session_state.empleados if e["Rol"] == "Empresa" and e["Nombre"] == empresa_actual), None)
        mi_plan = empresa_obj.get("Plan", "ESCUADRON") if empresa_obj else "ESCUADRON"
    else:
        mi_plan = u.get("Plan", "BASE")

_legacy = {"Gratis": "BASE", "Individual": "OPERADOR", "Pro": "ESCUADRON", "Enterprise": "COMANDANCIA"}
mi_plan = _legacy.get(mi_plan, mi_plan)

ops_limite      = PLANES_INFO.get(mi_plan, {}).get("ops", 1)
escenarios_lim  = PLANES_INFO.get(mi_plan, {}).get("escenarios", 0)
agentes_lim     = PLANES_INFO.get(mi_plan, {}).get("agentes", 0)

tiene_intel = (mi_plan in PLANES_CON_INTEL) or (u["Nombre"] == COMANDANTE_SUPREMO)

if u["Nombre"] == COMANDANTE_SUPREMO:
    historial_visible   = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]
    agentes_de_mi_empresa = [u["Nombre"]]
elif es_empresa:
    agentes_de_mi_empresa = [e["Nombre"] for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"]
    historial_visible     = [s for s in st.session_state.historial_sesiones if s["Agente"] in agentes_de_mi_empresa and s.get("Tipo_Mision", "Corporativa") != "Personal"]
else:
    historial_visible     = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]
    agentes_de_mi_empresa = [u["Nombre"]]

mis_escenarios = {k: v for k, v in st.session_state.escenarios_custom.items()
                  if v.get("Creador") == empresa_actual or u["Nombre"] == COMANDANTE_SUPREMO}
TODAS_LAS_MISIONES = {**CONTEXTOS_MISION, **mis_escenarios}

# ─────────────────────────────────────────
# TOPBAR
# ─────────────────────────────────────────
rol_label = ("OMNISCIENCIA GLOBAL" if u["Nombre"] == COMANDANTE_SUPREMO
             else (f"SUPERVISION [{mi_plan}]" if es_empresa
                   else f"OPERADOR · {empresa_actual.upper()} [{mi_plan}]"))

col_top1, col_top2 = st.columns([8, 1])
with col_top1:
    pantalla = st.session_state.pantalla_actual
    nombres_pantalla = {"estadisticas": "ESTADISTICAS", "personal": "PERSONAL", "expedientes": "EXPEDIENTES",
                        "simulador": "SIMULADOR", "sintesis": "SINTESIS IA", "admin": "ADMINISTRACION"}
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
        if st.button("MENU", key="btn_menu"): st.session_state.pantalla_actual = "menu"; st.rerun()
    if st.button("SALIR", key="btn_logout", type="secondary"):
        st.session_state.usuario_actual = None; st.session_state.login_step = 1; st.session_state.pantalla_actual = "menu"; st.rerun()

def ir_a(p):
    st.session_state.pantalla_actual = p; st.rerun()

# ─────────────────────────────────────────
# MENÚ PRINCIPAL
# ─────────────────────────────────────────
if st.session_state.pantalla_actual == "menu":
    total_ops    = len(historial_visible)
    media_global = int(sum(s["Nota"] for s in historial_visible) / total_ops) if total_ops > 0 else 0
    ops_exitosas = sum(1 for s in historial_visible if s["Nota"] >= 80)
    tasa_exito   = int((ops_exitosas / total_ops) * 100) if total_ops > 0 else 0
    hora_actual  = datetime.now().strftime("%H:%M") + " · " + datetime.now().strftime("%d.%m.%Y")

    st.markdown(f"""
    <div class="hq-header">
        <div class="hq-label">CUARTEL GENERAL</div>
        <div class="hq-greeting">Bienvenido, {u['Nombre'].upper()}</div>
        <div class="hq-date">{hora_actual} · SISTEMA OPERATIVO</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="module-card primary">
            <div class="module-accent"></div>
            <div class="module-code">MOD-01 / ESTADISTICAS</div>
            <div class="module-title">Análisis de Rendimiento</div>
            <div class="module-desc">Métricas globales, histórico de desempeño y distribución de escenarios por operador.</div>
        </div>""", unsafe_allow_html=True)
        st.markdown(f"<div style='font-family:var(--mono); font-size:0.62rem; letter-spacing:0.18em; color:var(--text-lo); margin-top:-6px; margin-bottom:6px;'>RENDIMIENTO MEDIO · {media_global}%</div>", unsafe_allow_html=True)
        if st.button("ACCEDER A ESTADISTICAS", key="goto_stats", use_container_width=True): ir_a("estadisticas")

    with c2:
        st.markdown("""
        <div class="module-card danger">
            <div class="module-accent"></div>
            <div class="module-code">MOD-02 / DESPLIEGUE</div>
            <div class="module-title">Simulador Táctico</div>
            <div class="module-desc">Inicia una operación de negociación táctica en tiempo real con objetivo generado por IA.</div>
        </div>""", unsafe_allow_html=True)
        mes_actual = datetime.now().strftime("%Y-%m")
        ops_mes    = len([s for s in historial_visible if str(s.get("Fecha","")).startswith(mes_actual)])
        st.markdown(f"<div style='font-family:var(--mono); font-size:0.62rem; letter-spacing:0.18em; color:var(--text-lo); margin-top:-6px; margin-bottom:6px;'>OPERACIONES ESTE MES · {ops_mes}</div>", unsafe_allow_html=True)
        if st.button("INICIAR DESPLIEGUE", key="goto_sim", use_container_width=True): ir_a("simulador")

    with c3:
        st.markdown("""
        <div class="module-card">
            <div class="module-accent"></div>
            <div class="module-code">MOD-03 / EXPEDIENTES</div>
            <div class="module-title">Archivo Operacional</div>
            <div class="module-desc">Consulta y descarga de dossiers de sesiones anteriores con transcripciones completas.</div>
        </div>""", unsafe_allow_html=True)
        st.markdown(f"<div style='font-family:var(--mono); font-size:0.62rem; letter-spacing:0.18em; color:var(--text-lo); margin-top:-6px; margin-bottom:6px;'>EXPEDIENTES TOTALES · {total_ops}</div>", unsafe_allow_html=True)
        if st.button("VER EXPEDIENTES", key="goto_exp", use_container_width=True): ir_a("expedientes")

    if u["Nombre"] == COMANDANTE_SUPREMO:
        c4, c5, c6 = st.columns(3)
    else:
        c4, c5 = st.columns(2)

    with c4:
        st.markdown("""
        <div class="module-card">
            <div class="module-accent"></div>
            <div class="module-code">MOD-04 / PERSONAL</div>
            <div class="module-title">Gestión de Operadores</div>
            <div class="module-desc">Reclutamiento de agentes, control de accesos, enlace cifrado y ajustes de cuenta.</div>
        </div>""", unsafe_allow_html=True)
        agentes_activos = len([e for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"])
        st.markdown(f"<div style='font-family:var(--mono); font-size:0.62rem; letter-spacing:0.18em; color:var(--text-lo); margin-top:-6px; margin-bottom:6px;'>AGENTES ACTIVOS · {agentes_activos}</div>", unsafe_allow_html=True)
        if st.button("GESTIONAR PERSONAL", key="goto_pers", use_container_width=True): ir_a("personal")

    with c5:
        st.markdown("""
        <div class="module-card gold">
            <div class="module-accent"></div>
            <div class="module-code">MOD-05 / SINTESIS</div>
            <div class="module-title">Generación de Escenarios</div>
            <div class="module-desc">Motor de IA para crear simulaciones personalizadas adaptadas a tu contexto operativo.</div>
        </div>""", unsafe_allow_html=True)
        escenarios_creados = len(mis_escenarios)
        st.markdown(f"<div style='font-family:var(--mono); font-size:0.62rem; letter-spacing:0.18em; color:var(--text-lo); margin-top:-6px; margin-bottom:6px;'>ESCENARIOS ACTIVOS · {escenarios_creados}</div>", unsafe_allow_html=True)
        if st.button("ACCEDER A SINTESIS", key="goto_sint", use_container_width=True): ir_a("sintesis")

    if u["Nombre"] == COMANDANTE_SUPREMO:
        with c6:
            total_clientes = len([e for e in st.session_state.empleados if e["Nombre"] != COMANDANTE_SUPREMO])
            mrr = sum({"COMANDANCIA":199,"ESCUADRON":89,"ELITE":49,"OPERADOR":19,"BASE":0}.get(
                _legacy.get(e.get("Plan","BASE"), e.get("Plan","BASE")), 0) for e in st.session_state.empleados)
            st.markdown("""
            <div class="module-card" style="border-left-color: #E8394A;">
                <div class="module-accent" style="background:#E8394A;"></div>
                <div class="module-code">MOD-06 / ADMIN</div>
                <div class="module-title">Consola Omega</div>
                <div class="module-desc">Panel de control global. Gestión de usuarios, planes y métricas SaaS en tiempo real.</div>
            </div>""", unsafe_allow_html=True)
            st.markdown(f"<div style='font-family:var(--mono); font-size:0.62rem; letter-spacing:0.18em; color:var(--text-lo); margin-top:-6px; margin-bottom:6px;'>MRR ESTIMADO · {mrr}€</div>", unsafe_allow_html=True)
            if st.button("CONSOLA OMEGA", key="goto_admin", use_container_width=True): ir_a("admin")

    st.stop()

# ─────────────────────────────────────────
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
            st.markdown("<div class='section-label'>DISTRIBUCION DE ESCENARIOS</div>", unsafe_allow_html=True)
            esc_count = df["Escenario"].value_counts().reset_index()
            esc_count.columns = ["Escenario","Count"]
            fig2 = go.Figure(go.Pie(labels=esc_count["Escenario"], values=esc_count["Count"], hole=0.65,
                                    marker=dict(colors=['#4F8EF7','#00D4A0','#F0A500'])))
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
                fig3 = go.Figure(go.Scatter(x=df_sorted["Fecha_dt"], y=df_sorted["Nota"],
                                            mode='lines+markers', line=dict(color='#4F8EF7')))
                fig3.add_hline(y=80, line_dash="dot", line_color="#00D4A0")
                fig3.update_layout(**PLOTLY_THEME, height=280)
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────
# PERSONAL
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "personal":
    st.markdown("<div class='section-header'><div><div class='section-code'>MOD-04</div><div class='section-title'>Gestión de Operadores</div></div></div>", unsafe_allow_html=True)

    if es_empresa:
        st.markdown("<div class='section-label'>ENLACE SEGURO DE RECLUTAMIENTO</div>", unsafe_allow_html=True)
        if agentes_lim > 0 or u["Nombre"] == COMANDANTE_SUPREMO:
            token_cifrado  = base64.urlsafe_b64encode(empresa_actual.encode()).decode()
            URL_BASE_APP   = "https://crysis.streamlit.app/"
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
        st.markdown(f"""<div class="briefing-box"><h4>DATOS DEL OPERADOR</h4>
        <p><b>Identificador:</b> {u['Nombre']} | <b>Unidad:</b> {empresa_actual} | <b>Plan:</b> {mi_plan}</p></div>""",
        unsafe_allow_html=True)

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
        planes_suscripcion = [
            ("OPERADOR",    "19€/mes", "Individual · 10 ops", "OPERADOR"),
            ("ELITE",       "49€/mes", "Individual · ∞ ops · IA ∞", "ELITE"),
            ("ESCUADRON",   "89€/mes", "Equipo · 15 agentes", "ESCUADRON"),
            ("COMANDANCIA", "199€/mes","Enterprise · ∞ agentes", "COMANDANCIA"),
        ]
        cols_plan = st.columns(4)
        for col, (nombre, precio, desc, plan_key) in zip(cols_plan, planes_suscripcion):
            with col:
                es_elite_p = plan_key in ["ELITE","ESCUADRON","COMANDANCIA"]
                color_p    = "#F0A500" if es_elite_p else "#4F8EF7"
                st.markdown(f"""<div class="metric-card" style="{'border-left-color:#F0A500' if es_elite_p else ''}">
                    <div class="metric-label">{nombre}</div>
                    <div class="metric-value" style="font-size:1.2rem; color:{color_p};">{precio}</div>
                    <div style="font-family:var(--mono); font-size:0.6rem; color:var(--text-mid); margin-top:10px;">{desc}</div>
                </div>""", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                if mi_plan == plan_key:
                    st.success("Activo")
                else:
                    link = LINKS_PAGO.get(plan_key, "#")
                    st.markdown(f'<a href="{link}" target="_blank"><button style="background:#4F8EF7;color:#060810;font-family:var(--mono);font-weight:700;border:none;padding:11px;border-radius:4px;cursor:pointer;width:100%;font-size:0.68rem;letter-spacing:0.1em;">ACTIVAR</button></a>', unsafe_allow_html=True)

    st.markdown("<br><div class='section-label'>ZONA DE RIESGO</div>", unsafe_allow_html=True)
    if st.button("ELIMINAR MI CUENTA DEFINITIVAMENTE", type="primary"):
        if es_empresa:
            st.session_state.empleados = [e for e in st.session_state.empleados if e.get("Empresa") != u["Nombre"]]
        else:
            st.session_state.empleados = [e for e in st.session_state.empleados if e["Nombre"] != u["Nombre"]]
        st.session_state.usuario_actual = None; guardar_datos(); st.rerun()

# ─────────────────────────────────────────
# EXPEDIENTES — CON BORRADO INDIVIDUAL
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
                            tiene_intel_exp = bool(s.get("Transcripcion_Intel"))
                            puede_borrar = (s["Agente"] == u["Nombre"]) or (u["Nombre"] == COMANDANTE_SUPREMO)

                            # Unique key for this session entry
                            entry_key = f"{s['Agente']}_{s['Fecha']}".replace(" ", "_").replace(":", "-")

                            st.markdown(f"""
                            <div class="exp-card">
                              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                                <span style="color:var(--text-mid); font-size:0.82rem; font-family:var(--mono);">
                                  {s['Fecha']} · {modo_badge} ·
                                  <span style="color:{dif_color};">{dif_badge}</span>
                                  {"&nbsp;·&nbsp;<span style='color:#F0A500;'>INTEL</span>" if tiene_intel_exp else ""}
                                </span>
                                <span style="font-family:var(--mono); color:{c_nota}; font-weight:700; font-size:1rem;">{nota_ind}/100</span>
                              </div>
                              <div style="font-size:0.9rem; color:var(--text); line-height:1.6; margin-bottom:12px;">{s['Evaluacion'][:320]}...</div>
                            """, unsafe_allow_html=True)

                            if s.get("Evaluacion_Intel"):
                                st.markdown(f"""
                                <div style="background:#0D0A18; border:1px solid #2A1A4A; border-left:3px solid #F0A500;
                                            padding:12px 16px; margin-bottom:12px; border-radius:var(--radius);">
                                    <div style="font-family:var(--mono); font-size:0.55rem; letter-spacing:0.18em;
                                                color:#F0A500; margin-bottom:8px;">EVALUACIÓN USO DE INTELIGENCIA</div>
                                    <div style="font-size:0.88rem; color:var(--text); line-height:1.6;">{str(s.get('Evaluacion_Intel',''))[:420]}...</div>
                                </div>
                                """, unsafe_allow_html=True)

                            st.markdown("</div>", unsafe_allow_html=True)

                            # Botones acción
                            col_pdf, col_del = st.columns([3, 1])

                            with col_pdf:
                                st.download_button(
                                    label="EXTRAER DOSSIER PDF",
                                    data=generar_pdf_dossier(s),
                                    file_name=f"CRYSIS_{s['Agente']}_{s['Fecha'][:10]}.pdf",
                                    mime="application/pdf",
                                    key=f"pdf_{entry_key}"
                                )

                            with col_del:
                                if puede_borrar:
                                    confirm_key = f"confirm_del_{entry_key}"
                                    input_key   = f"input_del_{entry_key}"

                                    if not st.session_state.get(confirm_key, False):
                                        if st.button("ELIMINAR", key=f"btn_del_{entry_key}", type="secondary", use_container_width=True):
                                            st.session_state[confirm_key] = True
                                            st.rerun()
                                    else:
                                        st.markdown("""
                                        <div style="background:#140A0A; border:1px solid #E8394A; border-left:3px solid #E8394A;
                                                    padding:12px 14px; border-radius:var(--radius); margin-bottom:8px;">
                                            <div style="font-family:var(--mono); font-size:0.58rem; letter-spacing:0.18em;
                                                        color:#E8394A; margin-bottom:8px;">CONFIRMACIÓN REQUERIDA</div>
                                            <div style="font-family:var(--mono); font-size:0.62rem; color:var(--text-mid); line-height:1.6;">
                                                Escribe <b style="color:var(--text-hi);">CONFIRMAR BORRADO</b> y pulsa ejecutar para eliminar este expediente de forma permanente.
                                            </div>
                                        </div>
                                        """, unsafe_allow_html=True)

                                        texto_confirmacion = st.text_input(
                                            "Frase de confirmación:",
                                            key=input_key,
                                            placeholder="CONFIRMAR BORRADO",
                                            label_visibility="collapsed"
                                        )

                                        col_conf, col_canc = st.columns(2)
                                        with col_conf:
                                            if st.button("EJECUTAR", key=f"exec_del_{entry_key}", use_container_width=True):
                                                if texto_confirmacion.strip().upper() == "CONFIRMAR BORRADO":
                                                    st.session_state.historial_sesiones = [
                                                        ses for ses in st.session_state.historial_sesiones
                                                        if not (ses["Agente"] == s["Agente"] and ses["Fecha"] == s["Fecha"])
                                                    ]
                                                    guardar_datos()
                                                    del st.session_state[confirm_key]
                                                    st.rerun()
                                                else:
                                                    st.error("Frase incorrecta.")
                                        with col_canc:
                                            if st.button("CANCELAR", key=f"canc_del_{entry_key}", use_container_width=True, type="secondary"):
                                                del st.session_state[confirm_key]
                                                st.rerun()

                            if es_empresa and mi_plan == "COMANDANCIA" and "Transcripcion" in s:
                                st.markdown("<br><span style='color:#F0A500; font-size:0.72rem; font-family:var(--mono); letter-spacing:0.1em;'>AUDITORÍA DE COMUNICACIONES</span>", unsafe_allow_html=True)
                                for tr in s["Transcripcion"]:
                                    ag_tr = "OPERADOR" if tr["role"] == "user" else "SUJETO"
                                    colr  = "#4F8EF7" if tr["role"] == "user" else "#E8394A"
                                    st.markdown(f"<div style='font-size:0.88rem; margin-bottom:6px;'><b style='color:{colr}'>{ag_tr}:</b> <span style='color:var(--text-mid)'>{tr['content']}</span></div>", unsafe_allow_html=True)

                            st.markdown("<hr style='border:none; border-top:1px solid var(--border); margin:18px 0 6px 0;'>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center; padding:80px; color:#18213A; font-family:var(--mono); letter-spacing:0.2em; font-size:0.9rem;'>DIRECTORIO VACÍO</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SIMULADOR TÁCTICO — REDISEÑADO
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "simulador":
    st.markdown("<div class='section-header'><div><div class='section-code'>MOD-02</div><div class='section-title'>Simulador Táctico</div></div></div>", unsafe_allow_html=True)

    # ── PANTALLA DE CONFIGURACIÓN ──
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
                <div class="diff-card {'selected' if is_sel_d else ''}"
                     style="border-color:{border_d}; background:{bg_d};">
                    <div class="diff-name" style="color:{d_data['color']};">{d_nombre}</div>
                    <div style="font-family:var(--mono); font-size:0.58rem; color:{d_data['color']}; opacity:0.7; margin-top:4px; letter-spacing:0.1em;">LVL {d_data['nivel']}</div>
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

        intel_badge = ""
        if tiene_intel:
            intel_badge = f"<span style='background:rgba(240,165,0,0.15); border:1px solid rgba(240,165,0,0.4); border-radius:3px; padding:3px 10px; font-family:var(--mono); font-size:0.58rem; color:#F0A500; letter-spacing:0.14em; margin-left:10px;'>INTEL ACTIVO</span>"

        st.markdown(f"""
        <div class="briefing-box">
            <h4>REPORTE DE SITUACIÓN {intel_badge}</h4>
            <p><b>Contexto:</b> {info['contexto']}</p>
            <p><b>Perfil:</b> {info['perfil_sujeto']}</p>
            <p><b>Directiva:</b> {info['objetivo']}</p>
            <p><b>Dificultad:</b> <span style="color:{dif_color}; font-family:var(--mono); font-weight:700;">{dif_activa} (Nivel {DIFICULTADES[dif_activa]['nivel']})</span></p>
            {"<p style='color:#F0A500; font-family:var(--mono); font-size:0.7rem; margin-top:8px;'>▸ SERVICIOS DE INTELIGENCIA disponibles durante la operación</p>" if tiene_intel else "<p style='color:var(--text-lo); font-family:var(--mono); font-size:0.7rem; margin-top:8px;'>▸ SERVICIOS DE INTELIGENCIA requieren plan ELITE o superior</p>"}
        </div>
        """, unsafe_allow_html=True)

        mes_actual  = datetime.now().strftime("%Y-%m")
        ops_este_mes = len([s for s in st.session_state.historial_sesiones
                            if s["Agente"] == ag_sel and str(s.get("Fecha","")).startswith(mes_actual)])

        bloquear_inicio = False
        if mi_plan != "COMANDANCIA" and u["Nombre"] != COMANDANTE_SUPREMO:
            if ops_este_mes >= ops_limite:
                bloquear_inicio = True
                st.error(f"AUTORIZACIÓN DENEGADA: Cuota mensual superada ({ops_este_mes}/{ops_limite} ops). Actualiza tu plan.")

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

            st.session_state.mision_iniciada      = True
            st.session_state.mensajes             = []
            st.session_state.mensajes_intel       = []
            st.session_state.evaluacion_actual    = None
            st.session_state.evaluacion_intel     = None
            st.session_state.agente_activo        = ag_sel
            st.session_state.escenario_activo     = es_sel
            st.session_state.tipo_mision_actual   = tipo_mision_val
            st.session_state.dificultad_sesion    = dif_activa
            st.session_state.imagen_seed          = random.randint(1000, 9999)
            st.rerun()

    # ── PANTALLA DE EVALUACIÓN FINAL ──
    elif st.session_state.evaluacion_actual:
        st.markdown("<div class='section-label'>INFORME DE EVALUACIÓN TÁCTICA — CANAL PRINCIPAL</div>", unsafe_allow_html=True)
        st.markdown(st.session_state.evaluacion_actual)

        if st.session_state.evaluacion_intel:
            st.markdown("""
            <div style="margin-top:28px; padding:18px 0 10px 0; border-top:1px solid #2A1A4A;">
                <div style="font-family:var(--mono); font-size:0.62rem; letter-spacing:0.22em; color:#F0A500;
                            margin-bottom:16px; padding-bottom:10px; border-bottom:1px solid #2A1A4A;">
                    EVALUACIÓN DE USO DE SERVICIOS DE INTELIGENCIA
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(st.session_state.evaluacion_intel)

        st.markdown("<br>", unsafe_allow_html=True)
        col_end1, col_end2 = st.columns(2)

        with col_end1:
            if st.button("ARCHIVAR INFORME Y VOLVER AL MENÚ", use_container_width=True):
                st.session_state.mision_iniciada   = False
                st.session_state.evaluacion_actual = None
                st.session_state.evaluacion_intel  = None
                st.session_state.mensajes          = []
                st.session_state.mensajes_intel    = []
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

    # ── PANTALLA DE SIMULACIÓN ACTIVA — DOS COLUMNAS LADO A LADO ──
    else:
        dif_sesion  = st.session_state.get("dificultad_sesion", "OPERATOR")
        dif_color_s = DIFICULTADES.get(dif_sesion, {}).get("color","#4F8EF7")

        st.markdown(f"""
        <div class='status-bar'>
            LÍNEA SEGURA ACTIVA: {st.session_state.escenario_activo} —
            OPERADOR: {st.session_state.agente_activo.upper()} —
            <span style="color:{dif_color_s};">DIFICULTAD: {dif_sesion}</span>
            {"— <span style='color:#F0A500;'>INTEL: ONLINE</span>" if tiene_intel else ""}
        </div>
        """, unsafe_allow_html=True)

        # ── TARJETA OBJETIVO ──
        if st.session_state.tarjeta_objetivo:
            t = st.session_state.tarjeta_objetivo
            st.markdown(f"""
            <div style="display:flex; gap:0; background:#0B0E1A; border:1px solid #18213A;
                        border-left:3px solid #F0A500; border-radius:var(--radius); padding:16px 22px;
                        margin-bottom:22px; gap:24px;">
                <div style="flex:1;">
                    <div style="color:#F0A500; font-size:0.6rem; font-family:var(--mono); letter-spacing:0.2em; margin-bottom:5px;">IDENTIFICACIÓN</div>
                    <div style="color:#E2EAF8; font-size:0.95rem; font-weight:600;">{str(t.get('Nombre_Completo','N/A'))}</div>
                </div>
                <div style="flex:1;">
                    <div style="color:#F0A500; font-size:0.6rem; font-family:var(--mono); letter-spacing:0.2em; margin-bottom:5px;">VÍNCULOS</div>
                    <div style="color:var(--text); font-size:0.9rem;">{str(t.get('Familia','N/A'))}</div>
                </div>
                <div style="flex:1;">
                    <div style="color:#F0A500; font-size:0.6rem; font-family:var(--mono); letter-spacing:0.2em; margin-bottom:5px;">ESTADO CLÍNICO</div>
                    <div style="color:var(--text); font-size:0.9rem;">{str(t.get('Estado_Mental','N/A'))}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ════════════════════════════════════════
        # DOS COLUMNAS: 60% PRINCIPAL / 40% INTEL
        # ════════════════════════════════════════
        if tiene_intel:
            col_main, col_intel = st.columns([3, 2], gap="medium")
        else:
            col_main = st.container()
            col_intel = None

        # ── CANAL PRINCIPAL ──
        with col_main:
            st.markdown("""
            <div class="sim-col-header principal">
                <span style="display:inline-block; width:8px; height:8px; background:#4F8EF7; border-radius:50%;"></span>
                CANAL PRINCIPAL — ENLACE CON OBJETIVO
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="sim-chat-box principal">', unsafe_allow_html=True)
            for m in st.session_state.mensajes:
                label  = "TÚ" if m["role"] == "user" else "SUJETO"
                bg     = "rgba(79,142,247,0.08)" if m["role"] == "user" else "rgba(232,57,74,0.06)"
                border = "#4F8EF7" if m["role"] == "user" else "#E8394A"
                align  = "flex-end" if m["role"] == "user" else "flex-start"
                st.markdown(f"""
                <div style="display:flex; justify-content:{align}; margin-bottom:14px;">
                    <div style="max-width:88%; background:{bg}; border:1px solid {border}33;
                                border-left:3px solid {border}; border-radius:var(--radius); padding:12px 16px;">
                        <div style="font-family:var(--mono); font-size:0.58rem; letter-spacing:0.2em;
                                    color:{border}; margin-bottom:7px;">{label}</div>
                        <div style="color:var(--text); font-size:0.9rem; line-height:1.65;">{m['content']}</div>
                    </div>
                </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            if prompt_principal := st.chat_input("Introduzca directiva de respuesta...", key="chat_principal"):
                st.session_state.mensajes.append({"role":"user","content":prompt_principal}); st.rerun()

            if st.session_state.mensajes and st.session_state.mensajes[-1]["role"] == "user":
                if GROQ_API_KEY:
                    client       = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                    escenario_a  = st.session_state.escenario_activo
                    base_prompt  = TODAS_LAS_MISIONES[escenario_a]["prompt"]
                    dif_instruc  = DIFICULTADES.get(dif_sesion, {}).get("instruccion","")
                    base_prompt += f"\n\n[NIVEL DE DIFICULTAD: {dif_sesion}. {dif_instruc}]"
                    if st.session_state.tarjeta_objetivo:
                        t2 = st.session_state.tarjeta_objetivo
                        base_prompt += f"\n\n[Tu nombre es {t2.get('Nombre_Completo')}. Familia: {t2.get('Familia')}. Estado: {t2.get('Estado_Mental')}.]"
                    res = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role":"system","content": base_prompt}] + st.session_state.mensajes
                    ).choices[0].message.content
                    st.session_state.mensajes.append({"role":"assistant","content":res}); st.rerun()

        # ── CANAL INTELIGENCIA ──
        if tiene_intel and col_intel is not None:
            with col_intel:
                st.markdown("""
                <div class="sim-col-header intel">
                    <span class="intel-dot"></span>
                    SERVICIOS DE INTELIGENCIA
                </div>
                """, unsafe_allow_html=True)

                st.markdown('<div class="sim-chat-box intel">', unsafe_allow_html=True)

                if not st.session_state.mensajes_intel:
                    st.markdown("""
                    <div style="text-align:center; padding:40px 16px; color:#2A1A4A; font-family:var(--mono); font-size:0.6rem; letter-spacing:0.16em; line-height:1.8;">
                        CANAL CIFRADO ACTIVO<br>
                        <span style="color:#1A1030;">Consulta datos, perfiles,<br>imágenes de reconocimiento.</span>
                    </div>
                    """, unsafe_allow_html=True)

                for m in st.session_state.mensajes_intel:
                    if m["role"] == "user":
                        st.markdown(f"""
                        <div style="display:flex; justify-content:flex-end; margin-bottom:12px;">
                            <div style="max-width:92%; background:rgba(240,165,0,0.07); border:1px solid rgba(240,165,0,0.2);
                                        border-left:3px solid #F0A500; border-radius:var(--radius); padding:10px 14px;">
                                <div style="font-family:var(--mono); font-size:0.55rem; letter-spacing:0.18em;
                                            color:#F0A500; margin-bottom:6px;">OPERADOR → INTEL</div>
                                <div style="color:var(--text); font-size:0.88rem; line-height:1.6;">{m['content']}</div>
                            </div>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="display:flex; justify-content:flex-start; margin-bottom:12px;">
                            <div style="max-width:92%; background:rgba(155,89,182,0.06); border:1px solid rgba(155,89,182,0.2);
                                        border-left:3px solid #9B59B6; border-radius:var(--radius); padding:10px 14px;">
                                <div style="font-family:var(--mono); font-size:0.55rem; letter-spacing:0.18em;
                                            color:#9B59B6; margin-bottom:6px;">INTEL → OPERADOR</div>
                                <div style="color:var(--text); font-size:0.88rem; line-height:1.6;">{m['content']}</div>
                            </div>
                        </div>""", unsafe_allow_html=True)

                        # Imagen de reconocimiento en miniatura con lightbox
                        idx = st.session_state.mensajes_intel.index(m)
                        if idx > 0:
                            prev = st.session_state.mensajes_intel[idx - 1]
                            if prev["role"] == "user" and es_peticion_imagen_intel(prev["content"]):
                                seed_img = st.session_state.get("imagen_seed", 42) + idx
                                url_img  = generar_url_imagen_intel(
                                    st.session_state.escenario_activo,
                                    prev["content"],
                                    seed_img
                                )
                                st.markdown(f"""
                                <div class="intel-image-container">
                                    <div class="intel-image-label">▸ SAT-{seed_img} · {datetime.now().strftime('%H:%M:%S')} · CLASIFICADO</div>
                                    <a href="{url_img}" target="_blank" title="Ver imagen completa">
                                        <img src="{url_img}" style="width:100%; max-width:250px; height:auto;
                                             border-radius:3px; border:1px solid rgba(240,165,0,0.3);
                                             display:block; cursor:pointer;"
                                             alt="Imagen de reconocimiento" />
                                    </a>
                                    <div style="font-family:var(--mono); font-size:0.5rem; color:#4A3A6A; margin-top:6px; letter-spacing:0.1em;">
                                        Pulsa para ampliar
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown("""
                <div style="background:#08050E; border:1px solid #1A1030; border-top:none;
                            padding:8px 12px; border-radius:0 0 var(--radius) var(--radius);">
                    <span style="font-family:var(--mono); font-size:0.52rem; letter-spacing:0.12em; color:#2A1A4A;">
                        ▸ Independiente del canal principal · La info puede ser parcial
                    </span>
                </div>
                """, unsafe_allow_html=True)

                if prompt_intel := st.chat_input("Consultar a Inteligencia...", key="chat_intel"):
                    st.session_state.mensajes_intel.append({"role":"user","content":prompt_intel}); st.rerun()

                if st.session_state.mensajes_intel and st.session_state.mensajes_intel[-1]["role"] == "user":
                    if GROQ_API_KEY:
                        client_intel   = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                        escenario_intel = st.session_state.escenario_activo
                        intel_system   = INTEL_PROMPTS.get(escenario_intel, INTEL_PROMPT_DEFAULT)
                        info_escenario = TODAS_LAS_MISIONES.get(escenario_intel, {})
                        intel_system += f"\n\nCONTEXTO OPERACION: {info_escenario.get('contexto', '')}"
                        intel_system += f"\nOBJETIVO DE LA MISION: {info_escenario.get('objetivo', '')}"
                        if st.session_state.tarjeta_objetivo:
                            t_intel = st.session_state.tarjeta_objetivo
                            intel_system += f"\nSUJETO IDENTIFICADO: {t_intel.get('Nombre_Completo')} · Estado: {t_intel.get('Estado_Mental')}"
                        res_intel = client_intel.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role":"system","content": intel_system}] + st.session_state.mensajes_intel
                        ).choices[0].message.content
                        st.session_state.mensajes_intel.append({"role":"assistant","content":res_intel}); st.rerun()

        elif not tiene_intel:
            st.markdown("""
            <div style="background:#0A0A14; border:1px solid var(--border); border-left:3px solid #1A1A30;
                        padding:18px 22px; border-radius:var(--radius); margin-top:24px; text-align:center;">
                <div style="font-family:var(--mono); font-size:0.62rem; letter-spacing:0.2em;
                            color:#1A1A30; margin-bottom:8px;">SERVICIOS DE INTELIGENCIA — BLOQUEADO</div>
                <div style="font-family:var(--mono); font-size:0.7rem; color:var(--text-lo);">
                    Disponible en planes ELITE · ESCUADRON · COMANDANCIA
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── CONTROLES INFERIORES ──
        st.markdown("<br>", unsafe_allow_html=True)
        col_abort, col_end = st.columns([1, 3])

        with col_abort:
            if st.button("ROMPER ENLACE", type="secondary", use_container_width=True):
                st.session_state.mision_iniciada  = False
                st.session_state.mensajes         = []
                st.session_state.mensajes_intel   = []
                st.session_state.tarjeta_objetivo = None
                st.rerun()

        with col_end:
            if len(st.session_state.mensajes) > 0:
                if st.button("SOLICITAR EVALUACIÓN TÁCTICA", use_container_width=True):
                    with st.spinner("Procesando auditoría lingüística..."):
                        client    = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                        escenario = st.session_state.escenario_activo
                        info_ev   = TODAS_LAS_MISIONES[escenario]
                        dif_ev    = st.session_state.get("dificultad_sesion", "OPERATOR")
                        dif_nivel = DIFICULTADES.get(dif_ev, {}).get("nivel", 2)

                        hist_txt = "\n".join([
                            f"{'OPERADOR' if m['role']=='user' else 'SUJETO'}: {m['content']}"
                            for m in st.session_state.mensajes
                        ])

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

TRANSCRIPCION:
{hist_txt}

REGLAS:
1. NO regales puntuación por cortesía básica.
2. Evalúa: control, técnicas de desescalada, resistencia a manipulación, lenguaje estratégico.
3. Penaliza: ceder sin contrapartida, lenguaje amenazante, pérdida de control emocional.

Estructura: ANALISIS DE LENGUAJE / TACTICAS EMPLEADAS / ERRORES CRITICOS / VEREDICTO / COMO MEJORAR

PUNTUACION FINAL: XX/100"""

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

                        informe_intel = None
                        if tiene_intel and st.session_state.mensajes_intel:
                            hist_intel_txt = "\n".join([
                                f"{'OPERADOR' if m['role']=='user' else 'INTEL'}: {m['content']}"
                                for m in st.session_state.mensajes_intel
                            ])
                            hist_principal_txt = "\n".join([
                                f"{'OPERADOR' if m['role']=='user' else 'SUJETO'}: {m['content']}"
                                for m in st.session_state.mensajes
                            ])

                            eval_intel_prompt = f"""Eres un Supervisor de Operaciones de Inteligencia. Evalúa cómo el OPERADOR utilizó los Servicios de Inteligencia durante la operación.

ESCENARIO: {escenario}
OBJETIVO: {info_ev['objetivo']}
DIFICULTAD: {dif_ev}

CANAL PRINCIPAL (conversación con el objetivo):
{hist_principal_txt}

CANAL DE INTELIGENCIA (consultas del operador):
{hist_intel_txt}

EVALÚA LOS SIGUIENTES ASPECTOS (sé estricto y específico):

1. PERTINENCIA DE LAS CONSULTAS
2. USO DE INFORMACIÓN RECIBIDA
3. GESTIÓN DE INFORMACIÓN IMPERFECTA
4. COORDINACIÓN TÁCTICA

VEREDICTO FINAL DE USO DE INTELIGENCIA: [EXCELENTE / CORRECTO / DEFICIENTE]

PUNTUACION DE USO DE INTELIGENCIA: XX/100"""

                            informe_intel = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{"role":"user","content":eval_intel_prompt}]
                            ).choices[0].message.content

                        st.session_state.evaluacion_actual = informe
                        st.session_state.evaluacion_intel  = informe_intel

                        sesion_guardada = {
                            "Fecha":               datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "Agente":              st.session_state.agente_activo,
                            "Escenario":           escenario,
                            "Nota":                nota,
                            "Evaluacion":          informe,
                            "Evaluacion_Intel":    informe_intel,
                            "Transcripcion":       st.session_state.mensajes,
                            "Transcripcion_Intel": st.session_state.mensajes_intel if tiene_intel else [],
                            "Tipo_Mision":         st.session_state.tipo_mision_actual,
                            "Dificultad":          dif_ev,
                        }
                        st.session_state.historial_sesiones.append(sesion_guardada)
                        guardar_datos()
                        st.rerun()

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
                c_esc1.markdown(f"<span style='color:var(--text); font-size:0.92rem;'>{nombre_esc}</span>", unsafe_allow_html=True)
                if c_esc2.button("ELIMINAR", key=f"del_{nombre_esc}", type="secondary"):
                    del st.session_state.escenarios_custom[nombre_esc]; guardar_datos(); st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("<div class='section-label'>NUEVA SIMULACIÓN</div>", unsafe_allow_html=True)

        if mi_plan == "BASE" and u["Nombre"] != COMANDANTE_SUPREMO:
            st.error("RESTRICCIÓN: El Nivel BASE no posee autorización para el uso de IA Generativa.")
            st.button("GENERAR NUEVA SIMULACIÓN", disabled=True)
        else:
            if u["Nombre"] == COMANDANTE_SUPREMO:
                limite_esc = 99999
            else:
                limite_esc = escenarios_lim

            if limite_esc != 99999 and creados >= limite_esc:
                st.error(f"CUOTA DE SÍNTESIS ALCANZADA ({creados}/{limite_esc}). Elimina uno existente para crear otro.")
                st.button("GENERAR NUEVA SIMULACIÓN", disabled=True)
            else:
                idea_prompt = st.text_area("Describe los parámetros del entorno táctico:", height=110)
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
                                    "contexto":       nuevo_esc["contexto"],
                                    "perfil_sujeto":  nuevo_esc["perfil_sujeto"],
                                    "objetivo":       nuevo_esc["objetivo"],
                                    "prompt":         nuevo_esc["prompt"],
                                    "Creador":        empresa_actual
                                }
                                guardar_datos(); st.success(f"Protocolo {nuevo_esc['nombre_op']} configurado."); st.rerun()
                            except Exception as e:
                                st.error(f"Fallo del Motor IA: {e}")
                    elif not idea_prompt:
                        st.warning("Escribe los parámetros base.")

    with col_der:
        st.markdown("<div class='section-label'>NIVELES DE ACCESO IA</div>", unsafe_allow_html=True)
        st.markdown("""
        <div>
            <div class="auth-tier"><div style="display:flex;justify-content:space-between;margin-bottom:10px;border-bottom:1px solid #18213A;padding-bottom:8px;">
                <span style="font-family:var(--mono);font-size:0.72rem;color:var(--text-hi);">BASE</span>
                <span style="font-family:var(--mono);font-size:0.82rem;color:var(--text-lo);">0€</span></div>
                <div class="tier-spec">Sin acceso a IA generativa</div><div class="tier-spec">1 op/mes</div></div>
            <div class="auth-tier"><div style="display:flex;justify-content:space-between;margin-bottom:10px;border-bottom:1px solid #18213A;padding-bottom:8px;">
                <span style="font-family:var(--mono);font-size:0.72rem;color:var(--text-hi);">OPERADOR</span>
                <span style="font-family:var(--mono);font-size:0.82rem;color:#4F8EF7;">19€/mes</span></div>
                <div class="tier-spec">3 escenarios propios</div><div class="tier-spec">10 ops/mes</div></div>
            <div class="auth-tier elite"><div style="display:flex;justify-content:space-between;margin-bottom:10px;border-bottom:1px solid #18213A;padding-bottom:8px;">
                <span style="font-family:var(--mono);font-size:0.72rem;color:var(--text-hi);">ELITE</span>
                <span style="font-family:var(--mono);font-size:0.82rem;color:#F0A500;">49€/mes</span></div>
                <div class="tier-spec">Escenarios ilimitados</div><div class="tier-spec">Intel + Imágenes</div></div>
            <div class="auth-tier elite"><div style="display:flex;justify-content:space-between;margin-bottom:10px;border-bottom:1px solid #18213A;padding-bottom:8px;">
                <span style="font-family:var(--mono);font-size:0.72rem;color:var(--text-hi);">ESCUADRON</span>
                <span style="font-family:var(--mono);font-size:0.82rem;color:#F0A500;">89€/mes</span></div>
                <div class="tier-spec">15 agentes · IA ∞</div><div class="tier-spec">Intel + Imágenes</div></div>
            <div class="auth-tier elite"><div style="display:flex;justify-content:space-between;margin-bottom:10px;border-bottom:1px solid #18213A;padding-bottom:8px;">
                <span style="font-family:var(--mono);font-size:0.72rem;color:var(--text-hi);">COMANDANCIA</span>
                <span style="font-family:var(--mono);font-size:0.82rem;color:#F0A500;">199€/mes</span></div>
                <div class="tier-spec">Agentes ∞ · IA ∞</div><div class="tier-spec">Intel + Imágenes</div></div>
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
                        st.session_state.empleados = [e for e in st.session_state.empleados if not (e["Nombre"] == usr["Nombre"] and e.get("Rol") == usr.get("Rol") and e.get("Empresa") == usr.get("Empresa"))]
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
                new_n    = st.text_input("ID / Entidad", key="admin_new_n")
                new_email= st.text_input("Correo",       key="admin_new_email")
                new_pass = st.text_input("Contraseña", type="password", key="admin_new_pass")
                new_rol  = st.selectbox("Rol", ["Individual","Empresa"], key="admin_new_rol")
                new_plan = st.selectbox("Plan", ["BASE","OPERADOR","ELITE","ESCUADRON","COMANDANCIA"], key="admin_new_plan")
                expira   = st.checkbox("Licencia temporal (30 dias)", value=False, key="admin_expira")
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
                    f"{e['Nombre']} [{e.get('Rol','?')}] — Plan: {_legacy.get(e.get('Plan','BASE'), e.get('Plan','BASE'))}"
                    for e in usuarios_no_admin
                ]
                sel_idx = st.selectbox(
                    "Usuario:",
                    range(len(opciones_labels)),
                    format_func=lambda i: opciones_labels[i],
                    key="admin_sel_usuario_v2"
                )
                nuevo_plan_upg = st.selectbox(
                    "Nuevo Plan:",
                    ["BASE","OPERADOR","ELITE","ESCUADRON","COMANDANCIA"],
                    key="admin_nuevo_plan_v2"
                )
                nueva_exp2 = st.checkbox("Añadir expiración (30 días)", value=False, key="admin_exp_check_v2")

                if st.button("APLICAR PLAN", use_container_width=True, key="btn_aplicar_plan_v2"):
                    usuario_obj   = usuarios_no_admin[sel_idx]
                    nombre_target = usuario_obj["Nombre"]
                    rol_target    = usuario_obj.get("Rol")
                    empresa_target= usuario_obj.get("Empresa")
                    fe = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d") if nueva_exp2 else None
                    actualizado = False
                    for e in st.session_state.empleados:
                        if (e["Nombre"] == nombre_target
                                and e.get("Rol") == rol_target
                                and e.get("Empresa") == empresa_target):
                            e["Plan"] = nuevo_plan_upg
                            if fe:
                                e["Expiracion"] = fe
                            elif "Expiracion" in e:
                                del e["Expiracion"]
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
    if st.button("FORMATEAR PLATAFORMA COMPLETA", use_container_width=True, key="btn_formatear"):
        st.session_state.empleados          = []
        st.session_state.historial_sesiones = []
        st.session_state.escenarios_custom  = {}
        st.session_state.usuario_actual     = None
        guardar_datos(); st.rerun()

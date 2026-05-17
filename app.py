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
import bcrypt
import requests
from urllib.parse import quote

@st.cache_data(ttl=86400)
def buscar_wikipedia(nombre: str):
    try:
        url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{quote(nombre)}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if 'extract' in data:
                return {
                    "titulo": data.get('title', nombre),
                    "resumen": data['extract'][:500],
                    "url": data.get('content_urls', {}).get('desktop', {}).get('page', '')
                }
    except:
        pass
    return None

# ─────────────────────────────────────────
# CONFIGURACIÓN DE SUPERUSUARIO Y PLANES
# ─────────────────────────────────────────
COMANDANTE_SUPREMO = "CRYSIS"
LINKS_PAGO = {
    "OPERADOR":    "https://buy.stripe.com/4gM28r2NU7b15Jf6wGc7u03",
    "ELITE":       "https://buy.stripe.com/bJe3cv2NU3YP1sZ3kuc7u02",
    "ESCUADRON":   "https://buy.stripe.com/dRm5kD3RY52T5Jf08ic7u01",
    "COMANDANCIA": "https://buy.stripe.com/8x23cvfAGdzp7RnaMWc7u00",
}

PLANES_INFO = {
    "BASE":        {"precio": "0€",      "desc": "Individual · 1 op/mes · sin IA",        "ops": 1,     "escenarios": 0,     "agentes": 0,     "elite": False},
    "OPERADOR":    {"precio": "19€/mes", "desc": "Individual · 10 ops/mes · 3 escenarios", "ops": 10,    "escenarios": 3,     "agentes": 0,     "elite": False},
    "ELITE":       {"precio": "49€/mes", "desc": "Individual · ilimitado · IA sin límite", "ops": 99999, "escenarios": 99999, "agentes": 0,     "elite": True},
    "ESCUADRON":   {"precio": "89€/mes", "desc": "Equipo · ilimitado · 15 agentes",        "ops": 99999, "escenarios": 99999, "agentes": 15,    "elite": True},
    "COMANDANCIA": {"precio": "199€/mes","desc": "Enterprise · ilimitado · ∞ agentes",   "ops": 99999, "escenarios": 99999, "agentes": 99999, "elite": True},
}

DIFICULTADES = {
    "RECRUIT":  {"nivel": 1, "color": "#22C87A", "var": "--green2",  "desc": "Sujeto cooperativo. Cede ante argumentos básicos.",
                 "instruccion": "Eres cooperativo, respondes con relativa facilidad, cedes ante argumentos razonables."},
    "OPERATOR": {"nivel": 2, "color": "#5B8EF0", "var": "--blue2",   "desc": "Sujeto resistente. Exige justificaciones, desconfía.",
                 "instruccion": "Eres moderadamente resistente. Exiges justificaciones claras, desconfías."},
    "VETERAN":  {"nivel": 3, "color": "#E8A84A", "var": "--amber2",  "desc": "Sujeto hostil. Agresivo, manipulador, raramente cede.",
                 "instruccion": "Eres hostil y agresivo. Usas tácticas de presión psicológica."},
    "NIGHTMARE":{"nivel": 4, "color": "#E05050", "var": "--red2",    "desc": "Casi impenetrable. Amenazas veladas, silencio.",
                 "instruccion": "Eres extremadamente hostil e impenetrable. Silencios, amenazas veladas, manipulación avanzada."},
}

@st.cache_resource
def init_supabase():
    url: str = st.secrets["SUPABASE_URL"].strip().rstrip("/")
    key: str = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_supabase()

def obtener_fernet(): return Fernet(st.secrets["ENCRYPTION_KEY"])
def cifrar_memoria(datos_dict): return obtener_fernet().encrypt(json.dumps(datos_dict).encode()).decode()
def descifrar_memoria(texto_cifrado):
    try: return json.loads(obtener_fernet().decrypt(texto_cifrado.encode()).decode())
    except: return None

def cargar_datos():
    try:
        response = supabase.table("crysis_data").select("memoria").eq("id", "main").execute()
        if response.data:
            contenido = response.data[0]["memoria"]
            datos = descifrar_memoria(contenido)
            if datos is None: datos = contenido if isinstance(contenido, dict) else {"empleados": [], "historial_sesiones": [], "escenarios_custom": {}}
            if "escenarios_custom" not in datos: datos["escenarios_custom"] = {}
            return datos
    except: pass
    return {"empleados": [], "historial_sesiones": [], "escenarios_custom": {}}

def guardar_datos():
    try:
        datos = {"empleados": st.session_state.empleados, "historial_sesiones": st.session_state.historial_sesiones, "escenarios_custom": st.session_state.escenarios_custom}
        supabase.table("crysis_data").update({"memoria": cifrar_memoria(datos)}).eq("id", "main").execute()
    except Exception as e: st.error(f"Fallo al sincronizar: {e}")

def enviar_correo_2fa(destinatario, codigo):
    try:
        msg = MIMEText(f"Tu código de autorización táctica para CRYSIS es: {codigo}\n\nSi no has solicitado este acceso, reporta una brecha de seguridad inmediatamente.")
        msg['Subject'] = 'CRYSIS | Código de Acceso 2FA'
        msg['From'] = "CRYSIS Security <crysisapp@outlook.com>"
        msg['To'] = destinatario
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls()
        server.login(st.secrets["SMTP_EMAIL"], st.secrets["SMTP_PASS"])
        server.send_message(msg); server.quit()
        return True
    except: return False

def enviar_correo_reset(destinatario, nueva_pass):
    try:
        msg = MIMEText(f"Tu nueva contraseña temporal para CRYSIS es: {nueva_pass}\n\nCámbiala en Ajustes de Cuenta tras acceder.")
        msg['Subject'] = 'CRYSIS | Recuperación de Contraseña'
        msg['From'] = "CRYSIS Security <crysisapp@outlook.com>"
        msg['To'] = destinatario
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls()
        server.login(st.secrets["SMTP_EMAIL"], st.secrets["SMTP_PASS"])
        server.send_message(msg); server.quit()
        return True
    except: return False

def sanitizar_texto(texto):
    if not isinstance(texto, str): texto = str(texto)
    return texto.replace('**','').replace('*','-').replace('•','-').replace('✅','[V]').replace('❌','[X]').encode('latin-1','replace').decode('latin-1')

def generar_pdf_dossier(sesion):
    pdf = FPDF(); pdf.add_page()
    pdf.set_font("Arial",'B',16); pdf.set_text_color(91, 142, 240); pdf.cell(0,10,"CRYSIS | INTELLIGENCE UNIT",ln=True,align='C')
    pdf.set_font("Arial",'B',11); pdf.set_text_color(224, 80, 80); pdf.cell(0,8,"DOSSIER OPERACIONAL CLASIFICADO",ln=True,align='C'); pdf.ln(5)
    pdf.set_font("Arial",'B',10); pdf.set_text_color(200,200,200); pdf.cell(45,8,"OPERADOR:"); pdf.set_font("Arial",'',10); pdf.cell(0,8,sanitizar_texto(sesion.get("Agente","N/A").upper()),ln=True)
    pdf.set_font("Arial",'B',10); pdf.cell(45,8,"FECHA:"); pdf.set_font("Arial",'',10); pdf.cell(0,8,sanitizar_texto(sesion.get("Fecha","N/A")),ln=True)
    pdf.set_font("Arial",'B',10); pdf.cell(45,8,"PROTOCOLO:"); pdf.set_font("Arial",'',10); pdf.cell(0,8,sanitizar_texto(sesion.get("Escenario","N/A")),ln=True)
    pdf.set_font("Arial",'B',10); pdf.cell(45,8,"DIFICULTAD:"); pdf.set_font("Arial",'',10); pdf.cell(0,8,sanitizar_texto(sesion.get("Dificultad","N/A")),ln=True)
    pdf.set_font("Arial",'B',10); pdf.cell(45,8,"EVALUACION FINAL:"); pdf.set_font("Arial",'B',10); pdf.cell(0,8,f"{sesion.get('Nota',0)}/100",ln=True); pdf.ln(10)
    pdf.set_font("Arial",'B',12); pdf.cell(0,8,"1. INFORME DE EVALUACION TACTICA",ln=True); pdf.set_font("Arial",'',10)
    pdf.multi_cell(0,6,sanitizar_texto(sesion.get("Evaluacion",""))); pdf.ln(5)
    if "Transcripcion" in sesion:
        pdf.set_font("Arial",'B',12); pdf.cell(0,8,"2. REGISTRO DE COMUNICACIONES",ln=True); pdf.ln(2)
        for msg in sesion["Transcripcion"]:
            ag = "OPERADOR" if msg["role"] == "user" else "OBJETIVO"
            if msg["role"] == "user": pdf.set_text_color(91, 142, 240)
            else: pdf.set_text_color(224, 80, 80)
            pdf.set_font("Arial",'B',10); pdf.cell(0,6,f"{ag}:",ln=True)
            pdf.set_text_color(200,200,200); pdf.set_font("Arial",'',10)
            pdf.multi_cell(0,6,sanitizar_texto(msg["content"])); pdf.ln(2)
    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else out

# ─────────────────────────────────────────
# ESTADOS, RUTAS Y QUERY PARAMS
# ─────────────────────────────────────────
st.set_page_config(page_title="CRYSIS | Intelligence Unit", layout="wide", initial_sidebar_state="collapsed")

if "sidebar_collapsed" not in st.session_state: st.session_state.sidebar_collapsed = False
if "pantalla_actual"   not in st.session_state: st.session_state.pantalla_actual   = "menu"

# Interceptar la navegación por URL (Botones de la barra lateral HTML)
qp = st.query_params
if "menu" in qp:
    nav = qp["menu"]
    if nav == "toggle": st.session_state.sidebar_collapsed = not st.session_state.sidebar_collapsed
    elif nav in ["menu", "estadisticas", "simulador", "expedientes", "sintesis", "personal", "admin", "cuenta"]:
        st.session_state.pantalla_actual = nav
    st.query_params.clear()
    st.rerun()

# Carga de datos base
datos_guardados = cargar_datos()
if "empleados"          not in st.session_state: st.session_state.empleados          = datos_guardados["empleados"]
if "historial_sesiones" not in st.session_state: st.session_state.historial_sesiones = datos_guardados["historial_sesiones"]
if "escenarios_custom"  not in st.session_state: st.session_state.escenarios_custom  = datos_guardados.get("escenarios_custom", {})
if "mensajes"           not in st.session_state: st.session_state.mensajes           = []
if "evaluacion_actual"  not in st.session_state: st.session_state.evaluacion_actual  = None
if "mision_iniciada"    not in st.session_state: st.session_state.mision_iniciada    = False
if "usuario_actual"     not in st.session_state: st.session_state.usuario_actual     = None
if "login_step"         not in st.session_state: st.session_state.login_step         = 1
if "login_modo"         not in st.session_state: st.session_state.login_modo         = "acceso"
if "login_subpantalla"  not in st.session_state: st.session_state.login_subpantalla  = "main"
if "dificultad_actual"  not in st.session_state: st.session_state.dificultad_actual  = "OPERATOR"
if "tension_actual"     not in st.session_state: st.session_state.tension_actual     = 0

try: GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except: GROQ_API_KEY = None

INSTRUCCION_ORTOGRAFIA = " Escribe en español correcto. Nunca uses acotaciones entre paréntesis. Solo diálogo."
CONTEXTOS_MISION = {
    "OPERACION: FRONTERA":   {"contexto": "Tensiones militares en el paralelo 38.", "perfil_sujeto": "Ministro Volkov.", "objetivo": "Evitar la escalada bélica.", "prompt": "Eres el Ministro de Defensa de Krasnovia. Hostil y burocrático. Solo diálogo directo." + INSTRUCCION_ORTOGRAFIA},
    "OPERACION: BLACKOUT":   {"contexto": "Ataque masivo al sistema eléctrico nacional. Rescate exigido.", "perfil_sujeto": "'Shadow'. Hacker mercenario.", "objetivo": "Ganar tiempo.", "prompt": "Eres Shadow, hacker de elite acorralado. Solo texto directo. Sin emociones." + INSTRUCCION_ORTOGRAFIA},
    "OPERACION: EXTRACCION": {"contexto": "Robo a banco fallido. 3 civiles retenidos.", "perfil_sujeto": "Sujeto inestable, bajo presión extrema.", "objetivo": "Asegurar liberación.", "prompt": "Eres un secuestrador acorralado. Gritas, estás nervioso. Solo diálogo crudo." + INSTRUCCION_ORTOGRAFIA},
}
PLOTLY_THEME = dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family='Inter', color='#7A8AAE', size=12), margin=dict(l=16,r=16,t=40,b=16))

# ─────────────────────────────────────────
# CSS GLOBAL & MOCKUP STYLES INJECTION
# ─────────────────────────────────────────
st.markdown("""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.44.0/tabler-icons.min.css">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --bg:#090C14; --bg2:#0D1020; --bg3:#111525; --bd:#1C2338; --bd2:#252E48;
  --blue:#3B6EE8; --blue2:#5B8EF0; --blue3:#1A2540;
  --green2:#22C87A; --green3:#0E2219;
  --amber2:#E8A84A; --amber3:#221A0E; --amber:#B87818;
  --purple2:#A97FF5; --purple3:#160E22;
  --red:#C0302E; --red2:#E05050; --red3:#220E0E;
  --text:#E4EAF8; --text2:#7A8AAE; --text3:#3A4560;
  --sb-w:210px; --sb-w-min:68px;
}

/* STREAMLIT OVERRIDES */
html, body, [class*="css"], .stApp { background-color: var(--bg) !important; color: var(--text) !important; font-family: 'Inter', sans-serif !important; }
header[data-testid="stHeader"], .stDeployButton, #MainMenu, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; margin: 0 !important; }

/* TWEAK INPUTS */
.stTextInput input, .stSelectbox > div > div, .stTextArea textarea {
  background: var(--bg3) !important; border: 0.5px solid var(--bd2) !important;
  color: var(--text) !important; border-radius: 7px !important; font-size: 13px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--blue2) !important; box-shadow: 0 0 0 1px var(--blue2) !important; }
.stTextInput label, .stTextArea label, .stSelectbox label { color: var(--text3) !important; font-size: 11px !important; letter-spacing: .06em !important; text-transform: uppercase !important; }

/* TWEAK BUTTONS */
.stButton > button {
  background: var(--blue) !important; color: #fff !important; font-weight: 500 !important;
  border: none !important; border-radius: 7px !important; padding: 10px 18px !important; font-size: 12px !important; transition: all .15s !important;
}
.stButton > button:hover { background: var(--blue2) !important; transform: translateY(-1px); }
button[kind="secondary"] { background: transparent !important; border: 0.5px solid var(--bd2) !important; color: var(--text2) !important; }
button[kind="secondary"]:hover { background: var(--bg3) !important; color: var(--text) !important; border-color: var(--bd2) !important; }

/* HACK CHAT NATIVO (Oculta avatares y quita padding extra para dar paso al diseño HTML) */
[data-testid="stChatMessage"] { background: transparent !important; padding: 0 !important; border: none !important; margin-bottom: 4px !important; }
[data-testid="chatAvatarIcon-user"], [data-testid="chatAvatarIcon-assistant"], .st-emotion-cache-1c7y2kd { display: none !important; }
[data-testid="stChatMessage"] > div { padding: 0 !important; }

/* MOCKUP CUSTOM CLASSES */
.cry-sidebar { width: var(--sb-w); height: 100vh; background: var(--bg2); border-right: 0.5px solid var(--bd); padding: 16px 12px; display: flex; flex-direction: column; gap: 4px; transition: width .25s; overflow: hidden; position: fixed; left: 0; top: 0; z-index: 100; }
.cry-sidebar.collapsed { width: var(--sb-w-min); padding: 16px 8px; }
.cry-sidebar .logo { display: flex; align-items: center; gap: 9px; margin-bottom: 24px; padding: 0 4px; overflow: hidden; }
.cry-sidebar .logomark { width: 28px; height: 28px; background: var(--blue); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 600; color: #fff; letter-spacing: .04em; flex-shrink: 0; }
.cry-sidebar .logoname { font-size: 14px; font-weight: 600; color: var(--text); letter-spacing: .1em; white-space: nowrap; transition: opacity .2s; }
.cry-sidebar.collapsed .logoname { opacity: 0; width: 0; }
.cry-sidebar .ns { font-size: 10px; color: var(--text3); letter-spacing: .12em; padding: 0 8px; margin: 16px 0 6px; text-transform: uppercase; white-space: nowrap; transition: opacity .15s; }
.cry-sidebar.collapsed .ns { opacity: 0; height: 0; margin: 0; padding: 0; }
.cry-ni { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 7px; font-size: 13px; color: var(--text2); text-decoration: none !important; transition: all .15s; white-space: nowrap; overflow: hidden; }
.cry-ni:hover { background: var(--bg3); color: var(--text); }
.cry-ni.active { background: var(--blue3); color: var(--blue2); }
.cry-ni i { font-size: 18px; flex-shrink: 0; }
.cry-sidebar.collapsed .cry-ni span { opacity: 0; width: 0; }
.cry-sidebar.collapsed .cry-ni { justify-content: center; padding: 10px; }
.cry-toggle { position: absolute; right: -14px; top: 20px; width: 28px; height: 28px; background: var(--bg2); border: 0.5px solid var(--bd); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--text2); text-decoration: none; z-index: 101; transition: color .2s; cursor:pointer;}
.cry-toggle:hover { color: var(--text); background: var(--bg3); }

.main-content { margin-left: var(--sb-w); padding: 32px 40px; min-height: 100vh; transition: margin-left .25s; }
.main-content.expanded { margin-left: var(--sb-w-min); }

.topbar { display: flex; align-items: center; justify-content: flex-end; padding-bottom: 24px; border-bottom: 0.5px solid var(--bd); margin-bottom: 32px; gap: 12px; }
.badge { font-size: 11px; padding: 3px 10px; border-radius: 20px; background: var(--blue3); color: var(--blue2); letter-spacing: .04em; font-weight: 500; }
.avatar { width: 32px; height: 32px; border-radius: 50%; background: #1E2D50; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; color: var(--blue2); border: 1px solid var(--blue3);}

.ph { margin-bottom: 28px; }
.pg { font-size: 24px; font-weight: 600; color: var(--text); margin-bottom: 4px; letter-spacing: -0.01em; }
.ps { font-size: 13px; color: var(--text3); }
.dot { color: var(--blue); margin: 0 6px; }

.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
.metric { background: var(--bg3); border: 0.5px solid var(--bd); border-radius: 10px; padding: 16px 20px; position: relative; overflow: hidden; }
.metric::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--blue2); }
.ml { font-size: 11px; color: var(--text3); margin-bottom: 8px; letter-spacing: .06em; text-transform: uppercase; }
.mv { font-size: 26px; font-weight: 600; color: var(--text); line-height: 1; }

.seclabel { font-size: 11px; color: var(--text3); letter-spacing: .1em; text-transform: uppercase; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 0.5px solid var(--bd); font-weight: 500; }
.box { background: var(--bg3); border: 0.5px solid var(--bd); border-radius: 10px; padding: 20px; }
.diffcard { background: var(--bg3); border: 0.5px solid var(--bd); border-radius: 9px; padding: 16px; cursor: pointer; transition: all .2s; }
.diffcard:hover { border-color: var(--bd2); transform: translateY(-2px); }
.diffcard.sel { background: var(--blue3); border-color: var(--blue2); }
.difflvl { font-size: 12px; letter-spacing: .1em; text-transform: uppercase; margin-bottom: 4px; font-weight: 600; }
.diffdesc { font-size: 12px; color: var(--text3); margin-top: 6px; line-height: 1.5; }

/* LOGIN SHELL */
.login-shell { background: var(--bg); border: 0.5px solid var(--bd); border-radius: 12px; overflow: hidden; display: flex; max-width: 900px; margin: 80px auto; min-height: 500px; box-shadow: 0 20px 40px rgba(0,0,0,0.4); }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# LOGIN FLOW (NO SIDEBAR)
# ─────────────────────────────────────────
if st.session_state.usuario_actual is None:
    st.markdown('<div class="login-shell">', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1], gap="small")
    
    with c1:
        st.markdown("""
        <div style="background:var(--bg2); padding: 48px 40px; height: 100%; border-right: 0.5px solid var(--bd); display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="font-size:32px; font-weight:700; color:var(--text); letter-spacing:.12em; margin-bottom:4px">CRYSIS</div>
                <div style="font-size:11px; color:var(--blue2); letter-spacing:.25em; text-transform:uppercase; margin-bottom:24px">Intelligence Unit</div>
                <div style="width:32px; height:2px; background:var(--blue); margin-bottom:18px"></div>
                <div style="font-size:13px; color:var(--text3); line-height:1.7">Plataforma de simulación táctica avanzada para entrenamiento en negociación y desescalada bajo presión extrema.</div>
            </div>
            <div>
                <div style="font-size:10px; color:var(--text3); letter-spacing:.12em; text-transform:uppercase; margin-bottom:6px">Estado del sistema</div>
                <div style="font-size:12px; color:var(--green2); font-weight:500;">● Operativo · Acceso seguro</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown('<div style="padding: 48px 40px;">', unsafe_allow_html=True)
        if st.session_state.login_subpantalla == "forgot":
            st.markdown("<div class='seclabel'>RECUPERACIÓN DE ACCESO</div>", unsafe_allow_html=True)
            with st.form("forgot"):
                rid = st.text_input("ID Operativo")
                remail = st.text_input("Correo Registrado")
                if st.form_submit_button("ENVIAR CLAVE", use_container_width=True):
                    agente_r = next((e for e in st.session_state.empleados if e["Nombre"] == rid and e.get("Email","").lower() == remail.lower()), None)
                    if agente_r:
                        np = str(random.randint(100000, 999999))
                        if enviar_correo_reset(remail, np):
                            for e in st.session_state.empleados:
                                if e["Nombre"] == rid: e["Password"] = np
                            guardar_datos(); st.success("Clave enviada.")
                        else: st.error("Error al enviar.")
                    else: st.error("Datos no coinciden.")
                if st.form_submit_button("VOLVER", type="secondary", use_container_width=True):
                    st.session_state.login_subpantalla = "main"; st.rerun()
        else:
            t1, t2 = st.columns(2)
            if t1.button("Acceso", type="primary" if st.session_state.login_modo=="acceso" else "secondary", use_container_width=True): st.session_state.login_modo="acceso"; st.rerun()
            if t2.button("Registro", type="primary" if st.session_state.login_modo=="registro" else "secondary", use_container_width=True): st.session_state.login_modo="registro"; st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)

            if st.session_state.login_modo == "acceso":
                if st.session_state.login_step == 1:
                    with st.form("login"):
                        uid = st.text_input("ID Operativo")
                        upass = st.text_input("Clave de Seguridad", type="password")
                        if st.form_submit_button("INICIAR SESIÓN", use_container_width=True):
                            ag = next((e for e in st.session_state.empleados if e["Nombre"] == uid and e.get("Password") == upass), None)
                            if ag:
                                if ag.get("2FA_Verificado", False) or ag["Nombre"] == COMANDANTE_SUPREMO:
                                    st.session_state.usuario_actual = ag; st.rerun()
                                else:
                                    st.session_state["2fa_code"] = str(random.randint(100000, 999999)); st.session_state["2fa_agente"] = ag; st.session_state.login_step = 2; st.rerun()
                            else: st.error("Credenciales inválidas.")
                    if st.button("¿Olvidaste tu contraseña?", type="secondary"): st.session_state.login_subpantalla = "forgot"; st.rerun()
                elif st.session_state.login_step == 2:
                    st.info("Revisa tu correo para el código 2FA.")
                    with st.form("2fa"):
                        ucode = st.text_input("Código de 6 dígitos")
                        if st.form_submit_button("VERIFICAR", use_container_width=True):
                            if ucode == st.session_state["2fa_code"]:
                                st.session_state["2fa_agente"]["2FA_Verificado"] = True; guardar_datos()
                                st.session_state.usuario_actual = st.session_state["2fa_agente"]; st.session_state.login_step = 1; st.rerun()
                            else: st.error("Código incorrecto.")
            else:
                st.markdown("<div class='seclabel'>SELECCIONA TU PLAN</div>", unsafe_allow_html=True)
                plan = st.selectbox("Plan", ["BASE (Gratis)", "OPERADOR (19€/m)", "ELITE (49€/m)", "ESCUADRON (Equipos)"])
                plan_key = plan.split(" ")[0]
                with st.form("reg"):
                    n = st.text_input("ID / Entidad")
                    email = st.text_input("Correo")
                    p = st.text_input("Contraseña", type="password")
                    if st.form_submit_button("CREAR CUENTA", use_container_width=True):
                        if n and p and email:
                            if any(e["Nombre"] == n for e in st.session_state.empleados): st.warning("ID ya en uso.")
                            else:
                                nu = {"Nombre": n, "Email": email, "Rol": "Empresa" if plan_key in ["ESCUADRON"] else "Individual", "Plan": plan_key, "Password": p, "2FA_Verificado": True}
                                st.session_state.empleados.append(nu); guardar_datos()
                                st.session_state.usuario_actual = nu; st.rerun()
                        else: st.warning("Completa los campos.")
        st.markdown('</div></div>', unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────
# MAIN APP (LOGGED IN)
# ─────────────────────────────────────────
u = st.session_state.usuario_actual
es_emp = u.get("Rol") == "Empresa" or u["Nombre"] == COMANDANTE_SUPREMO
emp_act = u.get("Empresa", u["Nombre"])
mi_plan = u.get("Plan", "BASE")
if u["Nombre"] == COMANDANTE_SUPREMO: mi_plan = "COMANDANCIA"

col_collapsed = st.session_state.sidebar_collapsed
p_act = st.session_state.pantalla_actual

# HTML SIDEBAR GENERATION
sb_html = f"""
<div class="cry-sidebar {'collapsed' if col_collapsed else ''}">
    <a href="/?menu=toggle" target="_self" class="cry-toggle"><i class="ti ti-chevron-{'right' if col_collapsed else 'left'}"></i></a>
    <div class="logo">
        <div class="logomark">CRY</div>
        <div class="logoname">CRYSIS</div>
    </div>
    
    <div class="ns">Principal</div>
    <a href="/?menu=menu" target="_self" class="cry-ni {'active' if p_act=='menu' else ''}"><i class="ti ti-layout-dashboard"></i><span>Inicio</span></a>
    <a href="/?menu=simulador" target="_self" class="cry-ni {'active' if p_act=='simulador' else ''}"><i class="ti ti-shield"></i><span>Simulador</span></a>
    <a href="/?menu=estadisticas" target="_self" class="cry-ni {'active' if p_act=='estadisticas' else ''}"><i class="ti ti-chart-bar"></i><span>Estadísticas</span></a>
    <a href="/?menu=expedientes" target="_self" class="cry-ni {'active' if p_act=='expedientes' else ''}"><i class="ti ti-folder"></i><span>Expedientes</span></a>
    
    <div class="ns">Avanzado</div>
    <a href="/?menu=sintesis" target="_self" class="cry-ni {'active' if p_act=='sintesis' else ''}"><i class="ti ti-sparkles"></i><span>Escenarios IA</span></a>
    {"<a href='/?menu=personal' target='_self' class='cry-ni "+('active' if p_act=='personal' else '')+"'><i class='ti ti-users'></i><span>Agentes</span></a>" if es_emp else ""}
    {"<a href='/?menu=admin' target='_self' class='cry-ni "+('active' if p_act=='admin' else '')+"'><i class='ti ti-server'></i><span>Consola Omega</span></a>" if u["Nombre"]==COMANDANTE_SUPREMO else ""}
    
    <div style="flex:1"></div>
    <div class="ns">Sistema</div>
    <a href="/?menu=cuenta" target="_self" class="cry-ni {'active' if p_act=='cuenta' else ''}"><i class="ti ti-settings"></i><span>Tu Cuenta</span></a>
</div>
"""
st.markdown(sb_html, unsafe_allow_html=True)

# MAIN CONTENT WRAPPER
st.markdown(f'<div class="main-content {'expanded' if col_collapsed else ''}">', unsafe_allow_html=True)

# TOPBAR
st.markdown(f"""
<div class="topbar">
    <div class="badge">{mi_plan.upper()}</div>
    <div class="avatar">{u['Nombre'][:2].upper()}</div>
    <a href="/?menu=logout" target="_self" style="color:var(--text2); text-decoration:none; margin-left:8px; display:flex; align-items:center;"><i class="ti ti-logout" style="font-size:20px;"></i></a>
</div>
""", unsafe_allow_html=True)

if p_act == "logout":
    st.session_state.usuario_actual = None; st.session_state.pantalla_actual = "menu"; st.query_params.clear(); st.rerun()

# ─────────────────────────────────────────
# PANTALLAS (Lógica de Contenido)
# ─────────────────────────────────────────
historial = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"] or es_emp]

if p_act == "menu":
    st.markdown(f"""
    <div class="ph">
        <div class="pg">Buenos días, {u['Nombre'].upper()}</div>
        <div class="ps">{datetime.now().strftime("%d %b %Y")} <span class="dot">·</span> Red Global Segura <span class="dot">·</span> Unidad: {emp_act.upper()}</div>
    </div>
    """, unsafe_allow_html=True)
    
    t_ops = len(historial)
    media = int(sum(s["Nota"] for s in historial)/t_ops) if t_ops>0 else 0
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric"><div class="ml">Rendimiento Medio</div><div class="mv" style="color:var(--green2)">{media}%</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric"><div class="ml">Misiones Completadas</div><div class="mv" style="color:var(--blue2)">{t_ops}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric"><div class="ml">Estado de Licencia</div><div class="mv" style="color:var(--amber2)">ACTIVA</div></div>', unsafe_allow_html=True)

elif p_act == "simulador":
    st.markdown('<div class="ph"><div class="pg">Simulador Táctico</div><div class="ps">Configura y despliega un escenario de negociación.</div></div>', unsafe_allow_html=True)
    
    if not st.session_state.mision_iniciada:
        escenarios = {**CONTEXTOS_MISION, **st.session_state.escenarios_custom}
        esc_sel = st.selectbox("Seleccionar Protocolo:", list(escenarios.keys()))
        
        st.markdown("<br><div class='seclabel'>NIVEL DE DIFICULTAD</div>", unsafe_allow_html=True)
        c_d = st.columns(4)
        for i, (dn, dd) in enumerate(DIFICULTADES.items()):
            sel = st.session_state.dificultad_actual == dn
            c_d[i].markdown(f"""
            <div class="diffcard {'sel' if sel else ''}" style="border-color:{dd['color'] if sel else 'var(--bd)'}">
                <div class="difflvl" style="color:{dd['color']}">{dn}</div>
                <div style="font-size:10px;color:{dd['color']};opacity:0.7;">Lvl {dd['nivel']}</div>
                <div class="diffdesc">{dd['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
            if c_d[i].button(f"Seleccionar {dn}", key=f"btn_d_{dn}", use_container_width=True):
                st.session_state.dificultad_actual = dn; st.rerun()
                
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("INICIAR ENLACE DE COMUNICACIÓN", type="primary"):
            st.session_state.mision_iniciada = True; st.session_state.escenario_activo = esc_sel; st.session_state.mensajes = []; st.rerun()
            
    else:
        # SESIÓN ACTIVA (CHAT COLORIDO HACKEADO)
        dif = st.session_state.dificultad_actual
        c_dif = DIFICULTADES[dif]["color"]
        st.markdown(f"""
        <div class="box" style="border-left:3px solid {c_dif}; margin-bottom:24px;">
            <div style="font-size:10px; color:{c_dif}; letter-spacing:.1em; margin-bottom:8px; text-transform:uppercase;">ENLACE ACTIVO</div>
            <div style="font-size:16px; font-weight:600; color:var(--text);">{st.session_state.escenario_activo}</div>
            <div style="font-size:12px; color:var(--text3); margin-top:4px;">DIFICULTAD: {dif}</div>
        </div>
        """, unsafe_allow_html=True)

        # Renderizar Chat
        for m in st.session_state.mensajes:
            role = m["role"]
            with st.chat_message(role):
                if role == "user":
                    st.markdown(f"""
                    <div style="background:var(--blue3); border:0.5px solid var(--bd2); border-left:3px solid var(--blue2); border-radius:8px; padding:12px 16px;">
                        <div style="font-size:10px; color:var(--blue2); letter-spacing:.1em; margin-bottom:6px; text-transform:uppercase;">TÚ (Operador)</div>
                        <div style="color:var(--text); font-size:13px; line-height:1.6;">{m['content']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background:var(--red3); border:0.5px solid var(--bd2); border-left:3px solid var(--red2); border-radius:8px; padding:12px 16px;">
                        <div style="font-size:10px; color:var(--red2); letter-spacing:.1em; margin-bottom:6px; text-transform:uppercase;">SUJETO</div>
                        <div style="color:var(--text); font-size:13px; line-height:1.6;">{m['content']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
        prompt = st.chat_input("Introduce tu respuesta táctica...")
        if prompt:
            st.session_state.mensajes.append({"role": "user", "content": prompt})
            if GROQ_API_KEY:
                client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                esc = {**CONTEXTOS_MISION, **st.session_state.escenarios_custom}[st.session_state.escenario_activo]
                sys_p = esc["prompt"] + f" [Dificultad: {DIFICULTADES[dif]['instruccion']}]"
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":sys_p}] + st.session_state.mensajes).choices[0].message.content
                st.session_state.mensajes.append({"role": "assistant", "content": res})
            st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("FINALIZAR Y EVALUAR", type="secondary"):
            st.session_state.historial_sesiones.append({
                "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "Agente": u["Nombre"], 
                "Escenario": st.session_state.escenario_activo, "Nota": random.randint(40, 95), # Mock evaluation for simplicity
                "Dificultad": dif, "Evaluacion": "Simulación finalizada por el operador.", "Transcripcion": st.session_state.mensajes
            }); guardar_datos()
            st.session_state.mision_iniciada = False; st.session_state.pantalla_actual = "expedientes"; st.rerun()

elif p_act == "estadisticas":
    st.markdown('<div class="ph"><div class="pg">Análisis de Rendimiento</div><div class="ps">Métricas de evolución operativa.</div></div>', unsafe_allow_html=True)
    if historial:
        df = pd.DataFrame(historial)
        c1, c2 = st.columns(2)
        fig = px.line(df, y="Nota", title="Evolución de Puntuación", markers=True, template="plotly_dark", color_discrete_sequence=["#5B8EF0"])
        fig.update_layout(**PLOTLY_THEME, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        c1.plotly_chart(fig, use_container_width=True)
    else: st.info("No hay datos suficientes para mostrar estadísticas.")

elif p_act == "expedientes":
    st.markdown('<div class="ph"><div class="pg">Archivo Operacional</div><div class="ps">Dossiers de misiones pasadas.</div></div>', unsafe_allow_html=True)
    for s in reversed(historial):
        with st.expander(f"{s['Fecha']} | {s['Escenario']} | Nota: {s['Nota']}%"):
            st.write(f"**Dificultad:** {s.get('Dificultad', '—')}")
            st.write(f"**Evaluación:** {s['Evaluacion']}")
            if st.button("Eliminar Expediente", key=f"del_{s['Fecha']}"):
                st.session_state.historial_sesiones.remove(s); guardar_datos(); st.rerun()

else:
    st.markdown(f'<div class="ph"><div class="pg">{p_act.capitalize()}</div><div class="ps">Módulo en construcción.</div></div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True) # Cierra main-content

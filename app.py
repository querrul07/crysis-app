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
import hashlib

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
# CONFIGURACIÓN DE SUPERUSUARIO
# ─────────────────────────────────────────
COMANDANTE_SUPREMO = "CRYSIS"
LINKS_PAGO = {
    "OPERADOR":    "https://buy.stripe.com/4gM28r2NU7b15Jf6wGc7u03",
    "ELITE":       "https://buy.stripe.com/bJe3cv2NU3YP1sZ3kuc7u02",
    "ESCUADRON":   "https://buy.stripe.com/dRm5kD3RY52T5Jf08ic7u01",
    "COMANDANCIA": "https://buy.stripe.com/8x23cvfAGdzp7RnaMWc7u00",
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

# ─────────────────────────────────────────
# SISTEMA DE PROGRESIÓN: NIVELES Y LOGROS
# ─────────────────────────────────────────
NIVELES_XP = [
    (0,    "RECRUIT",    "#00D4A0"),
    (300,  "OPERATIVE",  "#4F8EF7"),
    (700,  "SPECIALIST", "#A855F7"),
    (1400, "AGENT",      "#F0A500"),
    (2800, "ELITE",      "#E8394A"),
    (5000, "COMMANDER",  "#FFD700"),
]

LOGROS_DEF = {
    "PRIMERA_MISION":  {"i":"◈","nombre":"Bautismo de Fuego",   "desc":"Completa tu primera misión",            "xp":50},
    "PUNTUACION_90":   {"i":"◉","nombre":"Precisión Quirúrgica", "desc":"Consigue 90+ en una misión",            "xp":100},
    "PUNTUACION_100":  {"i":"★","nombre":"Operación Perfecta",   "desc":"Consigue 100/100 en una misión",        "xp":250},
    "RACHA_3":         {"i":"▲","nombre":"Impulso Táctico",      "desc":"3 días consecutivos entrenando",        "xp":75},
    "RACHA_7":         {"i":"◆","nombre":"Semana de Acero",      "desc":"7 días consecutivos",                   "xp":200},
    "RACHA_30":        {"i":"✦","nombre":"Agente Incansable",    "desc":"30 días consecutivos",                  "xp":1000},
    "MISIONES_10":     {"i":"▸","nombre":"Veterano de Campo",    "desc":"Completa 10 misiones",                  "xp":100},
    "MISIONES_50":     {"i":"▶","nombre":"Agente de Élite",      "desc":"Completa 50 misiones",                  "xp":400},
    "NIGHTMARE_WIN":   {"i":"☠","nombre":"Pesadilla Domada",     "desc":"Supera NIGHTMARE con puntuación +60",   "xp":300},
    "DIARIA_X7":       {"i":"◐","nombre":"Disciplina Táctica",   "desc":"7 misiones diarias completadas",        "xp":200},
    "PRIMER_ESC":      {"i":"◇","nombre":"Arquitecto Táctico",   "desc":"Crea tu primer escenario personalizado","xp":150},
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
            datos = descifrar_memoria(contenido)
            if datos is None: datos = contenido if isinstance(contenido, dict) else {"empleados": [], "historial_sesiones": [], "escenarios_custom": {}}
            if "escenarios_custom" not in datos: datos["escenarios_custom"] = {}
            datos["empleados"] = [e for e in datos.get("empleados", []) if "Rol" in e]
            # Inicializar campos de progresión para usuarios antiguos
            for e in datos.get("empleados", []):
                for campo, defecto in [("xp",0), ("logros",[]), ("racha",0), ("ultima_sesion",""), ("diarias",0), ("diaria_hoy","")]:
                    if campo not in e:
                        e[campo] = defecto
            return datos
    except Exception as e:
        st.error(f"Error al conectar con Base de Datos: {e}")
    return {"empleados": [], "historial_sesiones": [], "escenarios_custom": {}}

def guardar_usuario_plano(nombre, email, plan="BASE"):
    try:
        data = {"nombre": nombre, "email": email, "plan": plan}
        supabase.table("usuarios").upsert(data, on_conflict="nombre").execute()
    except:
        pass

def guardar_datos():
    try:
        datos_actualizados = {
            "empleados": st.session_state.empleados,
            "historial_sesiones": st.session_state.historial_sesiones,
            "escenarios_custom": st.session_state.escenarios_custom
        }
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
        msg['From']    = "CRYSIS Security <crysisapp@outlook.com>"
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
        msg['From']    = "CRYSIS Security <crysisapp@outlook.com>"
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
# HELPERS DE PROGRESIÓN
# ─────────────────────────────────────────
def recalcular_xp_historico():
    """Recalcula el XP de todos los usuarios basado en sus misiones pasadas."""
    for empleado in st.session_state.empleados:
        # Saltar si ya tiene XP > 0 (asumimos que ya está actualizado)
        if empleado.get("xp", 0) > 0:
            continue
        # Obtener todas las misiones de este agente
        misiones = [s for s in st.session_state.historial_sesiones if s["Agente"] == empleado["Nombre"]]
        if not misiones:
            continue
        total_xp = 0
        for m in misiones:
            nota = m.get("Nota", 0)
            dificultad = m.get("Dificultad", "OPERATOR")
            dif_mult = {1: 1.0, 2: 1.3, 3: 1.6, 4: 2.0}
            niv = DIFICULTADES.get(dificultad, {}).get("nivel", 2)
            xp_base = int((nota / 2) * dif_mult.get(niv, 1.0))
            total_xp += xp_base
        empleado["xp"] = total_xp
        # Inicializar racha (aproximada: si la última misión fue hoy)
        if misiones:
            ult_fecha = max(datetime.strptime(m["Fecha"], "%Y-%m-%d %H:%M") for m in misiones)
            if ult_fecha.date() == datetime.now().date():
                empleado["racha"] = 1
            else:
                empleado["racha"] = 0
    guardar_datos()

def get_nivel_usuario(xp_total):
    nivel_actual = NIVELES_XP[0]
    siguiente    = None
    for i, nivel in enumerate(NIVELES_XP):
        if xp_total >= nivel[0]:
            nivel_actual = nivel
            siguiente = NIVELES_XP[i + 1] if i + 1 < len(NIVELES_XP) else None
    if siguiente:
        xp_en_nivel = xp_total - nivel_actual[0]
        rango       = siguiente[0] - nivel_actual[0]
        pct         = min(99, int((xp_en_nivel / rango) * 100))
        falta       = siguiente[0] - xp_total
    else:
        pct, falta = 100, 0
    return nivel_actual[1], nivel_actual[2], falta, pct

def get_mision_diaria_hoy():
    today    = datetime.now().strftime("%Y-%m-%d")
    h        = int(hashlib.md5(today.encode()).hexdigest(), 16)
    keys     = list(CONTEXTOS_MISION.keys())
    difs     = list(DIFICULTADES.keys())
    return {
        "escenario":  keys[h % len(keys)],
        "dificultad": difs[(h // 1000) % len(difs)],
        "fecha":      today,
        "bonus_xp":   80,
    }

def generar_mision_diaria_ia():
    """Genera una misión diaria única usando Groq (si está disponible)."""
    if not GROQ_API_KEY:
        # Fallback a misión predefinida
        return get_mision_diaria_hoy()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    # Si ya generamos una hoy, la devolvemos
    if "mision_diaria_cache" in st.session_state and st.session_state.mision_diaria_cache.get("fecha") == today_str:
        return st.session_state.mision_diaria_cache["mision"]
    
    try:
        client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        prompt = f"""Eres un diseñador de escenarios tácticos. Genera una MISIÓN DIARIA completamente original para hoy {today_str}.
La misión debe ser realista, de negociación o inteligencia, con un nombre atractivo (ej: OPERACIÓN: ECO PROFUNDO).
Devuelve SOLO JSON con estas claves:
{{
    "nombre_op": "OPERACIÓN: ...",
    "contexto": "texto del contexto (situación actual)",
    "perfil_sujeto": "descripción detallada del sujeto (nombre, motivaciones, debilidad)",
    "objetivo": "objetivo claro y medible",
    "prompt": "Instrucciones para la IA: eres [nombre]. [rol]. Responde en español, solo diálogo, sin acotaciones."
}}
La dificultad será aleatoria pero debe ser entre RECRUIT y NIGHTMARE. NO uses los mismos escenarios de siempre.
"""
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content": prompt}],
            response_format={"type":"json_object"}
        ).choices[0].message.content
        nueva_mision = json.loads(res)
        # Elegir dificultad aleatoria (puede ser fija o según día)
        import random
        random.seed(int(hashlib.md5(today_str.encode()).hexdigest(), 16))
        dificultad = random.choice(list(DIFICULTADES.keys()))
        mision = {
            "escenario": nueva_mision["nombre_op"],
            "dificultad": dificultad,
            "fecha": today_str,
            "bonus_xp": 80,
            "datos": nueva_mision
        }
        # Cachear
        st.session_state.mision_diaria_cache = {"fecha": today_str, "mision": mision}
        return mision
    except Exception as e:
        # Fallback seguro
        return get_mision_diaria_hoy()

def otorgar_xp_y_logros(nombre_agente, nota, dificultad, es_diaria=False):
    dif_mult = {1: 1.0, 2: 1.3, 3: 1.6, 4: 2.0}
    niv      = DIFICULTADES.get(dificultad, {}).get("nivel", 1)
    xp_base  = int((nota / 2) * dif_mult.get(niv, 1.0))
    xp_total = xp_base + (80 if es_diaria else 0)

    nuevos_logros = []
    hoy  = datetime.now().strftime("%Y-%m-%d")
    ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    for e in st.session_state.empleados:
        if e["Nombre"] != nombre_agente:
            continue
        # Aseguramos campos
        for campo, defecto in [("xp", 0), ("logros", []), ("racha", 0),
                                ("ultima_sesion", ""), ("diarias", 0), ("diaria_hoy", "")]:
            if campo not in e:
                e[campo] = defecto

        e["xp"] += xp_total

        # Racha diaria
        if e["ultima_sesion"] == ayer:
            e["racha"] += 1
        elif e["ultima_sesion"] != hoy:
            e["racha"] = 1
        e["ultima_sesion"] = hoy

        if es_diaria and e["diaria_hoy"] != hoy:
            e["diaria_hoy"] = hoy
            e["diarias"]   += 1

        total_misiones = len([s for s in st.session_state.historial_sesiones
                               if s["Agente"] == nombre_agente])
        checks = {
            "PRIMERA_MISION": total_misiones >= 1,
            "PUNTUACION_90":  nota >= 90,
            "PUNTUACION_100": nota >= 100,
            "RACHA_3":        e["racha"] >= 3,
            "RACHA_7":        e["racha"] >= 7,
            "RACHA_30":       e["racha"] >= 30,
            "MISIONES_10":    total_misiones >= 10,
            "MISIONES_50":    total_misiones >= 50,
            "NIGHTMARE_WIN":  dificultad == "NIGHTMARE" and nota >= 60,
            "DIARIA_X7":      e["diarias"] >= 7,
            "PRIMER_ESC":     len(st.session_state.escenarios_custom) >= 1,
        }
        for key, ok in checks.items():
            if ok and key not in e["logros"]:
                e["logros"].append(key)
                nuevos_logros.append(key)
                e["xp"] += LOGROS_DEF[key]["xp"]
        break

    return xp_total, nuevos_logros

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

.topbar { display: flex; align-items: center; justify-content: space-between; padding: 16px 0 12px 0; border-bottom: 1px solid var(--border); margin-bottom: 0; }
.topbar-brand { font-family: var(--mono); font-size: 1.1rem; letter-spacing: 0.3em; color: var(--text-hi); }
.topbar-meta  { font-family: var(--mono); font-size: 0.55rem; letter-spacing: 0.2em; color: var(--text-lo); margin-top: 3px; }

.dashboard-header { margin-bottom: 44px; }
.dashboard-greeting { font-size: 2rem; font-weight: 700; color: var(--text-hi); margin-bottom: 2px; }
.dashboard-meta { font-family: var(--mono); font-size: 0.6rem; letter-spacing: 0.15em; color: var(--text-lo); margin-bottom: 16px; }
.dashboard-status {
    display: flex; gap: 32px; font-family: var(--mono); font-size: 0.5rem;
    letter-spacing: 0.15em; color: var(--blue); text-transform: uppercase;
    border-top: 1px solid var(--border); padding-top: 14px;
}

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

.section-header { padding: 28px 0 24px 0; border-bottom: 1px solid var(--border); margin-bottom: 32px; display: flex; align-items: flex-end; justify-content: space-between; }
.section-title { font-size: 1.4rem; font-weight: 700; color: var(--text-hi); letter-spacing: 0.02em; }
.section-code  { font-family: var(--mono); font-size: 0.52rem; letter-spacing: 0.3em; color: var(--text-lo); margin-bottom: 4px; }

.metric-card { background: var(--bg2); border: 1px solid var(--border); border-radius: 2px; padding: 24px; position: relative; overflow: hidden; }
.metric-card::before { content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: var(--blue); }
.metric-label { font-family: var(--mono); font-size: 0.52rem; letter-spacing: 0.22em; color: var(--blue); margin-bottom: 10px; }
.metric-value { font-family: var(--mono); font-size: 2rem; font-weight: 700; color: var(--text-hi); line-height: 1; }

.briefing-box { background: var(--bg2); border: 1px solid var(--border); border-left: 3px solid var(--blue); padding: 20px 24px; border-radius: 2px; margin-bottom: 20px; }
.briefing-box h4 { font-family: var(--mono); font-size: 0.58rem; letter-spacing: 0.2em; color: var(--blue); margin-bottom: 12px; }
.section-label { font-family: var(--mono); font-size: 0.55rem; letter-spacing: 0.25em; color: var(--blue); margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.status-bar { background: var(--bg2); border: 1px solid var(--border); border-left: 3px solid var(--green); padding: 10px 18px; border-radius: 2px; font-family: var(--mono); font-size: 0.62rem; letter-spacing: 0.12em; color: var(--green); margin-bottom: 20px; }

.diff-card { border: 2px solid var(--border); border-radius: 2px; padding: 14px 16px; cursor: pointer; transition: all 0.2s; background: var(--bg3); text-align: center; }
.diff-card:hover { transform: translateY(-2px); }
.diff-card.selected { background: rgba(79,142,247,0.08); }
.diff-name  { font-family: var(--mono); font-size: 0.7rem; letter-spacing: 0.18em; font-weight: 700; }
.diff-desc  { font-family: var(--mono); font-size: 0.52rem; color: var(--text-lo); margin-top: 6px; line-height: 1.5; }

.stTextInput input, .stSelectbox > div > div, .stTextArea textarea {
  background: var(--bg3) !important; border: 1px solid var(--border2) !important;
  color: var(--text) !important; border-radius: 2px !important; font-family: var(--sans) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--blue) !important; box-shadow: 0 0 0 2px rgba(79,142,247,0.08) !important; }
.stTextInput label, .stTextArea label, .stSelectbox label { color: var(--text-lo) !important; font-family: var(--mono) !important; font-size: 0.62rem !important; letter-spacing: 0.15em !important; }

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

.login-tab-active { background: var(--blue) !important; color: var(--bg) !important; border: none !important; }
.login-tab-inactive { background: transparent !important; color: var(--text-lo) !important; border: 1px solid var(--border) !important; }

.auth-tier { background: var(--bg3); border: 1px solid var(--border); border-left: 3px solid var(--border2); padding: 20px; border-radius: 2px; transition: border-color 0.2s; margin-bottom: 8px; }
.auth-tier:hover { border-left-color: var(--blue); }
.auth-tier.elite { border-left-color: var(--amber); }
.tier-spec { font-size: 0.75rem; color: #8B9CC8; margin-bottom: 6px; display: flex; align-items: center; }
.tier-spec::before { content: '—'; margin-right: 8px; color: var(--blue); font-size: 0.6rem; }

.alert-box { background: #0D1020; border: 1px solid var(--border); border-left: 3px solid var(--blue); padding: 14px 18px; border-radius: 2px; margin-bottom: 16px; font-family: var(--mono); font-size: 0.62rem; color: var(--text-lo); line-height: 1.6; }
.alert-box.warning { border-left-color: var(--amber); }
.alert-box.error   { border-left-color: var(--red); background: #120808; }

.link-btn { background: none; border: none; color: var(--text-lo); font-family: var(--mono); font-size: 0.58rem; letter-spacing: 0.1em; cursor: pointer; padding: 0; text-decoration: underline; transition: color 0.15s; }
.link-btn:hover { color: var(--blue); }

.plan-card { border: 1px solid var(--border); background: var(--bg3); border-radius: 2px; padding: 12px 14px; margin-bottom: 4px; cursor: pointer; transition: all 0.15s; }
.plan-card:hover { border-color: var(--border2); }
.plan-card.selected-plan { border-color: var(--blue); background: rgba(79,142,247,0.08); }
.plan-card.selected-plan.elite-plan { border-color: var(--amber); background: rgba(240,165,0,0.08); }

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--blue); }

@keyframes ring{0%{opacity:.6;transform:scale(1)}100%{opacity:0;transform:scale(2.5)}}
.card-wrapper { position:relative; margin-bottom:14px; }
.card-wrapper button {
    background:linear-gradient(135deg,#0B0E1A,#0F1425) !important;
    border:1px solid #18213A !important;
    border-left:5px solid var(--card-color,#4F8EF7) !important;
    border-radius:2px !important;
    padding:28px 20px 24px !important;
    text-align:left !important;
    white-space:normal !important;
    min-height:140px !important;
    position:relative !important;
    overflow:hidden !important;
    transition:all 0.25s ease !important;
    font-size:0.75rem !important;
    line-height:1.8 !important;
}
.card-wrapper button::after {
    content:'';position:absolute;inset:0;pointer-events:none;
    background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,.06) 3px,rgba(0,0,0,.06) 4px);
}
.card-wrapper:hover button {
    border-left-color:var(--card-color,#4F8EF7) !important;
    border-color:var(--card-color,#4F8EF7) !important;
    box-shadow:0 16px 48px rgba(0,0,0,.6), 0 0 30px var(--card-color,#4F8EF7)33 !important;
    transform:translateY(-4px) !important;
}
.card-wrapper::before {
    content:''; position:absolute; right:20px; top:20px; z-index:5; pointer-events:none;
    width:8px; height:8px; border-radius:50%;
    background:var(--card-color,#4F8EF7); opacity:.9;
    box-shadow:0 0 8px var(--card-color,#4F8EF7);
}
.card-wrapper::after {
    content:''; position:absolute; right:16px; top:16px; z-index:4; pointer-events:none;
    width:16px; height:16px; border-radius:50%;
    border:1px solid var(--card-color,#4F8EF7);
    animation:ring 2.2s ease-out infinite;
}
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
recalcular_xp_historico()
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
if "tension_actual"     not in st.session_state: st.session_state.tension_actual      = 0
# NUEVOS PARA PROGRESIÓN
if "es_mision_diaria"      not in st.session_state: st.session_state.es_mision_diaria      = False
if "xp_ganado_ultimo"      not in st.session_state: st.session_state.xp_ganado_ultimo       = 0
if "logros_nuevos_ultimo"  not in st.session_state: st.session_state.logros_nuevos_ultimo   = []
if "mision_diaria_cache" not in st.session_state:
    st.session_state.mision_diaria_cache = {"fecha": "", "mision": None}

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
                acepta_tyc_ag = st.checkbox(
                            "He leído y acepto los Términos y Condiciones y la Política de Privacidad",
                            key="check_tyc_agente"
                        )
                acepta_rgpd_ag = st.checkbox(
                    "Consiento el tratamiento de mis datos personales conforme al RGPD (UE) 2016/679",
                    key="check_rgpd_agente"
                )
                if st.form_submit_button("REGISTRAR CREDENCIALES", use_container_width=True):
                        if not acepta_tyc_ag or not acepta_rgpd_ag:
                            st.error("Debes aceptar los Términos y la Política de Privacidad para continuar.")
                        elif n and p and email:
                            if any(e["Nombre"] == n and e.get("Empresa") == empresa_invitada for e in st.session_state.empleados):
                                st.warning("Este ID ya está registrado en esta corporación.")
                            elif any(e["Nombre"] == n and e.get("Password") == p for e in st.session_state.empleados):
                                st.warning("ID ya en uso. Utiliza una contraseña diferente.")
                            else:
                                nuevo_agente = {"Nombre": n, "Email": email, "Departamento": d, "Rol": "Agente", "Empresa": empresa_invitada, "Password": p, "2FA_Verificado": True}
                                st.session_state.empleados.append(nuevo_agente); guardar_datos()
                                guardar_usuario_plano(nuevo_agente["Nombre"], nuevo_agente.get("Email", ""), empresa_obj.get("Plan", "BASE"))
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
                        st.markdown(
                            "📄 [Términos y Condiciones](https://github.com/querrul07/crysis-app/blob/main/terminos_condiciones_crysis.md) · [Política de Privacidad](https://github.com/querrul07/crysis-app/blob/main/politica_privacidad_crysis.md)",
                            unsafe_allow_html=True
                        )
                        acepta_tyc = st.checkbox(
                            "He leído y acepto los Términos y Condiciones y la Política de Privacidad",
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
                                        nuevo_usuario = {"Nombre": n, "Email": email, "Departamento": "Administración", "Rol": "Empresa", "Plan": "BASE", "Empresa": n, "Password": p, "2FA_Verificado": True, "Acepta_TyC": True, "Acepta_RGPD": True, "Acepta_Comms": acepta_comms, "Fecha_Consentimiento": datetime.now().strftime("%Y-%m-%d %H:%M")}
                                    else:
                                        nuevo_usuario = {"Nombre": n, "Email": email, "Rol": "Individual", "Plan": "BASE", "Empresa": n, "Password": p, "2FA_Verificado": True, "Acepta_TyC": True, "Acepta_RGPD": True, "Acepta_Comms": acepta_comms, "Fecha_Consentimiento": datetime.now().strftime("%Y-%m-%d %H:%M")}
                                    st.session_state.empleados.append(nuevo_usuario); guardar_datos()
                                    guardar_usuario_plano(nuevo_usuario["Nombre"], nuevo_usuario.get("Email", ""), nuevo_usuario.get("Plan", "BASE"))
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

    st.stop()

# ─────────────────────────────────────────
# MANEJADOR DE NAVEGACIÓN POR TARJETAS
# ─────────────────────────────────────────
menu_destino = st.query_params.get("menu", None)
if menu_destino and st.session_state.usuario_actual is not None:
    st.session_state.pantalla_actual = menu_destino
    st.query_params.clear()
    st.rerun()

# ─────────────────────────────────────────
# RESOLUCIÓN DE PERMISOS
# ─────────────────────────────────────────
u = st.session_state.usuario_actual

if u["Nombre"] == COMANDANTE_SUPREMO:
    es_empresa     = True
    mi_plan        = "COMANDANCIA"
    empresa_actual = u["Nombre"]
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

_legacy = {"Gratis": "BASE", "Individual": "OPERADOR", "Pro": "ESCUADRON", "Enterprise": "COMANDANCIA"}
mi_plan = _legacy.get(mi_plan, mi_plan)

ops_limite      = PLANES_INFO.get(mi_plan, {}).get("ops", 1)
escenarios_lim  = PLANES_INFO.get(mi_plan, {}).get("escenarios", 0)
agentes_lim     = PLANES_INFO.get(mi_plan, {}).get("agentes", 0)

if u["Nombre"] != COMANDANTE_SUPREMO:
    if es_empresa:
        agentes_de_mi_empresa = [e["Nombre"] for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"]
        historial_visible = [s for s in st.session_state.historial_sesiones if s["Agente"] in agentes_de_mi_empresa and s.get("Tipo_Mision") == "Corporativa"]
    else:
        historial_visible = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]
        agentes_de_mi_empresa = [u["Nombre"]]

if u["Nombre"] == COMANDANTE_SUPREMO:
    mis_escenarios = {k: v for k, v in st.session_state.escenarios_custom.items() 
                      if v.get("Creador") == COMANDANTE_SUPREMO}
else:
    mis_escenarios = {k: v for k, v in st.session_state.escenarios_custom.items() 
                      if v.get("Creador") == empresa_actual}

TODAS_LAS_MISIONES = {**CONTEXTOS_MISION, **mis_escenarios}

# ─────────────────────────────────────────
# TOPBAR (con XP y nivel)
# ─────────────────────────────────────────
if st.session_state.pantalla_actual != "menu":
    u_top      = next((e for e in st.session_state.empleados if e["Nombre"] == u["Nombre"]), {})
    xp_top     = u_top.get("xp", 0)
    nv_top, _, _, _ = get_nivel_usuario(xp_top)
    racha_top  = u_top.get("racha", 0)
    rol_label = ("OMNISCIENCIA GLOBAL" if u["Nombre"] == COMANDANTE_SUPREMO
                 else (f"SUPERVISION [{mi_plan}]" if es_empresa
                       else f"OPERADOR · {nv_top} · {xp_top} XP · RACHA {racha_top}d [{mi_plan}]"))
    col_top1, col_top2 = st.columns([8, 1])
    with col_top1:
        pantalla = st.session_state.pantalla_actual
        nombres_pantalla = {"estadisticas": "ESTADÍSTICAS", "personal": "AGENTES", "expedientes": "EXPEDIENTES",
                            "simulador": "SIMULADOR", "sintesis": "SÍNTESIS IA", "admin": "ADMINISTRACIÓN", "cuenta": "CUENTA",
                            "mision_diaria": "MISIÓN DIARIA", "ranking": "RANKING"}
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
# MENÚ PRINCIPAL (con tarjetas de progresión)
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

    total_ops    = len(historial_visible)
    media_global = int(sum(s["Nota"] for s in historial_visible) / total_ops) if total_ops > 0 else 0
    mes_actual   = datetime.now().strftime("%Y-%m")
    ops_mes      = len([s for s in historial_visible if str(s.get("Fecha","")).startswith(mes_actual)])
    agentes_act  = len([e for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"])
    esc_creados  = len(mis_escenarios)
    metrica_cuenta = f"{u['Nombre'].upper()} · {mi_plan}"
    metrica_agentes = f"AGENTES ACTIVOS {agentes_act}"
    _precios = {"COMANDANCIA":199,"ESCUADRON":89,"ELITE":49,"OPERADOR":19,"BASE":0,
                "Enterprise":199,"Pro":89,"Individual":19,"Gratis":0}
    mrr = sum(_precios.get(_legacy.get(e.get("Plan","BASE"), e.get("Plan","BASE")), 0)
              for e in st.session_state.empleados)

    tarjetas = [
        ("estadisticas", "ANÁLISIS DE RENDIMIENTO",  f"RENDIMIENTO MEDIO {media_global}%",         "#4F8EF7"),
        ("simulador",    "SIMULADOR TÁCTICO",         f"OPERACIONES ACTIVAS ESTE MES {ops_mes}",     "#00D4A0"),
        ("expedientes",  "HISTORIAL DE EXPEDIENTES",  f"EXPEDIENTES TOTALES {total_ops}",            "#F0A500"),
    ]
    tarjetas.append(("cuenta", "TU CUENTA", metrica_cuenta, "#6B7280"))
    if es_empresa:
        tarjetas.append(("personal", "GESTIÓN DE AGENTES", metrica_agentes, "#E8394A"))
    tarjetas.append(("sintesis", "GENERACIÓN DE ESCENARIOS", f"ESCENARIOS ACTIVOS {esc_creados}", "#A855F7"))
    if u["Nombre"] == COMANDANTE_SUPREMO:
        tarjetas.append(("admin", "CONSOLA OMEGA", f"ESTIMATED VALUE {mrr} EUR", "#F59E0B"))

    # Tarjetas de progresión
    mision_hoy    = get_mision_diaria_hoy()
    u_data_menu   = next((e for e in st.session_state.empleados if e["Nombre"] == u["Nombre"]), {})
    ya_hizo_diaria = u_data_menu.get("diaria_hoy", "") == datetime.now().strftime("%Y-%m-%d")
    estado_diaria  = "COMPLETADA HOY" if ya_hizo_diaria else "DISPONIBLE AHORA"
    tarjetas.append(("mision_diaria", "MISIÓN DIARIA", f"{estado_diaria} · +80 XP BONUS", "#10B981"))
    tarjetas.append(("ranking", "RANKING GLOBAL", "CLASIFICACIÓN EN TIEMPO REAL", "#6366F1"))

    for fila in range(0, len(tarjetas), 3):
        cols = st.columns(3)
        for i, (destino, titulo, metrica, color) in enumerate(tarjetas[fila:fila+3]):
            with cols[i]:
                st.markdown(f'<div class="card-wrapper" style="--card-color: {color};">', unsafe_allow_html=True)
                if st.button(f"**{titulo}**\n\n**{metrica}**", key=f"btn_{destino}", use_container_width=True):
                    st.session_state.pantalla_actual = destino
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

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
# PERSONAL (sin cambios)
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
# CUENTA (con progresión y medallero)
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "cuenta":
    st.markdown("<div class='section-header'><div><div class='section-code'>CUENTA</div><div class='section-title'>Tu Cuenta</div></div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-label'>ACREDITACIÓN CONFIRMADA</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class="briefing-box"><h4>DATOS DE LA CUENTA</h4>
    <p><b>Identificador:</b> {u['Nombre']} &nbsp;|&nbsp; <b>Unidad:</b> {empresa_actual} &nbsp;|&nbsp; <b>Plan:</b> {mi_plan}</p>
    <p><b>Email:</b> {u.get('Email','—')}</p>
    </div>""", unsafe_allow_html=True)

    # Progresión
    u_prog   = next((e for e in st.session_state.empleados if e["Nombre"] == u["Nombre"]), {})
    xp_act   = u_prog.get("xp", 0)
    racha_act= u_prog.get("racha", 0)
    niv_nom, niv_col, xp_falta, pct_niv = get_nivel_usuario(xp_act)

    st.markdown("<br><div class='section-label'>PROGRESIÓN TÁCTICA</div>", unsafe_allow_html=True)
    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.markdown(f"""<div class="metric-card" style="border-left-color:{niv_col};">
        <div class="metric-label">NIVEL</div>
        <div class="metric-value" style="color:{niv_col}; font-size:1.3rem;">{niv_nom}</div>
        <div style="height:3px; background:#18213A; margin-top:10px; border-radius:1px; overflow:hidden;">
            <div style="height:100%; width:{pct_niv}%; background:{niv_col}; border-radius:1px;"></div>
        </div>
        <div style="font-family:var(--mono); font-size:0.48rem; color:#3A4A6A; margin-top:5px;">{pct_niv}% · {xp_falta} XP para el siguiente</div>
    </div>""", unsafe_allow_html=True)
    col_p2.markdown(f"""<div class="metric-card" style="border-left-color:#F0A500;">
        <div class="metric-label">XP TOTAL</div>
        <div class="metric-value" style="color:#F0A500;">{xp_act}</div>
    </div>""", unsafe_allow_html=True)
    col_p3.markdown(f"""<div class="metric-card" style="border-left-color:#10B981;">
        <div class="metric-label">RACHA ACTIVA</div>
        <div class="metric-value" style="color:#10B981;">{racha_act}</div>
        <div style="font-family:var(--mono); font-size:0.5rem; color:#3A4A6A; margin-top:6px;">DÍAS CONSECUTIVOS</div>
    </div>""", unsafe_allow_html=True)

    # Medallero
    logros_usuario = u_prog.get("logros", [])
    st.markdown("<br><div class='section-label'>MEDALLERO OPERACIONAL</div>", unsafe_allow_html=True)
    cols_log = st.columns(4)
    for idx_l, (key, data) in enumerate(LOGROS_DEF.items()):
        obtenido   = key in logros_usuario
        col_l      = cols_log[idx_l % 4]
        bg_l       = "rgba(16,185,129,0.07)"  if obtenido else "#0B0E1A"
        border_l   = "#10B981" if obtenido else "#18213A"
        color_txt  = "#E2EAF8" if obtenido else "#1E2A40"
        color_desc = "#3A4A6A" if obtenido else "#18213A"
        col_l.markdown(f"""
        <div style="border:1px solid {border_l}; background:{bg_l}; border-radius:2px;
            padding:12px 10px; margin-bottom:8px; text-align:center;">
            <div style="font-size:1.2rem; margin-bottom:6px; opacity:{'1' if obtenido else '0.15'};">{data['i']}</div>
            <div style="font-family:var(--mono); font-size:0.52rem; color:{color_txt}; letter-spacing:0.05em;">
                {data['nombre'] if obtenido else '???'}
            </div>
            <div style="font-family:var(--mono); font-size:0.45rem; color:{color_desc}; margin-top:4px; line-height:1.5;">
                {data['desc'] if obtenido else '...'}
            </div>
            {f'<div style="font-family:var(--mono); font-size:0.48rem; color:#F0A500; margin-top:5px;">+{data["xp"]} XP</div>' if obtenido else ''}
        </div>
        """, unsafe_allow_html=True)

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
                for e in st.session_state.empleados:
                    if e["Nombre"] == u["Nombre"] and e.get("Empresa") == u.get("Empresa"):
                        e["Email"] = nuevo_email
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
# SIMULADOR TÁCTICO (con integración de XP)
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
            st.session_state.tension_actual     = 0
            st.rerun()

    elif st.session_state.evaluacion_actual:
        st.markdown("<div class='section-label'>INFORME DE EVALUACIÓN TÁCTICA</div>", unsafe_allow_html=True)
        st.markdown(st.session_state.evaluacion_actual)

        # Banner de XP y logros (BLOQUE 8)
        xp_ob  = st.session_state.get("xp_ganado_ultimo", 0)
        log_n  = st.session_state.get("logros_nuevos_ultimo", [])
        if xp_ob > 0:
            logros_html = "".join([
                f'<div style="margin-top:8px; font-family:var(--mono); font-size:0.6rem; color:#10B981;">'
                f'◉ LOGRO DESBLOQUEADO: {LOGROS_DEF[l]["nombre"]} (+{LOGROS_DEF[l]["xp"]} XP)</div>'
                for l in log_n
            ])
            st.markdown(f"""<div class="alert-box" style="border-left-color:#F0A500; background:rgba(240,165,0,0.04);">
                <span style="color:#F0A500; font-family:var(--mono); font-weight:700; font-size:0.8rem;">+{xp_ob} XP</span>
                <span style="color:#3A4A6A; font-family:var(--mono); font-size:0.58rem;"> OBTENIDOS EN ESTA MISIÓN</span>
                {logros_html}
            </div>""", unsafe_allow_html=True)

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
        # CAMBIO 2 va aquí, al principio del else:
        escenario_activo_now = st.session_state.get("escenario_activo", "")
        if escenario_activo_now not in TODAS_LAS_MISIONES:
            cache = st.session_state.get("mision_diaria_cache", {})
            mision_cache = cache.get("mision")
            if mision_cache and mision_cache.get("escenario") == escenario_activo_now:
                datos = mision_cache.get("datos", {})
                TODAS_LAS_MISIONES[escenario_activo_now] = {
                    "contexto":      datos.get("contexto", ""),
                    "perfil_sujeto": datos.get("perfil_sujeto", ""),
                    "objetivo":      datos.get("objetivo", ""),
                    "prompt":        datos.get("prompt", "") + " " + INSTRUCCION_ORTOGRAFIA,
                }

        dif_sesion  = st.session_state.get("dificultad_sesion", "OPERATOR")  # esta línea ya estaba
        ...
        dif_color_s = DIFICULTADES.get(dif_sesion, {}).get("color","#4F8EF7")
        st.markdown(f"""
        <div class='status-bar'>
            ● LÍNEA SEGURA ACTIVA: {st.session_state.escenario_activo} — 
            OPERADOR: {st.session_state.agente_activo.upper()} — 
            <span style="color:{dif_color_s};">DIFICULTAD: {dif_sesion}</span>
        </div>
        """, unsafe_allow_html=True)
        t = st.session_state.tension_actual
        t_c = "#00D4A0" if t < 35 else ("#F0A500" if t < 65 else "#E8394A")

        if t < 20:   t_txt, t_status = "SITUACIÓN CONTROLADA", "00D4A0"
        elif t < 45: t_txt, t_status = "TENSIÓN MODERADA",     "F0A500"
        elif t < 70: t_txt, t_status = "TENSIÓN ELEVADA",      "F0A500"
        elif t < 85: t_txt, t_status = "ZONA CRÍTICA",         "E8394A"
        else:        t_txt, t_status = "⚡ RUPTURA INMINENTE", "E8394A"

        estabilidad     = max(5, min(95, int(100 - t * 1.1)))
        ventana_neg     = max(5, min(95, int(100 - t * 0.9)))
        riesgo_escalada = max(5, min(95, int(t * 0.8)))
        c_estab   = "#00D4A0" if estabilidad     > 50 else ("#F0A500" if estabilidad     > 30 else "#E8394A")
        c_ventana = "#00D4A0" if ventana_neg     > 50 else ("#F0A500" if ventana_neg     > 30 else "#E8394A")
        c_riesgo  = "#00D4A0" if riesgo_escalada < 40 else ("#F0A500" if riesgo_escalada < 65 else "#E8394A")

        segs_html = "".join([
            f'<div style="flex:1;height:18px;background:{t_c};border-radius:1px;position:relative;overflow:hidden;">'
            f'<div style="position:absolute;inset:0;background:linear-gradient(90deg,transparent 40%,rgba(255,255,255,.1))"></div></div>'
            if i < round(t / 100 * 20) else
            '<div style="flex:1;height:18px;background:#18213A;border-radius:1px"></div>'
            for i in range(20)
        ])

        st.markdown(f"""
        <div style="background:#0B0E1A;border:1px solid #18213A;border-left:3px solid #{t_status};border-radius:2px;padding:20px;margin-bottom:16px">
          <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:16px">
            <div>
              <div style="font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:.25em;color:#3A4A6A;margin-bottom:6px">ÍNDICE DE TENSIÓN TÁCTICA</div>
              <div style="display:flex;align-items:baseline;gap:12px">
                <div style="font-family:'Share Tech Mono',monospace;font-size:26px;font-weight:700;color:#{t_status};line-height:1">{t}</div>
                <div style="font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:.2em;color:#{t_status}">● {t_txt}</div>
              </div>
            </div>
            <div style="text-align:right">
              <div style="font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:.2em;color:#3A4A6A">PROTOCOLO ACTIVO</div>
              <div style="font-family:'Share Tech Mono',monospace;font-size:10px;color:#E2EAF8;margin-top:4px">{st.session_state.escenario_activo}</div>
              <div style="font-family:'Share Tech Mono',monospace;font-size:9px;color:{dif_color_s};margin-top:2px">DIFICULTAD: {dif_sesion}</div>
            </div>
          </div>
          <div style="display:flex;gap:3px;margin-bottom:16px">{segs_html}</div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
            <div style="background:#101525;border:1px solid #18213A;border-radius:2px;padding:10px 12px">
              <div style="font-family:'Share Tech Mono',monospace;font-size:8px;letter-spacing:.2em;color:#3A4A6A;margin-bottom:6px">ESTABILIDAD OBJETIVO</div>
              <div style="font-family:'Share Tech Mono',monospace;font-size:14px;font-weight:700;color:{c_estab}">{estabilidad}%</div>
              <div style="height:2px;background:#18213A;margin-top:6px;border-radius:1px;overflow:hidden">
                <div style="height:100%;width:{estabilidad}%;background:{c_estab};border-radius:1px"></div>
              </div>
            </div>
            <div style="background:#101525;border:1px solid #18213A;border-radius:2px;padding:10px 12px">
              <div style="font-family:'Share Tech Mono',monospace;font-size:8px;letter-spacing:.2em;color:#3A4A6A;margin-bottom:6px">VENTANA DE NEGOCIACIÓN</div>
              <div style="font-family:'Share Tech Mono',monospace;font-size:14px;font-weight:700;color:{c_ventana}">{ventana_neg}%</div>
              <div style="height:2px;background:#18213A;margin-top:6px;border-radius:1px;overflow:hidden">
                <div style="height:100%;width:{ventana_neg}%;background:{c_ventana};border-radius:1px"></div>
              </div>
            </div>
            <div style="background:#101525;border:1px solid #18213A;border-radius:2px;padding:10px 12px">
              <div style="font-family:'Share Tech Mono',monospace;font-size:8px;letter-spacing:.2em;color:#3A4A6A;margin-bottom:6px">RIESGO DE ESCALADA</div>
              <div style="font-family:'Share Tech Mono',monospace;font-size:14px;font-weight:700;color:{c_riesgo}">{riesgo_escalada}%</div>
              <div style="height:2px;background:#18213A;margin-top:6px;border-radius:1px;overflow:hidden">
                <div style="height:100%;width:{riesgo_escalada}%;background:{c_riesgo};border-radius:1px"></div>
              </div>
            </div>
          </div>
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
                if escenario_a not in TODAS_LAS_MISIONES:
                    st.error("El escenario ya no está disponible. La misión ha sido cancelada.")
                    st.session_state.mision_iniciada  = False
                    st.session_state.mensajes         = []
                    st.session_state.tarjeta_objetivo = None
                    st.rerun()
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
                st.session_state.mensajes.append({"role":"assistant","content":res})
                _t = st.session_state.tension_actual
                res_lower = res.lower()
                prompt_lower = prompt.lower() if prompt else ""

                _hostil_op = ['mierdas','mierda','idiota','imbécil','imbecil','gilipollas',
                              'estúpido','estupido','inútil','inutíl','incompetente',
                              'amenaza','amenaza','mato','muerto','destruir','atacar',
                              'guerra','bomba','ultimátum','ultimatum','rendirse','rendición']
                _subida_sujeto = ['no','jamás','jamas','nunca','imposible','inaceptable',
                                  'traidor','silencio','fin','fuera','advertencia','consecuencias',
                                  'cuidado','error','peligro','ataque','ruptura']
                _bajada = ['acuerdo','entiendo','comprendo','posible','juntos','paz',
                           'dialogar','cooperar','dispuesto','escucho','propongo',
                           'solución','solucion','negociar','respetar']

                for _p in _hostil_op:
                    if _p in prompt_lower:
                        _t = min(100, _t + 15)
                hits_subida = sum(1 for _p in _subida_sujeto if _p in res_lower)
                _t = min(100, _t + hits_subida * 6)
                hits_bajada = sum(1 for _p in _bajada if _p in res_lower)
                _t = max(0, _t - min(hits_bajada * 4, 10))
                if hits_subida == 0 and hits_bajada == 0:
                    _t = max(0, _t - 1)
                st.session_state.tension_actual = _t
                st.rerun()

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
                        # ── Conceder XP y comprobar logros (BLOQUE 7) ──
                        es_diaria_act = st.session_state.get("es_mision_diaria", False)
                        xp_obt, logros_nuevos = otorgar_xp_y_logros(
                            st.session_state.agente_activo,
                            nota,
                            dif_ev,
                            es_diaria=es_diaria_act,
                        )
                        st.session_state.xp_ganado_ultimo     = xp_obt
                        st.session_state.logros_nuevos_ultimo = logros_nuevos
                        st.session_state.es_mision_diaria     = False
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
                c_esc1.markdown(f"""
                <div style="background:var(--bg2); border:1px solid var(--border); border-radius:2px; padding:10px 14px; margin-bottom:4px;">
                    <span style="color:var(--text-hi); font-size:0.85rem;">{nombre_esc}</span>
                    <span style="color:var(--text-lo); font-family:var(--mono); font-size:0.55rem; margin-left:8px;">Creador: {datos_esc.get('Creador','—')}</span>
                </div>
                """, unsafe_allow_html=True)
                if c_esc2.button("ELIMINAR", key=f"del_{nombre_esc}", type="secondary"):
                    del st.session_state.escenarios_custom[nombre_esc]; guardar_datos(); st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("<div class='section-label'>NUEVA SIMULACIÓN AVANZADA</div>", unsafe_allow_html=True)

        if mi_plan == "BASE" and u["Nombre"] != COMANDANTE_SUPREMO:
            st.markdown("""<div class="alert-box error">RESTRICCIÓN: El nivel BASE no permite el uso de IA Generativa.</div>""", unsafe_allow_html=True)
        else:
            limite_esc = 99999 if u["Nombre"] == COMANDANTE_SUPREMO else escenarios_lim
            if limite_esc != 99999 and creados >= limite_esc:
                st.markdown(f"""<div class="alert-box warning">CUOTA ALCANZADA ({creados}/{limite_esc}). Elimina uno para crear otro.</div>""", unsafe_allow_html=True)
            else:
                idea_prompt = st.text_area("Describe el escenario o la persona real:", height=120,
                                           placeholder="Ej: Negociación con Pablo Escobar, líder del cartel de Medellín, carácter violento pero inteligente. Objetivo: rendición pacífica.")

                palabras = idea_prompt.split() if idea_prompt else []
                nombre_candidato = None
                for p in palabras:
                    if p[0].isupper() and len(p) > 2 and p.lower() not in ['un','una','el','la','los','las','de','del','y','a','ante','con','sin','por','para']:
                        nombre_candidato = p.strip(',.;:')
                        break

                wiki_data = None
                if nombre_candidato and len(nombre_candidato) > 3:
                    with st.spinner(f"Consultando Wikipedia sobre {nombre_candidato}..."):
                        wiki_data = buscar_wikipedia(nombre_candidato)
                    if wiki_data:
                        st.success(f"✅ Datos reales cargados: {wiki_data['titulo']}")
                        with st.expander("Ver biografía (fuente Wikipedia)"):
                            st.caption(wiki_data['resumen'])
                elif idea_prompt and not nombre_candidato:
                    st.info("No se detectó un nombre propio. Se generará un escenario original.")

                if st.button("GENERAR ESCENARIO PROFESIONAL", use_container_width=True):
                    if idea_prompt and GROQ_API_KEY:
                        with st.spinner("Motor táctico IA en funcionamiento..."):
                            try:
                                client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                                contexto_wiki = ""
                                if wiki_data:
                                    contexto_wiki = f"""
DATOS REALES DE WIKIPEDIA:
- Nombre: {wiki_data['titulo']}
- Biografía: {wiki_data['resumen']}
DEBES USAR ESTOS DATOS PARA CARACTERIZAR AL SUJETO.
"""
                                super_prompt = f"""Eres un experto generador de escenarios tácticos de élite. Crea una simulación profesional y realista.

INSTRUCCIONES:
- Nombra la operación con un nombre clave atractivo (ej: OPERACIÓN: NIEVE NEGRA, OPERACIÓN: ECO ROTO).
- El OPERADOR (usuario) es quien ACTÚA en la descripción. Si dice "comprar", operador es comprador; si dice "vender", operador es vendedor. El SUJETO (IA) es la contraparte.
- Contexto serio, de inteligencia o negociación de alto nivel.
- Perfil del sujeto detallado (motivaciones, debilidades, estilo).
- Objetivo claro y medible.
- Prompt del sujeto en PRIMERA PERSONA, sin acotaciones, solo diálogo.

{contexto_wiki}

DESCRIPCIÓN DEL USUARIO: {idea_prompt}

DEVUELVE SOLO JSON:
{{
    "nombre_op": "OPERACIÓN: [NOMBRE]",
    "contexto": "texto",
    "perfil_sujeto": "texto detallado",
    "objetivo": "texto",
    "prompt": "Instrucciones para la IA: eres [nombre]. [rol]. Responde en español. Sin paréntesis."
}}
"""
                                res = client.chat.completions.create(
                                    model="llama-3.3-70b-versatile",
                                    messages=[{"role":"user","content": super_prompt}],
                                    response_format={"type":"json_object"}
                                ).choices[0].message.content
                                nuevo_esc = json.loads(res)
                                nuevo_esc["prompt"] += " Escribe en español correcto. Solo diálogo directo, sin acotaciones entre paréntesis."
                                st.session_state.escenarios_custom[nuevo_esc["nombre_op"]] = {
                                    "contexto": nuevo_esc["contexto"],
                                    "perfil_sujeto": nuevo_esc["perfil_sujeto"],
                                    "objetivo": nuevo_esc["objetivo"],
                                    "prompt": nuevo_esc["prompt"],
                                    "Creador": empresa_actual
                                }
                                guardar_datos()
                                st.success(f"✅ Creado: {nuevo_esc['nombre_op']}")
                                st.balloons()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    elif not idea_prompt:
                        st.warning("Escribe una descripción.")
                    elif not GROQ_API_KEY:
                        st.error("API key no configurada.")

    with col_der:
        st.markdown("<div class='section-label'>NIVELES DE ACCESO</div>", unsafe_allow_html=True)
        planes_der = [
            ("BASE", "0€", False, ["Sin IA generativa", "1 op/mes"]),
            ("OPERADOR", "19€/mes", False, ["3 escenarios", "10 ops/mes"]),
            ("ELITE", "49€/mes", True, ["Ilimitado", "IA ∞"]),
            ("ESCUADRON", "89€/mes", True, ["15 agentes", "IA ∞"]),
            ("COMANDANCIA", "199€/mes", True, ["Agentes ∞", "IA ∞"]),
        ]
        for nombre, precio, elite, specs in planes_der:
            activo = mi_plan == nombre
            color = "#F0A500" if elite else "#4F8EF7"
            border = "#00D4A0" if activo else ("#F0A500" if elite else "var(--border2)")
            st.markdown(f"""
            <div class="auth-tier {'elite' if elite else ''}" style="border-left-color:{border};">
                <div style="display:flex;justify-content:space-between;border-bottom:1px solid #18213A;padding-bottom:6px;">
                    <span style="font-family:var(--mono);font-size:0.65rem;color:{'#00D4A0' if activo else 'var(--text-hi)'};">{'● ' if activo else ''}{nombre}</span>
                    <span style="font-family:var(--mono);font-size:0.75rem;color:{color};">{precio}</span>
                </div>
                {''.join(f'<div class="tier-spec">{s}</div>' for s in specs)}
            </div>
            """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# MISIÓN DIARIA
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "mision_diaria":
    mision = generar_mision_diaria_ia()   # <--- Llamada a la nueva función IA
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    u_d = next((e for e in st.session_state.empleados if e["Nombre"] == u["Nombre"]), {})
    completada_hoy = u_d.get("diaria_hoy", "") == hoy_str

    # --- Inyectar escenario diario en TODAS_LAS_MISIONES ---
    if mision["escenario"] not in TODAS_LAS_MISIONES:
        TODAS_LAS_MISIONES[mision["escenario"]] = {
            "contexto": mision["datos"]["contexto"],
            "perfil_sujeto": mision["datos"]["perfil_sujeto"],
            "objetivo": mision["datos"]["objetivo"],
            "prompt": mision["datos"]["prompt"] + " " + INSTRUCCION_ORTOGRAFIA,
        }


    st.markdown("""<div class='section-header'><div>
        <div class='section-code'>DIARIA</div>
        <div class='section-title'>Misión del Día</div>
    </div></div>""", unsafe_allow_html=True)

    ahora      = datetime.now()
    medianoche = datetime(ahora.year, ahora.month, ahora.day) + timedelta(days=1)
    resta      = medianoche - ahora
    horas_r    = int(resta.seconds // 3600)
    mins_r     = int((resta.seconds % 3600) // 60)

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""<div class="metric-card" style="border-left-color:#10B981;">
        <div class="metric-label" style="color:#10B981;">PROTOCOLO ASIGNADO</div>
        <div style="color:#E2EAF8; font-size:0.85rem; margin-top:10px; line-height:1.4;">{mision['escenario']}</div>
    </div>""", unsafe_allow_html=True)
    dif_col_d = DIFICULTADES[mision['dificultad']]['color']
    c2.markdown(f"""<div class="metric-card" style="border-left-color:{dif_col_d};">
        <div class="metric-label" style="color:{dif_col_d};">DIFICULTAD</div>
        <div class="metric-value" style="color:{dif_col_d}; font-size:1.4rem;">{mision['dificultad']}</div>
        <div style="font-family:var(--mono); font-size:0.5rem; color:{dif_col_d}; margin-top:6px; opacity:0.7;">LVL {DIFICULTADES[mision['dificultad']]['nivel']}/4</div>
    </div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="metric-card" style="border-left-color:#F0A500;">
        <div class="metric-label">NUEVA MISIÓN EN</div>
        <div class="metric-value" style="font-size:1.6rem;">{horas_r:02d}:{mins_r:02d}</div>
        <div style="font-family:var(--mono); font-size:0.48rem; color:#3A4A6A; margin-top:6px;">ROTA AUTOMÁTICAMENTE</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if completada_hoy:
        st.markdown("""<div class="alert-box" style="border-left-color:#10B981; background:rgba(16,185,129,0.05);">
            <div style="color:#10B981; font-family:var(--mono); font-size:0.7rem; letter-spacing:0.2em; margin-bottom:8px;">◉ MISIÓN DIARIA COMPLETADA</div>
            <div style="color:#3A4A6A; font-family:var(--mono); font-size:0.58rem;">El operador ha cumplido su cuota de entrenamiento diario. Vuelve mañana para una nueva asignación.</div>
        </div>""", unsafe_allow_html=True)
    else:
        info_d = TODAS_LAS_MISIONES.get(mision["escenario"], {})
        st.markdown(f"""<div class="briefing-box" style="border-left-color:#10B981;">
            <h4 style="color:#10B981;">BRIEFING CLASIFICADO</h4>
            <p><b>Contexto:</b> {info_d.get('contexto','—')}</p>
            <p><b>Perfil del objetivo:</b> {info_d.get('perfil_sujeto','—')}</p>
            <p><b>Directiva:</b> {info_d.get('objetivo','—')}</p>
            <p><b>Dificultad asignada:</b> <span style="color:{dif_col_d}; font-family:var(--mono); font-weight:700;">{mision['dificultad']}</span></p>
            <p style="margin-top:12px;"><b>Recompensa:</b>
                <span style="color:#F0A500; font-family:var(--mono); font-weight:700;"> +80 XP BONUS DIARIO</span>
                <span style="color:#3A4A6A; font-family:var(--mono); font-size:0.75rem;"> + XP por rendimiento</span>
            </p>
        </div>""", unsafe_allow_html=True)

        if st.button("ACEPTAR MISIÓN DIARIA", use_container_width=True):
            tarjeta = {"Nombre_Completo": "Desconocido", "Familia": "Clasificado", "Estado_Mental": "Inestable"}
            if GROQ_API_KEY:
                try:
                    client_d = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                    info_d2  = TODAS_LAS_MISIONES.get(mision["escenario"], {})
                    jp = f"Genera para {info_d2.get('perfil_sujeto','un sujeto')} EXCLUSIVAMENTE JSON PLANO con 3 claves: 'Nombre_Completo', 'Familia', 'Estado_Mental'."
                    res_t = client_d.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role":"user","content": jp}],
                        response_format={"type":"json_object"}
                    ).choices[0].message.content
                    tarjeta = json.loads(res_t)
                except:
                    pass
            st.session_state.tarjeta_objetivo   = tarjeta
            st.session_state.mision_iniciada    = True
            st.session_state.mensajes           = []
            st.session_state.agente_activo      = u["Nombre"]
            st.session_state.escenario_activo   = mision["escenario"]
            st.session_state.tipo_mision_actual = "Personal"
            st.session_state.dificultad_sesion  = mision["dificultad"]
            st.session_state.es_mision_diaria   = True
            st.session_state.tarjeta_objetivo   = None
            st.session_state.tension_actual     = 0
            st.session_state.pantalla_actual    = "simulador"
            st.rerun()

# ─────────────────────────────────────────
# RANKING GLOBAL
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "ranking":
    st.markdown("""<div class='section-header'><div>
        <div class='section-code'>RANKING</div>
        <div class='section-title'>Clasificación Global</div>
    </div></div>""", unsafe_allow_html=True)

    datos_ranking = []
    for ag in st.session_state.empleados:
        if ag["Nombre"] == COMANDANTE_SUPREMO:
            continue
        nombre = ag["Nombre"]
        xp_ag  = ag.get("xp", 0)
        misiones_ag = [s for s in st.session_state.historial_sesiones if s["Agente"] == nombre]
        if not misiones_ag and xp_ag == 0:
            continue
        media_ag = int(sum(s["Nota"] for s in misiones_ag) / len(misiones_ag)) if misiones_ag else 0
        nv_nom, nv_col, _, _ = get_nivel_usuario(xp_ag)
        datos_ranking.append({
            "Agente":  nombre,
            "XP":      xp_ag,
            "Nivel":   nv_nom,
            "Color":   nv_col,
            "Misiones":len(misiones_ag),
            "Media":   media_ag,
            "Racha":   ag.get("racha", 0),
        })

    datos_ranking.sort(key=lambda x: x["XP"], reverse=True)

    if not datos_ranking:
        st.markdown("<div style='text-align:center; padding:60px; color:#18213A; font-family:var(--mono); letter-spacing:0.2em;'>SIN DATOS SUFICIENTES</div>", unsafe_allow_html=True)
    else:
        col_rank_izq, col_rank_der = st.columns([3, 1], gap="large")
        
        with col_rank_izq:
            st.markdown("<div class='section-label'>CLASIFICACIÓN POR XP ACUMULADO</div>", unsafe_allow_html=True)
            podio = {0: "#FFD700", 1: "#C0C0C0", 2: "#CD7F32"}
            
            for i, row in enumerate(datos_ranking[:20]):
                pos_str = f"{i+1}"
                if i < 3:
                    color_rgb = podio[i].lstrip("#")
                    r, g, b = int(color_rgb[0:2], 16), int(color_rgb[2:4], 16), int(color_rgb[4:6], 16)
                    bg = f"rgba({r}, {g}, {b}, 0.05)"
                else:
                    bg = "transparent"
                border = podio.get(i, "#18213A")
                es_yo = row["Agente"] == u["Nombre"]

                yo_badge = ""
                if es_yo:
                    yo_badge = '<span style="font-family: var(--mono); font-size: 0.45rem; color: #4F8EF7; margin-left: 8px; background: rgba(79,142,247,0.1); padding: 2px 5px;">TÚ</span>'

                color_nombre = "#FFD700" if es_yo else "#E2EAF8"
                peso_nombre  = "700" if es_yo else "400"

                html_row = (
                    f'<div style="display:flex; align-items:center; gap:16px;'
                    f'background:{bg}; border:1px solid {border}22;'
                    f'border-left:3px solid {row["Color"]}; border-radius:2px;'
                    f'padding:12px 18px; margin-bottom:6px;">'
                    f'<div style="font-family:var(--mono); font-size:0.6rem; color:#3A4A6A; width:26px; text-align:right;">{pos_str}</div>'
                    f'<div style="flex:1;">'
                    f'<span style="color:{color_nombre}; font-weight:{peso_nombre};">{row["Agente"]}</span>'
                    f'{yo_badge}'
                    f'<span style="font-family:var(--mono); font-size:0.5rem; color:{row["Color"]}; margin-left:10px;">{row["Nivel"]}</span>'
                    f'</div>'
                    f'<div style="text-align:right; min-width:120px;">'
                    f'<div style="font-family:var(--mono); font-size:0.85rem; color:#F0A500; font-weight:700;">{row["XP"]} XP</div>'
                    f'<div style="font-family:var(--mono); font-size:0.48rem; color:#3A4A6A; margin-top:2px;">{row["Misiones"]} ops · media {row["Media"]}%</div>'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(html_row, unsafe_allow_html=True)
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

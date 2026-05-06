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
# 👑 CONFIGURACIÓN DE SUPERUSUARIO
# ─────────────────────────────────────────
COMANDANTE_SUPREMO = "CRYSIS" # <--- CAMBIA ESTO POR TU ID
LINKS_PAGO = {
    "Enterprise": "https://crysisanalitics.lemonsqueezy.com/checkout/buy/d864d72e-5ff1-4bac-966d-eafc555c5bd2",
    "Pro": "https://crysisanalitics.lemonsqueezy.com/checkout/buy/1dba647d-e120-4816-9ea0-a25492650825",
    "Individual": "https://crysisanalitics.lemonsqueezy.com/checkout/buy/adfd50b4-b2e5-40fb-9ece-30717f8828ba"
}

# --- CONEXIÓN A SUPABASE (NUBE SEGURA) ---
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
        st.error(f"⚠️ Error al conectar con Base de Datos Central: {e}")
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
        st.error(f"⚠️ Fallo crítico al sincronizar con Inteligencia Central: {e}")

# --- MOTOR DE CORREO 2FA ---
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
    except Exception as e:
        return False

# --- MOTOR DE GENERACIÓN PDF ---
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
# 1. CONFIGURACIÓN Y CSS
# ─────────────────────────────────────────
st.set_page_config(page_title="CRYSIS | Intelligence Unit", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"], .stApp { background-color: #07090F !important; color: #C8D0E0 !important; font-family: 'DM Sans', sans-serif !important; }
header[data-testid="stHeader"] { background: #07090F !important; border-bottom: 1px solid #1A2035; }
.stDeployButton, #MainMenu, footer { display: none !important; }
.crysis-title { font-family: 'IBM Plex Mono', monospace; font-size: 3.2rem; font-weight: 700; letter-spacing: 0.35em; color: #E8EDF5; text-align: center; margin-bottom: 0; text-shadow: 0 0 40px rgba(79, 142, 247, 0.25); }
.crysis-subtitle { font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem; letter-spacing: 0.45em; color: #4F8EF7; text-align: center; margin-top: 4px; margin-bottom: 28px; }
.crysis-divider { border: none; border-top: 1px solid #1A2035; margin: 0 0 32px 0; }
.stTabs [data-baseweb="tab-list"] { gap: 0; background: #0C1020; border-bottom: 1px solid #1A2035; border-radius: 0; padding: 0 8px; justify-content: center; }
.stTabs [data-baseweb="tab"] { height: 48px; padding: 0 24px; font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.15em; color: #4A5568; border-radius: 0; border: none !important; border-bottom: 2px solid transparent !important; transition: all 0.2s; }
.stTabs [data-baseweb="tab"]:hover { color: #8B9CC8; }
.stTabs [aria-selected="true"] { color: #4F8EF7 !important; background: transparent !important; border-bottom: 2px solid #4F8EF7 !important; }
.metric-card { background: #0C1020; border: 1px solid #1A2035; border-radius: 6px; padding: 22px 24px; position: relative; overflow: hidden; }
.metric-card::before { content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: #4F8EF7; }
.metric-label { font-family: 'IBM Plex Mono', monospace; font-size: 0.6rem; letter-spacing: 0.2em; color: #4F8EF7; margin-bottom: 8px; }
.metric-value { font-family: 'IBM Plex Mono', monospace; font-size: 2rem; font-weight: 700; color: #E8EDF5; line-height: 1; }
.briefing-box { background: #0C1020; border: 1px solid #1A2035; border-left: 3px solid #4F8EF7; padding: 24px 28px; border-radius: 4px; margin-bottom: 24px; }
.briefing-box h4 { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; letter-spacing: 0.2em; color: #4F8EF7; margin-bottom: 16px; }
.stTextInput input, .stSelectbox > div > div, .stTextArea textarea { background: #0C1020 !important; border: 1px solid #1A2035 !important; color: #C8D0E0 !important; border-radius: 4px !important; font-family: 'DM Sans', sans-serif !important; }
.stTextInput input:focus, .stTextArea textarea:focus { border-color: #4F8EF7 !important; box-shadow: 0 0 0 2px rgba(79,142,247,0.1) !important; }
.stButton > button { background: #4F8EF7 !important; color: #07090F !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 0.7rem !important; font-weight: 700 !important; letter-spacing: 0.15em !important; border: none !important; border-radius: 3px !important; padding: 12px 28px !important; transition: all 0.2s !important; width: auto; }
.stButton > button:hover { background: #3A7AE4 !important; box-shadow: 0 0 20px rgba(79,142,247,0.3) !important; transform: translateY(-2px); }
.section-label { font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; letter-spacing: 0.25em; color: #4F8EF7; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #1A2035; }
.status-bar { background: #0C1020; border: 1px solid #1A2035; border-left: 3px solid #22D3A5; padding: 10px 18px; border-radius: 3px; font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; letter-spacing: 0.12em; color: #22D3A5; margin-bottom: 20px; }
[data-testid="stButton"] button[disabled] { background: #1A2035 !important; color: #4A5568 !important; border: 1px solid #2A3550 !important; box-shadow: none !important; cursor: not-allowed; }
.auth-matrix { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; margin-bottom: 30px; }
.auth-tier { background: #0C1020; border: 1px solid #1A2035; border-left: 4px solid #4A5568; padding: 24px; border-radius: 4px; transition: border-color 0.3s ease; }
.auth-tier:hover { border-left-color: #4F8EF7; background: #0F1528; }
.auth-tier.elite { border-left-color: #F59E0B; }
.tier-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid #1A2035; padding-bottom: 10px; }
.tier-name { font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem; font-weight: 700; color: #E8EDF5; letter-spacing: 0.1em; }
.tier-price { font-size: 1.2rem; color: #4F8EF7; font-weight: 600; }
.tier-spec { font-size: 0.8rem; color: #8B9CC8; margin-bottom: 8px; display: flex; align-items: center; }
.tier-spec::before { content: '▪'; margin-right: 8px; color: #4F8EF7; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 2. DATOS BASE
# ─────────────────────────────────────────
INSTRUCCION_ORTOGRAFIA = " Escribe en español correcto. Nunca uses acotaciones entre paréntesis. Solo diálogo."
CONTEXTOS_MISION = {
    "OPERACION: FRONTERA": {"contexto": "Tensiones militares en el paralelo 38.", "perfil_sujeto": "Ministro Volkov.", "objetivo": "Evitar la escalada bélica.", "prompt": "Eres el Ministro de Defensa de Krasnovia. Hostil y burocrático. Solo diálogo directo." + INSTRUCCION_ORTOGRAFIA},
    "OPERACION: BLACKOUT": {"contexto": "Ataque masivo al sistema eléctrico nacional. Rescate exigido.", "perfil_sujeto": "'Shadow'. Hacker mercenario. Frío y calculador.", "objetivo": "Ganar tiempo para localizar el origen del ataque.", "prompt": "Eres Shadow, hacker de elite acorralado. Solo texto directo. Sin emociones." + INSTRUCCION_ORTOGRAFIA},
    "OPERACION: EXTRACCION": {"contexto": "Robo a banco fallido. 3 civiles retenidos.", "perfil_sujeto": "Sujeto inestable, bajo presión extrema.", "objetivo": "Asegurar la liberación de rehenes.", "prompt": "Eres un secuestrador acorralado. Gritas, estás nervioso. Solo diálogo crudo." + INSTRUCCION_ORTOGRAFIA}
}
PLOTLY_THEME = dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family='DM Sans', color='#8B9CC8', size=12), margin=dict(l=16, r=16, t=40, b=16))
AXIS_STYLE = dict(gridcolor='#1A2035', zeroline=False, color='#4A5568', linecolor='#1A2035')

# ─────────────────────────────────────────
# 3. CARGA DE MEMORIA Y ESTADOS
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

try: GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except: GROQ_API_KEY = None

# ─────────────────────────────────────────
# 4. LOGIN, REGISTRO Y AUTO-LOGIN (CIFRADO)
# ─────────────────────────────────────────
token_invitacion = st.query_params.get("invite", None)
empresa_invitada = None

if token_invitacion:
    try: empresa_invitada = base64.urlsafe_b64decode(token_invitacion.encode()).decode()
    except: pass

if st.session_state.usuario_actual is None:
    st.markdown("<div class='crysis-title' style='margin-top: 40px;'>CRYSIS</div>", unsafe_allow_html=True)

    if empresa_invitada:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown(f"<div class='crysis-subtitle'>ALISTAMIENTO ACTIVO: {empresa_invitada.upper()}</div><hr class='crysis-divider'>", unsafe_allow_html=True)
            empresa_obj = next((e for e in st.session_state.empleados if e["Rol"] == "Empresa" and e["Nombre"] == empresa_invitada), None)

            if empresa_obj:
                agentes_actuales = len([e for e in st.session_state.empleados if e.get("Empresa") == empresa_invitada and e.get("Rol") == "Agente"])
                # Verificamos el plan real de la empresa para asignar el límite
                plan_emp = empresa_obj.get("Plan", "Gratis")
                limite_agentes = 9999 if plan_emp == "Enterprise" else (15 if plan_emp == "Pro" else 0)
                
                if agentes_actuales >= limite_agentes:
                    st.error("🔒 ESTA ENTIDAD NO TIENE LICENCIA CORPORATIVA ACTIVA O HA ALCANZADO SU LÍMITE.")
                    st.stop()

            with st.form("reg_agente"):
                n = st.text_input("Identificador de Agente (ID)")
                email = st.text_input("Correo Corporativo")
                d = st.text_input("Unidad / Departamento")
                p = st.text_input("Establecer Clave de Acceso", type="password")
                if st.form_submit_button("REGISTRAR CREDENCIALES OFICIALES", use_container_width=True):
                    if n and p and email:
                        if any(e["Nombre"] == n and e.get("Empresa") == empresa_invitada for e in st.session_state.empleados):
                            st.warning("⚠️ Este ID ya está registrado en esta corporación.")
                        elif any(e["Nombre"] == n and e.get("Password") == p for e in st.session_state.empleados):
                            st.warning("⚠️ Este ID ya está en uso. Usa una CONTRASEÑA DIFERENTE a tu cuenta privada para que el sistema las distinga.")
                        else:
                            nuevo_agente = {"Nombre": n, "Email": email, "Departamento": d, "Rol": "Agente", "Empresa": empresa_invitada, "Password": p, "2FA_Verificado": True}
                            st.session_state.empleados.append(nuevo_agente); guardar_datos()
                            st.session_state.registro_completado = True
                            st.query_params.clear(); st.rerun()
    else:
        st.markdown("<div class='crysis-subtitle'>PLATAFORMA DE SIMULACIÓN TÁCTICA AVANZADA</div>", unsafe_allow_html=True)

        if st.session_state.get("registro_completado"):
            st.success("✅ Acreditación procesada y guardada en el Creador Central. Por favor, identifícate en el Portal de Acceso para entrar.")
            st.session_state.registro_completado = False

        t_log, t_reg = st.tabs(["IDENTIFICACIÓN", "NIVELES DE AUTORIZACIÓN (ALTA)"])
        with t_log:
            st.markdown("<br>", unsafe_allow_html=True)
            c_log1, c_log2, c_log3 = st.columns([1, 1.5, 1])
            with c_log2:
                if st.session_state.login_step == 1:
                    with st.form("login_directo"):
                        st.markdown("<div class='section-label'>PORTAL DE ACCESO</div>", unsafe_allow_html=True)
                        u_id = st.text_input("ID Operativo")
                        u_pass = st.text_input("Clave de Seguridad", type="password")
                        if st.form_submit_button("INICIAR CONEXIÓN", use_container_width=True):
                            agente = next((e for e in st.session_state.empleados if e["Nombre"] == u_id and e.get("Password") == u_pass), None)
                            if agente:
                                expiro = False
                                if "Expiracion" in agente:
                                    fecha_exp = datetime.strptime(agente["Expiracion"], "%Y-%m-%d")
                                    if datetime.now() > fecha_exp: expiro = True
                                if expiro: st.error(f"❌ ACCESO DENEGADO: Tu licencia expiró el {agente['Expiracion']}.")
                                else:
                                    if agente.get("2FA_Verificado", False) == True or agente["Nombre"] == COMANDANTE_SUPREMO:
                                        st.session_state.usuario_actual = agente; st.rerun()
                                    else:
                                        st.session_state["2fa_code"] = str(random.randint(100000, 999999))
                                        st.session_state["2fa_agente"] = agente
                                        st.session_state.login_step = 2; st.rerun()
                            else: st.error("❌ Identificación fallida. Revisa tu ID o Contraseña.")
                elif st.session_state.login_step == 2:
                    correo_dest = st.session_state["2fa_agente"].get("Email", "Desconocido")
                    if "correo_enviado" not in st.session_state:
                        exito = enviar_correo_2fa(correo_dest, st.session_state["2fa_code"])
                        if exito: st.success(f"📧 Código enviado a: {correo_dest}")
                        else: st.error("❌ ERROR SMTP.")
                        st.session_state["correo_enviado"] = True
                    with st.form("2fa_form"):
                        st.info("Autenticación de dispositivo requerida (Solo una vez).")
                        u_code = st.text_input("Código de Validación")
                        colA, colB = st.columns(2)
                        if colA.form_submit_button("VERIFICAR DISPOSITIVO", use_container_width=True):
                            if u_code == st.session_state["2fa_code"]:
                                st.session_state["2fa_agente"]["2FA_Verificado"] = True; guardar_datos()
                                st.session_state.usuario_actual = st.session_state["2fa_agente"]
                                st.session_state.login_step = 1; del st.session_state["correo_enviado"]; st.rerun()
                            else: st.error("❌ Código incorrecto.")
                        if colB.form_submit_button("CANCELAR", use_container_width=True):
                            st.session_state.login_step = 1; del st.session_state["correo_enviado"]; st.rerun()
        with t_reg:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div class="auth-matrix">
                <div class="auth-tier"><div class="tier-header"><span class="tier-name">NIVEL: BASE</span><span class="tier-price">0€</span></div><div class="tier-spec">Acceso Individual</div><div class="tier-spec">1 Operación Mensual</div><div class="tier-spec">Escenarios Estándar</div></div>
                <div class="auth-tier"><div class="tier-header"><span class="tier-name">NIVEL: OPERADOR</span><span class="tier-price">29€</span></div><div class="tier-spec">Acceso Individual</div><div class="tier-spec">Operaciones Ilimitadas</div><div class="tier-spec">Síntesis IA (3 Misiones)</div></div>
                <div class="auth-tier"><div class="tier-header"><span class="tier-name">NIVEL: ESCUADRÓN</span><span class="tier-price">89€</span></div><div class="tier-spec">Hasta 15 Agentes</div><div class="tier-spec">3 Operaciones/Mes por Agente</div><div class="tier-spec">Panel de Supervisión</div></div>
                <div class="auth-tier elite"><div class="tier-header"><span class="tier-name" style="color:#F59E0B;">NIVEL: COMANDANCIA</span><span class="tier-price" style="color:#F59E0B;">199€</span></div><div class="tier-spec">Agentes Ilimitados</div><div class="tier-spec">Auditoría Total (Transcripciones)</div><div class="tier-spec">Exportación de Datos CSV</div></div>
            </div>
            """, unsafe_allow_html=True)
            c_reg1, c_reg2, c_reg3 = st.columns([1, 2, 1])
            with c_reg2:
                # Mostrar enlace de pago si se acaba de registrar con plan de pago
                if st.session_state.get("mostrar_pago"):
                    info_pago = st.session_state.mostrar_pago
                    st.success(f"✅ Cuenta creada con Nivel BASE. Completa el pago para activar tu plan.")
                    st.markdown(f"""
                    <div style="background:#0C1020; border:1px solid #F59E0B; border-left:4px solid #F59E0B; padding:20px; border-radius:4px; margin-bottom:16px;">
                        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.65rem; letter-spacing:0.2em; color:#F59E0B; margin-bottom:10px;">⚡ ACTIVACIÓN DE PLAN PENDIENTE</div>
                        <p style="color:#C8D0E0; font-size:0.85rem; margin-bottom:14px;">Tu cuenta <b style='color:#E8EDF5'>{info_pago['id']}</b> ha sido creada con Nivel BASE. Tras completar el pago, el administrador activará tu plan en un máximo de 24h.</p>
                        <a href="{info_pago['link']}" target="_blank" style="display:inline-block; background:#F59E0B; color:#07090F; font-family:'IBM Plex Mono',monospace; font-weight:700; font-size:0.7rem; letter-spacing:0.1em; padding:10px 24px; border-radius:3px; text-decoration:none;">IR AL PAGO → {info_pago['plan']}</a>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("ENTRAR CON NIVEL BASE POR AHORA", use_container_width=True):
                        st.session_state.usuario_actual = info_pago["usuario"]
                        del st.session_state.mostrar_pago
                        st.rerun()
                else:
                    with st.form("registro_unificado"):
                        st.markdown("<div class='section-label'>SOLICITUD DE CREDENCIALES</div>", unsafe_allow_html=True)
                        plan_sel = st.selectbox("Seleccione Nivel", [
                            "Nivel: BASE (Gratis / 1 Usuario)",
                            "Nivel: OPERADOR (Individual / Ilimitado) — 29€/mes",
                            "Nivel: ESCUADRÓN (Corporativo / 15 Agentes) — 89€/mes",
                            "Nivel: COMANDANCIA (Corporativo / Ilimitado) — 199€/mes"
                        ])
                        es_corporativo = "Corporativo" in plan_sel
                        es_pago = "BASE" not in plan_sel
                        if es_corporativo:
                            n = st.text_input("Identificador de la Entidad (Empresa)")
                        else:
                            n = st.text_input("Identificador Personal (Alias)")
                        email = st.text_input("Correo de Contacto")
                        p = st.text_input("Clave Maestra", type="password")
                        lbl_btn = "CREAR CUENTA Y IR AL PAGO →" if es_pago else "EMITIR CREDENCIALES Y ENTRAR"
                        if st.form_submit_button(lbl_btn, use_container_width=True):
                            if n and p and email:
                                empresa_destino = n if es_corporativo else "Independiente"
                                if any(e["Nombre"] == n and e.get("Empresa", "Independiente") == empresa_destino for e in st.session_state.empleados):
                                    st.warning("⚠️ Ya tienes una cuenta de este tipo registrada.")
                                elif any(e["Nombre"] == n and e.get("Password") == p for e in st.session_state.empleados):
                                    st.warning("⚠️ ID ya en uso con esa contraseña. Usa una contraseña diferente.")
                                else:
                                    # SIEMPRE se crea con plan Gratis. El admin activa planes de pago.
                                    if es_corporativo:
                                        nuevo_usuario = {"Nombre": n, "Email": email, "Departamento": "Administración", "Rol": "Empresa", "Plan": "Gratis", "Empresa": n, "Password": p, "2FA_Verificado": True}
                                    else:
                                        nuevo_usuario = {"Nombre": n, "Email": email, "Rol": "Individual", "Plan": "Gratis", "Empresa": n, "Password": p, "2FA_Verificado": True}
                                    st.session_state.empleados.append(nuevo_usuario)
                                    guardar_datos()
                                    if es_pago:
                                        # Determinar link de pago correcto
                                        if "OPERADOR" in plan_sel: link_pago = LINKS_PAGO["Individual"]; nombre_plan = "NIVEL OPERADOR (29€/mes)"
                                        elif "ESCUADRÓN" in plan_sel: link_pago = LINKS_PAGO["Pro"]; nombre_plan = "NIVEL ESCUADRÓN (89€/mes)"
                                        else: link_pago = LINKS_PAGO["Enterprise"]; nombre_plan = "NIVEL COMANDANCIA (199€/mes)"
                                        st.session_state.mostrar_pago = {"id": n, "link": link_pago, "plan": nombre_plan, "usuario": nuevo_usuario}
                                        st.rerun()
                                    else:
                                        st.session_state.usuario_actual = nuevo_usuario
                                        st.rerun()
                            else:
                                st.warning("⚠️ Información incompleta.")
    st.stop()

# ─────────────────────────────────────────
# 5. RESOLUCIÓN DE PERMISOS
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

rol_label = f"SUPERVISIÓN [{mi_plan.upper()}]" if es_empresa else f"AGENTE: {empresa_actual.upper()} [{mi_plan.upper()}]"
if u["Nombre"] == COMANDANTE_SUPREMO: rol_label = "👑 OMNISCIENCIA GLOBAL"

c_head1, c_head2 = st.columns([8, 1])
with c_head1:
    st.markdown("<div class='crysis-title' style='text-align:left; font-size:2.2rem;'>CRYSIS</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='crysis-subtitle' style='text-align:left; margin-bottom:10px;'>{rol_label} | ID: {u['Nombre'].upper()}</div>", unsafe_allow_html=True)
with c_head2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("DESCONECTAR", key="logout", type="secondary"): st.session_state.usuario_actual = None; st.session_state.login_step = 1; st.rerun()
st.markdown("<hr class='crysis-divider' style='margin-top:0;'>", unsafe_allow_html=True)

# FILTRO Y MODO FANTASMA
if u["Nombre"] == COMANDANTE_SUPREMO:
    historial_visible = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]
    agentes_de_mi_empresa = [u["Nombre"]]
elif es_empresa:
    agentes_de_mi_empresa = [e["Nombre"] for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"]
    historial_visible = [s for s in st.session_state.historial_sesiones if s["Agente"] in agentes_de_mi_empresa and s.get("Tipo_Mision", "Corporativa") != "Personal"]
else:
    historial_visible = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]

mis_escenarios = {k: v for k, v in st.session_state.escenarios_custom.items() if v.get("Creador") == empresa_actual or u["Nombre"] == COMANDANTE_SUPREMO}
TODAS_LAS_MISIONES = {**CONTEXTOS_MISION, **mis_escenarios}

if u["Nombre"] == COMANDANTE_SUPREMO: t1, t2, t3, t4, t5 = st.tabs(["MÉTRICAS GLOBALES", "GESTIÓN DE PERSONAL", "EXPEDIENTES", "DESPLIEGUE", "CONSOLA OMEGA (ADMIN)"])
elif es_empresa: t1, t2, t3, t4, t5 = st.tabs(["MÉTRICAS GLOBALES", "GESTIÓN DE PERSONAL", "ARCHIVO OPERACIONAL", "DESPLIEGUE", "SÍNTESIS IA"])
elif u["Rol"] == "Individual" or mi_plan == "Gratis": t1, t2, t3, t4, t5 = st.tabs(["ESTADÍSTICAS", "PERFIL Y CUENTA", "EXPEDIENTES", "DESPLIEGUE", "SÍNTESIS IA"])
else:
    t1, t2, t3, t4 = st.tabs(["MÉTRICAS", "PERFIL Y CUENTA", "EXPEDIENTES", "DESPLIEGUE"])
    t5 = None

# ══════════════════════════════════════════
# TAB 1: ESTADÍSTICAS
# ══════════════════════════════════════════
with t1:
    total_ops = len(historial_visible)
    media_global = int(sum(s["Nota"] for s in historial_visible) / total_ops) if total_ops > 0 else 0
    ops_exitosas = sum(1 for s in historial_visible if s["Nota"] >= 80)
    tasa_exito = int((ops_exitosas / total_ops) * 100) if total_ops > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""<div class="metric-card"><div class="metric-label">RENDIMIENTO MEDIO</div><div class="metric-value" style="color:{'#22D3A5' if media_global >= 70 else '#EF4444'}">{media_global}%</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="metric-card"><div class="metric-label">TASA DE EXCELENCIA (>80%)</div><div class="metric-value" style="color:{'#22D3A5' if tasa_exito >= 50 else '#EF4444'}">{tasa_exito}%</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="metric-card"><div class="metric-label">MISIONES COMPLETADAS</div><div class="metric-value" style="color:#4F8EF7">{total_ops}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if not historial_visible:
        st.markdown("<div style='text-align:center; padding: 60px; color: #2A3550; font-family: IBM Plex Mono; letter-spacing: 0.2em;'>SIN REGISTROS OPERACIONALES</div>", unsafe_allow_html=True)
    else:
        df = pd.DataFrame(historial_visible)
        df["Nota"] = pd.to_numeric(df["Nota"])
        col_left, col_right = st.columns(2, gap="medium")
        with col_left:
            st.markdown("<div class='section-label'>DISTRIBUCIÓN DE ESCENARIOS</div>", unsafe_allow_html=True)
            esc_count = df["Escenario"].value_counts().reset_index()
            esc_count.columns = ["Escenario", "Count"]
            fig2 = go.Figure(go.Pie(labels=esc_count["Escenario"], values=esc_count["Count"], hole=0.65, marker=dict(colors=['#4F8EF7', '#22D3A5', '#F59E0B'])))
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
                fig3 = go.Figure(go.Scatter(x=df_sorted["Fecha_dt"], y=df_sorted["Nota"], mode='lines+markers', line=dict(color='#4F8EF7')))
                fig3.add_hline(y=80, line_dash="dot", line_color="#22D3A5")
                fig3.update_layout(**PLOTLY_THEME, height=280)
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

# ══════════════════════════════════════════
# TAB 2: GESTIÓN DE PERSONAL / ENLACE CIFRADO
# ══════════════════════════════════════════
with t2:
    if es_empresa:
        st.markdown("<div class='section-label'>ENLACE SEGURO DE RECLUTAMIENTO</div>", unsafe_allow_html=True)
        
        # Solo mostramos el link si tienen plan Corporativo (Pro/Enterprise) o son el Comandante
        if mi_plan in ["Pro", "Enterprise"] or u["Nombre"] == COMANDANTE_SUPREMO:
            token_cifrado = base64.urlsafe_b64encode(empresa_actual.encode()).decode()
            URL_BASE_APP = "https://crysis.streamlit.app/"
            enlace_completo = f"{URL_BASE_APP}?invite={token_cifrado}"
            st.info("Copia y comparte este enlace directo con tus agentes para que se unan a tu unidad automáticamente.")
            st.code(enlace_completo, language="html")
        else:
            st.warning("🔒 Tu nivel de licencia actual (BASE o OPERADOR) no permite la formación de escuadrones. Actualiza a ESCUADRÓN o COMANDANCIA para habilitar el reclutamiento de agentes.")

        st.markdown("<br><div class='section-label'>PLANTILLA OPERATIVA ACTIVA</div>", unsafe_allow_html=True)
        agentes_mios = [e for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"]
        if agentes_mios:
            for ag in agentes_mios: st.markdown(f"**{ag['Nombre']}** | Unidad: {ag['Departamento']} | Contacto: {ag['Email']}")
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("🗑️ REVOCAR ACCESO DE PERSONAL"):
                ag_a_borrar = st.selectbox("Seleccione el operador a revocar:", [a['Nombre'] for a in agentes_mios])
                if st.button("REVOCAR CREDENCIALES DE AGENTE", type="primary"):
                    st.session_state.empleados = [e for e in st.session_state.empleados if e['Nombre'] != ag_a_borrar]
                    guardar_datos(); st.success(f"Operador {ag_a_borrar} revocado."); st.rerun()
        else:
            st.markdown("No hay agentes activos en esta unidad.")
    else:
        st.markdown("<div class='section-label'>ACREDITACIÓN CONFIRMADA</div>", unsafe_allow_html=True)
        st.markdown(f"""<div class="briefing-box" style="border-left-color:#22D3A5;"><h4 style="color:#22D3A5;">🛡️ DATOS DEL OPERADOR</h4><p><b>Identificador:</b> {u['Nombre']} | <b>Unidad Asignada:</b> {empresa_actual}</p></div>""", unsafe_allow_html=True)

    st.markdown("<br><div class='section-label'>PORTAL DE AUTOGESTIÓN Y SEGURIDAD</div>", unsafe_allow_html=True)
    with st.expander("⚙️ AJUSTES DE CUENTA", expanded=False):
        st.markdown("##### Cambiar Clave de Acceso")
        nueva_pass = st.text_input("Nueva Contraseña", type="password")
        if st.button("ACTUALIZAR CONTRASEÑA"):
            if nueva_pass:
                for e in st.session_state.empleados:
                    if e["Nombre"] == u["Nombre"]: e["Password"] = nueva_pass
                st.session_state.usuario_actual["Password"] = nueva_pass
                guardar_datos(); st.success("✅ Contraseña actualizada.")
            else: st.warning("Introduce una contraseña válida.")

        st.markdown("---")

        if u["Nombre"] != COMANDANTE_SUPREMO:
            st.markdown("##### Gestión de Suscripción Personal (SaaS)")

            if u.get("Rol") == "Agente":
                # Agente de empresa: ofrecemos mejorar su cuenta personal
                st.info("💡 Tu corporación cubre tus misiones oficiales. Puedes adquirir el Nivel OPERADOR para tener misiones de entrenamiento privadas e ilimitadas.")
                planes_disp = ["Plan Base (Corporativo)", "Individual (Operador Premium)"]
                index_actual = 1 if u.get("Plan_Privado") == "Individual" else 0
                nuevo_plan = st.selectbox("Mejora tu Nivel:", planes_disp, index=index_actual)
                if st.button("ACTUALIZAR LICENCIA PRIVADA"):
                    plan_interno = "Individual" if "Operador" in nuevo_plan else "Gratis"
                    with st.spinner("Actualizando licencias..."):
                        for e in st.session_state.empleados:
                            if e["Nombre"] == u["Nombre"]: e["Plan_Privado"] = plan_interno
                        st.session_state.usuario_actual["Plan_Privado"] = plan_interno
                        guardar_datos()
                        st.success("✅ Licencia privada actualizada a Premium.")
                        st.rerun()
            else:
                # Usuario independiente o empresa: mostrar tabla de planes
                st.markdown("#### ACTUALIZAR NIVEL DE SUSCRIPCIÓN")
                st.markdown("<br>", unsafe_allow_html=True)
                col_p1, col_p2, col_p3 = st.columns(3)

                with col_p1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">NIVEL OPERADOR</div>
                        <div class="metric-value" style="font-size:1.4rem;">29€<span style="font-size:0.8rem">/mes</span></div>
                        <div class="metric-sub">Ilimitado · Individual</div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    if mi_plan == "Individual":
                        st.success("✅ Plan activo")
                    else:
                        st.markdown(f'<a href="{LINKS_PAGO["Individual"]}" target="_blank"><button style="background:#4F8EF7;color:#07090F;font-family:IBM Plex Mono,monospace;font-weight:700;border:none;padding:10px;border-radius:3px;cursor:pointer;width:100%;font-size:0.7rem;letter-spacing:0.1em;">ACTIVAR →</button></a>', unsafe_allow_html=True)

                with col_p2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">NIVEL ESCUADRÓN</div>
                        <div class="metric-value" style="font-size:1.4rem;">89€<span style="font-size:0.8rem">/mes</span></div>
                        <div class="metric-sub">15 Agentes · Corporativo</div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    if mi_plan == "Pro":
                        st.success("✅ Plan activo")
                    else:
                        st.markdown(f'<a href="{LINKS_PAGO["Pro"]}" target="_blank"><button style="background:#4F8EF7;color:#07090F;font-family:IBM Plex Mono,monospace;font-weight:700;border:none;padding:10px;border-radius:3px;cursor:pointer;width:100%;font-size:0.7rem;letter-spacing:0.1em;">ACTIVAR →</button></a>', unsafe_allow_html=True)

                with col_p3:
                    st.markdown(f"""
                    <div class="metric-card" style="border-left-color:#F59E0B;">
                        <div class="metric-label" style="color:#F59E0B;">NIVEL COMANDANCIA</div>
                        <div class="metric-value" style="font-size:1.4rem;">199€<span style="font-size:0.8rem">/mes</span></div>
                        <div class="metric-sub">Ilimitado · Enterprise</div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    if mi_plan == "Enterprise":
                        st.success("✅ Plan activo")
                    else:
                        st.markdown(f'<a href="{LINKS_PAGO["Enterprise"]}" target="_blank"><button style="background:#F59E0B;color:#07090F;font-family:IBM Plex Mono,monospace;font-weight:700;border:none;padding:10px;border-radius:3px;cursor:pointer;width:100%;font-size:0.7rem;letter-spacing:0.1em;">ACTIVAR →</button></a>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                st.info("💡 Tras completar el pago en Lemon Squeezy, tu plan se actualizará automáticamente en un máximo de 5 minutos.")

        st.markdown("---")
        st.markdown("##### Zona de Riesgo")
        if st.button("🚨 ELIMINAR MI CUENTA DEFINITIVAMENTE", type="primary"):
            if es_empresa: st.session_state.empleados = [e for e in st.session_state.empleados if e.get("Empresa") != u["Nombre"]]
            else: st.session_state.empleados = [e for e in st.session_state.empleados if e["Nombre"] != u["Nombre"]]
            st.session_state.usuario_actual = None; guardar_datos(); st.rerun()

# ══════════════════════════════════════════
# TAB 3: EXPEDIENTES (OMNISCIENCIA)
# ══════════════════════════════════════════
with t3:
    st.markdown("<div class='section-label'>BASE DE DATOS DE EXPEDIENTES</div>", unsafe_allow_html=True)
    if historial_visible:
        df_hist = pd.DataFrame(historial_visible)
        df_hist["Nota"] = pd.to_numeric(df_hist["Nota"])
        for agente, df_agente in df_hist.groupby("Agente"):
            media_agente = int(df_agente["Nota"].mean())
            with st.expander(f"👤 OPERADOR: {agente.upper()}  ·  MÉTRICA GLOBAL: {media_agente}%", expanded=False):
                st.markdown("<br>", unsafe_allow_html=True)
                for escenario, df_op in df_agente.groupby("Escenario"):
                    media_op = int(df_op["Nota"].mean())
                    lbl_esc = escenario.replace("OPERACION: ", "")
                    with st.expander(f"⬡ {lbl_esc} · Evaluación Media: {media_op}%", expanded=True):
                        for _, s in df_op.sort_values("Fecha", ascending=False).iterrows():
                            nota_ind = s['Nota']
                            c_nota = "#22D3A5" if nota_ind >= 80 else ("#F59E0B" if nota_ind >= 50 else "#EF4444")
                            modo_badge = "👻 PRIVADO" if s.get("Tipo_Mision") == "Personal" else "🛡️ OFICIAL"
                            st.markdown(f"""<div style="border-bottom: 1px solid #1A2035; padding: 12px 0; margin-bottom: 12px;">
                            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                                <span style="color:#8B9CC8; font-size:0.8rem;">{s['Fecha']} | <span style="color:#4A5568;">{modo_badge}</span></span>
                                <span style="font-family:IBM Plex Mono, monospace; color:{c_nota}; font-weight:700;">{nota_ind}%</span>
                            </div>
                            <div style="font-size:0.85rem; color:#C8D0E0; margin-bottom:10px;">{s['Evaluacion']}</div>""", unsafe_allow_html=True)
                            st.download_button(label="📄 EXTRAER DOSSIER PDF", data=generar_pdf_dossier(s), file_name=f"CRYSIS_{s['Agente']}_{s['Fecha'][:10]}.pdf", mime="application/pdf", key=f"pdf_{s['Agente']}_{s['Fecha']}")
                            if es_empresa and mi_plan == "Enterprise" and "Transcripcion" in s:
                                st.markdown("<br><span style='color:#F59E0B; font-size:0.7rem; letter-spacing:0.1em;'>🔍 AUDITORÍA DE COMUNICACIONES</span>", unsafe_allow_html=True)
                                for tr in s["Transcripcion"]:
                                    ag = "OPERADOR" if tr["role"] == "user" else "SUJETO"
                                    colr = "#4F8EF7" if tr["role"] == "user" else "#EF4444"
                                    st.markdown(f"<div style='font-size:0.8rem; margin-bottom:4px;'><b style='color:{colr}'>{ag}:</b> <span style='color:#8B9CC8'>{tr['content']}</span></div>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center; padding:60px; color:#2A3550; font-family:IBM Plex Mono;'>DIRECTORIO VACÍO</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════
# TAB 4: SIMULADOR (CON MODO FANTASMA)
# ══════════════════════════════════════════
with t4:
    if not st.session_state.mision_iniciada:
        st.markdown("<div class='section-label'>PARÁMETROS DE DESPLIEGUE</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        ag_sel = c1.selectbox("Asignar Operador:", agentes_de_mi_empresa) if es_empresa else c1.text_input("Operador:", value=u["Nombre"], disabled=True)
        if ag_sel is None and es_empresa: ag_sel = u["Nombre"]
        es_sel = c2.selectbox("Seleccionar Protocolo:", list(TODAS_LAS_MISIONES.keys()))

        # MODO FANTASMA (Solo para Agentes de Empresa)
        if u.get("Rol") == "Agente":
            st.markdown("<br>", unsafe_allow_html=True)
            tipo_despliegue = st.radio("Nivel de Privacidad de la Operación:", ["🛡️ Misión Oficial (Auditable por el Mando)", "👻 Entrenamiento Privado (Oculto en expediente personal)"], horizontal=True)
            tipo_mision_val = "Corporativa" if "Oficial" in tipo_despliegue else "Personal"
        else: tipo_mision_val = "Personal"

        info = TODAS_LAS_MISIONES[es_sel]
        st.markdown(f"""<div class="briefing-box"><h4>📄 REPORTE DE SITUACIÓN</h4><p><b>Contexto:</b> {info['contexto']}</p><p><b>Perfil:</b> {info['perfil_sujeto']}</p><p><b>Directiva:</b> {info['objetivo']}</p></div>""", unsafe_allow_html=True)

        mes_actual = datetime.now().strftime("%Y-%m")
        ops_este_mes = len([s for s in st.session_state.historial_sesiones if s["Agente"] == ag_sel and str(s.get("Fecha", "")).startswith(mes_actual)])

        bloquear_inicio = False
        if mi_plan == "Gratis" and ops_este_mes >= 1:
            bloquear_inicio = True; st.error(f"🔒 AUTORIZACIÓN DENEGADA: Cuota del Nivel BASE superada.")
        elif mi_plan == "Pro" and ops_este_mes >= 3:
            bloquear_inicio = True; st.error(f"🔒 AUTORIZACIÓN DENEGADA: Cuota del Nivel ESCUADRÓN superada para el operador {ag_sel}.")

        if st.button("INICIAR ENLACE DE COMUNICACIÓN →", use_container_width=True, disabled=bloquear_inicio):
            if GROQ_API_KEY:
                with st.spinner("Estableciendo conexión..."):
                    try:
                        client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                        json_prompt = f"Genera para {info['perfil_sujeto']} EXCLUSIVAMENTE JSON PLANO (cadenas de texto breves) con 3 claves: 'Nombre_Completo', 'Familia', 'Estado_Mental'."
                        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": json_prompt}], response_format={"type": "json_object"}).choices[0].message.content
                        st.session_state.tarjeta_objetivo = json.loads(res)
                    except: st.session_state.tarjeta_objetivo = {"Nombre_Completo": "Desconocido", "Familia": "Clasificado", "Estado_Mental": "Inestable"}
            st.session_state.mision_iniciada = True; st.session_state.mensajes = []; st.session_state.agente_activo = ag_sel; st.session_state.escenario_activo = es_sel; st.session_state.tipo_mision_actual = tipo_mision_val; st.rerun()

    elif st.session_state.evaluacion_actual:
        st.markdown("<div class='section-label'>INFORME DE EVALUACIÓN TÁCTICA</div>", unsafe_allow_html=True)
        st.markdown(st.session_state.evaluacion_actual)
        st.markdown("<br>", unsafe_allow_html=True)
        col_end1, col_end2 = st.columns(2)
        with col_end1:
            if st.button("ARCHIVAR INFORME Y VOLVER →", use_container_width=True):
                st.session_state.mision_iniciada = False; st.session_state.evaluacion_actual = None; st.session_state.mensajes = []; st.session_state.tarjeta_objetivo = None; st.rerun()
        with col_end2:
            ultima_sesion = st.session_state.historial_sesiones[-1]
            st.download_button(label="📄 DESCARGAR DOSSIER PDF AHORA", data=generar_pdf_dossier(ultima_sesion), file_name=f"CRYSIS_{ultima_sesion['Agente']}_Report.pdf", mime="application/pdf", use_container_width=True)

    else:
        st.markdown(f"<div class='status-bar'>◉ LÍNEA SEGURA ACTIVA: {st.session_state.escenario_activo} · OPERADOR: {st.session_state.agente_activo.upper()}</div>", unsafe_allow_html=True)
        if st.session_state.tarjeta_objetivo:
            t = st.session_state.tarjeta_objetivo
            st.markdown(f"""<div style="display:flex; gap:15px; background:#0C1020; border:1px solid #1A2035; border-left:3px solid #F59E0B; border-radius:4px; padding:12px 18px; margin-bottom:20px;">
                <div style="flex:1;"><div style="color:#F59E0B; font-size:0.55rem; font-family:'IBM Plex Mono'; letter-spacing:0.15em; margin-bottom:4px;">IDENTIFICACIÓN</div><div style="color:#E8EDF5; font-size:0.85rem;">{str(t.get('Nombre_Completo', 'N/A'))}</div></div>
                <div style="flex:1;"><div style="color:#F59E0B; font-size:0.55rem; font-family:'IBM Plex Mono'; letter-spacing:0.15em; margin-bottom:4px;">VÍNCULOS</div><div style="color:#C8D0E0; font-size:0.8rem;">{str(t.get('Familia', 'N/A'))}</div></div>
                <div style="flex:1;"><div style="color:#F59E0B; font-size:0.55rem; font-family:'IBM Plex Mono'; letter-spacing:0.15em; margin-bottom:4px;">ESTADO CLÍNICO</div><div style="color:#C8D0E0; font-size:0.8rem;">{str(t.get('Estado_Mental', 'N/A'))}</div></div>
            </div>""", unsafe_allow_html=True)

        for m in st.session_state.mensajes:
            label = "TÚ" if m["role"] == "user" else "SUJETO"
            bg = "#0F1829" if m["role"] == "user" else "#0C1020"
            border = "#4F8EF7" if m["role"] == "user" else "#EF4444"
            align = "flex-end" if m["role"] == "user" else "flex-start"
            st.markdown(f"""<div style="display:flex; justify-content:{align}; margin-bottom:12px;"><div style="max-width:78%; background:{bg}; border:1px solid {border}22; border-left: 3px solid {border}; border-radius:4px; padding:14px 18px;"><div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.18em; color:{border}; margin-bottom:8px;">{label}</div><div style="color:#C8D0E0; font-size:0.9rem; line-height:1.6;">{m['content']}</div></div></div>""", unsafe_allow_html=True)

        if prompt := st.chat_input("Introduzca directiva de respuesta..."):
            st.session_state.mensajes.append({"role": "user", "content": prompt}); st.rerun()

        if st.session_state.mensajes and st.session_state.mensajes[-1]["role"] == "user":
            if GROQ_API_KEY:
                client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                base_prompt = TODAS_LAS_MISIONES[st.session_state.escenario_activo]["prompt"]
                if st.session_state.tarjeta_objetivo: base_prompt += f"\n\n[INSTRUCCIÓN VITAL: Tu nombre es {st.session_state.tarjeta_objetivo.get('Nombre_Completo')}. Familia: {st.session_state.tarjeta_objetivo.get('Familia')}. Estado actual: {st.session_state.tarjeta_objetivo.get('Estado_Mental')}.]"
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": base_prompt}] + st.session_state.mensajes).choices[0].message.content
                st.session_state.mensajes.append({"role": "assistant", "content": res})
                st.rerun()

        col_end, col_abort = st.columns([3, 1])
        with col_abort:
            if st.button("✖ ROMPER ENLACE", type="secondary", use_container_width=True):
                st.session_state.mision_iniciada = False; st.session_state.mensajes = []; st.session_state.tarjeta_objetivo = None; st.rerun()
        with col_end:
            if len(st.session_state.mensajes) > 0:
                if st.button("🛑 SOLICITAR EVALUACIÓN TÁCTICA →", use_container_width=True):
                    with st.spinner("Procesando auditoría lingüística (ANALISTA ESTRICTO)..."):
                        client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                        escenario = st.session_state.escenario_activo
                        info = TODAS_LAS_MISIONES[escenario]
                        hist_txt = "\n".join([f"{'OPERADOR' if m['role'] == 'user' else 'SUJETO'}: {m['content']}" for m in st.session_state.mensajes])

                        eval_prompt = f"""Eres un Analista de Inteligencia y Negociación Táctica altamente estricto e implacable. 
                        Evalúa el desempeño del OPERADOR en el escenario: {escenario}. Situación base: {info['contexto']}.
                        TRANSCRIPCIÓN COMPLETA DE LA OPERACIÓN:\n{hist_txt}\n
                        REGLAS DE EVALUACIÓN (CRÍTICO):
                        1. NO regales puntuación por cortesía ("buenos días", "hola"). Eso es lo mínimo esperado.
                        2. Un puntaje de 80-100 SOLO se otorga si hay un control absoluto de la crisis, uso de técnicas avanzadas de desescalada, empatía táctica y resolución impecable.
                        3. Puntuación de 50-70 es para un trabajo ya bueno: no empeoró la situación, pero tampoco usó técnicas profesionales de persuasión.
                        4. Puntuación de 0-49 si el operador cede muy rápido, es manipulado, usa lenguaje amenazante o rompe protocolos de rehenes.
                        
                        Estructura tu informe exactamente así:
                        **ANÁLISIS DE LENGUAJE Y PSICOLOGÍA**
                        **TÁCTICAS EMPLEADAS (O AUSENTES)**
                        **ERRORES CRÍTICOS**
                        **VEREDICTO DEL ANALISTA**
                        **CÓMO MEJORAR**
                        
                        PUNTUACIÓN FINAL: XX/100"""

                        informe = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": eval_prompt}]).choices[0].message.content
                        try:
                            match = re.search(r'PUNTUACI[OÓ]N FINAL[^\d]*(\d+)\s*\/?\s*100', informe, re.IGNORECASE)
                            nota = min(int(match.group(1)), 100) if match else (min(int(re.search(r'(\d+)\s*/\s*100', informe).group(1)), 100) if re.search(r'(\d+)\s*/\s*100', informe) else 50)
                        except: nota = 50

                        st.session_state.evaluacion_actual = informe
                        st.session_state.historial_sesiones.append({"Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "Agente": st.session_state.agente_activo, "Escenario": escenario, "Nota": nota, "Evaluacion": informe, "Transcripcion": st.session_state.mensajes, "Tipo_Mision": st.session_state.tipo_mision_actual})
                        guardar_datos(); st.rerun()

# ══════════════════════════════════════════
# TAB 5: SÍNTESIS IA Y CONSOLA OMEGA (SUPERADMIN)
# ══════════════════════════════════════════
if t5:
    with t5:
        if u["Nombre"] == COMANDANTE_SUPREMO:
            st.markdown("<div class='section-label'>RADAR ESTRATÉGICO (SAAS METRICS)</div>", unsafe_allow_html=True)
            clientes_corporativos = [e for e in st.session_state.empleados if e["Rol"] == "Empresa"]
            clientes_individuales = [e for e in st.session_state.empleados if e["Rol"] == "Individual"]
            todos_clientes = clientes_corporativos + clientes_individuales
            total_enterprise = len([c for c in todos_clientes if c.get("Plan") == "Enterprise"])
            total_pro = len([c for c in todos_clientes if c.get("Plan") == "Pro"])
            total_indiv = len([c for c in todos_clientes if c.get("Plan") == "Individual"])
            total_gratis = len([c for c in todos_clientes if c.get("Plan") == "Gratis"])
            mrr_estimado = (total_enterprise * 199) + (total_pro * 89) + (total_indiv * 29)
            total_agentes = len([e for e in st.session_state.empleados if e["Rol"] == "Agente"])
            total_operaciones = len(st.session_state.historial_sesiones)
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.markdown(f"""<div class="metric-card" style="border-left-color:#F59E0B;"><div class="metric-label" style="color:#F59E0B;">MRR ESTIMADO</div><div class="metric-value">{mrr_estimado}€</div></div>""", unsafe_allow_html=True)
            col_m2.markdown(f"""<div class="metric-card"><div class="metric-label">CUENTAS PAGO</div><div class="metric-value">{total_enterprise + total_pro + total_indiv}</div></div>""", unsafe_allow_html=True)
            col_m3.markdown(f"""<div class="metric-card"><div class="metric-label">AGENTES DESPLEGADOS</div><div class="metric-value">{total_agentes}</div></div>""", unsafe_allow_html=True)
            col_m4.markdown(f"""<div class="metric-card"><div class="metric-label">SESIONES TOTALES</div><div class="metric-value">{total_operaciones}</div></div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

           with st.expander("🌍 GESTIÓN GLOBAL DE USUARIOS (OMNISCIENCIA)", expanded=False):
                st.info("Directorio completo de agentes y corporaciones registradas.")
                # Añadimos enumerate para que cada botón tenga un ID único (i)
                for i, usr in enumerate(st.session_state.empleados):
                    if usr["Nombre"] != COMANDANTE_SUPREMO:
                        c_u1, c_u2 = st.columns([4, 1])
                        c_u1.markdown(f"**ID:** {usr['Nombre']} | **Rol:** {usr['Rol']} | **Email:** {usr['Email']}")
                        # Se añade _{i} a la clave del botón
                        if c_u2.button("PURGAR", key=f"del_g_{usr['Nombre']}_{i}", type="secondary"):
                            st.session_state.empleados = [e for e in st.session_state.empleados if e["Nombre"] != usr["Nombre"]]
                            guardar_datos(); st.rerun()

            with st.expander("🌍 GESTIÓN GLOBAL DE ESCENARIOS", expanded=False):
                st.info("Monitorización de simulaciones creadas por las corporaciones.")
                if not st.session_state.escenarios_custom: st.markdown("No hay escenarios personalizados en la base de datos.")
                for n_esc, d_esc in st.session_state.escenarios_custom.items():
                    c_e1, c_e2 = st.columns([4, 1])
                    c_e1.markdown(f"**{n_esc}** | Creador: {d_esc.get('Creador', 'Desconocido')}")
                    if c_e2.button("ELIMINAR", key=f"del_g_esc_{n_esc}", type="secondary"):
                        del st.session_state.escenarios_custom[n_esc]
                        guardar_datos(); st.rerun()

        col_izq, col_der = st.columns([2, 1], gap="large")
        with col_izq:
            if u["Nombre"] != COMANDANTE_SUPREMO: st.markdown("<div class='section-label'>MÓDULO DE SÍNTESIS DE ESCENARIOS</div>", unsafe_allow_html=True)
            creados = len(mis_escenarios)
            if mis_escenarios and u["Nombre"] != COMANDANTE_SUPREMO:
                st.markdown("#### TUS ESCENARIOS ACTIVOS")
                for nombre_esc, datos_esc in mis_escenarios.items():
                    c_esc1, c_esc2 = st.columns([3, 1])
                    c_esc1.markdown(f"<span style='color:#C8D0E0;'>{nombre_esc}</span>", unsafe_allow_html=True)
                    if c_esc2.button("🗑️ ELIMINAR", key=f"del_{nombre_esc}", type="secondary"):
                        del st.session_state.escenarios_custom[nombre_esc]; guardar_datos(); st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)

            if u["Nombre"] != COMANDANTE_SUPREMO:
                if mi_plan == "Gratis":
                    st.error("🔒 RESTRICCIÓN DE SISTEMA: El Nivel BASE no posee autorización para el uso de Inteligencia Artificial Generativa.")
                    st.button("✨ GENERAR NUEVA SIMULACIÓN", disabled=True)
                else:
                    limite_escenarios = 3 if mi_plan == "Individual" else (1 if mi_plan == "Pro" else 9999)
                    if creados >= limite_escenarios:
                        st.error(f"🔒 CUOTA DE SÍNTESIS ALCANZADA ({creados}/{limite_escenarios}). Borre uno existente para crear otro.")
                        st.button("✨ GENERAR NUEVA SIMULACIÓN", disabled=True)
                    else:
                        idea_prompt = st.text_area("Describa los parámetros del entorno táctico:", height=100)
                        if st.button("✨ GENERAR NUEVA SIMULACIÓN", use_container_width=True):
                            if idea_prompt and GROQ_API_KEY:
                                with st.spinner("Enlazando con el motor de Inteligencia Central..."):
                                    try:
                                        client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                                        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": "Devuelve JSON: {'nombre_op': 'OPERACION: [NOMBRE]', 'contexto': '[Desc]', 'perfil_sujeto': '[Perfil]', 'objetivo': '[Misión]', 'prompt': '[Instrucciones]'} "}, {"role": "user", "content": idea_prompt}], response_format={"type": "json_object"}).choices[0].message.content
                                        nuevo_esc = json.loads(res)
                                        nuevo_esc["prompt"] += INSTRUCCION_ORTOGRAFIA
                                        st.session_state.escenarios_custom[nuevo_esc["nombre_op"]] = {"contexto": nuevo_esc["contexto"], "perfil_sujeto": nuevo_esc["perfil_sujeto"], "objetivo": nuevo_esc["objetivo"], "prompt": nuevo_esc["prompt"], "Creador": empresa_actual}
                                        guardar_datos(); st.success(f"✅ Protocolo {nuevo_esc['nombre_op']} configurado."); st.rerun()
                                    except Exception as e: st.error(f"❌ Fallo de Motor IA: {e}")
                            elif not idea_prompt: st.warning("Escriba los parámetros base.")

        with col_der:
            if u["Nombre"] == COMANDANTE_SUPREMO:
                st.markdown("<div class='section-label'>HERRAMIENTAS DE MANDO</div>", unsafe_allow_html=True)

                with st.expander("🛠️ EMITIR CREDENCIAL DE CORTESÍA (NUEVA CUENTA)", expanded=True):
                    st.info("Genera cuentas nuevas con cualquier plan, saltando el pago.")
                    with st.form("admin_create_user"):
                        new_n = st.text_input("ID / Entidad")
                        new_email = st.text_input("Correo Electrónico")
                        new_pass = st.text_input("Contraseña", type="password")
                        new_rol = st.selectbox("Rol Estructural", ["Individual", "Empresa"])
                        new_plan = st.selectbox("Nivel a Otorgar", ["Gratis", "Individual", "Pro", "Enterprise"])
                        expira = st.checkbox("Licencia Temporal (30 días)", value=False)
                        if st.form_submit_button("GENERAR ACCESO", use_container_width=True):
                            if new_n and new_email and new_pass:
                                if any(e["Nombre"] == new_n for e in st.session_state.empleados):
                                    st.warning("⚠️ ID ya registrado. Usa 'Actualizar Plan' para cambiar el plan de un usuario existente.")
                                else:
                                    fecha_exp_str = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d") if expira else None
                                    nuevo_usuario = {"Nombre": new_n, "Email": new_email, "Rol": new_rol, "Plan": new_plan, "Empresa": new_n, "Password": new_pass, "2FA_Verificado": True}
                                    if new_rol == "Empresa": nuevo_usuario["Departamento"] = "Administración"
                                    if fecha_exp_str: nuevo_usuario["Expiracion"] = fecha_exp_str
                                    st.session_state.empleados.append(nuevo_usuario)
                                    guardar_datos()
                                    st.success(f"✅ Cuenta '{new_n}' creada con plan {new_plan}. Expira: {fecha_exp_str if expira else 'Nunca'}.")
                            else:
                                st.warning("⚠️ Rellena todos los campos.")

                st.markdown("<br>", unsafe_allow_html=True)

                with st.expander("⚡ ACTIVAR / CAMBIAR PLAN DE USUARIO EXISTENTE", expanded=True):
                    st.info("Activa el plan de pago de un usuario que ya pagó o concede cortesía.")
                    usuarios_no_admin = [e for e in st.session_state.empleados if e["Nombre"] != COMANDANTE_SUPREMO]
                    if usuarios_no_admin:
                        with st.form("admin_upgrade_plan"):
                            opciones_usuarios = [f"{e['Nombre']} [{e.get('Rol','?')}] — Plan actual: {e.get('Plan','?')}" for e in usuarios_no_admin]
                            sel_idx = st.selectbox("Seleccionar Usuario:", range(len(opciones_usuarios)), format_func=lambda i: opciones_usuarios[i])
                            nuevo_plan_upgrade = st.selectbox("Nuevo Plan a Asignar:", ["Gratis", "Individual", "Pro", "Enterprise"])
                            nueva_exp = st.checkbox("Añadir expiración (30 días)", value=False)
                            if st.form_submit_button("✅ APLICAR PLAN", use_container_width=True):
                                usuario_objetivo = usuarios_no_admin[sel_idx]
                                fecha_exp_str = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d") if nueva_exp else None
                                for e in st.session_state.empleados:
                                    if e["Nombre"] == usuario_objetivo["Nombre"]:
                                        e["Plan"] = nuevo_plan_upgrade
                                        if fecha_exp_str: e["Expiracion"] = fecha_exp_str
                                        elif "Expiracion" in e: del e["Expiracion"]
                                guardar_datos()
                                st.success(f"✅ Plan de '{usuario_objetivo['Nombre']}' actualizado a {nuevo_plan_upgrade}.")
                                st.rerun()
                    else:
                        st.markdown("No hay usuarios registrados aún.")

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("""<div class="briefing-box" style="border-left-color: #EF4444;"><h4 style="color: #EF4444; font-size:0.6rem;">⚠ PROTOCOLO OMEGA</h4><p style="font-size:0.75rem;">Limpieza irreversible de toda la base de datos.</p></div>""", unsafe_allow_html=True)
                if st.button("☣️ FORMATEAR PLATAFORMA", use_container_width=True):
                    st.session_state.empleados = []; st.session_state.historial_sesiones = []; st.session_state.escenarios_custom = {}
                    st.session_state.usuario_actual = None; guardar_datos(); st.rerun()
            else:
                st.info("🔒 ACCESO RESTRINGIDO: El uso de Inteligencia Generativa queda registrado por motivos de auditoría.")


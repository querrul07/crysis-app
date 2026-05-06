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

# --- CONEXIÓN A SUPABASE ---
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
        st.error(f"Error de enlace con Base Central: {e}")
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
        st.error(f"Fallo critico de sincronizacion: {e}")

# --- UTILIDADES TÉCNICAS ---
def enviar_correo_2fa(destinatario, codigo):
    try:
        remitente = st.secrets["SMTP_EMAIL"]
        password = st.secrets["SMTP_PASS"]
        msg = MIMEText(f"Codigo de autorizacion CRYSIS: {codigo}")
        msg['Subject'] = 'CRYSIS | Seguridad 2FA'
        msg['From'] = "CRYSIS Security"
        msg['To'] = destinatario
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        server.send_message(msg)
        server.quit()
        return True
    except: return False

def generar_pdf_dossier(sesion):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.set_text_color(79, 142, 247)
    pdf.cell(0, 10, "CRYSIS | INTELLIGENCE UNIT", ln=True, align='C')
    def s_txt(t): return str(t).replace('**', '').encode('latin-1', 'replace').decode('latin-1')
    pdf.set_font("Arial", 'B', 10); pdf.set_text_color(0, 0, 0)
    pdf.cell(45, 8, "OPERADOR:", border=1); pdf.cell(0, 8, s_txt(sesion.get("Agente", "").upper()), border=1, ln=True)
    pdf.cell(45, 8, "NOTA:", border=1); pdf.cell(0, 8, f"{sesion.get('Nota', 0)}/100", border=1, ln=True); pdf.ln(10)
    pdf.multi_cell(0, 6, s_txt(sesion.get("Evaluacion", "")))
    return pdf.output(dest='S').encode('latin-1')

# ─────────────────────────────────────────
# 1. ESTILOS Y NAVEGACIÓN
# ─────────────────────────────────────────
st.set_page_config(page_title="CRYSIS | Tactical OS", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"], .stApp { background-color: #07090F !important; color: #C8D0E0 !important; font-family: 'DM Sans', sans-serif !important; }
header[data-testid="stHeader"] { background: #07090F !important; border-bottom: 1px solid #1A2035; }
.crysis-title { font-family: 'IBM Plex Mono', monospace; font-size: 3.2rem; font-weight: 700; letter-spacing: 0.35em; color: #E8EDF5; text-align: center; text-shadow: 0 0 40px rgba(79, 142, 247, 0.25); }
.crysis-subtitle { font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem; letter-spacing: 0.45em; color: #4F8EF7; text-align: center; margin-bottom: 28px; }
.metric-card { background: #0C1020; border: 1px solid #1A2035; border-radius: 6px; padding: 22px 24px; border-left: 3px solid #4F8EF7; }
.metric-label { font-family: 'IBM Plex Mono', monospace; font-size: 0.6rem; letter-spacing: 0.2em; color: #4F8EF7; margin-bottom: 8px; }
.metric-value { font-family: 'IBM Plex Mono', monospace; font-size: 2rem; font-weight: 700; color: #E8EDF5; }
.hub-card { background: #0C1020; border: 1px solid #1A2035; border-radius: 6px; padding: 25px; height: 100%; transition: all 0.3s ease; }
.hub-card:hover { border-color: #4F8EF7; transform: translateY(-3px); }
.hub-icon { font-size: 2.2rem; margin-bottom: 15px; color: #4F8EF7; font-family: sans-serif; }
.hub-title { font-family: 'IBM Plex Mono', monospace; font-size: 1.1rem; font-weight: 700; color: #E8EDF5; margin-bottom: 8px; }
.hub-desc { font-size: 0.85rem; color: #8B9CC8; line-height: 1.4; }
.section-label { font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; letter-spacing: 0.25em; color: #4F8EF7; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #1A2035; }
.stButton > button { background: #4F8EF7 !important; color: #07090F !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 0.7rem !important; font-weight: 700 !important; letter-spacing: 0.15em !important; border-radius: 3px !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 2. GESTIÓN DE DATOS Y SESIÓN
# ─────────────────────────────────────────
if "db_init" not in st.session_state:
    d = cargar_datos()
    st.session_state.empleados = d["empleados"]
    st.session_state.historial_sesiones = d["historial_sesiones"]
    st.session_state.escenarios_custom = d["escenarios_custom"]
    st.session_state.usuario_actual = None
    st.session_state.vista_actual = "HOME"
    st.session_state.login_step = 1
    st.session_state.db_init = True

# ─────────────────────────────────────────
# 3. ACCESO AL SISTEMA
# ─────────────────────────────────────────
if st.session_state.usuario_actual is None:
    token_inv = st.query_params.get("invite", None)
    empresa_inv = None
    if token_inv:
        try: empresa_inv = base64.urlsafe_b64decode(token_inv.encode()).decode()
        except: pass

    st.markdown("<div class='crysis-title' style='margin-top: 40px;'>CRYSIS</div>", unsafe_allow_html=True)
    
    if empresa_inv:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown(f"<div class='crysis-subtitle'>ALISTAMIENTO ACTIVO: {empresa_inv.upper()}</div>", unsafe_allow_html=True)
            with st.form("reg_corp"):
                n = st.text_input("ID Operativo")
                email = st.text_input("Email Corporativo")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("REGISTRAR ACREDITACION", use_container_width=True):
                    if n and p and email:
                        nuevo = {"Nombre": n, "Email": email, "Rol": "Agente", "Empresa": empresa_inv, "Password": p, "2FA_Verificado": True}
                        st.session_state.empleados.append(nuevo); guardar_datos()
                        st.query_params.clear(); st.success("Registro completado. Identifiquese para entrar."); st.rerun()
    else:
        st.markdown("<div class='crysis-subtitle'>TACTICAL NEGOTIATION OS</div>", unsafe_allow_html=True)
        tab_l, tab_r = st.tabs(["IDENTIFICACION", "NUEVA ALTA"])
        with tab_l:
            c1, c2, c3 = st.columns([1, 1.5, 1])
            with c2:
                with st.form("login"):
                    u_id = st.text_input("ID")
                    u_ps = st.text_input("Password", type="password")
                    if st.form_submit_button("CONECTAR"):
                        user = next((e for e in st.session_state.empleados if e["Nombre"] == u_id and e["Password"] == u_ps), None)
                        if u_id == COMANDANTE_SUPREMO and u_ps == "TU_PASS_AQUI": user = {"Nombre": COMANDANTE_SUPREMO, "Rol": "Comandante"}
                        if user: st.session_state.usuario_actual = user; st.session_state.vista_actual = "HOME"; st.rerun()
                        else: st.error("Fallo de acceso.")
        with tab_r:
            with st.form("reg_unificado"):
                plan = st.selectbox("Nivel de Acceso", ["Base (Gratis)", "Operador (Premium)", "Escuadron (Corporativo)"])
                n = st.text_input("ID / Entidad")
                email = st.text_input("Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("EMITIR CREDENCIALES"):
                    rol = "Empresa" if "Escuadron" in plan else "Individual"
                    nuevo = {"Nombre": n, "Email": email, "Rol": rol, "Empresa": n, "Password": p, "Plan": "Gratis", "2FA_Verificado": True}
                    st.session_state.empleados.append(nuevo); guardar_datos()
                    st.session_state.usuario_actual = nuevo; st.session_state.vista_actual = "HOME"; st.rerun()
    st.stop()

# ─────────────────────────────────────────
# 4. LOGICA DE PERMISOS
# ─────────────────────────────────────────
u = st.session_state.usuario_actual
es_adm = u["Nombre"] == COMANDANTE_SUPREMO
es_emp = u.get("Rol") == "Empresa"
empresa_actual = u.get("Empresa", u["Nombre"])

if es_adm: mi_plan = "Enterprise"
elif u.get("Rol") == "Agente":
    e_obj = next((e for e in st.session_state.empleados if e["Nombre"] == empresa_actual), {"Plan": "Gratis"})
    mi_plan = e_obj.get("Plan", "Gratis")
else: mi_plan = u.get("Plan", "Gratis")

# Filtros de historial y misiones
if es_adm:
    historial = st.session_state.historial_sesiones
    agentes_lista = [e["Nombre"] for e in st.session_state.empleados]
elif es_emp:
    agentes_lista = [e["Nombre"] for e in st.session_state.empleados if e.get("Empresa") == empresa_actual]
    historial = [s for s in st.session_state.historial_sesiones if s["Agente"] in agentes_lista and s.get("Tipo_Mision") != "Personal"]
else:
    agentes_lista = [u["Nombre"]]
    historial = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]

mis_escenarios = {k: v for k, v in st.session_state.escenarios_custom.items() if v.get("Creador") == empresa_actual or es_adm}
TODAS_LAS_MISIONES = {**CONTEXTOS_MISION, **mis_escenarios}

# --- HEADER SUPERIOR ---
c_h1, c_h2, c_h3 = st.columns([7, 1.5, 1.5])
with c_h1:
    st.markdown(f"<div class='crysis-title' style='text-align:left; font-size:1.8rem;'>CRYSIS <span style='font-size:0.8rem; color:#4F8EF7; letter-spacing:0.2em;'>| {u['Nombre'].upper()}</span></div>", unsafe_allow_html=True)
with c_h2:
    if st.session_state.vista_actual != "HOME" and st.button("MENU INICIO", use_container_width=True):
        st.session_state.vista_actual = "HOME"; st.rerun()
with c_h3:
    if st.button("DESCONECTAR", type="secondary", use_container_width=True):
        st.session_state.usuario_actual = None; st.rerun()
st.markdown("<hr style='border:none; border-top:1px solid #1A2035; margin-top:0; margin-bottom:30px;'>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 5. ENRUTADOR DE VISTAS (HUB)
# ─────────────────────────────────────────

if st.session_state.vista_actual == "HOME":
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='hub-card'><div class='hub-icon'>⬢</div><div class='hub-title'>DESPLIEGUE</div><div class='hub-desc'>Simulador tactico de negociacion en tiempo real.</div></div>", unsafe_allow_html=True)
        if st.button("ABRIR TERMINAL", key="h_sim", use_container_width=True): st.session_state.vista_actual = "SIM"; st.rerun()
    with col2:
        st.markdown("<div class='hub-card'><div class='hub-icon'>▤</div><div class='hub-title'>RADAR</div><div class='hub-desc'>Analisis de rendimiento y metricas de exito.</div></div>", unsafe_allow_html=True)
        if st.button("VER METRICAS", key="h_rad", use_container_width=True): st.session_state.vista_actual = "RADAR"; st.rerun()
    with col3:
        st.markdown("<div class='hub-card'><div class='hub-icon'>≡</div><div class='hub-title'>ARCHIVO</div><div class='hub-desc'>Historial de misiones y descarga de expedientes.</div></div>", unsafe_allow_html=True)
        if st.button("ABRIR REGISTROS", key="h_arc", use_container_width=True): st.session_state.vista_actual = "ARCH"; st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown("<div class='hub-card'><div class='hub-icon'>⌬</div><div class='hub-title'>SINTESIS IA</div><div class='hub-desc'>Creacion de protocolos y escenarios personalizados.</div></div>", unsafe_allow_html=True)
        if st.button("CREAR MISION", key="h_sin", use_container_width=True): st.session_state.vista_actual = "SINT"; st.rerun()
    with col5:
        st.markdown("<div class='hub-card'><div class='hub-icon'>⎈</div><div class='hub-title'>AJUSTES</div><div class='hub-desc'>Gestion de seguridad, clave y licencias.</div></div>", unsafe_allow_html=True)
        if st.button("CONFIGURACION", key="h_conf", use_container_width=True): st.session_state.vista_actual = "CONF"; st.rerun()
    with col6:
        if es_emp or es_adm:
            st.markdown("<div class='hub-card'><div class='hub-icon'>◩</div><div class='hub-title'>ESCUADRON</div><div class='hub-desc'>Control de agentes y reclutamiento de unidad.</div></div>", unsafe_allow_html=True)
            if st.button("PANEL MANDO", key="h_esc", use_container_width=True): st.session_state.vista_actual = "ESCU"; st.rerun()

    if es_adm:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div class='hub-card' style='border-color:#F59E0B;'><div class='hub-icon' style='color:#F59E0B;'>Ω</div><div class='hub-title' style='color:#F59E0B;'>CONSOLA OMEGA</div><div class='hub-desc'>Administracion global de la infraestructura SaaS.</div></div>", unsafe_allow_html=True)
        if st.button("ACCESO RAIZ", key="h_adm", use_container_width=True): st.session_state.vista_actual = "OMEGA"; st.rerun()

# --- VISTA: SIMULADOR ---
elif st.session_state.vista_actual == "SIM":
    if not st.session_state.mision_iniciada:
        c1, c2 = st.columns(2)
        ag_sel = c1.selectbox("Asignar Operador", agentes_lista)
        es_sel = c2.selectbox("Protocolo", list(TODAS_LAS_MISIONES.keys()))
        if u.get("Rol") == "Agente":
            m = st.radio("Privacidad", ["Oficial (Empresa)", "Personal (Privado)"], horizontal=True)
            t_m = "Corporativa" if "Oficial" in m else "Personal"
        else: t_m = "Personal"
        
        if st.button("INICIAR ENLACE"):
            st.session_state.mision_iniciada = True
            st.session_state.ag_activo = ag_sel; st.session_state.es_activo = es_sel; st.session_state.t_m_act = t_m; st.session_state.mensajes = []
            st.rerun()
    else:
        for msg in st.session_state.mensajes:
            with st.chat_message(msg["role"]): st.write(msg["content"])
        if p := st.chat_input("Directiva..."):
            st.session_state.mensajes.append({"role": "user", "content": p})
            client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":TODAS_LAS_MISIONES[st.session_state.es_activo]["prompt"]}] + st.session_state.mensajes).choices[0].message.content
            st.session_state.mensajes.append({"role": "assistant", "content": res}); st.rerun()
        if st.button("TERMINAR Y EVALUAR"):
            # Lógica de evaluación simplificada para el ejemplo
            st.session_state.historial_sesiones.append({"Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "Agente": st.session_state.ag_activo, "Escenario": st.session_state.es_activo, "Nota": 85, "Evaluacion": "Analisis completado.", "Transcripcion": st.session_state.mensajes, "Tipo_Mision": st.session_state.t_m_act})
            guardar_datos(); st.session_state.mision_iniciada = False; st.session_state.vista_actual = "ARCH"; st.rerun()

# --- VISTA: ARCHIVO ---
elif st.session_state.vista_actual == "ARCH":
    st.markdown("<div class='section-label'>REGISTROS OPERACIONALES</div>", unsafe_allow_html=True)
    for i, s in enumerate(reversed(historial)):
        with st.expander(f"{s['Fecha']} | {s['Agente']} | {s['Escenario']}"):
            st.write(s["Evaluacion"])
            c1, c2 = st.columns(2)
            c1.download_button("DESCARGAR PDF", generar_pdf_dossier(s), file_name="report.pdf", key=f"pdf_{i}")
            if u["Nombre"] == s["Agente"] or es_adm:
                if c2.button("ELIMINAR REGISTRO", key=f"del_h_{i}"):
                    st.session_state.historial_sesiones = [h for h in st.session_state.historial_sesiones if h != s]
                    guardar_datos(); st.rerun()

# --- VISTA: SÍNTESIS IA (CORREGIDA) ---
elif st.session_state.vista_actual == "SINT":
    st.markdown("<div class='section-label'>CREADOR DE PROTOCOLOS</div>", unsafe_allow_html=True)
    creados = len(mis_escenarios)
    
    if mi_plan == "Gratis" and not es_adm:
        st.error("Licencia insuficiente para generacion IA.")
    else:
        idea = st.text_area("Describa la situacion de crisis:")
        if st.button("GENERAR SIMULACION"):
            if idea and GROQ_API_KEY:
                with st.spinner("Sintetizando..."):
                    client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                    res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":"JSON: {'nombre_op':'','contexto':'','perfil_sujeto':'','objetivo':'','prompt':''}"},{"role":"user","content":idea}], response_format={"type":"json_object"}).choices[0].message.content
                    nuevo = json.loads(res); nuevo["Creador"] = empresa_actual
                    st.session_state.escenarios_custom[nuevo["nombre_op"]] = nuevo
                    guardar_datos(); st.success("Protocolo guardado."); st.rerun()
        
        st.markdown("---")
        for k, v in list(st.session_state.escenarios_custom.items()):
            if v.get("Creador") == empresa_actual or es_adm:
                c1, c2 = st.columns([4,1])
                c1.write(f"Mision: {k}")
                if c2.button("BORRAR", key=f"del_esc_{k}"):
                    del st.session_state.escenarios_custom[k]; guardar_datos(); st.rerun()

# --- VISTA: OMEGA (CORREGIDA ID DUPLICADOS) ---
elif st.session_state.vista_actual == "OMEGA" and es_adm:
    st.markdown("<div class='section-label'>CONTROL DE INSTANCIAS</div>", unsafe_allow_html=True)
    for idx, usr in enumerate(st.session_state.empleados):
        if usr["Nombre"] != COMANDANTE_SUPREMO:
            c1, c2 = st.columns([4, 1])
            c1.write(f"ID: {usr['Nombre']} | Rol: {usr['Rol']} | Plan: {usr.get('Plan','Base')}")
            if c2.button("PURGAR", key=f"purgar_{usr['Nombre']}_{idx}"):
                st.session_state.empleados = [e for e in st.session_state.empleados if e["Nombre"] != usr["Nombre"]]
                guardar_datos(); st.rerun()

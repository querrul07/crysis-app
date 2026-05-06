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
# 👑 CONFIGURACIÓN CORE
# ─────────────────────────────────────────
st.set_page_config(page_title="CRYSIS | Tactical OS", layout="wide", initial_sidebar_state="collapsed")

COMANDANTE_SUPREMO = "CRYSIS" # <--- TU ID
LINKS_PAGO = {
    "Enterprise": "https://crysisanalitics.lemonsqueezy.com/checkout/buy/d864d72e-5ff1-4bac-966d-eafc555c5bd2",
    "Pro": "https://crysisanalitics.lemonsqueezy.com/checkout/buy/1dba647d-e120-4816-9ea0-a25492650825",
    "Individual": "https://crysisanalitics.lemonsqueezy.com/checkout/buy/adfd50b4-b2e5-40fb-9ece-30717f8828ba"
}

# --- ESTILOS CSS ORGÁNICOS Y MODERNOS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');
html, body, [class*="css"], .stApp { background-color: #070A0F !important; color: #D1D5DB !important; font-family: 'Inter', sans-serif !important; }
.stButton > button { background-color: #2563EB !important; color: white !important; font-weight: 600 !important; border: none !important; border-radius: 8px !important; padding: 10px 24px !important; transition: all 0.3s ease; }
.stButton > button:hover { background-color: #1D4ED8 !important; transform: translateY(-2px); box-shadow: 0 8px 16px rgba(37, 99, 235, 0.3); }
button[title="View fullscreen"] { display: none; }
.module-card { background: #111827; border: 1px solid #1F2937; border-radius: 12px; padding: 24px; transition: all 0.3s ease; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
.module-card:hover { border-color: #3B82F6; box-shadow: 0 10px 20px rgba(0,0,0,0.4); transform: translateY(-3px); }
.module-icon { font-size: 2.5rem; margin-bottom: 15px; }
.module-title { font-family: 'IBM Plex Mono', monospace; font-size: 1.1rem; font-weight: 700; color: #F3F4F6; margin-bottom: 10px; letter-spacing: 0.05em; }
.module-desc { font-size: 0.85rem; color: #9CA3AF; margin-bottom: 20px; line-height: 1.5; flex-grow: 1; }
.title-font { font-family: 'IBM Plex Mono', monospace; font-weight: 700; letter-spacing: 0.1em; color: #60A5FA; }
.metric-card { background: #1F2937; border-radius: 8px; padding: 20px; border-left: 4px solid #3B82F6; }
.metric-value { font-size: 2rem; font-family: 'IBM Plex Mono'; font-weight: bold; color: white; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 2. CONEXIÓN A BASE DE DATOS Y UTILIDADES
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
            d = response.data[0]["memoria"]
            if "escenarios_custom" not in d: d["escenarios_custom"] = {}
            d["empleados"] = [e for e in d.get("empleados", []) if "Rol" in e]
            return d
    except Exception as e: st.error("⚠️ Error BD")
    return {"empleados": [], "historial_sesiones": [], "escenarios_custom": {}}

def guardar_datos():
    try:
        datos = {"empleados": st.session_state.empleados, "historial_sesiones": st.session_state.historial_sesiones, "escenarios_custom": st.session_state.escenarios_custom}
        supabase.table("crysis_data").update({"memoria": datos}).eq("id", "main").execute()
    except Exception as e: st.error("⚠️ Error al guardar.")

def generar_pdf_dossier(sesion):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "CRYSIS DOSSIER", ln=True, align='C'); pdf.ln(10)
    def s_txt(t): return str(t).replace('**', '').encode('latin-1', 'replace').decode('latin-1')
    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 8, f"AGENTE: {s_txt(sesion.get('Agente', ''))}", ln=True)
    pdf.cell(0, 8, f"NOTA: {sesion.get('Nota', 0)}/100", ln=True); pdf.ln(5)
    pdf.multi_cell(0, 6, s_txt(sesion.get("Evaluacion", ""))); return pdf.output(dest='S').encode('latin-1')

# ─────────────────────────────────────────
# 3. DATOS TÁCTICOS Y ESTADO
# ─────────────────────────────────────────
INSTRUCCION_ORTOGRAFIA = " Escribe en español correcto. Solo diálogo, sin acotaciones."
CONTEXTOS_MISION = {
    "OP: FRONTERA": {"contexto": "Tensión militar.", "perfil_sujeto": "Ministro Volkov.", "objetivo": "Evitar guerra.", "prompt": "Eres el Ministro Volkov. Hostil." + INSTRUCCION_ORTOGRAFIA},
    "OP: EXTRACCION": {"contexto": "Secuestro banco.", "perfil_sujeto": "Captor inestable.", "objetivo": "Liberar rehenes.", "prompt": "Eres secuestrador nervioso." + INSTRUCCION_ORTOGRAFIA}
}

try: GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except: GROQ_API_KEY = None

if "db_cargada" not in st.session_state:
    d = cargar_datos(); st.session_state.empleados = d["empleados"]; st.session_state.historial_sesiones = d["historial_sesiones"]; st.session_state.escenarios_custom = d["escenarios_custom"]; st.session_state.db_cargada = True
    st.session_state.usuario_actual = None; st.session_state.mision_iniciada = False; st.session_state.mensajes = []
    st.session_state.vista_actual = "HOME" # <--- NUEVO SISTEMA DE NAVEGACIÓN

# ─────────────────────────────────────────
# 4. MÓDULO DE ACCESO (LOGIN / REGISTRO ORGÁNICO)
# ─────────────────────────────────────────
if st.session_state.usuario_actual is None:
    token_inv = st.query_params.get("invite", None)
    if token_inv:
        try:
            empresa_inv = base64.urlsafe_b64decode(token_inv.encode()).decode()
            empresa_obj = next((e for e in st.session_state.empleados if e["Rol"] == "Empresa" and e["Nombre"] == empresa_inv), None)
            if empresa_obj:
                st.markdown(f"<br><br><h1 class='title-font' style='text-align: center;'>CRYSIS</h1>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='text-align: center; color: #34D399;'>INVITACIÓN DE ESCUADRÓN: {empresa_inv.upper()}</h3>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns([1,2,1])
                with c2:
                    with st.form("reg_empleado"):
                        st.info("Únete a la unidad operativa de tu empresa. Tus misiones oficiales serán evaluadas por tus superiores.")
                        n = st.text_input("Identificador Operativo (ID)")
                        email = st.text_input("Correo Profesional")
                        p = st.text_input("Contraseña de Acceso", type="password")
                        if st.form_submit_button("UNIRSE AL ESCUADRÓN", use_container_width=True):
                            if n and email and p:
                                if any(e["Nombre"] == n for e in st.session_state.empleados): st.warning("Ese ID ya existe. Por favor, elige otro.")
                                else:
                                    st.session_state.empleados.append({"Nombre": n, "Email": email, "Rol": "Agente", "Empresa": empresa_inv, "Password": p, "Plan_Privado": "Gratis"})
                                    guardar_datos(); st.query_params.clear(); st.success("¡Acreditación lista! Por favor, inicia sesión."); st.rerun()
                st.stop()
        except: pass

    # --- PANTALLA PRINCIPAL DE LOGIN ---
    st.markdown("<br><br><h1 class='title-font' style='text-align: center; font-size: 4.5rem;'>CRYSIS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #9CA3AF; margin-bottom: 40px; font-size: 1.2rem; letter-spacing: 0.2em;'>SISTEMA OPERATIVO TÁCTICO</p>", unsafe_allow_html=True)

    c_izq, c_cen, c_der = st.columns([1, 1.5, 1])
    with c_cen:
        tab_log, tab_reg = st.tabs(["🔑 INICIAR SESIÓN", "🛡️ NUEVA CUENTA"])
        
        with tab_log:
            with st.container():
                st.markdown("<br>", unsafe_allow_html=True)
                u_id = st.text_input("ID Operativo", placeholder="Introduce tu nombre en clave")
                u_pass = st.text_input("Contraseña", type="password", placeholder="••••••••")
                if st.button("ACCEDER AL SISTEMA", use_container_width=True):
                    usuario = next((e for e in st.session_state.empleados if e["Nombre"] == u_id and e.get("Password") == u_pass), None)
                    if usuario: 
                        st.session_state.usuario_actual = usuario; st.session_state.vista_actual = "HOME"; st.rerun()
                    else: st.error("❌ Identificación rechazada. Verifica tus credenciales.")

        with tab_reg:
            st.markdown("<br>", unsafe_allow_html=True)
            tipo_cuenta = st.radio("Selecciona tu perfil de uso:", ["👤 Operador Individual", "🏢 Organización / Empresa"], horizontal=True)
            
            n = st.text_input("Identificador (Tu alias o el nombre de tu Empresa)")
            email = st.text_input("Correo Electrónico")
            p = st.text_input("Contraseña", type="password")
            
            if "Individual" in tipo_cuenta:
                plan_sel = st.selectbox("Plan de Operador", ["Nivel BASE (Gratis)", "Nivel OPERADOR Premium (29€/mes)"])
                rol_asignado = "Individual"
            else:
                plan_sel = st.selectbox("Plan Corporativo", ["Nivel ESCUADRÓN (89€/mes - 15 Agentes)", "Nivel COMANDANCIA (199€/mes - Ilimitado)"])
                rol_asignado = "Empresa"
            
            if st.button("SOLICITAR ACREDITACIÓN", use_container_width=True):
                if n and email and p:
                    if any(e["Nombre"] == n for e in st.session_state.empleados): st.warning("⚠️ Este Identificador ya está en uso.")
                    else:
                        nuevo_usuario = {"Nombre": n, "Email": email, "Rol": rol_asignado, "Plan": "Gratis", "Empresa": n, "Password": p}
                        st.session_state.empleados.append(nuevo_usuario); guardar_datos()
                        
                        es_pago = "Gratis" not in plan_sel
                        if es_pago:
                            link_pago = LINKS_PAGO["Pro"] if "ESCUADRÓN" in plan_sel else (LINKS_PAGO["Enterprise"] if "COMANDANCIA" in plan_sel else LINKS_PAGO["Individual"])
                            st.session_state.mostrar_pago = {"id": n, "link": link_pago, "usuario": nuevo_usuario}
                            st.rerun()
                        else:
                            st.session_state.usuario_actual = nuevo_usuario; st.session_state.vista_actual = "HOME"; st.rerun()
                else: st.warning("Rellena todos los campos para continuar.")

        if st.session_state.get("mostrar_pago"):
            info = st.session_state.mostrar_pago
            st.success("✅ Cuenta BASE creada. Completa el pago para activar tu suscripción Premium.")
            st.markdown(f'<a href="{info["link"]}" target="_blank"><button style="width:100%; background:#F59E0B; color:black; padding:12px; border:none; border-radius:6px; font-weight:bold; cursor:pointer;">💳 PROCEDER AL PAGO SEGURO</button></a>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Continuar con Nivel Base por ahora", use_container_width=True):
                st.session_state.usuario_actual = info["usuario"]; st.session_state.vista_actual = "HOME"; del st.session_state.mostrar_pago; st.rerun()

    st.stop() # Bloquea la app si no hay sesión

# ─────────────────────────────────────────
# 5. RESOLUCIÓN DE PERMISOS
# ─────────────────────────────────────────
u = st.session_state.usuario_actual
es_adm = (u["Nombre"] == COMANDANTE_SUPREMO)
es_empresa = (u.get("Rol") == "Empresa")
empresa_actual = u.get("Empresa", u["Nombre"])

if es_adm: mi_plan = "Enterprise"
elif u.get("Rol") == "Agente":
    e_obj = next((e for e in st.session_state.empleados if e["Nombre"] == empresa_actual and e["Rol"] == "Empresa"), None)
    mi_plan = e_obj.get("Plan", "Gratis") if e_obj else "Gratis"
else: mi_plan = u.get("Plan", "Gratis")

if es_adm:
    historial = st.session_state.historial_sesiones
    agentes_scope = [u["Nombre"]]
elif es_empresa:
    agentes_scope = [e["Nombre"] for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"]
    historial = [s for s in st.session_state.historial_sesiones if s["Agente"] in agentes_scope and s.get("Tipo_Mision") != "Personal"]
else:
    historial = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]
    agentes_scope = [u["Nombre"]]

mis_escenarios = {k: v for k, v in st.session_state.escenarios_custom.items() if v.get("Creador") == empresa_actual or v.get("Creador") == u["Nombre"] or es_adm}
TODAS_LAS_MISIONES = {**CONTEXTOS_MISION, **mis_escenarios}

# ─────────────────────────────────────────
# 6. HEADER COMÚN DE NAVEGACIÓN
# ─────────────────────────────────────────
c_logo, c_btn = st.columns([6, 1])
with c_logo:
    rol_tag = f"[{mi_plan.upper()}]" if u["Rol"] != "Agente" else f"[{empresa_actual.upper()}]"
    if es_adm: rol_tag = "[GOD MODE]"
    st.markdown(f"<span class='title-font' style='font-size:1.8rem;'>CRYSIS</span> <span style='color:#9CA3AF; margin-left:15px;'>AGENTE: {u['Nombre']} {rol_tag}</span>", unsafe_allow_html=True)
with c_btn:
    if st.session_state.vista_actual != "HOME":
        if st.button("🏠 Inicio", use_container_width=True): st.session_state.vista_actual = "HOME"; st.rerun()
    else:
        if st.button("🚪 Salir", use_container_width=True): st.session_state.usuario_actual = None; st.session_state.vista_actual = "HOME"; st.rerun()
st.markdown("<hr style='border-color:#374151; margin-top:5px; margin-bottom:25px;'>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 7. ENRUTADOR DE VISTAS (PANTALLAS)
# ─────────────────────────────────────────

# ==================================
# VISTA: HUB PRINCIPAL (MENÚ)
# ==================================
if st.session_state.vista_actual == "HOME":
    st.markdown(f"<h2>Centro de Operaciones</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#9CA3AF;'>Selecciona un módulo para comenzar.</p><br>", unsafe_allow_html=True)
    
    # FILA 1 DE TARJETAS
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""<div class='module-card'><div class='module-icon'>⚔️</div><div class='module-title'>DESPLIEGUE TÁCTICO</div><div class='module-desc'>Inicia el simulador de IA para practicar negociaciones críticas en tiempo real.</div></div>""", unsafe_allow_html=True)
        if st.button("Abrir Simulador →", key="btn_sim", use_container_width=True): st.session_state.vista_actual = "SIMULADOR"; st.rerun()
    with col2:
        st.markdown("""<div class='module-card'><div class='module-icon'>📊</div><div class='module-title'>RADAR ESTRATÉGICO</div><div class='module-desc'>Visualiza tus métricas de rendimiento, tasas de éxito y análisis de progreso.</div></div>""", unsafe_allow_html=True)
        if st.button("Ver Estadísticas →", key="btn_rad", use_container_width=True): st.session_state.vista_actual = "RADAR"; st.rerun()
    with col3:
        st.markdown("""<div class='module-card'><div class='module-icon'>🗂️</div><div class='module-title'>ARCHIVO DE EXPEDIENTES</div><div class='module-desc'>Consulta el historial de misiones pasadas y descarga los dossier en PDF.</div></div>""", unsafe_allow_html=True)
        if st.button("Abrir Archivo →", key="btn_hist", use_container_width=True): st.session_state.vista_actual = "HISTORIAL"; st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # FILA 2 DE TARJETAS
    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown("""<div class='module-card'><div class='module-icon'>🧠</div><div class='module-title'>SÍNTESIS IA</div><div class='module-desc'>Genera tus propios protocolos de crisis usando el motor generativo avanzado.</div></div>""", unsafe_allow_html=True)
        if st.button("Ir al Creador →", key="btn_ia", use_container_width=True): st.session_state.vista_actual = "SINTESIS"; st.rerun()
    with col5:
        if es_empresa or es_adm:
            st.markdown("""<div class='module-card'><div class='module-icon'>👥</div><div class='module-title'>ESCUADRÓN</div><div class='module-desc'>Gestiona tu equipo de agentes, invitaciones y supervisión de unidad.</div></div>""", unsafe_allow_html=True)
            if st.button("Gestionar Unidad →", key="btn_esc", use_container_width=True): st.session_state.vista_actual = "ESCUADRON"; st.rerun()
        else:
            st.markdown("""<div class='module-card' style='opacity: 0.5;'><div class='module-icon'>👥</div><div class='module-title'>ESCUADRÓN</div><div class='module-desc'>Función reservada para cuentas corporativas.</div></div>""", unsafe_allow_html=True)
            st.button("Acceso Bloqueado", key="btn_esc_lock", disabled=True, use_container_width=True)
    with col6:
        st.markdown("""<div class='module-card'><div class='module-icon'>⚙️</div><div class='module-title'>AJUSTES DE SISTEMA</div><div class='module-desc'>Gestiona tu contraseña, licencias y parámetros de seguridad.</div></div>""", unsafe_allow_html=True)
        if st.button("Configuración →", key="btn_conf", use_container_width=True): st.session_state.vista_actual = "CONFIGURACION"; st.rerun()

    # ADMIN PANEL OPCIONAL
    if es_adm:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""<div class='module-card' style='border-color:#F59E0B;'><div class='module-title' style='color:#F59E0B;'>👑 CONSOLA OMEGA (SUPERADMIN)</div><div class='module-desc'>Control total del SaaS, usuarios, planes y formateo de base de datos.</div></div>""", unsafe_allow_html=True)
        if st.button("Acceso Administrativo →", key="btn_admin", use_container_width=True): st.session_state.vista_actual = "ADMIN"; st.rerun()

# ==================================
# VISTA: SIMULADOR (DESPLIEGUE)
# ==================================
elif st.session_state.vista_actual == "SIMULADOR":
    st.markdown("## ⚔️ DESPLIEGUE TÁCTICO")
    if not st.session_state.mision_iniciada:
        colA, colB = st.columns(2)
        agente_asignado = colA.selectbox("Operador Asignado", agentes_scope) if es_empresa else colA.text_input("Operador", value=u["Nombre"], disabled=True)
        if es_empresa and not agente_asignado: agente_asignado = u["Nombre"]
        escenario_sel = colB.selectbox("Protocolo de Operación", list(TODAS_LAS_MISIONES.keys()))
        
        tipo_mision = "Corporativa"
        if u.get("Rol") == "Agente":
            modo = st.radio("Privacidad de la Sesión:", ["🛡️ Misión Oficial (Auditable por la empresa)", "👻 Entrenamiento Privado (Oculto al mando)"], horizontal=True)
            tipo_mision = "Oficial" if "Oficial" in modo else "Personal"
        
        st.info(f"**OBJETIVO:** {TODAS_LAS_MISIONES[escenario_sel]['objetivo']}")
        
        if st.button("🚀 INICIAR ENLACE TÁCTICO", type="primary"):
            st.session_state.mision_iniciada = True
            st.session_state.es_activo = escenario_sel; st.session_state.ag_activo = agente_asignado; st.session_state.tipo_mision = tipo_mision
            st.session_state.mensajes = [{"role": "assistant", "content": f"Enlace establecido. El sujeto ({TODAS_LAS_MISIONES[escenario_sel]['perfil_sujeto']}) está a la espera."}]
            st.rerun()
    else:
        st.markdown(f"<span style='color:#34D399; font-weight:bold;'>◉ ENLACE ACTIVO:</span> {st.session_state.es_activo} | **OPERADOR:** {st.session_state.ag_activo}", unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#374151;'>", unsafe_allow_html=True)
        
        for msg in st.session_state.mensajes:
            if msg["role"] != "system": 
                with st.chat_message(msg["role"]): st.write(msg["content"])
        
        if prompt := st.chat_input("Escribe tu directiva aquí..."):
            st.session_state.mensajes.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.write(prompt)
            with st.spinner("Sujeto escribiendo..."):
                client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                sys_prompt = TODAS_LAS_MISIONES[st.session_state.es_activo]["prompt"]
                api_messages = [{"role": "system", "content": sys_prompt}] + [m for m in st.session_state.mensajes if m["role"] != "assistant" or m["content"].startswith("Enlace") == False]
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=api_messages).choices[0].message.content
                st.session_state.mensajes.append({"role": "assistant", "content": res})
            st.rerun()

        colC, colD = st.columns([1,3])
        if colC.button("🛑 CERRAR ENLACE (ABORTAR)", type="secondary", use_container_width=True):
            st.session_state.mision_iniciada = False; st.rerun()
        if len(st.session_state.mensajes) > 2:
            if colD.button("✅ FINALIZAR Y SOLICITAR EVALUACIÓN", type="primary", use_container_width=True):
                with st.spinner("Inteligencia analizando tácticas..."):
                    client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                    hist_txt = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.mensajes])
                    eval_prompt = f"Evalúa esta negociación del 0 al 100 de forma estricta. Historial:\n{hist_txt}\nEstructura: \n**ANÁLISIS**\n**ERRORES**\n**PUNTUACIÓN FINAL: XX/100**"
                    inf = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": eval_prompt}]).choices[0].message.content
                    try: nota = int(re.search(r'(\d+)\s*/\s*100', inf).group(1))
                    except: nota = 50
                    st.session_state.historial_sesiones.append({"Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "Agente": st.session_state.ag_activo, "Escenario": st.session_state.es_activo, "Nota": nota, "Evaluacion": inf, "Tipo_Mision": st.session_state.tipo_mision, "Transcripcion": st.session_state.mensajes})
                    guardar_datos(); st.session_state.mision_iniciada = False; st.session_state.vista_actual = "HISTORIAL"; st.rerun()

# ==================================
# VISTA: RADAR (ESTADÍSTICAS)
# ==================================
elif st.session_state.vista_actual == "RADAR":
    st.markdown("## 📊 RADAR DE RENDIMIENTO")
    ops_total = len(historial)
    avg_nota = int(sum(s["Nota"] for s in historial)/ops_total) if ops_total > 0 else 0
    ops_exito = sum(1 for s in historial if s["Nota"] >= 80)
    
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='metric-card'><div class='metric-title'>MISIONES COMPLETADAS</div><div class='metric-value'>{ops_total}</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='metric-card'><div class='metric-title'>CALIFICACIÓN MEDIA</div><div class='metric-value' style='color:{'#34D399' if avg_nota>=70 else '#F87171'}'>{avg_nota}%</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='metric-card'><div class='metric-title'>OPERACIONES EXCELENTES</div><div class='metric-value'>{ops_exito}</div></div>", unsafe_allow_html=True)

# ==================================
# VISTA: HISTORIAL (EXPEDIENTES)
# ==================================
elif st.session_state.vista_actual == "HISTORIAL":
    st.markdown("## 🗂️ ARCHIVO DE EXPEDIENTES")
    if not historial: st.info("Directorio vacío. No hay registros operacionales.")
    for s in reversed(historial):
        badge = "👻 PRIVADA" if s.get("Tipo_Mision") == "Personal" else "🛡️ OFICIAL"
        color = "#34D399" if s['Nota']>=80 else ("#FBBF24" if s['Nota']>=50 else "#F87171")
        with st.expander(f"{s['Fecha']} | Operador: {s['Agente']} | {s['Escenario'].replace('OP: ','')} | Nota: {s['Nota']}% {badge}"):
            st.markdown(f"<h3 style='color:{color};'>EVALUACIÓN: {s['Nota']}/100</h3>", unsafe_allow_html=True)
            st.markdown(s["Evaluacion"])
            st.download_button("📄 Extraer Dossier PDF", generar_pdf_dossier(s), file_name=f"Dossier_{s['Agente']}.pdf")

# ==================================
# VISTA: SÍNTESIS IA
# ==================================
elif st.session_state.vista_actual == "SINTESIS":
    st.markdown("## 🧠 SÍNTESIS DE ESCENARIOS IA")
    if u.get("Rol") == "Agente" and u.get("Plan_Privado") != "Individual":
        st.warning("🔒 Esta función requiere la licencia 'Operador Premium'. Actualiza tu cuenta en 'Configuración'.")
    else:
        idea = st.text_area("Describa la situación táctica, perfil del hostil y objetivo:", height=100)
        if st.button("✨ GENERAR PROTOCOLO"):
            with st.spinner("Forjando escenario..."):
                client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": f"Crea JSON: {{'nombre_op': 'OP: [Nombre]', 'contexto': '', 'perfil_sujeto': '', 'objetivo': '', 'prompt': ''}} basado en: {idea}"}], response_format={"type": "json_object"}).choices[0].message.content
                nuevo = json.loads(res); nuevo["Creador"] = u["Nombre"]
                st.session_state.escenarios_custom[nuevo["nombre_op"]] = nuevo
                guardar_datos(); st.success("Escenario creado."); st.rerun()
        
        st.markdown("### Tus Escenarios Personalizados")
        for k, v in list(st.session_state.escenarios_custom.items()):
            if v.get("Creador") == u["Nombre"] or es_adm:
                c1, c2 = st.columns([4,1])
                c1.write(f"**{k}** - {v['objetivo']}")
                if c2.button("Borrar", key=f"del_{k}"): del st.session_state.escenarios_custom[k]; guardar_datos(); st.rerun()

# ==================================
# VISTA: ESCUADRÓN (Solo Empresa)
# ==================================
elif st.session_state.vista_actual == "ESCUADRON":
    st.markdown("## 👥 GESTIÓN DE ESCUADRÓN")
    if mi_plan in ["Pro", "Enterprise"] or es_adm:
        token_c = base64.urlsafe_b64encode(empresa_actual.encode()).decode()
        st.info("Copia este enlace y envíalo a tus empleados para que se unan a tu escuadrón.")
        st.code(f"https://crysis.streamlit.app/?invite={token_c}", language="html")
        st.markdown("### Agentes Activos")
        agentes = [e for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e["Rol"] == "Agente"]
        for ag in agentes: st.markdown(f"- **{ag['Nombre']}** ({ag['Email']})")
    else:
        st.warning("🔒 Tu plan actual (BASE) no permite reclutar. Actualiza en 'Configuración'.")

# ==================================
# VISTA: CONFIGURACIÓN
# ==================================
elif st.session_state.vista_actual == "CONFIGURACION":
    st.markdown("## ⚙️ CONFIGURACIÓN DE CUENTA")
    st.markdown("#### Seguridad")
    nueva_pass = st.text_input("Nueva Contraseña", type="password")
    if st.button("Actualizar Contraseña"):
        for e in st.session_state.empleados:
            if e["Nombre"] == u["Nombre"]: e["Password"] = nueva_pass
        st.session_state.usuario_actual["Password"] = nueva_pass
        guardar_datos(); st.success("Actualizada.")
    
    st.markdown("---")
    st.markdown("#### Licencia y Suscripción")
    if u.get("Rol") == "Agente":
        st.info("💡 Tu corporación cubre tus misiones oficiales. Puedes comprar tu licencia 'Operador Premium' para hacer misiones privadas ilimitadas y usar la IA.")
        if u.get("Plan_Privado") != "Individual":
            st.markdown(f'<a href="{LINKS_PAGO["Individual"]}" target="_blank"><button style="background:#F59E0B; padding:10px; border-radius:5px; font-weight:bold; color:black; width:100%; border:none; cursor:pointer;">💳 COMPRAR PLAN PREMIUM (29€/mes)</button></a>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Ya he pagado, verificar estado", use_container_width=True):
                for e in st.session_state.empleados:
                    if e["Nombre"] == u["Nombre"]: e["Plan_Privado"] = "Individual"
                st.session_state.usuario_actual["Plan_Privado"] = "Individual"
                guardar_datos(); st.success("Plan Privado Activado."); st.rerun()
        else: st.success("✅ Tienes activo el Plan Premium Personal.")
    elif u.get("Rol") in ["Individual", "Empresa"] and not es_adm:
        st.write(f"Tu plan actual es: **{mi_plan}**")
        st.markdown(f'<a href="{LINKS_PAGO["Pro"] if u["Rol"]=="Empresa" else LINKS_PAGO["Individual"]}" target="_blank"><button style="background:#2563EB; padding:10px; border-radius:5px; color:white; width:100%; border:none; cursor:pointer;">💳 MEJORAR PLAN EN LEMON SQUEEZY</button></a>', unsafe_allow_html=True)

# ==================================
# VISTA: OMEGA (ADMIN)
# ==================================
elif st.session_state.vista_actual == "ADMIN" and es_adm:
    st.markdown("## 👑 CONSOLA DE ADMINISTRACIÓN GLOBAL")
    st.write(f"Total Usuarios Registrados: {len(st.session_state.empleados)}")
    with st.expander("Modificar Plan de Usuario", expanded=True):
        nombres = [e["Nombre"] for e in st.session_state.empleados]
        sel_u = st.selectbox("Usuario", nombres)
        nuevo_p = st.selectbox("Nuevo Plan", ["Gratis", "Individual", "Pro", "Enterprise"])
        if st.button("Forzar Actualización de Licencia"):
            for e in st.session_state.empleados:
                if e["Nombre"] == sel_u: e["Plan"] = nuevo_p
            guardar_datos(); st.success("Actualizado."); st.rerun()

import streamlit as st
from openai import OpenAI
import json
from datetime import datetime
import pandas as pd
import re
import plotly.express as px
import plotly.graph_objects as go
import os
import smtplib
from email.mime.text import MIMEText
import random

# --- SISTEMA DE MEMORIA LOCAL ---
DATA_FILE = "crysis_data.json"

def cargar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)
            if "escenarios_custom" not in datos: datos["escenarios_custom"] = {}
            # Migración automática: borrar usuarios antiguos sin rol para evitar crasheos
            datos["empleados"] = [e for e in datos.get("empleados", []) if "Rol" in e]
            return datos
    return {"empleados": [], "historial_sesiones": [], "escenarios_custom": {}}

def guardar_datos():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "empleados": st.session_state.empleados,
            "historial_sesiones": st.session_state.historial_sesiones,
            "escenarios_custom": st.session_state.escenarios_custom
        }, f, ensure_ascii=False, indent=4)

# --- MOTOR DE CORREO 2FA ---
def enviar_correo_2fa(destinatario, codigo):
    try:
        remitente = st.secrets["SMTP_EMAIL"]
        password = st.secrets["SMTP_PASS"]
        msg = MIMEText(f"Tu código de autorización táctica para CRYSIS es: {codigo}\n\nSi no has solicitado este acceso, reporta una brecha de seguridad inmediatamente.")
        msg['Subject'] = 'CRYSIS | Código de Acceso 2FA'
        msg['From'] = remitente
        msg['To'] = destinatario
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        return False

# ─────────────────────────────────────────
# 1. CONFIGURACIÓN
# ─────────────────────────────────────────
st.set_page_config(page_title="CRYSIS | Intelligence Unit", layout="wide", initial_sidebar_state="collapsed")

# ─────────────────────────────────────────
# 2. TEMA OSCURO TÁCTICO-PREMIUM (CSS acortado para limpieza)
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"], .stApp { background-color: #07090F !important; color: #C8D0E0 !important; font-family: 'DM Sans', sans-serif !important; }
header[data-testid="stHeader"] { background: #07090F !important; border-bottom: 1px solid #1A2035; }
.stDeployButton, #MainMenu, footer { display: none !important; }
.crysis-title { font-family: 'IBM Plex Mono', monospace; font-size: 3.2rem; font-weight: 700; letter-spacing: 0.35em; color: #E8EDF5; text-align: center; margin-bottom: 0; text-shadow: 0 0 40px rgba(79, 142, 247, 0.25); }
.crysis-subtitle { font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem; letter-spacing: 0.45em; color: #4F8EF7; text-align: center; margin-top: 4px; margin-bottom: 28px; }
.crysis-divider { border: none; border-top: 1px solid #1A2035; margin: 0 0 32px 0; }
.stTabs [data-baseweb="tab-list"] { gap: 0; background: #0C1020; border-bottom: 1px solid #1A2035; border-radius: 0; padding: 0 8px; }
.stTabs [data-baseweb="tab"] { height: 48px; padding: 0 24px; font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.15em; color: #4A5568; border-radius: 0; border: none !important; border-bottom: 2px solid transparent !important; transition: all 0.2s; }
.stTabs [data-baseweb="tab"]:hover { color: #8B9CC8; }
.stTabs [aria-selected="true"] { color: #4F8EF7 !important; background: transparent !important; border-bottom: 2px solid #4F8EF7 !important; }
.stTabs [data-baseweb="tab-panel"] { background: transparent; padding: 24px 0 0 0; }
.metric-card { background: #0C1020; border: 1px solid #1A2035; border-radius: 6px; padding: 22px 24px; position: relative; overflow: hidden; }
.metric-card::before { content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: #4F8EF7; }
.metric-label { font-family: 'IBM Plex Mono', monospace; font-size: 0.6rem; letter-spacing: 0.2em; color: #4F8EF7; margin-bottom: 8px; }
.metric-value { font-family: 'IBM Plex Mono', monospace; font-size: 2rem; font-weight: 700; color: #E8EDF5; line-height: 1; }
.metric-sub { font-size: 0.75rem; color: #4A5568; margin-top: 6px; }
.briefing-box { background: #0C1020; border: 1px solid #1A2035; border-left: 3px solid #4F8EF7; padding: 24px 28px; border-radius: 4px; margin-bottom: 24px; }
.briefing-box h4 { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; letter-spacing: 0.2em; color: #4F8EF7; margin-bottom: 16px; }
.briefing-box p { color: #8B9CC8; font-size: 0.88rem; margin-bottom: 8px; }
.stDataFrame, .stTable { background: #0C1020 !important; }
thead tr th { background: #111827 !important; color: #4F8EF7 !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 0.65rem !important; letter-spacing: 0.15em !important; }
tbody tr td { color: #C8D0E0 !important; font-size: 0.85rem !important; }
.stTextInput input, .stSelectbox > div > div, .stTextArea textarea { background: #0C1020 !important; border: 1px solid #1A2035 !important; color: #C8D0E0 !important; border-radius: 4px !important; font-family: 'DM Sans', sans-serif !important; }
.stTextInput input:focus, .stTextArea textarea:focus { border-color: #4F8EF7 !important; box-shadow: 0 0 0 2px rgba(79,142,247,0.1) !important; }
label, .stSelectbox label { color: #4A5568 !important; font-size: 0.78rem !important; letter-spacing: 0.05em !important; }
.stButton > button { background: #4F8EF7 !important; color: #07090F !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 0.7rem !important; font-weight: 700 !important; letter-spacing: 0.15em !important; border: none !important; border-radius: 3px !important; padding: 12px 28px !important; transition: all 0.2s !important; width: auto; }
.stButton > button:hover { background: #3A7AE4 !important; box-shadow: 0 0 20px rgba(79,142,247,0.3) !important; transform: translateY(-1px); }
.stChatMessage { background: #0C1020 !important; border: 1px solid #1A2035 !important; border-radius: 4px !important; margin-bottom: 8px !important; }
.stChatInputContainer { background: #0C1020 !important; border: 1px solid #1A2035 !important; border-radius: 4px !important; }
.stChatInputContainer textarea { background: transparent !important; color: #C8D0E0 !important; }
.stExpander { background: #0C1020 !important; border: 1px solid #1A2035 !important; border-radius: 4px !important; }
.section-label { font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; letter-spacing: 0.25em; color: #4F8EF7; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #1A2035; }
.status-bar { background: #0C1020; border: 1px solid #1A2035; border-left: 3px solid #22D3A5; padding: 10px 18px; border-radius: 3px; font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; letter-spacing: 0.12em; color: #22D3A5; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 3. DATOS DE CONTEXTO
# ─────────────────────────────────────────
INSTRUCCION_ORTOGRAFIA = " Escribe siempre en español correcto, sin faltas de ortografía ni errores gramaticales. Nunca uses acotaciones entre paréntesis para describir acciones o estados de ánimo. Solo diálogo puro."
CONTEXTOS_MISION = {
    "OPERACION: FRONTERA": {"contexto": "Tensiones militares en el paralelo 38.", "perfil_sujeto": "Ministro Volkov.", "objetivo": "Evitar la escalada bélica.", "prompt": "Eres el Ministro de Defensa de Krasnovia. Hostil y burocrático. Solo diálogo directo." + INSTRUCCION_ORTOGRAFIA},
    "OPERACION: BLACKOUT": {"contexto": "Ataque masivo al sistema eléctrico nacional.", "perfil_sujeto": "'Shadow'. Hacker mercenario.", "objetivo": "Ganar tiempo para localizar el exploit.", "prompt": "Eres Shadow, hacker de elite. Solo texto directo. Sin emociones." + INSTRUCCION_ORTOGRAFIA},
    "OPERACION: EXTRACCION": {"contexto": "Robo a banco fallido. 3 civiles retenidos.", "perfil_sujeto": "Sujeto inestable, bajo presión extrema.", "objetivo": "Asegurar la liberación de rehenes.", "prompt": "Eres un secuestrador acorralado. Gritas, estás nervioso. Solo diálogo crudo." + INSTRUCCION_ORTOGRAFIA}
}
PLOTLY_THEME = dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family='DM Sans', color='#8B9CC8', size=12), margin=dict(l=16, r=16, t=40, b=16))
AXIS_STYLE = dict(gridcolor='#1A2035', zeroline=False, color='#4A5568', linecolor='#1A2035')

# ─────────────────────────────────────────
# 4. PERSISTENCIA Y ESTADOS
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
if "2fa_code" not in st.session_state: st.session_state["2fa_code"] = None
if "2fa_agente" not in st.session_state: st.session_state["2fa_agente"] = None

TODAS_LAS_MISIONES = {**CONTEXTOS_MISION, **st.session_state.escenarios_custom}
try: GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except: GROQ_API_KEY = None

# ─────────────────────────────────────────
# 5. EL MURO DE SEGURIDAD (ENRUTAMIENTO DINÁMICO)
# ─────────────────────────────────────────
params = st.query_params
empresa_invitada = params.get("empresa", None)

if st.session_state.usuario_actual is None:
    st.markdown("<div class='crysis-title' style='margin-top: 50px;'>CRYSIS</div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if empresa_invitada:
            # --- MODO RECLUTAMIENTO (AGENTE) ---
            st.markdown(f"<div class='crysis-subtitle'>ALISTAMIENTO TÁCTICO: {empresa_invitada.upper()}</div><hr class='crysis-divider'>", unsafe_allow_html=True)
            st.info(f"Has sido invitado a unirte a la unidad operativa de **{empresa_invitada}**.")
            with st.form("reg_agente"):
                n = st.text_input("Nombre de Agente / ID")
                email = st.text_input("Correo Electrónico (Para 2FA)")
                d = st.text_input("Departamento")
                p = st.text_input("Crear Código de Acceso", type="password")
                if st.form_submit_button("UNIRSE A LA UNIDAD", use_container_width=True):
                    if n and p and email:
                        if any(e["Nombre"] == n for e in st.session_state.empleados):
                            st.warning("⚠️ Este ID ya está en uso.")
                        else:
                            st.session_state.empleados.append({
                                "Nombre": n, "Email": email, "Departamento": d, "Rol": "Agente", "Empresa": empresa_invitada, "Password": p
                            })
                            guardar_datos()
                            st.success("✅ Alistamiento completado. Borra '?empresa=...' de la URL para Iniciar Sesión normal.")
                    else:
                        st.warning("⚠️ Rellena todos los campos clave.")
        else:
            # --- MODO ESTÁNDAR (LOGIN / REGISTRO EMPRESA) ---
            st.markdown("<div class='crysis-subtitle'>SISTEMA CERRADO · IDENTIFICACIÓN REQUERIDA</div><hr class='crysis-divider'>", unsafe_allow_html=True)
            t_log, t_reg_empresa = st.tabs(["INICIAR SESIÓN", "ALTA DE EMPRESA (COMANDANCIA)"])
            
            with t_log:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.session_state.login_step == 1:
                    with st.form("login_form"):
                        u_id = st.text_input("ID de Acceso")
                        u_pass = st.text_input("Código de Seguridad", type="password")
                        if st.form_submit_button("AUTORIZAR ACCESO", use_container_width=True):
                            agente = next((e for e in st.session_state.empleados if e["Nombre"] == u_id and e.get("Password") == u_pass), None)
                            if agente:
                                st.session_state["2fa_code"] = str(random.randint(100000, 999999))
                                st.session_state["2fa_agente"] = agente
                                st.session_state.login_step = 2
                                st.rerun()
                            else:
                                st.error("❌ Acceso denegado.")
                elif st.session_state.login_step == 2:
                    correo_dest = st.session_state["2fa_agente"].get("Email", "Desconocido")
                    if "correo_enviado" not in st.session_state:
                        exito = enviar_correo_2fa(correo_dest, st.session_state["2fa_code"])
                        if exito: st.success(f"📧 Código enviado a: {correo_dest}")
                        else: st.error("❌ ERROR SMTP. Operación abortada.")
                        st.session_state["correo_enviado"] = True

                    with st.form("2fa_form"):
                        u_code = st.text_input("Código 2FA de 6 dígitos")
                        colA, colB = st.columns(2)
                        with colA:
                            if st.form_submit_button("VERIFICAR", use_container_width=True):
                                if u_code == st.session_state["2fa_code"]:
                                    st.session_state.usuario_actual = st.session_state["2fa_agente"]
                                    st.session_state.login_step = 1
                                    del st.session_state["correo_enviado"]
                                    st.rerun()
                                else: st.error("❌ Código incorrecto.")
                        with colB:
                            if st.form_submit_button("CANCELAR", use_container_width=True):
                                st.session_state.login_step = 1
                                del st.session_state["correo_enviado"]
                                st.rerun()
            
            with t_reg_empresa:
                st.markdown("<br>", unsafe_allow_html=True)
                st.info("Registra un perfil corporativo para invitar a tus agentes y centralizar los datos.")
                with st.form("reg_empresa"):
                    n = st.text_input("Nombre de la Empresa (Este será tu ID de inicio de sesión)")
                    email = st.text_input("Correo Administrativo (Para 2FA)")
                    p = st.text_input("Contraseña Maestra", type="password")
                    if st.form_submit_button("CREAR COMANDANCIA", use_container_width=True):
                        if n and p and email:
                            if any(e["Nombre"] == n for e in st.session_state.empleados):
                                st.warning("⚠️ Esta entidad ya existe.")
                            else:
                                st.session_state.empleados.append({
                                    "Nombre": n, "Email": email, "Departamento": "Comandancia", "Rol": "Empresa", "Empresa": n, "Password": p
                                })
                                guardar_datos()
                                st.success("✅ Infraestructura creada. Inicia sesión para generar links de invitación.")
                        else:
                            st.warning("⚠️ Todos los campos son obligatorios.")
    st.stop()

# ─────────────────────────────────────────
# 6. HEADER AUTENTICADO
# ─────────────────────────────────────────
u = st.session_state.usuario_actual
es_empresa = u.get("Rol") == "Empresa"
rol_label = "COMANDANCIA" if es_empresa else f"AGENTE: {u['Empresa'].upper()}"

c_head1, c_head2 = st.columns([8, 1])
with c_head1:
    st.markdown("<div class='crysis-title' style='text-align:left; font-size:2.2rem;'>CRYSIS</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='crysis-subtitle' style='text-align:left; margin-bottom:10px;'>{rol_label} | ID: {u['Nombre'].upper()}</div>", unsafe_allow_html=True)
with c_head2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("SALIR", key="logout", type="secondary"):
        st.session_state.usuario_actual = None
        st.session_state.login_step = 1 
        st.rerun()
st.markdown("<hr class='crysis-divider' style='margin-top:0;'>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 7. LOGICA DE DATOS (Filtrado B2B)
# ─────────────────────────────────────────
empresa_actual = u["Empresa"]
# Si es Empresa, ve las notas de TODOS sus agentes. Si es Agente, solo ve las suyas.
if es_empresa:
    agentes_de_mi_empresa = [e["Nombre"] for e in st.session_state.empleados if e["Empresa"] == empresa_actual and e["Rol"] == "Agente"]
    historial_visible = [s for s in st.session_state.historial_sesiones if s["Agente"] in agentes_de_mi_empresa]
else:
    historial_visible = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]

# ─────────────────────────────────────────
# 8. TABS DINÁMICOS
# ─────────────────────────────────────────
if es_empresa:
    t1, t2, t3, t4, t5 = st.tabs(["RENDIMIENTO GLOBAL", "CENTRO DE RECLUTAMIENTO", "EXPEDIENTES GENERALES", "SIMULADOR", "LABORATORIO VIP"])
else:
    t1, t2, t3, t4 = st.tabs(["MIS ESTADÍSTICAS", "MI PERFIL", "MIS EXPEDIENTES", "SIMULADOR"])
    t5 = None # Agentes no tienen Laboratorio VIP

# ══════════════════════════════════════════
# TAB 1: ESTADÍSTICAS (Compartidas o Individuales)
# ══════════════════════════════════════════
with t1:
    total_ops = len(historial_visible)
    media_global = int(sum(s["Nota"] for s in historial_visible) / total_ops) if total_ops > 0 else 0
    ops_exitosas = sum(1 for s in historial_visible if s["Nota"] >= 70)
    tasa_exito = int((ops_exitosas / total_ops) * 100) if total_ops > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""<div class="metric-card"><div class="metric-label">RENDIMIENTO MEDIO</div><div class="metric-value" style="color:{'#22D3A5' if media_global >= 70 else '#EF4444'}">{media_global}%</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="metric-card"><div class="metric-label">TASA DE ÉXITO</div><div class="metric-value" style="color:{'#22D3A5' if tasa_exito >= 60 else '#EF4444'}">{tasa_exito}%</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="metric-card"><div class="metric-label">MISIONES COMPLETADAS</div><div class="metric-value" style="color:#4F8EF7">{total_ops}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if not historial_visible:
        st.markdown("<div style='text-align:center; padding: 60px; color: #2A3550; font-family: IBM Plex Mono; letter-spacing: 0.2em;'>SIN DATOS OPERACIONALES</div>", unsafe_allow_html=True)
    else:
        df = pd.DataFrame(historial_visible)
        col_left, col_right = st.columns(2, gap="medium")
        
        with col_left:
            st.markdown("<div class='section-label'>DISTRIBUCIÓN POR ESCENARIO</div>", unsafe_allow_html=True)
            esc_count = df["Escenario"].value_counts().reset_index()
            esc_count.columns = ["Escenario", "Count"]
            esc_count["Escenario"] = esc_count["Escenario"].str.replace("OPERACION: ", "", regex=False)
            fig2 = go.Figure(go.Pie(labels=esc_count["Escenario"], values=esc_count["Count"], hole=0.65, marker=dict(colors=['#4F8EF7', '#22D3A5', '#F59E0B'])))
            fig2.update_layout(**PLOTLY_THEME, height=280, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        with col_right:
            if es_empresa:
                st.markdown("<div class='section-label'>RENDIMIENTO POR AGENTE</div>", unsafe_allow_html=True)
                avg_agent = df.groupby("Agente")["Nota"].mean().reset_index()
                fig3 = go.Figure(go.Bar(x=avg_agent["Nota"], y=avg_agent["Agente"], orientation='h', marker=dict(color='#4F8EF7')))
                fig3.update_layout(**PLOTLY_THEME, height=280)
            else:
                st.markdown("<div class='section-label'>EVOLUCIÓN TEMPORAL</div>", unsafe_allow_html=True)
                df["Fecha_dt"] = pd.to_datetime(df["Fecha"])
                df_sorted = df.sort_values("Fecha_dt")
                fig3 = go.Figure(go.Scatter(x=df_sorted["Fecha_dt"], y=df_sorted["Nota"], mode='lines+markers', line=dict(color='#4F8EF7')))
                fig3.add_hline(y=70, line_dash="dot", line_color="#22D3A5")
                fig3.update_layout(**PLOTLY_THEME, height=280)
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

# ══════════════════════════════════════════
# TAB 2: MI PERFIL / RECLUTAMIENTO
# ══════════════════════════════════════════
with t2:
    if es_empresa:
        st.markdown("<div class='section-label'>ENLACE DE ALISTAMIENTO</div>", unsafe_allow_html=True)
        st.info("Envía este enlace a tus empleados. Cuando se registren, aparecerán automáticamente en tu panel global.")
        
        # Generar URL Dinámica
        import urllib.parse
        empresa_url = urllib.parse.quote(u['Nombre'])
        st.code(f"?empresa={empresa_url}", language="html")
        st.caption("Copia la URL de tu página web y añádele el texto de arriba al final.")
        
        st.markdown("<br><div class='section-label'>TUS AGENTES ACTIVOS</div>", unsafe_allow_html=True)
        for ag in [e for e in st.session_state.empleados if e["Empresa"] == empresa_actual and e["Rol"] == "Agente"]:
            st.markdown(f"**{ag['Nombre']}** | Dept: {ag['Departamento']} | Correo: {ag['Email']}")
    else:
        st.markdown("<div class='section-label'>CREDENCIALES ACTIVAS</div>", unsafe_allow_html=True)
        st.markdown(f"""<div class="briefing-box" style="border-left-color:#22D3A5;">
            <h4 style="color:#22D3A5;">🛡️ IDENTIFICACIÓN VALIDADA</h4>
            <p><b>Agente:</b> {u['Nombre']} | <b>Unidad:</b> {u['Empresa']}</p>
            <p><b>Departamento:</b> {u.get('Departamento', 'Desconocido')}</p>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════
# TAB 3: EXPEDIENTES
# ══════════════════════════════════════════
with t3:
    st.markdown("<div class='section-label'>ARCHIVO DE OPERACIONES CLASIFICADAS</div>", unsafe_allow_html=True)
    if historial_visible:
        # Mostrar invertido (más recientes primero)
        for s in reversed(historial_visible):
            nota_color = "#22D3A5" if s["Nota"] >= 70 else ("#F59E0B" if s["Nota"] >= 40 else "#EF4444")
            label_agente = f"[{s['Agente']}] " if es_empresa else ""
            with st.expander(f"⬡ {label_agente}{s['Fecha']} · {s['Escenario']} · PUNTUACIÓN: {s['Nota']}%"):
                st.markdown(s['Evaluacion'])
    else:
        st.markdown("<div style='text-align:center; padding:60px; color:#2A3550; font-family:IBM Plex Mono;'>SIN EXPEDIENTES</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════
# TAB 4: SIMULADOR
# ══════════════════════════════════════════
with t4:
    if not st.session_state.mision_iniciada:
        st.markdown("<div class='section-label'>CONFIGURACIÓN DE DESPLIEGUE</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        ag_sel = c1.selectbox("Agente Asignado:", agentes_de_mi_empresa) if es_empresa else c1.text_input("Agente:", value=u["Nombre"], disabled=True)
        # Fix: Si no hay agentes reclutados en la empresa, el selectbox devuelve None
        if ag_sel is None and es_empresa: ag_sel = u["Nombre"] 

        es_sel = c2.selectbox("Seleccionar Escenario:", list(TODAS_LAS_MISIONES.keys()))
        info = TODAS_LAS_MISIONES[es_sel]
        st.markdown(f"""<div class="briefing-box"><h4>📄 BRIEFING OPERATIVO BASE</h4><p><b>Contexto:</b> {info['contexto']}</p><p><b>Perfil:</b> {info['perfil_sujeto']}</p><p><b>Objetivo:</b> {info['objetivo']}</p></div>""", unsafe_allow_html=True)

        if st.button("INICIAR PROTOCOLO DE CONTACTO →", use_container_width=True):
            if GROQ_API_KEY:
                with st.spinner("Generando variables dinámicas..."):
                    try:
                        client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                        sys_prompt = f"Genera para este perfil: {info['perfil_sujeto']}. Devuelve EXCLUSIVAMENTE JSON con: 'Nombre_Completo', 'Familia', 'Estado_Mental'."
                        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": sys_prompt}], response_format={"type": "json_object"}).choices[0].message.content
                        st.session_state.tarjeta_objetivo = json.loads(res)
                    except: st.session_state.tarjeta_objetivo = {"Nombre_Completo": "Desconocido", "Familia": "Clasificado", "Estado_Mental": "Inestable"}
            
            st.session_state.mision_iniciada = True
            st.session_state.mensajes = []
            st.session_state.agente_activo = ag_sel
            st.session_state.escenario_activo = es_sel
            st.rerun()

    elif st.session_state.evaluacion_actual:
        st.markdown("<div class='section-label'>DEBRIEFING — INFORME DE RENDIMIENTO</div>", unsafe_allow_html=True)
        st.markdown(st.session_state.evaluacion_actual)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("CERRAR OPERACIÓN Y VOLVER A BASE →", use_container_width=True):
            st.session_state.mision_iniciada = False; st.session_state.evaluacion_actual = None; st.session_state.mensajes = []; st.session_state.tarjeta_objetivo = None; st.rerun()

    else:
        st.markdown(f"<div class='status-bar'>◉ OPERACIÓN: {st.session_state.escenario_activo} · AGENTE: {st.session_state.agente_activo.upper()}</div>", unsafe_allow_html=True)
        if st.session_state.tarjeta_objetivo:
            t = st.session_state.tarjeta_objetivo
            st.markdown(f"""<div style="display:flex; gap:15px; background:#0C1020; border:1px solid #1A2035; border-left:3px solid #F59E0B; border-radius:4px; padding:12px 18px; margin-bottom:20px;">
                <div style="flex:1;"><div style="color:#F59E0B; font-size:0.55rem; font-family:'IBM Plex Mono'; letter-spacing:0.15em; margin-bottom:4px;">ID OBJETIVO</div><div style="color:#E8EDF5; font-size:0.85rem;">{t.get('Nombre_Completo', 'N/A')}</div></div>
                <div style="flex:1;"><div style="color:#F59E0B; font-size:0.55rem; font-family:'IBM Plex Mono'; letter-spacing:0.15em; margin-bottom:4px;">VÍNCULOS FAMILIARES</div><div style="color:#C8D0E0; font-size:0.8rem;">{t.get('Familia', 'N/A')}</div></div>
                <div style="flex:1;"><div style="color:#F59E0B; font-size:0.55rem; font-family:'IBM Plex Mono'; letter-spacing:0.15em; margin-bottom:4px;">ESTADO CLÍNICO</div><div style="color:#C8D0E0; font-size:0.8rem;">{t.get('Estado_Mental', 'N/A')}</div></div>
            </div>""", unsafe_allow_html=True)

        for m in st.session_state.mensajes:
            label = "AGENTE" if m["role"] == "user" else "OBJETIVO"
            bg = "#0F1829" if m["role"] == "user" else "#0C1020"
            border = "#4F8EF7" if m["role"] == "user" else "#EF4444"
            align = "flex-end" if m["role"] == "user" else "flex-start"
            st.markdown(f"""<div style="display:flex; justify-content:{align}; margin-bottom:12px;"><div style="max-width:78%; background:{bg}; border:1px solid {border}22; border-left: 3px solid {border}; border-radius:4px; padding:14px 18px;"><div style="font-family:'IBM Plex Mono',monospace; font-size:0.58rem; letter-spacing:0.18em; color:{border}; margin-bottom:8px;">{label}</div><div style="color:#C8D0E0; font-size:0.9rem; line-height:1.6;">{m['content']}</div></div></div>""", unsafe_allow_html=True)

        if prompt := st.chat_input("Introduzca directiva de negociación..."):
            st.session_state.mensajes.append({"role": "user", "content": prompt}); st.rerun()

        if st.session_state.mensajes and st.session_state.mensajes[-1]["role"] == "user":
            if GROQ_API_KEY:
                client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                base_prompt = TODAS_LAS_MISIONES[st.session_state.escenario_activo]["prompt"]
                if st.session_state.tarjeta_objetivo:
                    t = st.session_state.tarjeta_objetivo
                    base_prompt += f"\n\n[INSTRUCCIÓN VITAL: Tu nombre es {t.get('Nombre_Completo')}. Familia: {t.get('Familia')}. Estado actual: {t.get('Estado_Mental')}.]"
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": base_prompt}] + st.session_state.mensajes).choices[0].message.content
                st.session_state.mensajes.append({"role": "assistant", "content": res})
                st.rerun()

        col_end, col_abort = st.columns([3, 1])
        with col_abort:
            if st.button("✖ ABORTAR", type="secondary", use_container_width=True):
                st.session_state.mision_iniciada = False; st.session_state.mensajes = []; st.session_state.tarjeta_objetivo = None; st.rerun()
        with col_end:
            if len(st.session_state.mensajes) > 0:
                if st.button("🛑 FINALIZAR Y GENERAR INFORME OPERACIONAL →", use_container_width=True):
                    with st.spinner("Procesando análisis táctico..."):
                        client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                        escenario = st.session_state.escenario_activo
                        info = TODAS_LAS_MISIONES[escenario]
                        hist_txt = "\n".join([f"{'NEGOCIADOR' if m['role'] == 'user' else 'OBJETIVO'}: {m['content']}" for m in st.session_state.mensajes])
                        eval_prompt = f"Evalúa ÚNICAMENTE al NEGOCIADOR en esta misión: {escenario}. Situación: {info['contexto']}.\nTRANSCRIPCIÓN:\n{hist_txt}\nGenera informe estricto. Estructura:\n**ANÁLISIS DE LENGUAJE**\n**TÁCTICAS EMPLEADAS**\n**ERRORES CRÍTICOS**\n**VEREDICTO DEL EVALUADOR**\n\nPUNTUACIÓN FINAL: XX/100"
                        informe = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": eval_prompt}]).choices[0].message.content
                        try:
                            match = re.search(r'PUNTUACI[OÓ]N FINAL[^\d]*(\d+)\s*\/?\s*100', informe, re.IGNORECASE)
                            nota = min(int(match.group(1)), 100) if match else (min(int(re.search(r'(\d+)\s*/\s*100', informe).group(1)), 100) if re.search(r'(\d+)\s*/\s*100', informe) else 50)
                        except: nota = 50
                        st.session_state.evaluacion_actual = informe
                        st.session_state.historial_sesiones.append({"Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "Agente": st.session_state.agente_activo, "Escenario": escenario, "Nota": nota, "Evaluacion": informe})
                        guardar_datos()
                        st.rerun()

# ══════════════════════════════════════════
# TAB 5: LABORATORIO VIP (SOLO EMPRESAS)
# ══════════════════════════════════════════
if t5:
    with t5:
        col_izq, col_der = st.columns([2, 1], gap="large")
        with col_izq:
            st.markdown("<div class='section-label'>SÍNTESIS DE OPERACIONES MEDIANTE IA</div>", unsafe_allow_html=True)
            idea_prompt = st.text_area("Describa la situación táctica.", height=100)
            if st.button("✨ SINTETIZAR NUEVA OPERACIÓN", use_container_width=True):
                if idea_prompt and GROQ_API_KEY:
                    with st.spinner("Conectando con Inteligencia Central..."):
                        try:
                            client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                            sys_instruct = "Eres creador de simulaciones. Devuelve EXCLUSIVAMENTE JSON: {'nombre_op': 'OPERACION: [NOMBRE]', 'contexto': '[Desc]', 'perfil_sujeto': '[Perfil]', 'objetivo': '[Misión]', 'prompt': '[Instrucciones para el LLM]'}"
                            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": sys_instruct}, {"role": "user", "content": idea_prompt}], response_format={"type": "json_object"}).choices[0].message.content
                            nuevo_esc = json.loads(res)
                            nuevo_esc["prompt"] += INSTRUCCION_ORTOGRAFIA
                            st.session_state.escenarios_custom[nuevo_esc["nombre_op"]] = {"contexto": nuevo_esc["contexto"], "perfil_sujeto": nuevo_esc["perfil_sujeto"], "objetivo": nuevo_esc["objetivo"], "prompt": nuevo_esc["prompt"]}
                            guardar_datos()
                            st.success(f"✅ Protocolo {nuevo_esc['nombre_op']} integrado.")
                            st.rerun()
                        except Exception as e: st.error(f"❌ Fallo Groq: {e}")
                elif not idea_prompt: st.warning("Escriba los parámetros antes de sintetizar.")

        with col_der:
            st.markdown("<div class='section-label'>CONTROL DE MEMORIA</div>", unsafe_allow_html=True)
            st.markdown("""<div class="briefing-box" style="border-left-color: #EF4444;"><h4 style="color: #EF4444; font-size:0.6rem;">⚠ PROTOCOLO DE PURGA</h4><p style="font-size:0.75rem;">Elimina a TODOS los agentes, historiales y misiones.</p></div>""", unsafe_allow_html=True)
            if st.button("☣️ PURGAR TODO EL SISTEMA", use_container_width=True):
                st.session_state.empleados = []; st.session_state.historial_sesiones = []; st.session_state.escenarios_custom = {}
                st.session_state.usuario_actual = None; st.session_state.login_step = 1
                guardar_datos(); st.rerun()

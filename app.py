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
# HORA ESPAÑA
# ─────────────────────────────────────────
def hora_espana():
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo("Europe/Madrid")
        return datetime.now(tz)
    except Exception:
        try:
            import pytz
            tz = pytz.timezone("Europe/Madrid")
            return datetime.now(tz)
        except Exception:
            return datetime.now()

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
    "BASE":        {"precio": "0€",      "desc": "Individual · 1 op/mes · sin IA",        "ops": 1,     "escenarios": 0,     "agentes": 0,     "elite": False},
    "OPERADOR":    {"precio": "19€/mes", "desc": "Individual · 10 ops/mes · 3 escenarios", "ops": 10,    "escenarios": 3,     "agentes": 0,     "elite": False},
    "ELITE":       {"precio": "49€/mes", "desc": "Individual · ilimitado · IA sin límite", "ops": 99999, "escenarios": 99999, "agentes": 0,     "elite": True},
    "ESCUADRON":   {"precio": "89€/mes", "desc": "Equipo · ilimitado · 15 agentes",        "ops": 99999, "escenarios": 99999, "agentes": 15,    "elite": True},
    "COMANDANCIA": {"precio": "199€/mes","desc": "Enterprise · ilimitado · ∞ agentes",     "ops": 99999, "escenarios": 99999, "agentes": 99999, "elite": True},
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
# TRADUCCIONES
# ─────────────────────────────────────────
T = {
    "es": {
        "hq": "CUARTEL GENERAL", "welcome": "Bienvenido,", "operative": "SISTEMA OPERATIVO",
        "mod01": "MOD-01 / ESTADÍSTICAS", "mod01_title": "Análisis de Rendimiento",
        "mod01_desc": "Métricas globales, histórico de desempeño y distribución de escenarios por operador.",
        "mod01_stat": "RENDIMIENTO MEDIO",
        "mod02": "MOD-02 / DESPLIEGUE", "mod02_title": "Simulador Táctico",
        "mod02_desc": "Inicia una operación de negociación táctica en tiempo real con objetivo generado por IA.",
        "mod02_stat": "OPS ESTE MES",
        "mod03": "MOD-03 / EXPEDIENTES", "mod03_title": "Archivo Operacional",
        "mod03_desc": "Consulta y descarga de dossiers de sesiones anteriores con transcripciones completas.",
        "mod03_stat": "EXPEDIENTES TOTALES",
        "mod04": "MOD-04 / PERSONAL", "mod04_title": "Gestión de Operadores",
        "mod04_desc": "Reclutamiento de agentes, control de accesos, enlace cifrado y ajustes de cuenta.",
        "mod04_stat": "AGENTES ACTIVOS",
        "mod05": "MOD-05 / SÍNTESIS", "mod05_title": "Generación de Escenarios",
        "mod05_desc": "Motor de IA para crear simulaciones personalizadas adaptadas a tu contexto operativo.",
        "mod05_stat": "ESCENARIOS ACTIVOS",
        "mod06": "MOD-06 / ADMIN", "mod06_title": "Consola Omega",
        "mod06_desc": "Panel de control global. Gestión de usuarios, planes y métricas SaaS en tiempo real.",
        "mod06_stat": "MRR ESTIMADO",
        "profile": "PERFIL", "settings": "AJUSTES", "logout": "CERRAR SESIÓN",
        "back_menu": "← MENÚ", "status_ok": "● OPERATIVO · ACCESO SEGURO",
        "lang_label": "🌐 ES",
        "access": "ACCESO", "register": "REGISTRO",
        "operator_id": "ID Operativo", "security_key": "Clave de Seguridad",
        "login_btn": "INICIAR SESIÓN SEGURA", "forgot": "¿Olvidaste tu contraseña?",
        "brand_desc": "Plataforma de simulación táctica avanzada para el entrenamiento en negociación, desescalada y comunicación bajo presión extrema.",
        "system_status": "ESTADO DEL SISTEMA",
        "stats_title": "Análisis de Rendimiento", "stats_code": "MOD-01",
        "avg_perf": "RENDIMIENTO MEDIO", "excellence": "TASA DE EXCELENCIA", "missions": "MISIONES COMPLETADAS",
        "no_records": "SIN REGISTROS OPERACIONALES",
        "scenario_dist": "DISTRIBUCIÓN DE ESCENARIOS", "agent_eval": "EVALUACIÓN POR OPERADOR",
        "perf_history": "HISTÓRICO DE DESEMPEÑO",
        "sim_title": "Simulador Táctico", "sim_code": "MOD-02",
        "assign_op": "Asignar Operador:", "select_proto": "Seleccionar Protocolo:",
        "difficulty": "NIVEL DE DIFICULTAD", "situation_report": "REPORTE DE SITUACIÓN",
        "context": "Contexto:", "target_profile": "Perfil del objetivo:", "directive": "Directiva:", "diff_label": "Dificultad:",
        "start_link": "INICIAR ENLACE DE COMUNICACIÓN", "break_link": "ROMPER ENLACE",
        "request_eval": "SOLICITAR EVALUACIÓN TÁCTICA", "chat_placeholder": "Introduce tu directiva de respuesta...",
        "archive_report": "ARCHIVAR INFORME Y VOLVER AL MENÚ", "download_pdf": "DESCARGAR DOSSIER PDF",
        "tactical_eval": "INFORME DE EVALUACIÓN TÁCTICA",
        "exp_title": "Archivo Operacional", "exp_code": "MOD-03",
        "operator_label": "OPERADOR:", "global_metric": "MÉTRICA GLOBAL:",
        "extract_dossier": "EXTRAER DOSSIER PDF", "delete": "ELIMINAR",
        "pers_title": "Gestión de Operadores", "pers_code": "MOD-04",
        "recruit_link": "ENLACE SEGURO DE RECLUTAMIENTO", "active_roster": "PLANTILLA OPERATIVA ACTIVA",
        "revoke_access": "REVOCAR ACCESO DE PERSONAL",
        "account_settings": "AJUSTES DE CUENTA", "change_pass": "CAMBIAR CONTRASEÑA",
        "new_pass": "Nueva Contraseña", "confirm_pass": "Confirmar Contraseña",
        "update_pass": "ACTUALIZAR CONTRASEÑA", "subscription": "GESTIÓN DE SUSCRIPCIÓN",
        "danger_zone": "ZONA DE RIESGO", "delete_account": "ELIMINAR MI CUENTA DEFINITIVAMENTE",
        "sint_title": "Generación de Escenarios", "sint_code": "MOD-05",
        "active_scenarios": "ESCENARIOS ACTIVOS", "new_sim": "NUEVA SIMULACIÓN",
        "gen_sim": "GENERAR NUEVA SIMULACIÓN", "ai_access": "NIVELES DE ACCESO IA",
        "admin_title": "Consola Omega — Administración Global", "admin_code": "MOD-06",
        "mrr": "MRR ESTIMADO", "paid_accounts": "CUENTAS DE PAGO",
        "deployed_agents": "AGENTES DESPLEGADOS", "total_sessions": "SESIONES TOTALES",
        "official_mission": "Misión Oficial (Auditable por el Mando)",
        "private_training": "Entrenamiento Privado (Oculto en expediente corporativo)",
        "privacy_level": "Nivel de Privacidad:",
        "confirmed_credential": "ACREDITACIÓN CONFIRMADA", "operator_data": "DATOS DEL OPERADOR",
        "identifier": "Identificador:", "unit": "Unidad:", "plan": "Plan:",
        "revoke_credentials": "REVOCAR CREDENCIALES",
        "access_denied_quota": "AUTORIZACIÓN DENEGADA: Cuota mensual superada",
        "access_denied_expired": "ACCESO DENEGADO: Licencia expirada",
        "wrong_credentials": "ID o contraseña incorrectos. Verifica tus credenciales.",
        "2fa_title": "VERIFICACION DE DISPOSITIVO", "2fa_info": "Autenticación de dos factores requerida la primera vez. Revisa tu correo.",
        "verify": "VERIFICAR", "cancel": "CANCELAR",
        "recovery_title": "RECUPERACION DE ACCESO",
        "recovery_info": "Introduce tu ID de operador y el correo registrado. Si coinciden, recibirás una contraseña temporal por correo.",
        "send_temp": "ENVIAR CLAVE TEMPORAL", "back": "VOLVER",
        "registered_email": "Correo Registrado",
        "select_access": "SELECCIONAR NIVEL DE ACCESO", "access_data": "DATOS DE ACCESO",
        "entity_name": "Nombre de la Entidad / Empresa", "personal_alias": "Alias / ID Personal",
        "contact_email": "Correo de Contacto", "password": "Contraseña",
        "create_pay": "CREAR CUENTA E IR AL PAGO", "create_enter": "CREAR CUENTA Y ENTRAR",
        "activation_pending": "ACTIVACION DE PLAN PENDIENTE",
        "go_payment": "IR AL PAGO —", "enter_base": "ENTRAR CON NIVEL BASE",
        "invite_label": "ALISTAMIENTO ACTIVO ·",
        "agent_credentials": "SOLICITUD DE CREDENCIALES DE AGENTE",
        "agent_id": "Identificador de Agente (ID)", "corp_email": "Correo Corporativo",
        "dept": "Unidad / Departamento", "set_key": "Establecer Clave de Acceso",
        "register_credentials": "REGISTRAR CREDENCIALES",
        "no_agents": "No hay agentes activos en esta unidad.",
        "describe_scenario": "Describe el entorno táctico y el tipo de sujeto:",
        "scenario_placeholder": "Ej: Un ejecutivo corrupto atrapado en una negociación empresarial. Arrogante y calculador...",
        "activate": "ACTIVAR", "active": "● ACTIVO",
        "empty_dir": "DIRECTORIO VACÍO",
        "confirm_required": "CONFIRMACIÓN REQUERIDA",
        "confirm_delete_phrase": "CONFIRMAR BORRADO",
        "write_confirm": "Escribe CONFIRMAR BORRADO y pulsa ejecutar.",
        "execute": "EJECUTAR",
        "comms_audit": "AUDITORÍA DE COMUNICACIONES",
        "identification": "IDENTIFICACIÓN", "links": "VÍNCULOS", "clinical_state": "ESTADO CLÍNICO",
        "secure_line": "● LÍNEA SEGURA ACTIVA:", "operator_short": "OPERADOR:", "diff_short": "DIFICULTAD:",
        "processing": "Procesando auditoría lingüística...", "connecting": "Estableciendo conexión segura...",
        "ai_engine": "Enlazando con el motor de IA...",
        "global_dir": "DIRECTORIO GLOBAL DE USUARIOS", "scenario_dir": "DIRECTORIO GLOBAL DE ESCENARIOS",
        "issue_credential": "EMITIR CREDENCIAL DE CORTESÍA", "activate_plan": "ACTIVAR / CAMBIAR PLAN",
        "generate_access": "GENERAR ACCESO", "apply_plan": "APLICAR PLAN",
        "temp_license": "Licencia temporal (30 días)", "add_expiry": "Añadir expiración (30 días)",
        "format_platform": "FORMATEAR PLATAFORMA COMPLETA",
        "purge": "PURGAR", "new_plan": "Nuevo Plan:", "user_label": "Usuario:",
        "account_created": "Cuenta creada. Tras el pago, tu plan se activará en máximo 24h.",
        "no_users": "No hay usuarios registrados.", "no_scenarios": "Sin escenarios personalizados.",
        "id_label": "ID / Entidad", "email_label": "Correo", "role_label": "Rol",
        "plan_label": "Plan", "select_role": "Seleccionar", "select_plan": "Seleccionar",
        "temp_pass_sent": "Clave temporal enviada a",
        "pass_updated": "Contraseña actualizada correctamente.",
        "account_revoked": "Operador revocado.",
        "scenario_created": "Protocolo creado y activado.",
        "plan_updated": "Plan actualizado.",
        "id_taken": "Ya existe una cuenta con ese identificador.",
        "fill_all": "Rellena todos los campos para continuar.",
        "invalid_pass": "Introduce una contraseña válida.",
        "pass_mismatch": "Las contraseñas no coinciden.",
        "wrong_confirm": "Frase incorrecta.",
        "wrong_code": "Código incorrecto.",
        "corp_info": "Las cuentas corporativas pueden añadir agentes mediante enlace de invitación.",
        "share_link": "Comparte este enlace con tus agentes para que se incorporen automáticamente a tu unidad.",
        "quota_reached": "CUOTA ALCANZADA",
        "no_ai_access": "RESTRICCIÓN: El nivel BASE no permite el uso de IA Generativa. Actualiza tu plan para desbloquear esta función.",
        "license_no_agents": "Tu nivel de licencia no permite la formación de escuadrones. Actualiza a ESCUADRON o COMANDANCIA.",
        "irrev_action": "Esta acción es irreversible. Se eliminarán todos los datos asociados a tu cuenta.",
        "destroy_all": "Esta acción destruirá todos los datos de la plataforma de forma irreversible.",
        "secure_access": "ACCESO SEGURO",
        "classified": "v3.2.0 · CLASIFICADO",
        "enrollment_done": "Acreditación procesada. Identifícate en el portal de acceso.",
        "corp_accounts": "Las cuentas corporativas pueden añadir agentes mediante enlace de invitación.",
        "select_operator": "Seleccionar",
        # Simulator v2
        "tactical_context": "CONTEXTO TÁCTICO",
        "live_feed": "LIVE COMMUNICATION FEED",
        "subject_diag": "DIAGNÓSTICO DEL SUJETO",
        "active_negotiation": "Negociación Activa:",
        "obj1": "OBJ.1: Establecer contacto inicial",
        "obj2": "OBJ.2: Evaluar demandas y estado",
        "obj3": "OBJ.3: Ejecutar protocolo de desescalada",
        "operator_controls": "OPERATOR CONTROLS",
        "emotional_state": "ESTADO EMOCIONAL",
        "response_latency": "LATENCIA DE RESPUESTA",
        "compliance_trend": "TENDENCIA DE COMPLIANCE",
        "analysis": "ANÁLISIS",
        "status_high": "ALTA TENSIÓN · INESTABLE",
        "status_med": "TENSIÓN MEDIA · MONITORIZAR",
        "status_low": "BAJA TENSIÓN · ESTABLE",
        "advice_deesc": "Prioriza recopilación de información. Mantén desescalada.",
        "prev_nota": "NOTA ANTERIOR:",
        "curr_perf": "RENDIMIENTO ACTUAL (EST.):",
        "no_prev": "N/A",
        "btn_contact": "ESTABLECER CONTACTO",
        "btn_protocol": "DESPLEGAR PROTOCOLO ALFA-4",
        "btn_info": "INICIAR RECOPILACIÓN INFO",
        "btn_crisis": "SOLICITAR APOYO DE CRISIS",
        "quick_contact": "Operador al habla, aquí para establecer un canal de comunicación directo.",
        "quick_protocol": "Escucha, existe un protocolo que podemos seguir los dos. Necesito que confíes en mí.",
        "quick_info": "Antes de tomar cualquier decisión, necesito entender exactamente qué necesitas.",
        "quick_crisis": "Estoy contactando con el equipo de apoyo. Permanece en línea.",
        "network_secure": "RED SEGURA",
        "ai_online": "IA EN LÍNEA",
        "sys_global": "SISTEMA",
    },
    "en": {
        "hq": "HEADQUARTERS", "welcome": "Welcome,", "operative": "SYSTEM OPERATIVE",
        "mod01": "MOD-01 / STATISTICS", "mod01_title": "Performance Analysis",
        "mod01_desc": "Global metrics, performance history and scenario distribution by operator.",
        "mod01_stat": "GLOBAL AVG",
        "mod02": "MOD-02 / DEPLOYMENT", "mod02_title": "Tactical Simulator",
        "mod02_desc": "Launch a real-time tactical negotiation operation with AI-generated target.",
        "mod02_stat": "OPS THIS MONTH",
        "mod03": "MOD-03 / DOSSIERS", "mod03_title": "Operational Archive",
        "mod03_desc": "Consult and download dossiers from previous sessions with full transcripts.",
        "mod03_stat": "TOTAL DOSSIERS",
        "mod04": "MOD-04 / PERSONNEL", "mod04_title": "Operator Management",
        "mod04_desc": "Agent recruitment, access control, encrypted link and account settings.",
        "mod04_stat": "ACTIVE AGENTS",
        "mod05": "MOD-05 / SYNTHESIS", "mod05_title": "Scenario Generation",
        "mod05_desc": "AI engine to create custom simulations adapted to your operational context.",
        "mod05_stat": "ACTIVE SCENARIOS",
        "mod06": "MOD-06 / ADMIN", "mod06_title": "Omega Console",
        "mod06_desc": "Global control panel. User management, plans and real-time SaaS metrics.",
        "mod06_stat": "ESTIMATED MRR",
        "profile": "PROFILE", "settings": "SETTINGS", "logout": "SIGN OUT",
        "back_menu": "← MENU", "status_ok": "● OPERATIVE · SECURE ACCESS",
        "lang_label": "🌐 EN",
        "access": "ACCESS", "register": "REGISTER",
        "operator_id": "Operator ID", "security_key": "Security Key",
        "login_btn": "SECURE LOGIN", "forgot": "Forgot your password?",
        "brand_desc": "Advanced tactical simulation platform for training in negotiation, de-escalation and communication under extreme pressure.",
        "system_status": "SYSTEM STATUS",
        "stats_title": "Performance Analysis", "stats_code": "MOD-01",
        "avg_perf": "AVERAGE PERFORMANCE", "excellence": "EXCELLENCE RATE", "missions": "COMPLETED MISSIONS",
        "no_records": "NO OPERATIONAL RECORDS",
        "scenario_dist": "SCENARIO DISTRIBUTION", "agent_eval": "AGENT EVALUATION",
        "perf_history": "PERFORMANCE HISTORY",
        "sim_title": "Tactical Simulator", "sim_code": "MOD-02",
        "assign_op": "Assign Operator:", "select_proto": "Select Protocol:",
        "difficulty": "DIFFICULTY LEVEL", "situation_report": "SITUATION REPORT",
        "context": "Context:", "target_profile": "Target profile:", "directive": "Directive:", "diff_label": "Difficulty:",
        "start_link": "INITIATE SECURE LINK", "break_link": "BREAK LINK",
        "request_eval": "REQUEST TACTICAL EVALUATION", "chat_placeholder": "Enter your response directive...",
        "archive_report": "ARCHIVE REPORT AND BACK TO MENU", "download_pdf": "DOWNLOAD PDF DOSSIER",
        "tactical_eval": "TACTICAL EVALUATION REPORT",
        "exp_title": "Operational Archive", "exp_code": "MOD-03",
        "operator_label": "OPERATOR:", "global_metric": "GLOBAL METRIC:",
        "extract_dossier": "EXTRACT PDF DOSSIER", "delete": "DELETE",
        "pers_title": "Operator Management", "pers_code": "MOD-04",
        "recruit_link": "SECURE RECRUITMENT LINK", "active_roster": "ACTIVE OPERATIONAL ROSTER",
        "revoke_access": "REVOKE PERSONNEL ACCESS",
        "account_settings": "ACCOUNT SETTINGS", "change_pass": "CHANGE PASSWORD",
        "new_pass": "New Password", "confirm_pass": "Confirm Password",
        "update_pass": "UPDATE PASSWORD", "subscription": "SUBSCRIPTION MANAGEMENT",
        "danger_zone": "DANGER ZONE", "delete_account": "PERMANENTLY DELETE MY ACCOUNT",
        "sint_title": "Scenario Generation", "sint_code": "MOD-05",
        "active_scenarios": "ACTIVE SCENARIOS", "new_sim": "NEW SIMULATION",
        "gen_sim": "GENERATE NEW SIMULATION", "ai_access": "AI ACCESS LEVELS",
        "admin_title": "Omega Console — Global Administration", "admin_code": "MOD-06",
        "mrr": "ESTIMATED MRR", "paid_accounts": "PAID ACCOUNTS",
        "deployed_agents": "DEPLOYED AGENTS", "total_sessions": "TOTAL SESSIONS",
        "official_mission": "Official Mission (Auditable by Command)",
        "private_training": "Private Training (Hidden from corporate dossier)",
        "privacy_level": "Privacy Level:",
        "confirmed_credential": "CONFIRMED CREDENTIAL", "operator_data": "OPERATOR DATA",
        "identifier": "Identifier:", "unit": "Unit:", "plan": "Plan:",
        "revoke_credentials": "REVOKE CREDENTIALS",
        "access_denied_quota": "ACCESS DENIED: Monthly quota exceeded",
        "access_denied_expired": "ACCESS DENIED: License expired",
        "wrong_credentials": "Incorrect ID or password. Verify your credentials.",
        "2fa_title": "DEVICE VERIFICATION", "2fa_info": "Two-factor authentication required on first login. Check your email.",
        "verify": "VERIFY", "cancel": "CANCEL",
        "recovery_title": "ACCESS RECOVERY",
        "recovery_info": "Enter your operator ID and registered email. If they match, you'll receive a temporary password by email.",
        "send_temp": "SEND TEMPORARY KEY", "back": "BACK",
        "registered_email": "Registered Email",
        "select_access": "SELECT ACCESS LEVEL", "access_data": "ACCESS DATA",
        "entity_name": "Entity / Company Name", "personal_alias": "Alias / Personal ID",
        "contact_email": "Contact Email", "password": "Password",
        "create_pay": "CREATE ACCOUNT & GO TO PAYMENT", "create_enter": "CREATE ACCOUNT & ENTER",
        "activation_pending": "PLAN ACTIVATION PENDING",
        "go_payment": "GO TO PAYMENT —", "enter_base": "ENTER WITH BASE LEVEL",
        "invite_label": "ACTIVE ENLISTMENT ·",
        "agent_credentials": "AGENT CREDENTIALS REQUEST",
        "agent_id": "Agent Identifier (ID)", "corp_email": "Corporate Email",
        "dept": "Unit / Department", "set_key": "Set Access Key",
        "register_credentials": "REGISTER CREDENTIALS",
        "no_agents": "No active agents in this unit.",
        "describe_scenario": "Describe the tactical environment and subject type:",
        "scenario_placeholder": "E.g.: A corrupt executive trapped in a corporate negotiation. Arrogant and calculating...",
        "activate": "ACTIVATE", "active": "● ACTIVE",
        "empty_dir": "EMPTY DIRECTORY",
        "confirm_required": "CONFIRMATION REQUIRED",
        "confirm_delete_phrase": "CONFIRM DELETION",
        "write_confirm": "Type CONFIRM DELETION and press execute.",
        "execute": "EXECUTE",
        "comms_audit": "COMMUNICATIONS AUDIT",
        "identification": "IDENTIFICATION", "links": "LINKS", "clinical_state": "CLINICAL STATE",
        "secure_line": "● SECURE LINE ACTIVE:", "operator_short": "OPERATOR:", "diff_short": "DIFFICULTY:",
        "processing": "Processing linguistic audit...", "connecting": "Establishing secure connection...",
        "ai_engine": "Linking to AI engine...",
        "global_dir": "GLOBAL USER DIRECTORY", "scenario_dir": "GLOBAL SCENARIO DIRECTORY",
        "issue_credential": "ISSUE COURTESY CREDENTIAL", "activate_plan": "ACTIVATE / CHANGE PLAN",
        "generate_access": "GENERATE ACCESS", "apply_plan": "APPLY PLAN",
        "temp_license": "Temporary license (30 days)", "add_expiry": "Add expiration (30 days)",
        "format_platform": "FORMAT ENTIRE PLATFORM",
        "purge": "PURGE", "new_plan": "New Plan:", "user_label": "User:",
        "account_created": "Account created. After payment, your plan will be activated within 24h.",
        "no_users": "No registered users.", "no_scenarios": "No custom scenarios.",
        "id_label": "ID / Entity", "email_label": "Email", "role_label": "Role",
        "plan_label": "Plan", "select_role": "Select", "select_plan": "Select",
        "temp_pass_sent": "Temporary key sent to",
        "pass_updated": "Password updated successfully.",
        "account_revoked": "Operator revoked.",
        "scenario_created": "Protocol created and activated.",
        "plan_updated": "Plan updated.",
        "id_taken": "An account with that identifier already exists.",
        "fill_all": "Fill in all fields to continue.",
        "invalid_pass": "Enter a valid password.",
        "pass_mismatch": "Passwords do not match.",
        "wrong_confirm": "Incorrect phrase.",
        "wrong_code": "Incorrect code.",
        "corp_info": "Corporate accounts can add agents via invitation link.",
        "share_link": "Share this link with your agents so they join your unit automatically.",
        "quota_reached": "QUOTA REACHED",
        "no_ai_access": "RESTRICTION: BASE level does not allow Generative AI. Upgrade your plan to unlock this feature.",
        "license_no_agents": "Your license level does not allow forming squadrons. Upgrade to SQUADRON or COMMAND.",
        "irrev_action": "This action is irreversible. All data associated with your account will be deleted.",
        "destroy_all": "This action will irreversibly destroy all platform data.",
        "secure_access": "SECURE ACCESS",
        "classified": "v3.2.0 · CLASSIFIED",
        "enrollment_done": "Credential processed. Log in at the access portal.",
        "corp_accounts": "Corporate accounts can add agents via invitation link.",
        "select_operator": "Select",
        # Simulator v2
        "tactical_context": "TACTICAL CONTEXT",
        "live_feed": "LIVE COMMUNICATION FEED",
        "subject_diag": "SUBJECT DIAGNOSTICS",
        "active_negotiation": "Active Negotiation:",
        "obj1": "OBJ.1: Establish initial contact",
        "obj2": "OBJ.2: Assess demands and state",
        "obj3": "OBJ.3: Execute de-escalation protocol",
        "operator_controls": "OPERATOR CONTROLS",
        "emotional_state": "EMOTIONAL STATE",
        "response_latency": "RESPONSE LATENCY",
        "compliance_trend": "COMPLIANCE TREND",
        "analysis": "ANALYSIS",
        "status_high": "HIGH TENSION · UNSTABLE",
        "status_med": "MED TENSION · MONITOR",
        "status_low": "LOW TENSION · STABLE",
        "advice_deesc": "Prioritize information gathering. Maintain de-escalation.",
        "prev_nota": "PREVIOUS NOTA:",
        "curr_perf": "CURRENT PERFORMANCE (EST.):",
        "no_prev": "N/A",
        "btn_contact": "ESTABLISH CONTACT",
        "btn_protocol": "DEPLOY PROTOCOL ALPHA-4",
        "btn_info": "INITIATE INFO GATHERING",
        "btn_crisis": "REQUEST CRISIS TEAM SUPPORT",
        "quick_contact": "Operator on the line, here to establish direct communication.",
        "quick_protocol": "There's a protocol we can both follow. I need you to trust me.",
        "quick_info": "Before any decision, I need to understand exactly what you need.",
        "quick_crisis": "I'm contacting the support team. Please stay on the line.",
        "network_secure": "NETWORK SECURE",
        "ai_online": "AI ONLINE",
        "sys_global": "SYSTEM",
    }
}

def t(key):
    lang = st.session_state.get("lang", "es")
    return T.get(lang, T["es"]).get(key, T["es"].get(key, key))

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
# CONFIG
# ─────────────────────────────────────────
st.set_page_config(page_title="CRYSIS | Intelligence Unit", layout="wide", initial_sidebar_state="collapsed")

# ─────────────────────────────────────────
# CSS PREMIUM v2
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Condensed:wght@300;400;500;600;700;800;900&family=Barlow:wght@300;400;500;600&display=swap');

:root {
  --bg:        #04060F;
  --bg2:       #080C1A;
  --bg3:       #0C1020;
  --bg4:       #101628;
  --border:    #141C30;
  --border2:   #1E2A44;
  --border3:   #2A3A5E;
  --blue:      #4F8EF7;
  --blue2:     #3A7AE4;
  --blue-glow: rgba(79,142,247,0.18);
  --blue-dim:  rgba(79,142,247,0.08);
  --green:     #00D4A0;
  --green-dim: rgba(0,212,160,0.08);
  --red:       #E8394A;
  --red-dim:   rgba(232,57,74,0.08);
  --amber:     #F0A500;
  --amber-dim: rgba(240,165,0,0.08);
  --purple:    #A855F7;
  --text:      #8B9CC8;
  --text-hi:   #D4E0F8;
  --text-lo:   #2A3650;
  --mono:      'Share Tech Mono', monospace;
  --sans:      'Barlow', sans-serif;
  --cond:      'Barlow Condensed', sans-serif;
}

html, body, [class*="css"], .stApp {
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: var(--sans) !important;
}

.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.04) 3px, rgba(0,0,0,0.04) 4px),
    radial-gradient(ellipse at 50% 0%, rgba(79,142,247,0.04) 0%, transparent 60%);
  pointer-events: none;
  z-index: 9999;
}

header[data-testid="stHeader"] { background: var(--bg) !important; border-bottom: 1px solid var(--border); }
.stDeployButton, #MainMenu, footer { display: none !important; }

/* ── TOPBAR ── */
.topbar-wrap {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 0 10px 0; border-bottom: 1px solid var(--border); margin-bottom: 0;
}
.topbar-logo { font-family: var(--mono); font-size: 1.15rem; letter-spacing: 0.35em; color: var(--text-hi); text-shadow: 0 0 20px rgba(79,142,247,0.4); }
.topbar-logo span { color: var(--blue); }
.topbar-meta { font-family: var(--mono); font-size: 0.48rem; letter-spacing: 0.18em; color: var(--text-lo); margin-top: 2px; }

/* ── HQ HEADER ── */
.hq-header { padding: 52px 0 40px 0; text-align: center; position: relative; }
.hq-header::before { content: ''; position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 600px; height: 2px; background: linear-gradient(90deg, transparent, var(--blue), transparent); opacity: 0.4; }
.hq-label { font-family: var(--mono); font-size: 0.52rem; letter-spacing: 0.5em; color: var(--blue); margin-bottom: 14px; text-transform: uppercase; }
.hq-greeting { font-family: var(--cond); font-size: 3.2rem; font-weight: 800; color: var(--text-hi); letter-spacing: 0.08em; margin-bottom: 8px; text-transform: uppercase; text-shadow: 0 0 80px rgba(79,142,247,0.15); }
.hq-date { font-family: var(--mono); font-size: 0.55rem; letter-spacing: 0.3em; color: var(--text-lo); }

/* ── SYSTEM STATUS ── */
.sys-status { display: flex; align-items: center; justify-content: center; gap: 32px; padding: 10px 0 36px 0; }
.sys-status-item { display: flex; align-items: center; gap: 8px; font-family: var(--mono); font-size: 0.5rem; letter-spacing: 0.15em; color: var(--text-lo); }
.sys-status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); box-shadow: 0 0 6px var(--green); animation: pulse-dot 2s infinite; }
.sys-status-dot.amber { background: var(--amber); box-shadow: 0 0 6px var(--amber); }
.sys-status-dot.blue  { background: var(--blue);  box-shadow: 0 0 6px var(--blue); }
@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:0.4} }
.sys-status-val { color: var(--text); font-weight: 600; }

/* ── MODULE CARDS (clickable) ── */
.module-card {
  background: linear-gradient(135deg, var(--bg2) 0%, var(--bg3) 100%);
  border: 1px solid var(--border); border-radius: 3px; padding: 0;
  position: relative; overflow: hidden; cursor: pointer;
  transition: all 0.25s ease; min-height: 220px; display: flex; flex-direction: column;
}
.module-card:hover { border-color: var(--border2); transform: translateY(-4px); box-shadow: 0 20px 60px rgba(0,0,0,0.6), 0 0 0 1px var(--border2); }
.module-card.primary:hover { border-color: var(--blue);  box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 30px var(--blue-glow); }
.module-card.danger:hover  { border-color: var(--red);   box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 30px var(--red-dim); }
.module-card.gold:hover    { border-color: var(--amber); box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 30px var(--amber-dim); }
.module-card.admin-card:hover { border-color: var(--red); box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 30px var(--red-dim); }
.module-top-bar { height: 2px; width: 100%; background: var(--border2); transition: background 0.25s; }
.module-card.primary .module-top-bar { background: linear-gradient(90deg, var(--blue), transparent); }
.module-card.danger  .module-top-bar { background: linear-gradient(90deg, var(--red), transparent); }
.module-card.gold    .module-top-bar { background: linear-gradient(90deg, var(--amber), transparent); }
.module-card.admin-card .module-top-bar { background: linear-gradient(90deg, var(--red), var(--purple)); }
.module-body { padding: 22px 22px 0 22px; flex: 1; }
.module-chart-area { padding: 0 8px; margin-top: 4px; }
.module-footer { padding: 12px 22px 16px 22px; border-top: 1px solid var(--border); margin-top: 8px; display: flex; align-items: center; justify-content: space-between; }
.module-code { font-family: var(--mono); font-size: 0.48rem; letter-spacing: 0.3em; color: var(--text-lo); margin-bottom: 10px; }
.module-title { font-family: var(--cond); font-size: 1.15rem; font-weight: 700; color: var(--text-hi); letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 6px; }
.module-desc { font-family: var(--mono); font-size: 0.55rem; color: var(--text-lo); line-height: 1.65; letter-spacing: 0.04em; }
.module-stat-label { font-family: var(--mono); font-size: 0.48rem; letter-spacing: 0.2em; color: var(--text-lo); }
.module-stat-value { font-family: var(--cond); font-size: 1.4rem; font-weight: 700; color: var(--text-hi); letter-spacing: 0.05em; line-height: 1; }
.module-arrow { font-family: var(--mono); font-size: 0.65rem; color: var(--text-lo); opacity: 0; transform: translateX(-8px); transition: all 0.25s ease; }
.module-card:hover .module-arrow { opacity: 1; transform: translateX(0); }
.module-card.primary:hover .module-arrow { color: var(--blue); }
.module-card.danger:hover  .module-arrow { color: var(--red); }
.module-card.gold:hover    .module-arrow { color: var(--amber); }

/* Invisible click overlay button ON TOP of card */
.card-click-btn { position: relative; }
.card-click-btn .stButton > button {
  position: absolute !important; top: 0 !important; left: 0 !important;
  width: 100% !important; height: 100% !important;
  opacity: 0 !important; z-index: 20 !important;
  cursor: pointer !important; background: transparent !important;
  border: none !important; border-radius: 3px !important;
  min-height: 220px !important;
}

/* ── SECTION HEADERS ── */
.section-header { padding: 28px 0 22px 0; border-bottom: 1px solid var(--border); margin-bottom: 32px; display: flex; align-items: flex-end; justify-content: space-between; position: relative; }
.section-header::after { content: ''; position: absolute; bottom: -1px; left: 0; width: 60px; height: 2px; background: var(--blue); }
.section-title { font-family: var(--cond); font-size: 1.6rem; font-weight: 700; color: var(--text-hi); letter-spacing: 0.06em; text-transform: uppercase; }
.section-code { font-family: var(--mono); font-size: 0.48rem; letter-spacing: 0.3em; color: var(--text-lo); margin-bottom: 4px; }

/* ── METRICS ── */
.metric-card { background: linear-gradient(135deg, var(--bg2), var(--bg3)); border: 1px solid var(--border); border-radius: 3px; padding: 22px 24px; position: relative; overflow: hidden; }
.metric-card::before { content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: var(--blue); }
.metric-label { font-family: var(--mono); font-size: 0.48rem; letter-spacing: 0.22em; color: var(--blue); margin-bottom: 10px; }
.metric-value { font-family: var(--cond); font-size: 2.2rem; font-weight: 800; color: var(--text-hi); line-height: 1; letter-spacing: 0.03em; }

/* ── BRIEFING BOX ── */
.briefing-box { background: linear-gradient(135deg, var(--bg2), var(--bg3)); border: 1px solid var(--border); border-left: 3px solid var(--blue); padding: 20px 24px; border-radius: 3px; margin-bottom: 20px; position: relative; overflow: hidden; }
.briefing-box::after { content: ''; position: absolute; top: 0; right: 0; width: 120px; height: 120px; background: radial-gradient(circle at top right, var(--blue-dim), transparent); }
.briefing-box h4 { font-family: var(--mono); font-size: 0.52rem; letter-spacing: 0.22em; color: var(--blue); margin-bottom: 14px; }

/* ── SECTION LABEL ── */
.section-label { font-family: var(--mono); font-size: 0.5rem; letter-spacing: 0.28em; color: var(--blue); margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border); text-transform: uppercase; }

/* ── STATUS BAR ── */
.status-bar { background: linear-gradient(90deg, rgba(0,212,160,0.06), transparent); border: 1px solid var(--border); border-left: 3px solid var(--green); padding: 10px 18px; border-radius: 3px; font-family: var(--mono); font-size: 0.58rem; letter-spacing: 0.1em; color: var(--green); margin-bottom: 20px; }

/* ── DIFF CARDS ── */
.diff-card { border: 1px solid var(--border); border-radius: 3px; padding: 16px; cursor: pointer; transition: all 0.2s; background: var(--bg3); text-align: center; position: relative; overflow: hidden; }
.diff-card::before { content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 2px; background: transparent; transition: background 0.2s; }
.diff-card:hover { transform: translateY(-2px); }
.diff-card.selected::before { background: currentColor; }
.diff-name  { font-family: var(--cond); font-size: 0.85rem; letter-spacing: 0.15em; font-weight: 700; text-transform: uppercase; }
.diff-desc  { font-family: var(--mono); font-size: 0.5rem; color: var(--text-lo); margin-top: 8px; line-height: 1.5; }

/* ── INPUTS ── */
.stTextInput input, .stSelectbox > div > div, .stTextArea textarea { background: var(--bg3) !important; border: 1px solid var(--border2) !important; color: var(--text-hi) !important; border-radius: 2px !important; font-family: var(--sans) !important; font-size: 0.88rem !important; }
.stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--blue) !important; box-shadow: 0 0 0 3px rgba(79,142,247,0.08) !important; }
.stTextInput label, .stTextArea label, .stSelectbox label { color: var(--text-lo) !important; font-family: var(--mono) !important; font-size: 0.55rem !important; letter-spacing: 0.15em !important; }

/* ── BUTTONS ── */
.stButton > button { background: linear-gradient(135deg, var(--blue), var(--blue2)) !important; color: #fff !important; font-family: var(--cond) !important; font-size: 0.7rem !important; font-weight: 700 !important; letter-spacing: 0.2em !important; border: none !important; border-radius: 2px !important; padding: 12px 24px !important; transition: all 0.2s !important; text-transform: uppercase !important; }
.stButton > button:hover { background: linear-gradient(135deg, #5A9CF8, var(--blue)) !important; box-shadow: 0 4px 20px rgba(79,142,247,0.3) !important; transform: translateY(-1px) !important; }
button[kind="secondary"] { background: transparent !important; border: 1px solid var(--border2) !important; color: var(--text) !important; }
button[kind="secondary"]:hover { border-color: var(--blue) !important; color: var(--text-hi) !important; background: var(--blue-dim) !important; }

/* ── AUTH TIERS ── */
.auth-tier { background: var(--bg3); border: 1px solid var(--border); border-left: 3px solid var(--border2); padding: 16px 18px; border-radius: 3px; transition: border-color 0.2s; margin-bottom: 8px; }
.auth-tier:hover { border-left-color: var(--blue); }
.auth-tier.elite { border-left-color: var(--amber); }
.tier-spec { font-size: 0.72rem; color: #8B9CC8; margin-bottom: 5px; display: flex; align-items: center; }
.tier-spec::before { content: '—'; margin-right: 8px; color: var(--blue); font-size: 0.55rem; }

/* ── ALERT BOXES ── */
.alert-box { background: var(--bg3); border: 1px solid var(--border); border-left: 3px solid var(--blue); padding: 12px 16px; border-radius: 2px; margin-bottom: 14px; font-family: var(--mono); font-size: 0.58rem; color: var(--text-lo); line-height: 1.65; }
.alert-box.warning { border-left-color: var(--amber); background: rgba(240,165,0,0.03); }
.alert-box.error   { border-left-color: var(--red);   background: rgba(232,57,74,0.03); }

/* ── BRAND (LOGIN) ── */
.brand-wordmark { font-family: var(--cond); font-size: 4.5rem; font-weight: 900; letter-spacing: 0.4em; color: var(--text-hi); line-height: 1; margin-bottom: 10px; text-shadow: 0 0 80px rgba(79,142,247,0.2); text-transform: uppercase; }
.brand-sub { font-family: var(--mono); font-size: 0.52rem; letter-spacing: 0.45em; color: var(--blue); margin-bottom: 36px; }
.brand-line { width: 40px; height: 2px; background: linear-gradient(90deg, var(--blue), transparent); margin-bottom: 22px; }
.brand-desc { font-size: 0.78rem; color: var(--text-lo); line-height: 1.75; letter-spacing: 0.01em; font-family: var(--mono); }

/* ── CHAT v2 ── */
.chat-msg { display: flex; margin-bottom: 14px; }
.chat-msg.user { justify-content: flex-end; }
.chat-msg.assistant { justify-content: flex-start; }
.chat-bubble { max-width: 95%; border-radius: 3px; padding: 12px 16px; }
.chat-bubble.user { background: linear-gradient(135deg, #0D1830, #0D1424); border: 1px solid rgba(79,142,247,0.2); border-left: 3px solid var(--blue); }
.chat-bubble.assistant { background: linear-gradient(135deg, var(--bg3), var(--bg2)); border: 1px solid rgba(232,57,74,0.2); border-left: 3px solid var(--red); }
.chat-role { font-family: var(--mono); font-size: 0.48rem; letter-spacing: 0.25em; margin-bottom: 6px; }
.chat-text { color: var(--text); font-size: 0.82rem; line-height: 1.6; }

/* ── TACTICAL PANEL v2 ── */
.tac-panel {
  background: linear-gradient(135deg, var(--bg2), var(--bg3));
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 16px;
  height: 100%;
  min-height: 520px;
}
.tac-panel-header {
  font-family: var(--mono);
  font-size: 0.5rem;
  letter-spacing: 0.25em;
  color: var(--blue);
  border-bottom: 1px solid var(--border);
  padding-bottom: 10px;
  margin-bottom: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.tac-badge {
  font-family: var(--mono);
  font-size: 0.42rem;
  padding: 3px 8px;
  border-radius: 2px;
  letter-spacing: 0.1em;
}
.tac-badge.secure { background: rgba(0,212,160,0.1); color: var(--green); border: 1px solid rgba(0,212,160,0.2); }
.tac-badge.red    { background: rgba(232,57,74,0.1);  color: var(--red);   border: 1px solid rgba(232,57,74,0.2); }

/* Tactical map placeholder */
.tac-map {
  background: linear-gradient(135deg, #050812, #080D1A);
  border: 1px solid var(--border2);
  border-radius: 2px;
  height: 140px;
  position: relative;
  overflow: hidden;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.tac-map::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    repeating-linear-gradient(0deg, transparent, transparent 20px, rgba(79,142,247,0.04) 20px, rgba(79,142,247,0.04) 21px),
    repeating-linear-gradient(90deg, transparent, transparent 20px, rgba(79,142,247,0.04) 20px, rgba(79,142,247,0.04) 21px);
}
.tac-map-ping {
  width: 12px; height: 12px;
  border-radius: 50%;
  background: var(--red);
  box-shadow: 0 0 0 0 rgba(232,57,74,0.6);
  animation: radar-ping 1.5s infinite;
  position: relative; z-index: 2;
}
@keyframes radar-ping {
  0%   { box-shadow: 0 0 0 0 rgba(232,57,74,0.6); }
  70%  { box-shadow: 0 0 0 16px rgba(232,57,74,0); }
  100% { box-shadow: 0 0 0 0 rgba(232,57,74,0); }
}
.tac-map-label {
  position: absolute;
  bottom: 6px; right: 8px;
  font-family: var(--mono);
  font-size: 0.42rem;
  color: var(--text-lo);
  letter-spacing: 0.1em;
  z-index: 2;
}
.tac-obj {
  font-family: var(--mono);
  font-size: 0.52rem;
  color: var(--text-lo);
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 8px;
}
.tac-obj-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--green); flex-shrink: 0; }
.tac-obj-dot.pending { background: var(--text-lo); }

/* ── OPERATOR QUICK BUTTONS ── */
.op-btn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 8px; }
.op-btn { background: rgba(79,142,247,0.06); border: 1px solid var(--border2); border-radius: 2px; padding: 8px 10px; font-family: var(--mono); font-size: 0.46rem; letter-spacing: 0.08em; color: var(--text-lo); cursor: pointer; transition: all 0.15s; text-align: center; }
.op-btn:hover { background: rgba(79,142,247,0.12); border-color: var(--blue); color: var(--blue); }

/* ── SUBJECT DIAGNOSTICS ── */
.diag-panel { background: linear-gradient(135deg, var(--bg2), var(--bg3)); border: 1px solid var(--border); border-radius: 3px; padding: 16px; }
.diag-section { margin-bottom: 18px; }
.diag-label { font-family: var(--mono); font-size: 0.46rem; letter-spacing: 0.2em; color: var(--blue); margin-bottom: 10px; }
.diag-status-bar { height: 6px; border-radius: 1px; background: var(--border); overflow: hidden; margin-bottom: 4px; }
.diag-status-fill { height: 100%; border-radius: 1px; transition: width 0.5s ease; }
.diag-metric-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.diag-metric-name { font-family: var(--mono); font-size: 0.46rem; color: var(--text-lo); }
.diag-metric-val  { font-family: var(--cond); font-size: 0.75rem; font-weight: 700; }
.diag-analysis { background: var(--bg4); border: 1px solid var(--border); border-radius: 2px; padding: 10px 12px; margin-top: 8px; }
.diag-analysis-label { font-family: var(--mono); font-size: 0.44rem; letter-spacing: 0.18em; color: var(--amber); margin-bottom: 8px; }
.diag-analysis-item { font-family: var(--mono); font-size: 0.48rem; color: var(--text-lo); margin-bottom: 4px; padding-left: 10px; position: relative; }
.diag-analysis-item::before { content: '▸'; position: absolute; left: 0; color: var(--blue); }
.diag-score-row { display: flex; gap: 8px; margin-top: 10px; }
.diag-score-box { flex: 1; background: var(--bg3); border: 1px solid var(--border); border-radius: 2px; padding: 8px; text-align: center; }
.diag-score-label { font-family: var(--mono); font-size: 0.42rem; color: var(--text-lo); letter-spacing: 0.1em; }
.diag-score-val   { font-family: var(--cond); font-size: 1.1rem; font-weight: 700; margin-top: 2px; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--blue); }

/* ── RADIO ── */
.stRadio label { color: var(--text) !important; font-size: 0.82rem !important; }
.stRadio > div { gap: 12px !important; }

/* ── EXPANDER ── */
.streamlit-expanderHeader { background: var(--bg2) !important; border: 1px solid var(--border) !important; border-radius: 2px !important; color: var(--text) !important; font-family: var(--mono) !important; font-size: 0.6rem !important; letter-spacing: 0.1em !important; }

/* Plan cards */
.plan-card { border: 1px solid var(--border); background: var(--bg3); border-radius: 3px; padding: 12px 14px; margin-bottom: 6px; cursor: pointer; transition: all 0.15s; }
.plan-card:hover { border-color: var(--border2); }
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
PLOTLY_THEME = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Barlow Condensed', color='#4A5A7A', size=11),
    margin=dict(l=0, r=0, t=8, b=0)
)
AXIS_STYLE = dict(gridcolor='#141C30', zeroline=False, color='#2A3650', linecolor='#141C30', tickfont=dict(size=10))

# ─────────────────────────────────────────
# ESTADOS
# ─────────────────────────────────────────
datos_guardados = cargar_datos()
defaults = {
    "empleados": datos_guardados["empleados"],
    "historial_sesiones": datos_guardados["historial_sesiones"],
    "escenarios_custom": datos_guardados.get("escenarios_custom", {}),
    "mensajes": [],
    "evaluacion_actual": None,
    "mision_iniciada": False,
    "tarjeta_objetivo": None,
    "usuario_actual": None,
    "login_step": 1,
    "pantalla_actual": "menu",
    "login_modo": "acceso",
    "dificultad_actual": "OPERATOR",
    "login_subpantalla": "main",
    "lang": "es",
    "show_avatar_menu": False,
    "diagnostico_sujeto": None,
    "quick_msg": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

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
            <div class="brand-sub">{t('invite_label')} {empresa_invitada.upper()}</div>
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
                st.markdown(f"<div class='section-label'>{t('agent_credentials')}</div>", unsafe_allow_html=True)
                n     = st.text_input(t("agent_id"))
                email = st.text_input(t("corp_email"))
                d     = st.text_input(t("dept"))
                p     = st.text_input(t("set_key"), type="password")
                if st.form_submit_button(t("register_credentials"), use_container_width=True):
                    if n and p and email:
                        if any(e["Nombre"] == n and e.get("Empresa") == empresa_invitada for e in st.session_state.empleados):
                            st.warning(t("id_taken"))
                        else:
                            nuevo_agente = {"Nombre": n, "Email": email, "Departamento": d, "Rol": "Agente", "Empresa": empresa_invitada, "Password": p, "2FA_Verificado": True}
                            st.session_state.empleados.append(nuevo_agente); guardar_datos()
                            st.session_state.registro_completado = True
                            st.query_params.clear(); st.rerun()
        st.stop()

    if st.session_state.get("registro_completado"):
        st.success(t("enrollment_done"))
        st.session_state.registro_completado = False

    col_lang_top = st.columns([8,1])[1]
    with col_lang_top:
        if st.button("EN" if st.session_state.lang == "es" else "ES", key="lang_login"):
            st.session_state.lang = "en" if st.session_state.lang == "es" else "es"; st.rerun()

    col_brand, col_form = st.columns([1, 1])

    with col_brand:
        st.markdown(f"""
        <div style="padding: 80px 40px 80px 20px; min-height: 80vh; display: flex; flex-direction: column; justify-content: space-between; border-right: 1px solid var(--border);">
            <div>
                <div class="brand-wordmark">CRYSIS</div>
                <div class="brand-sub">INTELLIGENCE UNIT</div>
                <div class="brand-line"></div>
                <div class="brand-desc">{t('brand_desc')}</div>
            </div>
            <div>
                <div style="font-family:var(--mono); font-size:0.48rem; letter-spacing:0.3em; color:var(--text-lo); margin-bottom:8px;">{t('system_status')}</div>
                <div style="font-family:var(--mono); font-size:0.55rem; color:var(--green); letter-spacing:0.15em;">{t('status_ok')}</div>
                <div style="margin-top:16px; font-family:var(--mono); font-size:0.45rem; letter-spacing:0.25em; color:var(--text-lo);">{t('classified')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_form:
        st.markdown("<div style='padding: 60px 20px 60px 40px;'>", unsafe_allow_html=True)

        if st.session_state.login_subpantalla == "forgot":
            st.markdown(f"<div class='section-label'>{t('recovery_title')}</div>", unsafe_allow_html=True)
            st.markdown(f"""<div class="alert-box">{t('recovery_info')}</div>""", unsafe_allow_html=True)
            with st.form("forgot_form"):
                r_id    = st.text_input(t("operator_id"))
                r_email = st.text_input(t("registered_email"))
                col_f1, col_f2 = st.columns(2)
                enviar = col_f1.form_submit_button(t("send_temp"), use_container_width=True)
                volver = col_f2.form_submit_button(t("back"), use_container_width=True)
                if enviar:
                    agente_r = next((e for e in st.session_state.empleados if e["Nombre"] == r_id and e.get("Email","").lower() == r_email.lower()), None)
                    if agente_r:
                        nueva_pass = str(random.randint(100000, 999999))
                        ok = enviar_correo_reset(r_email, nueva_pass)
                        if ok:
                            for e in st.session_state.empleados:
                                if e["Nombre"] == r_id: e["Password"] = nueva_pass
                            guardar_datos()
                            st.success(f"{t('temp_pass_sent')} {r_email}")
                        else: st.error("Error sending email. Contact support.")
                    else: st.error("No account found with that ID and email.")
                if volver:
                    st.session_state.login_subpantalla = "main"; st.rerun()
        else:
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                if st.button(t("access"), key="modo_acceso", use_container_width=True,
                             type="primary" if st.session_state.login_modo == "acceso" else "secondary"):
                    st.session_state.login_modo = "acceso"; st.rerun()
            with col_t2:
                if st.button(t("register"), key="modo_registro", use_container_width=True,
                             type="primary" if st.session_state.login_modo == "registro" else "secondary"):
                    st.session_state.login_modo = "registro"; st.rerun()

            st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)

            if st.session_state.login_modo == "acceso":
                if st.session_state.login_step == 1:
                    with st.form("login_form"):
                        st.markdown(f"<div class='section-label'>IDENTIFICACIÓN DE OPERADOR</div>", unsafe_allow_html=True)
                        u_id   = st.text_input(t("operator_id"))
                        u_pass = st.text_input(t("security_key"), type="password")
                        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                        submitted = st.form_submit_button(t("login_btn"), use_container_width=True)
                        if submitted:
                            agente = next((e for e in st.session_state.empleados if e["Nombre"] == u_id and e.get("Password") == u_pass), None)
                            if agente:
                                expiro = False
                                if "Expiracion" in agente:
                                    fecha_exp = datetime.strptime(agente["Expiracion"], "%Y-%m-%d")
                                    if datetime.now() > fecha_exp: expiro = True
                                if expiro:
                                    st.error(f"{t('access_denied_expired')} el {agente['Expiracion']}.")
                                else:
                                    if agente.get("2FA_Verificado", False) == True or agente["Nombre"] == COMANDANTE_SUPREMO:
                                        st.session_state.usuario_actual = agente; st.session_state.pantalla_actual = "menu"; st.rerun()
                                    else:
                                        st.session_state["2fa_code"]   = str(random.randint(100000, 999999))
                                        st.session_state["2fa_agente"] = agente
                                        st.session_state.login_step = 2; st.rerun()
                            else: st.error(t("wrong_credentials"))

                    st.markdown("<div style='margin-top:10px; text-align:right;'>", unsafe_allow_html=True)
                    if st.button(t("forgot"), key="btn_forgot"):
                        st.session_state.login_subpantalla = "forgot"; st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

                elif st.session_state.login_step == 2:
                    correo_dest = st.session_state["2fa_agente"].get("Email", "Desconocido")
                    if "correo_enviado" not in st.session_state:
                        exito = enviar_correo_2fa(correo_dest, st.session_state["2fa_code"])
                        if exito: st.success(f"Code sent to: {correo_dest}")
                        else:     st.error("Secure mail system failure.")
                        st.session_state["correo_enviado"] = True
                    with st.form("2fa_form"):
                        st.markdown(f"<div class='section-label'>{t('2fa_title')}</div>", unsafe_allow_html=True)
                        st.markdown(f"""<div class="alert-box">{t('2fa_info')}</div>""", unsafe_allow_html=True)
                        u_code = st.text_input("6-digit code")
                        colA, colB = st.columns(2)
                        if colA.form_submit_button(t("verify"), use_container_width=True):
                            if u_code == st.session_state["2fa_code"]:
                                st.session_state["2fa_agente"]["2FA_Verificado"] = True; guardar_datos()
                                st.session_state.usuario_actual = st.session_state["2fa_agente"]
                                st.session_state.pantalla_actual = "menu"
                                st.session_state.login_step = 1; del st.session_state["correo_enviado"]; st.rerun()
                            else: st.error(t("wrong_code"))
                        if colB.form_submit_button(t("cancel"), use_container_width=True):
                            st.session_state.login_step = 1; del st.session_state["correo_enviado"]; st.rerun()
            else:
                if st.session_state.get("mostrar_pago"):
                    info_pago = st.session_state.mostrar_pago
                    st.markdown(f"""
                    <div style="background:var(--bg3); border:1px solid var(--amber); border-left:3px solid var(--amber); padding:20px; border-radius:3px; margin-bottom:16px;">
                        <div style="font-family:var(--mono); font-size:0.52rem; letter-spacing:0.2em; color:var(--amber); margin-bottom:10px;">{t('activation_pending')}</div>
                        <p style="color:var(--text); font-size:0.82rem; margin-bottom:14px;">{t('account_created')}</p>
                        <a href="{info_pago['link']}" target="_blank" style="display:inline-block; background:var(--amber); color:#060810; font-family:var(--cond); font-weight:700; font-size:0.7rem; letter-spacing:0.1em; padding:10px 20px; border-radius:2px; text-decoration:none;">{t('go_payment')} {info_pago['plan']}</a>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(t("enter_base"), use_container_width=True):
                        st.session_state.usuario_actual = info_pago["usuario"]
                        st.session_state.pantalla_actual = "menu"
                        del st.session_state.mostrar_pago; st.rerun()
                else:
                    st.markdown(f"<div class='section-label'>{t('select_access')}</div>", unsafe_allow_html=True)
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
                            border_col = "#F0A500" if elite and is_sel else ("#4F8EF7" if is_sel else "var(--border)")
                            bg_col     = "rgba(240,165,0,0.08)" if elite and is_sel else ("rgba(79,142,247,0.08)" if is_sel else "var(--bg3)")
                            check      = "✓ " if is_sel else ""
                            st.markdown(f"""
                            <div style="border:1px solid {border_col}; background:{bg_col}; padding:10px 14px; border-radius:2px; margin-bottom:4px;">
                                <div style="font-family:var(--mono); font-size:0.55rem; letter-spacing:0.12em; color:var(--text-hi);">{check}{nombre}</div>
                                <div style="font-family:var(--cond); font-size:1rem; color:{'#F0A500' if elite else '#4F8EF7'}; font-weight:700; margin-top:2px;">{precio}</div>
                                <div style="font-family:var(--mono); font-size:0.48rem; color:var(--text-lo); margin-top:2px;">{desc}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button("Select" if st.session_state.lang=="en" else "Seleccionar", key=f"plan_reg_{nombre}", use_container_width=True):
                                st.session_state.plan_sel_reg = nombre; st.rerun()

                    plan_sel = st.session_state.plan_sel_reg
                    es_corporativo = plan_sel in ["ESCUADRON", "COMANDANCIA"]
                    es_pago = plan_sel != "BASE"
                    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
                    with st.form("registro_form"):
                        st.markdown(f"<div class='section-label'>{t('access_data')}</div>", unsafe_allow_html=True)
                        lbl_id = t("entity_name") if es_corporativo else t("personal_alias")
                        n      = st.text_input(lbl_id)
                        email  = st.text_input(t("contact_email"))
                        p      = st.text_input(t("password"), type="password")
                        if es_corporativo:
                            st.markdown(f"""<div class="alert-box">{t('corp_info')}</div>""", unsafe_allow_html=True)
                        lbl_btn = t("create_pay") if es_pago else t("create_enter")
                        if st.form_submit_button(lbl_btn, use_container_width=True):
                            if n and p and email:
                                empresa_destino = n if es_corporativo else "Independiente"
                                if any(e["Nombre"] == n and e.get("Empresa", "Independiente") == empresa_destino for e in st.session_state.empleados):
                                    st.warning(t("id_taken"))
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
                            else: st.warning(t("fill_all"))

        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────
# PERMISOS
# ─────────────────────────────────────────
u = st.session_state.usuario_actual
_legacy = {"Gratis": "BASE", "Individual": "OPERADOR", "Pro": "ESCUADRON", "Enterprise": "COMANDANCIA"}

if u["Nombre"] == COMANDANTE_SUPREMO:
    es_empresa = True; mi_plan = "COMANDANCIA"; empresa_actual = u["Nombre"]
else:
    es_empresa = u.get("Rol") == "Empresa"
    empresa_actual = u.get("Empresa", u["Nombre"])
    if u.get("Rol") == "Agente":
        empresa_obj = next((e for e in st.session_state.empleados if e["Rol"] == "Empresa" and e["Nombre"] == empresa_actual), None)
        mi_plan = empresa_obj.get("Plan", "ESCUADRON") if empresa_obj else "ESCUADRON"
    else:
        mi_plan = u.get("Plan", "BASE")

mi_plan = _legacy.get(mi_plan, mi_plan)
ops_limite     = PLANES_INFO.get(mi_plan, {}).get("ops", 1)
escenarios_lim = PLANES_INFO.get(mi_plan, {}).get("escenarios", 0)
agentes_lim    = PLANES_INFO.get(mi_plan, {}).get("agentes", 0)

if u["Nombre"] == COMANDANTE_SUPREMO:
    historial_visible     = [s for s in st.session_state.historial_sesiones if s["Agente"] == u["Nombre"]]
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
pantalla = st.session_state.pantalla_actual
nombres_pantalla = {
    "estadisticas": t("stats_title"), "personal": t("pers_title"),
    "expedientes": t("exp_title"), "simulador": t("sim_title"),
    "sintesis": t("sint_title"), "admin": t("admin_title")
}
rol_label = ("OMNISCIENCIA GLOBAL" if u["Nombre"] == COMANDANTE_SUPREMO
             else (f"SUPERVISOR [{mi_plan}]" if es_empresa
                   else f"{t('operator_short')} {empresa_actual.upper()} [{mi_plan}]"))

initials = "".join([w[0].upper() for w in u["Nombre"].split()[:2]]) or u["Nombre"][0].upper()

top_left, top_right = st.columns([7, 1])

with top_left:
    bc_html = ""
    if pantalla != "menu":
        section_name = nombres_pantalla.get(pantalla, pantalla.upper())
        bc_html = f'<span style="display:inline-block; width:1px; height:14px; background:var(--border2); margin:0 10px; vertical-align:middle;"></span><span style="font-family:var(--mono); font-size:0.52rem; letter-spacing:0.2em; color:var(--blue);">{section_name}</span>'
    st.markdown(f"""
    <div class="topbar-wrap">
        <div>
            <div class="topbar-logo">CRY<span>SIS</span> {bc_html}</div>
            <div class="topbar-meta">{rol_label} · ID: {u['Nombre'].upper()}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_right:
    st.markdown("<div style='padding-top:8px; display:flex; gap:6px; justify-content:flex-end;'>", unsafe_allow_html=True)
    col_lang, col_av = st.columns([1,1])
    with col_lang:
        if st.button("EN" if st.session_state.lang == "es" else "ES", key="lang_topbar", type="secondary"):
            st.session_state.lang = "en" if st.session_state.lang == "es" else "es"; st.rerun()
    with col_av:
        if st.button(initials, key="avatar_btn", type="secondary"):
            st.session_state.show_avatar_menu = not st.session_state.get("show_avatar_menu", False)
            st.rerun()

    if st.session_state.get("show_avatar_menu", False):
        st.markdown(f"""
        <div style="position:absolute; right:0; top:54px; width:180px; background:var(--bg2);
                    border:1px solid var(--border2); border-radius:3px; z-index:1000;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.6);">
            <div style="padding:12px 16px; border-bottom:1px solid var(--border);">
                <div style="font-family:var(--cond); font-size:0.85rem; color:var(--text-hi); font-weight:700;">{u['Nombre'].upper()}</div>
                <div style="font-family:var(--mono); font-size:0.48rem; color:var(--blue); letter-spacing:0.15em; margin-top:2px;">{mi_plan}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        col_p, col_s, col_l = st.columns(3)
        with col_p:
            if st.button("👤", key="av_profile", help=t("profile"), type="secondary"):
                st.session_state.show_avatar_menu = False
                st.session_state.pantalla_actual = "personal"; st.rerun()
        with col_s:
            if st.button("⚙", key="av_settings", help=t("settings"), type="secondary"):
                st.session_state.show_avatar_menu = False
                st.session_state.pantalla_actual = "personal"; st.rerun()
        with col_l:
            if st.button("🚪", key="av_logout", help=t("logout"), type="secondary"):
                st.session_state.usuario_actual = None
                st.session_state.login_step = 1
                st.session_state.pantalla_actual = "menu"
                st.session_state.show_avatar_menu = False; st.rerun()

    if pantalla != "menu":
        if st.button(t("back_menu"), key="btn_menu", type="secondary", use_container_width=True):
            st.session_state.pantalla_actual = "menu"; st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

def ir_a(p):
    st.session_state.pantalla_actual = p
    st.session_state.show_avatar_menu = False
    st.rerun()

# ─────────────────────────────────────────
# MENÚ PRINCIPAL — TARJETAS CLICKABLES
# ─────────────────────────────────────────
if st.session_state.pantalla_actual == "menu":
    total_ops    = len(historial_visible)
    media_global = int(sum(s["Nota"] for s in historial_visible) / total_ops) if total_ops > 0 else 0
    ops_exitosas = sum(1 for s in historial_visible if s["Nota"] >= 80)
    tasa_exito   = int((ops_exitosas / total_ops) * 100) if total_ops > 0 else 0
    ahora        = hora_espana()
    hora_actual  = ahora.strftime("%H:%M") + " · " + ahora.strftime("%d.%m.%Y")
    mes_actual   = ahora.strftime("%Y-%m")
    ops_mes      = len([s for s in historial_visible if str(s.get("Fecha","")).startswith(mes_actual)])
    escenarios_creados = len(mis_escenarios)
    agentes_activos    = len([e for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"])

    st.markdown(f"""
    <div class="hq-header">
        <div class="hq-label">{t('hq')}</div>
        <div class="hq-greeting">{t('welcome')} {u['Nombre'].upper()}</div>
        <div class="hq-date">{hora_actual} · {t('operative')}</div>
    </div>
    <div class="sys-status">
        <div class="sys-status-item"><div class="sys-status-dot"></div> {t('network_secure')} <span class="sys-status-val">OK</span></div>
        <div class="sys-status-item"><div class="sys-status-dot blue"></div> {t('ai_online')} <span class="sys-status-val">ONLINE</span></div>
        <div class="sys-status-item"><div class="sys-status-dot amber"></div> OPS <span class="sys-status-val">{ops_mes} / {ops_limite if ops_limite < 99999 else '∞'}</span></div>
        <div class="sys-status-item"><div class="sys-status-dot"></div> AGENTS <span class="sys-status-val">{agentes_activos}</span></div>
    </div>
    """, unsafe_allow_html=True)

    def sparkline_perf(sessions, color="#4F8EF7"):
        if not sessions:
            fig = go.Figure(); fig.update_layout(**PLOTLY_THEME, height=60, xaxis=dict(visible=False), yaxis=dict(visible=False)); return fig
        notas = [s["Nota"] for s in sessions[-10:]]
        r, g, b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
        fig = go.Figure(go.Scatter(y=notas, mode='lines', line=dict(color=color, width=2), fill='tozeroy', fillcolor=f"rgba({r},{g},{b},0.08)"))
        fig.update_layout(**PLOTLY_THEME, height=60, xaxis=dict(visible=False, **AXIS_STYLE), yaxis=dict(visible=False, range=[0,105], **AXIS_STYLE))
        return fig

    def ops_barchart(sessions, color="#E8394A"):
        if not sessions:
            fig = go.Figure(); fig.update_layout(**PLOTLY_THEME, height=60, xaxis=dict(visible=False), yaxis=dict(visible=False)); return fig
        last_6 = sessions[-6:]; notas = [s["Nota"] for s in last_6]
        colors_bar = [color if n >= 70 else "#2A3650" for n in notas]
        fig = go.Figure(go.Bar(y=notas, marker=dict(color=colors_bar), width=0.6))
        fig.update_layout(**PLOTLY_THEME, height=60, xaxis=dict(visible=False), yaxis=dict(visible=False, range=[0,110]))
        return fig

    def scenario_donut(sessions):
        if not sessions:
            fig = go.Figure(); fig.update_layout(**PLOTLY_THEME, height=60); return fig
        from collections import Counter
        counts = Counter(s.get("Escenario","?") for s in sessions)
        fig = go.Figure(go.Pie(labels=list(counts.keys()), values=list(counts.values()), hole=0.7, marker=dict(colors=['#4F8EF7','#00D4A0','#F0A500','#E8394A']), textinfo='none'))
        fig.update_layout(**PLOTLY_THEME, height=60, showlegend=False)
        return fig

    def diff_radar(sessions):
        if not sessions:
            fig = go.Figure(); fig.update_layout(**PLOTLY_THEME, height=60); return fig
        diff_scores = {}
        for s in sessions:
            d = s.get("Dificultad","OPERATOR")
            if d not in diff_scores: diff_scores[d] = []
            diff_scores[d].append(s["Nota"])
        cats = list(diff_scores.keys()); vals = [int(sum(diff_scores[c])/len(diff_scores[c])) for c in cats]
        fig = go.Figure(go.Bar(x=cats, y=vals, marker=dict(color=['#00D4A0','#4F8EF7','#F0A500','#E8394A'][:len(cats)]), width=0.5))
        fig.update_layout(**PLOTLY_THEME, height=60, xaxis=dict(visible=False), yaxis=dict(visible=False, range=[0,110]))
        return fig

    # ── ROW 1: 3 cards ──
    c1, c2, c3 = st.columns(3)

    with c1:
        perf_color = "#00D4A0" if media_global >= 70 else "#E8394A"
        st.markdown(f"""
        <div class="module-card primary" style="position:relative;">
            <div class="module-top-bar"></div>
            <div class="module-body">
                <div class="module-code">{t('mod01')}</div>
                <div class="module-title">{t('mod01_title')}</div>
                <div class="module-desc">{t('mod01_desc')}</div>
            </div>
            <div class="module-chart-area" id="c_stats"></div>
            <div class="module-footer">
                <div>
                    <div class="module-stat-label">{t('mod01_stat')}</div>
                    <div class="module-stat-value" style="color:{perf_color};">{media_global}%</div>
                </div>
                <div class="module-arrow">→</div>
            </div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(sparkline_perf(historial_visible), use_container_width=True, config={"displayModeBar": False}, key="sp1")
        if st.button("→ ESTADÍSTICAS", key="nav_stats", use_container_width=True, type="secondary"):
            ir_a("estadisticas")

    with c2:
        st.markdown(f"""
        <div class="module-card danger" style="position:relative;">
            <div class="module-top-bar"></div>
            <div class="module-body">
                <div class="module-code">{t('mod02')}</div>
                <div class="module-title">{t('mod02_title')}</div>
                <div class="module-desc">{t('mod02_desc')}</div>
            </div>
            <div class="module-chart-area"></div>
            <div class="module-footer">
                <div>
                    <div class="module-stat-label">{t('mod02_stat')}</div>
                    <div class="module-stat-value">{ops_mes}</div>
                </div>
                <div class="module-arrow">→</div>
            </div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(ops_barchart(historial_visible), use_container_width=True, config={"displayModeBar": False}, key="sp2")
        if st.button("→ SIMULADOR", key="nav_sim", use_container_width=True, type="secondary"):
            ir_a("simulador")

    with c3:
        st.markdown(f"""
        <div class="module-card" style="position:relative;">
            <div class="module-top-bar"></div>
            <div class="module-body">
                <div class="module-code">{t('mod03')}</div>
                <div class="module-title">{t('mod03_title')}</div>
                <div class="module-desc">{t('mod03_desc')}</div>
            </div>
            <div class="module-chart-area"></div>
            <div class="module-footer">
                <div>
                    <div class="module-stat-label">{t('mod03_stat')}</div>
                    <div class="module-stat-value">{total_ops}</div>
                </div>
                <div class="module-arrow">→</div>
            </div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(scenario_donut(historial_visible), use_container_width=True, config={"displayModeBar": False}, key="sp3")
        if st.button("→ EXPEDIENTES", key="nav_exp", use_container_width=True, type="secondary"):
            ir_a("expedientes")

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    # ── ROW 2 ──
    if u["Nombre"] == COMANDANTE_SUPREMO:
        c4, c5, c6 = st.columns(3)
    else:
        c4, c5 = st.columns(2)

    with c4:
        st.markdown(f"""
        <div class="module-card" style="position:relative;">
            <div class="module-top-bar"></div>
            <div class="module-body">
                <div class="module-code">{t('mod04')}</div>
                <div class="module-title">{t('mod04_title')}</div>
                <div class="module-desc">{t('mod04_desc')}</div>
            </div>
            <div class="module-chart-area"></div>
            <div class="module-footer">
                <div>
                    <div class="module-stat-label">{t('mod04_stat')}</div>
                    <div class="module-stat-value">{agentes_activos}</div>
                </div>
                <div class="module-arrow">→</div>
            </div>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(diff_radar(historial_visible), use_container_width=True, config={"displayModeBar": False}, key="sp4")
        if st.button("→ PERSONAL", key="nav_pers", use_container_width=True, type="secondary"):
            ir_a("personal")

    with c5:
        st.markdown(f"""
        <div class="module-card gold" style="position:relative;">
            <div class="module-top-bar"></div>
            <div class="module-body">
                <div class="module-code">{t('mod05')}</div>
                <div class="module-title">{t('mod05_title')}</div>
                <div class="module-desc">{t('mod05_desc')}</div>
            </div>
            <div class="module-chart-area"></div>
            <div class="module-footer">
                <div>
                    <div class="module-stat-label">{t('mod05_stat')}</div>
                    <div class="module-stat-value">{escenarios_creados}</div>
                </div>
                <div class="module-arrow">→</div>
            </div>
        </div>""", unsafe_allow_html=True)
        fig_sint = go.Figure(go.Bar(y=[escenarios_creados], x=[""], marker=dict(color='#F0A500'), width=0.3))
        fig_sint.update_layout(**PLOTLY_THEME, height=60, xaxis=dict(visible=False), yaxis=dict(visible=False))
        st.plotly_chart(fig_sint, use_container_width=True, config={"displayModeBar": False}, key="sp5")
        if st.button("→ SÍNTESIS", key="nav_sint", use_container_width=True, type="secondary"):
            ir_a("sintesis")

    if u["Nombre"] == COMANDANTE_SUPREMO:
        with c6:
            _precio_plan_mrr = {"COMANDANCIA":199,"ESCUADRON":89,"ELITE":49,"OPERADOR":19,"BASE":0}
            mrr = sum(_precio_plan_mrr.get(_legacy.get(e.get("Plan","BASE"), e.get("Plan","BASE")), 0)
                      for e in st.session_state.empleados)
            st.markdown(f"""
            <div class="module-card admin-card" style="position:relative;">
                <div class="module-top-bar"></div>
                <div class="module-body">
                    <div class="module-code">{t('mod06')}</div>
                    <div class="module-title">{t('mod06_title')}</div>
                    <div class="module-desc">{t('mod06_desc')}</div>
                </div>
                <div class="module-chart-area"></div>
                <div class="module-footer">
                    <div>
                        <div class="module-stat-label">{t('mod06_stat')}</div>
                        <div class="module-stat-value" style="color:var(--amber);">{mrr}€</div>
                    </div>
                    <div class="module-arrow">→</div>
                </div>
            </div>""", unsafe_allow_html=True)
            mrr_fig = go.Figure(go.Indicator(mode="gauge", value=mrr,
                gauge=dict(axis=dict(range=[0, max(mrr*1.5, 500)], visible=False),
                           bar=dict(color="#F0A500", thickness=0.5),
                           bgcolor='rgba(0,0,0,0)', bordercolor='rgba(0,0,0,0)')))
            mrr_fig.update_layout(**PLOTLY_THEME, height=60)
            st.plotly_chart(mrr_fig, use_container_width=True, config={"displayModeBar": False}, key="sp6")
            if st.button("→ ADMIN", key="nav_admin", use_container_width=True, type="secondary"):
                ir_a("admin")

    st.stop()

# ─────────────────────────────────────────
# ESTADÍSTICAS
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "estadisticas":
    st.markdown(f"<div class='section-header'><div><div class='section-code'>{t('stats_code')}</div><div class='section-title'>{t('stats_title')}</div></div></div>", unsafe_allow_html=True)

    total_ops    = len(historial_visible)
    media_global = int(sum(s["Nota"] for s in historial_visible) / total_ops) if total_ops > 0 else 0
    ops_exitosas = sum(1 for s in historial_visible if s["Nota"] >= 80)
    tasa_exito   = int((ops_exitosas / total_ops) * 100) if total_ops > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""<div class="metric-card"><div class="metric-label">{t('avg_perf')}</div><div class="metric-value" style="color:{'#00D4A0' if media_global>=70 else '#E8394A'}">{media_global}%</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="metric-card"><div class="metric-label">{t('excellence')}</div><div class="metric-value" style="color:{'#00D4A0' if tasa_exito>=50 else '#E8394A'}">{tasa_exito}%</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="metric-card"><div class="metric-label">{t('missions')}</div><div class="metric-value" style="color:#4F8EF7">{total_ops}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if not historial_visible:
        st.markdown(f"<div style='text-align:center; padding:60px; color:var(--text-lo); font-family:var(--mono); letter-spacing:0.2em;'>{t('no_records')}</div>", unsafe_allow_html=True)
    else:
        df = pd.DataFrame(historial_visible)
        df["Nota"] = pd.to_numeric(df["Nota"])
        col_left, col_right = st.columns(2, gap="medium")
        with col_left:
            st.markdown(f"<div class='section-label'>{t('scenario_dist')}</div>", unsafe_allow_html=True)
            esc_count = df["Escenario"].value_counts().reset_index(); esc_count.columns = ["Escenario","Count"]
            fig2 = go.Figure(go.Pie(labels=esc_count["Escenario"], values=esc_count["Count"], hole=0.65, marker=dict(colors=['#4F8EF7','#00D4A0','#F0A500','#E8394A']), textfont=dict(size=11)))
            fig2.update_layout(**PLOTLY_THEME, height=300, showlegend=True, legend=dict(font=dict(size=10, color='#4A5A7A'), bgcolor='rgba(0,0,0,0)'))
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        with col_right:
            if es_empresa:
                st.markdown(f"<div class='section-label'>{t('agent_eval')}</div>", unsafe_allow_html=True)
                avg_agent = df.groupby("Agente")["Nota"].mean().reset_index()
                fig3 = go.Figure(go.Bar(x=avg_agent["Nota"], y=avg_agent["Agente"], orientation='h', marker=dict(color='#4F8EF7', opacity=0.85), text=avg_agent["Nota"].round(1), textposition='outside', textfont=dict(color='#4A5A7A', size=10)))
                fig3.update_layout(**PLOTLY_THEME, height=300, xaxis=dict(range=[0,110], **AXIS_STYLE), yaxis=dict(**AXIS_STYLE))
            else:
                st.markdown(f"<div class='section-label'>{t('perf_history')}</div>", unsafe_allow_html=True)
                df["Fecha_dt"] = pd.to_datetime(df["Fecha"]); df_sorted = df.sort_values("Fecha_dt")
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(x=df_sorted["Fecha_dt"], y=df_sorted["Nota"], mode='lines+markers', line=dict(color='#4F8EF7', width=2), marker=dict(size=6, color='#4F8EF7', line=dict(color='#0C1020', width=2)), fill='tozeroy', fillcolor='rgba(79,142,247,0.06)'))
                fig3.add_hline(y=80, line_dash="dot", line_color="#00D4A0", line_width=1, annotation_text="80%", annotation_font_color="#00D4A0", annotation_font_size=10)
                fig3.update_layout(**PLOTLY_THEME, height=300, xaxis=dict(**AXIS_STYLE), yaxis=dict(range=[0,110], **AXIS_STYLE))
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────
# PERSONAL
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "personal":
    st.markdown(f"<div class='section-header'><div><div class='section-code'>{t('pers_code')}</div><div class='section-title'>{t('pers_title')}</div></div></div>", unsafe_allow_html=True)

    if es_empresa:
        st.markdown(f"<div class='section-label'>{t('recruit_link')}</div>", unsafe_allow_html=True)
        if agentes_lim > 0 or u["Nombre"] == COMANDANTE_SUPREMO:
            token_cifrado   = base64.urlsafe_b64encode(empresa_actual.encode()).decode()
            URL_BASE_APP    = "https://crysis.streamlit.app/"
            enlace_completo = f"{URL_BASE_APP}?invite={token_cifrado}"
            st.markdown(f"""<div class="alert-box">{t('share_link')}</div>""", unsafe_allow_html=True)
            st.code(enlace_completo, language="html")
        else:
            st.markdown(f"""<div class="alert-box warning">{t('license_no_agents')}</div>""", unsafe_allow_html=True)

        st.markdown(f"<br><div class='section-label'>{t('active_roster')}</div>", unsafe_allow_html=True)
        agentes_mios = [e for e in st.session_state.empleados if e.get("Empresa") == empresa_actual and e.get("Rol") == "Agente"]
        if agentes_mios:
            for ag in agentes_mios:
                col_ag1, col_ag2 = st.columns([4, 1])
                with col_ag1:
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,var(--bg2),var(--bg3)); border:1px solid var(--border); border-radius:3px; padding:12px 16px; margin-bottom:6px; display:flex; align-items:center; gap:12px;">
                        <div style="width:32px; height:32px; border-radius:50%; background:linear-gradient(135deg,var(--blue2),var(--purple)); display:flex; align-items:center; justify-content:center; font-family:var(--cond); font-weight:700; color:#fff; font-size:0.8rem;">{ag['Nombre'][0].upper()}</div>
                        <div>
                            <div style="color:var(--text-hi); font-weight:600; font-size:0.88rem;">{ag['Nombre']}</div>
                            <div style="color:var(--text-lo); font-family:var(--mono); font-size:0.52rem; margin-top:2px;">{ag.get('Departamento','—')} · {ag['Email']}</div>
                        </div>
                    </div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander(t("revoke_access")):
                ag_a_borrar = st.selectbox(t("select_operator"), [a['Nombre'] for a in agentes_mios])
                if st.button(t("revoke_credentials"), type="primary"):
                    st.session_state.empleados = [e for e in st.session_state.empleados if e['Nombre'] != ag_a_borrar]
                    guardar_datos(); st.success(f"{t('account_revoked')} {ag_a_borrar}"); st.rerun()
        else:
            st.markdown(f"<div style='color:var(--text-lo); font-family:var(--mono); font-size:0.62rem; padding:20px 0;'>{t('no_agents')}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='section-label'>{t('confirmed_credential')}</div>", unsafe_allow_html=True)
        st.markdown(f"""<div class="briefing-box"><h4>{t('operator_data')}</h4>
        <p><b>{t('identifier')}</b> {u['Nombre']} &nbsp;|&nbsp; <b>{t('unit')}</b> {empresa_actual} &nbsp;|&nbsp; <b>{t('plan')}</b> {mi_plan}</p></div>""", unsafe_allow_html=True)

    st.markdown(f"<br><div class='section-label'>{t('account_settings')}</div>", unsafe_allow_html=True)
    with st.expander(t("change_pass")):
        nueva_pass = st.text_input(t("new_pass"), type="password", key="nueva_pass_input")
        confirmar  = st.text_input(t("confirm_pass"), type="password", key="confirmar_pass_input")
        if st.button(t("update_pass")):
            if not nueva_pass: st.warning(t("invalid_pass"))
            elif nueva_pass != confirmar: st.error(t("pass_mismatch"))
            else:
                for e in st.session_state.empleados:
                    if e["Nombre"] == u["Nombre"]: e["Password"] = nueva_pass
                st.session_state.usuario_actual["Password"] = nueva_pass
                guardar_datos(); st.success(t("pass_updated"))

    if u["Nombre"] != COMANDANTE_SUPREMO:
        st.markdown(f"<br><div class='section-label'>{t('subscription')}</div>", unsafe_allow_html=True)
        planes_suscripcion = [("OPERADOR","19€/mes","10 ops/mes · 3 esc.","OPERADOR"),("ELITE","49€/mes","Ilimitado · IA ∞","ELITE"),("ESCUADRON","89€/mes","Equipo · 15 agentes","ESCUADRON"),("COMANDANCIA","199€/mes","Enterprise · ∞","COMANDANCIA")]
        cols_plan = st.columns(4)
        for col, (nombre, precio, desc, plan_key) in zip(cols_plan, planes_suscripcion):
            with col:
                es_elite_p = plan_key in ["ELITE","ESCUADRON","COMANDANCIA"]
                color_p    = "#F0A500" if es_elite_p else "#4F8EF7"
                activo     = mi_plan == plan_key
                border_col = "#00D4A0" if activo else ("#F0A500" if es_elite_p else "var(--border)")
                st.markdown(f"""<div class="metric-card" style="border-left-color:{border_col};">
                    <div class="metric-label">{nombre}</div>
                    <div class="metric-value" style="font-size:1.1rem; color:{color_p};">{precio}</div>
                    <div style="font-family:var(--mono); font-size:0.5rem; color:var(--text-lo); margin-top:8px;">{desc}</div>
                    {'<div style="font-family:var(--mono); font-size:0.5rem; color:#00D4A0; margin-top:10px;">' + t("active") + '</div>' if activo else ''}
                </div>""", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                if not activo:
                    link = LINKS_PAGO.get(plan_key, "#")
                    st.markdown(f'<a href="{link}" target="_blank"><button style="background:linear-gradient(135deg,#4F8EF7,#3A7AE4);color:#fff;font-family:var(--cond);font-weight:700;border:none;padding:10px;border-radius:2px;cursor:pointer;width:100%;font-size:0.65rem;letter-spacing:0.1em;">{t("activate")}</button></a>', unsafe_allow_html=True)

    st.markdown(f"<br><div class='section-label'>{t('danger_zone')}</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class="alert-box error">{t('irrev_action')}</div>""", unsafe_allow_html=True)
    if st.button(t("delete_account"), type="primary"):
        if es_empresa:
            st.session_state.empleados = [e for e in st.session_state.empleados if e.get("Empresa") != u["Nombre"]]
        else:
            st.session_state.empleados = [e for e in st.session_state.empleados if e["Nombre"] != u["Nombre"]]
        st.session_state.usuario_actual = None; guardar_datos(); st.rerun()

# ─────────────────────────────────────────
# EXPEDIENTES
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "expedientes":
    st.markdown(f"<div class='section-header'><div><div class='section-code'>{t('exp_code')}</div><div class='section-title'>{t('exp_title')}</div></div></div>", unsafe_allow_html=True)

    if historial_visible:
        df_hist = pd.DataFrame(historial_visible)
        df_hist["Nota"] = pd.to_numeric(df_hist["Nota"])
        for agente, df_agente in df_hist.groupby("Agente"):
            media_agente = int(df_agente["Nota"].mean())
            with st.expander(f"{t('operator_label')} {agente.upper()}  —  {t('global_metric')} {media_agente}%", expanded=False):
                st.markdown("<br>", unsafe_allow_html=True)
                for escenario, df_op in df_agente.groupby("Escenario"):
                    media_op = int(df_op["Nota"].mean()); lbl_esc = escenario.replace("OPERACION: ","")
                    with st.expander(f"{lbl_esc}  —  {media_op}%", expanded=True):
                        for _, s in df_op.sort_values("Fecha", ascending=False).iterrows():
                            nota_ind   = s['Nota']
                            c_nota     = "#00D4A0" if nota_ind >= 80 else ("#F0A500" if nota_ind >= 50 else "#E8394A")
                            modo_badge = "PRIVADO" if s.get("Tipo_Mision") == "Personal" else "OFICIAL"
                            dif_badge  = s.get("Dificultad", "—")
                            dif_color  = DIFICULTADES.get(dif_badge, {}).get("color", "#3A4A6A")
                            puede_borrar = (s["Agente"] == u["Nombre"]) or (u["Nombre"] == COMANDANTE_SUPREMO)

                            st.markdown(f"""
                            <div style="border-bottom: 1px solid var(--border); padding: 12px 0; margin-bottom: 12px;">
                            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                                <span style="color:var(--text-lo); font-size:0.78rem; font-family:var(--mono);">
                                    {s['Fecha']} · {modo_badge} · <span style="color:{dif_color};">{dif_badge}</span>
                                </span>
                                <span style="font-family:var(--cond); color:{c_nota}; font-weight:700; font-size:1.1rem;">{nota_ind}%</span>
                            </div>
                            <div style="font-size:0.85rem; color:var(--text); margin-bottom:10px; line-height:1.6;">{s['Evaluacion']}</div>
                            """, unsafe_allow_html=True)

                            col_pdf, col_del = st.columns([3, 1])
                            with col_pdf:
                                st.download_button(label=t("extract_dossier"), data=generar_pdf_dossier(s), file_name=f"CRYSIS_{s['Agente']}_{s['Fecha'][:10]}.pdf", mime="application/pdf", key=f"pdf_{s['Agente']}_{s['Fecha']}")
                            with col_del:
                                if puede_borrar:
                                    confirm_key = f"confirm_del_{s['Agente']}_{s['Fecha']}"
                                    input_key   = f"input_del_{s['Agente']}_{s['Fecha']}"
                                    if not st.session_state.get(confirm_key, False):
                                        if st.button(t("delete"), key=f"btn_del_{s['Agente']}_{s['Fecha']}", type="secondary", use_container_width=True):
                                            st.session_state[confirm_key] = True; st.rerun()
                                    else:
                                        st.markdown(f"""<div style="background:rgba(232,57,74,0.05); border:1px solid var(--red); border-left:3px solid var(--red); padding:10px 12px; border-radius:2px; margin-bottom:6px;"><div style="font-family:var(--mono); font-size:0.48rem; letter-spacing:0.2em; color:var(--red); margin-bottom:6px;">{t('confirm_required')}</div><div style="font-family:var(--mono); font-size:0.5rem; color:var(--text-lo); line-height:1.5;">{t('write_confirm')}</div></div>""", unsafe_allow_html=True)
                                        texto_confirmacion = st.text_input("", key=input_key, placeholder=t("confirm_delete_phrase"), label_visibility="collapsed")
                                        col_conf, col_canc = st.columns(2)
                                        with col_conf:
                                            if st.button(t("execute"), key=f"exec_del_{s['Agente']}_{s['Fecha']}", use_container_width=True):
                                                phrase = "CONFIRMAR BORRADO" if st.session_state.lang == "es" else "CONFIRM DELETION"
                                                if texto_confirmacion.strip().upper() == phrase:
                                                    st.session_state.historial_sesiones = [ses for ses in st.session_state.historial_sesiones if not (ses["Agente"] == s["Agente"] and ses["Fecha"] == s["Fecha"])]
                                                    guardar_datos(); del st.session_state[confirm_key]; st.rerun()
                                                else: st.error(t("wrong_confirm"))
                                        with col_canc:
                                            if st.button(t("cancel"), key=f"canc_del_{s['Agente']}_{s['Fecha']}", use_container_width=True, type="secondary"):
                                                del st.session_state[confirm_key]; st.rerun()

                            if es_empresa and mi_plan == "COMANDANCIA" and "Transcripcion" in s:
                                st.markdown(f"<br><span style='color:var(--amber); font-size:0.6rem; font-family:var(--mono); letter-spacing:0.1em;'>{t('comms_audit')}</span>", unsafe_allow_html=True)
                                for tr in s["Transcripcion"]:
                                    ag_tr = t("operator_short")[:-1] if tr["role"] == "user" else "SUJETO"
                                    colr  = "#4F8EF7" if tr["role"] == "user" else "#E8394A"
                                    st.markdown(f"<div style='font-size:0.8rem; margin-bottom:4px;'><b style='color:{colr}'>{ag_tr}:</b> <span style='color:var(--text-lo)'>{tr['content']}</span></div>", unsafe_allow_html=True)

                            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='text-align:center; padding:60px; color:var(--text-lo); font-family:var(--mono);'>{t('empty_dir')}</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SIMULADOR TÁCTICO v2 — REDISEÑO VISUAL
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "simulador":
    st.markdown(f"<div class='section-header'><div><div class='section-code'>{t('sim_code')}</div><div class='section-title'>{t('sim_title')}</div></div></div>", unsafe_allow_html=True)

    # ── PANTALLA SETUP ──
    if not st.session_state.mision_iniciada:
        c1, c2 = st.columns(2)
        if es_empresa:
            ag_sel = c1.selectbox(t("assign_op"), agentes_de_mi_empresa)
            if ag_sel is None: ag_sel = u["Nombre"]
        else:
            ag_sel = c1.text_input(t("assign_op"), value=u["Nombre"], disabled=True)

        es_sel = c2.selectbox(t("select_proto"), list(TODAS_LAS_MISIONES.keys()))

        st.markdown(f"<br><div class='section-label'>{t('difficulty')}</div>", unsafe_allow_html=True)
        d_cols = st.columns(4)
        for i, (d_nombre, d_data) in enumerate(DIFICULTADES.items()):
            with d_cols[i]:
                is_sel_d  = st.session_state.dificultad_actual == d_nombre
                border_d  = d_data["color"] if is_sel_d else "var(--border)"
                bg_d      = f"rgba({int(d_data['color'][1:3],16)},{int(d_data['color'][3:5],16)},{int(d_data['color'][5:7],16)},0.1)" if is_sel_d else "var(--bg3)"
                st.markdown(f"""
                <div class="diff-card {'selected' if is_sel_d else ''}" style="border-color:{border_d}; background:{bg_d}; color:{d_data['color']};">
                    <div class="diff-name">{d_nombre}</div>
                    <div style="font-family:var(--mono); font-size:0.48rem; opacity:0.7; margin-top:2px; letter-spacing:0.12em;">LVL {d_data['nivel']}</div>
                    <div class="diff-desc">{d_data['desc']}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"{'▶ ' if is_sel_d else ''}{d_nombre}", key=f"diff_{d_nombre}", use_container_width=True):
                    st.session_state.dificultad_actual = d_nombre; st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        if u.get("Rol") == "Agente":
            tipo_despliegue = st.radio(t("privacy_level"), [t("official_mission"), t("private_training")], horizontal=True)
            tipo_mision_val = "Corporativa" if t("official_mission") in tipo_despliegue else "Personal"
        else:
            tipo_mision_val = "Personal"

        info = TODAS_LAS_MISIONES[es_sel]
        dif_activa = st.session_state.dificultad_actual
        dif_color  = DIFICULTADES[dif_activa]["color"]
        st.markdown(f"""
        <div class="briefing-box">
            <h4>{t('situation_report')}</h4>
            <p><b>{t('context')}</b> {info['contexto']}</p>
            <p><b>{t('target_profile')}</b> {info['perfil_sujeto']}</p>
            <p><b>{t('directive')}</b> {info['objetivo']}</p>
            <p><b>{t('diff_label')}</b> <span style="color:{dif_color}; font-family:var(--mono); font-weight:700;">{dif_activa} (Nivel {DIFICULTADES[dif_activa]['nivel']})</span></p>
        </div>
        """, unsafe_allow_html=True)

        ahora_setup  = hora_espana()
        mes_actual_s = ahora_setup.strftime("%Y-%m")
        ops_este_mes = len([s for s in st.session_state.historial_sesiones
                            if s["Agente"] == ag_sel and str(s.get("Fecha","")).startswith(mes_actual_s)])

        bloquear_inicio = False
        if mi_plan != "COMANDANCIA" and u["Nombre"] != COMANDANTE_SUPREMO:
            if ops_este_mes >= ops_limite:
                bloquear_inicio = True
                st.markdown(f"""<div class="alert-box error">{t('access_denied_quota')} ({ops_este_mes}/{ops_limite} ops).</div>""", unsafe_allow_html=True)

        if st.button(t("start_link"), use_container_width=True, disabled=bloquear_inicio):
            if GROQ_API_KEY:
                with st.spinner(t("connecting")):
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
            st.session_state.diagnostico_sujeto = None
            st.session_state.quick_msg          = None
            st.rerun()

    # ── PANTALLA EVALUACION ──
    elif st.session_state.evaluacion_actual:
        st.markdown(f"<div class='section-label'>{t('tactical_eval')}</div>", unsafe_allow_html=True)
        st.markdown(st.session_state.evaluacion_actual)
        st.markdown("<br>", unsafe_allow_html=True)
        col_end1, col_end2 = st.columns(2)
        with col_end1:
            if st.button(t("archive_report"), use_container_width=True):
                st.session_state.mision_iniciada   = False
                st.session_state.evaluacion_actual = None
                st.session_state.mensajes          = []
                st.session_state.tarjeta_objetivo  = None
                st.session_state.diagnostico_sujeto = None
                st.session_state.pantalla_actual   = "menu"
                st.rerun()
        with col_end2:
            ultima_sesion = st.session_state.historial_sesiones[-1]
            st.download_button(label=t("download_pdf"), data=generar_pdf_dossier(ultima_sesion), file_name=f"CRYSIS_{ultima_sesion['Agente']}_Report.pdf", mime="application/pdf", use_container_width=True)

    # ── PANTALLA SIMULADOR ACTIVO v2 ──
    else:
        dif_sesion  = st.session_state.get("dificultad_sesion", "OPERATOR")
        dif_color_s = DIFICULTADES.get(dif_sesion, {}).get("color","#4F8EF7")
        escenario_a = st.session_state.escenario_activo
        info_activa = TODAS_LAS_MISIONES.get(escenario_a, {})

        # Handle quick message injection
        quick_to_inject = st.session_state.get("quick_msg", None)
        if quick_to_inject:
            st.session_state.mensajes.append({"role":"user","content": quick_to_inject})
            st.session_state.quick_msg = None

        # ── 3-COLUMN LAYOUT ──
        col_left, col_center, col_right = st.columns([1, 1.6, 1], gap="small")

        # ── COL LEFT: TACTICAL CONTEXT ──
        with col_left:
            st.markdown(f"""
            <div class="tac-panel">
                <div class="tac-panel-header">
                    <span>{t('tactical_context')}</span>
                    <span class="tac-badge secure">{t('network_secure')}</span>
                </div>
                <div style="font-family:var(--mono); font-size:0.5rem; letter-spacing:0.15em; color:var(--text-lo); margin-bottom:8px;">{t('active_negotiation')}</div>
                <div style="font-family:var(--cond); font-size:0.95rem; font-weight:700; color:var(--text-hi); margin-bottom:16px;">{escenario_a.replace('OPERACION: ','')}</div>
                <div class="tac-map">
                    <div class="tac-map-ping"></div>
                    <div class="tac-map-label">GRID: {escenario_a[:3].upper()}-{random.randint(100,999) if not st.session_state.get('grid_id') else st.session_state.grid_id}</div>
                </div>
                <div style="margin-bottom:12px;">
                    <div class="tac-obj"><div class="tac-obj-dot"></div>{t('obj1')}</div>
                    <div class="tac-obj"><div class="tac-obj-dot {'pending' if len(st.session_state.mensajes) < 4 else ''}"></div>{t('obj2')}</div>
                    <div class="tac-obj"><div class="tac-obj-dot pending"></div>{t('obj3')}</div>
                </div>
                <div style="font-family:var(--mono); font-size:0.44rem; letter-spacing:0.15em; color:var(--blue); margin-bottom:8px; border-top:1px solid var(--border); padding-top:10px;">INTEL</div>
            """, unsafe_allow_html=True)

            if st.session_state.tarjeta_objetivo:
                t2 = st.session_state.tarjeta_objetivo
                st.markdown(f"""
                <div style="font-family:var(--mono); font-size:0.48rem; color:var(--text-lo); line-height:1.8;">
                    <div><span style="color:var(--amber);">{t('identification').upper()}</span></div>
                    <div style="color:var(--text-hi);">{str(t2.get('Nombre_Completo','N/A'))}</div>
                    <div style="margin-top:6px;"><span style="color:var(--amber);">{t('links').upper()}</span></div>
                    <div>{str(t2.get('Familia','N/A'))}</div>
                    <div style="margin-top:6px;"><span style="color:var(--amber);">{t('clinical_state').upper()}</span></div>
                    <div>{str(t2.get('Estado_Mental','N/A'))}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
                <div style="margin-top:14px;">
                    <div style="font-family:var(--mono); font-size:0.44rem; letter-spacing:0.15em; color:var(--blue); margin-bottom:8px; border-top:1px solid var(--border); padding-top:10px;">{t('operator_controls')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Quick action buttons
            b1, b2 = st.columns(2)
            with b1:
                if st.button(t("btn_contact"), key="qb1", use_container_width=True, type="secondary"):
                    st.session_state.quick_msg = t("quick_contact"); st.rerun()
                if st.button(t("btn_info"), key="qb3", use_container_width=True, type="secondary"):
                    st.session_state.quick_msg = t("quick_info"); st.rerun()
            with b2:
                if st.button(t("btn_protocol"), key="qb2", use_container_width=True, type="secondary"):
                    st.session_state.quick_msg = t("quick_protocol"); st.rerun()
                if st.button(t("btn_crisis"), key="qb4", use_container_width=True, type="secondary"):
                    st.session_state.quick_msg = t("quick_crisis"); st.rerun()

        # ── COL CENTER: LIVE FEED ──
        with col_center:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,var(--bg2),var(--bg3)); border:1px solid var(--border); border-radius:3px; padding:16px; min-height:520px;">
                <div class="tac-panel-header">
                    <span>{t('live_feed')}</span>
                    <span class="tac-badge red">{t('diff_short')} {dif_sesion}</span>
                </div>
            """, unsafe_allow_html=True)

            # Render messages
            for m in st.session_state.mensajes:
                label  = t("operator_short")[:-1] if m["role"] == "user" else "SUJETO"
                bubble_class = "user" if m["role"] == "user" else "assistant"
                role_color = "#4F8EF7" if m["role"] == "user" else "#E8394A"
                st.markdown(f"""
                <div class="chat-msg {bubble_class}">
                    <div class="chat-bubble {bubble_class}">
                        <div class="chat-role" style="color:{role_color};">{label}</div>
                        <div class="chat-text">{m['content']}</div>
                    </div>
                </div>""", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # Chat input
            if prompt := st.chat_input(t("chat_placeholder")):
                st.session_state.mensajes.append({"role":"user","content":prompt})
                st.session_state.quick_msg = None
                st.rerun()

            # Control row
            col_abort, col_eval = st.columns([1, 2])
            with col_abort:
                if st.button(t("break_link"), type="secondary", use_container_width=True):
                    st.session_state.mision_iniciada  = False
                    st.session_state.mensajes         = []
                    st.session_state.tarjeta_objetivo = None
                    st.session_state.diagnostico_sujeto = None
                    st.rerun()
            with col_eval:
                if len(st.session_state.mensajes) > 0:
                    if st.button(t("request_eval"), use_container_width=True):
                        with st.spinner(t("processing")):
                            client    = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                            info_ev   = TODAS_LAS_MISIONES[escenario_a]
                            dif_ev    = st.session_state.get("dificultad_sesion","OPERATOR")
                            dif_nivel = DIFICULTADES.get(dif_ev,{}).get("nivel",2)
                            hist_txt  = "\n".join([f"{'OPERADOR' if m['role']=='user' else 'SUJETO'}: {m['content']}" for m in st.session_state.mensajes])
                            umbral_excelente = {1:85, 2:80, 3:70, 4:60}.get(dif_nivel, 80)
                            umbral_correcto  = {1:65, 2:55, 3:45, 4:35}.get(dif_nivel, 55)
                            eval_prompt = f"""Eres un Analista de Inteligencia y Negociación Táctica altamente estricto.
Evalúa el desempeño del OPERADOR en el escenario: {escenario_a}.
Situación: {info_ev['contexto']}.
Dificultad seleccionada: {dif_ev} (Nivel {dif_nivel}/4).
AJUSTE POR DIFICULTAD: En nivel {dif_ev}, una puntuación de {umbral_excelente} o más es EXCELENTE.
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
                            ahora_eval = hora_espana()
                            st.session_state.historial_sesiones.append({
                                "Fecha":        ahora_eval.strftime("%Y-%m-%d %H:%M"),
                                "Agente":       st.session_state.agente_activo,
                                "Escenario":    escenario_a,
                                "Nota":         nota,
                                "Evaluacion":   informe,
                                "Transcripcion": st.session_state.mensajes,
                                "Tipo_Mision":  st.session_state.tipo_mision_actual,
                                "Dificultad":   dif_ev,
                            })
                            guardar_datos(); st.rerun()

        # ── COL RIGHT: SUBJECT DIAGNOSTICS ──
        with col_right:
            # Generate or update diagnostics after each AI response
            msgs = st.session_state.mensajes
            last_assistant = next((m["content"] for m in reversed(msgs) if m["role"] == "assistant"), None)

            # Compute diagnostic metrics from conversation state
            n_msgs = len(msgs)
            n_user = sum(1 for m in msgs if m["role"] == "user")
            n_asst = sum(1 for m in msgs if m["role"] == "assistant")

            # Heuristic: tension based on difficulty + message count
            dif_nivel_s = DIFICULTADES.get(dif_sesion, {}).get("nivel", 2)
            base_tension = {1: 20, 2: 45, 3: 65, 4: 85}.get(dif_nivel_s, 45)

            # Pull from stored diagnostics if available
            diag = st.session_state.get("diagnostico_sujeto") or {}
            agitation_val   = diag.get("agitation", min(base_tension + random.randint(-5,5), 100))
            index_val       = diag.get("index",     min(50 + random.randint(-10,10), 100))
            high_val        = diag.get("high",      min(base_tension + random.randint(0,15), 100))
            receptivity_val = diag.get("receptivity", max(100 - base_tension + random.randint(-10,10), 0))
            rating_val      = diag.get("rating",    max(100 - base_tension + random.randint(-5,5), 0))
            compliance_val  = diag.get("compliance", max(100 - base_tension + random.randint(-15,5), 0))
            latency_val     = diag.get("latency",   random.randint(20,80))

            # Re-generate diagnostics via AI if there is a new assistant message
            if last_assistant and GROQ_API_KEY and n_asst > 0:
                diag_key = f"diag_msg_{n_asst}"
                if not st.session_state.get(diag_key):
                    try:
                        client_d = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                        diag_prompt = f"""Analiza el último mensaje del sujeto y devuelve EXCLUSIVAMENTE JSON con estas claves numéricas de 0 a 100:
'agitation' (agitación), 'index' (índice de riesgo), 'high' (hostilidad), 'receptivity' (receptividad al diálogo), 'rating' (evaluación general positiva), 'compliance' (tendencia a ceder), 'latency' (velocidad de respuesta percibida).
Último mensaje del sujeto: "{last_assistant[:300]}"
Dificultad base: {dif_sesion} (nivel {dif_nivel_s}/4). Ajusta según el tono del mensaje."""
                        diag_res = client_d.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role":"user","content": diag_prompt}],
                            response_format={"type":"json_object"},
                            max_tokens=200
                        ).choices[0].message.content
                        new_diag = json.loads(diag_res)
                        st.session_state.diagnostico_sujeto = new_diag
                        st.session_state[diag_key] = True
                        agitation_val   = new_diag.get("agitation",   agitation_val)
                        index_val       = new_diag.get("index",       index_val)
                        high_val        = new_diag.get("high",        high_val)
                        receptivity_val = new_diag.get("receptivity", receptivity_val)
                        rating_val      = new_diag.get("rating",      rating_val)
                        compliance_val  = new_diag.get("compliance",  compliance_val)
                        latency_val     = new_diag.get("latency",     latency_val)
                    except:
                        pass

            # Determine status
            mean_tension = (agitation_val + high_val) / 2
            if mean_tension >= 65:
                status_text  = t("status_high")
                status_color = "#E8394A"
            elif mean_tension >= 40:
                status_text  = t("status_med")
                status_color = "#F0A500"
            else:
                status_text  = t("status_low")
                status_color = "#00D4A0"

            # Last known score
            prev_nota = historial_visible[-1]["Nota"] if historial_visible else None
            curr_est  = max(0, 100 - int(mean_tension * 0.6)) if n_asst > 0 else "—"

            def bar_color(val):
                if val >= 70: return "#E8394A"
                elif val >= 40: return "#F0A500"
                return "#00D4A0"

            def bar_color_pos(val):
                if val >= 70: return "#00D4A0"
                elif val >= 40: return "#F0A500"
                return "#E8394A"

            st.markdown(f"""
            <div class="diag-panel">
                <div class="tac-panel-header">
                    <span>{t('subject_diag')}</span>
                    <span class="tac-badge" style="background:rgba({int(status_color[1:3],16)},{int(status_color[3:5],16)},{int(status_color[5:7],16)},0.1); color:{status_color}; border:1px solid {status_color}40;">LIVE</span>
                </div>

                <div class="diag-section">
                    <div class="diag-label">{t('emotional_state')}</div>
                    <div class="diag-metric-row">
                        <span class="diag-metric-name">Agitation</span>
                        <span class="diag-metric-val" style="color:{bar_color(agitation_val)};">{agitation_val}</span>
                    </div>
                    <div class="diag-status-bar"><div class="diag-status-fill" style="width:{agitation_val}%; background:{bar_color(agitation_val)};"></div></div>
                    <div class="diag-metric-row" style="margin-top:6px;">
                        <span class="diag-metric-name">Index</span>
                        <span class="diag-metric-val" style="color:{bar_color(index_val)};">{index_val}</span>
                    </div>
                    <div class="diag-status-bar"><div class="diag-status-fill" style="width:{index_val}%; background:{bar_color(index_val)};"></div></div>
                    <div class="diag-metric-row" style="margin-top:6px;">
                        <span class="diag-metric-name">High</span>
                        <span class="diag-metric-val" style="color:{bar_color(high_val)};">{high_val}</span>
                    </div>
                    <div class="diag-status-bar"><div class="diag-status-fill" style="width:{high_val}%; background:{bar_color(high_val)};"></div></div>
                </div>

                <div class="diag-section">
                    <div class="diag-label">{t('response_latency')}</div>
                    <div class="diag-metric-row">
                        <span class="diag-metric-name">Receptiveness</span>
                        <span class="diag-metric-val" style="color:{bar_color_pos(receptivity_val)};">{receptivity_val}</span>
                    </div>
                    <div class="diag-status-bar"><div class="diag-status-fill" style="width:{receptivity_val}%; background:{bar_color_pos(receptivity_val)};"></div></div>
                    <div class="diag-metric-row" style="margin-top:6px;">
                        <span class="diag-metric-name">Rating</span>
                        <span class="diag-metric-val" style="color:{bar_color_pos(rating_val)};">{rating_val}</span>
                    </div>
                    <div class="diag-status-bar"><div class="diag-status-fill" style="width:{rating_val}%; background:{bar_color_pos(rating_val)};"></div></div>
                </div>

                <div class="diag-section">
                    <div class="diag-label">{t('compliance_trend')}</div>
                    <div class="diag-metric-row">
                        <span class="diag-metric-name">Compromise Extent</span>
                        <span class="diag-metric-val" style="color:{bar_color_pos(compliance_val)};">{compliance_val}</span>
                    </div>
                    <div class="diag-status-bar"><div class="diag-status-fill" style="width:{compliance_val}%; background:{bar_color_pos(compliance_val)};"></div></div>
                </div>

                <div class="diag-analysis">
                    <div class="diag-analysis-label">{t('analysis')}</div>
                    <div class="diag-analysis-item">STATUS: <span style="color:{status_color};">{status_text}</span></div>
                    <div class="diag-analysis-item">{t('advice_deesc')}</div>
                </div>

                <div class="diag-score-row">
                    <div class="diag-score-box">
                        <div class="diag-score-label">{t('prev_nota')}</div>
                        <div class="diag-score-val" style="color:#4F8EF7;">{prev_nota if prev_nota else t('no_prev')}</div>
                    </div>
                    <div class="diag-score-box">
                        <div class="diag-score-label">{t('curr_perf')}</div>
                        <div class="diag-score-val" style="color:#00D4A0;">{curr_est}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── AI RESPONSE (triggers after user message) ──
        if st.session_state.mensajes and st.session_state.mensajes[-1]["role"] == "user":
            if GROQ_API_KEY:
                with st.spinner(t("ai_engine")):
                    client_r    = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                    base_prompt = TODAS_LAS_MISIONES[escenario_a]["prompt"]
                    dif_instruc = DIFICULTADES.get(dif_sesion, {}).get("instruccion","")
                    base_prompt += f"\n\n[NIVEL DE DIFICULTAD: {dif_sesion}. {dif_instruc}]"
                    if st.session_state.tarjeta_objetivo:
                        t3 = st.session_state.tarjeta_objetivo
                        base_prompt += f"\n\n[Tu nombre es {t3.get('Nombre_Completo')}. Familia: {t3.get('Familia')}. Estado: {t3.get('Estado_Mental')}.]"
                    res = client_r.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role":"system","content": base_prompt}] + st.session_state.mensajes
                    ).choices[0].message.content
                    st.session_state.mensajes.append({"role":"assistant","content":res})
                    st.rerun()

# ─────────────────────────────────────────
# SÍNTESIS IA
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "sintesis":
    st.markdown(f"<div class='section-header'><div><div class='section-code'>{t('sint_code')}</div><div class='section-title'>{t('sint_title')}</div></div></div>", unsafe_allow_html=True)

    col_izq, col_der = st.columns([2, 1], gap="large")
    with col_izq:
        creados = len(mis_escenarios)
        if mis_escenarios:
            st.markdown(f"<div class='section-label'>{t('active_scenarios')}</div>", unsafe_allow_html=True)
            for nombre_esc, datos_esc in mis_escenarios.items():
                c_esc1, c_esc2 = st.columns([3, 1])
                c_esc1.markdown(f"""<div style="background:linear-gradient(135deg,var(--bg2),var(--bg3)); border:1px solid var(--border); border-radius:3px; padding:12px 16px; margin-bottom:4px;"><span style="color:var(--text-hi); font-size:0.88rem; font-weight:600;">{nombre_esc}</span><span style="color:var(--text-lo); font-family:var(--mono); font-size:0.5rem; margin-left:10px;">Creator: {datos_esc.get('Creador','—')}</span></div>""", unsafe_allow_html=True)
                if c_esc2.button(t("delete"), key=f"del_{nombre_esc}", type="secondary"):
                    del st.session_state.escenarios_custom[nombre_esc]; guardar_datos(); st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(f"<div class='section-label'>{t('new_sim')}</div>", unsafe_allow_html=True)

        if mi_plan == "BASE" and u["Nombre"] != COMANDANTE_SUPREMO:
            st.markdown(f"""<div class="alert-box error">{t('no_ai_access')}</div>""", unsafe_allow_html=True)
        else:
            limite_esc = 99999 if u["Nombre"] == COMANDANTE_SUPREMO else escenarios_lim
            if limite_esc != 99999 and creados >= limite_esc:
                st.markdown(f"""<div class="alert-box warning">{t('quota_reached')} ({creados}/{limite_esc}).</div>""", unsafe_allow_html=True)
            else:
                idea_prompt = st.text_area(t("describe_scenario"), height=100, placeholder=t("scenario_placeholder"))
                if st.button(t("gen_sim"), use_container_width=True):
                    if idea_prompt and GROQ_API_KEY:
                        with st.spinner(t("ai_engine")):
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
                                guardar_datos(); st.success(f"{t('scenario_created')} {nuevo_esc['nombre_op']}"); st.rerun()
                            except Exception as e:
                                st.error(f"AI Engine Failure: {e}")
                    elif not idea_prompt:
                        st.warning(t("fill_all"))

    with col_der:
        st.markdown(f"<div class='section-label'>{t('ai_access')}</div>", unsafe_allow_html=True)
        planes_der = [
            ("BASE",        "0€",     False, ["No AI generativa", "1 op/mes"]),
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
                <div style="display:flex;justify-content:space-between;margin-bottom:6px;border-bottom:1px solid var(--border);padding-bottom:6px;">
                    <span style="font-family:var(--mono);font-size:0.6rem;color:{'#00D4A0' if activo else 'var(--text-hi)'};">{'● ' if activo else ''}{nombre}</span>
                    <span style="font-family:var(--cond);font-size:0.85rem;color:{color};font-weight:700;">{precio}</span>
                </div>
                {''.join(f'<div class="tier-spec">{s}</div>' for s in specs)}
            </div>
            """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# ADMIN — CONSOLA OMEGA
# ─────────────────────────────────────────
elif st.session_state.pantalla_actual == "admin" and u["Nombre"] == COMANDANTE_SUPREMO:
    st.markdown(f"<div class='section-header'><div><div class='section-code'>{t('admin_code')}</div><div class='section-title'>{t('admin_title')}</div></div></div>", unsafe_allow_html=True)

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
    col_m1.markdown(f"""<div class="metric-card" style="border-left-color:var(--amber);"><div class="metric-label" style="color:var(--amber);">{t('mrr')}</div><div class="metric-value" style="color:var(--amber);">{mrr_estimado}€</div></div>""", unsafe_allow_html=True)
    col_m2.markdown(f"""<div class="metric-card"><div class="metric-label">{t('paid_accounts')}</div><div class="metric-value">{total_enterprise+total_escuadron+total_elite+total_operador}</div></div>""", unsafe_allow_html=True)
    col_m3.markdown(f"""<div class="metric-card"><div class="metric-label">{t('deployed_agents')}</div><div class="metric-value">{total_agentes}</div></div>""", unsafe_allow_html=True)
    col_m4.markdown(f"""<div class="metric-card"><div class="metric-label">{t('total_sessions')}</div><div class="metric-value">{len(st.session_state.historial_sesiones)}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_adm1, col_adm2 = st.columns(2, gap="large")

    with col_adm1:
        with st.expander(t("global_dir"), expanded=False):
            for i, usr in enumerate(st.session_state.empleados):
                if usr["Nombre"] != COMANDANTE_SUPREMO:
                    c_u1, c_u2 = st.columns([4, 1])
                    plan_disp = _legacy.get(usr.get("Plan","BASE"), usr.get("Plan","BASE"))
                    c_u1.markdown(f"**{usr['Nombre']}** | {usr['Rol']} | {usr['Email']} | {plan_disp}")
                    if c_u2.button(t("purge"), key=f"del_g_{usr['Nombre']}_{i}", type="secondary"):
                        st.session_state.empleados = [e for e in st.session_state.empleados if not (e["Nombre"] == usr["Nombre"] and e.get("Rol") == usr.get("Rol") and e.get("Empresa") == usr.get("Empresa"))]
                        guardar_datos(); st.rerun()

        with st.expander(t("scenario_dir"), expanded=False):
            if not st.session_state.escenarios_custom:
                st.markdown(t("no_scenarios"))
            for n_esc, d_esc in list(st.session_state.escenarios_custom.items()):
                c_e1, c_e2 = st.columns([4, 1])
                c_e1.markdown(f"**{n_esc}** | Creator: {d_esc.get('Creador','—')}")
                if c_e2.button(t("delete"), key=f"del_g_esc_{n_esc}", type="secondary"):
                    del st.session_state.escenarios_custom[n_esc]; guardar_datos(); st.rerun()

    with col_adm2:
        with st.expander(t("issue_credential"), expanded=True):
            with st.form("admin_create_user"):
                new_n     = st.text_input(t("id_label"),    key="admin_new_n")
                new_email = st.text_input(t("email_label"), key="admin_new_email")
                new_pass  = st.text_input(t("password"), type="password", key="admin_new_pass")
                new_rol   = st.selectbox(t("role_label"), ["Individual","Empresa"], key="admin_new_rol")
                new_plan  = st.selectbox(t("plan_label"), ["BASE","OPERADOR","ELITE","ESCUADRON","COMANDANCIA"], key="admin_new_plan")
                expira    = st.checkbox(t("temp_license"), value=False, key="admin_expira")
                if st.form_submit_button(t("generate_access"), use_container_width=True):
                    if new_n and new_email and new_pass:
                        if any(e["Nombre"] == new_n for e in st.session_state.empleados):
                            st.warning(t("id_taken"))
                        else:
                            fecha_exp_str = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d") if expira else None
                            nuevo_u = {"Nombre": new_n, "Email": new_email, "Rol": new_rol, "Plan": new_plan, "Empresa": new_n, "Password": new_pass, "2FA_Verificado": True}
                            if new_rol == "Empresa": nuevo_u["Departamento"] = "Administración"
                            if fecha_exp_str: nuevo_u["Expiracion"] = fecha_exp_str
                            st.session_state.empleados.append(nuevo_u); guardar_datos()
                            st.success(f"Account '{new_n}' created."); st.rerun()
                    else: st.warning(t("fill_all"))

        with st.expander(t("activate_plan"), expanded=True):
            usuarios_no_admin = [e for e in st.session_state.empleados if e["Nombre"] != COMANDANTE_SUPREMO]
            if usuarios_no_admin:
                opciones_labels = [f"{e['Nombre']} [{e.get('Rol','?')}] — {_legacy.get(e.get('Plan','BASE'), e.get('Plan','BASE'))}" for e in usuarios_no_admin]
                sel_idx = st.selectbox(t("user_label"), range(len(opciones_labels)), format_func=lambda i: opciones_labels[i], key="admin_sel_usuario_v2")
                nuevo_plan_upg = st.selectbox(t("new_plan"), ["BASE","OPERADOR","ELITE","ESCUADRON","COMANDANCIA"], key="admin_nuevo_plan_v2")
                nueva_exp2 = st.checkbox(t("add_expiry"), value=False, key="admin_exp_check_v2")
                if st.button(t("apply_plan"), use_container_width=True, key="btn_aplicar_plan_v2"):
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
                        guardar_datos(); st.success(f"{t('plan_updated')} '{nombre_target}' → {nuevo_plan_upg}."); st.rerun()
                    else: st.error("User not found.")
            else:
                st.info(t("no_users"))

    st.markdown(f"<br><div class='section-label'>{t('danger_zone')}</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class="alert-box error">{t('destroy_all')}</div>""", unsafe_allow_html=True)
    if st.button(t("format_platform"), use_container_width=True, key="btn_formatear"):
        st.session_state.empleados          = []
        st.session_state.historial_sesiones = []
        st.session_state.escenarios_custom  = {}
        st.session_state.usuario_actual     = None
        guardar_datos(); st.rerun()

import io
import json
from pathlib import Path
from typing import List

import streamlit as st
import qrcode

from app_utils_core import (
    # Solo necesitamos web, waze, apple.
    build_gmaps_web_url, 
    build_waze_url, 
    build_apple_maps_url,
    resolve_selection,
    # Comentar o eliminar las líneas de deep-link si ya no están en app_utils_core.py
    # build_gmaps_app_link_navigation, 
    # build_gmaps_android_intent_url, 
    # build_gmaps_ios_comgooglemaps,
)

# Definición base para la carpeta de rutas
ROUTES_DIR = Path(".streamlit")
ROUTES_DIR.mkdir(parents=True, exist_ok=True)

MAX_POINTS = 10


# ---------------------------
# Estado
# ---------------------------
def _get_user_routes_path():
    """Devuelve el objeto Path del archivo de rutas del usuario logeado."""
    username = st.session_state.get('username', 'default')
    return ROUTES_DIR / f"routes_{username}.json"

def _load_routes_file():
    """Carga las rutas del archivo específico del usuario."""
    routes_db_path = _get_user_routes_path()
    try:
        if routes_db_path.exists():
            return json.loads(routes_db_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _persist_routes_file():
    """Guarda las rutas en el archivo específico del usuario."""
    routes_db_path = _get_user_routes_path()
    try:
        routes_db_path.write_text(
            json.dumps(st.session_state["saved_routes"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _bump_list_version():
    st.session_state["list_version"] += 1


# ---------------------------
# Acciones lista
# ---------------------------
def _add_point(val: str):
    ss = st.session_state
    val = (val or "").strip()
    if not val:
        return
    if len(ss["prof_points"]) >= MAX_POINTS:
        st.warning(f"Límite de {MAX_POINTS} puntos.")
        return
    ss["prof_points"].append(val)
    
    # === CORRECCIÓN: LIMPIAR EL INPUT ===
    if "prof_text_input" in ss:
        del ss["prof_text_input"]
    # ==================================
    
    _bump_list_version()
    st.rerun()


def _clear_points():
    ss = st.session_state
    ss["prof_points"] = []
    ss["last_gmaps_url"] = None
    if "prof_text_input" in ss:
        del ss["prof_text_input"]
    _bump_list_version()
    st.rerun()


def _move_point_up(i: int):
    pts = st.session_state["prof_points"]
    if i > 0:
        pts[i-1], pts[i] = pts[i], pts[i-1]
        _bump_list_version()
    st.rerun()


def _move_point_down(i: int):
    pts = st.session_state["prof_points"]
    if i < len(pts) - 1:
        # CORRECCIÓN: el swap estaba incorrecto, debe ser i+1, i
        pts[i+1], pts[i] = pts[i], pts[i+1]
        _bump_list_version()
    st.rerun()


def _delete_point(i: int):
    pts = st.session_state["prof_points"]
    if 0 <= i < len(pts):
        pts.pop(i)
        _bump_list_version()
    st.rerun()


# ---------------------------
# Guardar / cargar (con sobrescritura)
# ---------------------------
def _save_current_route():
    ss = st.session_state
    name = (ss.get("route_name_input") or "").strip()
    if not name:
        st.warning("Pon un nombre para guardar la ruta.")
        return
    if len(ss["prof_points"]) < 1:
        st.warning("No hay puntos para guardar.")
        return

    if name in ss["saved_routes"] and ss.get("ow_pending") != name:
        ss["ow_pending"] = name
        st.rerun()
        return

    ss["saved_routes"][name] = list(ss["prof_points"])
    _persist_routes_file()
    ss["saved_choice"] = name
    ss["ow_pending"] = None
    st.success("Ruta guardada ✅")


def _confirm_overwrite(ok: bool):
    ss = st.session_state
    name = ss.get("ow_pending")
    if not name:
        return
    if ok:
        ss["saved_routes"][name] = list(ss["prof_points"])
        _persist_routes_file()
        ss["saved_choice"] = name
        st.success("Ruta sobrescrita ✅")
    ss["ow_pending"] = None
    st.rerun()


def _load_route(name: str):
    ss = st.session_state
    if not name:
        return
    data = ss["saved_routes"].get(name)
    if data is None:
        return
    
    # === CORRECCIÓN DE LIMPIEZA ===
    cleaned_data = []
    for item in data:
        s = str(item).strip()
        if s: 
            cleaned_data.append(s)
            
    ss["prof_points"] = cleaned_data
    # ==============================
    
    ss["route_name_input"] = name
    _bump_list_version()


def _delete_saved_route(name: str):
    ss = st.session_state
    if name and name in ss["saved_routes"]:
        del ss["saved_routes"][name]
        _persist_routes_file()
        ss["saved_choice"] = ""
        st.success("Ruta borrada 🗑️")
        st.rerun()


# ---------------------------
# QR helper
# ---------------------------
def _qr_image_for(url: str):
    qr = qrcode.QRCode(version=2, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ---------------------------
# Componentes de diseño (Estilo Retool)
# ---------------------------

def _add_direction_container():
    st.subheader("Agregar Dirección")
    with st.form("add_form", clear_on_submit=False):
        st.text_input(
            "Dirección",
            key="prof_text_input",
            placeholder="Ingrese una dirección...",
            label_visibility="visible"
        )
        st.checkbox(
            "Optimizar ruta",
            value=st.session_state.get("optimize_route", False),
            key="optimize_route",
        )
        submitted = st.form_submit_button("Agregar", type="primary", use_container_width=True)
    if submitted:
        _add_point(st.session_state.get("prof_text_input"))


def _list_col():
    ss = st.session_state
    
    pts: List[str] = ss.get("prof_points", [])
    if not pts:
        st.info("Añade al menos dos puntos (origen y destino).")
    else:
        ver = ss.get("list_version", 0)
        for i, p in enumerate(pts):
            # Usamos las columnas [Indice, Campo, Botones]
            row = st.columns([1, 8, 3]) 
            
            with row[0]:
                st.markdown(f"**{i+1}.**") # Añadimos el índice
            
            with row[1]:
                st.text_input(
                    f"Punto {i+1}: {p}",
                    value=str(p) if p is not None else "",
                    key=f"pt_{ver}_{i}",
                    disabled=True,
                    label_visibility="collapsed",
                )
            
            with row[2]:
                col_btn = st.columns(3)  
                
                with col_btn[0]:
                    st.button("✖", key=f"del_{ver}_{i}", on_click=_delete_point, args=(i,), use_container_width=True)
                with col_btn[1]:
                    st.button("▲", key=f"up_{ver}_{i}", on_click=_move_point_up, args=(i,), use_container_width=True,
                              disabled=(i==0))
                with col_btn[2]:
                    st.button("▼", key=f"dn_{ver}_{i}", on_click=_move_point_down, args=(i,), use_container_width=True,
                              disabled=(i==len(pts)-1))


def _save_load_col():
    ss = st.session_state
    
    col_name, col_status = st.columns([7, 3])
    with col_name:
        st.text_input("Nombre de ruta", key="route_name_input", placeholder="Ej. Reparto Lunes mañana", label_visibility="collapsed")
    with col_status:
        # Esto es un placeholder que necesitaría lógica para mostrar el estado real de la ruta guardada
        st.selectbox("Ruta actual", options=["Entrega Centro", "Sin guardar"], key="route_status_display", disabled=True, label_visibility="collapsed")
    
    c1, c2, c3 = st.columns(3)
    with c1: st.button("Crear ruta", on_click=_save_current_route, use_container_width=True)
    with c2: st.button("Guardar Cambios", on_click=_save_current_route, use_container_width=True)
    with c3: st.button("Eliminar ruta", on_click=lambda: _delete_saved_route(st.session_state.get("saved_choice")), use_container_width=True)

    # Aviso de sobrescritura (si aplica)
    if st.session_state.get("ow_pending"):
        st.warning(f"La ruta «{st.session_state['ow_pending']}» ya existe. ¿Sobrescribir?")
        cA, cB = st.columns(2)
        with cA:
            st.button("✅ Sí, sobrescribir", on_click=_confirm_overwrite, args=(True,), use_container_width=True)
        with cB:
            st.button("❌ Cancelar", on_click=_confirm_overwrite, args=(False,), use_container_width=True)


# ---------------------------
# Generar y salidas
# ---------------------------
def _build_and_show_outputs():
    ss = st.session_state
    
    # Inicialización de variables
    o_meta = None
    d_meta = None

    pts = ss["prof_points"]
    if len(pts) < 2:
        st.warning("Añade origen y destino (mínimo 2 puntos).")
        return 
        
    o_text = pts[0]
    d_text = pts[-1]
    w_texts = pts[1:-1]

    o_meta = resolve_selection(o_text, None)
    d_meta = resolve_selection(d_text, None)
    waypoints_meta = [resolve_selection(w, None) for w in w_texts]

    optimize_flag = ss.get('optimize_route', False)
    
    # === GENERACIÓN DE URLS ===
    # Usamos la URL web estándar que el móvil puede interceptar.
    
    gmaps_web = build_gmaps_web_url(
        o_meta, d_meta, 
        waypoints_meta=waypoints_meta if waypoints_meta else None, 
        optimize=optimize_flag
    )
    
    ss["last_gmaps_url"] = gmaps_web
    
    # Actualiza el estado de la aplicación para que se rendericen las métricas
    st.rerun()


# ---------------------------
# Entrada principal
# ---------------------------
def mostrar_profesional():
    ss = st.session_state
    
    # Aseguramos que la bandera de optimización existe al iniciar
    if 'optimize_route' not in st.session_state:
        st.session_state['optimize_route'] = False
        
    # 1. HEADER (Título - simulación)
    st.title("Gestor de Rutas")
    
    # 2. Forzamos la recarga si el usuario cambia (MANTENEMOS LÓGICA DE ESTADO)
    if st.session_state.get('_current_routes_user') != st.session_state.get('username'):
        st.session_state['_current_routes_user'] = st.session_state.get('username')
        st.session_state["saved_routes"] = _load_routes_file()
        st.session_state["prof_points"] = []
        st.session_state["route_name_input"] = ""
        st.session_state["saved_choice"] = ""
        st.session_state["optimize_route"] = False # Resetear bandera de optimización
        
    # ====================================================================
    # ESTRUCTURA PRINCIPAL (COLUMNAS IZQUIERDA/DERECHA)
    # ====================================================================
    
    col_izq, col_der = st.columns([4, 6])
    
    with col_izq:
        # A. TARJETA AGREGAR DIRECCIÓN
        with st.container(border=True):
            _add_direction_container() 
            
        st.markdown("---")
        
        # B. TARJETA GESTIÓN DE RUTAS (Guardar / Cargar)
        with st.container(border=True):
            _save_load_col() # Usa la función para gestión de rutas

    with col_der:
        # C. TARJETA DIRECCIONES DE LA RUTA
        with st.container(border=True):
            col_list_header, col_list_clean = st.columns([8, 2])
            with col_list_header:
                st.subheader("Direcciones de la ruta")
            with col_list_clean:
                st.button("Limpiar", on_click=_clear_points, use_container_width=True, help="Limpiar todos los puntos")
                
            _list_col() # Usa la lista limpia sin subtítulos

    st.markdown("---") 

    # D. SECCIÓN INFERIOR: EXPORTAR Y OPTIMIZACIÓN/MÉTRICAS (Al pie de página)
    
    # Botón principal para generar la ruta que estaba abajo
    if st.button("Generar Ruta y Exportar", type="primary", use_container_width=True):
        _build_and_show_outputs()
        
    st.markdown("---")
        
    col_exp, col_met = st.columns([4, 8])
    
    with col_exp:
        st.subheader("Exportar a Mapas")
        if ss.get("last_gmaps_url"):
            # === CORRECCIÓN CLAVE: Resolver metadatos ANTES de llamar a build_waze_url ===
            
            # Asegurarse de que la lista tiene al menos dos puntos
            if len(ss["prof_points"]) >= 2:
                o_meta = resolve_selection(ss["prof_points"][0], None)
                d_meta = resolve_selection(ss["prof_points"][-1], None)

                # Generación de URLs con metadatos (dicts)
                waze_url = build_waze_url(o_meta, d_meta)
                apple_url = build_apple_maps_url(o_meta, d_meta)
            else:
                # Fallback si no hay suficientes puntos
                waze_url = "#"
                apple_url = "#"

            gmaps_url = ss["last_gmaps_url"]
            
            st.link_button("Abrir en Google Maps", gmaps_url, type="primary", use_container_width=True)
            st.link_button("Abrir en Waze", waze_url, use_container_width=True)
            st.link_button("Copiar enlace", gmaps_url, help="Copiar URL al portapapeles", use_container_width=True)

    with col_met:
        st.subheader("Optimización y Métricas")
        
        if ss.get("last_gmaps_url"):
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.markdown("Modo de optimización")
                st.selectbox("Modo", options=["Ruta optimizada" if ss.get('optimize_route') else "Original"], label_visibility="collapsed")
            with col_m2:
                st.metric("Distancia Total", "XX km")
            with col_m3:
                st.metric("Tiempo Estimado", "YY min")

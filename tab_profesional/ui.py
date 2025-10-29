import io
import json
from pathlib import Path
from typing import List

import streamlit as st
import qrcode

from app_utils_core import (
    # Nuevas funciones de URL que deben existir en app_utils_core.py
    build_gmaps_web_url, 
    build_gmaps_app_link_navigation, 
    build_gmaps_android_intent_url, 
    build_gmaps_ios_comgooglemaps,
    # Funciones existentes
    build_waze_url, 
    build_apple_maps_url,
    resolve_selection,
)

# Definición base para la carpeta de rutas
ROUTES_DIR = Path(".streamlit")
ROUTES_DIR.mkdir(parents=True, exist_ok=True)

MAX_POINTS = 10


# ---------------------------
# Estado
# ---------------------------
# Nota: La inicialización de estado ahora se hace en photo_agent_app.py
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
$(cat tab_profesional/ui_add_point.temp)

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
    # Aseguramos que solo guardamos y usamos STRINGS válidas
    cleaned_data = []
    for item in data:
        # Convierte a string, elimina espacios y verifica que no esté vacío
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
# Columnas
# ---------------------------
def _search_col():
    st.subheader("Añade puntos")
    with st.form("add_form", clear_on_submit=False):
        st.text_input(
            "Escribe dirección (mín. 3 letras).",
            key="prof_text_input",
            placeholder="p. ej. Passeig de Gràcia 1, Barcelona",
        )
        st.checkbox(
            "Optimizar ruta (visitar paradas en el orden más rápido)",
            value=st.session_state.get('optimize_route', False),
            key='optimize_route',
        )
        submitted = st.form_submit_button("Añadir", type="primary", use_container_width=True)
    if submitted:
        _add_point(st.session_state.get("prof_text_input"))


$(cat tab_profesional/ui_list_col.temp)

    # Limpiar debajo de la lista: Ahora usa el ancho completo.
    st.button("Limpiar ruta", on_click=_clear_points, use_container_width=True)


def _save_load_col():
    st.subheader("Guardar / Cargar")
    st.text_input("Nombre para guardar", key="route_name_input", placeholder="p. ej. Lunes")
    
    # Añadimos on_change para cargar la ruta automáticamente al seleccionar
    st.selectbox("Rutas guardadas",
                  options=[""] + sorted(st.session_state["saved_routes"].keys()),
                  key="saved_choice",
                  on_change=lambda: _load_route(st.session_state.get("saved_choice"))  
                  )
    
    # Quitamos el botón "Cargar" ya que la carga es automática
    c1, c2 = st.columns([1, 1])
    with c1:
        st.button("💾 Guardar", on_click=_save_current_route, use_container_width=True)
    with c2:
        st.button("🗑️ Borrar",
                  on_click=lambda: _delete_saved_route(st.session_state.get("saved_choice")),
                  use_container_width=True,
                  disabled=not st.session_state.get("saved_choice"))

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

    # Preparamos o_text/d_text/w_texts
    pts = ss["prof_points"]
    if len(pts) < 2:
        st.warning("Añade origen y destino (mínimo 2 puntos).")
        return 
        
    o_text = pts[0]
    d_text = pts[-1]
    w_texts = pts[1:-1]

    # Resolvemos todas las direcciones a meta-datos (incluyendo coordenadas)
    o_meta = resolve_selection(o_text, None)
    d_meta = resolve_selection(d_text, None)
    waypoints_meta = [resolve_selection(w, None) for w in w_texts]

    # La bandera de optimización se pasa directamente desde la sesión
    optimize_flag = ss.get('optimize_route', False)
    
    # === GENERACIÓN DE URLS ===
    # Solo generamos el enlace web estándar (build_gmaps_web_url)
    # y los enlaces de Waze y Apple Maps.
    
    gmaps_web = build_gmaps_web_url(
        o_meta, d_meta, 
        waypoints_meta=waypoints_meta if waypoints_meta else None, 
        optimize=optimize_flag
    )
    
    ss["last_gmaps_url"] = gmaps_web # Guardamos este para el QR
    waze = build_waze_url(o_meta, d_meta)
    apple = build_apple_maps_url(o_meta, d_meta)

    st.success("Ruta generada. Elige cómo abrirla 👇")
    
    st.markdown("---")
    
    # === RENDER DE BOTONES UNIFICADOS ===
    
    # Botón UNIFICADO para Google Maps (el móvil/navegador preguntará dónde abrir)
    st.link_button("🗺️ Abrir Ruta (Google Maps)", gmaps_web, type="primary", use_container_width=True)

    st.markdown("---")

    # Botones de Apps Alternativas
    col_waze, col_apple = st.columns(2)
    with col_waze:
        st.link_button("🚗 Abrir en Waze", waze, use_container_width=True)
    with col_apple:
        st.link_button("🍎 Abrir en Apple Maps", apple, use_container_width=True)

    st.markdown("---")
    st.caption("Escanea el QR (Google Maps Web)")
    if ss["last_gmaps_url"]:
        img_buf = _qr_image_for(ss["last_gmaps_url"])
        st.image(img_buf, caption="QR", width=220)




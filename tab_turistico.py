import streamlit as st
from app_utils_core import build_gmaps_url, build_waze_url, build_apple_maps_url, resolve_selection
from typing import List

# Archivo de ejemplo para la pestaña 'Turístico'

def mostrar_turistico():
    st.header("Planificador de Rutas Turísticas 🗺️")
    
    # Usamos una sola entrada de texto grande para múltiples paradas
    stops_txt = st.text_area(
        "Introduce Paradas de Interés (separa por líneas o con |)", 
        placeholder="Ej: Sagrada Familia\nParque Güell\nHotel Majestic\n...\n",
        height=150
    )
    
    # Parámetros opcionales
    col1, col2 = st.columns(2)
    with col1:
        start_point = st.text_input("Punto de Origen (Opcional)", placeholder="Tu ubicación inicial")
    with col2:
        end_point = st.text_input("Punto de Destino Final (Opcional)", placeholder="Punto de finalización")

    if st.button("Generar Ruta Turística", type="primary", use_container_width=True):
        
        # ------------------- LÓGICA DE SANEAMIENTO (TU CÓDIGO CORREGIDO) -------------------
        raw = stops_txt
        if isinstance(raw, str):
            # Soportar tanto entradas por líneas como separadas por '|'
            if "\n" in raw:
                items = [w.strip() for w in raw.splitlines()]
            else:
                items = [w.strip() for w in raw.split("|")]
        else:
            items = list(raw)

        # Filtrar vacíos, eliminar solo el token exacto 'optimize'/'optimize:true' y deduplicar (case-insensitive)
        seen = set()
        cleaned = []
        for w in items:
            s = (w or "").strip()
            if not s:
                continue
            # descartamos solo el token exacto 'optimize' / 'optimize:true'
            if s.lower() in ("optimize", "optimize:true"):
                continue
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append({"address": s})
        # --- FIN SANEAMIENTO ---

        # ------------------- CONSTRUCCIÓN DE RUTA -------------------
        
        # 1. Definir la lista de todos los puntos para la Geocodificación
        all_points = []
        
        # Añadir Origen y Destino si existen
        if start_point:
            all_points.append(start_point)
            
        all_points.extend([p["address"] for p in cleaned]) # Añadir paradas intermedias
        
        if end_point:
            all_points.append(end_point)
            
        if len(all_points) < 2:
            st.warning("Introduce al menos dos puntos para generar la ruta.")
            return

        # 2. Geocodificar todos los puntos
        # Nota: Aquí deberías llamar a una función para geocodificar todos los puntos
        # La versión simplificada usa los puntos de la lista final para la URL
        
        # Para la URL, usamos el primer y último punto de la lista
        origin_txt = all_points[0]
        destination_txt = all_points[-1]
        waypoints_txt = all_points[1:-1]

        # 3. Resolver metadatos
        origin_meta = resolve_selection(origin_txt)
        destination_meta = resolve_selection(destination_txt)
        
        waypoints_meta = [resolve_selection(w) for w in waypoints_txt]


        # 4. Generar URLs
        gmaps_url = build_gmaps_url(origin_meta, destination_meta, waypoints_meta=waypoints_meta)
        waze_url  = build_waze_url(origin_meta, destination_meta)
        apple_url = build_apple_maps_url(origin_meta, destination_meta)

        st.success("Ruta generada. Elige cómo abrirla 👇")
        
        c1, c2, c3 = st.columns(3)
        with c1: st.link_button("🗺️ Google Maps", gmaps_url, use_container_width=True)
        with c2: st.link_button("🚗 Waze", waze_url, use_container_width=True)
        with c3: st.link_button("🍎 Apple Maps", apple_url, use_container_width=True)

        # DEBUG (temporal) - Muestra los puntos saneados para verificación
        # Si ves el punto fantasma, sabrás que el error no vino de la entrada de usuario
        st.subheader("DEBUG: Puntos Saneados Enviados")
        st.write(cleaned)

# Si este archivo es llamado directamente (como módulo principal)
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    mostrar_turistico()


import streamlit as st
from app_utils_core import build_gmaps_url, build_waze_url, build_apple_maps_url
from app_utils_core import resolve_selection # Necesaria para resolver las direcciones

# Archivo de ejemplo para la pestaña 'Viajero'

def mostrar_viajero():
    st.header("Planificador de Rutas de Viaje 🏞️")
    
    col1, col2 = st.columns(2)
    with col1:
        origin_txt = st.text_input("Origen", placeholder="Ciudad de partida")
    with col2:
        destination_txt = st.text_input("Destino", placeholder="Punto de llegada")
        
    stops_txt = st.text_area(
        "Paradas Intermedias (Opcional)", 
        placeholder="Introduce paradas separadas por líneas o con |",
        height=100
    )

    if st.button("Generar Ruta de Viaje", type="primary", use_container_width=True):
        
        if not origin_txt or not destination_txt:
            st.warning("Introduce origen y destino.")
            return

        # ------------------- LÓGICA DE SANEAMIENTO (INTEGRACIÓN) -------------------
        raw = stops_txt or ""
        
        if isinstance(raw, str):
            # Soportar tanto entradas por líneas como separadas por '|'
            if "\n" in raw:
                items = [w.strip() for w in raw.splitlines()]
            else:
                items = [w.strip() for w in raw.split("|")]
        else:
            items = list(raw)

        # Filtrar vacíos, eliminar solo el token exacto 'optimize'/'optimize:true' y deduplicar
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
        # --- FIN SANEADO ---
        
        # 1. Resolver metadatos de Origen y Destino
        origin_meta = resolve_selection(origin_txt)
        destination_meta = resolve_selection(destination_txt)
        
        # 2. Resolver metadatos de Waypoints
        waypoints_meta = [resolve_selection(w["address"]) for w in cleaned]

        # 3. Generar URLs
        gmaps_url = build_gmaps_url(origin_meta, destination_meta, waypoints_meta=waypoints_meta)
        waze_url  = build_waze_url(origin_meta, destination_meta)
        apple_url = build_apple_maps_url(origin_meta, destination_meta)

        st.success("Ruta generada. Elige cómo abrirla 👇")
        
        c1, c2, c3 = st.columns(3)
        with c1: st.link_button("🗺️ Google Maps", gmaps_url, use_container_width=True)
        with c2: st.link_button("🚗 Waze", waze_url, use_container_width=True)
        with c3: st.link_button("🍎 Apple Maps", apple_url, use_container_width=True)

# Si este archivo es llamado directamente
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    mostrar_viajero()


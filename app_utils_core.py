import urllib.parse
import os
import streamlit as st
from dotenv import load_dotenv
import googlemaps

# ----------------- LECTURA DE CLAVES DE API -----------------
load_dotenv()
GMAPS_API_KEY = os.getenv("GOOGLE_API_KEY") 

# Inicialización del cliente de Google Maps
@st.cache_resource
def get_gmaps_client():
    key_to_use = GMAPS_API_KEY
    if not key_to_use:
        # Usamos st.error en lugar de st.warning si la clave es crítica para el funcionamiento
        st.warning("⚠️ Clave API no configurada. La Geocodificación será SIMULADA.")
        return None
    try:
        # Se verifica la clave antes de devolver el cliente
        client = googlemaps.Client(key=key_to_use)
        # Opcional: una prueba ligera para confirmar que la clave es válida
        client.geocode("Barcelona")
        return client
    except Exception:
        # Si falla por cualquier motivo (conexión, clave inválida), devolvemos None
        st.error("❌ Fallo al inicializar Google Maps API Client. Revisa la clave o la conexión.")
        return None

GMAPS_CLIENT = get_gmaps_client()

# ----------------- Funciones de Geocodificación y URL -----------------

def geocode_address(query):
    if not GMAPS_CLIENT:
        return None
    
    try:
        results = GMAPS_CLIENT.geocode(query)
        if results:
            location = results[0]['geometry']['location']
            formatted_address = results[0]['formatted_address']
            return {
                "address": formatted_address,
                "lat": location['lat'],
                "lon": location['lng']
            }
    except Exception as e:
        # Manejo de error de geocodificación (ej. límite excedido)
        print(f"Error geocodificando {query}: {e}")
        return None
    return None

def resolve_selection(label, meta=None):
    """Convierte la dirección a metadatos (coordenadas o texto)."""
    geo_data = geocode_address(label)
    
    if geo_data:
        coords = f"{geo_data['lat']},{geo_data['lon']}"
        # Aseguramos que los metadatos de las coordenadas también incluyan lat/lon por si waze/apple los usa
        return {
            "address": geo_data['address'], 
            "coords": coords,
            "lat": geo_data['lat'],
            "lon": geo_data['lon']
        }
        
    # Si la geocodificación falla, asumimos que es una dirección de texto o una coordenada mal escrita
    # y la guardamos en ambos campos para que build_gmaps_url decida.
    label_stripped = (label or "").strip()
    return {"address": label_stripped, "coords": label_stripped}

# --- Añadir estas utilidades para deep links / intents ---
def _encode_for_uri(s: str) -> str:
    """Codifica la cadena para URL/URI."""
    return urllib.parse.quote(str(s or ""), safe="")

def build_gmaps_web_url(origin_meta, destination_meta, waypoints_meta=None, mode="driving", avoid=None, optimize=False):
    """
    URL web (api=1) — preview en navegador / posibilidad de abrir app.
    Incluye la lógica de optimización (optimize=true|...) si el flag está activo.
    """
    origin = origin_meta.get("coords") or origin_meta.get("address")
    destination = destination_meta.get("coords") or destination_meta.get("address")
    params = {
        "api": "1",
        "origin": origin,
        "destination": destination,
        "travelmode": mode
    }
    
    # Waypoints
    if waypoints_meta:
        pts = []
        for w in waypoints_meta:
            # Asumiendo que w es un diccionario de metadatos (el resultado de resolve_selection)
            val = w.get("coords") if isinstance(w, dict) else w
            if val and not str(val).strip().lower() in ("optimize","optimize:true"):
                pts.append(str(val).strip())
        
        if pts:
            wp = "|".join(pts)
            # Añadir la bandera de optimización SÓLO si el checkbox estaba marcado
            if optimize:
                 wp = "optimize:true|" + wp
                 
            params["waypoints"] = wp
            
    # codificar
    parts = [f"{k}={_encode_for_uri(v)}" for k, v in params.items()]
    # Usamos /dir/ para forzar la navegación
    return "https://www.google.com/maps/dir/?" + "&".join(parts)

def build_waze_url(origin_meta, destination_meta):
    # CORRECCIÓN: Obtener la dirección del destino de los metadatos correctos
    origin = origin_meta.get("coords") or origin_meta.get("address")
    
    # Priorizamos coordenadas para waze, si están disponibles
    dest_lat = destination_meta.get("lat")
    dest_lon = destination_meta.get("lon")
    destination_address = destination_meta.get("address")
    
    if dest_lat and dest_lon:
        ll = f"{dest_lat},{dest_lon}"
        return (
            "https://waze.com/ul"
            f"?ll={_encode(ll)}"
            f"&navigate=yes&from_name={_encode(origin)}"
        )
    
    # Si no hay coordenadas (geo_data falló), usamos la dirección de texto
    return (
        "https://waze.com/ul"
        f"?q={_encode(destination_address)}"
        f"&navigate=yes&from_name={_encode(origin)}"
    )

def build_apple_maps_url(origin_meta, destination_meta, waypoints=None):
    # CORRECCIÓN: Obtener la dirección del destino de los metadatos correctos
    origin = origin_meta.get("address")
    destination = destination_meta.get("address")
    
    # Apple Maps es muy sensible. Usaremos saddr y daddr.
    return (
        "https://maps.apple.com/"
        f"?saddr={_encode(origin)}"
        f"&daddr={_encode(destination)}"
        "&dirflg=d" # Indica conducción
    )
# ==============================================================================
# NUEVAS FUNCIONES DE DEEP LINK 
# ==============================================================================

def build_gmaps_app_link_navigation(destination_meta, origin_meta=None, mode="d"):
    """Genera un esquema de navegación directa 'google.navigation:' (ideal para Android)."""
    dest = destination_meta.get("coords") or destination_meta.get("address")
    
    if not dest:
        return "https://google.com/maps"

    # google.navigation acepta q=dest (coords o text)
    q = _encode_for_uri(dest)
    nav_url = f"google.navigation:q={q}&mode={mode}"
    return nav_url


def build_gmaps_android_intent_url(origin_meta, destination_meta, waypoints_meta=None, mode="driving", optimize=False):
    """
    Construye un intent:// URL para Android que intenta abrir la app de Google Maps.
    """
    # Usamos build_gmaps_web_url para obtener la URL base con todos los parámetros (waypoints/optimización)
    web_url = build_gmaps_web_url(origin_meta, destination_meta, waypoints_meta, mode=mode, optimize=optimize)
    
    # Intent que abre la URL en la app com.google.android.apps.maps
    # Nota: la parte web_url.split('//')[-1] es CRÍTICA para que funcione en Android
    return (
        f"intent://{web_url.split('//')[-1]}"  # Quita el http(s)://
        f"#Intent;scheme=https;package=com.google.android.apps.maps;action=VIEW;S.browser_fallback_url={_encode_for_uri(web_url)};end"
    )

def build_gmaps_ios_comgooglemaps(origin_meta, destination_meta, mode="driving"):
    """
    Link para iOS abriendo Google Maps app si está instalada (comgooglemaps://).
    Nota: Este esquema NO soporta waypoints ni optimización. Solo Origen y Destino.
    """
    saddr = origin_meta.get("coords") or origin_meta.get("address") if origin_meta else ""
    daddr = destination_meta.get("coords") or destination_meta.get("address")
    params = []
    if saddr:
        params.append(f"saddr={_encode_for_uri(saddr)}")
    if daddr:
        params.append(f"daddr={_encode_for_uri(daddr)}")
    params.append(f"directionsmode={_encode_for_uri(mode)}")
    return "comgooglemaps://?" + "&".join(params)

# Funciones de Waze y Apple Maps (mantener)
def build_waze_url(origin_meta, destination_meta):
    origin = origin_meta.get("address")
    
    dest_lat = destination_meta.get("lat")
    dest_lon = destination_meta.get("lon")
    destination_address = destination_meta.get("address")
    
    if dest_lat and dest_lon:
        ll = f"{dest_lat},{dest_lon}"
        return (
            "https://waze.com/ul"
            f"?ll={_encode_for_uri(ll)}"
            f"&navigate=yes&from_name={_encode_for_uri(origin)}"
        )
    
    return (
        "https://waze.com/ul"
        f"?q={_encode_for_uri(destination_address)}"
        f"&navigate=yes&from_name={_encode_for_uri(origin)}"
    )

def build_apple_maps_url(origin_meta, destination_meta, waypoints=None):
    origin = origin_meta.get("address")
    destination = destination_meta.get("address")
    return (
        "https://maps.apple.com/"
        f"?saddr={_encode_for_uri(origin)}"
        f"&daddr={_encode_for_uri(destination)}"
        "&dirflg=d"
    )

# Bandera de “API disponible”
gmaps = bool(GMAPS_CLIENT)

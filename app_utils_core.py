import urllib.parse
import os
import streamlit as st
from dotenv import load_dotenv
import googlemaps

# ----------------- LECTURA DE CLAVES DE API -----------------
# Cargar variables de entorno (para desarrollo local)
load_dotenv()

# Prioridad 1: Leer desde .env (os.getenv) para desarrollo local
# Prioridad 2: Leer desde st.secrets (solo si estamos en la nube)
key_from_env = os.getenv("GOOGLE_API_KEY")

if key_from_env:
    GMAPS_API_KEY = key_from_env
elif hasattr(st, 'secrets'):
    # Si no tenemos clave local y estamos en un entorno con st.secrets, la usamos
    GMAPS_API_KEY = st.secrets.get("GOOGLE_API_KEY")
else:
    # No hay clave en el entorno
    GMAPS_API_KEY = None


# Inicialización del cliente de Google Maps
@st.cache_resource
def get_gmaps_client():
    key_to_use = GMAPS_API_KEY
    
    if not key_to_use:
        st.warning("⚠️ Clave API de Google no configurada. La Geocodificación será SIMULADA.")
        return None
    try:
        client = googlemaps.Client(key=key_to_use)
        client.geocode("Barcelona")
        return client
    except Exception as e:
        # Esto atrapa REQUEST_DENIED.
        st.error(f"Error al inicializar la API de Google Maps: {e}")
        return None

GMAPS_CLIENT = get_gmaps_client()

# ---------------------------------------------------------------------------
# Geocodificación Real (Implementación)
# ---------------------------------------------------------------------------
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
    except Exception:
        return None
    return None

def suggest_addresses(query, min_len=3, max_results=8):
    if not GMAPS_CLIENT:
        # Fallback si no hay API
        if not query or len(query.strip()) < 3:
            return []
        return [{"description": query.strip()}]
        
    # Lógica de autocompletado (si Places API estuviera implementada aquí)
    if not query or len(query.strip()) < 3:
        return []
    return [{"description": query.strip()}]


def resolve_selection(label, meta=None):
    """
    Convierte el texto de la dirección a coordenadas reales.
    """
    geo_data = geocode_address(label)
    
    if geo_data:
        coords = f"{geo_data['lat']},{geo_data['lon']}"
        return {"address": geo_data['address'], "coords": coords}
        
    # Fallback (Simulación)
    return {"address": (label or "").strip(), "coords": (label or "").strip()}


# ---------------------------------------------------------------------------
# Construcción de URLs Google / Waze / Apple (USANDO COORDENADAS)
# ---------------------------------------------------------------------------
def _encode(s: str) -> str:
    return urllib.parse.quote_plus(s or "")


def build_gmaps_url(origin_meta, destination_meta, waypoints_meta=None, mode="driving", avoid=None):
    """
    Implementación de optimización directa (solución final).
    """
    origin = origin_meta.get("coords", origin_meta.get("address"))
    destination = destination_meta.get("coords", destination_meta.get("address"))
    
    waypoints = [w.get("coords", w.get("address")) for w in (waypoints_meta or [])] 
    
    params = [
        "api=1",
        f"origin={_encode(origin)}",
        f"destination={_encode(destination)}",
        f"travelmode={_encode(mode)}",
    ]
    
    if waypoints:
        encoded_waypoints = [_encode(w.strip()) for w in waypoints if (w or "").strip()]
        waypoints_param = "optimize:true|" + "%7C".join(encoded_waypoints)
        params.append(f"waypoints={waypoints_param}")
        
    if avoid:
        params.append(f"avoid={_encode(avoid)}")
        
    return "https://www.google.com/maps/dir/?" + "&".join(params)


def build_waze_url(origin_meta, destination_meta):
    origin = origin_meta.get("address")
    destination = destination_meta.get("address")
    
    if destination_meta.get("lat") and destination_meta.get("lon"):
        ll = f"{destination_meta['lat']},{destination_meta.get('lon')}"
        return (
            "https://waze.com/ul"
            f"?ll={_encode(ll)}"
            f"&navigate=yes&from_name={_encode(origin)}"
        )
    
    return (
        "https://waze.com/ul"
        f"?q={_encode(destination)}"
        f"&navigate=yes&from_name={_encode(origin)}"
    )

def build_apple_maps_url(origin_meta, destination_meta, waypoints=None):
    origin = origin_meta.get("address")
    destination = destination_meta.get("address")
    return (
        "https://maps.apple.com/"
        f"?saddr={_encode(origin)}"
        f"&daddr={_encode(destination)}"
        "&dirflg=d"
    )

# Bandera de “API disponible”
gmaps = bool(GMAPS_CLIENT)

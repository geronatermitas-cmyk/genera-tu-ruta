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
        st.warning("⚠️ Clave API no configurada. La Geocodificación será SIMULADA.")
        return None
    try:
        client = googlemaps.Client(key=key_to_use)
        client.geocode("Barcelona")
        return client
    except Exception:
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
    except Exception:
        return None
    return None

def resolve_selection(label, meta=None):
    """Convierte la dirección a metadatos (coordenadas o texto)."""
    geo_data = geocode_address(label)
    
    if geo_data:
        coords = f"{geo_data['lat']},{geo_data['lon']}"
        return {"address": geo_data['address'], "coords": coords}
        
    return {"address": (label or "").strip(), "coords": (label or "").strip()}


def _encode(s: str) -> str:
    """Codifica la cadena para URL."""
    return urllib.parse.quote_plus(s or "")


def build_gmaps_url(origin_meta, destination_meta, waypoints_meta=None, mode="driving", avoid=None):
    """
    Implementación FINAL de optimización que evita el punto fantasma.
    """
    import urllib.parse
    
    origin = origin_meta.get("coords", origin_meta.get("address"))
    destination = destination_meta.get("coords", destination_meta.get("address"))

    # Extraemos los waypoints en crudo (coords o address)
    waypoints_for_url = [w.get("coords", w.get("address")) for w in (waypoints_meta or [])]

    # Parámetros base
    params = {
        "api": "1",
        "origin": origin,
        "destination": destination,
        "travelmode": mode,
    }

    # Waypoints: agregar si existen después de filtrar entradas que contengan optimize:...
    if waypoints_for_url:
        cleaned = []
        for w in waypoints_for_url:
            s = str(w).strip()
            if not s:
                continue
            # Descartamos solo el token EXACTO optimize / optimize:true
            if s.lower() in ("optimize", "optimize:true"):
                continue
            cleaned.append(s)
            
        if cleaned:
            # Construcción de la cadena de waypoints
            waypoints_string = "optimize:true|" + "|".join(cleaned)
            params["waypoints"] = waypoints_string

    if avoid:
        params["avoid"] = str(avoid)

    # Codificamos cada valor de forma segura y construimos la URL
    encoded_parts = []
    for k, v in params.items():
        # urllib.parse.quote con safe='' asegura que '|' se convierta en %7C
        encoded_value = urllib.parse.quote(str(v), safe="")
        encoded_parts.append(f"{k}={encoded_value}")

    # Utilizamos la URL universal de Google Maps (sin el número de versión)
    return "https://www.google.com/maps/dir/?" + "&".join(encoded_parts)


def build_waze_url(origin_meta, destination_meta):
    origin = origin_meta.get("address")
    destination = origin_meta.get("address")
    
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
    destination = origin_meta.get("address")
    return (
        "https://maps.apple.com/"
        f"?saddr={_encode(origin)}"
        f"&daddr={_encode(destination)}"
        "&dirflg=d"
    )

# Bandera de “API disponible”
gmaps = bool(GMAPS_CLIENT)

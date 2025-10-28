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
    Implementación FINAL de optimización.
    """
    origin = origin_meta.get("coords", origin_meta.get("address"))
    destination = destination_meta.get("coords", destination_meta.get("address"))
    
    # 1. Extraemos los waypoints del medio
    waypoints_for_url = [w.get("coords", w.get("address")) for w in (waypoints_meta or [])] 
    
    params = [
        "api=1",
        f"origin={_encode(origin)}",
        f"destination={_encode(destination)}",
        f"travelmode={_encode(mode)}",
    ]
    
    if waypoints_for_url:
        # Codificamos individualmente y unimos. 
        encoded_waypoints_list = [_encode(w.strip()) for w in waypoints_for_url if (w or "").strip()]
        
        # SINTAXIS FINAL: Aseguramos que 'optimize:true' vaya prefijado.
        waypoints_string = "optimize:true|" + "|".join(encoded_waypoints_list)
        
        # Reemplazamos los '|' por %7C
        params.append(f"waypoints={waypoints_string.replace('|', '%7C')}")
        
    if avoid:
        params.append(f"avoid={_encode(avoid)}")
        
    # Cambiamos el número de versión de la URL para forzar la recarga en el navegador
    return "https://www.google.com/maps/dir/?api=1&origin=36.5210142%2C-6.2804565&destination=37.9893044%2C-1.13?" + "&".join(params) 


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

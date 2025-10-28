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
        # comprobación opcional mínima
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
            formatted_address = results[0].get('formatted_address', query)
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
    """Codifica la cadena para URL. Usamos quote con safe='' para que '|' se convierta en %7C."""
    return urllib.parse.quote(str(s or ""), safe="")


def build_gmaps_url(origin_meta, destination_meta, waypoints_meta=None, mode="driving", avoid=None):
    """
    Construye una URL para Google Maps Directions (web), codificando de forma segura.
    Devuelve None si falta origin o destination.
    """
    # obtener origen/destino (coords preferidas)
    origin = origin_meta.get("coords") or origin_meta.get("address")
    destination = destination_meta.get("coords") or destination_meta.get("address")

    if not origin or not destination:
        return None

    # normalizar waypoints: aceptamos lista de dicts {'address'/'coords'} o lista de strings
    waypoints_for_url = []
    for w in (waypoints_meta or []):
        if isinstance(w, dict):
            val = w.get("coords") or w.get("address")
        else:
            val = w
        if val and str(val).strip():
            waypoints_for_url.append(str(val).strip())

    # Parámetros base en dict
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
            # descartamos entradas que ya vengan como optimize:... desde la UI
            if s.lower().startswith("optimize"):
                continue
            cleaned.append(s)
        if cleaned:
            # prefijamos 'optimize:true' (si quieres controlarlo desde UI, quítalo)
            waypoints_string = "optimize:true|" + "|".join(cleaned)
            # guardamos sin encode; se codificará después con _encode (quote safe='')
            params["waypoints"] = waypoints_string

    if avoid:
        params["avoid"] = str(avoid)

    # Codificamos cada valor con safe='' para asegurar %7C por '|' y no dejar caracteres problemáticos
    encoded_parts = []
    for k, v in params.items():
        encoded_parts.append(f"{k}={_encode(v)}")

    return "https://www.google.com/maps/dir/?" + "&".join(encoded_parts)


def build_waze_url(origin_meta, destination_meta):
    origin = origin_meta.get("address")
    destination = destination_meta.get("address")  # FIX: usar destination_meta

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
    destination = destination_meta.get("address")  # FIX: usar destination_meta
    return (
        "https://maps.apple.com/"
        f"?saddr={_encode(origin)}"
        f"&daddr={_encode(destination)}"
        "&dirflg=d"
    )


# Bandera de “API disponible”
gmaps = bool(GMAPS_CLIENT)

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


def _encode(s: str) -> str:
    """Codifica la cadena para URL usando quote_plus para espacios (por legibilidad en la URL)."""
    return urllib.parse.quote_plus(s or "")


def build_gmaps_url(origin_meta, destination_meta, waypoints_meta=None, mode="driving", avoid=None):
    """
    Implementación CORREGIDA que resuelve el problema del 'punto fantasma' (?api=1).
    Usa la URL base correcta y codifica correctamente los parámetros.
    """
    
    origin = origin_meta.get("coords", origin_meta.get("address"))
    destination = destination_meta.get("coords", destination_meta.get("address"))

    # Extraemos los waypoints en crudo (coords o address)
    waypoints_for_url = [w.get("coords", w.get("address")) for w in (waypoints_meta or [])]

    # Parámetros base
    # La API web de Google Maps para direcciones USA 'dir' (o 'd') pero con 'dir/...'
    # Usaremos el formato estándar de directions API (daddr, saddr) o el simple (origin, destination)
    # y nos aseguraremos de que no haya una '?' en el valor.
    params = {
        # 'api': '1' se añade al final y no como parte de un parámetro
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
            low = s.lower()
            # Descartamos solo el token EXACTO optimize / optimize:true
            if low in ("optimize", "optimize:true"):
                continue
            cleaned.append(s)
            
        if cleaned:
            # Construcción de la cadena de waypoints
            # La bandera 'optimize:true' DEBE ir como prefijo del parámetro waypoints.
            waypoints_string = "optimize:true|" + "|".join(cleaned)
            params["waypoints"] = waypoints_string

    if avoid:
        params["avoid"] = str(avoid)

    # 1. Codificamos cada valor de forma segura.
    encoded_parts = []
    for k, v in params.items():
        # urllib.parse.quote con safe='' asegura que '|' se convierta en %7C
        # y no codifica el coma ',' que es necesario en las coordenadas.
        # quote_plus codifica el espacio como '+' (lo cual es normal para query strings)
        encoded_value = urllib.parse.quote(str(v), safe=":,") 
        encoded_parts.append(f"{k}={encoded_value}")

    # 2. Añadimos el parámetro 'api=1' después de todos los demás.
    encoded_parts.append("api=1")

    # 3. Reemplazamos la URL base INCORRECTA con la estándar.
    # Usamos maps.google.com/maps para el enlace web directo
    return "https://www.google.com/maps/dir/?" + "&".join(encoded_parts)


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

# Bandera de “API disponible”
gmaps = bool(GMAPS_CLIENT)

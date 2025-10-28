# photo_agent_app.py - CÓDIGO FINAL Y COMPLETO CON INICIALIZACIÓN UNIFICADA
import streamlit as st
import yaml
from yaml.loader import SafeLoader
from pathlib import Path
from PIL import Image
import hashlib
import os
from dotenv import load_dotenv

# --- Ocultar avisos del sistema Streamlit (línas amarillas) ---
st.markdown(
    """
    <style>
        [data-testid="stNotification"] {
            display: none !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------- CONFIGURACIÓN GLOBAL Y SEGURIDAD -----------------
st.set_page_config(
    page_title="Planificador de Rutas",
    layout="wide",
    initial_sidebar_state="expanded",
)

CONFIG_FILE = Path('config.yaml')
ROUTES_DIR = Path(".streamlit")

# Funciones de Soporte
def load_config():
    """Carga configuraciones de YAML."""
    try:
        with open(CONFIG_FILE) as file:
            return yaml.load(file, Loader=SafeLoader)
    except FileNotFoundError:
        return {
            'credentials': {'usernames': {}}, 
            'cookie': {
                'expiry_days': 30,
                'key': hashlib.sha256(os.urandom(32)).hexdigest(),
                'name': 'auth_cookie'
            }
        }

def save_config(config):
    """Guarda configuraciones en YAML."""
    with open(CONFIG_FILE, 'w') as file:
        yaml.dump(config, file, default_flow_style=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(username, password_unhashed, config):
    user_data = config['credentials']['usernames'].get(username)
    if not user_data: return False
    stored_hash = user_data['password_hash']
    input_hash = hash_password(password_unhashed)
    return stored_hash == input_hash

def clear_route_state():
    """Función que borra las variables de ruta al cerrar sesión."""
    for key in ["prof_points", "saved_routes", "route_name_input", "saved_choice", "_current_routes_user", "logged_in", "username", "name", "list_version"]:
        if key in st.session_state: del st.session_state[key]


# Lógica de Rutas Guardadas (Adaptada para el archivo principal)
def _get_user_routes_path():
    username = st.session_state.get('username', 'default')
    return ROUTES_DIR / f"routes_{username}.json"

def _load_routes_file():
    routes_db_path = _get_user_routes_path()
    try:
        if routes_db_path.exists():
            return json.loads(routes_db_path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

# ----------------- INICIALIZACIÓN DE ESTADO UNIFICADO -----------------

def init_ui_state():
    """
    Inicializa todas las claves de estado de la interfaz (ahora centralizado aquí).
    Esta función reemplaza la lógica de _init_state en tab_profesional/ui.py.
    """
    ss = st.session_state
    ss.setdefault("prof_points", [])
    ss.setdefault("prof_text_input", "")
    ss.setdefault("route_name_input", "")
    ss.setdefault("saved_choice", "")
    ss.setdefault("saved_routes", _load_routes_file())
    ss.setdefault("open_target", "Navegador")
    ss.setdefault("last_gmaps_url", None)
    ss.setdefault("list_version", 0)
    ss.setdefault("ow_pending", None)
    ss.setdefault("logged_in", False)
    ss.setdefault("show_register", False)
    ss.setdefault("username", None)
    ss.setdefault("name", None)


# Llamadas de configuración inicial
load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    st.sidebar.warning("⚠️ Clave API de Google no configurada. La Geocodificación será SIMULADA.")
config = load_config()

# 💥 CORRECCIÓN FINAL: Unificamos la inicialización del estado de sesión.
init_ui_state()

# ----------------- LÓGICA DE LA APLICACIÓN -----------------

DONATION_URL = "https://www.paypal.com/donate/?business=73LFHKS2WCQ9U&no_recurring=0&item_name=Ayuda+para+desarrolladores&currency_code=EUR"

def _import_ui():
    """Importa solo la función de visualización de la UI."""
    try:
        from tab_profesional.ui import mostrar_profesional
        return mostrar_profesional
    except Exception:
        import importlib
        mod = importlib.import_module("tab_profesional.ui")
        return getattr(mod, "mostrar_profesional")


mostrar_profesional = _import_ui()


def main():
    
    st.title("🗺️ Planificador de Rutas")

    # Si estamos logeados, y el usuario cargado no es el de las rutas, recargamos las rutas
    if st.session_state.get('logged_in') and st.session_state.get('_current_routes_user') != st.session_state.get('username'):
        st.session_state['_current_routes_user'] = st.session_state.get('username')
        st.session_state["saved_routes"] = _load_routes_file()
        st.session_state["prof_points"] = []
        st.session_state["route_name_input"] = ""
        st.session_state["saved_choice"] = ""


    if st.session_state['logged_in']:
        # ------------------- PÁGINA PRINCIPAL (LOGEADO) -------------------
        st.sidebar.markdown("---")
        st.sidebar.subheader(f"Bienvenido, {st.session_state['name']}!") 
        
        # Botón de Logout MANUAL
        if st.sidebar.button('Logout', use_container_width=True):
            clear_route_state()
            st.session_state['logged_in'] = False
            st.session_state['username'] = None
            st.rerun() 
        
        # 2. RENDERIZAR LA APLICACIÓN PRINCIPAL
        mostrar_profesional() 
        
        # 3. MOSTRAR DONACIÓN
        st.sidebar.markdown("---")
        st.sidebar.subheader("Apoya el desarrollo 🧑‍💻")
        st.sidebar.info(
            "¿Te ha sido útil este planificador de rutas? "
            "Considera una pequeña donación para ayudarme a mantener y mejorar la aplicación."
        )
        st.sidebar.markdown(
            f"""
            <a href="{DONATION_URL}" target="_blank">
                <button style="background-color:#0070BA;color:#fff;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;width:100%;">
                    Ir al enlace de donación
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )
        st.sidebar.markdown("---")

    else:
        # ------------------- PÁGINA DE LOGIN/REGISTRO -------------------
        col_spacer1, col_content, col_spacer2 = st.columns([1, 4, 1])

        with col_content:
            try:
                # Intenta cargar el logo
                logo = Image.open("logo.png")
                st.image(logo, width=150) 
            except FileNotFoundError:
                st.write("🗺️") 
                
            st.markdown("<h1 style='text-align: center; margin-top: -15px;'>Planificador de Rutas</h1>", unsafe_allow_html=True)
            st.markdown("---")

            # Muestra el formulario de Registro si se solicita
            if st.session_state['show_register']:
                st.subheader("Registro de Nuevo Usuario")
                
                with st.form("register_form"):
                    new_username = st.text_input("Nombre de Usuario", key="reg_username")
                    new_email = st.text_input("Email", key="reg_email")
                    new_name = st.text_input("Nombre Completo", key="reg_name")
                    new_password = st.text_input("Contraseña", type="password", key="reg_password")
                    
                    submitted = st.form_submit_button("Registrarse")

                    if submitted:
                        usernames = config['credentials']['usernames']
                        
                        if not all([new_username, new_email, new_name, new_password]):
                            st.error("Rellena todos los campos.")
                        elif new_username in usernames:
                            st.error("El nombre de usuario ya existe.")
                        else:
                            config['credentials']['usernames'][new_username] = {
                                'email': new_email,
                                'name': new_name,
                                'password_hash': hash_password(new_password)
                            }
                            if 'key' not in config['cookie']:
                                config['cookie']['key'] = hashlib.sha256(os.urandom(32)).hexdigest()
                                config['cookie']['name'] = 'auth_cookie'
                                config['cookie']['expiry_days'] = 30
                                
                            save_config(config)
                            st.success('¡Registro exitoso! Ya puedes iniciar sesión.')
                            st.session_state['show_register'] = False
                            st.rerun()

                if st.button("Volver al Login", key='back_to_login'):
                    st.session_state['show_register'] = False
                    st.rerun()

            else:
                # Muestra el formulario de LOGIN
                st.subheader("Inicio de Sesión")
                
                with st.form("login_form"):
                    login_username = st.text_input("Usuario", key="login_username")
                    login_password = st.text_input("Contraseña", type="password", key="login_password")
                    
                    submitted = st.form_submit_button("Login")

                    if submitted:
                        if check_password(login_username, login_password, config):
                            user_data = config['credentials']['usernames'][login_username]
                            st.session_state['logged_in'] = True
                            st.session_state['username'] = login_username
                            st.session_state['name'] = user_data['name']
                            st.rerun()
                        else:
                            st.error("Usuario o contraseña incorrectos.")

                st.markdown("---")
                if st.button("Crear una cuenta (Registro)", type="secondary", use_container_width=True):
                    st.session_state['show_register'] = True
                    st.rerun()


if __name__ == "__main__":
    main()

import streamlit as st
from photo_agent_app import main, init_session_state, _init_state_ui

# 💥 CORRECCIÓN FINAL: Inicializamos el estado de sesión antes de cualquier cosa.
init_session_state()
_init_state_ui()

st.set_page_config(page_title="AppRutas", layout="wide")

try:
    main()
except Exception as e:
    st.error(f"Ocurrió un error al iniciar la aplicación: {e}")
    import traceback
    st.code(traceback.format_exc())

import streamlit as st
from photo_agent_app import main, init_session_state

# 💥 CORRECCIÓN FINAL: Inicializamos el estado de sesión antes de cualquier otra cosa.
init_session_state()

st.set_page_config(page_title="AppRutas", layout="wide")

try:
    main()
except Exception as e:
    st.error(f"Ocurrió un error al iniciar la aplicación: {e}")
    import traceback
    st.code(traceback.format_exc())

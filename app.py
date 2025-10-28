import streamlit as st
from photo_agent_app import main, init_ui_state

# 💥 CORRECCIÓN FINAL: Solo llamamos a la función de inicialización única.
init_ui_state()

st.set_page_config(page_title="AppRutas", layout="wide")

try:
    main()
except Exception as e:
    st.error(f"Ocurrió un error al iniciar la aplicación: {e}")
    import traceback
    st.code(traceback.format_exc())

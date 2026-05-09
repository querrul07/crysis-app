import streamlit as st
st.set_page_config(page_title="Política de Privacidad | CRYSIS", layout="wide")
with open("politica_privacidad_crysis.md", "r", encoding="utf-8") as f:
    st.markdown(f.read())

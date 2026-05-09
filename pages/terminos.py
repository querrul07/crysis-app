import streamlit as st
st.set_page_config(page_title="Términos y Condiciones | CRYSIS", layout="wide")
with open("terminos_condiciones_crysis.md", "r", encoding="utf-8") as f:
    st.markdown(f.read())

import streamlit as st
from pathlib import Path
import os
from PIL import Image

# Impostazioni di base della pagina
st.set_page_config(
    page_title="Dashboard Principale",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Funzione per trovare il percorso del file logo
def get_image_path(image_name):
    # Cerca l'immagine nella cartella corrente e nella sottocartella 'assets'
    current_dir = Path(__file__).parent
    image_path = current_dir / image_name
    if not image_path.exists():
        image_path = current_dir / "assets" / image_name
    return image_path

# Titolo e immagine
st.title("Pannello di Controllo Qualità e Osmosi")
try:
    logo_path = get_image_path("logo.jpg")
    if logo_path.exists():
        logo_image = Image.open(logo_path)
        st.image(logo_image, width=150)
except Exception as e:
    st.warning(f"Impossibile caricare il logo: {e}")

st.markdown("""
Benvenuto nella Dashboard di Controllo. Seleziona una delle opzioni qui sotto per procedere.
""")

st.markdown("---")

# Crea le colonne per i pulsanti per una migliore disposizione
col1, col2 = st.columns(2)

with col1:
    if st.button("🔴 CONTROLLO ACQUA", use_container_width=True):
        st.switch_page("pages/controllo_qualita.py")

with col2:
    if st.button("🔵 OSMOSI", use_container_width=True):
        st.switch_page("pages/osmosi.py")
import streamlit as st
import pandas as pd
from datetime import datetime
import os
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="Ephysio Analytics - Nathan Erard", layout="wide")

def fetch_from_ephysio(u, p):
    with sync_playwright() as p_wr:
        try:
            browser = p_wr.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True, 
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
            )
            # Ajout d'un User-Agent pour ressembler à un vrai navigateur
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
            page = context.new_page()
            
            # 1. Connexion (On force l'URL de login directement)
            st.info("🌍 Accès à la page de connexion...")
            page.goto("https://ephysio.pharmedsolutions.ch/fr/physio/login", wait_until="domcontentloaded", timeout=60000)
            
            # Sécurité : Si redirection, on retente d'aller sur le login
            if "login" not in page.url:
                page.goto("https://ephysio.pharmedsolutions.ch/fr/physio/login")

            st.info("🔑 Saisie des identifiants...")
            # On attend spécifiquement l'un des champs de saisie
            page.wait_for_selector("input[name='_username'], #username", timeout=30000)
            
            # Remplissage multi-sélecteurs
            page.fill("input[name='_username'], #username", u)
            page.fill("input[name='_password'], #password", p)
            
            # Clic sur le bouton (recherche par texte ou type)
            page.click("button[type='submit'], .btn-primary, text=Connexion")
            
            # 2. Sélection du profil "Nathan Erard"
            st.info("👤 Sélection du profil : Nathan Erard...")
            page.wait_for_selector("text=Nathan Erard", timeout=30000)
            page.click("text=Nathan Erard")
            
            # 3. Navigation Factures
            st.info("📄 Chargement des factures...")
            page.wait_for_url("**/app#**", timeout=30000)
            page.goto("https://ephysio.pharmedsolutions.ch")
            page.wait_for_load_state("networkidle")
            
            # 4. Menu Plus... et Export
            st.info("📂 Menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            page.wait_for_timeout(1000) 
            page.click("text=Exporter")
            
            # 5. Configuration Modale
            st.info("📅 Configuration dates (01.01.2025)...")
            page.wait_for_selector(".modal-content", timeout=15000)
            page.select_option("select", label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 6. Téléchargement
            st.info("⏳ Génération de l'Excel...")
            with page.expect_download(timeout=60000) as download_info:
                page.click("button:has-text('Créer le fichier Excel')")
            
            download = download_info.value
            path = "data_nathan.xlsx"
            download.save_as(path)
            
            browser.close()
            return path

        except Exception as e:
            if 'page' in locals():
                page.screenshot(path="debug_error.png")
            browser.close()
            st.error(f"Erreur : {e}")
            if os.path.exists("debug_error.png"):
                st.image("debug_error.png", caption="Capture d'écran du blocage")
            return None

# --- INTERFACE ---
st.title("🏥 Analyseur Facturation Ephysio")

with st.sidebar:
    u_val = st.text_input("Identifiant", value=st.secrets.get("USER", ""))
    p_val = st.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))
    if st.button("🚀 Synchroniser", type="primary"):
        res = fetch_from_ephysio(u_val, p_val)
        if res:
            st.session_state['df_nathan'] = pd.read_excel(res)
            st.success("Données récupérées !")

if 'df_nathan' in st.session_state:
    st.dataframe(st.session_state['df_nathan'], use_container_width=True)

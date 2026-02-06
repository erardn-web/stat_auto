import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
from playwright.sync_api import sync_playwright

# --- CONFIGURATION FUSEAU HORAIRE ---
os.environ['TZ'] = 'Europe/Zurich'
if hasattr(time, 'tzset'):
    time.tzset()

st.set_page_config(page_title="Analyseur Ephysio - Nathan Erard", layout="wide")

def fetch_from_ephysio(u, p):
    with sync_playwright() as p_wr:
        try:
            browser = p_wr.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True, 
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            
            # --- INJECTION DU FUSEAU DANS LE NAVIGATEUR ---
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800},
                locale="fr-CH",
                timezone_id="Europe/Zurich" # Crucial pour Ephysio
            )
            page = context.new_page()
            
            # 1. Accueil & Connexion
            st.info("🌍 Accès au site Ephysio (Heure Suisse)...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")

            st.info("🔑 Saisie des identifiants...")
            page.wait_for_selector("input", timeout=20000)
            page.locator("input[type='text'], #username").first.fill(u)
            page.locator("input[type='password'], #password").first.fill(p)
            page.keyboard.press("Enter")
            
            # 2. Sélection du profil (Nathan Erard)
            st.info("👤 Sélection du profil...")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000) 
            
            try:
                page.click("text=/Nathan Erard/i", timeout=8000)
            except:
                st.warning("Clic forcé sur le premier profil...")
                page.click(".profile-item, .list-group-item, .btn-profile")

            # 3. Navigation Factures
            st.info("📄 Accès à l'espace Facturation...")
            page.wait_for_url("**/app#**", timeout=30000)
            page.goto("https://ephysio.pharmedsolutions.ch")
            page.wait_for_load_state("networkidle")
            
            # 4. Menu Plus... et Export
            st.info("📂 Menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            page.wait_for_timeout(1500)
            page.click("text=Exporter")
            
            # 5. Configuration Modale
            st.info("📅 Configuration de l'export...")
            page.wait_for_selector(".modal-content", timeout=15000)
            page.locator("select").select_option(label="Factures")
            # Utilisation de la date du jour via l'heure suisse
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 6. Téléchargement
            st.info("⏳ Téléchargement de l'Excel...")
            with page.expect_download(timeout=60000) as download_info:
                page.locator("button:has-text('Créer'), .btn-primary").first.click()
            
            download = download_info.value
            path = "data_nathan.xlsx"
            download.save_as(path)
            
            browser.close()
            return path

        except Exception as e:
            if 'page' in locals():
                page.screenshot(path="debug_nathan.png")
            browser.close()
            st.error(f"Erreur : {e}")
            if os.path.exists("debug_nathan.png"):
                st.image("debug_nathan.png")
            return None

# Interface
st.title("🏥 Analyseur Facturation Ephysio")
u_side = st.sidebar.text_input("Identifiant", value=st.secrets.get("USER", ""))
p_side = st.sidebar.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))

if st.sidebar.button("🚀 Synchroniser"):
    res = fetch_from_ephysio(u_side, p_side)
    if res:
        st.session_state['df'] = pd.read_excel(res)
        st.success(f"Dernière synchro : {datetime.now().strftime('%H:%M:%S')}")

if 'df' in st.session_state:
    st.dataframe(st.session_state['df'], use_container_width=True)

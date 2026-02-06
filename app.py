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
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800},
                locale="fr-CH",
                timezone_id="Europe/Zurich"
            )
            page = context.new_page()
            
            # 1. Login
            st.info("🌍 Connexion à Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            page.fill("#username", u)
            page.fill("#password", p)
            page.keyboard.press("Enter")
            
            # 2. Attente forcée du changement de page
            st.info("👤 Chargement de la liste des profils...")
            # On attend que l'URL change (elle contient souvent 'select-profile' ou 'profile')
            page.wait_for_load_state("networkidle")
            time.sleep(5) # Pause réelle de 5 secondes
            
            # 3. Stratégie de clic multi-niveaux sur le profil
            st.info("🎯 Tentative de clic sur Nathan Erard...")
            
            # Option A : Par texte exact
            target = page.get_by_text("Nathan Erard", exact=False)
            if target.count() > 0:
                target.first.click()
            else:
                # Option B : Par sélecteur de liste Ephysio
                st.warning("Texte non trouvé, tentative par sélecteur de liste...")
                page.click(".profile-item, .list-group-item, a[href*='profile']")
            
            # 4. Vérification de l'entrée dans l'app
            st.info("📄 Accès aux factures...")
            # On force la destination pour ne pas rester bloqué sur l'accueil
            page.wait_for_url("**/app#**", timeout=30000)
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            
            # 5. Export
            st.info("📂 Ouverture menu Export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            time.sleep(2)
            page.click("text=Exporter")
            
            # Configuration Modale
            st.info("📅 Configuration de l'export...")
            page.wait_for_selector(".modal-content", timeout=15000)
            page.locator("select").select_option(label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 6. Téléchargement
            st.info("⏳ Téléchargement de l'Excel...")
            with page.expect_download(timeout=60000) as download_info:
                page.click("button:has-text('Créer'), .btn-primary")
            
            download = download_info.value
            path = "data_nathan.xlsx"
            download.save_as(path)
            
            browser.close()
            return path

        except Exception as e:
            if 'page' in locals():
                page.screenshot(path="debug_nathan.png")
            browser.close()
            st.error(f"Erreur de parcours : {e}")
            if os.path.exists("debug_nathan.png"):
                st.image("debug_nathan.png", caption="Vision du robot lors de l'erreur")
            return None

# Interface
st.title("🏥 Analyseur Facturation Ephysio")
u_in = st.sidebar.text_input("User", value=st.secrets.get("USER", ""))
p_in = st.sidebar.text_input("Pass", type="password", value=st.secrets.get("PWD", ""))

if st.sidebar.button("🚀 Synchroniser"):
    res = fetch_from_ephysio(u_in, p_in)
    if res:
        st.session_state['df'] = pd.read_excel(res)
        st.success("Données synchronisées !")

if 'df' in st.session_state:
    st.dataframe(st.session_state['df'], use_container_width=True)

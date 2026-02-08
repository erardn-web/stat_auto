import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
from playwright.sync_api import sync_playwright

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
            
            # 1. Accueil (Indispensable pour débloquer le formulaire)
            st.info("🌍 Accès au site Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="domcontentloaded")
            
            # 2. Accès au formulaire de connexion (On force le passage)
            st.info("🔗 Accès au formulaire...")
            try:
                # Tentative de clic sur le bouton de la page d'accueil
                page.click("a:has-text('Connexion'), text=Login", timeout=5000)
            except:
                # Si le bouton n'est pas trouvé, on force l'URL de login
                page.goto("https://ephysio.pharmedsolutions.ch/login")

            # 3. Saisie des identifiants
            st.info("🔑 Saisie des identifiants...")
            page.wait_for_selector("input[name*='user'], #username", timeout=15000)
            page.locator("input[type='text'], #username").first.fill(u)
            page.locator("input[type='password'], #password").first.fill(p)
            page.keyboard.press("Enter")
            
            # 4. Sélection du profil (DELAI 2s + Saisie du 'N')
            st.info("👤 Sélection du profil...")
            page.wait_for_load_state("networkidle")
            
            # CONSIGNE : 2 secondes
            time.sleep(2) 
            
            # Utilisation du sélecteur ng-model fourni
            selector_profil = 'input[ng-model="selectedClient"]'
            page.wait_for_selector(selector_profil, timeout=15000)
            
            # Activation et saisie du 'N'
            page.click(selector_profil)
            page.keyboard.type("N", delay=100)
            
            # On attend que la suggestion "Nathan Erard" apparaisse dans le menu Angular
            st.info("🎯 Sélection de Nathan Erard...")
            page.wait_for_selector("text=/Nathan Erard/i", timeout=10000)
            page.click("text=/Nathan Erard/i")

            # 5. Navigation Factures (Correction URL pour éviter retour accueil)
            st.info("📄 Accès aux factures...")
            page.wait_for_url("**/app#**", timeout=30000)
            page.goto("https://ephysio.pharmedsolutions.ch") 
            page.wait_for_load_state("networkidle")
            
            # 6. Menu Plus... et Export
            st.info("📂 Menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            page.wait_for_timeout(1500)
            page.click("text=Exporter")
            
            # 7. Configuration Modale
            st.info("📅 Configuration de l'export...")
            page.wait_for_selector(".modal-content", timeout=15000)
            page.locator("select").select_option(label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 8. Téléchargement
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
            st.error(f"Détail du blocage : {e}")
            if os.path.exists("debug_nathan.png"):
                st.image("debug_nathan.png", caption="Vision du robot")
            return None

# --- INTERFACE ---
st.title("🏥 Analyseur Facturation Ephysio")

with st.sidebar:
    u_side = st.text_input("Identifiant", value=st.secrets.get("USER", ""))
    p_side = st.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))
    btn_run = st.button("🚀 Synchroniser les données", type="primary")

if btn_run:
    if u_side and p_side:
        file_path = fetch_from_ephysio(u_side, p_side)
        if file_path:
            st.session_state['df_nathan'] = pd.read_excel(file_path)
            st.success("Synchronisation réussie !")
    else:
        st.error("Veuillez entrer vos identifiants.")

if 'df_nathan' in st.session_state:
    st.dataframe(st.session_state['df_nathan'], use_container_width=True)

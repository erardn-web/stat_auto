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
            
            # 1. Accueil & Accès Formulaire
            st.info("🌍 Accès au site Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="domcontentloaded")
            
            st.info("🔗 Accès au formulaire...")
            try:
                page.click("a:has-text('Connexion'), text=Login", timeout=5000)
            except:
                page.goto("https://ephysio.pharmedsolutions.ch")

            # 2. Saisie des identifiants (Ciblage précis par ID pour éviter les erreurs)
            st.info("🔑 Saisie des identifiants...")
            page.wait_for_selector("#username", timeout=15000)
            page.fill("#username", u)
            page.fill("#password", p)
            page.keyboard.press("Enter")
            
            # 3. Sélection du profil (FIX : On ignore le champ 'therapists')
            st.info("👤 Recherche du profil...")
            page.wait_for_load_state("networkidle")
            
            # Délai de 2 secondes comme demandé
            time.sleep(2) 
            
            # On cible UNIQUEMENT le champ Angular UI Typeahead via son ng-model
            selector_profil = 'input[ng-model="selectedClient"]'
            
            # On attend que CE champ spécifique soit visible
            page.wait_for_selector(selector_profil, timeout=15000)
            
            # Activation et saisie du 'N'
            page.click(selector_profil)
            page.keyboard.type("N", delay=100)
            
            # 4. Sélection de Nathan Erard
            st.info("🎯 Sélection de Nathan Erard...")
            # On attend que la suggestion contenant ton nom apparaisse
            page.wait_for_selector("text=/Nathan Erard/i", timeout=10000)
            page.click("text=/Nathan Erard/i")

            # 5. Navigation Factures
            st.info("📄 Accès à l'espace Facturation...")
            page.wait_for_url("**/app#**", timeout=30000)
            page.goto("https://ephysio.pharmedsolutions.ch") 
            page.wait_for_load_state("networkidle")
            
            # 6. Menu Plus... et Export
            st.info("📂 Menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            page.wait_for_timeout(1500)
            page.click("text=Exporter")
            
            # 7. Configuration Modale d'Export
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
                st.image("debug_nathan.png", caption="Dernière vue du robot")
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

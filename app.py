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
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800},
                locale="fr-CH",
                timezone_id="Europe/Zurich"
            )
            page = context.new_page()
            
            # 1. Accueil & Login
            st.info("🌍 Accès au site Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            
            st.info("🔑 Saisie des identifiants...")
            page.fill("#username", u)
            page.fill("#password", p)
            page.keyboard.press("Enter")
            
            # 2. Sélection du profil (Délai 2s + Saisie + Flèche Bas)
            st.info("👤 Recherche du profil...")
            page.wait_for_load_state("networkidle")
            time.sleep(2) # Délai demandé
            
            # Ciblage du champ Angular identifié
            selector_profil = 'input[ng-model="selectedClient"]'
            page.wait_for_selector(selector_profil, timeout=15000)
            page.click(selector_profil)
            
            # On tape "Nathan" lettre par lettre
            page.keyboard.type("Nathan", delay=100)
            time.sleep(1) # Attente que la liste apparaisse
            
            st.info("🎯 Sélection de 'Nathan Erard'...")
            try:
                # Tentative A : Clic direct sur le texte dans la liste de suggestions
                # On cherche l'élément de la liste (souvent un 'li' ou 'a') qui contient le nom
                suggestion = page.locator(".typeahead-step, .dropdown-menu li, a:has-text('Nathan Erard')").first
                if suggestion.is_visible():
                    suggestion.click()
                else:
                    # Tentative B : Utiliser le clavier (Flèche Bas + Entrée)
                    page.keyboard.press("ArrowDown")
                    page.wait_for_timeout(500)
                    page.keyboard.press("Enter")
            except:
                # Tentative C : Backup clavier pur
                page.keyboard.press("ArrowDown")
                page.keyboard.press("Enter")

            # 3. Navigation Factures
            st.info("📄 Accès à l'espace Facturation...")
            # On attend que l'URL change vers l'application
            page.wait_for_url("**/app#**", timeout=30000)
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            
            # 4. Menu Plus... et Export
            st.info("📂 Menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            time.sleep(1)
            page.click("text=Exporter")
            
            # 5. Configuration Modale
            st.info("📅 Configuration de l'export...")
            page.wait_for_selector(".modal-content", timeout=15000)
            page.locator("select").select_option(label="Factures")
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
            st.error(f"Détail : {e}")
            if os.path.exists("debug_nathan.png"):
                st.image("debug_nathan.png", caption="Vision du robot")
            return None

# --- INTERFACE ---
st.title("🏥 Analyseur Facturation Ephysio")

with st.sidebar:
    u_side = st.text_input("Identifiant", value=st.secrets.get("USER", ""))
    p_side = st.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))
    if st.button("🚀 Synchroniser", type="primary"):
        res = fetch_from_ephysio(u_side, p_side)
        if res:
            st.session_state['df_nathan'] = pd.read_excel(res)
            st.success("Synchronisation réussie !")

if 'df_nathan' in st.session_state:
    st.dataframe(st.session_state['df_nathan'], use_container_width=True)

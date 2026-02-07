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
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800},
                locale="fr-CH",
                timezone_id="Europe/Zurich"
            )
            page = context.new_page()
            
            # 1. Connexion
            st.info("🌍 Accès à Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="domcontentloaded")
            
            st.info("🔑 Saisie des identifiants...")
            page.wait_for_selector("input", timeout=20000)
            page.locator("input[type='text'], #username").first.fill(u)
            page.locator("input[type='password'], #password").first.fill(p)
            
            # On simule l'appui sur Entrée pour valider
            page.keyboard.press("Enter")
            
            # 2. Transition vers le profil
            st.info("👤 Chargement de la liste des profils...")
            # On attend que l'URL change (signe que le login est accepté)
            page.wait_for_load_state("networkidle")
            # PAUSE CRUCIALE : on laisse 5 secondes au système pour afficher les profils
            time.sleep(5) 
            
            # 3. Sélection du PREMIER PROFIL
            # On cherche n'importe quel élément cliquable qui ressemble à un choix de compte
            st.info("🎯 Clic sur le premier profil trouvé...")
            page.wait_for_selector(".profile-item, .list-group-item, a[href*='select'], .card, [role='button']", timeout=30000)
            
            # On force le clic sur le premier élément de la liste
            page.locator(".profile-item, .list-group-item, a[href*='select'], .card, [role='button']").first.click()
            
            # 4. Accès aux Factures
            st.info("📄 Navigation vers les factures...")
            page.wait_for_url("**/app#**", timeout=30000)
            page.goto("https://ephysio.pharmedsolutions.ch")
            page.wait_for_load_state("networkidle")
            
            # 5. Export
            st.info("📂 Ouverture menu Export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            time.sleep(2)
            page.click("text=Exporter")
            
            # 6. Configuration Modale
            st.info("📅 Configuration de l'export...")
            page.wait_for_selector(".modal-content", timeout=15000)
            page.locator("select").select_option(label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 7. Téléchargement
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
            st.error(f"Erreur de parcours : {e}")
            if os.path.exists("debug_nathan.png"):
                st.image("debug_nathan.png", caption="Vision du robot lors du blocage")
            return None

# Interface
st.title("🏥 Analyseur Facturation Ephysio")
u_in = st.sidebar.text_input("User", value=st.secrets.get("USER", ""))
p_in = st.sidebar.text_input("Pass", type="password", value=st.secrets.get("PWD", ""))

if st.sidebar.button("🚀 Synchroniser"):
    res = fetch_from_ephysio(u_in, p_in)
    if res:
        st.session_state['df'] = pd.read_excel(res)
        st.success("Synchronisation réussie !")

if 'df' in st.session_state:
    st.dataframe(st.session_state['df'], use_container_width=True)

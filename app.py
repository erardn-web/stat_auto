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
            
            # 1. Login Direct (Plus rapide que passer par l'accueil)
            st.info("🚀 Accès direct au login...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="domcontentloaded")
            
            # Saisie rapide
            page.fill("#username", u)
            page.fill("#password", p)
            page.keyboard.press("Enter")
            
            # 2. Transition Profil (Temps diminué à 2s au lieu de 10s)
            st.info("👤 Recherche du profil...")
            time.sleep(2) 
            
            # Ciblage précis du champ de recherche profil pour éviter le bug "therapists"
            # On cherche un champ de type texte ou recherche, pas un "number"
            search_input = page.locator("input[type='text'], .select2-search__field, input[placeholder*='Chercher']").first
            search_input.wait_for(state="visible", timeout=10000)
            search_input.click()
            
            # Saisie de la lettre N
            page.keyboard.type("N")
            
            # Sélection de Nathan Erard
            st.info("🎯 Sélection de Nathan Erard...")
            page.wait_for_selector("text=/Nathan Erard/i", timeout=10000)
            page.click("text=/Nathan Erard/i")

            # 3. Navigation Factures
            st.info("📄 Accès aux factures...")
            page.wait_for_url("**/app#**", timeout=20000)
            page.goto("https://ephysio.pharmedsolutions.ch") 
            page.wait_for_load_state("networkidle")
            
            # 4. Export
            st.info("📂 Export Excel...")
            page.wait_for_selector("button:has-text('Plus')", timeout=15000)
            page.click("button:has-text('Plus')")
            time.sleep(1)
            page.click("text=Exporter")
            
            # Configuration Modale
            page.wait_for_selector(".modal-content")
            page.locator("select").select_option(label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 5. Téléchargement
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

# Interface
st.title("🏥 Analyseur Ephysio")
u_side = st.sidebar.text_input("Identifiant", value=st.secrets.get("USER", ""))
p_side = st.sidebar.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))

if st.sidebar.button("🚀 Synchroniser"):
    res = fetch_from_ephysio(u_side, p_side)
    if res:
        st.session_state['df_nathan'] = pd.read_excel(res)
        st.success("Synchronisé !")

if 'df_nathan' in st.session_state:
    st.dataframe(st.session_state['df_nathan'], use_container_width=True)

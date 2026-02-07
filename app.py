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
            
            # 1. Accueil & Login
            st.info("🌍 Accès au site Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="domcontentloaded")
            
            try:
                page.click("a:has-text('Connexion'), text=Login", timeout=5000)
            except:
                page.goto("https://ephysio.pharmedsolutions.ch")

            st.info("🔑 Saisie des identifiants...")
            page.wait_for_selector("#username", timeout=20000)
            page.fill("#username", u)
            page.fill("#password", p)
            page.keyboard.press("Enter")
            
            # 2. Sélection du profil (FIX avec ng-model)
            st.info("👤 Recherche du profil...")
            page.wait_for_load_state("networkidle")
            time.sleep(2) # Les 2 secondes demandées
            
            # Ciblage du champ Angular spécifique
            target_input = page.locator('input[ng-model="selectedClient"]')
            target_input.wait_for(state="visible", timeout=15000)
            
            # On clique, on vide (au cas où) et on tape "Nathan"
            target_input.click()
            page.keyboard.type("Nathan", delay=150)
            
            st.info("🎯 Sélection de Nathan Erard dans la liste...")
            # On attend que la liste de suggestions d'Angular apparaisse
            # On clique sur l'élément qui contient le texte complet
            page.wait_for_selector("text=/Nathan Erard/i", timeout=10000)
            page.click("text=/Nathan Erard/i")

            # 3. Navigation Factures
            st.info("📄 Accès à l'espace Facturation...")
            page.wait_for_url("**/app#**", timeout=30000)
            page.goto("https://ephysio.pharmedsolutions.ch") 
            page.wait_for_load_state("networkidle")
            
            # 4. Export
            st.info("📂 Menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            page.wait_for_timeout(1500)
            page.click("text=Exporter")
            
            # 5. Configuration Modale
            st.info("📅 Configuration de l'export...")
            page.wait_for_selector(".modal-content", timeout=15000)
            page.locator("select").select_option(label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 6. Téléchargement
            st.info("⏳ Téléchargement...")
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

# Interface Streamlit
st.title("🏥 Analyseur Facturation Ephysio")

with st.sidebar:
    st.header("🔑 Connexion")
    u_side = st.text_input("Identifiant", value=st.secrets.get("USER", ""))
    p_side = st.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))
    if st.button("🚀 Synchroniser", type="primary"):
        res = fetch_from_ephysio(u_side, p_side)
        if res:
            st.session_state['df_nathan'] = pd.read_excel(res)
            st.success("Synchronisé !")

if 'df_nathan' in st.session_state:
    st.dataframe(st.session_state['df_nathan'], use_container_width=True)

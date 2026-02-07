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
                args=[
                    "--no-sandbox", 
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage"
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800},
                locale="fr-CH",
                timezone_id="Europe/Zurich" # Fix fuseau horaire
            )
            page = context.new_page()
            
            # 1. Accueil & Connexion
            st.info("🌍 Accès au site Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")

            st.info("🔑 Saisie des identifiants...")
            page.wait_for_selector("input", timeout=20000)
            page.locator("input[type='text'], #username").first.fill(u)
            page.locator("input[type='password'], #password").first.fill(p)
            page.keyboard.press("Enter")
            
            # 2. Transition vers le profil (CRITIQUE)
            st.info("⏳ Validation et chargement des profils (Attente 15s)...")
            page.wait_for_load_state("networkidle")
            # On laisse volontairement beaucoup de temps pour charger l'interface de profil
            time.sleep(15) 
            
            # 3. Sélection du profil "Nathan Erard"
            st.info("👤 Recherche du profil : Nathan Erard...")
            try:
                # On cherche le texte Nathan Erard de façon insensible à la casse
                page.wait_for_selector("text=/Nathan Erard/i", timeout=30000)
                page.click("text=/Nathan Erard/i")
                st.toast("Profil Nathan Erard sélectionné !")
            except Exception as profil_err:
                st.warning(f"Texte exact non trouvé, tentative sur le premier élément de liste. Erreur : {profil_err}")
                page.click(".profile-item, .list-group-item, a[href*='select'], .card")

            # 4. Navigation Factures
            st.info("📄 Accès à l'espace Facturation...")
            page.wait_for_url("**/app#**", timeout=40000)
            page.goto("https://ephysio.pharmedsolutions.ch") 
            page.wait_for_load_state("networkidle")
            
            # 5. Menu Plus... et Export
            st.info("📂 Menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=25000)
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
            st.error(f"Détail du blocage : {e}")
            if os.path.exists("debug_nathan.png"):
                st.image("debug_nathan.png", caption="Vision du robot lors de l'erreur")
            return None

# --- INTERFACE ---
st.title("🏥 Analyseur Facturation Ephysio")

with st.sidebar:
    u_side = st.text_input("Identifiant", value=st.secrets.get("USER", ""))
    p_side = st.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))
    btn = st.button("🚀 Synchroniser", type="primary")

if btn:
    res = fetch_from_ephysio(u_side, p_side)
    if res:
        st.session_state['df_nathan'] = pd.read_excel(res)
        st.success("Synchronisation réussie !")

if 'df_nathan' in st.session_state:
    st.dataframe(st.session_state['df_nathan'], use_container_width=True)

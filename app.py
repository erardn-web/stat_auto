import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="Ephysio - Nathan Erard", layout="wide")

def fetch_from_ephysio(u, p):
    with sync_playwright() as p_wr:
        try:
            # On utilise des arguments pour masquer le fait que c'est un robot
            browser = p_wr.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True, # Obligatoire sur Streamlit Cloud, mais on va masquer les traces
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--window-position=0,0",
                    "--ignore-certificate-errors"
                ]
            )
            
            # On crée un contexte avec des permissions spécifiques
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800},
                timezone_id="Europe/Zurich",
                locale="fr-CH"
            )
            
            # Injection d'un script pour supprimer l'indicateur "webdriver" (anti-robot)
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 1. Connexion
            st.info("🌍 Accès direct à la page de LOGIN...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            
            page.fill("#username", u)
            page.fill("#password", p)
            
            # On clique physiquement sur le bouton au lieu d'appuyer sur Entrée
            st.info("🚀 Clic sur le bouton Connexion...")
            page.click("button[type='submit']")
            
            # 2. Attente et vérification du profil
            st.info("👤 Attente du profil (Nathan Erard)...")
            # On attend que l'un des sélecteurs de profil soit visible
            page.wait_for_selector("text=Nathan Erard, .profile-item, .list-group-item", timeout=30000)
            
            # Clic spécifique
            if page.get_by_text("Nathan Erard").count() > 0:
                page.get_by_text("Nathan Erard").first.click()
            else:
                page.locator(".profile-item, .list-group-item").first.click()
            
            # 3. Forcer l'accès à l'URL de facturation
            st.info("📄 Redirection forcée vers les Factures...")
            time.sleep(3) # Pause pour laisser la session s'établir
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            
            # 4. Export
            st.info("📂 Ouverture du menu d'export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            time.sleep(1)
            page.click("text=Exporter")
            
            # 5. Modale
            page.wait_for_selector(".modal-content")
            page.locator("select").select_option(label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 6. Téléchargement
            st.info("⏳ Création de l'Excel...")
            with page.expect_download(timeout=60000) as download_info:
                page.click("button:has-text('Créer le fichier Excel')")
            
            download = download_info.value
            path = "data_nathan.xlsx"
            download.save_as(path)
            
            browser.close()
            return path

        except Exception as e:
            if 'page' in locals():
                page.screenshot(path="debug_final.png")
            browser.close()
            st.error(f"Échec : {e}")
            if os.path.exists("debug_final.png"):
                st.image("debug_final.png", caption="Image du blocage")
            return None

# --- Interface ---
st.title("Analyseur Ephysio")
u = st.sidebar.text_input("Login", value=st.secrets.get("USER", ""))
p = st.sidebar.text_input("Password", type="password", value=st.secrets.get("PWD", ""))

if st.sidebar.button("🚀 Lancer"):
    res = fetch_from_ephysio(u, p)
    if res:
        st.session_state['df'] = pd.read_excel(res)
        st.success("Terminé !")

if 'df' in st.session_state:
    st.dataframe(st.session_state['df'])

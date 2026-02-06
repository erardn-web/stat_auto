import streamlit as st
import pandas as pd
from datetime import datetime
import os
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="Analyseur Ephysio", layout="wide")

def fetch_from_ephysio(u, p):
    with sync_playwright() as p_wr:
        try:
            browser = p_wr.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True, 
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # 1. Connexion
            st.info("🌍 Chargement de la page de login...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            
            # Saisie des identifiants
            st.info("🔑 Saisie des accès...")
            page.wait_for_selector("#username", timeout=15000)
            page.fill("#username", u)
            page.fill("#password", p)
            
            # --- LA SÉCURITÉ : SIMULER LA TOUCHE ENTRÉE ---
            st.info("🚀 Envoi du formulaire...")
            page.keyboard.press("Enter")
            
            # On attend que la page change (soit le profil, soit l'app)
            page.wait_for_load_state("networkidle")
            
            # 2. Sélection du profil "Nathan Erard"
            st.info("👤 Recherche du profil...")
            # On attend un peu plus longtemps ici
            page.wait_for_selector("text=Nathan Erard", timeout=30000)
            page.click("text=Nathan Erard")
            
            # 3. Navigation et Export
            st.info("📄 Accès aux factures...")
            page.wait_for_url("**/app#**", timeout=30000)
            page.goto("https://ephysio.pharmedsolutions.ch")
            
            st.info("📂 Menu export...")
            page.wait_for_selector("button:has-text('Plus')")
            page.click("button:has-text('Plus')")
            page.click("text=Exporter")
            
            st.info("📅 Configuration de l'export...")
            page.wait_for_selector(".modal-content")
            page.locator("select").select_option(label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 4. Téléchargement
            st.info("⏳ Téléchargement...")
            with page.expect_download(timeout=60000) as download_info:
                page.locator("button:has-text('Créer le fichier Excel')").click()
            
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
                st.image("debug_nathan.png", caption="Vision du robot")
            return None

# --- INTERFACE ---
st.title("🏥 Analyseur Facturation Ephysio")
u_val = st.sidebar.text_input("User", value=st.secrets.get("USER", ""))
p_val = st.sidebar.text_input("Pass", type="password", value=st.secrets.get("PWD", ""))

if st.sidebar.button("🚀 Lancer"):
    res = fetch_from_ephysio(u_val, p_val)
    if res:
        st.session_state['df'] = pd.read_excel(res)
        st.success("Données synchronisées !")

if 'df' in st.session_state:
    st.dataframe(st.session_state['df'], use_container_width=True)

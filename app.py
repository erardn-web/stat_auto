import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
from playwright.sync_api import sync_playwright

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Analyseur Ephysio - Nathan Erard", layout="wide")

def fetch_from_ephysio(u, p):
    with sync_playwright() as p_wr:
        try:
            # Lancement de Chromium système
            browser = p_wr.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True, 
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            
            # --- FIX FUSEAU HORAIRE ---
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                timezone_id="Europe/Zurich",
                locale="fr-CH",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # 1. Connexion (L'URL directe de login)
            st.info("🌍 Connexion à Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            
            # Saisie des identifiants
            page.wait_for_selector("#username", timeout=15000)
            page.fill("#username", u)
            page.fill("#password", p)
            
            # Simulation de la touche Entrée (celle qui avait débloqué la situation)
            st.info("🚀 Envoi du formulaire...")
            page.keyboard.press("Enter")
            
            # 2. Sélection du profil "Nathan Erard"
            st.info("👤 Recherche du profil...")
            # On attend que la page se stabilise après le login
            page.wait_for_load_state("networkidle")
            time.sleep(3) # Petite pause humaine
            
            # La méthode get_by_text qui avait réussi
            page.get_by_text("Nathan Erard", exact=False).first.click()
            
            # 3. Navigation vers les factures
            st.info("📄 Accès aux factures...")
            page.wait_for_url("**/app#**", timeout=30000)
            # On force l'URL directe du module invoices
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            
            # 4. Menu "Plus..." et Export
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
            st.info("⏳ Génération de l'Excel...")
            with page.expect_download(timeout=60000) as download_info:
                page.click("button:has-text('Créer le fichier Excel')")
            
            download = download_info.value
            path = "data_nathan.xlsx"
            download.save_as(path)
            
            browser.close()
            return path

        except Exception as e:
            if 'page' in locals():
                page.screenshot(path="debug_error.png")
            browser.close()
            st.error(f"Erreur rencontrée : {e}")
            if os.path.exists("debug_error.png"):
                st.image("debug_error.png", caption="Vision du robot lors du blocage")
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
        st.session_state['df'] = pd.read_excel(res)
        st.success("Données synchronisées !")

if 'df' in st.session_state:
    st.dataframe(st.session_state['df'], use_container_width=True)

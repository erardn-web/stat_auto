import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
from playwright.sync_api import sync_playwright

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Ephysio - Nathan Erard", layout="wide")

def fetch_from_ephysio(u, p):
    with sync_playwright() as p_wr:
        try:
            # Lancement de Chromium (Utilisation du binaire système via packages.txt)
            browser = p_wr.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True, 
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            
            # --- LE FIX DU FUSEAU HORAIRE EST ICI ---
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                timezone_id="Europe/Zurich",  # Forcer l'heure suisse
                locale="fr-CH"               # Forcer la langue
            )
            page = context.new_page()
            
            # 1. Connexion (L'URL qui fonctionnait)
            st.info("🌍 Connexion à Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            
            # Remplissage par ID (le plus rapide)
            page.fill("#username", u)
            page.fill("#password", p)
            
            # On clique sur le bouton et on attend que la page de profil charge
            with page.expect_navigation(wait_until="networkidle"):
                page.click("button[type='submit']")
            
            # 2. Sélection du profil (Nathan Erard)
            st.info("👤 Sélection du profil...")
            # Petite pause humaine pour éviter le bug de détection
            time.sleep(2) 
            
            # On cherche Nathan Erard (insensible à la casse)
            page.wait_for_selector("text=/Nathan Erard/i", timeout=30000)
            page.click("text=/Nathan Erard/i")
            
            # 3. Navigation vers les factures
            st.info("📄 Accès aux factures...")
            page.wait_for_url("**/app#**", timeout=30000)
            # On force l'URL directe du module
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
            # Sélectionner 'Factures' et remplir la date
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
                st.image("debug_error.png", caption="Dernière vue avant l'erreur")
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
        st.success("Données récupérées !")

if 'df' in st.session_state:
    st.dataframe(st.session_state['df'], use_container_width=True)

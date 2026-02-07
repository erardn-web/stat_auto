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
            # 1. Lancement du navigateur système
            browser = p_wr.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True, 
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            
            # --- LE FIX CRUCIAL : On synchronise le navigateur sur l'heure Suisse ---
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                timezone_id="Europe/Zurich",
                locale="fr-CH"
            )
            page = context.new_page()
            
            # 2. Connexion (URL directe)
            st.info("🌍 Connexion à Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            
            # Saisie des identifiants (Sélecteurs ID qui marchaient)
            page.fill("#username", u)
            page.fill("#password", p)
            
            # Clic sur le bouton de soumission
            page.click("button[type='submit']")
            
            # 3. Sélection du profil "Nathan Erard"
            st.info("👤 Sélection du profil...")
            # On attend que le profil soit visible (étape qui réussissait avant le bug horaire)
            page.wait_for_selector("text=Nathan Erard", timeout=30000)
            page.click("text=Nathan Erard")
            
            # 4. Navigation Factures
            st.info("📄 Accès aux factures...")
            page.wait_for_url("**/app#**", timeout=30000)
            # On force l'URL pour éviter de rester sur le dashboard
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            
            # 5. Menu "Plus..." et Export
            st.info("📂 Menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            time.sleep(1) # Pause pour l'animation du menu
            page.click("text=Exporter")
            
            # 6. Configuration Modale
            st.info("📅 Configuration de l'export...")
            page.wait_for_selector(".modal-content", timeout=15000)
            # Sélectionner 'Factures' et remplir la date de début
            page.locator("select").select_option(label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 7. Téléchargement
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
    if u_side and p_side:
        res = fetch_from_ephysio(u_side, p_side)
        if res:
            st.session_state['df_nathan'] = pd.read_excel(res)
            st.success("Données synchronisées avec succès !")
    else:
        st.error("Veuillez entrer vos identifiants.")

if 'df_nathan' in st.session_state:
    st.divider()
    st.write("### Tableau des données")
    st.dataframe(st.session_state['df_nathan'], use_container_width=True)

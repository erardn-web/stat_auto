import streamlit as st
import pandas as pd
from datetime import datetime
import os
from playwright.sync_api import sync_playwright

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Ephysio Analytics - Nathan Erard", layout="wide")

def fetch_from_ephysio(u, p):
    """Pilote le navigateur système pour récupérer l'export Excel"""
    with sync_playwright() as p_wr:
        try:
            # On utilise le binaire installé par packages.txt (chemin standard Linux)
            # Cela évite l'erreur "Executable doesn't exist"
            browser = p_wr.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True, 
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-setuid-sandbox"]
            )
            context = browser.new_context(viewport={'width': 1280, 'height': 800})
            page = context.new_page()
            
            # 1. Connexion
            st.info("🌍 Connexion à Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle", timeout=60000)
            page.fill("#username", u)
            page.fill("#password", p)
            page.click("button[type='submit']")
            
            # 2. Sélection du profil "Nathan Erard"
            st.info("👤 Sélection du profil : Nathan Erard...")
            page.wait_for_selector("text=Nathan Erard", timeout=30000)
            page.click("text=Nathan Erard")
            
            # 3. Navigation Factures
            st.info("📄 Chargement des factures...")
            page.wait_for_url("**/app#**", timeout=30000)
            page.goto("https://ephysio.pharmedsolutions.ch")
            page.wait_for_load_state("networkidle")
            
            # 4. Menu Plus... et Export
            st.info("📂 Accès au menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            page.wait_for_timeout(1000) 
            page.click("text=Exporter")
            
            # 5. Configuration Modale
            st.info("📅 Configuration de l'export (01.01.2025)...")
            page.wait_for_selector(".modal-content", timeout=15000)
            page.select_option("select", label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 6. Créer et Télécharger
            st.info("⏳ Génération de l'Excel...")
            with page.expect_download(timeout=60000) as download_info:
                page.click("button:has-text('Créer le fichier Excel')")
            
            download = download_info.value
            path = "data_nathan.xlsx"
            download.save_as(path)
            
            browser.close()
            return path

        except Exception as e:
            # Capture d'écran automatique en cas de pépin
            if 'page' in locals():
                page.screenshot(path="debug_error.png")
            browser.close()
            st.error(f"Erreur de navigation : {e}")
            if os.path.exists("debug_error.png"):
                st.image("debug_error.png", caption="Dernière vue du robot avant l'erreur")
            return None

# --- INTERFACE UTILISATEUR ---
st.title("🏥 Analyseur Facturation Ephysio")
st.subheader("Compte : Nathan Erard")

with st.sidebar:
    st.header("🔑 Identifiants")
    u_val = st.text_input("Identifiant", value=st.secrets.get("USER", ""))
    p_val = st.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))
    
    btn_sync = st.button("🚀 Synchroniser maintenant", type="primary")

if btn_sync:
    if u_val and p_val:
        res = fetch_from_ephysio(u_val, p_val)
        if res:
            st.session_state['df_nathan'] = pd.read_excel(res)
            st.success("Données synchronisées avec succès !")
    else:
        st.error("Veuillez configurer vos identifiants.")

# --- AFFICHAGE ---
if 'df_nathan' in st.session_state:
    df = st.session_state['df_nathan']
    st.divider()
    st.write(f"### {len(df)} Factures trouvées")
    st.dataframe(df, use_container_width=True)
    
    with open("data_nathan.xlsx", "rb") as f:
        st.download_button("📥 Télécharger le fichier Excel", f, file_name="export_nathan.xlsx")
else:
    st.info("Lancez la synchronisation pour importer les données.")

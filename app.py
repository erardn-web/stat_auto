import streamlit as st
import pandas as pd
from datetime import datetime
import os
from playwright.sync_api import sync_playwright

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Ephysio Auto-Analyse", layout="wide")

def fetch_from_ephysio(u, p):
    """Pilote le navigateur pour récupérer l'export Excel"""
    with sync_playwright() as p_wr:
        # Lancement de Chromium avec les paramètres de compatibilité Cloud
        try:
            browser = p_wr.chromium.launch(
                headless=True, 
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-setuid-sandbox"]
            )
        except Exception as e:
            st.error(f"Erreur au lancement du navigateur : {e}")
            return None
            
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            # 1. Connexion
            st.info("🌍 Connexion à Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle", timeout=60000)
            
            page.wait_for_selector("#username", timeout=20000)
            page.fill("#username", u)
            page.fill("#password", p)
            page.click("button[type='submit']")
            
            # 2. Sélection du profil
            st.info("👤 Choix du profil...")
            page.wait_for_selector(".profile-item, .list-group-item", timeout=30000)
            page.click(".profile-item >> nth=0") 
            
            # 3. Navigation Factures
            st.info("📄 Chargement des factures...")
            page.wait_for_url("**/app#**", timeout=30000)
            page.goto("https://ephysio.pharmedsolutions.ch")
            page.wait_for_load_state("networkidle")
            
            # 4. Menu Plus... et Export
            st.info("📂 Ouverture du menu export...")
            page.click("button:has-text('Plus')")
            page.wait_for_timeout(1000)
            page.click("text=Exporter")
            
            # 5. Configuration Modale
            st.info("📅 Configuration des dates (01.01.2025)...")
            page.wait_for_selector(".modal-content", timeout=15000)
            page.select_option("select", label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 6. Créer et Télécharger
            st.info("⏳ Génération de l'Excel...")
            with page.expect_download(timeout=60000) as download_info:
                page.click("button:has-text('Créer le fichier Excel')")
            
            download = download_info.value
            path = "data_ephysio.xlsx"
            download.save_as(path)
            
            browser.close()
            return path

        except Exception as e:
            page.screenshot(path="debug_error.png")
            browser.close()
            st.error(f"Erreur de navigation : {e}")
            if os.path.exists("debug_error.png"):
                st.image("debug_error.png", caption="Capture écran du robot")
            return None

# --- INTERFACE ---
st.title("🏥 Analyseur Facturation Ephysio")

with st.sidebar:
    st.header("🔑 Identifiants")
    u_val = st.text_input("Identifiant", value=st.secrets.get("USER", ""))
    p_val = st.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))
    
    if st.button("🚀 Synchroniser Ephysio", type="primary"):
        if u_val and p_val:
            res = fetch_from_ephysio(u_val, p_val)
            if res:
                st.session_state['df_brut'] = pd.read_excel(res)
                st.success("Données synchronisées !")
        else:
            st.error("Identifiants manquants.")

if 'df_brut' in st.session_state:
    st.divider()
    df = st.session_state['df_brut']
    st.subheader("📊 Aperçu des données")
    st.dataframe(df, use_container_width=True)
    
    with open("data_ephysio.xlsx", "rb") as f:
        st.download_button("📥 Télécharger l'Excel extrait", f, file_name="export_ephysio.xlsx")
else:
    st.info("Utilisez la barre latérale pour importer vos données.")

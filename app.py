import streamlit as st
import pandas as pd
from datetime import datetime
import os
import subprocess
from playwright.sync_api import sync_playwright

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Analyseur Ephysio Pro", layout="wide")

# --- INITIALISATION PLAYWRIGHT (CRUCIAL POUR LE CLOUD) ---
def install_playwright_if_needed():
    """Vérifie et installe les navigateurs si absent (spécifique Streamlit Cloud)"""
    try:
        # On tente de lancer une commande simple pour voir si playwright est prêt
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"Erreur lors de l'initialisation système : {e}")

# --- FONCTION DE RÉCUPÉRATION EPHYSIO ---
def fetch_from_ephysio(u, p):
    install_playwright_if_needed()
    
    with sync_playwright() as p_wr:
        # Lancement du navigateur avec arguments de compatibilité Cloud
        browser = p_wr.chromium.launch(
            headless=True, 
            args=[
                "--no-sandbox", 
                "--disable-dev-shm-usage", 
                "--disable-gpu",
                "--disable-setuid-sandbox"
            ]
        )
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            # 1. Connexion
            st.info("🔑 Connexion à Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", timeout=60000)
            page.fill("input[name='_username']", u)
            page.fill("input[name='_password']", p)
            page.click("button[type='submit']")
            
            # 2. Sélection du profil
            st.info("👤 Sélection du profil...")
            page.wait_for_selector(".profile-item, .list-group-item", timeout=20000)
            page.click(".profile-item >> nth=0") 
            
            # 3. Page Factures
            page.wait_for_url("**/app#**", timeout=20000)
            page.goto("https://ephysio.pharmedsolutions.ch")
            page.wait_for_load_state("networkidle")
            
            # 4. Menu Plus... > Exporter
            st.info("📂 Accès au menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=15000)
            page.click("button:has-text('Plus')")
            page.click("text=Exporter")
            
            # 5. Configuration Fenêtre Export (Modale)
            st.info("📅 Configuration des dates (01.01.2025)...")
            page.wait_for_selector("div.modal-content select", timeout=10000)
            page.select_option("div.modal-content select", label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 6. Créer l'Excel et Télécharger
            with page.expect_download() as download_info:
                page.click("button:has-text('Créer le fichier Excel')")
            
            download = download_info.value
            path = "data_ephysio.xlsx"
            download.save_as(path)
            
            browser.close()
            return path

        except Exception as e:
            # Capture d'écran pour le debug affichée dans Streamlit
            page.screenshot(path="debug_error.png")
            browser.close()
            st.error(f"Erreur lors de la navigation : {e}")
            if os.path.exists("debug_error.png"):
                st.image("debug_error.png", caption="Dernière vue du robot")
            return None

# --- INTERFACE UTILISATEUR ---
st.title("🏥 Analyseur Facturation Ephysio")

with st.sidebar:
    st.header("🔑 Identifiants")
    u_default = st.secrets.get("USER", "")
    p_default = st.secrets.get("PWD", "")
    
    user_in = st.text_input("Identifiant", value=u_default)
    pwd_in = st.text_input("Mot de passe", type="password", value=p_default)
    
    btn_sync = st.button("🚀 Synchroniser Ephysio", type="primary")

if btn_sync:
    if user_in and pwd_in:
        file_path = fetch_from_ephysio(user_in, pwd_in)
        if file_path:
            st.session_state['df_brut'] = pd.read_excel(file_path)
            st.success("Données récupérées !")
    else:
        st.error("Identifiants manquants.")

# --- AFFICHAGE ET ANALYSE ---
if 'df_brut' in st.session_state:
    df = st.session_state['df_brut'].copy()
    
    st.divider()
    st.subheader("📊 Données Extraites")
    
    # Affichage du tableau
    st.dataframe(df, use_container_width=True)
    
    # Export manuel
    with open("data_ephysio.xlsx", "rb") as f:
        st.download_button(
            label="📥 Télécharger l'Excel extrait",
            data=f,
            file_name=f"ephysio_{datetime.now().strftime('%d-%m-%Y')}.xlsx"
        )
else:
    st.info("Utilisez la barre latérale pour importer vos données.")

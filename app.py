import streamlit as st
import pandas as pd
from datetime import datetime
import os
import sys

# --- FORCER L'INSTALLATION DES NAVIGATEURS POUR LE CLOUD ---
# Cette étape s'exécute une seule fois au démarrage sur Streamlit Cloud
try:
    import playwright
except ImportError:
    os.system("pip install playwright")

# Commande critique pour installer les binaires de Chromium sur le serveur
if "PLAYWRIGHT_INSTALLED" not in st.session_state:
    os.system("python -m playwright install chromium")
    st.session_state["PLAYWRIGHT_INSTALLED"] = True

from playwright.sync_api import sync_playwright

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Analyseur Ephysio Pro", layout="wide")

# --- FONCTION DE RÉCUPÉRATION ---
def fetch_from_ephysio(u, p):
    with sync_playwright() as p_wr:
        # Configuration robuste pour éviter les erreurs de droits/sandbox
        browser = p_wr.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
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
            
            # 3. Accès page Factures
            page.wait_for_url("**/app#**", timeout=20000)
            page.goto("https://ephysio.pharmedsolutions.ch")
            page.wait_for_load_state("networkidle")
            
            # 4. Menu Plus... et Exporter
            st.info("📂 Ouverture du menu Export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=15000)
            page.click("button:has-text('Plus')")
            page.click("text=Exporter")
            
            # 5. Configuration de la fenêtre d'export
            st.info("📅 Configuration des dates (01.01.2025)...")
            page.wait_for_selector("div.modal-content select", timeout=10000)
            # Sélectionner "Factures" dans le menu déroulant
            page.select_option("div.modal-content select", label="Factures")
            # Remplir la date de début
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 6. Créer le fichier et Télécharger
            with page.expect_download() as download_info:
                page.click("button:has-text('Créer le fichier Excel')")
            
            download = download_info.value
            path = "data_ephysio.xlsx"
            download.save_as(path)
            
            browser.close()
            return path

        except Exception as e:
            # En cas d'erreur, capture d'écran pour comprendre
            page.screenshot(path="debug_error.png")
            browser.close()
            st.error(f"Détail de l'erreur : {e}")
            if os.path.exists("debug_error.png"):
                st.image("debug_error.png", caption="Dernière vue avant l'erreur")
            return None

# --- INTERFACE UTILISATEUR ---
st.title("🏥 Analyseur Facturation Ephysio")
st.markdown("Récupération automatique et analyse des données de facturation.")

with st.sidebar:
    st.header("Connexion Ephysio")
    # On essaye de récupérer les codes via les secrets de Streamlit Cloud
    u_default = st.secrets.get("USER", "")
    p_default = st.secrets.get("PWD", "")
    
    user_in = st.text_input("Identifiant", value=u_default)
    pwd_in = st.text_input("Mot de passe", type="password", value=p_default)
    
    if st.button("🚀 Lancer la Synchronisation", type="primary"):
        if user_in and pwd_in:
            file_path = fetch_from_ephysio(user_in, pwd_in)
            if file_path:
                st.session_state['df_brut'] = pd.read_excel(file_path)
                st.success("Données récupérées avec succès !")
        else:
            st.error("Veuillez entrer vos identifiants.")

# --- AFFICHAGE ET ANALYSE ---
if 'df_brut' in st.session_state:
    df = st.session_state['df_brut'].copy()
    
    st.divider()
    st.subheader("📊 Aperçu des données extraites")
    
    # Affichage du tableau brut
    st.dataframe(df, use_container_width=True)
    
    # Bouton pour télécharger l'excel généré sur votre ordinateur
    with open("data_ephysio.xlsx", "rb") as f:
        st.download_button(
            label="📥 Télécharger l'Excel brut",
            data=f,
            file_name=f"ephysio_export_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Utilisez la barre latérale pour vous connecter et importer vos données Ephysio.")

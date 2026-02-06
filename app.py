import streamlit as st
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Ephysio Auto-Analyse", layout="wide")

def fetch_from_ephysio(u, p):
    with sync_playwright() as p_wr:
        # Configuration spécifique pour le cloud Streamlit
        browser = p_wr.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            # 1. Connexion
            st.info("Connexion à Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch")
            page.fill("input[name='_username']", u)
            page.fill("input[name='_password']", p)
            page.click("button[type='submit']")
            
            # 2. Sélection du profil
            # On attend que la page de choix de profil apparaisse
            st.info("Sélection du profil en cours...")
            page.wait_for_selector(".profile-item, .list-group-item", timeout=15000)
            # On clique sur le premier profil de la liste
            page.click(".profile-item >> nth=0") 
            
            # 3. Accès aux factures
            page.wait_for_url("**/app#**") # Attend le chargement de l'app
            page.goto("https://ephysio.pharmedsolutions.ch")
            
            # 4. Menu déroulant "Plus..." et Exporter
            st.info("Ouverture du menu d'export...")
            # On attend que le bouton avec "Plus" soit visible
            page.wait_for_selector("button:has-text('Plus')", timeout=10000)
            page.click("button:has-text('Plus')")
            page.click("text=Exporter")
            
            # 5. Configuration de la fenêtre d'export
            st.info("Configuration de l'export Excel...")
            # Sélectionner "Factures" dans le premier menu déroulant de la modale
            page.wait_for_selector("select", timeout=5000)
            page.select_option("select", label="Factures")
            
            # Plage de dates : Du 01.01.2025 à aujourd'hui (ou futur)
            # On cherche les champs de date. Playwright est bon pour cliquer sur les placeholders
            page.fill("input[placeholder='Du']", "01.01.2025")
            # Le champ "Au" peut rester tel quel s'il est déjà dans le futur
            
            # 6. Lancement du téléchargement
            with page.expect_download() as download_info:
                page.click("button:has-text('Créer le fichier Excel')")
            
            download = download_info.value
            path = "export_ephysio.xlsx"
            download.save_as(path)
            
            browser.close()
            return path

        except Exception as e:
            # En cas d'erreur, on prend une photo de l'écran pour comprendre où ça bloque
            page.screenshot(path="debug_error.png")
            browser.close()
            st.error(f"Erreur d'automatisation : {e}")
            if os.path.exists("debug_error.png"):
                st.image("debug_error.png", caption="Capture d'écran au moment de l'erreur")
            return None

# --- INTERFACE ---
st.title("🏥 Analyseur Facturation Ephysio")

with st.sidebar:
    st.header("🔑 Identifiants")
    # Utilisation des secrets Streamlit Cloud s'ils existent
    user = st.text_input("User", value=st.secrets.get("USER", ""))
    pwd = st.text_input("Password", type="password", value=st.secrets.get("PWD", ""))
    
    btn_sync = st.button("🚀 Synchroniser avec Ephysio", type="primary")

if btn_sync:
    if not user or not pwd:
        st.error("Veuillez remplir les identifiants dans la barre latérale.")
    else:
        file_path = fetch_from_ephysio(user, pwd)
        if file_path:
            st.session_state['df'] = pd.read_excel(file_path)
            st.success("Données synchronisées avec succès !")

# --- AFFICHAGE DES DONNÉES ---
if 'df' in st.session_state:
    df = st.session_state['df']
    st.divider()
    st.subheader("📊 Aperçu des données")
    st.dataframe(df.head(20)) # Affiche les 20 premières lignes
    
    # Bouton pour télécharger manuellement l'excel extrait si besoin
    with open("export_ephysio.xlsx", "rb") as f:
        st.download_button("📥 Télécharger le fichier Excel brut", f, file_name="ephysio_export.xlsx")
else:
    st.info("Cliquez sur le bouton de synchronisation pour récupérer les données d'Ephysio.")

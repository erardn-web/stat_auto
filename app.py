import streamlit as st
import pandas as pd
from datetime import datetime
import os
import subprocess
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="Analyseur Ephysio Pro", layout="wide")

def install_playwright_if_needed():
    if "PLAYWRIGHT_INSTALLED" not in st.session_state:
        subprocess.run(["python", "-m", "playwright", "install", "chromium"], check=True)
        st.session_state["PLAYWRIGHT_INSTALLED"] = True

def fetch_from_ephysio(u, p):
    install_playwright_if_needed()
    with sync_playwright() as p_wr:
        browser = p_wr.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            # 1. Connexion avec les ID réels du site
            st.info("🌍 Connexion à Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch/fr/physio/login", wait_until="networkidle")
            
            # Utilisation des ID exacts : username et password
            page.wait_for_selector("#username", timeout=20000)
            page.fill("#username", u)
            page.fill("#password", p)
            page.click("button[type='submit']")
            
            # 2. Sélection du profil
            st.info("👤 Choix du profil...")
            # On attend que la liste des profils soit là
            page.wait_for_selector(".profile-item, .list-group-item", timeout=30000)
            page.click(".profile-item >> nth=0") 
            
            # 3. Navigation Factures
            st.info("📄 Chargement des factures...")
            page.wait_for_url("**/app#**", timeout=30000)
            page.goto("https://ephysio.pharmedsolutions.ch")
            page.wait_for_load_state("networkidle")
            
            # 4. Menu "Plus..."
            st.info("📂 Menu Plus...")
            # On attend que le bouton soit cliquable
            btn_plus = page.locator("button:has-text('Plus')")
            btn_plus.wait_for(state="visible")
            btn_plus.click()
            page.wait_for_timeout(1000) # Pause pour l'animation du menu
            
            # 5. Export
            st.info("📤 Ouverture de l'export...")
            page.click("text=Exporter")
            
            # 6. Configuration de la fenêtre (Modale)
            st.info("📅 Configuration des dates...")
            page.wait_for_selector(".modal-content", timeout=15000)
            
            # Sélectionner 'Factures' dans le menu déroulant
            page.select_option("select", label="Factures")
            
            # Remplir la date de début
            # On utilise fill sur le champ qui a le placeholder "Du"
            page.fill("input[placeholder='Du']", "01.01.2025")
            page.wait_for_timeout(500)
            
            # 7. Créer et Télécharger
            st.info("⏳ Création de l'Excel...")
            with page.expect_download(timeout=60000) as download_info:
                # On clique sur le bouton vert 'Créer le fichier Excel'
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
                st.image("debug_error.png", caption="Dernière capture d'écran du robot")
            return None

# --- INTERFACE ---
st.title("🏥 Analyseur Facturation Ephysio")

with st.sidebar:
    st.header("🔑 Connexion")
    # On récupère les secrets si configurés sur Streamlit Cloud
    u_val = st.text_input("Identifiant", value=st.secrets.get("USER", ""))
    p_val = st.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))
    
    if st.button("🚀 Synchroniser", type="primary"):
        if u_val and p_val:
            res = fetch_from_ephysio(u_val, p_val)
            if res:
                st.session_state['df_brut'] = pd.read_excel(res)
                st.success("Données synchronisées !")
        else:
            st.error("Veuillez remplir les identifiants.")

if 'df_brut' in st.session_state:
    st.divider()
    st.dataframe(st.session_state['df_brut'], use_container_width=True)
    
    # Option de téléchargement local
    with open("data_ephysio.xlsx", "rb") as f:
        st.download_button("📥 Télécharger l'Excel", f, file_name="export_ephysio.xlsx")

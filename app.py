import streamlit as st
import pandas as pd
from datetime import datetime
import os
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="Analyseur Ephysio - Nathan Erard", layout="wide")

def fetch_from_ephysio(u, p):
    with sync_playwright() as p_wr:
        try:
            # Utilisation de Chromium avec des drapeaux d'indiscrétion
            browser = p_wr.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True, 
                args=[
                    "--no-sandbox", 
                    "--disable-blink-features=AutomationControlled", # Cache le fait que c'est un robot
                    "--disable-dev-shm-usage"
                ]
            )
            # On définit un profil plus complet
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800},
                locale="fr-CH"
            )
            page = context.new_page()
            
            # Étape 1 : Aller sur l'accueil d'abord pour simuler un parcours normal
            st.info("🌍 Accès au site Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="domcontentloaded")
            
            # Étape 2 : Cliquer sur le bouton "Connexion" de la page d'accueil
            st.info("🔗 Recherche du lien de connexion...")
            try:
                # On cherche le lien qui mène au login dans la barre de menu
                page.click("a:has-text('Connexion'), text=Login")
            except:
                # Si le clic échoue, on force l'URL de login
                page.goto("https://ephysio.pharmedsolutions.ch/login")

            # Étape 3 : Saisie des identifiants avec attente patiente
            st.info("🔑 Saisie des identifiants...")
            # On utilise un sélecteur très large pour trouver n'importe quel champ de texte
            page.wait_for_selector("input", timeout=20000)
            
            # On cherche les champs par leur type pour éviter les changements d'ID
            page.locator("input[type='text'], input[name*='user'], #username").first.fill(u)
            page.locator("input[type='password'], #password").first.fill(p)
            
            # Clic sur Connexion
            page.locator("button[type='submit'], .btn-primary, button:has-text('Connexion')").first.click()
            
            # Étape 4 : Profil Nathan Erard
            st.info("👤 Sélection du profil...")
            page.wait_for_selector("text=Nathan Erard", timeout=30000)
            page.click("text=Nathan Erard")
            
            # Étape 5 : Navigation Factures et Export
            st.info("📄 Navigation et Export...")
            page.wait_for_url("**/app#**", timeout=20000)
            page.goto("https://ephysio.pharmedsolutions.ch")
            
            page.wait_for_selector("button:has-text('Plus')")
            page.click("button:has-text('Plus')")
            page.click("text=Exporter")
            
            # Configuration Modale
            page.wait_for_selector(".modal-content")
            page.locator("select").select_option(label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # Étape 6 : Téléchargement
            st.info("⏳ Téléchargement de l'Excel...")
            with page.expect_download(timeout=60000) as download_info:
                page.locator("button:has-text('Créer')").first.click()
            
            download = download_info.value
            path = "data_nathan.xlsx"
            download.save_as(path)
            
            browser.close()
            return path

        except Exception as e:
            if 'page' in locals():
                page.screenshot(path="debug_nathan.png")
            browser.close()
            st.error(f"Détail du blocage : {e}")
            if os.path.exists("debug_nathan.png"):
                st.image("debug_nathan.png", caption="Vision du robot lors du crash")
            return None

# Interface
st.title("🏥 Analyseur Facturation")
u = st.sidebar.text_input("Identifiant", value=st.secrets.get("USER", ""))
p = st.sidebar.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))

if st.sidebar.button("🚀 Synchroniser"):
    res = fetch_from_ephysio(u, p)
    if res:
        st.session_state['df'] = pd.read_excel(res)
        st.success("Synchronisation réussie !")

if 'df' in st.session_state:
    st.dataframe(st.session_state['df'], use_container_width=True)

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
            # Lancement avec les options de compatibilité Streamlit
            browser = p_wr.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True, 
                args=[
                    "--no-sandbox", 
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage"
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800},
                locale="fr-CH",
                timezone_id="Europe/Zurich" # <--- Fix du bug de fuseau horaire
            )
            page = context.new_page()
            
            # 1. Accueil (Indispensable pour débloquer le formulaire)
            st.info("🌍 Accès au site Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="domcontentloaded")
            
            # 2. Accès au formulaire de connexion
            st.info("🔗 Accès au formulaire...")
            try:
                # Clic sur le bouton de connexion de la page d'accueil
                page.click("a:has-text('Connexion'), text=Login", timeout=8000)
            except:
                # Secours si le bouton n'est pas trouvé
                page.goto("https://ephysio.pharmedsolutions.ch/login")

            # 3. Saisie des identifiants
            st.info("🔑 Saisie des identifiants...")
            page.wait_for_selector("input", timeout=20000)
            page.locator("input[type='text'], input[name*='user'], #username").first.fill(u)
            page.locator("input[type='password'], #password").first.fill(p)
            page.keyboard.press("Enter")
            
            # 4. Sélection du profil (AVEC PATIENCE ACCRUE)
            st.info("⏳ Validation en cours, attente de la liste des profils...")
            page.wait_for_load_state("networkidle")
            
            # ON LAISSE 10 SECONDES ICI COMME DEMANDÉ
            time.sleep(10) 
            
            st.info("👤 Sélection du profil : Nathan Erard...")
            try:
                # On attend que le nom apparaisse avant de cliquer
                page.wait_for_selector("text=/Nathan Erard/i", timeout=15000)
                page.click("text=/Nathan Erard/i")
                st.toast("Profil Nathan Erard sélectionné !")
            except:
                st.warning("Nom exact non détecté, clic sur le premier profil de la liste...")
                page.click(".profile-item, .list-group-item, .btn-profile, .card")

            # 5. Navigation Factures
            st.info("📄 Accès à l'espace Facturation...")
            page.wait_for_url("**/app#**", timeout=30000)
            # On force l'URL vers les factures pour éviter le retour accueil
            page.goto("https://ephysio.pharmedsolutions.ch") 
            page.wait_for_load_state("networkidle")
            
            # 6. Menu Plus... et Export
            st.info("📂 Menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            page.wait_for_timeout(2000) # Attendre l'animation du menu
            page.click("text=Exporter")
            
            # 7. Configuration Modale d'Export
            st.info("📅 Configuration de l'export...")
            page.wait_for_selector(".modal-content", timeout=15000)
            page.locator("select").select_option(label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            page.wait_for_timeout(500)
            
            # 8. Téléchargement
            st.info("⏳ Téléchargement de l'Excel...")
            with page.expect_download(timeout=60000) as download_info:
                page.locator("button:has-text('Créer'), .btn-primary").first.click()
            
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
                st.image("debug_nathan.png", caption="Vision du robot lors de l'erreur")
            return None

# --- INTERFACE ---
st.title("🏥 Analyseur Facturation Ephysio")

with st.sidebar:
    u_side = st.text_input("Identifiant", value=st.secrets.get("USER", ""))
    p_side = st.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))
    btn = st.button("🚀 Synchroniser les données", type="primary")

if btn:
    res = fetch_from_ephysio(u_side, p_side)
    if res:
        st.session_state['df_nathan'] = pd.read_excel(res)
        st.success("Synchronisation réussie !")

if 'df_nathan' in st.session_state:
    st.dataframe(st.session_state['df_nathan'], use_container_width=True)

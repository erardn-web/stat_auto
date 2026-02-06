import streamlit as st
import pandas as pd
from datetime import datetime
import os
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="Analyseur Ephysio", layout="wide")

def fetch_from_ephysio(u, p):
    with sync_playwright() as p_wr:
        try:
            browser = p_wr.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True, 
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # 1. CONNEXION
            st.info("🌍 Chargement de la page de login...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            
            page.fill("#username", u)
            page.fill("#password", p)
            st.info("🚀 Connexion en cours...")
            page.keyboard.press("Enter")
            
            # 2. SÉLECTION DU PROFIL (Version renforcée)
            st.info("👤 Attente de la liste des profils...")
            # On attend que l'URL change ou qu'un élément de profil apparaisse
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000) # Pause de 3s pour laisser l'interface s'afficher
            
            # On cherche Nathan Erard de façon très large (insensible à la casse)
            profil = page.locator("text=/Nathan Erard/i")
            
            if profil.count() > 0:
                st.info("✅ Profil trouvé, clic sur 'Nathan Erard'...")
                profil.first.click()
            else:
                st.warning("⚠️ Texte exact non trouvé, tentative sur le premier profil de la liste...")
                # Alternative : cliquer sur le premier élément qui ressemble à un choix de profil
                page.locator(".profile-item, .list-group-item, a[href*='select']").first.click()

            # 3. NAVIGATION ET EXPORT
            st.info("📄 Accès à l'espace Facturation...")
            # On attend que l'URL contienne '/app' qui confirme qu'on est entré
            page.wait_for_url("**/app#**", timeout=30000)
            page.goto("https://ephysio.pharmedsolutions.ch")
            page.wait_for_load_state("networkidle")
            
            st.info("📂 Menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            page.wait_for_timeout(1000)
            page.click("text=Exporter")
            
            # 4. CONFIGURATION MODALE
            st.info("📅 Configuration de l'export (01.01.2025)...")
            page.wait_for_selector(".modal-content", timeout=15000)
            
            # Sélectionner 'Factures' et remplir la date
            page.locator("select").select_option(label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 5. TÉLÉCHARGEMENT
            st.info("⏳ Génération du fichier Excel...")
            with page.expect_download(timeout=60000) as download_info:
                page.locator("button:has-text('Créer le fichier Excel')").click()
            
            download = download_info.value
            path = "data_nathan.xlsx"
            download.save_as(path)
            
            browser.close()
            return path

        except Exception as e:
            if 'page' in locals():
                page.screenshot(path="debug_nathan.png")
            browser.close()
            st.error(f"Erreur de parcours : {e}")
            if os.path.exists("debug_nathan.png"):
                st.image("debug_nathan.png", caption="Dernière image avant l'erreur")
            return None

# --- INTERFACE ---
st.title("🏥 Analyseur Facturation Ephysio")

with st.sidebar:
    u_val = st.text_input("Identifiant", value=st.secrets.get("USER", ""))
    p_val = st.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))
    btn = st.button("🚀 Lancer l'analyse", type="primary")

if btn:
    res = fetch_from_ephysio(u_val, p_val)
    if res:
        st.session_state['df'] = pd.read_excel(res)
        st.success("Synchronisation terminée !")

if 'df' in st.session_state:
    st.write("### Tableau des factures (Nathan Erard)")
    st.dataframe(st.session_state['df'], use_container_width=True)

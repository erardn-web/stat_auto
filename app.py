import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
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
                viewport={'width': 1280, 'height': 800},
                timezone_id="Europe/Zurich",
                locale="fr-CH"
            )
            page = context.new_page()
            
            # 1. LOGIN DIRECT
            st.info("🔑 Connexion directe...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="domcontentloaded")
            
            # Saisie rapide
            page.wait_for_selector("#username", timeout=15000)
            page.fill("#username", u)
            page.fill("#password", p)
            page.keyboard.press("Enter")
            
            # 2. ATTENTE ET CLIC PROFIL
            st.info("👤 Choix du profil...")
            # On attend que la page de profil se charge (on cherche n'importe quel bouton ou lien)
            page.wait_for_load_state("networkidle")
            time.sleep(4) # Pause de sécurité
            
            # On clique sur le premier élément cliquable de la page (le profil)
            # On essaie d'abord un sélecteur de liste, sinon n'importe quel bouton
            try:
                page.locator(".profile-item, .list-group-item, a[href*='select'], button").first.click()
            except:
                page.mouse.click(640, 400) # Clic au centre de l'écran si tout échoue
            
            # 3. NAVIGATION FACTURES
            st.info("📄 Accès aux factures...")
            page.wait_for_url("**/app#**", timeout=20000)
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="networkidle")
            
            # 4. EXPORT
            st.info("📂 Menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=15000)
            page.click("button:has-text('Plus')")
            time.sleep(1)
            page.click("text=Exporter")
            
            # 5. MODALE & DATES
            st.info("📅 Configuration export...")
            page.wait_for_selector(".modal-content")
            page.locator("select").select_option(label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 6. TÉLÉCHARGEMENT
            st.info("⏳ Téléchargement...")
            with page.expect_download(timeout=60000) as download_info:
                page.locator("button:has-text('Créer'), .btn-primary").first.click()
            
            download = download_info.value
            path = "data_nathan.xlsx"
            download.save_as(path)
            
            browser.close()
            return path

        except Exception as e:
            if 'page' in locals():
                page.screenshot(path="debug_error.png")
            browser.close()
            st.error(f"Bloqué : {e}")
            if os.path.exists("debug_error.png"):
                st.image("debug_error.png", caption="Image du blocage")
            return None

# --- INTERFACE ---
st.title("🏥 Analyseur Facturation Ephysio")

u_sidebar = st.sidebar.text_input("Identifiant", value=st.secrets.get("USER", ""))
p_sidebar = st.sidebar.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))

if st.sidebar.button("🚀 Synchroniser"):
    res = fetch_from_ephysio(u_sidebar, p_sidebar)
    if res:
        st.session_state['df'] = pd.read_excel(res)
        st.success("Synchronisation réussie !")

if 'df' in st.session_state:
    st.dataframe(st.session_state['df'], use_container_width=True)

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
                timezone_id="Europe/Zurich"
            )
            page = context.new_page()
            
            # 1. Accueil & Connexion
            st.info("🌍 Accès au site Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch", wait_until="domcontentloaded")
            
            st.info("🔑 Saisie des identifiants...")
            page.wait_for_selector("input", timeout=20000)
            page.locator("input[type='text'], #username").first.fill(u)
            page.locator("input[type='password'], #password").first.fill(p)
            
            # Validation et attente de la transition
            page.keyboard.press("Enter")
            
            # --- MODIFICATION ICI : PATIENCE ACCRUE ---
            st.info("⏳ Validation en cours, attente de la liste des profils...")
            # On attend que le réseau soit calme
            page.wait_for_load_state("networkidle")
            # Pause de sécurité supplémentaire de 10 secondes
            time.sleep(10) 
            
            st.info("👤 Sélection du profil...")
            # On attend que le profil soit visible (timeout long de 30s au cas où)
            page.wait_for_selector("text=/Nathan Erard/i", timeout=30000)
            
            try:
                page.click("text=/Nathan Erard/i", timeout=10000)
                st.toast("Profil Nathan Erard sélectionné !")
            except:
                st.warning("Nom non détecté par clic direct, tentative sur le premier élément de liste...")
                page.click(".profile-item, .list-group-item, a[href*='select']")

            # 4. Navigation Factures
            st.info("📄 Accès à l'espace Facturation...")
            page.wait_for_url("**/app#**", timeout=30000)
            # Forçage de l'URL vers les factures
            page.goto("https://ephysio.pharmedsolutions.ch") 
            page.wait_for_load_state("networkidle")
            
            # 5. Menu Plus... et Export
            st.info("📂 Menu export...")
            page.wait_for_selector("button:has-text('Plus')", timeout=20000)
            page.click("button:has-text('Plus')")
            time.sleep(2) 
            page.click("text=Exporter")
            
            # 6. Configuration Modale d'Export
            st.info("📅 Configuration de l'export...")
            page.wait_for_selector(".modal-content", timeout=15000)
            page.locator("select").select_option(label="Factures")
            page.fill("input[placeholder='Du']", "01.01.2025")
            
            # 7. Téléchargement
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
    st.header("🔑 Connexion")
    u_side = st.text_input("Identifiant", value=st.secrets.get("USER", ""))
    p_side = st.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))
    btn = st.button("🚀 Synchroniser les données", type="primary")

if btn:
    if u_side and p_side:
        res = fetch_from_ephysio(u_side, p_side)
        if res:
            st.session_state['df_nathan'] = pd.read_excel(res)
            st.success("Synchronisation réussie !")

if 'df_nathan' in st.session_state:
    st.dataframe(st.session_state['df_nathan'], use_container_width=True)

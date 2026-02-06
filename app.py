import streamlit as st
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
import os

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Analyseur Ephysio Pro", layout="wide")

def fetch_from_ephysio(u, p):
    with sync_playwright() as p_wr:
        # Configuration pour le cloud
        browser = p_wr.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            # 1. Connexion
            st.toast("Connexion à Ephysio...")
            page.goto("https://ephysio.pharmedsolutions.ch")
            page.fill("input[name='_username']", u)
            page.fill("input[name='_password']", p)
            page.click("button[type='submit']")
            
            # 2. Sélection du profil
            st.toast("Sélection du profil...")
            page.wait_for_selector(".profile-item, .list-group-item", timeout=15000)
            page.click(".profile-item >> nth=0") # Clique sur le 1er profil
            
            # 3. Page Factures
            page.wait_for_url("**/app#**")
            page.goto("https://ephysio.pharmedsolutions.ch")
            page.wait_for_load_state("networkidle")
            
            # 4. Menu Plus... > Exporter
            st.toast("Accès au menu export...")
            page.click("button:has-text('Plus')")
            page.click("text=Exporter")
            
            # 5. Fenêtre d'export (Modale)
            st.toast("Configuration des dates...")
            # Sélection "Factures" dans le menu déroulant
            page.select_option("div.modal-content select", label="Factures")
            
            # Plage de dates : 01.01.2025
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
            page.screenshot(path="debug.png")
            browser.close()
            st.error(f"Erreur : {e}")
            if os.path.exists("debug.png"): st.image("debug.png")
            return None

# --- ANALYSE DES DONNÉES ---
st.title("🏥 Analyseur Facturation Ephysio")

with st.sidebar:
    st.header("🔑 Connexion")
    u = st.text_input("Identifiant", value=st.secrets.get("USER", ""))
    p = st.text_input("Mot de passe", type="password", value=st.secrets.get("PWD", ""))
    btn = st.button("🚀 Lancer la Synchronisation", type="primary")

if btn:
    res = fetch_from_ephysio(u, p)
    if res:
        st.session_state['df_brut'] = pd.read_excel(res)
        st.success("Données synchronisées !")

if 'df_brut' in st.session_state:
    df = st.session_state['df_brut'].copy()
    
    # Renommer les colonnes selon votre structure Ephysio (à ajuster si besoin)
    # On utilise les index pour éviter les erreurs de noms exacts
    df = df.rename(columns={
        df.columns[2]: "date_facture", df.columns[8]: "assureur",
        df.columns[12]: "statut", df.columns[13]: "montant", 
        df.columns[15]: "date_paiement"
    })
    
    # Nettoyage rapide
    df["montant"] = pd.to_numeric(df["montant"], errors="coerce").fillna(0)
    
    # --- GRAPHIQUES RAPIDES ---
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Facturé (depuis 01.2025)", f"{int(df['montant'].sum())} CHF")
    with col2:
        st.metric("Nombre de factures", len(df))

    st.write("### 📋 Détail des factures")
    st.dataframe(df, use_container_width=True)
    
    # Bouton de secours
    with open("data_ephysio.xlsx", "rb") as f:
        st.download_button("📥 Télécharger l'Excel extrait", f, file_name="export_ephysio.xlsx")

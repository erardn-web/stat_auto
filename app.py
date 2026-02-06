import streamlit as st
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
import time

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Ephysio Analytics Connect", layout="wide")

# --- FONCTION D'AUTOMATISATION ---
def fetch_from_ephysio(u, p):
    with sync_playwright() as p_wr:
        # Configuration pour le Cloud et le local
        browser = p_wr.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()
        
        try:
            # 1. Connexion
            page.goto("https://ephysio.pharmedsolutions.ch")
            page.fill("input[name='_username']", u)
            page.fill("input[name='_password']", p)
            page.click("button[type='submit']")
            
            # 2. Sélection du profil (Si plusieurs profils existent)
            # On attend que la page de profil s'affiche
            st.info("Sélection du profil...")
            page.wait_for_selector("text=Sélectionner le profil", timeout=10000)
            # Clique sur le premier profil disponible ou un texte spécifique
            page.click(".profile-item >> nth=0") # Ajuster le sélecteur si nécessaire
            
            # 3. Aller sur la page des factures
            page.goto("https://ephysio.pharmedsolutions.ch/app#/invoices")
            page.wait_for_load_state("networkidle")
            
            # 4. Menu déroulant "Plus..."
            # On cherche le bouton qui contient "Plus"
            page.click("button:has-text('Plus'), .btn-more") 
            
            # 5. Cliquer sur Exporter
            page.click("text=Exporter")
            
            # 6. Configuration de la fenêtre d'export (Modale)
            # Sélectionner "Factures" dans le menu déroulant de la fenêtre
            page.select_option("select.export-type", label="Factures") # Ajuster le sélecteur du select
            
            # Remplir la date de début (01.01.2025)
            # On cible le champ date par son label ou son placeholder
            page.fill("input[name='start_date'], .datepicker-start", "01.01.2025")
            
            # 7. Téléchargement
            with page.expect_download() as download_info:
                page.click("button:has-text('Créer le fichier Excel'), .btn-primary")
            
            download = download_info.value
            temp_path = "data_ephysio.xlsx"
            download.save_as(temp_path)
            
            browser.close()
            return temp_path

        except Exception as e:
            st.error(f"Erreur durant l'automatisation : {e}")
            # Capture d'écran pour le debug si ça rate (utile au début)
            page.screenshot(path="error_debug.png")
            browser.close()
            return None

# --- FONCTIONS DE CALCUL ---
def convertir_date(val):
    if pd.isna(val) or str(val).strip() == "": return pd.NaT
    try: return pd.to_datetime(str(val).strip(), format="%d.%m.%Y", errors="coerce")
    except: return pd.NaT

# --- INTERFACE STREAMLIT ---
st.title("🏥 Analyseur Facturation Ephysio")

with st.sidebar:
    st.header("🔑 Connexion")
    # On vérifie si les secrets existent sur Streamlit Cloud
    default_user = st.secrets.get("USER", "")
    default_pwd = st.secrets.get("PWD", "")
    
    u = st.text_input("Identifiant", value=default_user)
    p = st.text_input("Mot de passe", type="password", value=default_pwd)
    
    if st.button("🔄 Synchroniser Ephysio", type="primary"):
        path = fetch_from_ephysio(u, p)
        if path:
            st.session_state['df_brut'] = pd.read_excel(path)
            st.success("Données importées !")

# --- ANALYSE DES DONNÉES ---
if 'df_brut' in st.session_state:
    df_brut = st.session_state['df_brut']
    
    # Nettoyage selon votre script initial (Index des colonnes à vérifier)
    # On suppose ici les colonnes : 2=Date, 8=Assureur, 12=Statut, 13=Montant, 15=Paiement
    try:
        df = df_brut.copy()
        df = df.rename(columns={
            df.columns[2]: "date_facture", df.columns[8]: "assureur",
            df.columns[12]: "statut", df.columns[13]: "montant", 
            df.columns[15]: "date_paiement"
        })
        
        # Conversion et Logique
        df["date_facture"] = df["date_facture"].apply(convertir_date)
        df["date_paiement"] = df["date_paiement"].apply(convertir_date)
        df["montant"] = pd.to_numeric(df["montant"], errors="coerce").fillna(0)
        
        # --- AFFICHAGE ---
        st.write(f"### Analyse des données (Mise à jour : {datetime.now().strftime('%H:%M')})")
        
        m1, m2 = st.columns(2)
        m1.metric("Total Facturé", f"{int(df['montant'].sum())} CHF")
        m2.metric("Nb Factures", len(df))
        
        st.dataframe(df) # Affiche le tableau complet
        
        # Ajoutez ici vos onglets (Liquidités, Délais, etc.) comme dans votre premier script

    except Exception as e:
        st.error(f"Erreur d'analyse : {e}")
else:
    st.info("Veuillez lancer la synchronisation depuis la barre latérale.")

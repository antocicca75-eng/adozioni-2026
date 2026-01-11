import streamlit as st
import pandas as pd
import os
from datetime import datetime
from openpyxl import load_workbook
import io
import gspread
from google.oauth2.service_account import Credentials
import json

# --- CONFIGURAZIONE FILE ---
DB_FILE = "dati_adozioni.csv"
CONFIG_FILE = "anagrafiche.xlsx"
ID_FOGLIO = "1Ah5_pucc4b0ziNZxqo0NRpHwyUvFrUEggIugMXzlaKk"

st.set_page_config(page_title="Adozioni 2026", layout="wide", page_icon="📚")

# --- CONNESSIONE GOOGLE SHEETS ---
def connetti_google_sheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        json_info = json.loads(st.secrets["gspread"]["json_data"], strict=False)
        if "private_key" in json_info:
            json_info["private_key"] = json_info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(json_info, scopes=scope)
        client_gs = gspread.authorize(creds)
        return client_gs.open_by_key(ID_FOGLIO)
    except Exception as e:
        st.error(f"⚠️ Errore connessione Cloud: {e}")
        return None

def backup_su_google_sheets(df_da_salvare):
    sh = connetti_google_sheets()
    if sh:
        try:
            foglio = sh.worksheet("Adozioni_DB")
            foglio.clear()
            dati = [df_da_salvare.columns.values.tolist()] + df_da_salvare.fillna("").values.tolist()
            foglio.update(dati)
            return True
        except Exception as e:
            st.sidebar.error(f"Errore scrittura Cloud: {e}")
    return False

# --- LETTURA CATALOGO E PLESSI ---
@st.cache_data(ttl=600)
def get_anagrafiche_cloud():
    sh = connetti_google_sheets()
    if sh:
        try:
            # Legge Catalogo
            df_cat = pd.DataFrame(sh.worksheet("Catalogo").get_all_records())
            # Legge Plessi
            df_ple = pd.DataFrame(sh.worksheet("Plesso").get_all_records())
            return df_cat, sorted(df_ple.iloc[:, 0].dropna().tolist())
        except: pass
    return pd.DataFrame(), []

# --- CARICAMENTO INIZIALE ---
catalogo, elenco_plessi = get_anagrafiche_cloud()
elenco_titoli = sorted(catalogo["TITOLO"].unique().tolist()) if not catalogo.empty else []

# --- STILE CSS ---
st.markdown("""
    <style>
    [data-testid="stDataEditor"] thead tr th { background-color: #004a99 !important; color: white !important; }
    .totale-box { padding: 20px; background-color: #e8f0fe; border-radius: 10px; border: 1px solid #004a99; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- NAVIGAZIONE ---
if "pagina" not in st.session_state: st.session_state.pagina = "Inserimento"

with st.sidebar:
    st.title("🧭 MENU")
    if st.button("➕ NUOVA ADOZIONE", use_container_width=True): st.session_state.pagina = "Inserimento"; st.rerun()
    if st.button("✏️ MODIFICA ADOZIONE", use_container_width=True): st.session_state.pagina = "Modifica"; st.rerun()
    if st.button("📊 REGISTRO COMPLETO", use_container_width=True): st.session_state.pagina = "Registro"; st.rerun()
    if st.button("🔍 FILTRA E RICERCA", use_container_width=True): st.session_state.pagina = "Ricerca"; st.rerun()

st.title("📚 Gestione Adozioni 2026")

# --- SCHERMATA INSERIMENTO ---
if st.session_state.pagina == "Inserimento":
    st.subheader("Nuova Registrazione Adozione")
    if "form_id" not in st.session_state: st.session_state.form_id = 0

    with st.container(border=True):
        titolo_scelto = st.selectbox("📕 SELEZIONA TITOLO", [""] + elenco_titoli, key=f"t_{st.session_state.form_id}")
        
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            plesso = st.selectbox("🏫 Plesso", [""] + elenco_plessi, key=f"p_{st.session_state.form_id}")
            note = st.text_area("📝 Note", key=f"n_{st.session_state.form_id}", height=70)
        with c2:
            n_sez = st.number_input("🔢 N° sezioni", min_value=1, value=1, key=f"s_{st.session_state.form_id}")
            saggio = st.selectbox("📚 Saggio consegnato", ["NO", "SI"], key=f"sag_{st.session_state.form_id}")
        with c3:
            sez_lett = st.text_input("🔡 Lettera Sezione", key=f"l_{st.session_state.form_id}").upper()

        if st.button("💾 SALVA ADOZIONE", use_container_width=True, type="primary"):
            if titolo_scelto and plesso:
                info = catalogo[catalogo["TITOLO"] == titolo_scelto]
                nuova_riga = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Plesso": plesso, "Materia": info.iloc[0,1], "Titolo": titolo_scelto,
                    "Editore": info.iloc[0,2], "Agenzia": info.iloc[0,3], "N° sezioni": n_sez,
                    "Sezione": sez_lett, "Saggio Consegna": saggio, "Note": note
                }])
                df_attuale = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
                df_finale = pd.concat([df_attuale, nuova_riga], ignore_index=True)
                df_finale.to_csv(DB_FILE, index=False)
                backup_su_google_sheets(df_finale)
                st.session_state.form_id += 1
                st.success("✅ Salvato con successo!")
                st.rerun()

# --- SCHERMATA MODIFICA ---
elif st.session_state.pagina == "Modifica":
    st.subheader("✏️ Modifica o Cancella")
    if os.path.exists(DB_FILE):
        df_mod = pd.read_csv(DB_FILE).fillna("").astype(str)
        t_filtro = st.selectbox("🔍 Cerca Titolo da modificare", [""] + sorted(df_mod["Titolo"].unique().tolist()))
        
        if t_filtro:
            for i in df_mod[df_mod["Titolo"] == t_filtro].index:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        n_titolo = st.selectbox(f"Titolo", elenco_titoli, index=elenco_titoli.index(df_mod.at[i, 'Titolo']), key=f"et_{i}")
                        n_note = st.text_area("Note", value=df_mod.at[i, 'Note'], key=f"en_{i}", height=70)
                    with col2:
                        n_sezioni = st.number_input("N° sezioni", min_value=1, value=int(float(df_mod.at[i, 'N° sezioni'])), key=f"es_{i}")
                        n_saggio = st.selectbox("Saggio", ["NO", "SI"], index=0 if df_mod.at[i, 'Saggio Consegna'] == "NO" else 1, key=f"esag_{i}")
                    with col3:
                        n_lett = st.text_input("Sezione", value=df_mod.at[i, 'Sezione'], key=f"el_{i}").upper()
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("💾 AGGIORNA", key=f"up_{i}", use_container_width=True, type="primary"):
                            df_mod.at[i, 'Titolo'] = n_titolo
                            df_mod.at[i, 'N° sezioni'] = n_sezioni
                            df_mod.at[i, 'Sezione'] = n_lett
                            df_mod.at[i, 'Saggio Consegna'] = n_saggio
                            df_mod.at[i, 'Note'] = n_note
                            df_mod.to_csv(DB_FILE, index=False)
                            backup_su_google_sheets(df_mod)
                            st.rerun()
                    with b2:
                        if st.button("🗑️ ELIMINA", key=f"del_{i}", use_container_width=True):
                            df_mod = df_mod.drop(i)
                            df_mod.to_csv(DB_FILE, index=False)
                            backup_su_google_sheets(df_mod)
                            st.rerun()

# --- SCHERMATA REGISTRO ---
elif st.session_state.pagina == "Registro":
    st.subheader("📑 Registro Completo")
    if os.path.exists(DB_FILE):
        st.dataframe(pd.read_csv(DB_FILE).sort_index(ascending=False), use_container_width=True)

# --- SCHERMATA RICERCA ---
elif st.session_state.pagina == "Ricerca":
    st.subheader("🔍 Ricerca Avanzata")
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE).fillna("").astype(str)
        f_tit = st.multiselect("Filtra Titolo", sorted(df["Titolo"].unique().tolist()))
        f_sag = st.selectbox("Filtra Saggio Consegnato", ["TUTTI", "SI", "NO"])
        
        df_f = df.copy()
        if f_tit: df_f = df_f[df_f["Titolo"].isin(f_tit)]
        if f_sag != "TUTTI": df_f = df_f[df_f["Saggio Consegna"] == f_sag]
        
        st.dataframe(df_f, use_container_width=True)
        st.metric("Totale Classi", int(pd.to_numeric(df_f["N° sezioni"]).sum()))

st.markdown("<p style='text-align: center; color: gray;'>Created by Antonio Ciccarelli v13.0</p>", unsafe_allow_html=True)

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

# --- FUNZIONE CONNESSIONE GOOGLE SHEETS ---
def connetti_google_sheets():
    try:
        # 1. Definiamo i permessi necessari
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # 2. Carichiamo i dati dal blocco [gspread] dei Secrets
        # Usiamo strict=False per gestire meglio eventuali caratteri speciali nel JSON
        json_info = json.loads(st.secrets["gspread"]["json_data"], strict=False)
        
        # 3. Puliamo la chiave privata (fondamentale per evitare errori di escape)
        if "private_key" in json_info:
            json_info["private_key"] = json_info["private_key"].replace("\\n", "\n")
            
        # 4. Autorizzazione con le credenziali del Service Account
        creds = Credentials.from_service_account_info(json_info, scopes=scope)
        client_gs = gspread.authorize(creds)
        
        # 5. Apertura del foglio tramite l'ID fornito
        sh = client_gs.open_by_key(ID_FOGLIO)
        
        # 6. Restituiamo il foglio specifico per il database (Adozioni_DB)
        # Se preferisci il primo foglio in assoluto, usa: return sh.get_worksheet(0)
        return sh.worksheet("Adozioni_DB")
        
    except Exception as e:
        st.error(f"⚠️ Errore connessione Cloud: {e}")
        return None

def backup_su_google_sheets(df_da_salvare):
    foglio = connetti_google_sheets()
    if foglio:
        try:
            # Pulisce il foglio e scrive i nuovi dati (inclusa intestazione)
            foglio.clear()
            # Prepariamo i dati convertendo tutto in stringa per evitare errori JSON
            dati = [df_da_salvare.columns.values.tolist()] + df_da_salvare.fillna("").values.tolist()
            foglio.update(dati)
            return True
        except Exception as e:
            st.sidebar.error(f"Errore scrittura Cloud: {e}")
            return False
    return False

# --- STILE CSS ---
st.markdown("""
    <style>
    [data-testid="stDataEditor"] thead tr th { background-color: #004a99 !important; color: white !important; }
    .stApp { background-color: #ffffff; }
    .totale-box { padding: 20px; background-color: #e8f0fe; border-radius: 10px; border: 1px solid #004a99; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CARICAMENTO E SCRITTURA LOCALE ---
@st.cache_data
def get_catalogo_libri():
    if os.path.exists(CONFIG_FILE):
        try:
            df = pd.read_excel(CONFIG_FILE, sheet_name="ListaLibri")
            df.columns = [c.strip() for c in df.columns]
            return df.fillna("")
        except: return pd.DataFrame()
    return pd.DataFrame()

def aggiungi_libro_a_excel(t, m, e, a):
    try:
        wb = load_workbook(CONFIG_FILE)
        ws = wb["ListaLibri"]
        ws.append([t, m, e, a])
        wb.save(CONFIG_FILE)
        return True
    except: return False

def get_lista_plessi():
    if os.path.exists(CONFIG_FILE):
        try:
            df = pd.read_excel(CONFIG_FILE, sheet_name="Plesso")
            return sorted(df.iloc[:, 0].dropna().unique().tolist())
        except: return []
    return []

# --- PREPARAZIONE DATI ---
catalogo = get_catalogo_libri()
if not catalogo.empty:
    elenco_titoli = sorted([str(x) for x in catalogo.iloc[:, 0].unique() if str(x).strip() != ""])
    elenco_materie = sorted([str(x) for x in catalogo.iloc[:, 1].unique() if str(x).strip() != ""])
    elenco_editori = sorted([str(x) for x in catalogo.iloc[:, 2].unique() if str(x).strip() != ""])
    elenco_agenzie = sorted([str(x) for x in catalogo.iloc[:, 3].unique() if str(x).strip() != ""])
else:
    elenco_titoli = elenco_materie = elenco_editori = elenco_agenzie = []

elenco_plessi = get_lista_plessi()

# --- GESTIONE NAVIGAZIONE ---
if "pagina" not in st.session_state:
    st.session_state.pagina = "Inserimento"

def reset_ricerca():
    st.session_state.r_attiva = False
    st.session_state.ft = []
    st.session_state.fa = []
    st.session_state.fp = []
    st.session_state.fm = []
    st.session_state.fe = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧭 MENU")
    if st.button("➕ NUOVA ADOZIONE", use_container_width=True, type="primary" if st.session_state.pagina == "Inserimento" else "secondary"):
        st.session_state.pagina = "Inserimento"
        st.rerun()
    if st.button("✏️ MODIFICA ADOZIONE", use_container_width=True, type="primary" if st.session_state.pagina == "Modifica" else "secondary"):
        st.session_state.pagina = "Modifica"
        st.rerun()
    if st.button("🆕 AGGIUNGI A CATALOGO", use_container_width=True, type="primary" if st.session_state.pagina == "NuovoLibro" else "secondary"):
        st.session_state.pagina = "NuovoLibro"
        st.rerun()
    if st.button("📊 REGISTRO COMPLETO", use_container_width=True, type="primary" if st.session_state.pagina == "Registro" else "secondary"):
        st.session_state.pagina = "Registro"
        st.rerun()
    if st.button("🔍 FILTRA E RICERCA", use_container_width=True, type="primary" if st.session_state.pagina == "Ricerca" else "secondary"):
        st.session_state.pagina = "Ricerca"
        st.rerun()

    st.markdown("---")
    st.subheader("📥 Backup Google Sheets")
    if st.button("☁️ SINCRONIZZA ORA", use_container_width=True):
        if os.path.exists(DB_FILE):
            df_sync = pd.read_csv(DB_FILE)
            if backup_su_google_sheets(df_sync):
                st.sidebar.success("Sincronizzato!")
            else: st.sidebar.error("Errore sincronizzazione.")

st.title("📚 Gestione Adozioni 2026")

# --- SCHERMATE ---
if st.session_state.pagina == "NuovoLibro":
    st.subheader("🆕 Aggiungi nuovo titolo al catalogo Excel")
    with st.container(border=True):
        nt = st.text_input("Inserisci Titolo Libro")
        col1, col2, col3 = st.columns(3)
        with col1:
            m_sel = st.selectbox("Materia", [""] + elenco_materie + ["-- NUOVA MATERIA --"])
            m_val = st.text_input("Specifica Materia") if m_sel == "-- NUOVA MATERIA --" else m_sel
        with col2:
            e_sel = st.selectbox("Editore", [""] + elenco_editori + ["-- NUOVO EDITORE --"])
            e_val = st.text_input("Specifica Editore") if e_sel == "-- NUOVO EDITORE --" else e_sel
        with col3:
            a_sel = st.selectbox("Agenzia", [""] + elenco_agenzie + ["-- NUOVA AGENZIA --"])
            a_val = st.text_input("Specifica Agenzia") if a_sel == "-- NUOVA AGENZIA --" else a_sel
        
        if st.button("✅ SALVA NEL CATALOGO EXCEL", use_container_width=True, type="primary"):
            if nt and m_val and e_val and a_val:
                if aggiungi_libro_a_excel(nt, m_val, e_val, a_val):
                    st.success(f"Libro '{nt}' aggiunto!")
                    st.cache_data.clear()
                    st.rerun()
                else: st.error("Errore: chiudi il file Excel!")

elif st.session_state.pagina == "Inserimento":
    st.subheader("Nuova Registrazione Adozione")
    if "form_id" not in st.session_state: st.session_state.form_id = 0

    with st.container(border=True):
        titolo_scelto = st.selectbox("📕 SELEZIONA TITOLO", [""] + elenco_titoli, key=f"tit_{st.session_state.form_id}")
        if titolo_scelto:
            info = catalogo[catalogo.iloc[:, 0] == titolo_scelto]
            if not info.empty:
                st.info(f"Materia: {info.iloc[0,1]} | Editore: {info.iloc[0,2]} | Agenzia: {info.iloc[0,3]}")
        
        c1, c2 = st.columns(2)
        with c1:
            plesso = st.selectbox("🏫 Plesso", [""] + elenco_plessi, key=f"ple_{st.session_state.form_id}")
            n_sez = st.number_input("🔢 N° sezioni", min_value=1, value=1, key=f"n_{st.session_state.form_id}")
        with c2:
            sez_lett = st.text_input("🔡 Lettera Sezione", key=f"sez_{st.session_state.form_id}")
            note = st.text_area("📝 Note", key=f"not_{st.session_state.form_id}")

        if st.button("💾 SALVA ADOZIONE", use_container_width=True, type="primary"):
            if titolo_scelto and plesso:
                info = catalogo[catalogo.iloc[:, 0] == titolo_scelto]
                nuova_riga = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Plesso": plesso, 
                    "Materia": info.iloc[0,1], 
                    "Titolo": titolo_scelto,
                    "Editore": info.iloc[0,2], 
                    "Agenzia": info.iloc[0,3], 
                    "N° sezioni": n_sez, 
                    "Sezione": sez_lett.upper(), 
                    "Note": note
                }])
                
                df_attuale = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
                df_finale = pd.concat([df_attuale, nuova_riga], ignore_index=True)
                df_finale.to_csv(DB_FILE, index=False)
                
                # BACKUP AUTOMATICO SU CLOUD
                backup_su_google_sheets(df_finale)
                
                # Messaggio a scomparsa che sopravvive al rerun
                st.toast("✅ Registrazione avvenuta con successo!", icon="🎉")
                
                # Incrementiamo l'ID per resettare i widget e facciamo il rerun
                st.session_state.form_id += 1
                st.rerun()
            else: 
                st.error("⚠️ Seleziona Titolo e Plesso!")
elif st.session_state.pagina == "Modifica":
    st.subheader("✏️ Modifica o Cancella Adozioni")
    
    # FORZIAMO IL CARICAMENTO DEI DATI PER I MENU A TENDINA
    elenco_plessi = get_lista_plessi()
    catalogo = get_catalogo_libri()
    elenco_titoli = sorted([str(x) for x in catalogo.iloc[:, 0].unique() if str(x).strip() != ""]) if not catalogo.empty else []

    if os.path.exists(DB_FILE):
        df_mod = pd.read_csv(DB_FILE).fillna("").astype(str)
        
        # FILTRI DI RICERCA (In alto)
        c_ric1, c_ric2 = st.columns(2)
        with c_ric1:
            lista_plessi_db = sorted([x for x in df_mod["Plesso"].unique() if x != ""])
            p_cerca = st.selectbox("🔍 Filtra per Plesso", [""] + lista_plessi_db)
        with c_ric2:
            lista_titoli_db = sorted([x for x in df_mod["Titolo"].unique() if x != ""])
            t_cerca = st.selectbox("🔍 Filtra per Titolo", [""] + lista_titoli_db)
        
        # LOGICA DI VISUALIZZAZIONE
        if p_cerca or t_cerca:
            df_filtrato = df_mod.copy()
            if p_cerca: df_filtrato = df_filtrato[df_filtrato["Plesso"] == p_cerca]
            if t_cerca: df_filtrato = df_filtrato[df_filtrato["Titolo"] == t_cerca]

            if not df_filtrato.empty:
                for i in df_filtrato.index:
                    with st.container(border=True):
                        st.markdown(f"**Registrazione del {df_mod.at[i, 'Data']}**")
                        col1, col2, col3 = st.columns([2, 2, 1])
                        
                        with col1:
                            # PLESSO: Cerchiamo l'indice corretto per mostrare il valore attuale
                            try:
                                idx_p = elenco_plessi.index(df_mod.at[i, 'Plesso'])
                            except ValueError:
                                idx_p = 0
                            nuovo_plesso = st.selectbox(f"Plesso", elenco_plessi, index=idx_p, key=f"p_{i}")

                            # TITOLO: Cerchiamo l'indice corretto per mostrare il valore attuale
                            try:
                                idx_t = elenco_titoli.index(df_mod.at[i, 'Titolo'])
                            except ValueError:
                                idx_t = 0
                            nuovo_titolo = st.selectbox(f"Titolo Libro", elenco_titoli, index=idx_t, key=f"t_{i}")

                        with col2:
                            valore_sez = int(float(df_mod.at[i, 'N° sezioni'])) if df_mod.at[i, 'N° sezioni'] else 1
                            nuovo_n_sez = st.number_input("N° sezioni", min_value=1, value=valore_sez, key=f"n_{i}")
                            nuova_sez_lett = st.text_input("Lettera Sezione", value=df_mod.at[i, 'Sezione'], key=f"s_{i}")
                        
                        with col3:
                            nuove_note = st.text_area("Note", value=df_mod.at[i, 'Note'], key=f"not_{i}")

                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("💾 AGGIORNA", key=f"sav_{i}", use_container_width=True, type="primary"):
                                info_new = catalogo[catalogo.iloc[:, 0] == nuovo_titolo]
                                df_mod.at[i, 'Plesso'] = nuovo_plesso
                                df_mod.at[i, 'Titolo'] = nuovo_titolo
                                if not info_new.empty:
                                    df_mod.at[i, 'Materia'] = info_new.iloc[0,1]
                                    df_mod.at[i, 'Editore'] = info_new.iloc[0,2]
                                    df_mod.at[i, 'Agenzia'] = info_new.iloc[0,3]
                                df_mod.at[i, 'N° sezioni'] = nuovo_n_sez
                                df_mod.at[i, 'Sezione'] = nuova_sez_lett.upper()
                                df_mod.at[i, 'Note'] = nuove_note
                                df_mod.to_csv(DB_FILE, index=False)
                                backup_su_google_sheets(df_mod) 
                                st.rerun()
                        with b2:
                            if st.button("🗑️ ELIMINA", key=f"del_{i}", use_container_width=True):
                                df_mod = df_mod.drop(i)
                                df_mod.to_csv(DB_FILE, index=False)
                                backup_su_google_sheets(df_mod)
                                st.rerun()
            else:
                st.warning("Nessun record trovato con i filtri selezionati.")
        else:
            st.info("🔍 Seleziona un Plesso o un Titolo per visualizzare i dati da modificare.")

elif st.session_state.pagina == "Registro":
    st.subheader("📑 Registro Completo")
    if os.path.exists(DB_FILE):
        st.dataframe(pd.read_csv(DB_FILE).sort_index(ascending=False), use_container_width=True)
    else: st.info("Nessuna registrazione presente.")

elif st.session_state.pagina == "Ricerca":
    st.subheader("🔍 Motore di Ricerca Adozioni")
    if "r_attiva" not in st.session_state: st.session_state.r_attiva = False
    with st.container(border=True):
        r1c1, r1c2 = st.columns(2)
        with r1c1: f_tit = st.multiselect("📕 Titolo Libro", elenco_titoli, key="ft")
        with r1c2: f_age = st.multiselect("🤝 Agenzia", elenco_agenzie, key="fa")
        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1: f_ple = st.multiselect("🏫 Plesso", ["NESSUNO"] + elenco_plessi, key="fp")
        with r2c2: f_mat = st.multiselect("📖 Materia", elenco_materie, key="fm")
        with r2c3: f_edi = st.multiselect("🏢 Editore", elenco_editori, key="fe")
        
        btn1, btn2, _ = st.columns([1, 1, 2])
        with btn1:
            if st.button("🔍 AVVIA RICERCA", use_container_width=True, type="primary"): st.session_state.r_attiva = True
        with btn2:
            if st.button("🧹 PULISCI", use_container_width=True, on_click=reset_ricerca): st.rerun()

    if st.session_state.r_attiva and os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE).fillna("").astype(str)
        if f_ple: df = df[df["Plesso"].isin(f_ple)]
        if f_tit: df = df[df["Titolo"].isin(f_tit)]
        if f_age: df = df[df["Agenzia"].isin(f_age)]
        if f_mat: df = df[df["Materia"].isin(f_mat)]
        if f_edi: df = df[df["Editore"].isin(f_edi)]

        if not df.empty:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
            somma = pd.to_numeric(df["N° sezioni"], errors='coerce').sum()
            st.markdown(f"""<div class="totale-box">🔢 Totale Classi: <b>{int(somma)}</b></div>""", unsafe_allow_html=True)
        else: st.warning("Nessun dato trovato.")

st.markdown("<p style='text-align: center; color: gray;'>Created by Antonio Ciccarelli v12.9</p>", unsafe_allow_html=True)





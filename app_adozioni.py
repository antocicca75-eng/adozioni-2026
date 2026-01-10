import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import io

# --- CONFIGURAZIONE ---
CONFIG_FILE = "anagrafiche.xlsx"
# Nome del foglio all'interno del file Google Sheets (visto nell'immagine)
SHEET_NAME = "Adozioni_DB"

st.set_page_config(page_title="Adozioni 2026", layout="wide", page_icon="📚")

# --- CONNESSIONE GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- STILE CSS ---
st.markdown("""
    <style>
    [data-testid="stDataEditor"] thead tr th { background-color: #004a99 !important; color: white !important; }
    .stApp { background-color: #ffffff; }
    .totale-box { padding: 20px; background-color: #e8f0fe; border-radius: 10px; border: 1px solid #004a99; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DATI ---
def get_db_data():
    """Legge il database dal Cloud in modo sicuro"""
    try:
        # Tentativo 1: Cerca il foglio specifico configurato
        return conn.read(worksheet=SHEET_NAME, ttl="0s").fillna("")
    except Exception:
        try:
            # Tentativo 2: Se il nome fallisce, legge il primo foglio a sinistra
            # Questo evita il 404 se il nome del tab è leggermente diverso
            return conn.read(ttl="0s").fillna("")
        except Exception as e:
            st.error(f"Errore connessione Cloud: {e}")
            return pd.DataFrame()

def salva_su_gsheets(df):
    """Salva il dataframe su Google Sheets"""
    try:
        df_clean = df.fillna("")
        conn.update(worksheet=SHEET_NAME, data=df_clean)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio Cloud: {e}")
        return False

@st.cache_data
def get_catalogo_libri():
    """Legge il catalogo locale Excel (anagrafiche)"""
    if os.path.exists(CONFIG_FILE):
        try:
            df = pd.read_excel(CONFIG_FILE, sheet_name="ListaLibri")
            df.columns = [c.strip() for c in df.columns]
            return df.fillna("")
        except: return pd.DataFrame()
    return pd.DataFrame()

def get_lista_plessi():
    """Legge la lista plessi locale"""
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

# --- NAVIGAZIONE ---
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
    pagine = ["Inserimento", "Modifica", "NuovoLibro", "Registro", "Ricerca"]
    labels = ["➕ NUOVA ADOZIONE", "✏️ MODIFICA ADOZIONE", "🆕 AGGIUNGI CATALOGO", "📊 REGISTRO COMPLETO", "🔍 FILTRA E RICERCA"]
    
    for pag, lab in zip(pagine, labels):
        if st.button(lab, use_container_width=True, type="primary" if st.session_state.pagina == pag else "secondary"):
            st.session_state.pagina = pag
            st.rerun()

    st.markdown("---")
    st.subheader("📥 Export Excel")
    df_cloud = get_db_data()
    if not df_cloud.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_cloud.to_excel(writer, index=False, sheet_name='Adozioni')
        st.download_button("💾 SCARICA EXCEL", data=buffer.getvalue(), 
                         file_name=f"adozioni_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                         use_container_width=True)

st.title("📚 Gestione Adozioni 2026")

# --- 1. NUOVO LIBRO (LOCALE) ---
if st.session_state.pagina == "NuovoLibro":
    st.subheader("🆕 Aggiungi titolo al catalogo Excel")
    with st.container(border=True):
        nt = st.text_input("Titolo Libro")
        col1, col2, col3 = st.columns(3)
        with col1:
            m_sel = st.selectbox("Materia", [""] + elenco_materie + ["-- NUOVA --"])
            m_val = st.text_input("Specifica") if m_sel == "-- NUOVA --" else m_sel
        with col2:
            e_sel = st.selectbox("Editore", [""] + elenco_editori + ["-- NUOVO --"])
            e_val = st.text_input("Specifica") if e_sel == "-- NUOVO --" else e_sel
        with col3:
            a_sel = st.selectbox("Agenzia", [""] + elenco_agenzie + ["-- NUOVA --"])
            a_val = st.text_input("Specifica") if a_sel == "-- NUOVA --" else a_sel
        
        if st.button("✅ SALVA", use_container_width=True, type="primary"):
            # Nota: Questa operazione rimane locale/file-based
            st.warning("L'aggiunta al catalogo richiede permessi di scrittura sul file Excel locale del server.")

# --- 2. NUOVA ADOZIONE (CLOUD) ---
elif st.session_state.pagina == "Inserimento":
    st.subheader("Nuova Registrazione Adozione")
    if "form_id" not in st.session_state: st.session_state.form_id = 0

    with st.container(border=True):
        titolo_scelto = st.selectbox("📕 SELEZIONA TITOLO", [""] + elenco_titoli, key=f"t_{st.session_state.form_id}")
        if titolo_scelto:
            info = catalogo[catalogo.iloc[:, 0] == titolo_scelto]
            if not info.empty:
                st.info(f"Materia: {info.iloc[0,1]} | Editore: {info.iloc[0,2]} | Agenzia: {info.iloc[0,3]}")
        
        c1, c2 = st.columns(2)
        with c1:
            plesso = st.selectbox("🏫 Plesso", [""] + elenco_plessi, key=f"p_{st.session_state.form_id}")
            n_sez = st.number_input("🔢 N° sezioni", min_value=1, value=1, key=f"n_{st.session_state.form_id}")
        with c2:
            sez_lett = st.text_input("🔡 Lettera Sezione", key=f"s_{st.session_state.form_id}")
            note = st.text_area("📝 Note", key=f"no_{st.session_state.form_id}")

        if st.button("💾 SALVA ADOZIONE", use_container_width=True, type="primary"):
            if titolo_scelto and plesso:
                info = catalogo[catalogo.iloc[:, 0] == titolo_scelto]
                nuova_riga = pd.DataFrame([{
                    "DATA": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "PLESSO": plesso, 
                    "MATERIA": info.iloc[0,1], 
                    "TITOLO": titolo_scelto,
                    "EDITORE": info.iloc[0,2], 
                    "AGENZIA": info.iloc[0,3], 
                    "N° sezioni": str(n_sez), 
                    "Sezione": sez_lett.upper(), 
                    "Note": note
                }])
                
                df_attuale = get_db_data()
                df_nuovo = pd.concat([df_attuale, nuova_riga], ignore_index=True)
                if salva_su_gsheets(df_nuovo):
                    st.success("Registrato su Cloud!")
                    st.session_state.form_id += 1
                    st.rerun()
            else: st.error("Compila i campi obbligatori!")

# --- 3. MODIFICA (CLOUD) ---
elif st.session_state.pagina == "Modifica":
    st.subheader("✏️ Modifica o Cancella Adozioni")
    df_mod = get_db_data()
    
    if not df_mod.empty:
        df_mod = df_mod.astype(str)
        c_ric1, c_ric2 = st.columns(2)
        with c_ric1:
            lista_plessi_db = sorted([x for x in df_mod["PLESSO"].unique() if x != ""])
            p_cerca = st.selectbox("🔍 Filtra per Plesso", [""] + lista_plessi_db)
        with c_ric2:
            lista_titoli_db = sorted([x for x in df_mod["TITOLO"].unique() if x != ""])
            t_cerca = st.selectbox("🔍 Filtra per Titolo", [""] + lista_titoli_db)
        
        if p_cerca or t_cerca:
            df_filtrato = df_mod.copy()
            if p_cerca: df_filtrato = df_filtrato[df_filtrato["PLESSO"] == p_cerca]
            if t_cerca: df_filtrato = df_filtrato[df_filtrato["TITOLO"] == t_cerca]

            for i in df_filtrato.index:
                with st.container(border=True):
                    st.markdown(f"**Registrazione del {df_mod.at[i, 'DATA']}**")
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        nuovo_plesso = st.selectbox(f"Plesso", elenco_plessi, index=elenco_plessi.index(df_mod.at[i, 'PLESSO']) if df_mod.at[i, 'PLESSO'] in elenco_plessi else 0, key=f"p_{i}")
                        nuovo_titolo = st.selectbox(f"Titolo", elenco_titoli, index=elenco_titoli.index(df_mod.at[i, 'TITOLO']) if df_mod.at[i, 'TITOLO'] in elenco_titoli else 0, key=f"t_{i}")
                    with col2:
                        nuovo_n_sez = st.number_input("Sezioni", min_value=1, value=int(float(df_mod.at[i, 'N° sezioni'])) if df_mod.at[i, 'N° sezioni'] else 1, key=f"n_{i}")
                        nuova_sez = st.text_input("Lettera", value=df_mod.at[i, 'Sezione'], key=f"s_{i}")
                    with col3:
                        nuove_note = st.text_area("Note", value=df_mod.at[i, 'Note'], key=f"no_{i}")

                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("💾 AGGIORNA", key=f"up_{i}", use_container_width=True, type="primary"):
                            df_mod.at[i, 'PLESSO'] = nuovo_plesso
                            df_mod.at[i, 'TITOLO'] = nuovo_titolo
                            df_mod.at[i, 'N° sezioni'] = str(nuovo_n_sez)
                            df_mod.at[i, 'Sezione'] = nuova_sez.upper()
                            df_mod.at[i, 'Note'] = nuove_note
                            salva_su_gsheets(df_mod)
                            st.rerun()
                    with b2:
                        if st.button("🗑️ ELIMINA", key=f"del_{i}", use_container_width=True):
                            df_mod = df_mod.drop(i)
                            salva_su_gsheets(df_mod)
                            st.rerun()
    else: st.info("Database Cloud vuoto.")

# --- 4. REGISTRO (CLOUD) ---
elif st.session_state.pagina == "Registro":
    st.subheader("📑 Registro Completo")
    df = get_db_data()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else: st.info("Nessun dato.")

# --- 5. RICERCA (CLOUD) ---
elif st.session_state.pagina == "Ricerca":
    st.subheader("🔍 Motore di Ricerca")
    if "r_attiva" not in st.session_state: st.session_state.r_attiva = False
    
    with st.container(border=True):
        r1c1, r1c2 = st.columns(2)
        with r1c1: f_tit = st.multiselect("Titolo", elenco_titoli, key="ft")
        with r1c2: f_age = st.multiselect("Agenzia", elenco_agenzie, key="fa")
        if st.button("🔍 RICERCA", type="primary"): st.session_state.r_attiva = True
        if st.button("🧹 PULISCI", on_click=reset_ricerca): st.rerun()

    if st.session_state.r_attiva:
        df = get_db_data()
        if not df.empty:
            df = df.astype(str)
            if f_tit: df = df[df["TITOLO"].isin(f_tit)]
            if f_age: df = df[df["AGENZIA"].isin(f_age)]
            st.dataframe(df, use_container_width=True)
            somma = pd.to_numeric(df["N° sezioni"], errors='coerce').sum()
            st.markdown(f'<div class="totale-box">🔢 Totale Classi: <b>{int(somma)}</b></div>', unsafe_allow_html=True)


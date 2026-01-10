import streamlit as st
import pandas as pd
import os
from datetime import datetime
from openpyxl import load_workbook

# --- CONFIGURAZIONE FILE ---
DB_FILE = "dati_adozioni.csv"
CONFIG_FILE = "anagrafiche.xlsx"

st.set_page_config(page_title="Adozioni 2026", layout="wide", page_icon="📚")

# --- STILE CSS ---
st.markdown("""
    <style>
    [data-testid="stDataEditor"] thead tr th { background-color: #004a99 !important; color: white !important; }
    .stApp { background-color: #ffffff; }
    .totale-box { padding: 20px; background-color: #e8f0fe; border-radius: 10px; border: 1px solid #004a99; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CARICAMENTO E SCRITTURA ---
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

# --- GESTIONE NAVIGAZIONE E RESET ---
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
    if st.button("🆕 AGGIUNGI A CATALOGO", use_container_width=True, type="primary" if st.session_state.pagina == "NuovoLibro" else "secondary"):
        st.session_state.pagina = "NuovoLibro"
        st.rerun()
    if st.button("📊 REGISTRO COMPLETO", use_container_width=True, type="primary" if st.session_state.pagina == "Registro" else "secondary"):
        st.session_state.pagina = "Registro"
        st.rerun()
    if st.button("🔍 FILTRA E RICERCA", use_container_width=True, type="primary" if st.session_state.pagina == "Ricerca" else "secondary"):
        st.session_state.pagina = "Ricerca"
        st.rerun()

st.title("📚 Gestione Adozioni 2026")

# --- 1. SCHERMATA AGGIUNGI NUOVO LIBRO ---
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
                else:
                    st.error("Errore: chiudi il file Excel!")

# --- 2. NUOVA ADOZIONE ---
elif st.session_state.pagina == "Inserimento":
    st.subheader("Nuova Registrazione Adozione")
    with st.container(border=True):
        titolo_scelto = st.selectbox("📕 SELEZIONA TITOLO", [""] + elenco_titoli, key="tit_ins")
        if titolo_scelto:
            info = catalogo[catalogo.iloc[:, 0] == titolo_scelto]
            if not info.empty:
                st.info(f"Materia: {info.iloc[0,1]} | Editore: {info.iloc[0,2]} | Agenzia: {info.iloc[0,3]}")
        
        c1, c2 = st.columns(2)
        with c1:
            plesso = st.selectbox("🏫 Plesso", [""] + elenco_plessi)
            n_sez = st.number_input("🔢 N° sezioni", min_value=1, value=1)
        with c2:
            sez_lett = st.text_input("🔡 Lettera Sezione")
            note = st.text_area("📝 Note")

        if st.button("💾 SALVA ADOZIONE", use_container_width=True, type="primary"):
            if titolo_scelto and plesso:
                info = catalogo[catalogo.iloc[:, 0] == titolo_scelto]
                nuova_riga = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Plesso": plesso, "Materia": info.iloc[0,1], "Titolo": titolo_scelto,
                    "Editore": info.iloc[0,2], "Agenzia": info.iloc[0,3], 
                    "N° sezioni": n_sez, "Sezione": sez_lett.upper(), "Note": note
                }])
                df_attuale = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
                pd.concat([df_attuale, nuova_riga], ignore_index=True).to_csv(DB_FILE, index=False)
                st.success("Adozione registrata!")

# --- 3. REGISTRO COMPLETO ---
elif st.session_state.pagina == "Registro":
    st.subheader("📑 Registro Completo")
    if os.path.exists(DB_FILE):
        st.dataframe(pd.read_csv(DB_FILE).sort_index(ascending=False), use_container_width=True)
    else:
        st.info("Nessuna registrazione presente.")

# --- 4. RICERCA (CON LOGICA PLESSO RICHIESTA) ---
elif st.session_state.pagina == "Ricerca":
    st.subheader("🔍 Motore di Ricerca Adozioni")
    if "r_attiva" not in st.session_state: st.session_state.r_attiva = False

    with st.container(border=True):
        st.markdown("##### 🛠️ Imposta i Filtri")
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            f_tit = st.multiselect("📕 Titolo Libro", elenco_titoli, key="ft")
        with r1c2:
            f_age = st.multiselect("🤝 Agenzia", elenco_agenzie, key="fa")
        
        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            # Aggiunta voce "NESSUNO"
            f_ple = st.multiselect("🏫 Plesso", ["NESSUNO"] + elenco_plessi, key="fp")
        with r2c2:
            f_mat = st.multiselect("📖 Materia", elenco_materie, key="fm")
        with r2c3:
            f_edi = st.multiselect("🏢 Editore", elenco_editori, key="fe")
        
        st.markdown("<br>", unsafe_allow_html=True)
        btn1, btn2, _ = st.columns([1, 1, 2])
        with btn1:
            if st.button("🔍 AVVIA RICERCA", use_container_width=True, type="primary"):
                st.session_state.r_attiva = True
        with btn2:
            if st.button("🧹 PULISCI", use_container_width=True, on_click=reset_ricerca):
                st.rerun()

    if st.session_state.r_attiva:
        if os.path.exists(DB_FILE):
            df = pd.read_csv(DB_FILE).fillna("").astype(str)
            
            # --- LOGICA FILTRO PLESSO ---
            if f_ple:
                if "NESSUNO" in f_ple:
                    # Filtra via tutto (mostra tabella vuota per i plessi)
                    df = df[df["Plesso"] == "___ZERO_RESULTS___"]
                else:
                    # Filtra solo i plessi selezionati
                    df = df[df["Plesso"].isin(f_ple)]
            # Se f_ple è vuoto, NON filtra nulla (mostra tutti i plessi)

            # --- ALTRI FILTRI ---
            if f_tit: df = df[df["Titolo"].isin(f_tit)]
            if f_age: df = df[df["Agenzia"].isin(f_age)]
            if f_mat: df = df[df["Materia"].isin(f_mat)]
            if f_edi: df = df[df["Editore"].isin(f_edi)]

            if not df.empty:
                st.dataframe(df.sort_index(ascending=False), use_container_width=True)
                somma = pd.to_numeric(df["N° sezioni"], errors='coerce').sum()
                st.markdown(f"""<div class="totale-box">🔢 Totale Classi: <b>{int(somma)}</b></div>""", unsafe_allow_html=True)
            else:
                st.warning("Nessun dato trovato.")
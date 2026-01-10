import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Adozioni 2026", layout="wide", page_icon="📚")

# --- CONNESSIONE GOOGLE SHEETS (TEST DI CONNESSIONE) ---
try:
    # Connessione principale
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Errore fatale di configurazione. Verifica i Secrets.")
    st.stop()

# --- STILE CSS ---
st.markdown("""
    <style>
    [data-testid="stDataEditor"] thead tr th { background-color: #004a99 !important; color: white !important; }
    .stApp { background-color: #ffffff; }
    .totale-box { padding: 20px; background-color: #e8f0fe; border-radius: 10px; border: 1px solid #004a99; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CARICAMENTO DATI ---

def get_catalogo_libri():
    try:
        # ttl=1 forza il ricaricamento quasi immediato per il test
        df = conn.read(worksheet="Catalogo", ttl=1)
        if df is not None:
            df.columns = [c.strip().capitalize() for c in df.columns]
            return df.fillna("")
        return pd.DataFrame()
    except Exception as e:
        st.sidebar.error(f"Errore Catalogo: {e}")
        return pd.DataFrame()

def get_lista_plessi():
    try:
        df = conn.read(worksheet="Plesso", ttl=1)
        return sorted(df.iloc[:, 0].dropna().unique().tolist())
    except:
        return []

def get_lista_agenzie():
    try:
        df = conn.read(worksheet="Agenzie", ttl=1)
        return sorted(df.iloc[:, 0].dropna().unique().tolist())
    except:
        return []

def salva_adozione_google(nuova_riga_dict):
    try:
        df_esistente = conn.read(worksheet="Adozioni", ttl=0)
        nuova_riga_df = pd.DataFrame([nuova_riga_dict])
        df_finale = pd.concat([df_esistente, nuova_riga_df], ignore_index=True)
        conn.update(worksheet="Adozioni", data=df_finale)
        return True
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")
        return False

def aggiungi_libro_catalogo_google(t, m, e, a):
    try:
        df_esistente = conn.read(worksheet="Catalogo", ttl=0)
        nuova_riga = pd.DataFrame([{"Titolo": t, "Materia": m, "Editore": e, "Agenzia": a}])
        df_finale = pd.concat([df_esistente, nuova_riga], ignore_index=True)
        conn.update(worksheet="Catalogo", data=df_finale)
        return True
    except:
        return False

# --- PREPARAZIONE DATI ---
catalogo = get_catalogo_libri()
if not catalogo.empty:
    elenco_titoli = sorted([str(x) for x in catalogo.iloc[:, 0].unique() if str(x).strip() != ""])
    elenco_materie = sorted([str(x) for x in catalogo.iloc[:, 1].unique() if str(x).strip() != ""])
    elenco_editori = sorted([str(x) for x in catalogo.iloc[:, 2].unique() if str(x).strip() != ""])
else:
    elenco_titoli = elenco_materie = elenco_editori = []

elenco_plessi = get_lista_plessi()
elenco_agenzie = get_lista_agenzie()

# --- SIDEBAR E TEST CONNESSIONE ---
with st.sidebar:
    st.title("🧭 MENU")
    
    # PULSANTE DI RESET CACHE (TEST DI CONNESSIONE)
    if st.button("🔄 REFRESH DATI (TEST)", use_container_width=True):
        st.cache_data.clear()
        st.toast("Cache pulita! Ricaricamento...")
        st.rerun()

    st.markdown("---")
    if st.button("➕ NUOVA ADOZIONE", use_container_width=True, type="primary" if st.session_state.get("pagina") == "Inserimento" else "secondary"):
        st.session_state.pagina = "Inserimento"
        st.rerun()
    if st.button("🆕 AGGIUNGI A CATALOGO", use_container_width=True):
        st.session_state.pagina = "NuovoLibro"
        st.rerun()
    if st.button("📊 REGISTRO COMPLETO", use_container_width=True):
        st.session_state.pagina = "Registro"
        st.rerun()
    if st.button("🔍 FILTRA E RICERCA", use_container_width=True):
        st.session_state.pagina = "Ricerca"
        st.rerun()

    st.markdown("---")
    st.subheader("💾 Backup")
    try:
        df_back = conn.read(worksheet="Adozioni", ttl=0)
        if df_back is not None and not df_back.empty:
            st.download_button("📥 SCARICA CSV", df_back.to_csv(index=False).encode('utf-8'), "backup.csv", "text/csv", use_container_width=True)
        else:
            st.info("Nessun dato da scaricare.")
    except:
        st.warning("Connessione instabile...")

# --- LOGICA PAGINE ---
if "pagina" not in st.session_state:
    st.session_state.pagina = "Inserimento"

st.title("📚 Gestione Adozioni 2026")

# --- 1. NUOVA ADOZIONE ---
if st.session_state.pagina == "Inserimento":
    st.subheader("Nuova Registrazione")
    if not elenco_titoli:
        st.warning("⚠️ ATTENZIONE: Il catalogo libri sembra vuoto. Controlla il foglio Google o premi 'Refresh' nella sidebar.")
    
    with st.container(border=True):
        titolo_scelto = st.selectbox("📕 SELEZIONA TITOLO", [""] + elenco_titoli)
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

        if st.button("💾 SALVA ONLINE", use_container_width=True, type="primary"):
            if titolo_scelto and plesso:
                info = catalogo[catalogo.iloc[:, 0] == titolo_scelto]
                nuovo_dato = {
                    "DATA": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "PLESSO": plesso, "MATERIA": info.iloc[0,1], "TITOLO": titolo_scelto,
                    "EDITORE": info.iloc[0,2], "AGENZIA": info.iloc[0,3], 
                    "N° sezioni": n_sez, "Sezione": sez_lett.upper(), "Note": note
                }
                if salva_adozione_google(nuovo_dato):
                    st.success("Dato inviato con successo!")
                    st.rerun()
            else:
                st.error("Campi obbligatori mancanti!")

# --- ALTRE PAGINE (Semplificate per test) ---
elif st.session_state.pagina == "Registro":
    st.subheader("📑 Registro")
    df_reg = conn.read(worksheet="Adozioni", ttl=0)
    st.dataframe(df_reg, use_container_width=True)

elif st.session_state.pagina == "NuovoLibro":
    st.subheader("🆕 Nuovo Libro")
    # ... (Codice inserimento catalogo simile a prima)

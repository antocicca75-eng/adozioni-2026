import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Adozioni 2026", layout="wide", page_icon="📚")

# --- STILE CSS ---
st.markdown("""
    <style>
    [data-testid="stDataEditor"] thead tr th { background-color: #004a99 !important; color: white !important; }
    .stApp { background-color: #ffffff; }
    .totale-box { padding: 20px; background-color: #e8f0fe; border-radius: 10px; border: 1px solid #004a99; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CARICAMENTO DA REPOSITORY (CSV) ---
def get_catalogo_libri():
    try:
        df = pd.read_csv("Catalogo.csv")
        df.columns = [c.strip() for c in df.columns]
        return df.fillna("")
    except:
        return pd.DataFrame(columns=["Titolo", "Materia", "Editore", "Agenzia"])

def get_lista_plessi():
    try:
        df = pd.read_csv("Plesso.csv")
        return sorted(df.iloc[:, 0].dropna().unique().tolist())
    except:
        return ["Plesso A", "Plesso B", "Plesso C"]

def get_lista_agenzie():
    try:
        df = pd.read_csv("Agenzie.csv")
        return sorted(df.iloc[:, 0].dropna().unique().tolist())
    except:
        return []

def get_adozioni_esistenti():
    try:
        df = pd.read_csv("Adozioni.csv")
        return df.fillna("")
    except:
        return pd.DataFrame()

# --- PREPARAZIONE DATI ---
catalogo = get_catalogo_libri()
if not catalogo.empty:
    elenco_titoli = sorted([str(x) for x in catalogo.iloc[:, 0].unique() if str(x).strip() != ""])
    elenco_materie = sorted([str(x) for x in catalogo.iloc[:, 1].unique() if str(x).strip() != ""])
    elenco_editori = sorted([str(x) for x in catalogo.iloc[:, 2].unique() if str(x).strip() != ""])
    elenco_agenzie = get_lista_agenzie()
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
    if st.button("🆕 AGGIUNGI A CATALOGO", use_container_width=True, type="primary" if st.session_state.pagina == "NuovoLibro" else "secondary"):
        st.session_state.pagina = "NuovoLibro"
        st.rerun()
    if st.button("📊 REGISTRO COMPLETO", use_container_width=True, type="primary" if st.session_state.pagina == "Registro" else "secondary"):
        st.session_state.pagina = "Registro"
        st.rerun()
    if st.button("🔍 FILTRA E RICERCA", use_container_width=True, type="primary" if st.session_state.pagina == "Ricerca" else "secondary"):
        st.session_state.pagina = "Ricerca"
        st.rerun()

    # --- AGGIUNTA EXPORT EXCEL IN FONDO ALLA SIDEBAR ---
    st.markdown("---")
    st.subheader("📥 Export Dati")
    df_da_esportare = get_adozioni_esistenti()
    if not df_da_esportare.empty:
        buffer = io.BytesIO()
        # Nota: assicurati che 'openpyxl' sia presente nel file requirements.txt
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_da_esportare.to_excel(writer, index=False, sheet_name='Adozioni')
        
        st.download_button(
            label="💾 SCARICA EXCEL (.xlsx)",
            data=buffer.getvalue(),
            file_name=f"adozioni_export_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.caption("Nessun dato disponibile per l'export.")

st.title("📚 Gestione Adozioni 2026 (Modalità CSV)")

# --- 1. SCHERMATA NUOVO LIBRO ---
if st.session_state.pagina == "NuovoLibro":
    st.subheader("🆕 Aggiungi nuovo titolo al Catalogo locale")
    st.warning("Nota: In questa modalità CSV, le modifiche non verranno salvate permanentemente su GitHub.")
    with st.container(border=True):
        nt = st.text_input("Inserisci Titolo Libro")
        # Layout mantenuto come da richiesta

# --- 2. NUOVA ADOZIONE ---
elif st.session_state.pagina == "Inserimento":
    st.subheader("Nuova Registrazione Adozione")
    with st.container(border=True):
        titolo_scelto = st.selectbox("📕 SELEZIONA TITOLO", [""] + elenco_titoli)
        if st.button("💾 REGISTRA TEMPORANEAMENTE"):
            st.info("I dati sono letti da CSV. Per salvare davvero serve la connessione Google Sheets.")

# --- 3. REGISTRO ---
elif st.session_state.pagina == "Registro":
    st.subheader("📑 Registro dai file CSV")
    df_reg = get_adozioni_esistenti()
    st.dataframe(df_reg, use_container_width=True)

# --- 4. RICERCA ---
elif st.session_state.pagina == "Ricerca":
    st.subheader("🔍 Ricerca nel database CSV")
    df_search = get_adozioni_esistenti()
    if not df_search.empty:
        st.dataframe(df_search, use_container_width=True)

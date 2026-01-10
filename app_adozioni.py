import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Adozioni 2026", layout="wide", page_icon="📚")

# --- CONNESSIONE GOOGLE SHEETS ---
# Questa connessione cercherà l'URL del foglio nei "Secrets" di Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

# --- STILE CSS ---
st.markdown("""
    <style>
    [data-testid="stDataEditor"] thead tr th { background-color: #004a99 !important; color: white !important; }
    .stApp { background-color: #ffffff; }
    .totale-box { padding: 20px; background-color: #e8f0fe; border-radius: 10px; border: 1px solid #004a99; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CARICAMENTO E SCRITTURA (GOOGLE SHEETS) ---
def get_catalogo_libri():
    try:
        # Legge il foglio 'ListaLibri' dal Foglio Google
        df = conn.read(worksheet="ListaLibri", ttl="1m")
        df.columns = [c.strip() for c in df.columns]
        return df.fillna("")
    except:
        return pd.DataFrame()

def get_lista_plessi():
    # Per semplicità, i plessi li teniamo fissi o li leggiamo da un foglio chiamato 'Plesso'
    try:
        df = conn.read(worksheet="Plesso", ttl="10m")
        return sorted(df.iloc[:, 0].dropna().unique().tolist())
    except:
        return ["Plesso A", "Plesso B", "Plesso C"] # Default se manca il foglio

def salva_adozione_google(nuova_riga_dict):
    try:
        # 1. Legge i dati esistenti dal foglio 'Adozioni'
        df_esistente = conn.read(worksheet="Adozioni", ttl=0)
        # 2. Crea il DataFrame della nuova riga
        nuova_riga_df = pd.DataFrame([nuova_riga_dict])
        # 3. Concatena
        df_finale = pd.concat([df_esistente, nuova_riga_df], ignore_index=True)
        # 4. Sovrascrive il foglio Google
        conn.update(worksheet="Adozioni", data=df_finale)
        return True
    except Exception as e:
        st.error(f"Errore durante il salvataggio: {e}")
        return False

def aggiungi_libro_catalogo_google(t, m, e, a):
    try:
        df_esistente = conn.read(worksheet="ListaLibri", ttl=0)
        nuova_riga = pd.DataFrame([{"Titolo": t, "Materia": m, "Editore": e, "Agenzia": a}])
        df_finale = pd.concat([df_esistente, nuova_riga], ignore_index=True)
        conn.update(worksheet="ListaLibri", data=df_finale)
        return True
    except:
        return False

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
    if st.button("🆕 AGGIUNGI A CATALOGO", use_container_width=True, type="primary" if st.session_state.pagina == "NuovoLibro" else "secondary"):
        st.session_state.pagina = "NuovoLibro"
        st.rerun()
    if st.button("📊 REGISTRO COMPLETO", use_container_width=True, type="primary" if st.session_state.pagina == "Registro" else "secondary"):
        st.session_state.pagina = "Registro"
        st.rerun()
    if st.button("🔍 FILTRA E RICERCA", use_container_width=True, type="primary" if st.session_state.pagina == "Ricerca" else "secondary"):
        st.session_state.pagina = "Ricerca"
        st.rerun()
# --- AGGIUNTA NELLA SIDEBAR PER IL BACKUP ---
with st.sidebar:
    st.markdown("---") # Una linea di separazione
    st.subheader("💾 Sicurezza")
    
    # Recupera i dati attuali per il backup
    try:
        df_backup = conn.read(worksheet="Adozioni", ttl="0")
        
        if not df_backup.empty:
            # Converti il DataFrame in CSV per il download
            csv = df_backup.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 SCARICA BACKUP (CSV)",
                data=csv,
                file_name=f"backup_adozioni_{datetime.now().strftime('%d_%m_%Y')}.csv",
                mime='text/csv',
                use_container_width=True
            )
        else:
            st.write("Nessun dato da scaricare.")
    except:
        st.write("Errore caricamento backup.")
st.title("📚 Gestione Adozioni 2026 (Cloud)")

# --- 1. SCHERMATA AGGIUNGI NUOVO LIBRO ---
if st.session_state.pagina == "NuovoLibro":
    st.subheader("🆕 Aggiungi nuovo titolo al Catalogo Google")
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
        
        if st.button("✅ SALVA NEL CLOUD", use_container_width=True, type="primary"):
            if nt and m_val and e_val and a_val:
                if aggiungi_libro_catalogo_google(nt, m_val, e_val, a_val):
                    st.success(f"Libro '{nt}' aggiunto al catalogo!")
                    st.rerun()
            else:
                st.warning("Compila tutti i campi.")

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

        if st.button("💾 SALVA ONLINE", use_container_width=True, type="primary"):
            if titolo_scelto and plesso:
                info = catalogo[catalogo.iloc[:, 0] == titolo_scelto]
                nuovo_dato = {
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Plesso": plesso, "Materia": info.iloc[0,1], "Titolo": titolo_scelto,
                    "Editore": info.iloc[0,2], "Agenzia": info.iloc[0,3], 
                    "N° sezioni": n_sez, "Sezione": sez_lett.upper(), "Note": note
                }
                if salva_adozione_google(nuovo_dato):
                    st.success("Adozione registrata nel Cloud!")
            else:
                st.error("Titolo e Plesso obbligatori!")

# --- 3. REGISTRO COMPLETO ---
elif st.session_state.pagina == "Registro":
    st.subheader("📑 Registro Completo (Google Sheets)")
    df_reg = conn.read(worksheet="Adozioni", ttl="0")
    if not df_reg.empty:
        st.dataframe(df_reg.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("Nessuna registrazione presente.")

# --- 4. RICERCA ---
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
        df = conn.read(worksheet="Adozioni", ttl="0").fillna("").astype(str)
        
        if not df.empty:
            if f_ple:
                if "NESSUNO" in f_ple:
                    df = df[df["Plesso"] == "___ZERO___"]
                else:
                    df = df[df["Plesso"].isin(f_ple)]
            
            if f_tit: df = df[df["Titolo"].isin(f_tit)]
            if f_age: df = df[df["Agenzia"].isin(f_age)]
            if f_mat: df = df[df["Materia"].isin(f_mat)]
            if f_edi: df = df[df["Editore"].isin(f_edi)]

            if not df.empty:
                st.dataframe(df.sort_index(ascending=False), use_container_width=True)
                somma = pd.to_numeric(df["N° sezioni"], errors='coerce').sum()
                st.markdown(f"""<div class="totale-box">🔢 Totale Classi: <b>{int(somma)}</b></div>""", unsafe_allow_html=True)
            else:
                st.warning("Nessun risultato.")


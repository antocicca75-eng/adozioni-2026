import streamlit as st
import pandas as pd
import os
from datetime import datetime
from openpyxl import load_workbook
import io
from streamlit_gsheets import GSheetsConnection  # <--- Nuova libreria per Google Sheets

# --- CONFIGURAZIONE FILE ---
CONFIG_FILE = "anagrafiche.xlsx"

st.set_page_config(page_title="Adozioni 2026", layout="wide", page_icon="📚")

# --- CONNESSIONE GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_db_data():
    """Legge i dati dal database su Google Sheets"""
    try:
        # TTL=0 permette di leggere i dati sempre aggiornati
        return conn.read(ttl=0).dropna(how="all").astype(str)
    except:
        # Se il foglio è vuoto o errore, restituisce un DF con le colonne corrette
        return pd.DataFrame(columns=["Data", "Plesso", "Materia", "Titolo", "Editore", "Agenzia", "N° sezioni", "Sezione", "Note"])

def salva_su_gsheets(df):
    """Aggiorna il database su Google Sheets"""
    conn.update(data=df)
    st.cache_data.clear()

# --- STILE CSS ---
st.markdown("""
    <style>
    [data-testid="stDataEditor"] thead tr th { background-color: #004a99 !important; color: white !important; }
    .stApp { background-color: #ffffff; }
    .totale-box { padding: 20px; background-color: #e8f0fe; border-radius: 10px; border: 1px solid #004a99; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CARICAMENTO E SCRITTURA CATALOGO (EXCEL) ---
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
if "form_id" not in st.session_state:
    st.session_state.form_id = 0

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
    st.subheader("☁️ Backup Cloud")
    df_db = get_db_data() # Legge i dati da Cloud
    if not df_db.empty:
        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_db.to_excel(writer, index=False, sheet_name='Adozioni')
            st.download_button(
                label="💾 SCARICA BACKUP .XLSX",
                data=buffer.getvalue(),
                file_name=f"backup_cloud_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except: st.caption("Errore generazione backup.")
    
    if st.button("🔄 BACKUP MANUALE GOOGLE", use_container_width=True):
        salva_su_gsheets(df_db)
        st.toast("Backup su Google sincronizzato!")

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
                else: st.error("Errore: chiudi il file Excel!")

# --- 2. NUOVA ADOZIONE ---
elif st.session_state.pagina == "Inserimento":
    st.subheader("Nuova Registrazione Adozione (Cloud)")
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
                df_attuale = get_db_data()
                info = catalogo[catalogo.iloc[:, 0] == titolo_scelto]
                nuova_riga = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Plesso": plesso, 
                    "Materia": info.iloc[0,1], 
                    "Titolo": titolo_scelto,
                    "Editore": info.iloc[0,2], 
                    "Agenzia": info.iloc[0,3], 
                    "N° sezioni": str(n_sez), 
                    "Sezione": sez_lett.upper(), 
                    "Note": note
                }])
                salva_su_gsheets(pd.concat([df_attuale, nuova_riga], ignore_index=True))
                st.success("Adozione registrata su Google Sheets!")
                st.session_state.form_id += 1
                st.rerun()
            else: st.error("Seleziona Titolo e Plesso!")

# --- 3. MODIFICA / CANCELLA ADOZIONE ---
elif st.session_state.pagina == "Modifica":
    st.subheader("✏️ Modifica o Cancella Adozioni")
    if os.path.exists(DB_FILE):
        # Carichiamo il DB e forziamo le colonne a stringa per evitare problemi con i filtri
        df_mod = pd.read_csv(DB_FILE).fillna("").astype(str)
        
        # Filtri di ricerca: prendiamo i valori UNICI direttamente dal database CSV
        c_ric1, c_ric2 = st.columns(2)
        with c_ric1:
            lista_plessi_db = sorted([x for x in df_mod["Plesso"].unique() if x != ""])
            p_cerca = st.selectbox("🔍 Filtra per Plesso", [""] + lista_plessi_db)
        with c_ric2:
            lista_titoli_db = sorted([x for x in df_mod["Titolo"].unique() if x != ""])
            t_cerca = st.selectbox("🔍 Filtra per Titolo", [""] + lista_titoli_db)
        
        # MOSTRA I DATI SOLO SE UN FILTRO È ATTIVO
        if p_cerca or t_cerca:
            # Logica di filtraggio
            df_filtrato = df_mod.copy()
            if p_cerca:
                df_filtrato = df_filtrato[df_filtrato["Plesso"] == p_cerca]
            if t_cerca:
                df_filtrato = df_filtrato[df_filtrato["Titolo"] == t_cerca]

            if not df_filtrato.empty:
                for i in df_filtrato.index:
                    with st.container(border=True):
                        st.markdown(f"**Registrazione del {df_mod.at[i, 'Data']}**")
                        
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            # Qui usiamo elenco_plessi e elenco_titoli dalle anagrafiche generali per la modifica
                            nuovo_plesso = st.selectbox(f"Plesso", elenco_plessi, 
                                                       index=elenco_plessi.index(df_mod.at[i, 'Plesso']) if df_mod.at[i, 'Plesso'] in elenco_plessi else 0, 
                                                       key=f"p_{i}")
                            nuovo_titolo = st.selectbox(f"Titolo Libro", elenco_titoli, 
                                                       index=elenco_titoli.index(df_mod.at[i, 'Titolo']) if df_mod.at[i, 'Titolo'] in elenco_titoli else 0, 
                                                       key=f"t_{i}")
                        with col2:
                            try:
                                valore_sez = int(float(df_mod.at[i, 'N° sezioni']))
                            except:
                                valore_sez = 1
                            nuovo_n_sez = st.number_input("N° sezioni", min_value=1, value=valore_sez, key=f"n_{i}")
                            nuova_sez_lett = st.text_input("Lettera Sezione", value=df_mod.at[i, 'Sezione'], key=f"s_{i}")
                        with col3:
                            nuove_note = st.text_area("Note", value=df_mod.at[i, 'Note'], key=f"not_{i}")

                        # Pulsanti Azione
                        btn_up, btn_del = st.columns(2)
                        with btn_up:
                            if st.button("💾 AGGIORNA TUTTO", key=f"sav_{i}", use_container_width=True, type="primary"):
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
                                st.success("Modifica salvata!")
                                st.rerun()
                                
                        with btn_del:
                            if st.button("🗑️ ELIMINA RIGA", key=f"del_{i}", use_container_width=True):
                                df_mod = df_mod.drop(i)
                                df_mod.to_csv(DB_FILE, index=False)
                                st.warning("Adozione eliminata!")
                                st.rerun()
            else:
                st.info("Nessuna adozione corrispondente ai filtri.")
        else:
            # Messaggio mostrato all'apertura quando non c'è ricerca attiva
            st.info("☝️ Seleziona un Plesso o un Titolo per visualizzare e modificare le adozioni.")
    else:
        st.info("Database vuoto (file CSV non trovato).")

# --- 4. REGISTRO COMPLETO ---
elif st.session_state.pagina == "Registro":
    st.subheader("📑 Registro Completo (Cloud)")
    df = get_db_data()
    if not df.empty:
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    else: st.info("Nessuna registrazione presente su Cloud.")

# --- 5. RICERCA ---
elif st.session_state.pagina == "Ricerca":
    st.subheader("🔍 Motore di Ricerca Cloud")
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

    if st.session_state.get("r_attiva"):
        df = get_db_data()
        if f_ple:
            if "NESSUNO" in f_ple: df = df[df["Plesso"] == "___ZERO___"]
            else: df = df[df["Plesso"].isin(f_ple)]
        if f_tit: df = df[df["Titolo"].isin(f_tit)]
        if f_age: df = df[df["Agenzia"].isin(f_age)]
        if f_mat: df = df[df["Materia"].isin(f_mat)]
        if f_edi: df = df[df["Editore"].isin(f_edi)]

        if not df.empty:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
            somma = pd.to_numeric(df["N° sezioni"], errors='coerce').sum()
            st.markdown(f"""<div class="totale-box">🔢 Totale Classi: <b>{int(somma)}</b></div>""", unsafe_allow_html=True)
        else: st.warning("Nessun dato trovato.")


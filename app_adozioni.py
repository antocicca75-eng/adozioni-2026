import streamlit as st
import pandas as pd
import json 
import os
from datetime import datetime
from openpyxl import load_workbook
import io
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF 

# =========================================================
# --- BLOCCO 1: FUNZIONI CONFIGURAZIONE CONSEGNE ---
# =========================================================
def salva_config_consegne(db_dict):
    sh = connetti_google_sheets()
    if sh:
        try:
            try: foglio = sh.worksheet("ConfigConsegne")
            except: foglio = sh.add_worksheet(title="ConfigConsegne", rows="100", cols="20")
            foglio.clear()
            righe = [["Categoria", "Dati_JSON"]]
            for k, v in db_dict.items():
                righe.append([k, json.dumps(v)])
            foglio.update(righe)
        except Exception as e:
            st.sidebar.error(f"Errore salvataggio config: {e}")

def carica_config_consegne():
    sh = connetti_google_sheets()
    db_caricato = {
        "LETTURE CLASSE PRIMA": [], "LETTURE CLASSE QUARTA": [],
        "SUSSIDIARI DISCIPLINE": [], "INGLESE CLASSE PRIMA": [], 
        "INGLESE CLASSE QUARTA": [], "RELIGIONE": []
    }
    if sh:
        try:
            foglio = sh.worksheet("ConfigConsegne")
            dati = foglio.get_all_records()
            for r in dati:
                db_caricato[r["Categoria"]] = json.loads(r["Dati_JSON"])
        except: pass 
    return db_caricato

# =========================================================
# --- BLOCCO 2: FUNZIONI STORICO CLOUD ---
# =========================================================
def salva_storico_cloud(storico_dict):
    sh = connetti_google_sheets()
    if sh:
        try:
            try: foglio = sh.worksheet("StoricoConsegne")
            except: foglio = sh.add_worksheet(title="StoricoConsegne", rows="1000", cols="20")
            foglio.clear()
            righe = [["Plesso", "Dati_JSON"]]
            for plesso, dati in storico_dict.items():
                righe.append([plesso, json.dumps(dati)])
            foglio.update(righe)
        except Exception as e:
            st.sidebar.error(f"Errore salvataggio storico: {e}")

def carica_storico_cloud():
    sh = connetti_google_sheets()
    storico_caricato = {}
    if sh:
        try:
            foglio = sh.worksheet("StoricoConsegne")
            dati = foglio.get_all_records()
            for r in dati:
                storico_caricato[r["Plesso"]] = json.loads(r["Dati_JSON"])
        except: pass
    return storico_caricato

# =========================================================
# --- BLOCCO 3: CONFIGURAZIONE E COSTANTI ---
# =========================================================
DB_FILE = "dati_adozioni.csv"
CONFIG_FILE = "anagrafiche.xlsx"
ID_FOGLIO = "1Ah5_pucc4b0ziNZxqo0NRpHwyUvFrUEggIugMXzlaKk"

st.set_page_config(page_title="Adozioni 2026", layout="wide", page_icon="📚")

# =========================================================
# --- BLOCCO 4: CLASSE PDF ---
# =========================================================
class PDF_CONSEGNA(FPDF):
    def __init__(self, logo_data=None):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.logo_data = logo_data

    def disegna_modulo(self, x_offset, libri, categoria, p, ins, sez, data_m):
        if self.logo_data:
            with open("temp_logo.png", "wb") as f: f.write(self.logo_data.getbuffer())
            self.image("temp_logo.png", x=x_offset + 34, y=8, w=80)
        
        self.set_y(38); self.set_x(x_offset + 10)
        self.set_fill_color(230, 230, 230); self.set_font('Arial', 'B', 9)
        self.cell(129, 8, str(categoria).upper(), border=1, ln=1, align='C', fill=True)
        
        self.set_x(x_offset + 10); self.set_fill_color(245, 245, 245)
        self.cell(75, 7, 'TITOLO DEL TESTO', border=1, align='C', fill=True)
        self.cell(24, 7, 'CLASSE', border=1, align='C', fill=True) 
        self.cell(30, 7, 'EDITORE', border=1, ln=1, align='C', fill=True)
        
        for i, lib in enumerate(libri):
            fill = i % 2 == 1
            self.set_x(x_offset + 10); self.set_fill_color(250, 250, 250) if fill else self.set_fill_color(255, 255, 255)
            self.set_font('Arial', 'B', 7.5)
            self.cell(75, 6, f" {str(lib['t'])[:45]}", border=1, align='L', fill=fill)
            self.set_font('Arial', '', 8)
            self.cell(8, 6, str(lib.get('c1','')), border=1, align='C', fill=fill)
            self.cell(8, 6, str(lib.get('c2','')), border=1, align='C', fill=fill)
            self.cell(8, 6, str(lib.get('c3','')), border=1, align='C', fill=fill)
            self.cell(30, 6, str(lib.get('e',''))[:20], border=1, ln=1, align='C', fill=fill)

        self.set_y(145); self.set_x(x_offset + 10); self.set_fill_color(240, 240, 240); self.set_font('Arial', 'B', 8)
        self.cell(129, 7, ' DETTAGLI DI CONSEGNA', border=1, ln=1, fill=True)
        for label, val in [("PLESSO:", p), ("INSEGNANTE:", ins), ("CLASSE:", sez), ("DATA:", data_m)]:
            self.set_x(x_offset + 10); self.set_font('Arial', 'B', 7.5)
            self.cell(35, 6.2, label, border=1, align='L')
            self.set_font('Arial', '', 7.5)
            self.cell(94, 6.2, str(val).upper(), border=1, ln=1, align='L')

# =========================================================
# --- BLOCCO 5: CONNESSIONE GOOGLE E BACKUP ---
# =========================================================
def connetti_google_sheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        json_info = json.loads(st.secrets["gspread"]["json_data"], strict=False)
        if "private_key" in json_info:
            json_info["private_key"] = json_info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(json_info, scopes=scope)
        client_gs = gspread.authorize(creds)
        sh = client_gs.open_by_key(ID_FOGLIO)
        return sh
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
    return False

# =========================================================
# --- BLOCCO 6: STILE CSS E CACHE DATI ---
# =========================================================
st.markdown("""
    <style>
    [data-testid="stDataEditor"] thead tr th { background-color: #004a99 !important; color: white !important; }
    .stApp { background-color: #ffffff; }
    .totale-box { padding: 20px; background-color: #e8f0fe; border-radius: 10px; border: 1px solid #004a99; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_catalogo_libri():
    sh = connetti_google_sheets()
    if sh:
        try:
            df = pd.DataFrame(sh.worksheet("Catalogo").get_all_records())
            return df.fillna("")
        except: pass
    if os.path.exists(CONFIG_FILE):
        try:
            df = pd.read_excel(CONFIG_FILE, sheet_name="ListaLibri")
            df.columns = [c.strip() for c in df.columns]
            return df.fillna("")
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_lista_plessi():
    sh = connetti_google_sheets()
    if sh:
        try:
            df = pd.DataFrame(sh.worksheet("Plesso").get_all_records())
            return sorted(df.iloc[:, 0].dropna().unique().tolist())
        except: pass
    if os.path.exists(CONFIG_FILE):
        try:
            df = pd.read_excel(CONFIG_FILE, sheet_name="Plesso")
            return sorted(df.iloc[:, 0].dropna().unique().tolist())
        except: return []
    return []

def aggiungi_libro_a_excel(t, m, e, a):
    try:
        wb = load_workbook(CONFIG_FILE)
        ws = wb["ListaLibri"]
        ws.append([t, m, e, a])
        wb.save(CONFIG_FILE)
        st.cache_data.clear() 
        return True
    except: return False

# =========================================================
# --- BLOCCO 7: PREPARAZIONE STATO SESSIONE ---
# =========================================================
catalogo = get_catalogo_libri()
if not catalogo.empty:
    elenco_titoli = sorted([str(x) for x in catalogo.iloc[:, 0].unique() if str(x).strip() != ""])
    elenco_materie = sorted([str(x) for x in catalogo.iloc[:, 1].unique() if str(x).strip() != ""])
    elenco_editori = sorted([str(x) for x in catalogo.iloc[:, 2].unique() if str(x).strip() != ""])
    elenco_agenzie = sorted([str(x) for x in catalogo.iloc[:, 3].unique() if str(x).strip() != ""])
else:
    elenco_titoli = elenco_materie = elenco_editori = elenco_agenzie = []

elenco_plessi = get_lista_plessi()

if "pagina" not in st.session_state:
    st.session_state.pagina = "Inserimento"

if 'db_consegne' not in st.session_state:
    st.session_state.db_consegne = carica_config_consegne()
if 'lista_consegne_attuale' not in st.session_state:
    st.session_state.lista_consegne_attuale = []

def reset_ricerca():
    st.session_state.r_attiva = False
    st.session_state.ft = []
    st.session_state.fa = []
    st.session_state.fp = []
    st.session_state.fm = []
    st.session_state.fe = []
    st.session_state.fsag = "TUTTI"

# =========================================================
# --- BLOCCO 8: SIDEBAR NAVIGAZIONE ---
# =========================================================
with st.sidebar:
    st.title("🧭 MENU")
    if st.button("➕ NUOVA ADOZIONE", use_container_width=True): st.session_state.pagina = "Inserimento"; st.rerun()
    if st.button("✏️ MODIFICA ADOZIONE", use_container_width=True): st.session_state.pagina = "Modifica"; st.rerun()
    if st.button("🆕 AGGIUNGI A CATALOGO", use_container_width=True): st.session_state.pagina = "NuovoLibro"; st.rerun()
    if st.button("📊 REGISTRO COMPLETO", use_container_width=True): st.session_state.pagina = "Registro"; st.rerun()
    if st.button("🔍 FILTRA E RICERCA", use_container_width=True): st.session_state.pagina = "Ricerca"; st.rerun()
    st.markdown("---")
    if st.button("📄 MODULO CONSEGNE", use_container_width=True): st.session_state.pagina = "Consegne"; st.rerun()
    if st.button("📜 REGISTRO STORICO", use_container_width=True): st.session_state.pagina = "Registro Storico"; st.rerun()
    if st.button("📊 TABELLONE STATO", use_container_width=True): st.session_state.pagina = "Tabellone Stato"; st.rerun()
    if st.button("🚀 RICERCA AVANZATA", use_container_width=True): st.session_state.pagina = "Ricerca Avanzata Consegne"; st.rerun()

# =========================================================
# --- BLOCCO 9: LOGICA DI NAVIGAZIONE PRINCIPALE ---
# =========================================================

# 1. PAGINA INSERIMENTO (Adozioni)
if st.session_state.pagina == "Inserimento":
    st.header("➕ Nuova Adozione")
    st.info("Qui inserisci i dati delle adozioni libri.")
    # Inserisci qui il tuo codice originale per l'inserimento se lo hai

# 2. PAGINA CONSEGNE (Modulo Consegne)
elif st.session_state.pagina == "Consegne":
    st.header("📄 Generazione Moduli Consegna")
    
    if "storico_consegne" not in st.session_state: 
        st.session_state.storico_consegne = carica_storico_cloud()
    
    elenco_plessi_con_vuoto = ["- SELEZIONA PLESSO -"] + elenco_plessi
    
    col_p, col_c = st.columns(2)
    p_scelto = col_p.selectbox("Seleziona Plesso:", elenco_plessi_con_vuoto)
    
    basi = ["- SELEZIONA -", "TUTTE LE TIPOLOGIE", "INGLESE CLASSE PRIMA", "INGLESE CLASSE QUARTA"]
    altre = [k for k in st.session_state.db_consegne.keys() if k not in ["INGLESE", "INGLESE CLASSE PRIMA", "INGLESE CLASSE QUARTA"]]
    cat_scelta = col_c.selectbox("Tipologia Libri:", basi + altre)

    if cat_scelta == "TUTTE LE TIPOLOGIE":
        st.info("💡 Hai selezionato l'assegnazione massiva.")
        st.session_state.lista_consegne_attuale = []
        st.session_state.last_cat = "TUTTE"
    elif cat_scelta != "- SELEZIONA -" and st.session_state.get('last_cat') != cat_scelta:
        caricati = list(st.session_state.db_consegne.get(cat_scelta, []))
        for voce in caricati: voce['q'] = 1
        st.session_state.lista_consegne_attuale = caricati
        st.session_state.last_cat = cat_scelta

    if cat_scelta not in ["- SELEZIONA -", "TUTTE LE TIPOLOGIE"]:
        st.markdown("---")
        for i, lib in enumerate(st.session_state.lista_consegne_attuale):
            c_info, c_qta, c_del = st.columns([0.6, 0.3, 0.1])
            c_info.info(f"{lib['t']} | {lib['e']}")
            m1, v1, p1 = c_qta.columns([1,1,1])
            if m1.button("➖", key=f"m_{i}"):
                if lib['q'] > 1: lib['q'] -= 1; st.rerun()
            v1.markdown(f"<p style='text-align:center;'>{lib['q']}</p>", unsafe_allow_html=True)
            if p1.button("➕", key=f"p_{i}"): lib['q'] += 1; st.rerun()
            if c_del.button("❌", key=f"del_{i}"): st.session_state.lista_consegne_attuale.pop(i); st.rerun()

    st.markdown("---")
    d1, d2 = st.columns(2)
    docente = d1.text_input("Insegnante ricevente")
    data_con = d2.text_input("Data di consegna", value=datetime.now().strftime("%d/%m/%Y"))
    
    if st.button("✅ CONFERMA E REGISTRA CONSEGNA", use_container_width=True):
        if p_scelto != "- SELEZIONA PLESSO -":
            if p_scelto not in st.session_state.storico_consegne: st.session_state.storico_consegne[p_scelto] = {}
            if cat_scelta == "TUTTE LE TIPOLOGIE":
                for k, v in st.session_state.db_consegne.items():
                    st.session_state.storico_consegne[p_scelto][k] = [{"t": i['t'], "e": i['e'], "q": 1, "data": data_con} for i in v]
            else:
                st.session_state.storico_consegne[p_scelto][cat_scelta] = [{"t": i['t'], "e": i['e'], "q": i['q'], "data": data_con} for i in st.session_state.lista_consegne_attuale]
            salva_storico_cloud(st.session_state.storico_consegne)
            st.success("Registrazione completata!")

# =========================================================
# --- BLOCCO 10: PAGINA STORICO E RICERCA AVANZATA ---
# INIZIO BLOCCO
# =========================================================
elif st.session_state.pagina == "Storico":
    st.subheader("🔍 Ricerca Avanzata Collane Consegnate")
    
    # Inizializzazione storico se vuoto
    if "storico_consegne" not in st.session_state:
        st.session_state.storico_consegne = carica_storico_cloud()

    # Trasformiamo lo storico (che è un dizionario annidato) in un DataFrame per filtrarlo facilmente
    righe_storico = []
    for plesso, collane in st.session_state.storico_consegne.items():
        for nome_collana, libri in collane.items():
            for lib in libri:
                righe_storico.append({
                    "Plesso": plesso,
                    "Collana": nome_collana,
                    "Titolo": lib.get('t', ''),
                    "Editore": lib.get('e', ''),
                    "Quantità": lib.get('q', 0),
                    "Data": lib.get('data', '-')
                })
    
    df_st = pd.DataFrame(righe_storico)

    # --- PANNELLO FILTRI (Stile Pagina Ricerca Adozioni) ---
    with st.container(border=True):
        f1, f2, f3 = st.columns(3)
        with f1: f_ple_st = st.multiselect("🏫 Filtra Plesso", sorted(df_st["Plesso"].unique()) if not df_st.empty else [], key="f_ple_st")
        with f2: f_col_st = st.multiselect("📘 Filtra Collana", sorted(df_st["Collana"].unique()) if not df_st.empty else [], key="f_col_st")
        with f3: f_edi_st = st.multiselect("🏢 Filtra Editore", sorted(df_st["Editore"].unique()) if not df_st.empty else [], key="f_edi_st")
        
        btn_s1, btn_s2, _ = st.columns([1, 1, 2])
        # Nota: usiamo una variabile di stato per attivare la vista
        if "view_st" not in st.session_state: st.session_state.view_st = False
        
        if btn_s1.button("🔍 APPLICA FILTRI", use_container_width=True, type="primary"):
            st.session_state.view_st = True
        if btn_s2.button("🧹 RESET", use_container_width=True):
            st.session_state.view_st = False
            st.rerun()

    # --- VISUALIZZAZIONE RISULTATI ---
    if st.session_state.view_st:
        df_f = df_st.copy()
        if f_ple_st: df_f = df_f[df_f["Plesso"].isin(f_ple_st)]
        if f_col_st: df_f = df_f[df_f["Collana"].isin(f_col_st)]
        if f_edi_st: df_f = df_f[df_f["Editore"].isin(f_edi_st)]

        if not df_f.empty:
            st.dataframe(df_f, use_container_width=True, hide_index=True)
            tot_copie = df_f["Quantità"].sum()
            st.markdown(f"""<div class="totale-box">📚 Totale Copie Consegnate nei filtri: <b>{int(tot_copie)}</b></div>""", unsafe_allow_html=True)
            
            # Esportazione Excel veloce dei soli filtrati
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_f.to_excel(writer, index=False)
            st.download_button("📥 Scarica Risultati Excel", buffer.getvalue(), "ricerca_consegne.xlsx", use_container_width=True)
        else:
            st.warning("Nessun dato trovato con i filtri selezionati.")

    st.markdown("---")
    # Sezione Gestione (il vecchio expander per plessi per gestire i ritiri)
    with st.expander("⚙️ GESTIONE CONSEGNE (Ritiri e Cancellazioni)"):
        if not st.session_state.storico_consegne:
            st.info("Nessuna consegna presente.")
        else:
            p_gest = st.selectbox("Seleziona plesso da gestire:", ["-"] + sorted(list(st.session_state.storico_consegne.keys())))
            if p_gest != "-":
                per_tipo = st.session_state.storico_consegne[p_gest]
                for tipo, libri in per_tipo.items():
                    st.write(f"**{tipo}**")
                    for i, l in enumerate(libri):
                        col_t, col_q, col_az = st.columns([0.6, 0.2, 0.2])
                        col_t.text(f"{l['t']} ({l['e']})")
                        col_q.text(f"Q.tà: {l['q']}")
                        if col_az.button("❌", key=f"del_{p_gest}_{tipo}_{i}"):
                            st.session_state.storico_consegne[p_gest][tipo].pop(i)
                            if not st.session_state.storico_consegne[p_gest][tipo]: del st.session_state.storico_consegne[p_gest][tipo]
                            if not st.session_state.storico_consegne[p_gest]: del st.session_state.storico_consegne[p_gest]
                            salva_storico_cloud(st.session_state.storico_consegne)
                            st.rerun()

# =========================================================
# --- BLOCCO 11: PAGINA NUOVO LIBRO ---
# =========================================================
elif st.session_state.pagina == "NuovoLibro":
    st.subheader("🆕 Aggiungi nuovo titolo a Catalogo")
    with st.container(border=True):
        nt = st.text_input("Titolo Libro")
        col1, col2, col3 = st.columns(3)
        m_val = col1.text_input("Materia")
        e_val = col2.text_input("Editore")
        a_val = col3.text_input("Agenzia")
        if st.button("✅ SALVA NEL CATALOGO", use_container_width=True, type="primary"):
            if nt and m_val and e_val:
                if aggiungi_libro_a_excel(nt, m_val, e_val, a_val):
                    st.success("Libro aggiunto con successo!"); st.rerun()
            else:
                st.error("Compila Titolo, Materia ed Editore!")

# =========================================================
# --- BLOCCO 12: PAGINA INSERIMENTO ADOZIONE ---
# =========================================================
elif st.session_state.pagina == "Inserimento":
    st.subheader("Nuova Registrazione Adozione")
    if "form_id" not in st.session_state: st.session_state.form_id = 0
    with st.container(border=True):
        titolo_scelto = st.selectbox("📕 SELEZIONA TITOLO", [""] + elenco_titoli, key=f"tit_{st.session_state.form_id}")
        if titolo_scelto:
            info = catalogo[catalogo.iloc[:, 0] == titolo_scelto]
            if not info.empty:
                st.info(f"Materia: {info.iloc[0,1]} | Editore: {info.iloc[0,2]} | Agenzia: {info.iloc[0,3]}")
        
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            plesso = st.selectbox("🏫 Plesso", [""] + elenco_plessi, key=f"ple_{st.session_state.form_id}")
            note = st.text_area("📝 Note", key=f"not_{st.session_state.form_id}", height=70)
        with c2:
            n_sez = st.number_input("🔢 N° sezioni", min_value=1, value=1, key=f"n_{st.session_state.form_id}")
            saggio = st.selectbox("📚 Saggio consegnato", ["-", "NO", "SI"], key=f"sag_{st.session_state.form_id}")
        with c3:
            sez_lett = st.text_input("🔡 Lettera Sezione", key=f"sez_{st.session_state.form_id}")
        
        if st.button("💾 SALVA ADOZIONE", use_container_width=True, type="primary"):
            if titolo_scelto and plesso and saggio != "-":
                info = catalogo[catalogo.iloc[:, 0] == titolo_scelto]
                nuova_riga = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Plesso": plesso, "Materia": info.iloc[0,1], "Titolo": titolo_scelto,
                    "Editore": info.iloc[0,2], "Agenzia": info.iloc[0,3], "N° sezioni": n_sez,
                    "Sezione": sez_lett.upper(), "Saggio Consegna": saggio, "Note": note
                }])
                df_attuale = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
                df_finale = pd.concat([df_attuale, nuova_riga], ignore_index=True)
                df_finale.to_csv(DB_FILE, index=False)
                backup_su_google_sheets(df_finale)
                st.session_state.form_id += 1
                st.success("✅ Registrazione avvenuta con successo!")
                st.rerun()
            elif saggio == "-": st.error("⚠️ Devi specificare SI/NO!")
            else: st.error("⚠️ Seleziona Titolo e Plesso!")

# =========================================================
# --- BLOCCO 13: PAGINA REGISTRO E RICERCA ADOZIONI ---
# =========================================================
elif st.session_state.pagina == "Registro":
    st.subheader("📑 Registro Completo Adozioni")
    if os.path.exists(DB_FILE):
        df_reg = pd.read_csv(DB_FILE)
        st.dataframe(df_reg.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("Nessuna adozione registrata nel database CSV.")

elif st.session_state.pagina == "Ricerca":
    st.subheader("🔍 Motore di Ricerca Adozioni")
    if "r_attiva" not in st.session_state: st.session_state.r_attiva = False
    
    with st.container(border=True):
        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1: f_tit = st.multiselect("📕 Titolo Libro", elenco_titoli, key="ft")
        with r1c2: f_age = st.multiselect("🤝 Agenzia", elenco_agenzie, key="fa")
        with r1c3: f_sag = st.selectbox("📚 Saggio consegnato", ["TUTTI", "SI", "NO"], key="fsag")
        
        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1: f_ple = st.multiselect("🏫 Plesso", elenco_plessi, key="fp")
        with r2c2: f_mat = st.multiselect("📖 Materia", elenco_materie, key="fm")
        with r2c3: f_edi = st.multiselect("🏢 Editore", elenco_editori, key="fe")
        
        btn1, btn2, _ = st.columns([1, 1, 2])
        if btn1.button("🔍 AVVIA RICERCA", use_container_width=True, type="primary"): 
            st.session_state.r_attiva = True
        if btn2.button("🧹 PULISCI", use_container_width=True): 
            reset_ricerca()
            st.rerun()
            
    if st.session_state.r_attiva and os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE).fillna("").astype(str)
        if f_ple: df = df[df["Plesso"].isin(f_ple)]
        if f_tit: df = df[df["Titolo"].isin(f_tit)]
        if f_age: df = df[df["Agenzia"].isin(f_age)]
        if f_mat: df = df[df["Materia"].isin(f_mat)]
        if f_edi: df = df[df["Editore"].isin(f_edi)]
        if f_sag != "TUTTI": df = df[df["Saggio Consegna"] == f_sag]
        
        if not df.empty:
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
            somma = pd.to_numeric(df["N° sezioni"], errors='coerce').sum()
            st.markdown(f"""<div class="totale-box">🔢 Totale Classi: <b>{int(somma)}</b></div>""", unsafe_allow_html=True)
        else:
            st.warning("Nessun risultato trovato.")

# =========================================================
# --- BLOCCO 14: TABELLONE STATO ---
# =========================================================
elif st.session_state.pagina == "Tabellone Stato":
    st.header("📊 Tabellone Avanzamento Plessi")
    storico = st.session_state.get("storico_consegne", {})
    plessi_list = get_lista_plessi()
    
    if plessi_list:
        cols = st.columns(4)
        for idx, p in enumerate(plessi_list):
            ha_consegne = p in storico and storico[p]
            color = "#1E3A8A" if ha_consegne else "#f0f2f6"
            t_color = "white" if ha_consegne else "black"
            with cols[idx % 4]:
                st.markdown(f"""
                <div style="background:{color}; padding:20px; border-radius:10px; text-align:center; margin-bottom:10px; border:1px solid #ddd;">
                    <b style="color:{t_color}; font-size:16px;">{p}</b><br>
                    <small style="color:{t_color} text-transform:uppercase;">{'CONSEGNATO' if ha_consegne else 'DA CONSEGNARE'}</small>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.error("Configurazione plessi non trovata.")


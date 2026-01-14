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
    if

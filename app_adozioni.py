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
# --- BLOCCO 9: PAGINA CONSEGNE ---
# =========================================================
if st.session_state.pagina == "Consegne":
    st.header("📄 Generazione Moduli Consegna")
    
    if "storico_consegne" not in st.session_state: 
        st.session_state.storico_consegne = carica_storico_cloud()
    
    elenco_plessi_con_vuoto = ["- SELEZIONA PLESSO -"] + elenco_plessi
    
    def reset_consegne_totale():
        st.session_state.lista_consegne_attuale = []
        st.session_state.last_cat = None
        st.rerun()

    ctr = st.session_state.get('reset_ctr', 0)
    actr = st.session_state.get('add_ctr', 0)

    col_p, col_c = st.columns(2)
    p_scelto = col_p.selectbox("Seleziona Plesso:", elenco_plessi_con_vuoto, key=f"p_sel_{ctr}")
    
    basi = ["- SELEZIONA -", "TUTTE LE TIPOLOGIE", "INGLESE CLASSE PRIMA", "INGLESE CLASSE QUARTA"]
    altre = [k for k in st.session_state.db_consegne.keys() if k not in ["INGLESE", "INGLESE CLASSE PRIMA", "INGLESE CLASSE QUARTA"]]
    cat_scelta = col_c.selectbox("Tipologia Libri:", basi + altre, key=f"c_sel_{ctr}")

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
            if 'q' not in lib: lib['q'] = 1
            c_info, c_qta, c_del = st.columns([0.6, 0.3, 0.1])
            c_info.info(f"{lib['t']} | {lib['e']}")
            m1, v1, p1 = c_qta.columns([1,1,1])
            if m1.button("➖", key=f"m_{cat_scelta}_{i}"):
                if lib['q'] > 1: lib['q'] -= 1; st.rerun()
            v1.markdown(f"<p style='text-align:center;'>{lib['q']}</p>", unsafe_allow_html=True)
            if p1.button("➕", key=f"p_{cat_scelta}_{i}"): lib['q'] += 1; st.rerun()
            if c_del.button("❌", key=f"del_{cat_scelta}_{i}"): st.session_state.lista_consegne_attuale.pop(i); st.rerun()

    st.markdown("---")
    d1, d2 = st.columns(2)
    docente = d1.text_input("Insegnante ricevente", key=f"doc_{ctr}")
    data_con = d2.text_input("Data di consegna", value=datetime.now().strftime("%d/%m/%Y"), key=f"dat_{ctr}")
    classe_man = d1.text_input("Classe specifica", key=f"cla_{ctr}")

    col_print, col_conf = st.columns(2)
    if col_conf.button("✅ CONFERMA CONSEGNA", use_container_width=True):
        if p_scelto != "- SELEZIONA PLESSO -":
            if p_scelto not in st.session_state.storico_consegne: st.session_state.storico_consegne[p_scelto] = {}
            if cat_scelta == "TUTTE LE TIPOLOGIE":
                for k, v in st.session_state.db_consegne.items():
                    st.session_state.storico_consegne[p_scelto][k] = [{"t": i['t'], "e": i['e'], "q": 1, "data": data_con} for i in v]
            else:
                st.session_state.storico_consegne[p_scelto][cat_scelta] = [{"t": i['t'], "e": i['e'], "q": i['q'], "data": data_con} for i in st.session_state.lista_consegne_attuale]
            salva_storico_cloud(st.session_state.storico_consegne)
            st.success("Registrato!")

# =========================================================
# --- BLOCCO 14: REGISTRO STORICO (VERSIONE TABELLARE) ---
# =========================================================
elif st.session_state.pagina == "Registro Storico":
    st.header("📜 Registro Cronologico Consegne")
    storico = st.session_state.get("storico_consegne", {})
    with st.container(border=True):
        st.subheader("🔍 Ricerca nel Registro")
        f_col1, f_col2 = st.columns(2)
        with f_col1: cerca_plesso = st.text_input("🏢 Nome Plesso:", placeholder="Es: Manzoni...").upper()
        with f_col2:
            elenco_c = set()
            for p in storico:
                for c in storico[p]: elenco_c.add(c)
            opzioni_c = ["TUTTE"] + sorted(list(elenco_c))
            cerca_collana = st.selectbox("📘 Tipo Collana:", opzioni_c)
    if not storico: st.info("Registro vuoto.")
    else:
        righe = []
        for plesso, collane in storico.items():
            if cerca_plesso and cerca_plesso not in str(plesso).upper(): continue
            for nome_c, lista_libri in collane.items():
                if cerca_collana != "TUTTE" and cerca_collana != nome_c: continue
                for lib in lista_libri:
                    righe.append({"DATA": lib.get('data','-'), "PLESSO": plesso, "COLLANA": nome_c, "TITOLO": lib['t'], "Q.TÀ": lib['q']})
        if righe: st.table(pd.DataFrame(righe).sort_values(by="DATA", ascending=False))
        else: st.warning("Nessun risultato.")

# =========================================================
# --- BLOCCO 15: TABELLONE STATO ---
# =========================================================
elif st.session_state.pagina == "Tabellone Stato":
    st.header("📊 Tabellone Avanzamento Plessi")
    
    mappa_sigle = {
        "LETTURE CLASSE PRIMA": "L1", 
        "LETTURE CLASSE QUARTA": "L4", 
        "SUSSIDIARI DISCIPLINE": "S4", 
        "RELIGIONE": "R1/4", 
        "INGLESE CLASSE PRIMA": "E1", 
        "INGLESE CLASSE QUARTA": "E4"
    }
    
    storico = st.session_state.get("storico_consegne", {})
    mostra = get_lista_plessi()
    
    if not mostra:
        st.warning("Nessun plesso trovato in anagrafica.")
    else:
        n_col = 4
        for i in range(0, len(mostra), n_col):
            cols = st.columns(n_col)
            for j, plesso in enumerate(mostra[i:i+n_col]):
                cat_attive = storico.get(plesso, {}).keys()
                sigle = [mappa_sigle.get(c, c[:2]) for c in cat_attive]
                
                # Colore: Arancio se ha consegne, Grigio se vuoto
                bg_color = "#FF8C00" if sigle else "#f0f2f6"
                txt_color = "white" if sigle else "#333"
                
                with cols[j]:
                    html_card = f"""
                    <div style="background:{bg_color}; color:{txt_color}; border-radius:10px; padding:15px; text-align:center; min-height:100px; border:1px solid #ddd; margin-bottom:10px;">
                        <div style="font-weight:bold; font-size:16px;">{plesso}</div>
                        <div style="margin-top:10px;">
                            {' '.join([f'<span style="background:white; color:black; padding:2px 5px; border-radius:4px; font-size:11px; font-weight:bold; border:1px solid #000; margin:2px;">{s}</span>' for s in sigle])}
                        </div>
                    </div>
                    """
                    st.markdown(html_card, unsafe_allow_html=True)

    if st.button("⬅️ Torna Indietro", key="back_tab"):
        st.session_state.pagina = "Consegne"
        st.rerun()

# =========================================================
# --- BLOCCO 16: RICERCA AVANZATA CONSEGNE ---
# =========================================================
elif st.session_state.pagina == "Ricerca Avanzata Consegne":
    st.header("🚀 Ricerca Avanzata Consegne")
    
    storico = st.session_state.get("storico_consegne", {})
    
    # Prepariamo i dati
    tutte_righe = []
    for p, collane in storico.items():
        for nome_c, libri in collane.items():
            for lib in libri:
                tutte_righe.append({
                    "DATA": lib.get('data', '-'),
                    "PLESSO": p,
                    "COLLANA": nome_c,
                    "TITOLO": lib.get('t', ''),
                    "EDITORE": lib.get('e', ''),
                    "Q.TÀ": lib.get('q', 0)
                })
    
    df_storico = pd.DataFrame(tutte_righe)

    with st.container(border=True):
        st.subheader("🔍 Parametri di Ricerca")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            f_plesso = st.multiselect("🏫 Plesso", options=sorted(df_storico["PLESSO"].unique()) if not df_storico.empty else [])
        with c2:
            f_collana = st.multiselect("📘 Collana", options=sorted(df_storico["COLLANA"].unique()) if not df_storico.empty else [])
        with c3:
            f_editore = st.multiselect("🏢 Editore", options=sorted(df_storico["EDITORE"].unique()) if not df_storico.empty else [])

        b1, b2, _ = st.columns([1,1,2])
        avvia = b1.button("🔍 AVVIA RICERCA", type="primary", use_container_width=True)
        if b2.button("🧹 RESET", use_container_width=True):
            st.rerun()

    if avvia:
        if not df_storico.empty:
            df_f = df_storico.copy()
            if f_plesso: df_f = df_f[df_f["PLESSO"].isin(f_plesso)]
            if f_collana: df_f = df_f[df_f["COLLANA"].isin(f_collana)]
            if f_editore: df_f = df_f[df_f["EDITORE"].isin(f_editore)]
            st.dataframe(df_f, use_container_width=True, hide_index=True)
        else:
            st.info("Nessun dato nel registro.")

    if st.button("⬅️ Torna al Menu"):
        st.session_state.pagina = "Consegne"
        st.rerun()

# =========================================================
# --- BLOCCO 16: RICERCA AVANZATA CONSEGNE ---
# =========================================================
elif st.session_state.pagina == "Ricerca Avanzata Consegne":
    st.header("🚀 Ricerca Avanzata Consegne")
    
    storico = st.session_state.get("storico_consegne", {})
    
    # Prepariamo i dati in formato tabella per la ricerca
    tutte_righe = []
    for p, collane in storico.items():
        for nome_c, libri in collane.items():
            for lib in libri:
                tutte_righe.append({
                    "DATA": lib.get('data', '-'),
                    "PLESSO": p,
                    "COLLANA": nome_c,
                    "TITOLO": lib.get('t', ''),
                    "EDITORE": lib.get('e', ''),
                    "Q.TÀ": lib.get('q', 0)
                })
    df_storico = pd.DataFrame(tutte_righe)

    # 1. Pannello Filtri stile Adozioni
    with st.container(border=True):
        st.subheader("🔍 Parametri di Ricerca")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            f_plesso = st.multiselect("🏫 Plesso", options=sorted(df_storico["PLESSO"].unique()) if not df_storico.empty else [])
        with col2:
            f_collana = st.multiselect("📘 Collana", options=sorted(df_storico["COLLANA"].unique()) if not df_storico.empty else [])
        with col3:
            f_editore = st.multiselect("🏢 Editore", options=sorted(df_storico["EDITORE"].unique()) if not df_storico.empty else [])

        btn_c1, btn_c2, _ = st.columns([1,1,2])
        avvia = btn_c1.button("🔍 AVVIA RICERCA", type="primary", use_container_width=True)
        if btn_c2.button("🧹 RESET", use_container_width=True):
            st.rerun()

    # 2. Visualizzazione Risultati
    if avvia:
        if not df_storico.empty:
            df_filtro = df_storico.copy()
            if f_plesso: df_filtro = df_filtro[df_filtro["PLESSO"].isin(f_plesso)]
            if f_collana: df_filtro = df_filtro[df_filtro["COLLANA"].isin(f_collana)]
            if f_editore: df_filtro = df_filtro[df_filtro["EDITORE"].isin(f_editore)]
            
            st.subheader("📊 Risultati")
            st.dataframe(df_filtro, use_container_width=True, hide_index=True)
            st.info(f"Trovate {len(df_filtro)} righe corrispondenti.")
        else:
            st.warning("Il registro storico è vuoto.")

    st.markdown("---")
    if st.button("⬅️ Torna Indietro"):
        st.session_state.pagina = "Consegne"; st.rerun()


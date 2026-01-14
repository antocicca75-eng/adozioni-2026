
import streamlit as st
import pandas as pd
import json # Assicurati che ci sia anche questo import in alto
import os
from datetime import datetime
from openpyxl import load_workbook
import io
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF 

# =========================================================
# --- BLOCCO 1: FUNZIONI CONFIGURAZIONE CONSEGNE ---
# INIZIO BLOCCO
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
# FINE BLOCCO 1
# =========================================================


# =========================================================
# --- BLOCCO 2: FUNZIONI STORICO CLOUD ---
# INIZIO BLOCCO
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
# FINE BLOCCO 2
# =========================================================


# =========================================================
# --- BLOCCO 3: CONFIGURAZIONE E COSTANTI ---
# INIZIO BLOCCO
# =========================================================
DB_FILE = "dati_adozioni.csv"
CONFIG_FILE = "anagrafiche.xlsx"
ID_FOGLIO = "1Ah5_pucc4b0ziNZxqo0NRpHwyUvFrUEggIugMXzlaKk"

st.set_page_config(page_title="Adozioni 2026", layout="wide", page_icon="📚")
# =========================================================
# FINE BLOCCO 3
# =========================================================


# =========================================================
# --- BLOCCO 4: CLASSE PDF ---
# INIZIO BLOCCO
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
# FINE BLOCCO 4
# =========================================================


# =========================================================
# --- BLOCCO 5: CONNESSIONE GOOGLE E BACKUP ---
# INIZIO BLOCCO
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
# FINE BLOCCO 5
# =========================================================


# =========================================================
# --- BLOCCO 6: STILE CSS E CACHE DATI ---
# INIZIO BLOCCO
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
# FINE BLOCCO 6
# =========================================================


# =========================================================
# --- BLOCCO 7: PREPARAZIONE STATO SESSIONE ---
# INIZIO BLOCCO
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
# FINE BLOCCO 7
# =========================================================


# =========================================================
# --- BLOCCO 8: SIDEBAR NAVIGAZIONE ---
# INIZIO BLOCCO
# =========================================================
with st.sidebar:
    st.title("🧭 MENU")
    if st.button("➕ NUOVA ADOZIONE", use_container_width=True): st.session_state.pagina = "Inserimento"; st.rerun()
    if st.button("✏️ MODIFICA ADOZIONE", use_container_width=True): st.session_state.pagina = "Modifica"; st.rerun()
    if st.button("🆕 AGGIUNGI A CATALOGO", use_container_width=True): st.session_state.pagina = "NuovoLibro"; st.rerun()
    if st.button("📊 REGISTRO COMPLETO", use_container_width=True): st.session_state.pagina = "Registro"; st.rerun()
    if st.button("🔍 FILTRA E RICERCA", use_container_width=True): st.session_state.pagina = "Ricerca"; st.rerun()
    if st.button("📄 MODULO CONSEGNE", use_container_width=True): st.session_state.pagina = "Consegne"; st.rerun()
    if st.button("📚 COLLANE CONSEGNATE", use_container_width=True): st.session_state.pagina = "Storico"; st.rerun()
    
    st.markdown("---")
    
    # Pulsante per il Tabellone a tutto schermo
    if st.button("📊 APRI TABELLONE STATO", use_container_width=True):
        st.session_state.pagina = "Tabellone Stato"
        st.rerun()

# =========================================================
# FINE BLOCCO 8
# =========================================================


# =========================================================
# --- BLOCCO 9: PAGINA CONSEGNE (GESTIONE MASSIVA E COPIE) ---
# INIZIO BLOCCO
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
    
    # Aggiunta opzione "TUTTE LE TIPOLOGIE"
    basi = ["- SELEZIONA -", "TUTTE LE TIPOLOGIE", "INGLESE CLASSE PRIMA", "INGLESE CLASSE QUARTA"]
    altre = [k for k in st.session_state.db_consegne.keys() if k not in ["INGLESE", "INGLESE CLASSE PRIMA", "INGLESE CLASSE QUARTA"]]
    cat_scelta = col_c.selectbox("Tipologia Libri:", basi + altre, key=f"c_sel_{ctr}")

    # --- LOGICA CARICAMENTO ---
    if cat_scelta == "TUTTE LE TIPOLOGIE":
        st.info("💡 Hai selezionato l'assegnazione massiva. Clicca su 'CONFERMA CONSEGNA' in basso per registrare tutti i libri del database per questo plesso.")
        st.session_state.lista_consegne_attuale = [] # Svuota la lista singola per evitare confusioni
        st.session_state.last_cat = "TUTTE"

    elif cat_scelta != "- SELEZIONA -" and st.session_state.get('last_cat') != cat_scelta:
        caricati = list(st.session_state.db_consegne.get(cat_scelta, []))
        # Forza ogni libro caricato ad avere quantità 1 di default
        for voce in caricati:
            voce['q'] = 1
        st.session_state.lista_consegne_attuale = caricati
        st.session_state.last_cat = cat_scelta

    # --- VISUALIZZAZIONE LISTA (Solo se non è massiva) ---
    if cat_scelta not in ["- SELEZIONA -", "TUTTE LE TIPOLOGIE"]:
        st.markdown("---")
        for i, lib in enumerate(st.session_state.lista_consegne_attuale):
            if 'q' not in lib: lib['q'] = 1
            
            c_info, c_qta, c_del = st.columns([0.6, 0.3, 0.1])
            c_info.info(f"{lib['t']} | {lib['e']} | Classi: {lib['c1']} {lib['c2']} {lib['c3']}")
            
            m1, v1, p1 = c_qta.columns([1,1,1])
            if m1.button("➖", key=f"m_{cat_scelta}_{i}"):
                if lib['q'] > 1:
                    lib['q'] -= 1
                    st.rerun()
            v1.markdown(f"<p style='text-align:center; font-weight:bold; font-size:18px;'>{lib['q']}</p>", unsafe_allow_html=True)
            if p1.button("➕", key=f"p_{cat_scelta}_{i}"):
                lib['q'] += 1
                st.rerun()

            if c_del.button("❌", key=f"del_{cat_scelta}_{i}"):
                st.session_state.lista_consegne_attuale.pop(i)
                st.rerun()

        col_btns = st.columns(2)
        if col_btns[0].button("💾 REGISTRA LISTA BASE", use_container_width=True):
            lista_da_salvare = []
            for item in st.session_state.lista_consegne_attuale:
                nuovo_item = item.copy()
                nuovo_item['q'] = 1 
                lista_da_salvare.append(nuovo_item)
            st.session_state.db_consegne[cat_scelta] = lista_da_salvare
            salva_config_consegne(st.session_state.db_consegne)
            st.success("Configurazione salvata!")
        
        if col_btns[1].button("🗑️ SVUOTA SCHERMATA", use_container_width=True):
            st.session_state.reset_ctr = st.session_state.get('reset_ctr', 0) + 1
            reset_consegne_totale()

        # --- CERCA E AGGIUNGI LIBRO ---
        with st.expander("➕ Cerca e Aggiungi Libro"):
            df_cat = get_catalogo_libri()
            if not df_cat.empty:
                scelta_libro = st.selectbox("Seleziona libro:", ["- CERCA TITOLO -"] + sorted(df_cat.iloc[:, 0].astype(str).unique().tolist()), key=f"sk_{actr}")
                if scelta_libro != "- CERCA TITOLO -":
                    dati_libro = df_cat[df_cat.iloc[:, 0] == scelta_libro].iloc[0]
                    c_sez, c1, c2, c3, _ = st.columns([1.2, 1, 1, 1, 4])
                    sez_in = c_sez.text_input("Sezione", key=f"sez_{actr}")
                    c1in = c1.text_input("Classe", max_chars=2, key=f"in1_{actr}")
                    c2in = c2.text_input("Classe ", max_chars=2, key=f"in2_{actr}")
                    c3in = c3.text_input("Classe  ", max_chars=2, key=f"in3_{actr}")
                    
                    if st.button("Conferma Aggiunta", key=f"btn_add_{actr}", use_container_width=True):
                        st.session_state.lista_consegne_attuale.append({
                            "t": str(dati_libro.iloc[0]).upper(), "e": str(dati_libro.iloc[2]).upper(), 
                            "q": 1, "c1": c1in, "c2": c2in, "c3": c3in, "sez": sez_in
                        })
                        st.session_state.add_ctr = st.session_state.get('add_ctr', 0) + 1
                        st.rerun()

    # --- DATI RICEVENTE E GENERAZIONE PDF ---
    st.markdown("---")
    d1, d2 = st.columns(2)
    docente = d1.text_input("Insegnante ricevente", key=f"doc_{ctr}")
    data_con = d2.text_input("Data di consegna", key=f"dat_{ctr}")
    classe_man = d1.text_input("Classe specifica", key=f"cla_{ctr}")

    col_print, col_conf = st.columns(2)
    
    # Bottone PDF (disabilitato se massiva perché troppo grande)
    if cat_scelta != "TUTTE LE TIPOLOGIE":
        if col_print.button("🖨️ GENERA PDF", use_container_width=True):
            if st.session_state.lista_consegne_attuale:
                pdf = PDF_CONSEGNA(st.session_state.get('logo_scuola'))
                pdf.add_page()
                pdf.disegna_modulo(0, st.session_state.lista_consegne_attuale, cat_scelta, p_scelto, docente, classe_man, data_con)
                pdf.dashed_line(148.5, 0, 148.5, 210, 0.5)
                pdf.disegna_modulo(148.5, st.session_state.lista_consegne_attuale, cat_scelta, p_scelto, docente, classe_man, data_con)
                st.download_button("📥 SCARICA PDF", bytes(pdf.output()), "consegna.pdf", "application/pdf")

    # --- CONFERMA E REGISTRAZIONE (Gestisce anche il MASSIVO) ---
    if col_conf.button("✅ CONFERMA CONSEGNA", use_container_width=True):
        if p_scelto != "- SELEZIONA PLESSO -":
            if p_scelto not in st.session_state.storico_consegne: 
                st.session_state.storico_consegne[p_scelto] = {}
            
            if cat_scelta == "TUTTE LE TIPOLOGIE":
                # Ciclo su tutto il database per assegnare ogni categoria al plesso
                for k, v in st.session_state.db_consegne.items():
                    lista_clean = []
                    for item in v:
                        nuovo = item.copy()
                        nuovo['q'] = 1 # Forza sempre a 1 per il registro storico
                        lista_clean.append(nuovo)
                    st.session_state.storico_consegne[p_scelto][k] = lista_clean
                st.success(f"REGISTRAZIONE MASSIVA COMPLETATA per {p_scelto}!")
            else:
                # Registrazione singola tipologia
                st.session_state.storico_consegne[p_scelto][cat_scelta] = list(st.session_state.lista_consegne_attuale)
                st.success(f"Consegna registrata per {cat_scelta}!")
            
            salva_storico_cloud(st.session_state.storico_consegne)
# =========================================================
# --- BLOCCO 10: PAGINA STORICO (VERSIONE CORRETTA) ---
# INIZIO BLOCCO
# =========================================================
elif st.session_state.pagina == "Storico":
    st.header("📚 Registro Collane Consegnate")
    
    if "storico_ritiri" not in st.session_state:
        st.session_state.storico_ritiri = {}

    if not st.session_state.get("storico_consegne"):
        st.info("Nessuna consegna registrata.")
    else:
        elenco_plessi_storico = sorted(list(st.session_state.storico_consegne.keys()))
        opzioni_ricerca = ["- MOSTRA TUTTI -"] + elenco_plessi_storico
        scuola_selezionata = st.selectbox("🔍 Seleziona Plesso:", opzioni_ricerca)
        
        st.markdown("---")
        plessi_da_mostrare = [scuola_selezionata] if scuola_selezionata != "- MOSTRA TUTTI -" else elenco_plessi_storico

        for plesso in plessi_da_mostrare:
            with st.expander(f"🏫 {plesso}", expanded=False):
                
                if st.button(f"🔄 RITIRA TUTTO IL PLESSO: {plesso}", key=f"bulk_plesso_{plesso}"):
                    if plesso not in st.session_state.storico_ritiri: st.session_state.storico_ritiri[plesso] = {}
                    st.session_state.storico_ritiri[plesso].update(st.session_state.storico_consegne[plesso])
                    del st.session_state.storico_consegne[plesso]
                    salva_storico_cloud(st.session_state.storico_consegne)
                    st.success(f"Intero plesso {plesso} spostato nei Ritiri!"); st.rerun()

                per_tipo = st.session_state.storico_consegne[plesso]
                
                for tipo in sorted(list(per_tipo.keys())):
                    c_t, c_btn = st.columns([0.7, 0.3])
                    c_t.markdown(f"#### 📘 {tipo}")
                    
                    if c_btn.button(f"🔄 Ritira Tutto {tipo}", key=f"bulk_tipo_{plesso}_{tipo}"):
                        if plesso not in st.session_state.storico_ritiri: st.session_state.storico_ritiri[plesso] = {}
                        st.session_state.storico_ritiri[plesso][tipo] = per_tipo[tipo]
                        del st.session_state.storico_consegne[plesso][tipo]
                        if not st.session_state.storico_consegne[plesso]: del st.session_state.storico_consegne[plesso]
                        salva_storico_cloud(st.session_state.storico_consegne)
                        st.rerun()

                    with st.expander(f"Dettaglio {tipo}", expanded=True):
                        # Usiamo list() per evitare errori di iterazione se rimuoviamo elementi
                        for i, lib in enumerate(list(per_tipo[tipo])):
                            # --- PROTEZIONE VALORI ---
                            try:
                                qta_carico = int(lib.get('q', 1))
                            except:
                                qta_carico = 1
                            
                            # Se la quantità a sistema è 0, la consideriamo 1 per non bloccare il widget
                            qta_min_safe = max(1, qta_carico)
                            
                            col_titolo, col_qta, col_ritiro, col_del = st.columns([0.45, 0.20, 0.25, 0.10])
                            
                            col_titolo.markdown(f"<b style='font-size:15px; color:#1E3A8A;'>{lib['t']}</b><br><small>{lib['e']}</small>", unsafe_allow_html=True)
                            col_qta.markdown(f"<p style='text-align:center; font-size:14px;'>In carico:<br><b>{qta_carico}</b></p>", unsafe_allow_html=True)

                            with col_ritiro:
                                # Protezione: min_value=1, value non può essere minore di min_value
                                q_rit = st.number_input("Ritiro", min_value=1, max_value=qta_min_safe, value=qta_min_safe, key=f"qrit_{plesso}_{tipo}_{i}")
                                
                                if st.button("🔄", key=f"btn_rit_{plesso}_{tipo}_{i}"):
                                    if plesso not in st.session_state.storico_ritiri: st.session_state.storico_ritiri[plesso] = {}
                                    if tipo not in st.session_state.storico_ritiri[plesso]: st.session_state.storico_ritiri[plesso][tipo] = []
                                    
                                    # Registro il ritiro
                                    ritiro_item = lib.copy()
                                    ritiro_item['q'] = q_rit
                                    st.session_state.storico_ritiri[plesso][tipo].append(ritiro_item)
                                    
                                    # Sottraggo dalla consegna
                                    lib['q'] = qta_carico - q_rit
                                    
                                    # Se non restano copie, elimino la riga dalle consegne
                                    if lib['q'] <= 0:
                                        per_tipo[tipo].pop(i)
                                    
                                    # Pulizia strutture vuote
                                    if not st.session_state.storico_consegne[plesso][tipo]: del st.session_state.storico_consegne[plesso][tipo]
                                    if not st.session_state.storico_consegne[plesso]: del st.session_state.storico_consegne[plesso]
                                    
                                    salva_storico_cloud(st.session_state.storico_consegne)
                                    st.rerun()
                            
                            if col_del.button("❌", key=f"del_h_{plesso}_{tipo}_{i}"):
                                per_tipo[tipo].pop(i)
                                if not per_tipo[tipo]: del per_tipo[tipo]
                                if not st.session_state.storico_consegne[plesso]: del st.session_state.storico_consegne[plesso]
                                salva_storico_cloud(st.session_state.storico_consegne); st.rerun()

    st.markdown("---")
    if st.button("⬅️ Torna a Modulo Consegne"):
        st.session_state.pagina = "Consegne"; st.rerun()
# =========================================================
# =========================================================
# --- BLOCCO 11: PAGINA NUOVO LIBRO ---
# INIZIO BLOCCO
# =========================================================
elif st.session_state.pagina == "NuovoLibro":
    st.subheader("🆕 Aggiungi nuovo titolo")
    with st.container(border=True):
        nt = st.text_input("Titolo Libro")
        col1, col2, col3 = st.columns(3)
        m_val = col1.text_input("Materia")
        e_val = col2.text_input("Editore")
        a_val = col3.text_input("Agenzia")
        if st.button("✅ SALVA", use_container_width=True, type="primary"):
            if nt and m_val and e_val:
                if aggiungi_libro_a_excel(nt, m_val, e_val, a_val):
                    st.success("Libro aggiunto!"); st.rerun()
# =========================================================
# FINE BLOCCO 11
# =========================================================


# =========================================================
# --- BLOCCO 12: PAGINA INSERIMENTO ADOZIONE ---
# INIZIO BLOCCO
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
# FINE BLOCCO 12
# =========================================================


# =========================================================
# --- BLOCCO 13: PAGINA REGISTRO E RICERCA ---
# INIZIO BLOCCO
# =========================================================
elif st.session_state.pagina == "Registro":
    st.subheader("📑 Registro Completo")
    if os.path.exists(DB_FILE):
        st.dataframe(pd.read_csv(DB_FILE), use_container_width=True)

elif st.session_state.pagina == "Ricerca":
    st.subheader("🔍 Motore di Ricerca Adozioni")
    if "r_attiva" not in st.session_state: st.session_state.r_attiva = False
    
    with st.container(border=True):
        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1: f_tit = st.multiselect("📕 Titolo Libro", elenco_titoli, key="ft")
        with r1c2: f_age = st.multiselect("🤝 Agenzia", elenco_agenzie, key="fa")
        with r1c3: f_sag = st.selectbox("📚 Saggio consegnato", ["TUTTI", "SI", "NO"], key="fsag")
        
        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1: f_ple = st.multiselect("🏫 Plesso", ["NESSUNO"] + elenco_plessi, key="fp")
        with r2c2: f_mat = st.multiselect("📖 Materia", elenco_materie, key="fm")
        with r2c3: f_edi = st.multiselect("🏢 Editore", elenco_editori, key="fe")
        
        btn1, btn2, _ = st.columns([1, 1, 2])
        with btn1:
            if st.button("🔍 AVVIA RICERCA", use_container_width=True, type="primary"): 
                st.session_state.r_attiva = True
        with btn2:
            if st.button("🧹 PULISCI", use_container_width=True, on_click=reset_ricerca): 
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
            st.warning("Nessun dato trovato con i filtri selezionati.")
# =========================================================
# FINE BLOCCO 13
# =========================================================


# =========================================================
# --- BLOCCO 14: PAGINA MODIFICA ---
# INIZIO BLOCCO
# =========================================================
elif st.session_state.pagina == "Modifica":
    st.subheader("✏️ Modifica o Cancella Adozioni")
    if os.path.exists(DB_FILE):
        df_mod = pd.read_csv(DB_FILE).fillna("").astype(str)
        c_ric1, c_ric2 = st.columns(2)
        with c_ric1:
            lista_plessi_db = sorted([x for x in df_mod["Plesso"].unique() if x != ""])
            p_cerca = st.selectbox("🔍 Filtra per Plesso", [""] + lista_plessi_db)
        with c_ric2:
            lista_titoli_db = sorted([x for x in df_mod["Titolo"].unique() if x != ""])
            t_cerca = st.selectbox("🔍 Filtra per Titolo", [""] + lista_titoli_db)
        if p_cerca or t_cerca:
            df_filtrato = df_mod.copy()
            if p_cerca: df_filtrato = df_filtrato[df_filtrato["Plesso"] == p_cerca]
            if t_cerca: df_filtrato = df_filtrato[df_filtrato["Titolo"] == t_cerca]
            if not df_filtrato.empty:
                for i in df_filtrato.index:
                    with st.container(border=True):
                        st.markdown(f"**Registrazione del {df_mod.at[i, 'Data']}**")
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            try: idx_p = elenco_plessi.index(df_mod.at[i, 'Plesso'])
                            except: idx_p = 0
                            nuovo_plesso = st.selectbox(f"Plesso", elenco_plessi, index=idx_p, key=f"mp_{i}")
                            try: idx_t = elenco_titoli.index(df_mod.at[i, 'Titolo'])
                            except: idx_t = 0
                            nuovo_titolo = st.selectbox(f"Titolo Libro", elenco_titoli, index=idx_t, key=f"mt_{i}")
                            nuove_note = st.text_area("Note", value=df_mod.at[i, 'Note'], key=f"mnot_{i}", height=70)
                        with col2:
                            val_sez = int(float(df_mod.at[i, 'N° sezioni'])) if df_mod.at[i, 'N° sezioni'] else 1
                            nuovo_n_sez = st.number_input("N° sezioni", min_value=1, value=val_sez, key=f"mn_{i}")
                            nuova_sez_lett = st.text_input("Lettera Sezione", value=df_mod.at[i, 'Sezione'], key=f"ms_{i}")
                        with col3:
                            attuale_sag = df_mod.at[i, 'Saggio Consegna']
                            idx_saggio = ["-", "NO", "SI"].index(attuale_sag) if attuale_sag in ["-", "NO", "SI"] else 0
                            nuovo_saggio = st.selectbox("Saggio consegnato", ["-", "NO", "SI"], index=idx_saggio, key=f"msag_{i}")
                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("💾 AGGIORNA", key=f"upd_{i}", use_container_width=True, type="primary"):
                                if nuovo_saggio != "-":
                                    df_full = pd.read_csv(DB_FILE).fillna("").astype(str)
                                    info_new = catalogo[catalogo.iloc[:, 0] == nuovo_titolo]
                                    df_full.at[i, 'Plesso'] = nuovo_plesso
                                    df_full.at[i, 'Titolo'] = nuovo_titolo
                                    if not info_new.empty:
                                        df_full.at[i, 'Materia'] = info_new.iloc[0,1]; df_full.at[i, 'Editore'] = info_new.iloc[0,2]; df_full.at[i, 'Agenzia'] = info_new.iloc[0,3]
                                    df_full.at[i, 'N° sezioni'] = nuovo_n_sez; df_full.at[i, 'Sezione'] = nuova_sez_lett.upper()
                                    df_full.at[i, 'Saggio Consegna'] = nuovo_saggio; df_full.at[i, 'Note'] = nuove_note
                                    df_full.to_csv(DB_FILE, index=False); backup_su_google_sheets(df_full)
                                    st.success("Aggiornato!"); st.rerun()
                        with b2:
                            if st.button("🗑️ ELIMINA", key=f"del_{i}", use_container_width=True):
                                df_full = pd.read_csv(DB_FILE).fillna("").astype(str); df_full = df_full.drop(int(i))
                                df_full.to_csv(DB_FILE, index=False); backup_su_google_sheets(df_full); st.rerun()
# =========================================================
# FINE BLOCCO 14
# =========================================================
# =========================================================
# --- BLOCCO 10: PAGINA STORICO (VERSIONE CORRETTA) ---
# INIZIO BLOCCO
# =========================================================
elif st.session_state.pagina == "Storico":
    st.header("📚 Registro Collane Consegnate")
    
    if "storico_ritiri" not in st.session_state:
        st.session_state.storico_ritiri = {}

    if not st.session_state.get("storico_consegne"):
        st.info("Nessuna consegna registrata.")
    else:
        elenco_plessi_storico = sorted(list(st.session_state.storico_consegne.keys()))
        opzioni_ricerca = ["- MOSTRA TUTTI -"] + elenco_plessi_storico
        scuola_selezionata = st.selectbox("🔍 Seleziona Plesso:", opzioni_ricerca)
        
        st.markdown("---")
        plessi_da_mostrare = [scuola_selezionata] if scuola_selezionata != "- MOSTRA TUTTI -" else elenco_plessi_storico

        for plesso in plessi_da_mostrare:
            with st.expander(f"🏫 {plesso}", expanded=False):
                
                if st.button(f"🔄 RITIRA TUTTO IL PLESSO: {plesso}", key=f"bulk_plesso_{plesso}"):
                    if plesso not in st.session_state.storico_ritiri: st.session_state.storico_ritiri[plesso] = {}
                    st.session_state.storico_ritiri[plesso].update(st.session_state.storico_consegne[plesso])
                    del st.session_state.storico_consegne[plesso]
                    salva_storico_cloud(st.session_state.storico_consegne)
                    st.success(f"Intero plesso {plesso} spostato nei Ritiri!"); st.rerun()

                per_tipo = st.session_state.storico_consegne[plesso]
                
                for tipo in sorted(list(per_tipo.keys())):
                    c_t, c_btn = st.columns([0.7, 0.3])
                    c_t.markdown(f"#### 📘 {tipo}")
                    
                    if c_btn.button(f"🔄 Ritira Tutto {tipo}", key=f"bulk_tipo_{plesso}_{tipo}"):
                        if plesso not in st.session_state.storico_ritiri: st.session_state.storico_ritiri[plesso] = {}
                        st.session_state.storico_ritiri[plesso][tipo] = per_tipo[tipo]
                        del st.session_state.storico_consegne[plesso][tipo]
                        if not st.session_state.storico_consegne[plesso]: del st.session_state.storico_consegne[plesso]
                        salva_storico_cloud(st.session_state.storico_consegne)
                        st.rerun()

                    with st.expander(f"Dettaglio {tipo}", expanded=True):
                        # Usiamo una copia della lista per evitare errori durante la rimozione degli elementi
                        lista_libri = list(per_tipo[tipo])
                        for i, lib in enumerate(lista_libri):
                            # PROTEZIONE: Se q è nullo o <= 0, lo impostiamo a 1 per evitare errori Streamlit
                            qta_salvata = int(lib.get('q', 1))
                            if qta_salvata < 1: qta_salvata = 1 
                            
                            col_titolo, col_qta, col_ritiro, col_del = st.columns([0.45, 0.20, 0.25, 0.10])
                            
                            col_titolo.markdown(f"<b style='font-size:15px; color:#1E3A8A;'>{lib['t']}</b><br><small>{lib['e']}</small>", unsafe_allow_html=True)
                            col_qta.markdown(f"<p style='text-align:center; font-size:14px;'>In carico:<br><b>{qta_salvata}</b></p>", unsafe_allow_html=True)

                            with col_ritiro:
                                # Il min_value è 1, il value è qta_salvata (che ora è minimo 1)
                                q_rit = st.number_input("Ritiro", min_value=1, max_value=max(1, qta_salvata), value=max(1, qta_salvata), key=f"qrit_{plesso}_{tipo}_{i}")
                                if st.button("🔄", key=f"btn_rit_{plesso}_{tipo}_{i}", help="Esegui ritiro parziale"):
                                    if plesso not in st.session_state.storico_ritiri: st.session_state.storico_ritiri[plesso] = {}
                                    if tipo not in st.session_state.storico_ritiri[plesso]: st.session_state.storico_ritiri[plesso][tipo] = []
                                    
                                    ritiro_item = lib.copy()
                                    ritiro_item['q'] = q_rit
                                    st.session_state.storico_ritiri[plesso][tipo].append(ritiro_item)
                                    
                                    lib['q'] = qta_salvata - q_rit
                                    
                                    if lib['q'] <= 0:
                                        per_tipo[tipo].pop(i)
                                    
                                    if not st.session_state.storico_consegne[plesso][tipo]: del st.session_state.storico_consegne[plesso][tipo]
                                    if not st.session_state.storico_consegne[plesso]: del st.session_state.storico_consegne[plesso]
                                    
                                    salva_storico_cloud(st.session_state.storico_consegne)
                                    st.rerun()
                            
                            if col_del.button("❌", key=f"del_h_{plesso}_{tipo}_{i}"):
                                per_tipo[tipo].pop(i)
                                if not per_tipo[tipo]: del per_tipo[tipo]
                                if not st.session_state.storico_consegne[plesso]: del st.session_state.storico_consegne[plesso]
                                salva_storico_cloud(st.session_state.storico_consegne); st.rerun()

    st.markdown("---")
    if st.button("⬅️ Torna a Modulo Consegne"):
        st.session_state.pagina = "Consegne"; st.rerun()
# =========================================================
# --- BLOCCO 15: TABELLONE CON PANNELLO FILTRI IN PAGINA ---
# INIZIO BLOCCO
# =========================================================
elif st.session_state.pagina == "Tabellone Stato":
    st.header("📊 Tabellone Avanzamento Plessi")

    # Definizione mappa sigle (necessaria per il funzionamento del blocco)
    mappa_sigle = {
        "LETTURE CLASSE PRIMA": "L1",
        "LETTURE CLASSE QUARTA": "L4",
        "SUSSIDIARI DISCIPLINE": "S4",
        "RELIGIONE": "R1\\4",
        "INGLESE CLASSE PRIMA": "E1",
        "INGLESE CLASSE QUARTA": "E4"
    }

    # 1. GESTIONE STATO DEL PANNELLO
    if "mostra_pannello_filtri" not in st.session_state:
        st.session_state.mostra_pannello_filtri = False

    # Pulsante principale in alto
    if st.button("🔍 APRI RICERCA AVANZATA E FILTRI", use_container_width=True):
        st.session_state.mostra_pannello_filtri = not st.session_state.mostra_pannello_filtri

    # 2. IL PANNELLO DEI FILTRI (Appare solo se attivato)
    cerca = ""
    filtro_stato = "TUTTI"
    filtro_collana = "TUTTE"

    if st.session_state.mostra_pannello_filtri:
        with st.container(border=True): # Crea un box visivo per i filtri
            st.markdown("### 🛠 Parametri di Ricerca")
            f_col1, f_col2, f_col3 = st.columns(3)
            
            with f_col1:
                cerca = st.text_input("🔍 Nome Plesso:", placeholder="Es: Manzoni...").upper()
            
            with f_col2:
                filtro_stato = st.selectbox("📂 Stato:", 
                                           ["TUTTI", "DA INIZIARE", "DA RITIRARE", "RITIRATI"])
            
            with f_col3:
                # Recuperiamo le sigle dalla mappa per il menu a tendina
                opzioni_sigle = ["TUTTE"] + list(mappa_sigle.values())
                filtro_collana = st.selectbox("📘 Tipo Collana:", opzioni_sigle)
            
            if st.button(" Chiudi Filtri ❌"):
                st.session_state.mostra_pannello_filtri = False
                st.rerun()

    st.markdown("---")

    # 3. LOGICA DI FILTRAGGIO
    elenco_totale = get_lista_plessi()
    consegnati = st.session_state.get("storico_consegne", {})
    ritirati = st.session_state.get("storico_ritiri", {})

    mostra = []
    for p in elenco_totale:
        # Controllo Nome
        if cerca and cerca not in str(p).upper():
            continue
            
        cat_attive = consegnati.get(p, {}).keys()
        sigle_p = [mappa_sigle.get(cat, cat[:2]) for cat in cat_attive]
        
        ha_sigle = len(cat_attive) > 0
        e_ritirato = p in ritirati and not ha_sigle
        e_bianco = p not in consegnati and p not in ritirati

        # Controllo Stato
        passa_stato = False
        if filtro_stato == "TUTTI": passa_stato = True
        elif filtro_stato == "DA INIZIARE" and e_bianco: passa_stato = True
        elif filtro_stato == "DA RITIRARE" and ha_sigle: passa_stato = True
        elif filtro_stato == "RITIRATI" and e_ritirato: passa_stato = True
        
        if not passa_stato: continue

        # Controllo Collana (Sigla)
        if filtro_collana != "TUTTE" and filtro_collana not in sigle_p:
            continue

        mostra.append(p)

    # 4. VISUALIZZAZIONE GRIGLIA (Badge neri e font grande)
    if not mostra:
        st.info("ℹ️ Nessun plesso corrisponde ai filtri selezionati.")
    else:
        n_col = 4 
        for i in range(0, len(mostra), n_col):
            cols = st.columns(n_col)
            for j, plesso in enumerate(mostra[i:i+n_col]):
                
                categorie_attive = consegnati.get(plesso, {}).keys()
                sigle_da_mostrare = [mappa_sigle.get(cat, cat[:2]) for cat in categorie_attive]
                
                bg, txt, lab, brd = ("#f8f9fa", "#333", "DA INIZIARE", "2px solid #dee2e6")
                
                if plesso in ritirati and not sigle_da_mostrare:
                    bg, txt, lab, brd = ("#28a745", "#FFF", "✅ COMPLETATO", "2px solid #1e7e34")
                elif sigle_da_mostrare:
                    bg, txt, lab, brd = ("#FF8C00", "#FFF", "🚚 IN CONSEGNA", "2px solid #e67e22")

                # HTML per i badge (testo nero, font grande)
                html_blocco_sigle = ""
                if sigle_da_mostrare:
                    span_sigle = "".join([
                        f'''<span style="
                            background: white; color: black; padding: 5px 10px; border-radius: 6px; 
                            font-size: 15px; font-weight: 900; margin: 4px; border: 2.5px solid #000; 
                            display: inline-block; box-shadow: 2px 2px 0px rgba(0,0,0,0.2);
                        ">{s}</span>''' for s in sigle_da_mostrare
                    ])
                    html_blocco_sigle = f'<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 2px; margin-top: 12px;">{span_sigle}</div>'

                with cols[j]:
                    st.markdown(f"""
                        <div style="
                            background-color: {bg}; color: {txt}; border: {brd};
                            border-radius: 12px; padding: 20px 10px; margin-bottom: 20px;
                            text-align: center; min-height: 195px; display: flex;
                            flex-direction: column; justify-content: center; align-items: center;
                            box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
                        ">
                            <div style="font-size: 20px; font-weight: 900; line-height: 1.2; text-transform: uppercase; margin-bottom: 8px;">
                                {plesso}
                            </div>
                            <div style="font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; opacity: 0.9;">
                                {lab}
                            </div>
                            {html_blocco_sigle}
                        </div>
                    """, unsafe_allow_html=True)

    st.markdown("---")
    if st.button("⬅️ Torna al Modulo Consegne", key="btn_back_tab_final"):
        st.session_state.pagina = "Consegne"; st.rerun()

# =========================================================
# FINE BLOCCO 15
# =========================================================
        
        
st.markdown("<p style='text-align: center; color: gray;'>Created by Antonio Ciccarelli v13.4</p>", unsafe_allow_html=True)


















































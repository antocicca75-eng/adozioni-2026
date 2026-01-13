import streamlit as st
import pandas as pd
import os
from datetime import datetime
from openpyxl import load_workbook
import io
import gspread
from google.oauth2.service_account import Credentials
import json
from fpdf import FPDF 

# --- CONFIGURAZIONE FILE ---
DB_FILE = "dati_adozioni.csv"
CONFIG_FILE = "anagrafiche.xlsx"
ID_FOGLIO = "1Ah5_pucc4b0ziNZxqo0NRpHwyUvFrUEggIugMXzlaKk"

st.set_page_config(page_title="Adozioni 2026", layout="wide", page_icon="📚")

# =========================================================
# --- CLASSE PDF PER MODULO CONSEGNE ---
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

# --- FUNZIONE CONNESSIONE GOOGLE SHEETS ---
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

# --- STILE CSS ---
st.markdown("""
    <style>
    [data-testid="stDataEditor"] thead tr th { background-color: #004a99 !important; color: white !important; }
    .stApp { background-color: #ffffff; }
    .totale-box { padding: 20px; background-color: #e8f0fe; border-radius: 10px; border: 1px solid #004a99; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CARICAMENTO ---
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

if "pagina" not in st.session_state:
    st.session_state.pagina = "Inserimento"

if 'db_consegne' not in st.session_state:
    st.session_state.db_consegne = {
        "LETTURE CLASSE PRIMA": [], "LETTURE CLASSE QUARTA": [],
        "SUSSIDIARI DISCIPLINE": [], "INGLESE CLASSE PRIMA": [], "INGLESE CLASSE QUARTA": [], "RELIGIONE": []
    }
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

# --- SIDEBAR NAVIGAZIONE ---
with st.sidebar:
    st.title("🧭 MENU")
    if st.button("➕ NUOVA ADOZIONE", use_container_width=True): st.session_state.pagina = "Inserimento"; st.rerun()
    if st.button("✏️ MODIFICA ADOZIONE", use_container_width=True): st.session_state.pagina = "Modifica"; st.rerun()
    if st.button("🆕 AGGIUNGI A CATALOGO", use_container_width=True): st.session_state.pagina = "NuovoLibro"; st.rerun()
    if st.button("📊 REGISTRO COMPLETO", use_container_width=True): st.session_state.pagina = "Registro"; st.rerun()
    if st.button("🔍 FILTRA E RICERCA", use_container_width=True): st.session_state.pagina = "Ricerca"; st.rerun()
    if st.button("📄 MODULO CONSEGNE", use_container_width=True): st.session_state.pagina = "Consegne"; st.rerun()
    if st.button("📚 COLLANE CONSEGNATE", use_container_width=True): st.session_state.pagina = "Storico"; st.rerun()

# --- LOGICA PAGINE ---

# --- PAGINA CONSEGNE (VERSIONE CORRETTA E PULITA) ---
if st.session_state.pagina == "Consegne":
    st.header("📄 Generazione Moduli Consegna")
    if "storico_consegne" not in st.session_state: 
        st.session_state.storico_consegne = {}
    
    elenco_plessi_con_vuoto = ["- SELEZIONA PLESSO -"] + elenco_plessi
    
    def reset_consegne_totale():
        st.session_state.lista_consegne_attuale = []
        st.session_state.last_cat = None
        st.rerun()

    # Contatori per resettare i widget
    if "reset_ctr" not in st.session_state: st.session_state.reset_ctr = 0
    if "add_ctr" not in st.session_state: st.session_state.add_ctr = 0
    
    ctr = st.session_state.reset_ctr
    actr = st.session_state.add_ctr

    col_p, col_c = st.columns(2)
    p_scelto = col_p.selectbox("Seleziona Plesso:", elenco_plessi_con_vuoto, key=f"p_sel_{ctr}")
    
    basi = ["- SELEZIONA -", "INGLESE CLASSE PRIMA", "INGLESE CLASSE QUARTA"]
    altre = [k for k in st.session_state.db_consegne.keys() if k not in ["INGLESE", "INGLESE CLASSE PRIMA", "INGLESE CLASSE QUARTA"]]
    cat_scelta = col_c.selectbox("Tipologia Libri:", basi + altre, key=f"c_sel_{ctr}")

    if cat_scelta != "- SELEZIONA -" and st.session_state.get('last_cat') != cat_scelta:
        st.session_state.lista_consegne_attuale = list(st.session_state.db_consegne.get(cat_scelta, []))
        st.session_state.last_cat = cat_scelta

    if cat_scelta != "- SELEZIONA -":
        st.markdown("---")
        # Visualizzazione lista attuale
        for i, lib in enumerate(st.session_state.lista_consegne_attuale):
            ci, cd = st.columns([0.9, 0.1])
            ci.info(f"{lib['t']} | {lib['e']} | Classi: {lib['c1']} {lib['c2']} {lib['c3']}")
            if cd.button("❌", key=f"del_{cat_scelta}_{i}"):
                st.session_state.lista_consegne_attuale.pop(i)
                st.rerun()

        col_btns = st.columns(2)
        if col_btns[0].button("💾 REGISTRA LISTA", use_container_width=True):
            st.session_state.db_consegne[cat_scelta] = list(st.session_state.lista_consegne_attuale)
            st.success("Salvato!")
        
        if col_btns[1].button("🗑️ SVUOTA TUTTO", use_container_width=True):
            st.session_state.reset_ctr += 1
            reset_consegne_totale()

        # EXPANDER PER AGGIUNTA LIBRO (Sistemato Indentation e Reset)
        with st.expander("➕ Cerca e Aggiungi Libro"):
            df_cat = get_catalogo_libri()
            if not df_cat.empty:
                scelta_libro = st.selectbox(
                    "Seleziona libro:", 
                    ["- CERCA TITOLO -"] + sorted(df_cat.iloc[:, 0].astype(str).unique().tolist()),
                    key=f"scelta_lib_{actr}"
                )
                
                if scelta_libro != "- CERCA TITOLO -":
                    dati_libro = df_cat[df_cat.iloc[:, 0] == scelta_libro].iloc[0]
                    cc1, cc2, cc3, _ = st.columns([1, 1, 1, 5])
                    
                    c1in = cc1.text_input("N°", max_chars=2, key=f"in1_{actr}")
                    c2in = cc2.text_input("N° ", max_chars=2, key=f"in2_{actr}")
                    c3in = cc3.text_input("N°  ", max_chars=2, key=f"in3_{actr}")
                    
                    if st.button("Conferma Aggiunta", key=f"btn_add_{actr}"):
                        st.session_state.lista_consegne_attuale.append({
                            "t": str(dati_libro.iloc[0]).upper(), 
                            "e": str(dati_libro.iloc[2]).upper(), 
                            "c1": c1in, 
                            "c2": c2in, 
                            "c3": c3in
                        })
                        # Incrementiamo il contatore per svuotare i campi al prossimo rerun
                        st.session_state.add_ctr += 1
                        st.rerun()

    st.markdown("---")
    d1, d2 = st.columns(2)
    docente = d1.text_input("Insegnante ricevente", key=f"doc_{ctr}")
    data_con = d2.text_input("Data di consegna", key=f"dat_{ctr}")
    classe_man = d1.text_input("Classe specifica", key=f"cla_{ctr}")

    col_print, col_conf = st.columns(2)
    if col_print.button("🖨️ GENERA PDF", use_container_width=True):
        if st.session_state.lista_consegne_attuale:
            pdf = PDF_CONSEGNA()
            pdf.add_page()
            pdf.disegna_modulo(0, st.session_state.lista_consegne_attuale, cat_scelta, p_scelto, docente, classe_man, data_con)
            pdf.dashed_line(148.5, 0, 148.5, 210, 0.5)
            pdf.disegna_modulo(148.5, st.session_state.lista_consegne_attuale, cat_scelta, p_scelto, docente, classe_man, data_con)
            st.download_button("📥 SCARICA PDF", bytes(pdf.output()), f"consegna.pdf", "application/pdf")

    if col_conf.button("✅ CONFERMA CONSEGNA", use_container_width=True, key="conf_consegna_btn"):
        if p_scelto != "- SELEZIONA PLESSO -" and cat_scelta != "- SELEZIONA -":
            if p_scelto not in st.session_state.storico_consegne: 
                st.session_state.storico_consegne[p_scelto] = {}
            st.session_state.storico_consegne[p_scelto][cat_scelta] = list(st.session_state.lista_consegne_attuale)
            st.success(f"Consegna registrata per {p_scelto}!")
# --- PAGINA STORICO (PULITA) ---
elif st.session_state.pagina == "Storico":
    st.header("📚 Registro Collane Consegnate")
    if not st.session_state.get("storico_consegne"):
        st.info("Nessuna consegna registrata.")
    else:
        for plesso in list(st.session_state.storico_consegne.keys()):
            with st.expander(f"🏫 {plesso}", expanded=False):
                per_tipo = st.session_state.storico_consegne[plesso]
                for tipo in list(per_tipo.keys()):
                    with st.expander(f"📖 {tipo}", expanded=False):
                        for i, lib in enumerate(per_tipo[tipo]):
                            c_inf, c_del = st.columns([0.85, 0.15])
                            c_inf.write(f"**{lib['t']}** — {lib['e']} ({lib['c1']} {lib['c2']} {lib['c3']})")
                            if c_del.button("❌", key=f"rit_{plesso}_{tipo}_{i}"):
                                st.session_state.storico_consegne[plesso][tipo].pop(i)
                                if not st.session_state.storico_consegne[plesso][tipo]: del st.session_state.storico_consegne[plesso][tipo]
                                if not st.session_state.storico_consegne[plesso]: del st.session_state.storico_consegne[plesso]
                                st.rerun()

    if st.button("⬅️ Torna a Modulo Consegne", key="btn_back_st"):
        st.session_state.pagina = "Consegne"; st.rerun()

# --- PAGINA NUOVO LIBRO ---
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


# --- PAGINA REGISTRO ---
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
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        somma = pd.to_numeric(df["N° sezioni"], errors='coerce').sum()
        st.markdown(f"""<div class="totale-box">🔢 Totale Classi: <b>{int(somma)}</b></div>""", unsafe_allow_html=True)
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


st.markdown("<p style='text-align: center; color: gray;'>Created by Antonio Ciccarelli v13.4</p>", unsafe_allow_html=True)









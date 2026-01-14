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
# --- BLOCCO 1: CONFIGURAZIONE E COSTANTI ---
# =========================================================
DB_FILE = "dati_adozioni.csv"
ID_FOGLIO = "1Ah5_pucc4b0ziNZxqo0NRpHwyUvFrUEggIugMXzlaKk"

st.set_page_config(page_title="Adozioni 2026", layout="wide", page_icon="📚")

# =========================================================
# --- BLOCCO 2: CONNESSIONE CLOUD ---
# =========================================================
def connetti_google_sheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        json_info = json.loads(st.secrets["gspread"]["json_data"], strict=False)
        if "private_key" in json_info:
            json_info["private_key"] = json_info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(json_info, scopes=scope)
        client_gs = gspread.authorize(creds)
        return client_gs.open_by_key(ID_FOGLIO)
    except Exception as e:
        st.error(f"⚠️ Errore connessione Cloud: {e}")
        return None

# =========================================================
# --- BLOCCO 6: MOTORE PDF (Corretto) ---
# =========================================================
class PDF_CONSEGNA(FPDF):
    def __init__(self, logo_data=None):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.logo_data = logo_data

    def disegna_modulo(self, x_offset, libri, categoria, p, ins, sez, data_m):
        # Gestione Logo
        if self.logo_data:
            try:
                # Correzione Indentazione riga 129: il contenuto del try deve essere indentato
                with open("temp_logo.png", "wb") as f: 
                    f.write(self.logo_data.getbuffer())
                self.image("temp_logo.png", x=x_offset + 34, y=8, w=80)
            except Exception as e:
                st.warning(f"Impossibile caricare il logo: {e}")
        
        # Intestazione Tabella
        self.set_y(38)
        self.set_x(x_offset + 10)
        self.set_fill_color(230, 230, 230)
        self.set_font('Arial', 'B', 9)
        self.cell(129, 8, str(categoria).upper(), border=1, ln=1, align='C', fill=True)
        
        # Righe Libri
        self.set_font('Arial', '', 8)
        for i, lib in enumerate(libri):
            self.set_x(x_offset + 10)
            self.cell(75, 6, f" {str(lib['t'])[:45]}", border=1)
            self.cell(24, 6, str(lib.get('c1','')), border=1, align='C')
            self.cell(30, 6, str(lib.get('e',''))[:20], border=1, ln=1)

        # Sezione Firme/Dettagli
        self.set_y(145)
        for label, val in [("PLESSO:", p), ("INSEGNANTE:", ins), ("CLASSE:", sez), ("DATA:", data_m)]:
            self.set_x(x_offset + 10)
            self.set_font('Arial', 'B', 7.5)
            self.cell(35, 6.2, label, border=1)
            self.set_font('Arial', '', 7.5)
            self.cell(94, 6.2, str(val).upper(), border=1, ln=1)

# =========================================================
# --- BLOCCO 7: LOGICA DI NAVIGAZIONE ---
# =========================================================
if "pagina" not in st.session_state: 
    st.session_state.pagina = "Inserimento"

with st.sidebar:
    st.title("🧭 MENU")
    if st.button("➕ NUOVA ADOZIONE"): st.session_state.pagina = "Inserimento"
    if st.button("📄 MODULO CONSEGNE"): st.session_state.pagina = "Consegne"

# --- Rendering Pagine ---
if st.session_state.pagina == "Inserimento":
    st.subheader("Registrazione Adozioni")
    # Logica inserimento...

elif st.session_state.pagina == "Consegne":
    st.subheader("Generazione Moduli PDF")
    # Logica PDF...

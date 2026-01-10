import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import io

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Adozioni 2026", layout="wide", page_icon="📚")

# Connessione ultra-rapida
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNZIONI CARICAMENTO ---
def carica_dati(foglio, tempo=1):
    try:
        df = conn.read(worksheet=foglio, ttl=tempo)
        if df is not None:
            df.columns = [c.strip().upper() for c in df.columns]
            return df.fillna("")
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- PREPARAZIONE DATI ---
df_catalogo = carica_dati("Catalogo")
df_adozioni = carica_dati("Adozioni", tempo=0) # Tempo 0 per vedere subito i nuovi inserimenti
elenco_plessi = carica_dati("Plesso").iloc[:,0].tolist() if not carica_dati("Plesso").empty else []
elenco_agenzie = carica_dati("Agenzie").iloc[:,0].tolist() if not carica_dati("Agenzie").empty else []

# --- SIDEBAR: NAVIGAZIONE ED EXPORT ---
with st.sidebar:
    st.title("📂 GESTIONE")
    menu = st.radio("Vai a:", ["Nuova Adozione", "Registro e Export", "Aggiungi al Catalogo"])
    
    st.markdown("---")
    st.subheader("📥 Backup Dati")
    
    if not df_adozioni.empty:
        # Funzione per convertire DataFrame in Excel (in memoria)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_adozioni.to_excel(writer, index=False, sheet_name='Adozioni')
        
        st.download_button(
            label="XLSX - ESPORTA IN EXCEL",
            data=buffer.getvalue(),
            file_name=f"adozioni_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    if st.button("🔄 AGGIORNA TUTTO"):
        st.cache_data.clear()
        st.rerun()

# --- LOGICA PAGINE ---

# 1. REGISTRO ED EXPORT
if menu == "Registro e Export":
    st.subheader("📑 Registro Completo Adozioni")
    if not df_adozioni.empty:
        st.dataframe(df_adozioni, use_container_width=True)
        st.info(f"Totale righe nel database: {len(df_adozioni)}")
    else:
        st.warning("Il database delle adozioni è vuoto.")

# 2. NUOVA ADOZIONE
elif menu == "Nuova Adozione":
    st.subheader("✍️ Inserimento Nuova Adozione")
    
    with st.form("form_adozione", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            titoli = df_catalogo["TITOLO"].tolist() if not df_catalogo.empty else []
            scelta_titolo = st.selectbox("Seleziona Libro", [""] + titoli)
            plesso = st.selectbox("Plesso", [""] + elenco_plessi)
        with col2:
            sezioni = st.number_input("Numero Sezioni", min_value=1, step=1)
            classe = st.text_input("Sezione (es. A, B, C)")
        
        note = st.text_area("Note aggiuntive")
        submit = st.form_submit_button("SALVA ONLINE")

        if submit:
            if scelta_titolo and plesso:
                # Recupera info libro
                info = df_catalogo[df_catalogo["TITOLO"] == scelta_titolo].iloc[0]
                nuova_riga = {
                    "DATA": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "PLESSO": plesso,
                    "MATERIA": info["MATERIA"],
                    "TITOLO": scelta_titolo,
                    "EDITORE": info["EDITORE"],
                    "AGENZIA": info["AGENZIA"],
                    "N° SEZIONI": sezioni,
                    "SEZIONE": classe.upper(),
                    "NOTE": note
                }
                
                # Salvataggio
                df_updated = pd.concat([df_adozioni, pd.DataFrame([nuova_riga])], ignore_index=True)
                conn.update(worksheet="Adozioni", data=df_updated)
                st.success("Adozione registrata con successo!")
                st.cache_data.clear()
            else:
                st.error("Errore: Titolo e Plesso sono obbligatori.")

# 3. AGGIUNGI AL CATALOGO
elif menu == "Aggiungi al Catalogo":
    st.subheader("📖 Aggiungi Titolo alla Lista Libri")
    with st.form("form_catalogo", clear_on_submit=True):
        t = st.text_input("Titolo")
        m = st.text_input("Materia")
        e = st.text_input("Editore")
        a = st.selectbox("Agenzia", [""] + elenco_agenzie)
        
        if st.form_submit_button("AGGIUNGI AL CATALOGO"):
            if t and m and e and a:
                nuovo_libro = {"TITOLO": t, "MATERIA": m, "EDITORE": e, "AGENZIA": a}
                df_cat_up = pd.concat([df_catalogo, pd.DataFrame([nuovo_libro])], ignore_index=True)
                conn.update(worksheet="Catalogo", data=df_cat_up)
                st.success("Libro aggiunto!")
                st.cache_data.clear()

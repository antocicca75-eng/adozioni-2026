=========================================================
# --- BLOCCO 15: TABELLONE GENERALE (CON NUOVO FILTRO) ---
# INIZIO BLOCCO AGGIORNATO
# =========================================================
elif st.session_state.pagina == "Tabellone Stato":
    st.header("📊 Tabellone Avanzamento Plessi")

    mappa_sigle = {
        "LETTURE CLASSE PRIMA": "L1", "LETTURE CLASSE QUARTA": "L4",
        "SUSSIDIARI DISCIPLINE": "S4", "RELIGIONE": "R1\\4",
        "INGLESE CLASSE PRIMA": "E1", "INGLESE CLASSE QUARTA": "E4"
    }

    elenco_totale = get_lista_plessi()
    consegnati = st.session_state.get("storico_consegne", {})
    ritirati = st.session_state.get("storico_ritiri", {})

    if not elenco_totale:
        st.warning("⚠️ Nessun plesso trovato.")
    else:
        # Filtri
        f_c1, f_c2 = st.columns([2, 1])
        cerca = f_c1.text_input("🔍 Cerca Plesso...", "").upper()
        filtro_stato = f_c2.selectbox("📂 Filtra Stato:", ["TUTTI", "DA INIZIARE", "DA RITIRARE", "COMPLETATI"])

        # Logica di Filtraggio
        mostra = []
        for p in elenco_totale:
            if cerca not in str(p).upper(): continue
            
            p_consegnato = p in consegnati and len(consegnati[p]) > 0
            p_completato = p in ritirati and (p not in consegnati or len(consegnati[p]) == 0)
            p_bianco = not p_consegnato and not p_completato

            if filtro_stato == "TUTTI": mostra.append(p)
            elif filtro_stato == "DA INIZIARE" and p_bianco: mostra.append(p)
            elif filtro_stato == "DA RITIRARE" and p_consegnato: mostra.append(p)
            elif filtro_stato == "COMPLETATI" and p_completato: mostra.append(p)

        # Griglia
        n_col = 4 
        for i in range(0, len(mostra), n_col):
            cols = st.columns(n_col)
            for j, plesso in enumerate(mostra[i:i+n_col]):
                cat_attive = consegnati.get(plesso, {}).keys()
                sigle = [mappa_sigle.get(cat, cat[:2]) for cat in cat_attive]
                
                bg, lab, brd = ("#FFFFFF", "DA FARE", "2px solid #DDD")
                if plesso in ritirati and not sigle:
                    bg, lab, brd = ("#28a745", "✅ COMPLETATO", "2px solid #1e7e34")
                elif sigle:
                    bg, lab, brd = ("#FF8C00", "🚚 DA RITIRARE", "2px solid #e67e22")

                with cols[j]:
                    st.markdown(f"""
                        <div style="background-color: {bg}; border: {brd}; border-radius: 10px; padding: 10px; text-align: center; min-height: 120px;">
                            <div style="font-weight: 900; font-size: 13px;">{plesso}</div>
                            <div style="font-size: 10px; margin-top: 5px;">{lab}</div>
                            <div style="margin-top: 8px;">
                                {"".join([f'<span style="background:white; color:black; padding:2px 4px; border-radius:3px; font-size:9px; font-weight:900; border:1px solid #333; margin:1px; display:inline-block;">{s}</span>' for s in sigle])}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    if st.button("⬅️ Torna al Modulo Consegne"):
        st.session_state.pagina = "Consegne"; st.rerun()

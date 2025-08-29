AVS Dashboard Controllo Qualità dell'acqua ! 


Un'applicazione web interattiva per l'analisi dei dati di qualità dell'acqua.

Descrizione del Progetto
Dash-Quality è una dashboard intuitiva sviluppata con Streamlit che consente agli utenti di caricare un file Excel o CSV e visualizzare i dati in vari grafici dinamici, come grafici a linee, istogrammi e box plot. L'app offre filtri avanzati per analizzare i dati in base a data, operatore, campione e nome del test.

Come Avviare l'Applicazione
Per avviare l'applicazione in locale, segui questi semplici passaggi.

Assicurati di avere Python installato sul tuo sistema.

Installa le librerie necessarie utilizzando il file requirements.txt che abbiamo creato:

pip install -r requirements.txt



Avvia l'applicazione dal terminale (nella stessa cartella in cui si trova il file dashboard.py):

streamlit run dashboard.py

Utilizzo
Carica un file di dati: L'applicazione si avvia automaticamente con un set di dati predefinito. Puoi caricare un tuo file .xlsx o .csv per analizzare nuovi dati.

Usa i filtri: Sulla barra laterale a sinistra, puoi filtrare i dati per intervallo di date, ID operatore, ID campione e nomi dei test.

Seleziona il grafico: Scegli il tipo di visualizzazione che preferisci dal menu a tendina "Seleziona Tipo di Grafico".

Esplora i dati: Usa i grafici interattivi e la tabella dei dati filtrati per analizzare i risultati e individuare tendenze.

Informazioni sullo Sviluppo
Linguaggio: Python

Librerie Principali: Streamlit, Pandas, Plotly Express

Sviluppatore: Arnel Kovacevic (Orizon-aix)

Versione: 1.2.1

Contatti: info@orizon-aix.com | https://orizon-aix.com

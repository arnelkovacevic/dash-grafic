import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import io
import requests

# Impostazioni di base della pagina
st.set_page_config(
    page_title="Dashboard Qualità Acqua",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Definisci i nomi delle colonne per coerenza
COLUMN_NAMES = {
    'date_time': 'Time',
    'sample_id': 'Sample ID',
    'test_name': 'Test Name',
    'result': 'Result',
    'date': 'Date',
    'user_id': 'User ID',
    'abs': 'ABS'
}

# Funzione per leggere e pulire i dati
@st.cache_data
def load_data(file_source):
    """
    Carica e preprocessa i dati dal file.
    Supporta sia un file caricato che un percorso di file locale.
    """
    try:
        # Controlla se il file_source è un percorso (stringa) o un file caricato (UploadedFile)
        if isinstance(file_source, str):
            # Percorso del file locale
            df = pd.read_excel(file_source)
        elif file_source.name.endswith('.csv'):
            df = pd.read_csv(file_source)
        elif file_source.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_source)
        else:
            st.error('Tipo di file non supportato. Carica un file .csv o .xlsx.')
            return pd.DataFrame()
        
        # Pulizia e preparazione dei dati come nel codice originale
        df[COLUMN_NAMES['date_time']] = pd.to_datetime(df[COLUMN_NAMES['date_time']], errors='coerce')
        df = df[df[COLUMN_NAMES['date_time']].notna()]
        df[COLUMN_NAMES['date']] = df[COLUMN_NAMES['date_time']].dt.floor('D')
        
        return df

    except FileNotFoundError:
        st.error(f'Errore: File non trovato al percorso: {file_source}')
        return pd.DataFrame()
    except Exception as e:
        st.error(f'Errore durante l\'elaborazione del file: {e}')
        return pd.DataFrame()


# -------------------- Layout e Widget --------------------

# Inizializza lo stato della sessione per controllare il popup
if 'show_info_popup' not in st.session_state:
    st.session_state.show_info_popup = False

# Creiamo due colonne per il logo
col_logo, _ = st.columns([0.15, 0.85])

with col_logo:
    st.image("assets/logo.jpg", width=120)


st.title("Dashboard di Test della Qualità dell'Acqua")


# File uploader
uploaded_file = st.file_uploader("Trascina e rilascia o Seleziona un file", type=['csv', 'xlsx'])

# Definisci il percorso del file predefinito
LOCAL_FILE_PATH = "report_controlli_acqua.xlsx"

# Logica di caricamento del file
df = pd.DataFrame()
if uploaded_file:
    df = load_data(uploaded_file)
else:
    df = load_data(LOCAL_FILE_PATH)


if not df.empty:
    # Qui il resto del tuo codice originale per la visualizzazione e i filtri
    # ... (Il codice rimane invariato da questo punto in poi) ...
    
    # Crea la sidebar per i filtri
    st.sidebar.header("Filtri Dati")

    # Filtro per l'intervallo di date
    min_date = pd.to_datetime(df[COLUMN_NAMES['date']].min()).date()
    max_date = pd.to_datetime(df[COLUMN_NAMES['date']].max()).date()
    date_range = st.sidebar.date_input("Seleziona Intervallo di Date:", 
                                     [min_date, max_date], 
                                     min_value=min_date, 
                                     max_value=max_date)

    # Filtri a tendina
    operator_options = df[COLUMN_NAMES['user_id']].unique().tolist()
    selected_operators = st.sidebar.multiselect("Seleziona ID Operatore:", options=operator_options)
    
    # Abilita o disabilita i dropdown di Sample e Test
    disable_sample_test = bool(selected_operators)

    sample_options = df[COLUMN_NAMES['sample_id']].unique().tolist()
    # Imposta la selezione predefinita per mostrare tutti i campioni
    selected_samples = st.sidebar.multiselect("Seleziona ID Campione:", options=sample_options, disabled=disable_sample_test, default=sample_options)
    
    test_options = df[COLUMN_NAMES['test_name']].unique().tolist()
    # Imposta la selezione predefinita per mostrare solo il primo test
    default_test = [test_options[0]] if test_options else []
    selected_tests = st.sidebar.multiselect("Seleziona Nomi Test:", options=test_options, disabled=disable_sample_test, default=default_test)

    # Filtro per il valore del risultato
    min_result_val = float(df[COLUMN_NAMES['result']].min())
    max_result_val = float(df[COLUMN_NAMES['result']].max())
    results_range = st.sidebar.slider(
        "Filtra per Valore Risultato:",
        min_value=min_result_val,
        max_value=max_result_val,
        value=[min_result_val, max_result_val],
        step=(max_result_val - min_result_val) / 100
    )
    
    # Filtro per il tipo di grafico
    chart_type = st.sidebar.selectbox(
        "Seleziona Tipo di Grafico:",
        options=['line', 'scatter', 'box', 'histogram', 'density_histogram', 'scatter_matrix'],
        format_func=lambda x: {'line': 'Grafico a Linee', 'scatter': 'Grafico a Dispersione', 'box': 'Box Plot',
                               'histogram': 'Istogramma', 'density_histogram': 'Istogramma di Densità',
                               'scatter_matrix': 'Matrice di Correlazione'}[x]
    )

    # -------------------- Filtra i Dati --------------------
    # Streamlit riesegue lo script ogni volta che un widget cambia,
    # quindi la logica di filtraggio è qui
    df_filtered = df.copy()

    if len(date_range) == 2:
        start_date, end_date = date_range
        df_filtered = df_filtered[
            (df_filtered[COLUMN_NAMES['date']] >= pd.to_datetime(start_date)) &
            (df_filtered[COLUMN_NAMES['date']] <= pd.to_datetime(end_date))
        ]

    df_filtered = df_filtered[
        (df_filtered[COLUMN_NAMES['result']] >= results_range[0]) &
        (df_filtered[COLUMN_NAMES['result']] <= results_range[1])
    ]

    if selected_operators:
        df_filtered = df_filtered[df_filtered[COLUMN_NAMES['user_id']].isin(selected_operators)]
    elif selected_samples and selected_tests:
        df_filtered = df_filtered[
            df_filtered[COLUMN_NAMES['sample_id']].isin(selected_samples) &
            df_filtered[COLUMN_NAMES['test_name']].isin(selected_tests)
        ]

    # -------------------- Visualizzazione Principale --------------------
    if df_filtered.empty:
        st.warning("Nessun dato trovato con i filtri selezionati. Modifica la tua selezione.")
    else:
        # Crea le colonne per le summary cards
        col_samples, col_avg, col_tests = st.columns(3)

        with col_samples:
            total_samples = len(df_filtered[COLUMN_NAMES['sample_id']].unique())
            st.metric("Campioni Totali", total_samples)

        with col_avg:
            avg_result = f"{df_filtered[COLUMN_NAMES['result']].mean():.2f}"
            st.metric("Risultato Medio", avg_result)

        with col_tests:
            total_tests = len(df_filtered)
            st.metric("Test Totali", total_tests)

        st.markdown("---")
        
        # Crea una stringa dinamica per il titolo e determina la colonna per il colore
        dynamic_title = ""
        color_column = COLUMN_NAMES['sample_id']

        # Logica per il titolo dinamico e la colonna di colore
        if len(selected_samples) == 1 and selected_tests:
            # Caso 1: Un solo campione, uno o più test
            dynamic_title = f" per il campione: {selected_samples[0]}"
            color_column = COLUMN_NAMES['test_name']
        elif len(selected_samples) > 1 and selected_tests:
            # Caso 2: Più campioni, uno o più test
            dynamic_title = f" per i test: {', '.join(selected_tests)}"
            color_column = COLUMN_NAMES['sample_id']
        elif selected_tests:
            # Caso 3: Nessuna selezione di campioni, solo test
            dynamic_title = f" per i test: {', '.join(selected_tests)}"
        
        # --- Crea il grafico Plotly ---
        hover_cols = df_filtered.columns.tolist()
        
        fig = {}
        if chart_type == 'scatter':
            fig = px.scatter(df_filtered, x=COLUMN_NAMES['date'], y=COLUMN_NAMES['result'], color=color_column,
                            hover_data=hover_cols, title=f"Grafico a Dispersione dei Risultati dei Test{dynamic_title}")
        elif chart_type == 'line':
            fig = px.line(df_filtered, x=COLUMN_NAMES['date'], y=COLUMN_NAMES['result'], color=color_column,
                          hover_data=hover_cols, title=f"Grafico a Linee dei Risultati dei Test{dynamic_title}")
            fig.update_traces(mode='lines+markers')
        elif chart_type == 'box':
            fig = px.box(df_filtered, x=COLUMN_NAMES['sample_id'], y=COLUMN_NAMES['result'], color=COLUMN_NAMES['test_name'],
                         hover_data=hover_cols, title=f"Box Plot dei Risultati per ID Campione{dynamic_title}")
        elif chart_type == 'histogram':
            # Revertiamo per usare il comportamento standard di hover_data
            # che funziona correttamente con le aggregazioni.
            fig = px.histogram(df_filtered, x=COLUMN_NAMES['date'], y=COLUMN_NAMES['result'], color=color_column,
                               hover_data=hover_cols, title=f"Istogramma dei Risultati dei Test{dynamic_title}", barmode="group")
        elif chart_type == 'density_histogram':
            # Revertiamo per usare il comportamento standard di hover_data
            # che funziona correttamente con le aggregazioni.
            fig = px.histogram(df_filtered, x=COLUMN_NAMES['result'], color=COLUMN_NAMES['test_name'],
                               nbins=20, histnorm='probability density', marginal='rug',
                               hover_data=hover_cols, title=f"Istogramma di Densità dei Risultati{dynamic_title}")
        elif chart_type == 'scatter_matrix':
            fig = px.scatter_matrix(df_filtered, dimensions=[COLUMN_NAMES['result'], COLUMN_NAMES['abs']],
                                    color=COLUMN_NAMES['test_name'],
                                    hover_data=hover_cols, title=f"Matrice di Correlazione tra Risultato e ABS{dynamic_title}")
            fig.update_traces(diagonal_visible=False)
        
        # Mostra il grafico
        st.plotly_chart(fig, use_container_width=True)

        # Tabella dati
        st.markdown("---")
        st.header("Tabella Dati Filtrati")
        
        df_table_data = df_filtered.rename(columns={
            COLUMN_NAMES['date_time']: 'Ora',
            COLUMN_NAMES['sample_id']: 'ID Campione',
            COLUMN_NAMES['test_name']: 'Nome Test',
            COLUMN_NAMES['result']: 'Risultato',
            COLUMN_NAMES['user_id']: 'ID Operatore',
            COLUMN_NAMES['abs']: 'ABS'
        })
        
        st.dataframe(df_table_data)

        # Pulsante per il download
        csv_data = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Esporta Dati Filtrati",
            data=csv_data,
            file_name="dati_filtrati.csv",
            mime="text/csv",
        )


# -------------------- Footer --------------------
st.markdown("---")

if st.button("Info App"):
    st.session_state.show_info_popup = True

if st.session_state.show_info_popup:
    st.info("""
        ### Informazioni App
        **Nome:** Dash-Quality
        **Tipo:** web app
        
        **Linguaggio:** Python
        **Sviluppatore:** Arnel Kovacevic (Orizon-aix)
        
        **Versione:** 1.2.1
        **Lanciata:** Streamlit (01/09/2025)
        
        **Mail:** info@orizon-aix.com
        **Tel:** +39 3807525438
        **Web:** https://orizon-aix.com
    """)
    if st.button("Chiudi"):
        st.session_state.show_info_popup = False
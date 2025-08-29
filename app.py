import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import io
import openpyxl

# --- Impostazioni di base della pagina ---
st.set_page_config(
    page_title="Dashboard Qualità Acqua",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Definisci i nomi delle colonne per coerenza ---
COLUMN_NAMES = {
    'date_time': 'Time',
    'sample_id': 'Sample ID',
    'test_name': 'Test Name',
    'result': 'Result',
    'date': 'Date',
    'user_id': 'User ID',
    'abs': 'ABS'
}

# --- Funzione per leggere e pulire i dati (con spinner) ---
@st.cache_data
def load_data(file_source):
    """
    Carica e preprocessa i dati dal file.
    Supporta sia un file caricato che un percorso di file locale.
    """
    with st.spinner('Caricamento dati in corso...'):
        try:
            if isinstance(file_source, str):
                df = pd.read_excel(file_source)
            elif file_source.name.endswith('.csv'):
                df = pd.read_csv(file_source)
            elif file_source.name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_source)
            else:
                st.error('Tipo di file non supportato. Carica un file .csv o .xlsx.')
                return pd.DataFrame()
            
            # Pulizia e preparazione dei dati
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

# --- Funzione per salvare il DataFrame come XLSX ---
def to_excel(df):
    """Genera un file Excel in memoria da un DataFrame."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dati Filtrati')
    processed_data = output.getvalue()
    return processed_data

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
    # --- Sidebar per i filtri con espansori ---
    st.sidebar.header("Filtri Dati")

    # Filtro Intervallo di Date
    with st.sidebar.expander("Seleziona Intervallo di Date", expanded=True):
        min_date = pd.to_datetime(df[COLUMN_NAMES['date']].min()).date()
        max_date = pd.to_datetime(df[COLUMN_NAMES['date']].max()).date()
        date_range = st.date_input("Intervallo di Date:", 
                                     [min_date, max_date], 
                                     min_value=min_date, 
                                     max_value=max_date)

    # Filtri a tendina
    with st.sidebar.expander("Filtri Categoria", expanded=True):
        operator_options = df[COLUMN_NAMES['user_id']].unique().tolist()
        selected_operators = st.multiselect("ID Operatore:", options=operator_options)
        
        # Abilita o disabilita i dropdown di Sample e Test
        disable_sample_test = bool(selected_operators)
        
        sample_options = df[COLUMN_NAMES['sample_id']].unique().tolist()
        selected_samples = st.multiselect("ID Campione:", options=sample_options, disabled=disable_sample_test, default=sample_options)
        
        test_options = df[COLUMN_NAMES['test_name']].unique().tolist()
        default_test = [test_options[0]] if test_options else []
        selected_tests = st.multiselect("Nomi Test:", options=test_options, disabled=disable_sample_test, default=default_test)

    # Filtro per il valore del risultato
    with st.sidebar.expander("Filtro Valore Risultato", expanded=True):
        min_result_val = float(df[COLUMN_NAMES['result']].min())
        max_result_val = float(df[COLUMN_NAMES['result']].max())
        results_range = st.slider(
            "Valore Risultato:",
            min_value=min_result_val,
            max_value=max_result_val,
            value=[min_result_val, max_result_val],
            step=(max_result_val - min_result_val) / 100
        )
    
    # Filtro per il tipo di grafico
    with st.sidebar.expander("Tipo di Grafico", expanded=True):
        chart_type = st.selectbox(
            "Seleziona un tipo di grafico:",
            options=['line', 'scatter', 'box', 'violin', 'histogram', 'density_histogram', 'scatter_matrix'],
            format_func=lambda x: {'line': 'Grafico a Linee', 'scatter': 'Grafico a Dispersione', 'box': 'Box Plot',
                                   'violin': 'Grafico a Violino', 'histogram': 'Istogramma',
                                   'density_histogram': 'Istogramma di Densità', 'scatter_matrix': 'Matrice di Correlazione'}[x]
        )
    
    # --- Filtra i Dati ---
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
        st.warning("Nessun dato trovato con i filtri selezionati. Prova a modificare la tua selezione.")
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
        
        # --- Crea il grafico Plotly in un container ---
        with st.container():
            dynamic_title = ""
            color_column = COLUMN_NAMES['sample_id']
            
            if len(selected_samples) == 1 and selected_tests:
                dynamic_title = f" per il campione: {selected_samples[0]}"
                color_column = COLUMN_NAMES['test_name']
            elif len(selected_samples) > 1 and selected_tests:
                dynamic_title = f" per i test: {', '.join(selected_tests)}"
                color_column = COLUMN_NAMES['sample_id']
            elif selected_tests:
                dynamic_title = f" per i test: {', '.join(selected_tests)}"
            
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
            elif chart_type == 'violin':
                fig = px.violin(df_filtered, x=COLUMN_NAMES['test_name'], y=COLUMN_NAMES['result'], color=COLUMN_NAMES['test_name'],
                                hover_data=hover_cols, title=f"Grafico a Violino della Distribuzione dei Risultati{dynamic_title}")
            elif chart_type == 'histogram':
                fig = px.histogram(df_filtered, x=COLUMN_NAMES['date'], y=COLUMN_NAMES['result'], color=color_column,
                                   hover_data=hover_cols, title=f"Istogramma dei Risultati dei Test{dynamic_title}", barmode="group")
            elif chart_type == 'density_histogram':
                fig = px.histogram(df_filtered, x=COLUMN_NAMES['result'], color=COLUMN_NAMES['test_name'],
                                   nbins=20, histnorm='probability density', marginal='rug',
                                   hover_data=hover_cols, title=f"Istogramma di Densità dei Risultati{dynamic_title}")
            elif chart_type == 'scatter_matrix':
                fig = px.scatter_matrix(df_filtered, dimensions=[COLUMN_NAMES['result'], COLUMN_NAMES['abs']],
                                        color=COLUMN_NAMES['test_name'],
                                        hover_data=hover_cols, title=f"Matrice di Correlazione tra Risultato e ABS{dynamic_title}")
                fig.update_traces(diagonal_visible=False)
            
            st.plotly_chart(fig, use_container_width=True)

            # Pulsanti per il download dei dati
            download_expander = st.expander("Esporta Dati", expanded=False)
            with download_expander:
                col_csv, col_xlsx = st.columns(2)
                with col_csv:
                    csv_data = df_filtered.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Esporta Dati Filtrati (CSV)",
                        data=csv_data,
                        file_name="dati_filtrati.csv",
                        mime="text/csv",
                    )
                
                with col_xlsx:
                    excel_data = to_excel(df_filtered)
                    st.download_button(
                        label="Esporta Dati Filtrati (XLSX)",
                        data=excel_data,
                        file_name="dati_filtrati.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )


        # Tabella dati in un container
        with st.container():
            st.markdown("---")
            st.header("Tabella Dati Filtrati")
            
            df_table_data = df_filtered.rename(columns={
                COLUMN_NAMES['date_time']: 'Ora',
                COLUMN_NAMES['sample_id']: 'ID Campione',
                COLUMN_NAMES['test_name']: 'Nome Test',
                COLUMN_NAMES['result']: 'Risultato',
                COLUMN_NAMES['user_id']: 'ID Operatore',
                'abs': 'ABS'
            })
            
            st.dataframe(df_table_data)

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
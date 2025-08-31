import streamlit as st
import pandas as pd
import plotly.express as px
import io
import openpyxl
from datetime import datetime

# --- Impostazioni di base della pagina ---
st.set_page_config(
    page_title="Dashboard Osmosi",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Pulsante Home
if st.sidebar.button("🏠 Home"):
    st.switch_page("app.py")

# --- Colonne ---
COLUMN_NAMES = {
    'data_inizio': 'Data Inizio',
    'mc_inizio': 'MC Inizio',
    'data_fine': 'Data Fine',
    'mc_fine': 'MC Fine',
    'totale_mc': 'Totale MC',
    'mese': 'Mese',
    'lavaggio': 'Lavaggio',
    'anno': 'Anno'
}

# --- Mesi in ordine ---
mesi_ordine = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
               "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

# --- Funzione caricamento dati ---
@st.cache_data
def load_data(file_source):
    """Carica i dati da un file Excel e li preprocessa."""
    with st.spinner('Caricamento dati in corso...'):
        try:
            if isinstance(file_source, str):
                df = pd.read_excel(file_source, engine='openpyxl')
            elif file_source.name.endswith('.xlsx'):
                df = pd.read_excel(file_source, engine='openpyxl')
            else:
                st.error('Tipo di file non supportato. Carica un file .xlsx.')
                return pd.DataFrame()
        
            df[COLUMN_NAMES['data_inizio']] = pd.to_datetime(df[COLUMN_NAMES['data_inizio']], errors='coerce').dt.date
            df[COLUMN_NAMES['data_fine']] = pd.to_datetime(df[COLUMN_NAMES['data_fine']], errors='coerce').dt.date
            
            if COLUMN_NAMES['mese'] in df.columns:
                df[COLUMN_NAMES['mese']] = df[COLUMN_NAMES['mese']].str.strip().str.capitalize()
            
            return df
        except Exception as e:
            st.error(f'Errore durante l\'elaborazione del file: {e}')
            return pd.DataFrame()

# --- Funzione esportazione Excel ---
def to_excel(df):
    """Converte un DataFrame in un file Excel in memoria."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dati Filtrati')
    return output.getvalue()

# --- Layout ---
st.title("Dashboard Consumi Acqua (Osmosi)")

uploaded_file = st.file_uploader("Trascina e rilascia o Seleziona un file", type=['xlsx'])
LOCAL_FILE_PATH = "documents/osmosi_report.xlsx"

df = load_data(uploaded_file if uploaded_file else LOCAL_FILE_PATH)

if not df.empty:
    st.sidebar.header("Filtri Dati")

    # Tipo grafico
    with st.sidebar.expander("Tipo di Grafico", expanded=True):
        chart_type = st.selectbox(
            "Seleziona un tipo di grafico:",
            options=['bar', 'line'],
            format_func=lambda x: {'bar': 'Grafico a Barre', 'line': 'Grafico a Linee'}[x]
        )

    # Scelta della metrica
    y_axis_metric_options = {
        'Totale MC': COLUMN_NAMES['totale_mc'],
        'Lavaggi': COLUMN_NAMES['lavaggio']
    }
    y_axis_metric_name = st.sidebar.selectbox(
        "Seleziona la metrica da visualizzare:",
        options=list(y_axis_metric_options.keys())
    )
    y_axis_metric = y_axis_metric_options[y_axis_metric_name]

    # --- FILTRO ANNO ---
    anno_corrente = datetime.now().year
    year_options = sorted(df[COLUMN_NAMES['anno']].unique().tolist())
    default_year = [anno_corrente] if anno_corrente in year_options else [year_options[-1]]
    selected_years = st.sidebar.multiselect("Anno:", options=year_options, default=default_year)

    # --- FILTRO MESE ---
    month_options = df[COLUMN_NAMES['mese']].unique().tolist()
    default_months = [m for m in mesi_ordine if m in month_options]
    selected_months = st.sidebar.multiselect("Mese:", options=month_options, default=default_months)

    # --- FILTRO LAVAGGIO e Totale MC ---
    selected_lavaggio = st.sidebar.multiselect("Lavaggio:", df[COLUMN_NAMES['lavaggio']].unique().tolist())
    min_mc_val, max_mc_val = float(df[COLUMN_NAMES['totale_mc']].min()), float(df[COLUMN_NAMES['totale_mc']].max())
    mc_range = st.sidebar.slider("Totale MC:", min_mc_val, max_mc_val, [min_mc_val, max_mc_val], step=10000.0)

    # --- FILTRO DATI ---
    df_filtered = df.copy()
    if selected_months:
        df_filtered = df_filtered[df_filtered[COLUMN_NAMES['mese']].isin(selected_months)]
    if selected_years:
        df_filtered = df_filtered[df_filtered[COLUMN_NAMES['anno']].isin(selected_years)]
    if selected_lavaggio:
        df_filtered = df_filtered[df_filtered[COLUMN_NAMES['lavaggio']].isin(selected_lavaggio)]
    df_filtered = df_filtered[(df_filtered[COLUMN_NAMES['totale_mc']] >= mc_range[0]) &
                             (df_filtered[COLUMN_NAMES['totale_mc']] <= mc_range[1])]

    # Ordina mesi
    df_filtered[COLUMN_NAMES['mese']] = pd.Categorical(df_filtered[COLUMN_NAMES['mese']], categories=mesi_ordine, ordered=True)
    df_filtered = df_filtered.sort_values([COLUMN_NAMES['anno'], COLUMN_NAMES['mese']])

    if df_filtered.empty:
        st.warning("Nessun dato trovato con i filtri selezionati.")
    else:
        col_total, col_avg, col_wash = st.columns(3)
        col_total.metric("Totale MC Consumati", f"{df_filtered[COLUMN_NAMES['totale_mc']].sum():,.0f}")
        col_avg.metric("Media MC al Mese", f"{df_filtered[COLUMN_NAMES['totale_mc']].mean():,.2f}")
        col_wash.metric("Numero Totale di Lavaggi", df_filtered[COLUMN_NAMES['lavaggio']].sum())

        st.markdown("---")
        st.header(f"Consumo di {y_axis_metric_name} per Mese")

        # --- Grafico a barre o linea per mesi ---
        if chart_type == 'bar':
            fig = px.bar(df_filtered, x=COLUMN_NAMES['mese'], y=y_axis_metric,
                         color=COLUMN_NAMES['lavaggio'],
                         title=f"Consumo Totale {y_axis_metric_name} per Mese",
                         labels={y_axis_metric: f'{y_axis_metric_name}',
                                 COLUMN_NAMES['mese']: 'Mese',
                                 COLUMN_NAMES['lavaggio']:'Lavaggi'})
        else: # Grafico a linee
            df_grouped = df_filtered.groupby([COLUMN_NAMES['anno'], COLUMN_NAMES['mese']])[y_axis_metric].sum().reset_index()
            df_grouped[COLUMN_NAMES['mese']] = pd.Categorical(df_grouped[COLUMN_NAMES['mese']], categories=mesi_ordine, ordered=True)
            df_grouped = df_grouped.sort_values([COLUMN_NAMES['anno'], COLUMN_NAMES['mese']])
            df_grouped["Mese_Label"] = df_grouped[COLUMN_NAMES['mese']]
            
            fig = px.line(df_grouped, x="Mese_Label", y=y_axis_metric, color=COLUMN_NAMES['anno'],
                          title=f"Consumo Totale {y_axis_metric_name} per Mese",
                          labels={y_axis_metric: f'{y_axis_metric_name}', "Mese_Label":"Mese", COLUMN_NAMES['anno']:'Anno'})
            fig.update_traces(mode='lines+markers')
        
        st.plotly_chart(fig, use_container_width=True)

        # --- Grafico Totale MC annuale ---
        st.markdown("---")
        st.header("Consumo Totale MC per Anno")
        df_yearly = df_filtered.groupby(COLUMN_NAMES['anno'])[COLUMN_NAMES['totale_mc']].sum().reset_index()
        fig_yearly = px.line(df_yearly, x=COLUMN_NAMES['anno'], y=COLUMN_NAMES['totale_mc'],
                             title="Totale MC per Anno",
                             labels={COLUMN_NAMES['anno']:'Anno', COLUMN_NAMES['totale_mc']:'Totale MC'})
        fig_yearly.update_traces(mode='lines+markers')
        st.plotly_chart(fig_yearly, use_container_width=True)

        # --- Download ---
        with st.expander("Esporta Dati", expanded=False):
            excel_data = to_excel(df_filtered)
            st.download_button("Esporta Dati Filtrati (XLSX)", excel_data,
                               file_name="dati_osmosi_filtrati.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("---")
        st.header("Tabella Dati Filtrati")
        st.dataframe(df_filtered)

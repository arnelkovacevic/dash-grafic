import streamlit as st
import pandas as pd
import plotly.express as px
import io
import openpyxl

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

# --- Mapping mesi italiani -> numero ---
mesi_map = {
    "Gennaio": 1, "Febbraio": 2, "Marzo": 3, "Aprile": 4,
    "Maggio": 5, "Giugno": 6, "Luglio": 7, "Agosto": 8,
    "Settembre": 9, "Ottobre": 10, "Novembre": 11, "Dicembre": 12
}

# --- Funzione caricamento dati ---
@st.cache_data
def load_data(file_source):
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

    # Filtri
    selected_months = st.sidebar.multiselect("Mese:", df[COLUMN_NAMES['mese']].unique().tolist())
    selected_years = st.sidebar.multiselect("Anno:", df[COLUMN_NAMES['anno']].unique().tolist())
    selected_lavaggio = st.sidebar.multiselect("Lavaggio:", df[COLUMN_NAMES['lavaggio']].unique().tolist())
    min_mc_val, max_mc_val = float(df[COLUMN_NAMES['totale_mc']].min()), float(df[COLUMN_NAMES['totale_mc']].max())
    mc_range = st.sidebar.slider("Totale MC:", min_mc_val, max_mc_val, [min_mc_val, max_mc_val], step=10000.0)

    # Filtra dati
    df_filtered = df.copy()
    if selected_months:
        df_filtered = df_filtered[df_filtered[COLUMN_NAMES['mese']].isin(selected_months)]
    if selected_years:
        df_filtered = df_filtered[df_filtered[COLUMN_NAMES['anno']].isin(selected_years)]
    if selected_lavaggio:
        df_filtered = df_filtered[df_filtered[COLUMN_NAMES['lavaggio']].isin(selected_lavaggio)]
    df_filtered = df_filtered[(df_filtered[COLUMN_NAMES['totale_mc']] >= mc_range[0]) &
                              (df_filtered[COLUMN_NAMES['totale_mc']] <= mc_range[1])]

    if df_filtered.empty:
        st.warning("Nessun dato trovato con i filtri selezionati.")
    else:
        col_total, col_avg, col_wash = st.columns(3)
        col_total.metric("Totale MC Consumati", f"{df_filtered[COLUMN_NAMES['totale_mc']].sum():,}")
        col_avg.metric("Media MC al Mese", f"{df_filtered[COLUMN_NAMES['totale_mc']].mean():,.2f}")
        col_wash.metric("Numero Totale di Lavaggi", df_filtered[COLUMN_NAMES['lavaggio']].sum())

        st.markdown("---")
        st.header("Consumo di MC per Mese")

        if chart_type == 'bar':
            fig = px.bar(df_filtered, x=COLUMN_NAMES['mese'], y=COLUMN_NAMES['totale_mc'],
                         color=df_filtered[COLUMN_NAMES['lavaggio']].astype(str),
                         title="Consumo Totale MC per Mese",
                         labels={COLUMN_NAMES['totale_mc']: 'Totale MC', COLUMN_NAMES['mese']: 'Mese'})
        else:  # linee
            df_grouped_mc = df_filtered.groupby([COLUMN_NAMES['anno'], COLUMN_NAMES['mese']])[COLUMN_NAMES['totale_mc']].sum().reset_index()
            df_grouped_mc["Mese_Num"] = df_grouped_mc[COLUMN_NAMES['mese']].map(mesi_map)
            df_grouped_mc = df_grouped_mc.sort_values([COLUMN_NAMES['anno'], "Mese_Num"])
            df_grouped_mc["Mese_Label"] = df_grouped_mc[COLUMN_NAMES['mese']]
            fig = px.line(df_grouped_mc, x="Mese_Label", y=COLUMN_NAMES['totale_mc'],
                          title="Consumo Totale MC per Mese",
                          labels={COLUMN_NAMES['totale_mc']:'Totale MC', "Mese_Label":"Mese"})
            fig.update_traces(mode='lines+markers')

        st.plotly_chart(fig, use_container_width=True)

        # --- Lavaggi ---
        if chart_type == 'bar':
            fig_lavaggio = px.bar(df_filtered, x=COLUMN_NAMES['mese'], y=COLUMN_NAMES['lavaggio'],
                                  color=df_filtered[COLUMN_NAMES['lavaggio']].astype(str),
                                  title="Numero di Lavaggi per Mese",
                                  labels={COLUMN_NAMES['lavaggio']: 'Lavaggio', COLUMN_NAMES['mese']: 'Mese'})
        else:
            df_grouped_lavaggio = df_filtered.groupby([COLUMN_NAMES['anno'], COLUMN_NAMES['mese']])[COLUMN_NAMES['lavaggio']].sum().reset_index()
            df_grouped_lavaggio["Mese_Num"] = df_grouped_lavaggio[COLUMN_NAMES['mese']].map(mesi_map)
            df_grouped_lavaggio = df_grouped_lavaggio.sort_values([COLUMN_NAMES['anno'], "Mese_Num"])
            df_grouped_lavaggio["Mese_Label"] = df_grouped_lavaggio[COLUMN_NAMES['mese']]
            fig_lavaggio = px.line(df_grouped_lavaggio, x="Mese_Label", y=COLUMN_NAMES['lavaggio'],
                                   title="Numero di Lavaggi per Mese",
                                   labels={COLUMN_NAMES['lavaggio']:'Lavaggio', "Mese_Label":"Mese"})
            fig_lavaggio.update_traces(mode='lines+markers')

        st.plotly_chart(fig_lavaggio, use_container_width=True)

        # --- Download ---
        with st.expander("Esporta Dati", expanded=False):
            excel_data = to_excel(df_filtered)
            st.download_button("Esporta Dati Filtrati (XLSX)", excel_data,
                               file_name="dati_osmosi_filtrati.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("---")
        st.header("Tabella Dati Filtrati")
        st.dataframe(df_filtered.drop(columns='Anno-Mese', errors='ignore'))

import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, dash_table, no_update
import base64
import io
import os
import shutil

# -------------------- 1. Inizializzazione Dati e Cache --------------------
# Questo dizionario contiene un segnaposto per il dataframe.
# Caricheremo i dati da un file caricato dall'utente.
DATA = {'df': pd.DataFrame(), 'filename': None}

# Definisci i nomi delle colonne per chiarezza e gestione degli errori
COLUMN_NAMES = {
    'date_time': 'Time',
    'sample_id': 'Sample ID',
    'test_name': 'Test Name',
    'result': 'Result',
    'date': 'Date',
    'user_id': 'User ID',
    'abs': 'ABS'
}

# -------------------- 2. Creazione dell'App Dash --------------------
# Usiamo Bootstrap per un migliore stile e design responsivo
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Dashboard Avanzata Qualità Acqua"

# -------------------- 3. Layout dell'App --------------------
# Il layout è progettato utilizzando un Container Bootstrap per una corretta spaziatura
app.layout = dbc.Container([
    html.H2("Dashboard di Test della Qualità dell'Acqua", className="my-4 text-center"),

    # Componente per il caricamento del file
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Trascina e rilascia o ',
            html.A('Seleziona un file')
        ]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed',
            'borderRadius': '5px', 'textAlign': 'center', 'marginBottom': '20px'
        },
        multiple=False
    ),

    # Contenuto principale della dashboard, nascosto fino al caricamento dei dati
    html.Div(id='dashboard-content', style={'display': 'none'}, children=[
        dbc.Row([
            # Colonna sinistra per filtri e schede riassuntive
            dbc.Col([
                # Schede riassuntive
                dbc.CardGroup([
                    dbc.Card(
                        dbc.CardBody([
                            html.H5("Campioni Totali", className="card-title"),
                            html.P(id="total-samples-card", className="card-text")
                        ]),
                        color="primary", inverse=True
                    ),
                    dbc.Card(
                        dbc.CardBody([
                            html.H5("Risultato Medio", className="card-title"),
                            html.P(id="avg-result-card", className="card-text")
                        ]),
                        color="success", inverse=True
                    ),
                    dbc.Card(
                        dbc.CardBody([
                            html.H5("Test Totali", className="card-title"),
                            html.P(id="total-tests-card", className="card-text")
                        ]),
                        color="info", inverse=True
                    ),
                ], className="mb-4"),

                # Sezione filtri
                html.Label("Seleziona Intervallo di Date:", className="mt-2"),
                dcc.DatePickerRange(
                    id='date-picker',
                    display_format='YYYY-MM-DD'
                ),

                html.Label("Seleziona ID Operatore:", className="mt-4"),
                dcc.Dropdown(id='operator-dropdown', multi=True, placeholder="Lascia vuoto per tutti gli operatori"),

                html.Label("Seleziona ID Campione:", className="mt-4"),
                dcc.Dropdown(id='sample-dropdown', multi=True),

                html.Label("Seleziona Nomi Test:", className="mt-4"),
                dcc.Dropdown(id='test-dropdown', multi=True),

                html.Label("Filtra per Valore Risultato:", className="mt-4"),
                dcc.RangeSlider(id='results-slider', min=0, max=100, step=0.1, value=[0, 100],
                                marks=None, tooltip={"placement": "bottom", "always_visible": True}),

                html.Label("Seleziona Tipo di Grafico:", className="mt-4"),
                dcc.Dropdown(
                    id='chart-type',
                    options=[
                        {'label': 'Grafico a Dispersione', 'value': 'scatter'},
                        {'label': 'Grafico a Linee', 'value': 'line'},
                        {'label': 'Box Plot', 'value': 'box'},
                        {'label': 'Istogramma', 'value': 'histogram'},
                        {'label': 'Istogramma di Densità', 'value': 'density_histogram'},
                        {'label': 'Matrice di Correlazione', 'value': 'scatter_matrix'}
                    ],
                    value='scatter'
                ),
            ], md=4, className="me-4"),

            # Colonna destra per il grafico e la tabella dati
            dbc.Col([
                dcc.Loading(
                    id="loading-graph",
                    type="default",
                    children=dcc.Graph(id='results-graph', style={'height': '600px'})
                ),
                html.Hr(className="my-4"),
                dbc.Row([
                    dbc.Col(html.H4("Tabella Dati Filtrati", className="mb-3"), width=6),
                    dbc.Col(
                        dbc.Button("Esporta Dati Filtrati", id="export-button",
                                   color="success", className="ms-auto"),
                        width=6, className="d-flex justify-content-end align-items-center"
                    )
                ]),
                dash_table.DataTable(
                    id='results-table',
                    page_action="native",
                    page_size=15,
                    style_table={'overflowX': 'auto'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                    style_cell={'textAlign': 'left', 'padding': '10px'}
                ),
                dcc.Download(id="download-dataframe-csv"),
                dcc.Store(id='filtered-data-store')
            ], md=7)
        ], className="mt-4")
    ])
], fluid=True)

# -------------------- 4. Callback --------------------

# Callback per gestire il caricamento del file e inizializzare i componenti della dashboard
@app.callback(
    Output('dashboard-content', 'style'),
    Output('date-picker', 'min_date_allowed'),
    Output('date-picker', 'max_date_allowed'),
    Output('date-picker', 'start_date'),
    Output('date-picker', 'end_date'),
    Output('operator-dropdown', 'options'),
    Output('operator-dropdown', 'value'),
    Output('sample-dropdown', 'options'),
    Output('sample-dropdown', 'value'),
    Output('test-dropdown', 'options'),
    Output('test-dropdown', 'value'),
    Output('results-slider', 'min'),
    Output('results-slider', 'max'),
    Output('results-slider', 'value'),
    Output('upload-data', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def update_layout(contents, filename):
    if not contents:
        return (
            {'display': 'none'}, None, None, None, None, [], None, [], [], [], [], None, None, None,
            html.Div(['Trascina e rilascia o ', html.A('Seleziona un file')])
        )

    content_type, content_string = contents.split(',')
    
    try:
        decoded = base64.b64decode(content_string)
        if 'xls' in filename or 'xlsx' in filename:
            df = pd.read_excel(io.BytesIO(decoded))
        elif 'csv' in filename:
            df = pd.read_csv(io.BytesIO(decoded))
        else:
            raise Exception('Tipo di file non supportato. Carica un file .csv o .xlsx.')

        # Pulizia e preparazione dei dati
        df[COLUMN_NAMES['date_time']] = pd.to_datetime(df[COLUMN_NAMES['date_time']], errors='coerce')
        df = df[df[COLUMN_NAMES['date_time']].notna()]
        df[COLUMN_NAMES['date']] = df[COLUMN_NAMES['date_time']].dt.floor('D')
        
        # Archivia il dataframe elaborato per altre callback
        DATA['df'] = df
        DATA['filename'] = filename

        operator_options = [{'label': o, 'value': o} for o in df[COLUMN_NAMES['user_id']].unique()]
        sample_options = [{'label': s, 'value': s} for s in df[COLUMN_NAMES['sample_id']].unique()]
        test_options = [{'label': t, 'value': t} for t in df[COLUMN_NAMES['test_name']].unique()]
        
        min_result = df[COLUMN_NAMES['result']].min()
        max_result = df[COLUMN_NAMES['result']].max()
        
        return (
            {'display': 'block'},
            df[COLUMN_NAMES['date']].min(),
            df[COLUMN_NAMES['date']].max(),
            df[COLUMN_NAMES['date']].min(),
            df[COLUMN_NAMES['date']].max(),
            operator_options, None,
            sample_options,
            [sample_options[0]['value']] if sample_options else [],
            test_options,
            [test_options[0]['value']] if test_options else [],
            min_result, max_result, [min_result, max_result],
            html.Div([f'File caricato con successo: {filename}'])
        )

    except Exception as e:
        # Mostra un messaggio di errore se qualcosa va storto
        return (
            {'display': 'none'},
            None, None, None, None, [], None, [], [], [], [], None, None, None,
            html.Div([f'Errore: {e}'], style={'color': 'red'})
        )

# Callback per disabilitare i dropdown Campione e Test se è selezionato un Operatore
@app.callback(
    Output('sample-dropdown', 'disabled'),
    Output('test-dropdown', 'disabled'),
    Input('operator-dropdown', 'value')
)
def disable_dropdowns(operator_value):
    # Disabilita i dropdown se viene selezionato almeno un operatore
    if operator_value:
        return True, True
    return False, False


# Callback per aggiornare le schede riassuntive, il grafico e la tabella dati
@app.callback(
    Output('results-graph', 'figure'),
    Output('results-table', 'data'),
    Output('total-samples-card', 'children'),
    Output('avg-result-card', 'children'),
    Output('total-tests-card', 'children'),
    Output('filtered-data-store', 'data'),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date'),
    Input('sample-dropdown', 'value'),
    Input('test-dropdown', 'value'),
    Input('operator-dropdown', 'value'),
    Input('results-slider', 'value'),
    Input('chart-type', 'value')
)
def update_dashboard_content(start_date, end_date, samples, tests, operators, results_range, chart_type):
    # Usa il dataframe archiviato globalmente
    df = DATA['df']
    if df.empty:
        return {}, [], "0", "0", "0", no_update

    # Filtra i dati in base alle selezioni dell'utente
    df_filtered = df[
        (df[COLUMN_NAMES['date']] >= pd.to_datetime(start_date)) &
        (df[COLUMN_NAMES['date']] <= pd.to_datetime(end_date)) &
        (df[COLUMN_NAMES['result']] >= results_range[0]) &
        (df[COLUMN_NAMES['result']] <= results_range[1])
    ].copy()

    # Applica i filtri specifici in base alle selezioni
    if operators:
        df_filtered = df_filtered[df_filtered[COLUMN_NAMES['user_id']].isin(operators)]
    elif samples and tests:
        df_filtered = df_filtered[
            df_filtered[COLUMN_NAMES['sample_id']].isin(samples) &
            df_filtered[COLUMN_NAMES['test_name']].isin(tests)
        ]
    
    # Gestisci il caso in cui il dataframe filtrato sia vuoto
    if df_filtered.empty:
        return {}, [], "0", "0", "0", df_filtered.to_json(date_format='iso', orient='split')

    # --- Crea le metriche di riepilogo ---
    total_samples = len(df_filtered[COLUMN_NAMES['sample_id']].unique()) if not df_filtered.empty else 0
    avg_result = f"{df_filtered[COLUMN_NAMES['result']].mean():.2f}" if not df_filtered.empty else "0"
    total_tests = len(df_filtered) if not df_filtered.empty else 0

    # --- Crea la figura Plotly ---
    # Ora includiamo tutte le colonne nel tooltip del grafico
    hover_cols = df_filtered.columns.tolist()
    
    fig = {}
    if chart_type == 'scatter':
        fig = px.scatter(df_filtered, x=COLUMN_NAMES['date'], y=COLUMN_NAMES['result'], color=COLUMN_NAMES['sample_id'],
                         hover_data=hover_cols, title="Grafico a Dispersione dei Risultati dei Test")
    elif chart_type == 'line':
        fig = px.line(df_filtered, x=COLUMN_NAMES['date'], y=COLUMN_NAMES['result'], color=COLUMN_NAMES['sample_id'],
                      hover_data=hover_cols, title="Grafico a Linee dei Risultati dei Test")
        fig.update_traces(mode='lines+markers')
    elif chart_type == 'box':
        fig = px.box(df_filtered, x=COLUMN_NAMES['sample_id'], y=COLUMN_NAMES['result'], color=COLUMN_NAMES['test_name'],
                     hover_data=hover_cols, title="Box Plot dei Risultati per ID Campione")
    elif chart_type == 'histogram':
        fig = px.histogram(df_filtered, x=COLUMN_NAMES['date'], y=COLUMN_NAMES['result'], color=COLUMN_NAMES['sample_id'],
                           title="Istogramma dei Risultati dei Test",
                           barmode="group")
        fig.update_traces(hovertemplate='<b>Data:</b> %{x|%Y-%m-%d}<br><b>Risultato:</b> %{y}<br><b>ID Campione:</b> %{color}<extra></extra>')
    elif chart_type == 'density_histogram':
        fig = px.histogram(df_filtered, x=COLUMN_NAMES['result'], color=COLUMN_NAMES['test_name'],
                           nbins=20, histnorm='probability density', marginal='rug',
                           title='Istogramma di Densità dei Risultati')
    elif chart_type == 'scatter_matrix':
        fig = px.scatter_matrix(df_filtered, dimensions=[COLUMN_NAMES['result'], COLUMN_NAMES['abs']],
                                color=COLUMN_NAMES['test_name'],
                                title="Matrice di Correlazione tra Risultato e ABS")
        fig.update_traces(diagonal_visible=False)


    # Aggiorna il layout del grafico per un aspetto pulito e professionale
    if chart_type in ['scatter', 'line', 'box', 'histogram']:
        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="Risultato",
            legend_title="ID Campione",
            hovermode='closest',
            template='plotly_white'
        )
    elif chart_type == 'density_histogram':
        fig.update_layout(
            xaxis_title="Risultato",
            yaxis_title="Densità",
            template='plotly_white'
        )
    
    # --- Prepara i dati per la tabella Dash ---
    # Selezioniamo e rinominiamo le colonne per una visualizzazione più pulita della tabella
    df_table_data = df_filtered.rename(columns={
        COLUMN_NAMES['date_time']: 'Ora',
        COLUMN_NAMES['sample_id']: 'ID Campione',
        COLUMN_NAMES['test_name']: 'Nome Test',
        COLUMN_NAMES['result']: 'Risultato',
        COLUMN_NAMES['user_id']: 'ID Operatore',
        COLUMN_NAMES['abs']: 'ABS'
    })
    
    # Converti il dataframe in un elenco di dizionari per la tabella
    table_data = df_table_data.to_dict('records')

    # Restituisci tutti i componenti aggiornati
    return fig, table_data, str(total_samples), str(avg_result), str(total_tests), df_filtered.to_json(date_format='iso', orient='split')

# Callback per scaricare il dataframe filtrato
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("export-button", "n_clicks"),
    State("filtered-data-store", "data"),
    prevent_initial_call=True
)
def download_filtered_data(n_clicks, json_data):
    if not json_data:
        return no_update
    
    df_filtered = pd.read_json(json_data, orient='split')
    return dcc.send_data_frame(df_filtered.to_csv, "dati_filtrati.csv")


# --- 5. Esegui l'app ---
if __name__ == '__main__':
    app.run(debug=True)

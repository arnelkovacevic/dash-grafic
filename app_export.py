import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, dash_table, no_update
import base64
import io
import os
import shutil
# Import ThemeSwitchAIO for light/dark mode functionality
from dash_bootstrap_templates import ThemeSwitchAIO

# -------------------- 1. Data and Cache Initialization --------------------
# This dictionary holds a placeholder for the dataframe.
# We will load the data from a file uploaded by the user.
DATA = {'df': pd.DataFrame(), 'filename': None}

# Define column names for clarity and error handling
COLUMN_NAMES = {
    'date_time': 'Time',
    'sample_id': 'Sample ID',
    'test_name': 'Test Name',
    'result': 'Result',
    'date': 'Date',
    'user_id': 'User ID',
    'abs': 'ABS'
}

# -------------------- 2. Dash App Creation --------------------
# Define the two themes for the switch
url_theme1 = dbc.themes.BOOTSTRAP
url_theme2 = dbc.themes.CYBORG

# Use the two themes in the external_stylesheets list
app = Dash(__name__, external_stylesheets=[url_theme1])
app.title = "Dashboard Avanzata Qualità Acqua"

# -------------------- 3. App Layout --------------------
# The layout is designed using a Bootstrap Container for proper spacing
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(
            # Add a clickable logo that will trigger the info modal
            html.Div(
                # Reduced logo height
                html.Img(src='assets/logo.jpg', style={'height': '50px', 'display': 'block', 'margin': '0 auto'}),
                id='logo-button',
                style={'cursor': 'pointer'},
                className="my-4 text-center"
            ), width={"size": 10, "offset": 1}
        ),
        dbc.Col(
            # Add the theme switch component
            ThemeSwitchAIO(aio_id="theme-switch", themes=[url_theme1, url_theme2]),
            width={"size": 1, "offset": 0},
            className="d-flex align-items-center justify-content-end"
        )
    ]),
    html.H2("Dashboard di Test della Qualità dell'Acqua", className="my-4 text-center"),

    # File upload component
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

    # Main dashboard content, hidden until data is uploaded
    html.Div(id='dashboard-content', style={'display': 'none'}, children=[
        dbc.Row([
            # Left column for filters and summary cards
            dbc.Col([
                # Summary cards
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

                # Filter section
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
                    # Set the default value to 'line'
                    value='line'
                ),
            ], md=4, className="me-4"),

            # Right column for the graph and data table
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
    ]),

    # Modal for app information
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Informazioni App")),
            dbc.ModalBody([
                html.P("Nome: Dash-Viewer"),
                html.P("Linguaggio: Python"),
                html.P("Framework: Flask"),
                html.P("Deployed: Heroku"),
                html.P([html.B("Sviluppatore:"), " Arnel Kovacevic"]),
                html.P(["Società: ", html.A("Orizon-aix.com", href="https://Orizon-aix.com", target="_blank")]),
                # Updated the copyright information
                html.P("Versione: 1.2.1"),
                html.P("Anno: 2025"),
                html.P("Copyright © 2025 Orizon-aix. Tutti i diritti riservati."),
            ]),
            dbc.ModalFooter(
                dbc.Button("Chiudi", id="close-modal", className="ms-auto")
            ),
        ],
        id="info-modal",
        is_open=False,
    ),

], fluid=True, className="dbc")


# -------------------- 4. Callbacks --------------------

# Callback to toggle the info modal
@app.callback(
    Output("info-modal", "is_open"),
    [Input("logo-button", "n_clicks"), Input("close-modal", "n_clicks")],
    [State("info-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_modal(n_clicks_logo, n_clicks_close, is_open):
    if n_clicks_logo or n_clicks_close:
        return not is_open
    return is_open

# Callback to handle file upload and initialize dashboard components
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

        # Data cleaning and preparation
        df[COLUMN_NAMES['date_time']] = pd.to_datetime(df[COLUMN_NAMES['date_time']], errors='coerce')
        df = df[df[COLUMN_NAMES['date_time']].notna()]
        df[COLUMN_NAMES['date']] = df[COLUMN_NAMES['date_time']].dt.floor('D')
        
        # Store the processed dataframe for other callbacks
        DATA['df'] = df
        DATA['filename'] = filename

        operator_options = [{'label': o, 'value': o} for o in df[COLUMN_NAMES['user_id']].unique()]
        sample_options = [{'label': s, 'value': s} for s in df[COLUMN_NAMES['sample_id']].unique()]
        test_options = [{'label': t, 'value': t} for t in df[COLUMN_NAMES['test_name']].unique()]
        
        min_result = df[COLUMN_NAMES['result']].min()
        max_result = df[COLUMN_NAMES['result']].max()
        
        # Set all samples and tests as default selected
        default_samples = [s['value'] for s in sample_options]
        default_tests = [t['value'] for t in test_options]

        return (
            {'display': 'block'},
            df[COLUMN_NAMES['date']].min(),
            df[COLUMN_NAMES['date']].max(),
            df[COLUMN_NAMES['date']].min(),
            df[COLUMN_NAMES['date']].max(),
            operator_options, None,
            sample_options,
            default_samples, # Set all samples as default
            test_options,
            default_tests, # Set all tests as default
            min_result, max_result, [min_result, max_result],
            html.Div([f'File caricato con successo: {filename}'])
        )

    except Exception as e:
        # Show an error message if something goes wrong
        return (
            {'display': 'none'},
            None, None, None, None, [], None, [], [], [], [], None, None, None,
            html.Div([f'Errore: {e}'], style={'color': 'red'})
        )

# Callback to disable Sample and Test dropdowns if an Operator is selected
@app.callback(
    Output('sample-dropdown', 'disabled'),
    Output('test-dropdown', 'disabled'),
    Input('operator-dropdown', 'value')
)
def disable_dropdowns(operator_value):
    # Disable dropdowns if at least one operator is selected
    if operator_value:
        return True, True
    return False, False


# Callback to update summary cards, graph, and data table
# The template input is from the ThemeSwitchAIO component
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
    Input('chart-type', 'value'),
    Input(ThemeSwitchAIO.ids.switch("theme-switch"), "value")
)
def update_dashboard_content(start_date, end_date, samples, tests, operators, results_range, chart_type, is_light_theme):
    # Use the globally stored dataframe
    df = DATA['df']
    if df.empty:
        return {}, [], "0", "0", "0", no_update

    # Determine the Plotly template based on the theme switch state
    template = "bootstrap" if is_light_theme else "cyborg"

    # Filter data based on user selections
    df_filtered = df[
        (df[COLUMN_NAMES['date']] >= pd.to_datetime(start_date)) &
        (df[COLUMN_NAMES['date']] <= pd.to_datetime(end_date)) &
        (df[COLUMN_NAMES['result']] >= results_range[0]) &
        (df[COLUMN_NAMES['result']] <= results_range[1])
    ].copy()

    # Apply specific filters based on selections
    if operators:
        df_filtered = df_filtered[df_filtered[COLUMN_NAMES['user_id']].isin(operators)]
    elif samples and tests:
        df_filtered = df_filtered[
            df_filtered[COLUMN_NAMES['sample_id']].isin(samples) &
            df_filtered[COLUMN_NAMES['test_name']].isin(tests)
        ]
    
    # Handle case where the filtered dataframe is empty
    if df_filtered.empty:
        return {}, [], "0", "0", "0", df_filtered.to_json(date_format='iso', orient='split')

    # --- Create summary metrics ---
    total_samples = len(df_filtered[COLUMN_NAMES['sample_id']].unique()) if not df_filtered.empty else 0
    avg_result = f"{df_filtered[COLUMN_NAMES['result']].mean():.2f}" if not df_filtered.empty else "0"
    total_tests = len(df_filtered) if not df_filtered.empty else 0

    # --- Create the Plotly figure ---
    # Now we include all columns in the graph's tooltip
    hover_cols = df_filtered.columns.tolist()
    
    fig = {}
    if chart_type == 'scatter':
        fig = px.scatter(df_filtered, x=COLUMN_NAMES['date'], y=COLUMN_NAMES['result'], color=COLUMN_NAMES['sample_id'],
                         hover_data=hover_cols, title="Grafico a Dispersione dei Risultati dei Test", template=template)
    elif chart_type == 'line':
        fig = px.line(df_filtered, x=COLUMN_NAMES['date'], y=COLUMN_NAMES['result'], color=COLUMN_NAMES['sample_id'],
                      hover_data=hover_cols, title="Grafico a Linee dei Risultati dei Test", template=template)
        fig.update_traces(mode='lines+markers')
    elif chart_type == 'box':
        fig = px.box(df_filtered, x=COLUMN_NAMES['sample_id'], y=COLUMN_NAMES['result'], color=COLUMN_NAMES['test_name'],
                     hover_data=hover_cols, title="Box Plot dei Risultati per ID Campione", template=template)
    elif chart_type == 'histogram':
        fig = px.histogram(df_filtered, x=COLUMN_NAMES['date'], y=COLUMN_NAMES['result'], color=COLUMN_NAMES['sample_id'],
                           title="Istogramma dei Risultati dei Test",
                           barmode="group", template=template)
        fig.update_traces(hovertemplate='<b>Data:</b> %{x|%Y-%m-%d}<br><b>Risultato:</b> %{y}<br><b>ID Campione:</b> %{color}<extra></extra>')
    elif chart_type == 'density_histogram':
        fig = px.histogram(df_filtered, x=COLUMN_NAMES['result'], color=COLUMN_NAMES['test_name'],
                           nbins=20, histnorm='probability density', marginal='rug',
                           title='Istogramma di Densità dei Risultati', template=template)
    elif chart_type == 'scatter_matrix':
        fig = px.scatter_matrix(df_filtered, dimensions=[COLUMN_NAMES['result'], COLUMN_NAMES['abs']],
                                color=COLUMN_NAMES['test_name'],
                                title="Matrice di Correlazione tra Risultato e ABS", template=template)
        fig.update_traces(diagonal_visible=False)


    # Update graph layout for a clean, professional look
    if chart_type in ['scatter', 'line', 'box', 'histogram']:
        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="Risultato",
            legend_title="ID Campione",
            hovermode='closest',
            template=template
        )
    elif chart_type == 'density_histogram':
        fig.update_layout(
            xaxis_title="Risultato",
            yaxis_title="Densità",
            template=template
        )
    
    # --- Prepare data for the Dash table ---
    # Select and rename columns for a cleaner table view
    df_table_data = df_filtered.rename(columns={
        COLUMN_NAMES['date_time']: 'Ora',
        COLUMN_NAMES['sample_id']: 'ID Campione',
        COLUMN_NAMES['test_name']: 'Nome Test',
        COLUMN_NAMES['result']: 'Risultato',
        COLUMN_NAMES['user_id']: 'ID Operatore',
        COLUMN_NAMES['abs']: 'ABS'
    })
    
    # Convert dataframe to a list of dictionaries for the table
    table_data = df_table_data.to_dict('records')

    # Return all updated components
    return fig, table_data, str(total_samples), str(avg_result), str(total_tests), df_filtered.to_json(date_format='iso', orient='split')

# Callback to download the filtered dataframe
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


# --- 5. Run the app ---
if __name__ == '__main__':
    app.run(debug=True)

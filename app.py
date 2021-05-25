# standard modules
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

import pandas as pd
from influxdb import DataFrameClient

# custom module
from anomaly_detection import ADetector

host, port = '127.0.0.1', '8086'
dataset_name = 'Reaction Wheel Temperature'
db_name = 'sensors_data' 
retention_policie='rp_temp'
field_name = 'downsampled_temp'


def get_data(client, retention_policie, field_name):
    df = client.query(f'SELECT * FROM "{retention_policie}"."{field_name}"')[field_name]
    df.index = df.index.tz_localize(None)
    df.reset_index(inplace=True)
    df.columns = ['ds', 'y']
    return df

# init connection 
myclient = DataFrameClient(host=host, port=port, database=db_name)
dataframe = get_data(client=myclient, retention_policie=retention_policie, field_name=field_name)

# create anomaly detector
detector = ADetector(name='TRW1MT (C)')
params = ['D'] #['Y']
detector.update_model(df=dataframe, params=params)

# Start the app
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = 'Anomaly Detection Dashboard'
app.layout = html.Section([
    # banner title
    html.Div(className='banner_tsa', children=[
        html.Header(html.H1(className='titel_tsa', children=[
            'On-line', html.Span('Anomaly Detection', className='title_st'),
        ]))
    ]),

    html.Div(className='create_container', children=[
        # options
        html.Div(className='three columns card-display', children=[
            html.P('Model Controls', className='label-control'), 

            html.P('Model Parameters', className='label'),
            dcc.Checklist(
                id='model_parameters_checklist',
                options=[{
                    'label':interval,
                    'value':interval[0]
                } for interval in ['Daily Seasonality', 'Weekly Seasonality', 'Yearly Seasonality']],
                value=params,
                className='model-parameters-checklist',
                style={'color':'white', 'margin-left':'20px'}
            ),

            html.P('# of Days Forecasted', className='label'),
            dcc.Slider(
                id='forecast_days_slider',
                marks={str(days):str(days) for days in [7, 30, 90, 180, 365]},
                value=7,
                included=True,
                min=7, 
                max=365, 
                step=1, 
                updatemode='drag',
                className='forecast-days-slider'
            ),

            html.P('Model Updating', className='label'),
            dcc.RadioItems(
                id='updating_interval',
                options=[{'label':interval, 'value':days} for interval, days in zip(
                    ['Weekly', 'Monthly', 'Yearly'], 
                    [7, 30, 365]
                )],
                value=7,
                style={'color':'white', 'margin-left':'20px'},
                className='updating-interval'
            ),
        ]),

        # streaming
        html.Div(className='ten columns card-display', children=[
            dcc.Interval(
                id='update_chart', 
                interval=10000, 
                n_intervals=0,
            ),
            dcc.Graph(
                id='timeseries', 
                config=dict(displayModeBar='hover'), 
                # animate = True,
                figure=detector.stream_anomaly_plot(series_name=dataset_name),
            ),
        ]),
    ]),

    html.Div(className='create_container', children=[
        # histogram
        html.Div(className='four columns card-display', children=[#animate=True
            dcc.Graph(
                id='histogram', 
                config=dict(displayModeBar='hover'), 
                figure=detector.hist_plot()
            ),
        ]),
        # model-components
        html.Div(className='five columns card-display', children=[
            dcc.Graph(
                id='seasonal_components', 
                config=dict(displayModeBar='hover'), 
                figure=detector.seasonal_components_plot(),
            ),
        ]),
        # error-barchart
        html.Div(className='four columns card-display four columns', children=[
            dcc.Graph(
                id='error-barchart', 
                config=dict(displayModeBar='hover'), 
                figure=detector.metric_plot(),
            ),
        ]),
    ]),
])


@app.callback(
    Output('timeseries', 'figure'),
    Output('histogram', 'figure'),
    Output('seasonal_components', 'figure'),
    Output('error-barchart', 'figure'),
    
    Input('update_chart', 'n_intervals'),
    Input('forecast_days_slider', 'value'),
    Input('model_parameters_checklist', 'value'),
    Input('updating_interval', 'value'),
)
def update_graphs(index, period, params, interval):
    dataframe = get_data(client=myclient, retention_policie=retention_policie, field_name=field_name)

    # update model
    days = (dataframe.ds.iloc[-1] - detector.model_init_date).days
    if days >= interval or detector.params != params:
        detector.update_model(df=dataframe, params=params)
        detector.model_init_date = dataframe.ds.iloc[-1]

    # forecast
    if (detector.period != period) or (index >= len(detector.dataframe_forecast)):
        detector.future_dataframe(period=period)

    # update streaming data
    detector.predict_dataframe(series=dataframe)

    return [detector.stream_anomaly_plot(series_name=dataset_name), detector.hist_plot(), 
            detector.seasonal_components_plot(), detector.metric_plot()]


if __name__=='__main__':
    app.run_server(host='127.0.0.1', port='8050', debug=False)



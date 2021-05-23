# standard modules
import pandas as pd

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

# custom module
from anomaly_detection import ADetector

file_name, dataset_name = './data/TRW1MT.csv', 'Reaction Wheel Temperature'
def load_data(root, parse_time_by=0):
    series = pd.read_csv(root, parse_dates=[parse_time_by], index_col=[parse_time_by]).asfreq(freq='5T')
    series = series.iloc[:, :1].resample(rule='D').mean().interpolate(method='linear')
    series.reset_index(inplace=True)
    series.columns = ['ds', 'y']
    return series
sub_data = lambda df, index: df.iloc[0:index, :]

# load dataset 
data_train = load_data(root=file_name)
sample = 40# 1600
data_updated = sub_data(df=data_train, index=sample)

# create anomaly detector
detector = ADetector(name='TRW1MT (C)')
params = ['W'] #['Y']
detector.update_model(df=data_updated, params=params)

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
                value=30,
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
                n_intervals=sample+1,
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
            dcc.Graph(id='histogram', config=dict(displayModeBar='hover'), figure=detector.hist_plot()),
        ]),
        # model-components
        html.Div(className='five columns card-display', children=[
            dcc.Graph(id='seasonal_components', config=dict(displayModeBar='hover'), figure=detector.seasonal_components_plot()),
        ]),
        # error-barchart
        html.Div(className='four columns card-display four columns', children=[
            dcc.Graph(id='error-barchart', config=dict(displayModeBar='hover'), figure=detector.metric_plot()),
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
    data_updated = sub_data(df=data_train, index=index)

    # update model
    days = (data_updated.ds.iloc[-1] - detector.model_init_date).days
    if days >= interval or detector.params != params:
        detector.update_model(df=data_updated, params=params)
        detector.model_init_date = data_updated.ds.iloc[-1]

    # forecast
    if (detector.period != period) or (index >= len(detector.dataframe_forecast)):
        detector.future_dataframe(period=period)

    # update streaming data
    detector.predict_dataframe(series=data_updated)

    return [detector.stream_anomaly_plot(series_name=dataset_name), detector.hist_plot(), 
            detector.seasonal_components_plot(), detector.metric_plot()]


if __name__=='__main__':
    app.run_server(host='127.0.0.1', port='8050', debug=False)
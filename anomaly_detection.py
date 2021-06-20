# data manipulation modules
import pandas as pd

# data visualization modules
import plotly.graph_objs as go
import plotly.express as px

# model and Components_plot
from fbprophet import Prophet
from fbprophet.plot import plot_components_plotly

# error metrics
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error


class ADetector(object):
    def __init__(self, name):
        self.NAME = name
        self.METRICS = {
            'MAE': mean_absolute_error,
            'R2': r2_score,
            'MSE': mean_squared_error,
            'MedAE': median_absolute_error,
        }
        self.period = 30

    def update_model(self, df, params):
        self.params = params
        self.model_init_date = df.ds.iloc[-1]

        daily = 'D' in self.params
        weekly = 'W' in self.params
        yearly = 'Y' in self.params

        if daily or weekly or yearly:
            self.model = Prophet(
                daily_seasonality=daily,
                weekly_seasonality=weekly,
                yearly_seasonality=yearly,
            )
        else:
            self.model = Prophet()

        self.model.fit(df)
        self.future_dataframe(period=self.period)
        self.predict_dataframe(series=df)

    def future_dataframe(self, period):
        self.period = period
        data = self.model.make_future_dataframe(
            periods=self.period,
            freq='D',
            include_history=True,
        )
        self.dataframe_forecast = self.model.predict(df=data)

    def predict_dataframe(self, series):
        # get predictions and classify anomalies
        self.dataframe_predict = self.model.predict(df=series[['ds']])
        self.dataframe_predict['y'] = series['y']
        self.classify_anomaly()

    def classify_anomaly(self, stds=[2, 4, 8]):
        # populate errors
        self.dataframe_predict['residuals'] = self.dataframe_predict['y'] - \
            self.dataframe_predict['yhat']
        error = self.dataframe_predict.residuals.abs()
        mean_of_errors = error.values.mean()
        std_of_errors = error.values.std(ddof=0)

        # initialize the anomaly data with False and impact 0
        self.dataframe_predict['anomaly'] = False
        self.dataframe_predict['impact'] = 0

        for i in range(len(stds)):
            num_stds = stds[i]
            # define outliers by distance from mean of errors
            threshold = mean_of_errors + (std_of_errors * num_stds)
            # label outliers using standard deviations from the mean error
            self.dataframe_predict.at[error > threshold, 'anomaly'] = True
            self.dataframe_predict.at[error > threshold, 'impact'] = i+1

    def stream_anomaly_plot(self, series_name=''):

        normal = self.dataframe_predict[self.dataframe_predict.impact == 0]
        scatter_normal = go.Scatter(
            x=normal.ds,
            y=normal.y,
            mode='markers',
            name='Actual',
            marker=dict(color='#CCCCFF', size=4),
        )

        predicted_line = go.Scatter(
            x=self.dataframe_forecast.ds,
            y=self.dataframe_forecast.yhat,
            mode='lines',
            name='Prediction',
            line_color='RoyalBlue',
        )

        confidence_area = go.Scatter(
            x=pd.concat([
                self.dataframe_forecast.ds,
                self.dataframe_forecast.ds[::-1]
            ]),
            y=pd.concat([
                self.dataframe_forecast.yhat_upper,
                self.dataframe_forecast.yhat_lower[::-1]
            ]),
            mode='none',
            name='Confidence Interval',
            fill='toself',
            fillcolor='RoyalBlue',
            opacity=0.2,
        )

        data = [scatter_normal, predicted_line, confidence_area]
        colors = ['#F4D03F', '#F39C12', '#CB4335']
        for i in range(len(colors)):
            anomalies = self.dataframe_predict[
                self.dataframe_predict.impact == i+1
            ]
            scatter_anomaly = go.Scatter(
                x=anomalies.ds,
                y=anomalies.y,
                mode='markers',
                name=f'Actual-Anomaly-Impact {i+1}',
                marker=dict(color=colors[i], size=4)
            )
            data.append(scatter_anomaly)

        layout = go.Layout(
            hovermode='x',
            template='plotly_dark',
            showlegend=True,
            title=dict(
                text=f'{series_name} Streaming',
                font=dict(size=20),
            ),
            yaxis=dict(title=self.NAME),
            xaxis=dict(
                title='Date-Time (Day)',
                rangeselector=dict(
                    buttons=list([
                        dict(
                            count=1,
                            label='1D',
                            step='day',
                            stepmode='backward',
                        ),
                        dict(
                            count=6,
                            label='1M',
                            step='month',
                            stepmode='backward',
                        ),
                        dict(
                            count=1,
                            label='1Y',
                            step='year',
                            stepmode='backward',
                        ),
                        dict(step='all'),
                    ]),
                    font=dict(color='black'),
                ),
            ),
            legend=dict(
                orientation='h',
                xanchor='center',
                x=0.5,
                y=-0.3
            )
        )

        fig = go.Figure(data=data, layout=layout)
        return fig

    def hist_plot(self):
        fig = px.histogram(
            data_frame=self.dataframe_predict,
            x='y',
            marginal='box',
        )

        layout = go.Layout(
            template='plotly_dark',
            showlegend=False,
            title=dict(text='Histogram', font=dict(size=20)),
            yaxis=dict(title='Number of Samples'),
            margin=dict(r=10, l=10, b=10),
            xaxis=dict(title=self.NAME),
            legend=dict(
                orientation='h',
                xanchor='center',
                x=0.5,
                y=-0.2
            )
        )
        fig.update_layout(layout)
        fig.update_traces(
            marker=dict(
                color='RoyalBlue',
                opacity=0.4,
                line=dict(color='#9370db', width=1.3)
            )
        )

        return fig

    def seasonal_components_plot(self):
        fig = plot_components_plotly(self.model, self.dataframe_predict)
        fig.update_traces(line=dict(color=' RoyalBlue'))
        fig.update_layout(
            template='plotly_dark',
            title=dict(text='Seasonal Components', font=dict(size=20)),
            height=None,
            width=None,
            margin=dict(b=10, r=10, l=10),
        )
        return fig

    def error(self, metric): return metric(
        self.dataframe_predict.y,
        self.dataframe_predict.yhat
    )

    def metric_plot(self):
        metrics_results = {
            name: self.error(method)
            for name, method in self.METRICS.items()
        }

        error_df = pd.DataFrame(metrics_results, index=[0])
        error_df = error_df.melt(
            var_name='Metric',
            value_name='Error',
        )
        error_df.Error = error_df.Error.round(3)

        fig = px.bar(
            data_frame=error_df,
            x='Metric',
            y='Error',
            color='Metric',
            text='Error',
        )
        fig.update_traces(
            texttemplate='%{text}',
            textposition='outside',
        )
        fig.update_layout(
            title=dict(
                text='Error Metric Results',
                font=dict(size=20),
            ),
            template='plotly_dark',
            margin=dict(r=10, l=10, b=10),
        )
        return fig

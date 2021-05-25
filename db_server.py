# Imports
import pandas as pd
from influxdb import InfluxDBClient

def load_data(root, parse_time_by=0):
    series = pd.read_csv(root, parse_dates=[parse_time_by], index_col=[parse_time_by]).asfreq(freq='5T')
    series = series.iloc[:, :1].interpolate(method='linear')
    return series

def db_exists(client, db_name):
    for item in client.get_list_database():
        if item['name'] == db_name:
            return True
    return False

if __name__=='__main__':
    # load dataset
    file_name = './data/TRW1MT.csv'
    wheel_temp = load_data(root=file_name)

    # create a database
    host, port = '127.0.0.1', '8086'
    db_name = 'sensors_data' 
    measurement_name = 'whell_temperature'
    field_name = wheel_temp.columns[0]

    myclient = InfluxDBClient(host=host, port=port)#username=username, password=password)
    print("connection started...")
    
    # create a client
    myclient.drop_database(db_name)
    if not db_exists(client=myclient, db_name=db_name):
        myclient.create_database(db_name)

    # use database, note: client.query('use database') does not work...
    myclient.switch_database('sensors_data')

    # create retention policies: never delete a data-point, collect other data forever
    myclient.create_retention_policy(
        name='rp_temp',
        duration='INF', 
        replication='2', 
        database=db_name, 
        default=True,
    )

    # create continuous queries => downsampling in realtime
    myclient.create_continuous_query(
        name=f'{measurement_name}_cq', 
        select=f'''
            SELECT mean("{field_name}") AS "{field_name}_mean"
            INTO "rp_temp"."downsampled_temp" 
            FROM "{measurement_name}"
            GROUP BY time(1d)
        ''',
        database=db_name, 
        resample_opts='EVERY 1d',
    )

    # start measurement, write a points
    for date, temp in zip(wheel_temp.index, wheel_temp[field_name]):
        json_insert = [
            {
                'measurement': measurement_name,
                'time': date,
                'fields': {
                    field_name: temp 
                }
            } 
        ]

        # write temperature to db
        myclient.write_points(points=json_insert, retention_policy='rp_temp', batch_size=7200)
        # time.sleep(0.03)
        myclient.query(f'''
            SELECT mean("{field_name}") AS "values"
            INTO "rp_temp"."downsampled_temp" 
            FROM "{measurement_name}"
            GROUP BY time(1d), *
        ''')
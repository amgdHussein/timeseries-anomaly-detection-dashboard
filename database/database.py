from influxdb import InfluxDBClient
from .data_loader import load_data
import os


def db_exists(client, db_name):
    for item in client.get_list_database():
        if item['name'] == db_name:
            return True
    return False


def daily_sampling(client, db, measurement, field):
    # create retention policies: never delete a data-point,
    # collect other data forever
    client.create_retention_policy(
        name='rp_temp',
        duration='INF',
        replication='2',
        database=db,
        default=True,
    )

    # create continuous queries => downsampling in realtime
    client.create_continuous_query(
        name=f'{measurement}_cq',
        select=f'''
            SELECT mean("{field}") AS "{field}_mean"
            INTO "rp_temp"."downsampled_temp" 
            FROM "{measurement}"
            GROUP BY time(1d)
        ''',
        database=db_name,
        resample_opts='EVERY 1d',
    )


if __name__ == '__main__':
    # load dataset
    data_root = os.path.join('database', 'sensors')
    file_name = 'TRW1MT.csv'
    wheel_temp = load_data(root=data_root, file_name=file_name)

    # create a database
    host, port = '127.0.0.1', '8086'
    db_name = 'sensors_data'
    measurement_name = 'whell_temperature'
    field_name = wheel_temp.columns[0]

    # create a client
    #username, password
    myclient = InfluxDBClient(host=host, port=port)
    print("DB started...")

    # myclient.drop_database(db_name)
    if not db_exists(client=myclient, db_name=db_name):
        myclient.create_database(db_name)

    # note: client.query('use database') does not work...
    myclient.switch_database('sensors_data')

    daily_sampling(
        client=myclient,
        db=db_name,
        measurement=measurement_name,
        field=field_name
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
        myclient.write_points(
            points=json_insert,
            retention_policy='rp_temp',
            batch_size=7200,
        )
        myclient.query(f'''
            SELECT mean("{field_name}") AS "values"
            INTO "rp_temp"."downsampled_temp" 
            FROM "{measurement_name}"
            GROUP BY time(1d), *
        ''')

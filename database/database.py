from .data_loader import load_data
from influxdb import InfluxDBClient
from __init__ import *
import sys
sys.path.append('../')


def db_exists(client, db_name):
    for item in client.get_list_database():
        if item['name'] == db_name:
            return True
    return False


def daily_sampling(client, db, measurement, field):
    # create retention policies: never delete a data-point,
    # collect other data forever
    client.create_retention_policy(
        name=RETENTION_POLICIE,
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
            INTO "{RETENTION_POLICIE}"."{FIELD_NAME}" 
            FROM "{measurement}"
            GROUP BY time(1d)
        ''',
        database=DATABASE_NAME,
        resample_opts='EVERY 1d',
    )


if __name__ == '__main__':
    # load dataset
    wheel_temp = load_data(root=DATA_ROOT, file_name=FILE_NAME)

    # create a database
    field_name = wheel_temp.columns[0]

    # create a client
    myclient = InfluxDBClient(host=DATABASE_HOST, port=DATABASE_PORT)
    print("DB started...")

    # myclient.drop_database(DATABASE_NAME)
    if not db_exists(client=myclient, db_name=DATABASE_NAME):
        myclient.create_database(DATABASE_NAME)

    # note: client.query('use database') does not work...
    myclient.switch_database('sensors_data')

    daily_sampling(
        client=myclient,
        db=DATABASE_NAME,
        measurement=MEASUREMENT_NAME,
        field=field_name
    )

    # start measurement, write a points
    for date, temp in zip(wheel_temp.index, wheel_temp[field_name]):
        json_insert = [
            {
                'measurement': MEASUREMENT_NAME,
                'time': date,
                'fields': {
                    field_name: temp
                }
            }
        ]

        # write temperature to db
        myclient.write_points(
            points=json_insert,
            retention_policy=RETENTION_POLICIE,
            batch_size=7200,
        )
        myclient.query(f'''
            SELECT mean("{field_name}") AS "values"
            INTO "{RETENTION_POLICIE}"."{FIELD_NAME}" 
            FROM "{MEASUREMENT_NAME}"
            GROUP BY time(1d), *
        ''')

import os

DATA_ROOT = os.path.join('database', 'sensors')
DATABASE_HOST, DATABASE_PORT = '127.0.0.1', '8086'
DASH_HOST, DASH_PORT = '127.0.0.1', '8050'

DATASET_NAME = 'Reaction Wheel Temperature'
MEASUREMENT_NAME = 'whell_temperature'
DATABASE_NAME = 'sensors_data'
FILE_NAME = 'TRW1MT.csv'
RETENTION_POLICIE = 'rp_temp'
FIELD_NAME = 'downsampled_temp'
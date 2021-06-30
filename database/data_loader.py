import os
import pandas as pd


def load_data(root, file_name, parse_time_by=0):
    series = pd.read_csv(
        os.path.join(root, file_name),
        # parse time column format into default pandas time-stamp
        parse_dates=[parse_time_by],
        # set time to be the dataframe index
        index_col=[parse_time_by],
    )

    series = series.iloc[:, :1]
    # set index name = Datetime
    series.index.name = 'Datetime'
    return series


if __name__ == '__main__':
    root = './sensors/'

    # load dataset csv file
    wheel_temp = load_data(
        root=root,
        file_name='TRW1MT.csv'
    ).asfreq(freq='5T')

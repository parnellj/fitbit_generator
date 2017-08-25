from __future__ import division

import os
import fitbit
import glob
from datetime import datetime as dt, timedelta as tdelt
import numpy as np
import pandas as pd

pd.set_option('display.max_colwidth', -1)
pd.set_option('display.max_rows', 1000)

CONFIGS = os.path.join('.', 'config')
INPATH = os.path.join('.', 'inputs')
OUTPATH = os.path.join('.', 'outputs')
LOCAL_PATH = os.path.join('D:', 'Dropbox', 'Food and Fitness', 'fitbit_data')

with open(os.path.join(CONFIGS, 'api_key.txt'), 'r') as f:
            t = []
            for line in f.readlines():
                t.append(tuple(line[:-1].split(' = ')))
            token = dict(t)
			
CLIENT_ID = token['CLIENT_ID']
CLIENT_SECRET = token['CLIENT_SECRET']
REDIRECT_URI = token['REDIRECT_URI']

ZERO_DAY = dt(1900, 1, 1, 0, 0, 0)

COL_PARAMS = {'steps': {'fill': 'subdivide', 'aggregate': sum},
              'elevation': {'fill': 'subdivide', 'aggregate': sum},
              'heart': {'fill': 'interpolate', 'aggregate':np.mean},
              'sleep': {'fill': 'repeat', 'aggregate': lambda x: sum(x > 0) / 3600}}

class Dataset:
    def __init__(self, start_day=None, end_day=None, load_dir=None):
        self.time_series = None
        self.start_day = None
        self.end_day = None

        # 1. If a source directory is provided, load raw datasets from there.
        # 2. If no start and end day is provided, assume the range is yesterday -> today
        # 3. Otherwise, initialize a new time series.
        if load_dir is not None:
            self.load_raw(load_dir)
            self.start_day = self.time_series.index.min()
            self.end_day = self.time_series.index.max()
            return
        elif start_day is None and end_day is None:
            self.start_day = dt.today() - tdelt(days=1)
            self.end_day = dt.today()
        else:
            self.start_day = start_day
            self.end_day = end_day
            self.time_series = pd.DataFrame(index=pd.date_range(self.start_day, self.end_day + tdelt(days=1), freq='S'))

    def download_data(self, fields=None):
        if fields is None:
            fields = ['heart', 'steps', 'elevation', 'sleep']
        # Load an existing authorization token into memory
        with open('auth_token.txt', 'r') as f:
            t = []
            for line in f.readlines():
                t.append(tuple(line[:-1].split(' = ')))
            token = dict(t)

        # Initiate the fitbit API client
        fb = fitbit.Fitbit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                           access_token=token['access_token'],
                           refresh_token=token['refresh_token'],
                           expires_at=float(token['expires_at']))

        for day in [self.end_day - tdelt(days=x) for x in range(0, (self.end_day - self.start_day).days + 1)]:

            if 'heart' in fields:
                heart_intraday = fb.intraday_time_series(resource='activities/heart',
                                                         base_date=day, detail_level='1sec')
                heart_data = heart_intraday[u'activities-heart-intraday'][u'dataset']
                if heart_data[0][u'time'] != u'00:00:00':
                    heart_data = [{u'time': u'00:00:00', u'value': 0}] + heart_data
                if heart_data[-1][u'time'] != u'23:59:59':
                    heart_data = heart_data + [{u'time': u'23:59:59', u'value': 0}]
                self.add_observation('heart', day, heart_data, fill='interpolate')

            if 'steps' in fields:
                steps_intraday = fb.intraday_time_series(resource='activities/steps',
                                                         base_date=day, detail_level='1min')
                step_data = steps_intraday[u'activities-steps-intraday'][u'dataset']
                if step_data[0][u'time'] != u'00:00:00':
                    step_data = [{u'time': u'00:00:00', u'value': 0}] + step_data
                if step_data[-1][u'time'] != u'23:59:59':
                    step_data = step_data + [{u'time': u'23:59:59', u'value': 0}]
                self.add_observation('steps', day, step_data, fill='subdivide')

            if 'elevation' in fields:
                elevation_intraday = fb.intraday_time_series(resource='activities/elevation',
                                                             base_date=day, detail_level='1min')
                elevation_data = elevation_intraday[u'activities-elevation-intraday'][u'dataset']
                if elevation_data[0][u'time'] != u'00:00:00':
                    elevation_data = [{u'time': u'00:00:00', u'value': 0}] + elevation_data
                if elevation_data[-1][u'time'] != u'23:59:59':
                    elevation_data = elevation_data + [{u'time': u'23:59:59', u'value': 0}]
                self.add_observation('elevation', day, elevation_data, fill='subdivide')

            if 'sleep' in fields:
                sleep = fb.get_sleep(date=day)
                try:
                    sleep_data = [{u'value': s[u'value'], u'time': s[u'dateTime']}
                                  for s in sleep[u'sleep'][0][u'minuteData']]
                except IndexError:
                    sleep_data = None
                self.add_observation('sleep', day, sleep_data, fill='repeat')

    def add_observation(self, colname, start_day, observations, fill='subdivide'):
        if observations is None:
            return
        day = start_day
        for a, b in zip(observations, observations[1:]):
            this_time = dt.combine(day, dt.strptime(a['time'], '%H:%M:%S').time())
            next_time = dt.combine(day, (dt.strptime(b['time'], '%H:%M:%S') - tdelt(seconds=1)).time())

            # In case a day boundary is crossed
            if next_time.time() < this_time.time():
                day = (day + tdelt(days=1))
                next_time = dt.combine(day, (dt.strptime(b['time'], '%H:%M:%S') - tdelt(seconds=1)).time())
            time_steps = (next_time - this_time).seconds + 1

            if fill == 'subdivide':         period_obs = [a['value'] / time_steps] * time_steps
            elif fill == 'interpolate':     period_obs = np.linspace(a['value'], b['value'], time_steps)
            elif fill == 'repeat':          period_obs = [float(a['value'])] * time_steps
            else:                           period_obs = [a['value']] * time_steps

            try:                self.time_series.loc[this_time:next_time, colname] = period_obs
            except ValueError:  print 'Value Error'

    def resample(self, resolution='H'):
        return self.time_series.resample(resolution).agg({k: col['aggregate']
                                                          for k, col in COL_PARAMS.iteritems()})

    def save_raw(self):
        ts_list = [group[1] for group in self.time_series.groupby(self.time_series.index.day)]
        for ts in ts_list[:-1]:
            ts.to_csv(os.path.join(LOCAL_PATH, '0 - raw', ts.index.min().strftime('%Y%m%d') + '.csv'))

    def load_raw(self, directory):
        all_files = glob.glob(os.path.join(directory, '*.csv'))
        all_raw_dfs = [pd.read_csv(f, index_col=0) for f in all_files]

        dt_dfs = []
        for df in all_raw_dfs:
            df.index = pd.to_datetime(df.index)
            dt_dfs.append(df)

        self.time_series = pd.concat(dt_dfs)
        
if __name__ == '__main__':
    # ds = Dataset(load_dir=os.path.join(LOCAL_PATH, '0 - raw'))
    start_day = dt(2017, 7, 30)
    end_day = dt(2017, 8, 5)
    ds = Dataset(start_day, end_day)
    ds.download_data()
    ds.save_raw()

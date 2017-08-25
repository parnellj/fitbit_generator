from __future__ import division

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime
import numpy as np
from scipy.interpolate import spline
from datetime import datetime as dt, timedelta

ds_raw = []
start_time = dt(1900,1,1)

with open('20170221_0700_to_2359_hr.txt', 'r') as f:
    # f.readline()
    for entry in f.readlines():
        e = entry[:-1]
        time, obs = e.split(',')
        time = dt.strptime(time, '%Y-%m-%d %H:%M:%S')
        if len(ds_raw) == 0:
            start_time = time
        td = time - start_time
        ds_raw.append({'t':time,  'td':td.seconds, 'val':int(obs)})

def interpolate(observations):
    """
    Interpolate data for missing time steps using a linear method.
    :param observations: A list of observations
    :return: An interpolated list of observations
    """
    ds_interpolated = []
    pairs = zip(observations, observations[1:])
    for start, end in pairs:
        steps = end['td'] - start['td']
        value_delta = end['val'] - start['val']
        value_step = value_delta / steps

        for i in xrange(0, steps):
            interpolated = 'o' if i == 0 else 'i'
            ds_interpolated.append({'t':start['t'] + timedelta(0, i),
                                    'td':start['td'] + i,
                                    'val':start['val'] + (i * value_step),
                                    'ipl':interpolated})
    return ds_interpolated

def reduce(observations, step):
    """
    Reduce observations by averaging observations in the group size specified by step.
    :param observations: A list of observations
    :param step: The size of step by which to group
    :return: A reduced list of observations
    """
    ds_simplified = []
    for i in xrange(0, len(observations), step):
        subset = observations[i:i+step]
        td_avg = np.mean([d['td'] for d in subset])
        val_avg = np.mean([d['val'] for d in subset])
        ds_simplified.append({'t':observations[i]['t'], 'td':td_avg, 'val':val_avg})
    return ds_simplified

def level(observations, r):
    """
    Round off observation values to the number of places specified by r by division and multiplication.
    :param observations: A list of observations
    :param r: The number of places to which rounding should occur
    :return: A rounded list of observations
    """
    ds_leveled = []
    for o in observations:
        ds_leveled.append({'t': o['t'], 'td': o['td'],
                           'val': round((o['val'] / r)) * r})
    return ds_leveled


def envelope_plot(x, y, winsize, ax=None, fill='gray', color='blue'):
    """
    Resize plane and generate envelope and line objects for a MatPlotLib envelope plot.
    :param x: A list of x values
    :param y: A list of y values
    :param winsize: The size of the window 
    :param ax: A MatPlotLib axis object
    :param fill: The fill color of the envelope as a tuple hex triplet
    :param color: The color of the line
    :return: A filled region and line plotted on ax
    """
    if ax is None:
        ax = plt.gca()
    # Coarsely chunk the data, discarding the last window if it's not evenly
    # divisible. (Fast and memory-efficient)
    numwin = x.size // winsize
    ywin = y[:winsize * numwin].reshape(-1, winsize)
    xwin = x[:winsize * numwin].reshape(-1, winsize)
    # Find the min, max, and mean within each window
    ymin = ywin.min(axis=1)
    ymax = ywin.max(axis=1)
    ymean = ywin.mean(axis=1)
    xmean = xwin.mean(axis=1)

    fill_artist = ax.fill_between(xmean, ymin, ymax, color=fill,
                                  edgecolor='none', alpha=0.5)
    line, = ax.plot(xmean, ymean, color=color, linestyle='-')
    return fill_artist, line

dsi = interpolate(ds_raw)
x = np.array([d['t'] for d in dsi])
y = np.array([d['val'] for d in dsi])
# x = np.linspace(0, 10, 10000)
# y = np.cos(x) + 5 * np.random.random(10000)

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.gca().xaxis.set_major_locator(mdates.HourLocator())
plt.plot(x, y)
plt.gcf().autofmt_xdate()
plt.show()

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import numpy as np
import pytz
import os
from dateutil.relativedelta import relativedelta
from datetime import datetime
from . import socorro
from . import utils
from .connection import Query
from . import patchanalysis
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def mean(x):
    """Get the mean of the sequence x

    Args:
        x (list or numpy.array): numbers

    Returns:
        (float, float): the mean and the standard deviation
    """
    l = len(x)
    m = np.sum(x) / l
    e = np.sqrt(np.sum((x - m) ** 2 / l))
    return m, e


def median(x):
    """Get the median of the sequence x

    Args:
        x (list or numpy.array): numbers

    Returns:
        (float, float): the median and the interquartile-range
    """
    q1, m, q3 = np.percentile(x, [25, 50, 100], interpolation='midpoint')
    return m, q3 - q1


def __convert(x):
    """Convert a sequence into a numpy.array

    Args:
        x (list): numbers

    Returns:
        (numpy.array): a float64 array
    """
    if not isinstance(x, np.ndarray):
        return np.asarray(x, dtype=np.float64)
    return x


def moving(x, f=mean, coeff=2.0):
    """Get the constant trends of x.

       The idea is the following:
         - suppose that [x_0, ...,x_{n-1}] are 'constant' piece (constant in trend)
         - we've a new value x_n
         - we compute f([x_0, ..., x_n]) and get the position (p) and dispersion (d) parameters
         - if abs(x_n - p) <= coeff * d then the x_n is added to the constant piece
         - else a new piece containing x_n is beginning.

    Args:
        x (list): numbers
        f (func): the fonction to compute the position
        coeff (float): a coefficient for the tolerance relative to the dispersion

    Returns:
        (numpy.array): the smoothed data
    """
    x = __convert(x)
    pieces = [[0, 0]]
    coeff = float(coeff)
    l = len(x)

    for i in range(1, l):
        p, d = f(x[pieces[-1][0]:(i + 1)])
        if abs(x[i] - p) <= coeff * d:
            pieces[-1][1] = i
        else:
            pieces.append([i, i])

    yp = np.empty(l)
    yd = np.empty(l)
    pos = 0
    for piece in pieces:
        p, d = f(x[piece[0]:(piece[1] + 1)])
        N = piece[1] - piece[0] + 1
        yp[pos:(pos + N)] = p
        yd[pos:(pos + N)] = d
        pos += N

    return yp, yd


def multimoving(x, f=mean, coeff=2.0):
    """Compute all the moving curves in moving the first point from left to right
       and for each point, select the position which minimize the dispersion.

    Args:
        x (list): numbers
        f (func): the fonction to compute the position
        coeff (float): a coefficient for the tolerance relative to the dispersion

    Returns:
        (numpy.array): the smoothed data
    """
    x = __convert(x)
    l = len(x)
    ys = np.empty((l, l))
    ds = np.empty((l, l))
    for i in range(l):
        x1 = x[:(i + 1)]
        x2 = x[i:]
        y1, d1 = moving(x1[::-1], f, coeff)
        y2, d2 = moving(x2, f, coeff)
        ys[i][:len(y1)] = y1[::-1]
        ys[i][len(y1):] = y2[1:]
        ds[i][:len(d1)] = d1[::-1]
        ds[i][len(d1):] = d2[1:]

    y = np.empty(l)
    d = np.empty(l)
    mins_index = np.argmin(ds, axis=0)
    for i in range(l):
        y[i] = ys[mins_index[i]][i]
        d[i] = ds[mins_index[i]][i]

    return y, d


def plot(data, f=mean, coeff=2., multi=True, filename=''):
    tr = trends(data, f=f, coeff=coeff, multi=multi)
    x = tr['data']
    sx = tr['smooth_data']
    pieces = tr['pieces']
    r = np.arange(len(x))
    x1 = [pieces[0][0]]
    y1 = [x[pieces[0][0]]]
    for piece in pieces:
        x1.append(piece[1])
        y1.append(sx[piece[1]])

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(r, x, color='blue')
    ax.plot(r, sx, color='red')
    ax.plot(x1, y1, color='green')

    if filename:
        fig.savefig(filename)
        plt.close()
    else:
        plt.show()


def trends(data, f=mean, coeff=2., multi=True):
    """Get the global variations of the data

    Args:
        data (list or dict): the data
        f (func): the fonction to compute the position
        coeff (float): a coefficient for the tolerance relative to the dispersion
        multi (Bool): if True, then apply the multimoving smoothing

    Returns:
        (list or dict): the global variations of the data
    """
    if isinstance(data, dict):
        # we sort the data according to the key
        sorted_data = sorted(data.items(), key=lambda p: p[0])
        x = [y for _, y in sorted_data]
    else:
        sorted_data = []
        x = data

    x = __convert(x)
    if multi:
        m, _ = multimoving(x, f, coeff)
    else:
        m, _ = moving(x, f, coeff)

    diff = np.diff(m)
    pieces = [[0, 0, 0]]
    for i in range(len(diff)):
        dx = diff[i]
        last = pieces[-1]
        k = i + 1
        if dx > 0:
            if last[2] >= 0:
                last[1:] = k, +1
            else:
                pieces.append([i, k, +1])
        elif dx < 0:
            if last[2] <= 0:
                last[1:] = k, -1
            else:
                pieces.append([i, k, -1])
        else:
            last[1] = k

    incr = []
    decr = []
    inf = float('inf')
    for piece in pieces:
        p0 = piece[0]
        p1 = piece[1]
        percent = inf if m[p0] == 0 else round((m[p1] - m[p0]) / m[p0] * 100.)
        info = [p0, p1, percent]
        if piece[2] == 1:
            incr.append(info)
        elif piece[2] == -1:
            info[2] = abs(info[2])
            decr.append(info)
        elif p0 == 0:
            info[2] = abs(info[2])
            decr.append(info)
        else:
            info[2] = info[2]
            incr.append(info)

    if sorted_data:
        for i in incr:
            i[0] = sorted_data[i[0]][0]
            i[1] = sorted_data[i[1]][0]
        for d in decr:
            d[0] = sorted_data[d[0]][0]
            d[1] = sorted_data[d[1]][0]

    return {'increases': incr, 'decreases': decr, 'pieces': pieces, 'data': x, 'smooth_data': m}


def has_crash_stopped(data, date, threshold=51, f=mean, coeff=2., multi=True):
    """Check if a crash has stopped after a date

    Args:
        data (list or dict): the data
        date (datetime.datetime): the date
        threshold (float): the percentage of decrease
        f (func): the fonction to compute the position
        coeff (float): a coefficient for the tolerance relative to the dispersion
        multi (Bool): if True, then apply the multimoving smoothing

    Returns:
        (Bool): True if the crash has stopped
    """
    tr = trends(data, f=f, coeff=coeff, multi=multi)
    for dec in tr['decreases']:
        if dec[0] <= date <= dec[1] and dec[2] >= threshold:
            return True
    return False


def have_crashes_stopped(crashes_info, product='Firefox', thresholds={}, path=None):
    def handler(json, data):
        trend = data['trend']
        for info in json['facets']['build_id']:
            date = utils.get_date_from_buildid(info['term'])
            date = pytz.utc.localize(datetime(date.year, date.month, date.day))
            trend[date] += info['facets']['cardinality_install_time']['value']

        if thresholds:
            ts = thresholds.get(data['channel'], -1)
            for k, v in trend.items():
                if v <= ts:
                    trend[k] = 0

        data['stop'] = has_crash_stopped(trend, data['push_date'])
        if True or path and not data['stop']:
            signature = json['facets']['signature'][0]['term']
            count = json['facets']['signature'][0]['count']
            filename = os.path.join(path, '%s_%d.png' % (signature, count))
            plot(trend, filename=filename)

    def trends_handler(json, data):
        for info in json['facets']['build_id']:
            date = utils.get_date_from_buildid(info['term'])
            date = pytz.utc.localize(datetime(date.year, date.month, date.day))
            data[date] = 0

    queries = []
    for info in crashes_info:
        d = {}
        info['trend'] = d
        search_date = socorro.SuperSearch.get_search_date(info['start_date'], info['end_date'])
        queries.append(Query(socorro.SuperSearch.URL,
                             {'product': product,
                              'version': info.get('versions', None),
                              'release_channel': info.get('channel', None),
                              'build_id': info.get('build_id'),
                              'date': search_date,
                              '_aggs.build_id': '_cardinality.install_time',
                              '_facets_size': 1000,
                              '_results_number': 0},
                             handler=trends_handler, handlerdata=d))

    socorro.SuperSearch(queries=queries).wait()

    queries = []
    for info in crashes_info:
        search_date = socorro.SuperSearch.get_search_date(info['start_date'], info['end_date'])
        queries.append(Query(socorro.SuperSearch.URL,
                             {'signature': '=' + info['signature'],
                              'product': product,
                              'version': info.get('versions', None),
                              'release_channel': info.get('channel', None),
                              'build_id': info.get('build_id'),
                              'date': search_date,
                              '_aggs.build_id': '_cardinality.install_time',
                              '_facets_size': 1000,
                              '_results_number': 0},
                             handler=handler, handlerdata=info))

    socorro.SuperSearch(queries=queries).wait()


def analyze_bugs(bugs, thresholds={'nightly': 5, 'aurora': 5, 'beta': 10, 'release': 50}):
    patch_info = patchanalysis.get_patch_info(bugs)
    all_versions = socorro.ProductVersions.get_all_versions()

    # prepare the data
    data = []
    for bugid, info in patch_info.items():
        for sgn in info['signatures']:
            for chan, date in info['land'].items():
                d = {'signature': sgn, 'push_date': date, 'channel': chan, 'versions': None, 'bugid': bugid}
                chan_versions = all_versions[chan]
                for v in chan_versions.values():
                    dates = v['dates']
                    if dates[0] <= date <= dates[1]:
                        d['start_date'] = dates[0]
                        d['end_date'] = dates[1]
                        if dates[1]:
                            d['build_id'] = ['>=' + utils.get_buildid_from_date(dates[0]),
                                             '<' + utils.get_buildid_from_date(dates[1] + relativedelta(days=1))]
                        else:
                            d['build_id'] = '>=' + utils.get_buildid_from_date(dates[0])
                        d['versions'] = v['all']
                        break
                data.append(d)

    have_crashes_stopped(data, thresholds=thresholds, path='/tmp')

    for d in data:
        pi = patch_info[d['bugid']]
        sgn = d['signature']
        if 'stops' in pi:
            stops = pi['stops']
        else:
            stops = {}
            pi['stops'] = stops

        if sgn in stops:
            stops[sgn][d['channel']] = d['stop']
        else:
            stops[sgn] = {d['channel']: d['stop']}

    for bugid in bugs:
        bugid = str(bugid)
        if bugid not in patch_info:
            patch_info[bugid] = {}

    return patch_info

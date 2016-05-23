# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import six
import operator
import calendar
from datetime import (datetime, date, timedelta)
import math
import json
import random


def get_best(stats):
    """Get the key which has the higher value

    Args:
        stats (dict): the stats contained in a dictionary

    Returns:
        a key
    """
    if stats:
        return max(stats.items(), key=operator.itemgetter(1))[0]
    else:
        return None


def get_timestamp(dt):
    """Get a timestamp from a date

    Args:
        dt: a string or a datetime object

    Returns:
        int: the corresponding timestamp
    """
    if isinstance(dt, six.string_types):
        dt = get_date_ymd(dt)
    return int(calendar.timegm(dt.timetuple()))


def get_date_ymd(dt):
    """Get a datetime from a string 'Year-month-day'

    Args:
        dt (str): a date

    Returns:
        datetime: a datetime object
    """
    if dt == 'today':
        today = date.today()
        return datetime(today.year, today.month, today.day)
    elif dt == 'yesterday':
        yesterday = date.today() + timedelta(-1)
        return datetime(yesterday.year, yesterday.month, yesterday.day)
    elif dt == 'tomorrow':
        tomorrow = date.today() + timedelta(1)
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day)

    l = None
    if '-' in dt:
        l = dt.split('-')
    elif '/' in dt:
        l = dt.split('/')
    elif ' ' in dt:
        l = dt.split(' ')
    if l and len(l) == 3 and len(l[0]) == 4:
        (y, m, d) = map(int, l)
        return datetime(y, m, d)
    else:
        raise Exception('Malformed string (should be YYYY-MM-DD)')


def get_today():
    """Get the date for today

    Returns:
        str: the date of today
    """
    return get_date_str(date.today())


def get_date_str(ymd):
    """Get the date as string

    Args:
        ymd (datetime): a datetime
    Returns:
        str: the date as a string 'Year-month-day'
    """
    return ymd.strftime('%Y-%m-%d')


def get_date(_date, delta=None):
    """Get the date as string

    Args:
        ymd (str): a date
    Returns:
        str: the date as a string 'Year-month-day'
    """
    _date = get_date_ymd(_date)
    if delta:
        _date -= timedelta(delta)
    return get_date_str(_date)


def get_now_timestamp():
    """Get timestamp for now

    Returns:
        int: timestamp for now
    """
    return get_timestamp(datetime.utcnow())


def is64(cpu_name):
    """Check if a cpu is 64 bits or not

    Args:
        cpu_name (str): the cpu name

    Returns:
        bool: True if 64 is in the name
    """
    return '64' in cpu_name


def percent(x):
    """Get a percent from a ratio (0.23 => 23%)

    Args:
        x (float): ratio

    Returns:
        str: a string with a percent
    """
    return simple_percent(round(100 * x, 1))


def simple_percent(x):
    """Get a percent string

    Args:
        x (float): number

    Returns:
        str: a string with a percent
    """
    if math.floor(x) == x:
        x = int(x)
    return str(x) + '%'


def get_credentials(path):
    """Get credentials from a json file

    Args:
        path (str): the path of the file which contains json data with credentials for the differents sources

    Returns:
        dict: a json dict
    """
    with open(path) as In:
        return json.load(In)


def get_sample(data, fraction):
    """Get a random sample from the data according to the fraction

    Args:
        data (list): data
        fraction (float): the fraction

    Returns:
        list: a random sample
    """
    if fraction < 0 or fraction >= 1:
        return data
    else:
        return random.sample(data, int(fraction * len(data)))


def get_date_from_buildid(bid):
    """Get a date from buildid

    Args:
        bid (str): build_id

    Returns:
        date: date object
    """
    # 20160407164938 == 2016 04 07 16 49 38
    year = int(str(bid)[:4])
    month = int(str(bid)[4:6])
    day = int(str(bid)[6:8])

    return datetime(year, month, day)


def rate(x, y):
    """ Compute a rate

    Args:
        x (num): numerator
        y (num): denominator

    Returns:
        float: x / y or Nan if y == 0
    """
    return float(x) / float(y) if y else float('nan')

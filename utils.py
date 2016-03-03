import operator
import time
from datetime import datetime
from pprint import pprint
import math
import json


# return the key with the higher value
def get_best(stats):
    if stats:
        return max(stats.iteritems(), key = operator.itemgetter(1))[0]
    else:
        return None

def get_timestamp(dt):
    if isinstance(dt, basestring):
        dt = get_date_ymd(dt)
    return int(time.mktime(dt.timetuple()))

def get_date_ymd(dt):
    l = None
    if '-' in dt:
        l = dt.split('-')
    elif '/' in dt:
        l = dt.split('/')
    elif ' ' in dt:
        l = dt.split(' ')
    if l and len(l) == 3:
        if len(l[0]) == 4:
            (y, m, d) = map(int, l)
        elif len[2] == 4:
            (m, d, y) = map(int, l)
    return datetime(y, m, d)

def get_date_str(ymd):
    ymd = ymd.timetuple()[:3]
    ymd = map(str, ymd)
    return '-'.join(ymd)

def get_now_timestamp():
    return get_timestamp(datetime.utcnow())

def is64(cpu_name):
    return '64' in cpu_name

def percent(x):
    return simple_percent(round(100 * x, 1))

def simple_percent(x):
    if math.floor(x) == x:
        x = int(x)
    return str(x) + '%'

def get_credentials(path):
    with open(path) as In:    
        return json.load(In)
    return None

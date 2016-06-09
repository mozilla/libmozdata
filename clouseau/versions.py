# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen

from os.path import commonprefix
import json
from datetime import timedelta
from . import utils

__versions = None
__version_dates = None


def __get_major(v):
    return int(v.split('.')[0])


def __getVersions():
    """Get the versions number for each channel

    Returns:
        dict: versions for each channel
    """
    try:
        resp = urlopen('https://product-details.mozilla.org/firefox_versions.json')
        data = json.loads(resp.read().decode('utf-8'))
        resp.close()
    except:
        resp = urlopen('http://svn.mozilla.org/libs/product-details/json/firefox_versions.json')
        data = json.loads(resp.read().decode('utf-8'))
        resp.close()

    aurora = data['FIREFOX_AURORA']
    nightly = '%d.0a1' % (__get_major(aurora) + 1)
    return {'release': data['LATEST_FIREFOX_VERSION'],
            'beta': data['LATEST_FIREFOX_RELEASED_DEVEL_VERSION'],
            'aurora': str(aurora),
            'nightly': nightly}


def __getVersionDates():
    try:
        resp = urlopen('https://product-details.mozilla.org/firefox_history_major_releases.json')
        data = json.loads(resp.read().decode('utf-8'))
        resp.close()
    except:
        resp = urlopen('http://svn.mozilla.org/libs/product-details/json/firefox_history_major_releases.json')
        data = json.loads(resp.read().decode('utf-8'))
        resp.close()

    return data


def get(base=False):
    """Get current version number by channel

    Returns:
        dict: containing version by channel
    """
    global __versions
    if not __versions:
        __versions = __getVersions()

    if base:
        res = {}
        for k, v in __versions.items():
            res[k] = __get_major(v)
        return res

    return __versions


def getMajorDate(version):
    global __version_dates
    if not __version_dates:
        __version_dates = __getVersionDates()

    date = None
    longest_match = []
    longest_match_v = None
    for v, d in __version_dates.items():
        match = commonprefix([v.split('.'), str(version).split('.')])
        if len(match) > 0 and (len(match) > len(longest_match) or (len(match) == len(longest_match) and int(v[-1]) <= int(longest_match_v[-1]))):
            longest_match = match
            longest_match_v = v
            date = d

    return utils.get_date_ymd(date + 'T00:00:00Z') if date is not None else None


def getCloserMajorRelease(date, negative=False):
    global __version_dates
    if not __version_dates:
        __version_dates = __getVersionDates()

    def diff(d):
        return utils.get_date_ymd(d + 'T00:00:00Z') - date

    return min([(v, d) for v, d in __version_dates.items() if negative or diff(d) > timedelta(0)], key=lambda i: abs(diff(i[1])))

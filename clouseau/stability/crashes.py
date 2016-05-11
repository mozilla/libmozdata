# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import six
import functools
from datetime import (datetime, timedelta)
from pprint import pprint
import clouseau.socorro as socorro
import clouseau.utils as utils
from clouseau.redash import Redash
from clouseau.connection import (Connection, Query)
from clouseau.bugzilla import Bugzilla


def __get_khours(start_date, end_date, channel, versions, credentials):
    qid = '346'
    khours = Redash.get(qid, credentials=credentials)
    rows = khours[qid]['query_result']['data']['rows']
    res = {}

    # init the data
    duration = (end_date - start_date).days
    for i in range(duration + 1):
        res[start_date + timedelta(i)] = 0.

    if channel == 'beta':
        versions = set([v[:-2] for v in versions])
    else:
        versions = set(versions)

    for row in rows:
        if row['channel'] == channel:
            v = row['build_version']
            if v in versions:
                d = utils.get_date_ymd(row['activity_date'])
                if d >= start_date and d <= end_date:
                    res[d] += row['usage_khours']

    return res


def __tcbs_handler(json, data):
    for crash in json['crashes']:
        count = crash['count']
        startup_percent = crash['startup_percent']
        startup_count = int(round(float(count) * startup_percent))
        signature = crash['signature']
        data[signature] = [count, crash['win_count'], crash['mac_count'], crash['linux_count'], startup_count]


def __trend_handler(default_trend, json, data):
    for facets in json['facets']['histogram_date']:
        d = datetime.strptime(facets['term'], '%Y-%m-%dT00:00:00+00:00')
        s = facets['facets']['signature']
        for signature in s:
            count = signature['count']
            sgn = signature['term']
            if sgn in data:
                data[sgn][d] = count
            else:
                trend = default_trend.copy()
                trend[d] = count
                data[sgn] = trend


def __bug_handler(json, data):
    for bug in json['bugs']:
        data.append((bug['id'], bug['resolution']))


def get(channel, date, versions=None, product='Firefox', duration=11, tcbs_limit=50, crash_type='all', credentials=None):
    channel = channel.lower()
    if not isinstance(versions, list):
        if isinstance(versions, six.integer_types):
            versions = socorro.ProductVersions.get_active(vnumber=versions, product=product, credentials=credentials)
            versions = versions[channel.lower()]
        elif isinstance(versions, six.string_types):
            if '.' not in versions:
                versions = socorro.ProductVersions.get_active(vnumber=int(versions), product=product, credentials=credentials)
                versions = versions[channel.lower()]
            else:
                versions = [versions]
        else:
            versions = socorro.ProductVersions.get_active(product=product, credentials=credentials)
            versions = versions[channel.lower()]

    platforms = socorro.Platforms.get_cached_all(credentials=credentials)

    if crash_type and isinstance(crash_type, six.string_types):
        crash_type = [crash_type]

    _date = utils.get_date_ymd(date)
    start_date = utils.get_date_str(_date - timedelta(duration - 1))
    end_date = utils.get_date(date)

    signatures = {}

    # First, we get the ADI
    adi = socorro.ADI.get(version=versions, product=product, end_date=end_date, duration=duration, platforms=platforms, credentials=credentials)

    # Second we get info from TCBS (Top Crash By Signature)
    # we can have several active versions (45.0, 45.0.1) so we need to aggregates the results
    # TODO: ask to Socorro team to add a feature to get that directly
    tcbs = {}
    base = {'product': 'Firefox',
            'crash_type': 'all',
            'version': None,
            'limit': tcbs_limit,
            'duration': 24 * duration,
            'end_date': end_date}

    queries = []
    for v in versions:
        _dict = {}
        tcbs[v] = _dict
        cparams = base.copy()
        cparams['version'] = v
        queries.append(Query(socorro.TCBS.URL, cparams, __tcbs_handler, _dict))

    socorro.TCBS(queries=queries, credentials=credentials).wait()

    # aggregate the results from the different versions
    for tc in tcbs.values():
        for sgn, count in tc.items():
            if sgn in signatures:
                c = signatures[sgn]
                for i in range(5):  # 5 is the len of the list (see __tcbs_handler)
                    c[i] += count[i]
            else:
                signatures[sgn] = count

    # get the khours
    khours = __get_khours(utils.get_date_ymd(start_date), utils.get_date_ymd(end_date), channel, versions, credentials)
    khours = [khours[key] for key in sorted(khours.keys(), reverse=True)]

    # TODO: too many requests... should be improved with chunks
    bugs = {}
    base = {'f1': 'cf_crash_signature',
            'v1': None,
            'o1': 'substring',
            'include_fields': ['resolution', 'id']}
    queries = []
    for sgn in signatures.iterkeys():
        cparams = base.copy()
        cparams['v1'] = sgn
        _list = []
        bugs[sgn] = _list
        queries.append(Query(Bugzilla.API_URL, cparams, __bug_handler, _list))
    res_bugs = Bugzilla(queries=queries, credentials=credentials)

    # we have stats by signature in self.signatures
    # for each signature get the number of crashes on the last 7 days (7 is just an example)
    # so get the siganture trend
    trends = {}
    default_trend = {}
    for i in range(duration):
        default_trend[_date - timedelta(i)] = 0

    _start_date = utils.get_date_str(_date - timedelta(duration - 1))
    _end_date = utils.get_date_str(_date)

    base = {'product': 'Firefox',
            'version': versions,
            'signature': None,
            'date': socorro.SuperSearch.get_search_date(_start_date, _end_date),
            'release_channel': channel,
            '_results_number': 0,
            '_histogram.date': ['signature'],
            '_facets_size': 0}

    queries = []
    for sgns in Connection.chunks(map(lambda sgn: '=' + sgn, signatures.iterkeys()), 10):
        cparams = base.copy()
        cparams['signature'] = sgns
        queries.append(Query(socorro.SuperSearch.URL, cparams, functools.partial(__trend_handler, default_trend), trends))

    socorro.SuperSearch(queries=queries, credentials=credentials).wait()

    for sgn, trend in trends.items():
        signatures[sgn] = (signatures[sgn], [trend[key] for key in sorted(trend.keys(), reverse=True)])

    _signatures = {}
    # order self.signatures by crash count
    l = sorted(signatures.items(), key=lambda x: x[1][0][0], reverse=True)
    i = 1
    for s in l:
        _signatures[s[0]] = i  # top crash rank
        i += 1

    # adi maps date to adi count
    adi = [adi[key] for key in sorted(adi.keys(), reverse=True)]

    res_bugs.wait()

    for sgn, stats in signatures.items():
        # stats is 2-uple: ([count, win_count, mac_count, linux_count, startup_count], trend)
        nan = float('nan')
        crash_stats_per_mega_adi = [float(stats[1][s]) * 1e6 / float(adi[s]) if adi[s] else nan for s in range(duration)]
        crash_stats_per_mega_hours = [float(stats[1][s]) * 1e3 / khours[s] if khours[s] else nan for s in range(duration)]
        _signatures[sgn] = {'tc_rank': _signatures[sgn],
                            'crash_count': stats[0][0],
                            'startup_percent': float(stats[0][4]) / float(stats[0][0]),
                            'crash_stats_per_mega_adi': crash_stats_per_mega_adi,
                            'crash_stats_per_mega_hours': crash_stats_per_mega_hours,
                            'crash_by_day': stats[1],
                            'bugs': bugs[sgn]}

    return {'start_date': start_date,
            'end_date': end_date,
            'versions': versions,
            'adi': adi,
            'khours': khours,
            'signatures': _signatures}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Track')
    parser.add_argument('-c', '--channel', action='store', default='release', help='release channel')
    parser.add_argument('-d', '--date', action='store', default='yesterday', help='the end date')
    parser.add_argument('-D', '--duration', action='store', default=11, help='the duration')
    parser.add_argument('-v', '--versions', action='store', nargs='+', help='the Firefox versions')
    parser.add_argument('-t', '--tcbslimit', action='store', default=50, help='the Firefox versions')
    parser.add_argument('-C', '--credentials', action='store', default='', help='credentials file to use')

    args = parser.parse_args()

    credentials = utils.get_credentials(args.credentials) if args.credentials else None
    stats = get(args.channel, args.date, versions=args.versions, duration=int(args.duration), tcbs_limit=int(args.tcbslimit), credentials=credentials)
    pprint(stats)

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import json
import six
import functools
from datetime import (datetime, timedelta)
from pprint import pprint
import clouseau.socorro as socorro
import clouseau.utils as utils
from clouseau.redash import Redash
from clouseau.connection import (Connection, Query)
from clouseau.bugzilla import Bugzilla


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
        data.append({'id': bug['id'], 'resolution': bug['resolution'], 'last_change_time': bug['last_change_time']})


def get(channel, date, versions=None, product='Firefox', duration=11, tcbs_limit=50, crash_type='all'):
    """Get crashes info

    Args:
        channel (str): the channel
        date (str): the final date
        versions (Optional[List[str]]): the versions to treat
        product (Optional[str]): the product
        duration (Optional[int]): the duration to retrieve the data
        tcbs_limit (Optional[int]): the number of crashes to get from tcbs
        crash_type (Optional[str]): 'all' (default) or 'browser' or 'content' or 'plugin'

    Returns:
        dict: contains all the info relative to the crashes
    """
    channel = channel.lower()
    versions_info = socorro.ProductVersions.get_version_info(versions, channel=channel, product=product)
    versions = versions_info.keys()
    platforms = socorro.Platforms.get_cached_all()

    if crash_type and isinstance(crash_type, six.string_types):
        crash_type = [crash_type]

    throttle = set(map(lambda p: p[1], versions_info.values()))
    if len(throttle) == 1:
        throttle = throttle.pop()
    else:
        return

    _date = utils.get_date_ymd(date)
    start_date = utils.get_date_str(_date - timedelta(duration - 1))
    end_date = utils.get_date(date)

    signatures = {}

    # First, we get the ADI
    adi = socorro.ADI.get(version=versions, product=product, end_date=end_date, duration=duration, platforms=platforms)
    adi = [adi[key] for key in sorted(adi.keys(), reverse=True)]

    # Second we get info from TCBS (Top Crash By Signature)
    # we can have several active versions (45.0, 45.0.1) so we need to aggregates the results
    # TODO: ask to Socorro team to add a feature to get that directly
    tcbs = {}
    base = {'product': product,
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

    socorro.TCBS(queries=queries).wait()

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
    khours = Redash.get_khours(utils.get_date_ymd(start_date), utils.get_date_ymd(end_date), channel, versions, product)
    khours = [khours[key] for key in sorted(khours.keys(), reverse=True)]

    # TODO: too many requests... should be improved with chunks
    bugs = {}
    base = {'f1': 'cf_crash_signature',
            'v1': None,
            'o1': 'substring',
            'include_fields': ['resolution', 'id', 'last_change_time']}
    queries = []
    for sgn in signatures.keys():
        cparams = base.copy()
        cparams['v1'] = sgn
        _list = []
        bugs[sgn] = _list
        queries.append(Query(Bugzilla.API_URL, cparams, __bug_handler, _list))
    res_bugs = Bugzilla(queries=queries)

    # we have stats by signature in self.signatures
    # for each signature get the number of crashes on the last X days
    # so get the signature trend
    trends = {}
    default_trend = {}
    for i in range(duration):
        default_trend[_date - timedelta(i)] = 0

    _start_date = utils.get_date_str(_date - timedelta(duration - 1))
    _end_date = utils.get_date_str(_date)

    overall_crashes_by_day = []

    def crash_count_handler(json, data):
        for facets in json['facets']['histogram_date']:
            overall_crashes_by_day.insert(0, facets['count'])

    socorro.SuperSearch(params={
        'product': product,
        'version': versions,
        'date': socorro.SuperSearch.get_search_date(_start_date, _end_date),
        'release_channel': channel,
        '_results_number': 0,
        '_histogram.date': ['product'],
        '_histogram_interval': 1
    }, handler=crash_count_handler).wait()

    base = {'product': product,
            'version': versions,
            'signature': None,
            'date': socorro.SuperSearch.get_search_date(_start_date, _end_date),
            'release_channel': channel,
            '_results_number': 0,
            '_histogram.date': ['signature'],
            '_histogram_interval': 1}

    queries = []
    for sgns in Connection.chunks(list(map(lambda sgn: '=' + sgn, signatures.keys())), 10):
        cparams = base.copy()
        cparams['signature'] = sgns
        queries.append(Query(socorro.SuperSearch.URL, cparams, functools.partial(__trend_handler, default_trend), trends))

    socorro.SuperSearch(queries=queries).wait()

    for sgn, trend in trends.items():
        signatures[sgn] = (signatures[sgn], [trend[key] for key in sorted(trend.keys(), reverse=True)])

    _signatures = {}
    # order self.signatures by crash count
    l = sorted(signatures.items(), key=lambda x: x[1][0][0], reverse=True)
    i = 1
    for s in l:
        _signatures[s[0]] = i  # top crash rank
        i += 1

    res_bugs.wait()

    throttle = float(throttle)

    for sgn, stats in signatures.items():
        # stats is 2-uple: ([count, win_count, mac_count, linux_count, startup_count], trend)
        nan = None  # Use None because NaN isn't serializable in JSON.
        crash_stats_per_mega_adi = [100 / throttle * float(stats[1][s]) * 1e6 / float(adi[s]) if adi[s] else nan for s in range(duration)]
        crash_stats_per_mega_hours = [100 / throttle * float(stats[1][s]) * 1e3 / khours[s] if khours[s] else nan for s in range(duration)]
        startup_percent = float(stats[0][4]) / float(stats[0][0])
        is_startup_crash = round(startup_percent * 100.) > 50.
        _signatures[sgn] = {'tc_rank': _signatures[sgn],
                            'crash_count': stats[0][0],
                            'startup_percent': startup_percent,
                            'startup_crash': is_startup_crash,
                            'crash_stats_per_mega_adi': crash_stats_per_mega_adi,
                            'crash_stats_per_mega_hours': crash_stats_per_mega_hours,
                            'crash_by_day': stats[1],
                            'bugs': bugs[sgn]}

    return {'start_date': start_date,
            'end_date': end_date,
            'versions': list(versions),
            'adi': adi,
            'khours': khours,
            'crash_by_day': overall_crashes_by_day,
            'signatures': _signatures,
            'throttle': throttle}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Track')
    parser.add_argument('-c', '--channel', action='store', default='release', help='release channel')
    parser.add_argument('-d', '--date', action='store', default='yesterday', help='the end date')
    parser.add_argument('-D', '--duration', action='store', default=11, help='the duration')
    parser.add_argument('-v', '--versions', action='store', nargs='+', help='the Firefox versions')
    parser.add_argument('-t', '--tcbslimit', action='store', default=50, help='number of crashes to retrieve in Top Crash')

    args = parser.parse_args()

    stats = get(args.channel, args.date, versions=args.versions, duration=int(args.duration), tcbs_limit=int(args.tcbslimit))
    pprint(stats)

    with open('crashes.json', 'w') as f:
        json.dump(stats, f, allow_nan=False)

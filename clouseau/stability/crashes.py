# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from datetime import (datetime, timedelta)
import clouseau.socorro as socorro
import clouseau.utils as utils
from clouseau.connection import (Connection, Query)
from clouseau.bugzilla import Bugzilla


def __adi_handler(json, data):
    for adi in json['hits']:
        date = utils.get_date_ymd(adi['date'])
        adi_count = adi['adi_count']
        data[date] = data[date] + adi_count if date in data else adi_count


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


def get_stats(channel, date, versions=None, last_days=11, tcbs_limit=50, credentials=None):
    channel = channel.lower()
    if not versions:
        versions = socorro.ProductVersions.get_version(channel, credentials=credentials)
    platforms = socorro.Platforms.get_cached_all(credentials=credentials)

    _date = utils.get_date_ymd(date)
    start_date = utils.get_date_str(_date - timedelta(last_days - 1))
    end_date = date

    signatures = {}

    # First, we get the ADI
    adi = {}
    res_adi = socorro.ADI(params={'product': 'Firefox',
                                  'platforms': platforms,
                                  'versions': versions,
                                  'start_date': start_date,
                                  'end_date': end_date},
                          handler=__adi_handler,
                          handlerdata=adi)

    # Second we get info from TCBS (Top Crash By Signature)
    # we can have several active versions (45.0, 45.0.1) so we need to aggregates the results
    # TODO: ask to Socorro team to add a feature to get that directly
    tcbs = {}
    base = {'product': 'Firefox',
            'crash_type': 'Browser',
            'version': None,
            'limit': tcbs_limit,
            'duration': 24 * last_days,
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
    for tc in tcbs.itervalues():
        for sgn, count in tc.iteritems():
            if sgn in signatures:
                c = signatures[sgn]
                for i in range(5):
                    c[i] += count[i]
            else:
                signatures[sgn] = count

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
    for i in range(last_days):
        default_trend[_date - timedelta(i)] = 0

    _start_date = utils.get_date_str(_date - timedelta(last_days - 1))
    _end_date = utils.get_date_str(_date + timedelta(1))

    base = {'product': 'Firefox',
            'version': versions,
            'signature': None,
            'date': ['>=' + _start_date,
                     '<' + _end_date],
            'release_channel': channel,
            '_results_number': 0,
            '_histogram.date': ['signature'],
            '_facets_size': 0}

    queries = []
    for sgns in Connection.chunks(map(lambda sgn: '=' + sgn, signatures.iterkeys()), 10):
        cparams = base.copy()
        cparams['signature'] = sgns
        queries.append(Query(socorro.SuperSearch.URL, cparams, lambda json, data: __trend_handler(default_trend, json, data), trends))

    socorro.SuperSearch(queries=queries, credentials=credentials).wait()

    for sgn, trend in trends.iteritems():
        signatures[sgn] = (signatures[sgn], [trend[key] for key in sorted(trend.keys(), reverse=True)])

    _signatures = {}
    # order self.signatures by crash count
    l = sorted(signatures.iteritems(), key=lambda x: x[1][0][0], reverse=True)
    i = 1
    for s in l:
        _signatures[s[0]] = i  # top crash rank
        i += 1

    res_adi.wait()
    # adi maps date to adi count
    adi = [adi[key] for key in sorted(adi.keys(), reverse=True)]

    res_bugs.wait()

    for sgn, stats in signatures.iteritems():
        # stats is 2-uple: ([count, win_count, mac_count, linux_count, startup_count], trend)
        crash_stats_per_mega_adi = [float(stats[1][s]) * 1e6 / float(adi[s]) for s in range(last_days)]
        _signatures[sgn] = {'tc_rank': _signatures[sgn],
                            'crash_count': stats[0][0],
                            'startup_percent': float(stats[0][4]) / float(stats[0][0]),
                            'crash_stats_per_mega_adi': crash_stats_per_mega_adi,
                            'crash_by_day': stats[1],
                            'bugs': bugs[sgn]}

    return {'start_date': start_date,
            'end_date': end_date,
            'versions': versions,
            'adi': adi,
            'signatures': _signatures}

# sgns = get_stats('release', '2016-04-24', versions=['45.0.2'], credentials=utils.get_credentials('/home/calixte/credentials.json'), tcbs_limit=300)
# pprint(sgns)#['nsInterfaceHashtable<T>::Get | mozilla::dom::indexedDB::`anonymous namespace\'\'::DatabaseConnection::GetCachedStatement'])

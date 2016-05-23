# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import copy
import math
import functools
from datetime import (datetime, timedelta)
from pprint import pprint
import clouseau.socorro as socorro
import clouseau.utils as utils
from clouseau.redash import Redash
from clouseau.connection import Query


def __crash_handler(throttle, json, data):
    factor = 100. / throttle
    for facets in json['facets']['histogram_date']:
        d = datetime.strptime(facets['term'], '%Y-%m-%dT00:00:00+00:00')
        total = float(facets['count']) * factor
        facets = facets['facets']
        is_startup = 'uptime' in facets
        content = 0.
        plugin = 0.
        if 'process_type' in facets:
            pts = facets['process_type']
            for pt in pts:
                if pt['term'] == 'plugin':
                    plugin = float(pt['count']) * factor
                elif pt['term'] == 'content':
                    content = float(pt['count']) * factor

        info = data[d]['socorro']['startup'] if is_startup else data[d]['socorro']['global']
        info['m+c'] += total - plugin
        info['main'] += total - plugin - content
        info['content'] += content
        info['plugin'] += plugin
        info['all'] += total


def get(channel, date, versions=None, product='Firefox', duration=1, credentials=None):
    """Get stability info

    Args:
        channel (str): the channel
        date (str): the final date
        versions (Optional[List[str]]): the versions to treat
        product (Optional[str]): the product
        duration (Optional[int]): the duration to retrieve the data
        credentials (Optional[dict]): credentials

    Returns:
        dict: contains all the info relative to stability
    """
    channel = channel.lower()
    cycle = duration <= 0
    versions_info = socorro.ProductVersions.get_version_info(versions, channel=channel, product=product, credentials=credentials)

    versions = versions_info.keys()
    throttle = set(map(lambda p: p[1], versions_info.values()))
    diff_throttle = len(throttle) != 1
    # normally the throttle is 10% for release and 100% for others channel
    if not diff_throttle:
        throttle = throttle.pop()

    platforms = socorro.Platforms.get_cached_all(credentials=credentials)

    end_date_dt = utils.get_date_ymd(date)
    if cycle:
        # we get all the start date for each versions and get the min
        start_date_dt = min(map(lambda p: utils.get_date_ymd(p[0]), versions_info.values()))
        duration = (end_date_dt - start_date_dt).days + 1
    else:
        start_date_dt = end_date_dt - timedelta(duration - 1)

    start_date_str = utils.get_date_str(start_date_dt)
    end_date_str = utils.get_date_str(end_date_dt)

    # First, we get the ADI
    adi = socorro.ADI.get(version=versions, product=product, end_date=end_date_str, duration=duration, platforms=platforms, credentials=credentials)
    adi = [adi[key] for key in sorted(adi.keys(), reverse=False)]

    # Get the khours
    khours = Redash.get_khours(start_date_dt, end_date_dt, channel, versions, product, credentials=credentials)
    khours = [khours[key] for key in sorted(khours.keys(), reverse=False)]

    # Get the # of crashes (crash pings)
    crash_pings = Redash.get_number_of_crash(start_date_dt, end_date_dt, channel, versions, product, credentials=credentials)

    crashes = {}
    stats = {'m+c': 0.,
             'main': 0.,
             'content': 0.,
             'plugin': 0.,
             'all': 0.}
    for i in range(duration):
        d = end_date_dt - timedelta(i)
        crashes[d] = {}
        crashes[d]['socorro'] = {'global': stats.copy(), 'startup': stats.copy()}
        crashes[d]['telemetry'] = crash_pings[d]

    base = {'product': product,
            'version': None,
            'date': socorro.SuperSearch.get_search_date(start_date_str, end_date_str),
            'release_channel': channel,
            '_results_number': 1,
            '_histogram.date': ['product', 'process_type'],
            '_facets_size': 3}

    if diff_throttle:
        # in this case each version could have a different throttle so we need to compute stats for each version
        queries = []
        for v, t in versions_info.items():
            cparams = base.copy()
            cparams['version'] = v
            queries.append(Query(socorro.SuperSearch.URL, cparams, functools.partial(__crash_handler, t[1]), crashes))
            cparams = copy.deepcopy(cparams)
            cparams['uptime'] = '<60'
            cparams['_histogram.date'].append('uptime')
            queries.append(Query(socorro.SuperSearch.URL, cparams, functools.partial(__crash_handler, t[1]), crashes))
    else:
        base['version'] = versions
        queries = []
        queries.append(Query(socorro.SuperSearch.URL, base, functools.partial(__crash_handler, throttle), crashes))
        cparams = copy.deepcopy(base)
        cparams['uptime'] = '<60'
        cparams['_histogram.date'].append('uptime')
        queries.append(Query(socorro.SuperSearch.URL, cparams, functools.partial(__crash_handler, throttle), crashes))

    socorro.SuperSearch(queries=queries, credentials=credentials).wait()
    crashes = [crashes[key] for key in sorted(crashes.keys(), reverse=False)]

    # Now we compute the rates and the averages
    stats = {'m+c': [0., 0., 0., 0.],
             'main': [0., 0., 0., 0.],
             'content': [0., 0., 0., 0.],
             'plugin': [0., 0., 0., 0.],
             'all': [0., 0., 0., 0.]}
    averages = {}
    averages['socorro'] = {'global': stats, 'startup': copy.deepcopy(stats)}
    averages['telemetry'] = copy.deepcopy(stats)
    N = len(adi)

    # sum
    for i in range(N):
        crash_soc = crashes[i]['socorro']
        for k1, v1 in averages['socorro'].items():
            for k2, av in v1.items():
                c = crash_soc[k1][k2]
                # the rate is computed for 100 adi
                x = utils.rate(100. * c, adi[i])
                av[0] += x
                av[1] += x ** 2
                y = utils.rate(c, khours[i])
                av[2] += y
                av[3] += y ** 2
                crash_soc[k1][k2] = (c, x, y)
        crash_tel = crashes[i]['telemetry']
        for k1, av in averages['telemetry'].items():
            c = crash_tel[k1]
            # the rate is computed for 100 adi
            x = utils.rate(100. * c, adi[i])
            av[0] += x
            av[1] += x ** 2
            y = utils.rate(c, khours[i])
            av[2] += y
            av[3] += y ** 2
            crash_tel[k1] = (c, x, y)

    N = float(N)
    averages_old = {'socorro': {}, 'telemetry': {}}
    averages_new = copy.deepcopy(averages_old)

    # mean & standard deviation
    av_new_soc = averages_new['socorro']
    av_old_soc = averages_old['socorro']
    for k1, v1 in averages['socorro'].items():
        d1 = {}
        av_old_soc[k1] = d1
        d2 = {}
        av_new_soc[k1] = d2
        for k2, av in v1.items():
            m = av[0] / N
            d1[k2] = (m, math.sqrt(av[1] / N - m ** 2))
            m = av[2] / N
            d2[k2] = (m, math.sqrt(av[3] / N - m ** 2))

    av_new_tel = averages_new['telemetry']
    av_old_tel = averages_old['telemetry']
    for k1, av in averages['telemetry'].items():
        m = av[0] / N
        av_old_tel[k1] = (m, math.sqrt(av[1] / N - m ** 2))
        m = av[2] / N
        av_new_tel[k1] = (m, math.sqrt(av[3] / N - m ** 2))

    return {'start_date': start_date_str,
            'end_date': end_date_str,
            'versions': versions,
            'adi': adi,
            'khours': khours,
            'crashes': crashes,
            'averages_old': averages_old,
            'averages_new': averages_new}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Track')
    parser.add_argument('-c', '--channel', action='store', default='release', help='release channel')
    parser.add_argument('-s', '--startdate', action='store', default='', help='the end date')
    parser.add_argument('-e', '--enddate', action='store', default='yesterday', help='the end date')
    parser.add_argument('-D', '--duration', action='store', default=1, type=int, help='the duration')
    parser.add_argument('-p', '--product', action='store', default='Firefox', help='the product')
    parser.add_argument('-v', '--versions', action='store', nargs='+', help='the Firefox versions')
    parser.add_argument('-C', '--credentials', action='store', default='', help='credentials file to use')
    parser.add_argument('--cycle', action='store_true', help='duration is computed to take into account all the cycle')

    args = parser.parse_args()

    credentials = utils.get_credentials(args.credentials) if args.credentials else None
    if args.startdate:
        duration = (utils.get_date_ymd(args.enddate) - utils.get_date_ymd(args.startdate)).days + 1
    else:
        duration = -1 if args.cycle else args.duration
    stats = get(args.channel, args.enddate, product=args.product, versions=args.versions, duration=duration, credentials=credentials)
    pprint(stats)

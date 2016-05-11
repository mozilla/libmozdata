# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
from datetime import datetime
import numbers
import csv
import json
import clouseau.socorro as socorro
import clouseau.utils as utils
from pprint import pprint


def __super_search_handler(json, data):
    for facets in json['facets']['histogram_date']:
        d = datetime.strptime(facets['term'], '%Y-%m-%dT00:00:00+00:00')
        total_crashes = facets['count']
        pt = facets['facets']['process_type']
        plugin_crashes = 0
        content_crashes = 0
        for ty in pt:
            if ty['term'] == 'plugin':
                plugin_crashes = ty['count']
            elif ty['term'] == 'content':
                content_crashes = ty['count']
        browser_crashes = total_crashes - (plugin_crashes + content_crashes)
        if d in data:
            _d = data[d]
            adi = _d['adi']
            _d['browser'] = browser_crashes
            _d['content'] = content_crashes
            _d['plugin'] = plugin_crashes
            _d['b+c'] = browser_crashes + content_crashes
            _d['browser_rate'] = __rate(browser_crashes, adi)
            _d['content_rate'] = __rate(content_crashes, adi)
            _d['b+c_rate'] = __rate(browser_crashes + content_crashes, adi)
            _d['plugin_rate'] = __rate(plugin_crashes + content_crashes, adi)
        else:
            nan = float('nan')
            data[d] = {'adi': 0, 'browser': browser_crashes, 'content': content_crashes, 'plugin': plugin_crashes, 'browser_rate': nan, 'content_rate': nan, 'b+c_rate': nan, 'plugin_rate': nan}


def __rate(n, adi):
    return float('nan') if adi == 0 else float(n) / float(adi) * 100.


def get(channel, versions=None, product='Firefox', start_date=None, end_date='today', duration=30, platforms=None, credentials=None):
    if not isinstance(versions, list):
        if isinstance(versions, numbers.Number):
            versions = socorro.ProductVersions.get_active(vnumber=versions, product=product, credentials=credentials)
        else:
            versions = socorro.ProductVersions.get_active(product=product, credentials=credentials)
        versions = versions[channel.lower()]

    if start_date:
        _sdate = utils.get_date_ymd(start_date)
        _edate = utils.get_date_ymd(end_date)
        duration = (_edate - _sdate).days

    adi = socorro.ADI.get(version=versions, product=product, end_date=end_date, duration=duration, platforms=platforms, credentials=credentials)

    data = {}
    for d, n in adi.items():
        data[d] = {'adi': n, 'browser': 0, 'content': 0, 'plugin': 0, 'browser_rate': 0, 'content_rate': 0, 'b+c_rate': 0, 'plugin_rate': 0}

    start_date = utils.get_date(end_date, duration)
    search_date = socorro.SuperSearch.get_search_date(start_date, end_date)

    socorro.SuperSearch(params={'product': product,
                                'version': versions,
                                'release_channel': channel,
                                'date': search_date,
                                '_results_number': 0,
                                '_facets_size': 2,  # 2 is for a facet on plugin and on content
                                '_histogram.date': ['process_type']},
                        handler=__super_search_handler,
                        handlerdata=data,
                        credentials=credentials).wait()

    return data


def reformat_data(data):
    _data = {}
    for k, v in data.items():
        _data[utils.get_date_str(k)] = v
    return _data


def tocsv(filename, channel, versions=None, product='Firefox', start_date=None, end_date='today', duration=30, platforms=None, credentials=None):
    with open(filename, 'w') as Out:
        writer = csv.writer(Out, delimiter=',')
        data = get(channel, versions, product, start_date, end_date, duration, platforms, credentials)
        data = [(utils.get_date_str(d), data[d]) for d in sorted(data)]
        head = ['date', 'adi', 'browser', 'content', 'b+c', 'plugin', 'browser_rate', 'content_rate', 'b+c_rate', 'plugin_rate']
        writer.writerow(head)

        for d in data:
            row = [d[0], d[1]['adi'], d[1]['browser'], d[1]['content'], d[1]['b+c'], d[1]['plugin'], d[1]['browser_rate'], d[1]['content_rate'], d[1]['b+c_rate'], d[1]['plugin_rate']]
            writer.writerow(row)


def tojson(filename, channel, versions=None, product='Firefox', start_date=None, end_date='today', duration=30, platforms=None, credentials=None):
    with open(filename, 'w') as Out:
        data = get(channel, versions, product, start_date, end_date, duration, platforms, credentials)
        json.dump(reformat_data(data), Out)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Crash Stats')
    parser.add_argument('-f', '--format', action='store', default='csv', help='format')
    parser.add_argument('-o', '--output', action='store', help='output file (csv)')
    parser.add_argument('-s', '--startdate', action='store', help='the start date')
    parser.add_argument('-e', '--enddate', action='store', help='the end date')
    parser.add_argument('-v', '--version', action='store', default=0, help='the base version, e.g. 46')
    parser.add_argument('-c', '--channel', action='store', default='beta', help='release channel')
    parser.add_argument('-p', '--product', action='store', default='Firefox', help='the product, by default Firefox')
    parser.add_argument('-C', '--credentials', action='store', default='', help='credentials file to use')

    args = parser.parse_args()

    credentials = utils.get_credentials(args.credentials) if args.credentials else None
    if args.output:
        if args.format == 'csv':
            tocsv(args.output, args.channel, versions=int(args.version), product=args.product, start_date=args.startdate, end_date=args.enddate, credentials=credentials)
        else:  # json
            tojson(args.output, args.channel, versions=int(args.version), product=args.product, start_date=args.startdate, end_date=args.enddate, credentials=credentials)
    else:
        data = get(args.channel, versions=int(args.version), product=args.product, start_date=args.startdate, end_date=args.enddate, credentials=credentials)
        pprint(reformat_data(data))

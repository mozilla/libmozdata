# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
from urlparse import urlparse
from datetime import (date, datetime, timedelta)
from pprint import pprint
import utils
import math
import re
from FileStats import FileStats
import backtrace
import socorro
import hgmozilla
import memory


class Track(object):
    """
    Track a crash
    """

    def __init__(self, signature, start_date, duration=-1, channel='nightly', product='Firefox', credentials=None):
        """Constructor

        Args:
            signature (str): a crash signature
            start_date (str): a date with format '%Y-%m-%d' used to define the start of the crashes to retrieve
            duration (int): for crashes to retrieve
            channel (Optional[str]): release channel, by default 'nightly'
            credentials (Optional[dict]): credentials to use with Socorro
        """
        self.duration = duration
        self.channel = channel
        self.product = product
        self.credentials = credentials
        self.signature = signature
        self.info = {}
        self.date = utils.get_date_ymd(start_date)
        self.hg_pattern = re.compile('hg:hg.mozilla.org/%s:([^:]*):([a-z0-9]+)' % hgmozilla.Mercurial.get_repo(channel))
        self.__get_info()

    def get(self):
        """Get the info

        Returns:
            dict: info
        """
        self.search.wait()
        return self.info

    def has_addons(self):
        """Has addons

        Returns:
            bool: True if there are addons
        """
        return len(self.get()['addons']) != 0

    @staticmethod
    def __get_min_buildid(bids):
        """Get the minimal date corresponding to each buildids

        Args:
            bids (list): build ids

        Returns:
            datetime: the minimal date
        """
        if bids:
            min_date = utils.get_date_from_buildid(bids[0]['term'])
            for i in range(1, len(bids)):
                d = utils.get_date_from_buildid(bids[i]['term'])
                if d < min_date:
                    min_date = d
            return min_date

        return None

    @staticmethod
    def __get_stats(info, field):
        """Get stats about info[field]

        Args:
            info (dict): data
            field (str): field name

        Returns:
            dict: stats for each entry
        """
        l = info[field]
        total = float(info['total'])
        stats = {}
        for e in l:
            stats[e['term']] = utils.percent(float(e['count']) / total)
        return stats

    @staticmethod
    def __get_mean_stddev(info, field, prettyfy=None):
        """Get mean and standard deviation

        Args:
            info (dict): data
            field (str): field name

        Returns:
            dict: containing mean and std dev
        """
        l = info[field]
        total = float(info['total'])
        l = [(float(e['count']) / total, float(e['term'])) for e in l]
        m = 0.
        for e in l:
            m += e[0] * e[1]

        v = 0.
        for e in l:
            v += e[0] * (m - e[1]) ** 2

        std_dev = math.sqrt(v)

        if prettyfy:
            return {'mean': prettyfy(m), 'stddev': prettyfy(std_dev)}
        else:
            return {'mean': m, 'stddev': std_dev}

    @staticmethod
    def __get_url_stats(info):
        """Get stats about urls

        Args:
            info (dict): data

        Returns:
            dict: stats for each truncated url
        """
        urls = info['url']  # [{'count': ., 'term': .}, ...]
        d = {}
        for url in urls:
            count = url['count']
            url = url['term']
            res = urlparse(url)

            if res.scheme and res.scheme != 'file':  # files don't matter...
                if res.scheme == 'about':
                    simplified_url = 'about:' + res.path
                elif not (res.netloc.startswith('192.168.') or res.netloc == 'localhost'):
                    if res.scheme == 'http' or res.scheme == 'https':
                        simplified_url = res.netloc
                    else:
                        simplified_url = res.scheme + '://' + res.netloc
            else:
                simplified_url = ''

            d[simplified_url] = d[simplified_url] + count if simplified_url in d else count

        return d

    @staticmethod
    def __get_different_bt_stats(info):
        """Get stats about backtraces

        Args:
            info (dict): data

        Returns:
            dict: stats for each backtraces
        """
        _bts = {}
        for uuid, data in info.items():
            bt = data['functions']
            if bt:
                if bt in _bts:
                    _bts[bt].append(uuid)
                else:
                    _bts[bt] = [uuid]

        bts = {}
        common_part = None

        for bt, uuids in _bts.items():
            bts[bt] = (uuids[0], len(uuids))
            if common_part is None:
                common_part = bt
            else:
                n = min(len(common_part), len(bt))
                cp = []
                for i in range(n):
                    f = bt[i]
                    if common_part[i] == f:
                        cp.append(f)
                    else:
                        break
                common_part = cp

        return (bts, common_part)

    @staticmethod
    def __get_bt_stats(info, credentials):
        """Get stats about backtrace

        Args:
            info (dict): data
            credentials (Optional[dict]): credentials to use

        Returns:
            dict: stats for each backtraces
        """
        hits = info['hits']
        uuids = [hit['uuid'] for hit in hits]
        bt_info = backtrace.get_infos(uuids, fraction=1, credentials=credentials)
        total = 0
        rec = 0.
        weird_address = {}
        os_cpu = {}
        cycles = {}
        backtraces = {}
        bts_common_part = None
        if bt_info:
            recursive_bt = 0
            addrs = {}
            backtraces, bts_common_part = Track.__get_different_bt_stats(bt_info)

            total = float(len(bt_info))
            for v in bt_info.values():
                _cycles = v['cycles']
                if _cycles:
                    recursive_bt += 1
                    cycles[_cycles] = cycles[_cycles] + 1 if _cycles in cycles else 1

                addr = v['address']
                t = (addr, v['cpu_name'])
                addrs[t] = addrs[t] + 1 if t in addrs else 1
                t = (v['os'], v['cpu_name'])
                os_cpu[t] = os_cpu[t] + 1 if t in os_cpu else 1

            rec = utils.percent(float(recursive_bt) / total)

            for k, v in os_cpu.items():
                os_cpu[k] = utils.percent(float(v) / total)

            for k, v in addrs.items():
                percent = float(v) / total
                if memory.isweird(*k):
                    weird_address[k] = utils.percent(percent)
                elif percent >= 0.25:
                    weird_address[k] = utils.percent(percent)

            _addrs = []
            for k in addrs.iterkeys():
                _addrs.append(k[0])

            total = int(total)

        return {'sample_size': total,
                'bt_has_rec': rec,
                'weird_address': weird_address,
                'cycles': cycles,
                'os_cpu': os_cpu,
                'backtraces': backtraces,
                'common_part': bts_common_part}

    def __get_filename_node(self, path):
        """Get node for file name from path

        Args:
            path (str): path from socorro

        Returns:
            (str, str): filename and node
        """
        if path:
            m = self.hg_pattern.search(path)
            if m:
                filename = m.group(1)
                node = m.group(2)
            else:
                filename = path
                node = ''
            return (filename, node)
        return (None, None)

    def __get_topmost_filename(self, info):
        """Get topmost filename

        Args:
            info (dict): data

        Returns:
            (str, str): filename and node
        """
        hits = info['hits']
        fn = {}
        for hit in hits:
            name = hit['topmost_filenames']
            if name:
                fn[name] = fn[name] + 1 if name in fn else 1

        return self.__get_filename_node(utils.get_best(fn))

    def __walk_on_the_backtrace(self):
        """All is in the function name

        Returns:
            dict: file info
        """
        btinfo = self.info['btinfo']
        bt_common_part = btinfo['common_part']
        backtraces = btinfo['backtraces']

        # get the uuid where the bt has the better stats
        uuid = max(backtraces.items(), key=lambda x: x[1][1])[1][0]

        fileinfo = None
        bt = backtrace.get_files(uuid, common=bt_common_part, credentials=self.credentials)
        if len(bt) >= 2:
            ts = utils.get_timestamp(self.first_date)
            # remove the first (already done)
            for i in range(1, len(bt)):
                m = self.hg_pattern.match(bt[i])
                if m:
                    filename = m.group(1)
                    node = m.group(2)
                    fs = FileStats(path=filename, channel=self.channel, node=node, utc_ts=ts, credentials=self.credentials)
                    fileinfo = fs.get_info(dig_when_non_pertinent=False)
                    if fileinfo:
                        # hurrah \o/ we found a pertinent file !
                        break
        return fileinfo

    def __handler(self, json, data):
        """Handler for Socorro supersearch

        Args:
            json (dict): json
            data (dict): dictionary to update with data
        """
        total = json['total']
        info = {'total': total, 'hits': json['hits']}
        info.update(json['facets'])

        # we get the first date of appearance in using the different buildid
        self.first_date = Track.__get_min_buildid(info['build_id'])

        filename, node = self.__get_topmost_filename(info)
        self.info['filename'] = filename
        self.info['node'] = node
        self.info['total'] = total
        self.info['platforms'] = Track.__get_stats(info, 'platform_pretty_version')
        self.info['buildids'] = Track.__get_stats(info, 'build_id')
        self.info['versions'] = Track.__get_stats(info, 'version')
        self.info['cpu_name'] = Track.__get_stats(info, 'cpu_name')
        self.info['cpu_info'] = Track.__get_stats(info, 'cpu_info')
        self.info['reason'] = Track.__get_stats(info, 'reason')
        self.info['system_memory_use'] = Track.__get_mean_stddev(info, 'system_memory_use_percentage', prettyfy=lambda x: utils.simple_percent(round(x, 0)))
        self.info['uptime'] = Track.__get_mean_stddev(info, 'uptime', prettyfy=lambda x: str(x) + 's')
        self.info['btinfo'] = Track.__get_bt_stats(info, self.credentials)

        Track.__get_url_stats(info)

        ts = utils.get_timestamp(self.first_date)
        fs = FileStats(path=filename, channel=self.channel, node=node, utc_ts=ts, credentials=self.credentials)
        # don't dig: if non-pertinent we'll try in the next function in the backtrace
        fileinfo = fs.get_info(dig_when_non_pertinent=False)
        if fileinfo and fileinfo['guilty']:
            self.info['fileinfo'] = fileinfo
        else:
            fileinfo = self.__walk_on_the_backtrace()
            if fileinfo:
                self.info['fileinfo'] = fileinfo
            else:
                # didn't find out any guilty patches... :(
                self.info['fileinfo'] = fs.get_info(dig_when_non_pertinent=True)

    def __get_info(self):
        """Retrieve information
        """
        start_date = utils.get_date_str(self.date)
        if self.duration < 0:
            search_date = ['>=' + start_date]
        else:
            end_date = self.date + timedelta(self.duration)
            today = date.today()
            today = datetime(today.year, today.month, today.day)
            if end_date > today:
                search_date = ['>=' + start_date]
            else:
                search_date = ['>=' + start_date, '<' + utils.get_date_str(end_date)]

        nb_hits = []
        socorro.SuperSearch(params={'product': self.product,
                                    'signature': '=' + self.signature,
                                    'date': search_date,
                                    'release_channel': self.channel,
                                    '_results_number': 0},
                            handler=lambda json, data: nb_hits.append(json['total']),
                            credentials=self.credentials).wait()

        if nb_hits[0] > 1000:
            nb_hits[0] = 1000

        self.search = socorro.SuperSearch(params={'product': self.product,
                                                  'signature': '=' + self.signature,
                                                  'date': search_date,
                                                  'release_channel': self.channel,
                                                  '_sort': 'build_id',
                                                  '_columns': ['uuid', 'topmost_filenames'],
                                                  '_facets': ['platform_pretty_version',
                                                              'build_id',
                                                              'version',
                                                              'system_memory_use_percentage',
                                                              'cpu_name',
                                                              'cpu_info',
                                                              'reason',
                                                              'addons',
                                                              'uptime',
                                                              'url'],
                                                  '_facets_size': nb_hits[0],
                                                  '_results_number': nb_hits[0]},
                                          handler=self.__handler,
                                          credentials=self.credentials)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Track')
    parser.add_argument('-s', '--signature', action='store', help='crash signature as in Socorro')
    parser.add_argument('-S', '--startdate', action='store', default='today', help='the start date to retrieve crash info')
    parser.add_argument('-d', '--duration', action='store', default=-1, help='the number of day after the start date')
    parser.add_argument('-c', '--channel', action='store', default='nightly', help='release channel')
    parser.add_argument('-p', '--product', action='store', default='Firefox', help='the product, by default Firefox')
    parser.add_argument('-C', '--credentials', action='store', default='', help='credentials file to use')

    args = parser.parse_args()

    if args.signature:
        credentials = utils.get_credentials(args.credentials) if args.credentials else None
        t = Track(signature=args.signature, start_date=args.startdate, duration=int(args.duration), channel=args.channel, product=args.product, credentials=credentials)
        pprint(t.get())

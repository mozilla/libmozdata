# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import six
import functools
from operator import itemgetter
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
from .connection import (Connection, Query)
from . import utils
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from . import config


class Socorro(Connection):
    """Socorro connection: https://crash-stats.mozilla.com
    """

    CRASH_STATS_URL = config.get('Socorro', 'URL', 'https://crash-stats.mozilla.com')
    API_URL = CRASH_STATS_URL + '/api'
    TOKEN = config.get('Socorro', 'token', '')

    def __init__(self, queries, **kwargs):
        """Constructor

        Args:
            queries (List[Query]): queries to pass to Socorro
        """
        super(Socorro, self).__init__(self.CRASH_STATS_URL, queries=queries, **kwargs)

    def get_header(self):
        header = super(Socorro, self).get_header()
        header['Auth-Token'] = self.get_apikey()
        return header


class SuperSearch(Socorro):
    """SuperSearch: https://crash-stats.mozilla.com/search/?product=&_dont_run=1
    """

    URL = Socorro.API_URL + '/SuperSearch'
    URL_UNREDACTED = URL + 'Unredacted'
    WEB_URL = Socorro.CRASH_STATS_URL + '/search'

    def __init__(self, params=None, handler=None, handlerdata=None, queries=None, **kwargs):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            queries (Optional[List[Query]]): queries to execute
        """
        if queries is not None:
            super(SuperSearch, self).__init__(queries, **kwargs)
        else:
            url = SuperSearch.URL
            unredacted = False
            if '_facets' in params:
                facets = params['_facets']
                if 'url' in facets or 'email' in facets:
                    url = SuperSearch.URL_UNREDACTED
                    unredacted = True
            if not unredacted and '_columns' in params:
                columns = params['_columns']
                if 'url' in columns or 'email' in columns:
                    url = SuperSearch.URL_UNREDACTED
            if not unredacted:
                for k, v in params.items():
                    if 'url' in k or 'email' in k or ((isinstance(v, list) or isinstance(v, six.string_types)) and ('url' in v or 'email' in v)):
                        url = SuperSearch.URL_UNREDACTED
                        unredacted = True
                        break

            super(SuperSearch, self).__init__(Query(url, params, handler, handlerdata), **kwargs)

    @staticmethod
    def get_link(params):
        return utils.get_url(SuperSearch.WEB_URL) + utils.get_params_for_url(params)

    @staticmethod
    def get_search_date(start, end=None):
        """Get a search date list for [start, end[ (end can be in the future)

        Args:
            start (str): start date in 'YYYY-mm-dd' format or 'today'
            end (str): start date in 'YYYY-mm-dd' format or 'today'

        Returns:
            List(str): containing acceptable interval for Socorro.SuperSearch
        """
        _start = utils.get_date(start)

        if end:
            _end = utils.get_date_ymd(end)
            today = utils.get_date_ymd('today')
            if _end > today:
                search_date = ['>=' + _start]
            else:
                search_date = ['>=' + _start, '<' + utils.get_date_str(_end)]
        else:
            search_date = ['>=' + _start]

        return search_date


class ProcessedCrash(Socorro):
    """ProcessedCrash: https://crash-stats.mozilla.com/api/#ProcessedCrash
    """

    URL = Socorro.API_URL + '/ProcessedCrash'

    def __init__(self, params=None, handler=None, handlerdata=None, queries=None, **kwargs):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            queries (Optional[List[Query]]): queries to execute
        """
        if queries:
            super(ProcessedCrash, self).__init__(queries, **kwargs)
        else:
            super(ProcessedCrash, self).__init__(Query(ProcessedCrash.URL, params, handler, handlerdata), **kwargs)

    @staticmethod
    def default_handler(json, data):
        """Default handler

        Args:
            json (dict): json
            data (dict): dictionary to update with data
        """
        data.update(json)

    @staticmethod
    def get_processed(crashids):
        """Get processed crashes

        Args:
            crashids (Optional[list[str]]): the crash ids

        Returns:
            dict: the processed crashes
        """

        data = {}
        __base = {'crash_id': None,
                  'datatype': 'processed'}

        if isinstance(crashids, six.string_types):
            __base['crash_id'] = crashids
            _dict = {}
            data[crashids] = _dict
            ProcessedCrash(params=__base, handler=ProcessedCrash.default_handler, handlerdata=_dict).wait()
        else:
            queries = []
            for crashid in crashids:
                cparams = __base.copy()
                cparams['crash_id'] = crashid
                _dict = {}
                data[crashid] = _dict
                queries.append(Query(ProcessedCrash.URL, cparams, ProcessedCrash.default_handler, _dict))
            ProcessedCrash(queries=queries).wait()

        return data


class Platforms(Socorro):
    """Platforms: https://crash-stats.mozilla.com/api/#Platforms
    """

    URL = Socorro.API_URL + '/Platforms'
    __cached_platforms = None

    def __init__(self, params=None, handler=None, handlerdata=None, **kwargs):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            queries (Optional[List[Query]]): queries to execute
        """
        super(Platforms, self).__init__(Query(Platforms.URL, params, handler, handlerdata), **kwargs)

    @staticmethod
    def get_cached_all():
        """Get all the platforms

        Returns:
            List[str]: the different platforms
        """
        if not Platforms.__cached_platforms:
            Platforms.__cached_platforms = Platforms.get_all()

        return Platforms.__cached_platforms

    @staticmethod
    def default_handler(json, data):
        """Default handler

        Args:
            json (dict): json
            data (list): list to append the platforms name
        """
        for code in json:
            data.append(code['name'])

    @staticmethod
    def get_all():
        """Get all the platforms

        Returns:
            List[str]: the different platforms
        """
        platforms = []
        Platforms(handler=Platforms.default_handler, handlerdata=platforms).wait()
        return platforms


class ProductVersions(Socorro):
    """ProductVersions: https://crash-stats.mozilla.com/api/#ProductVersions
    """

    URL = Socorro.API_URL + '/ProductVersions'
    __cached_versions = {}

    def __init__(self, params=None, handler=None, handlerdata=None, **kwargs):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
        """
        super(ProductVersions, self).__init__(Query(ProductVersions.URL, params, handler, handlerdata), **kwargs)

    @staticmethod
    def get_cached_versions(product='Firefox'):
        """Get the versions (which has been put in a cache)

        Args:
            product (Optional[str]): product to use, by default 'Firefox'

        Returns:
            dict: versions
        """
        if product not in ProductVersions.__cached_versions:
            ProductVersions.__cached_versions[product] = ProductVersions.get_active(product)
        return ProductVersions.__cached_versions[product]

    @staticmethod
    def get_last_version(channel, product='Firefox'):
        """Get last version for a channel

        Args:
            channel (str): 'nightly', 'aurora', 'beta' or 'release'
            product (Optional[str]): product to use, by default 'Firefox'

        Returns:
            str: the last version corresponding to the channel
        """
        return ProductVersions.get_versions(channel, product)[0]

    @staticmethod
    def get_versions(channel, product='Firefox'):
        """Get last version for a channel

        Args:
            channel (str): 'nightly', 'aurora', 'beta' or 'release'
            product (Optional[str]): product to use, by default 'Firefox'

        Returns:
            str: the last version corresponding to the channel
        """
        if channel:
            return [p[1] for p in ProductVersions.get_cached_versions(product)[channel.lower()]]
        else:
            return None

    @staticmethod
    def get_major_version(v):
        """Get major version number

        Args:
            v (str): if v == 'V.x.y' then return V

        Returns:
           int: the major version number
        """
        # version is '45.x.y' or maybe '45'
        v = v.split('.')
        if v and v[0].isdigit():
            return int(v[0])
        else:
            return None

    @staticmethod
    def default_handler(number, json, data):
        """Default handler

        Args:
            number (int): version number
            json (dict): json
            data (list): list to append the platforms name
        """
        if json['total']:
            _data = {}
            ffs = json['hits']
            for ff in ffs:
                build_type = ff['build_type'].lower()  # release, beta, aurora, nightly
                start_date = ff['start_date']
                throttle = ff['throttle']
                version = ff['version']  # 45.x
                version_n = ProductVersions.get_major_version(version)
                # take only the latest versions, e.g. if 45.x and 44.x are "release"
                # then 45.x is only considered
                if number:
                    if number == version_n:
                        vst = (version, start_date, throttle)
                        if build_type in _data:
                            _data[build_type][1].append(vst)
                        else:
                            _data[build_type] = (version_n, [vst])
                else:
                    vst = (version, start_date, throttle)
                    if build_type in _data:
                        t = _data[build_type]
                        if version_n == t[0]:
                            t[1].append(vst)
                        elif version_n > t[0]:
                            _data[build_type] = (version_n, [vst])
                    else:
                        _data[build_type] = (version_n, [vst])

            for k, v in _data.items():
                versions = v[1]
                if len(versions) > 1:
                    sorted(versions, key=lambda t: utils.get_date_ymd(t[1]))
                data[k] = versions

    @staticmethod
    def get_active(product='Firefox', vnumber=None, active=True, is_rapid_beta=False, remove_dates=True, remove_throttle=True):
        """Get the active versions

        Args:
            product (Optional[str]): product to use, by default 'Firefox'
            vnumber (Optional[int]): a version number 45, 46, ...
            is_rapid_beta (Optional[bool]): for version which are rapid beta, by default False
            remove_dates (Optional[bool]): if True, the date info are removed
            remove_throttle (Optional[bool]): if True, the throttle info are removed

        Returns:
            dict: versions
        """
        versions = {}
        ProductVersions(params={'active': active,
                                'product': product,
                                'is_rapid_beta': is_rapid_beta},
                        handler=functools.partial(ProductVersions.default_handler, vnumber), handlerdata=versions).wait()

        index = [0]
        if not remove_dates:
            index.append(1)
        if not remove_throttle:
            index.append(2)

        if index != [0, 1, 2]:
            _versions = {}
            for k, v in versions.items():
                _versions[k] = list(map(lambda p: itemgetter(*index)(p), v))
            return _versions

        return versions

    @staticmethod
    def get_throttle(versions, product='Firefox', remove_dates=True):
        """Get the throttle for versions

        Args:
            versions (List[str]): versions
            product (Optional[str]): product to use, by default 'Firefox'
            remove_dates (Optional[bool]): if True, the date info are removed

        Returns:
            dict: throttle info for each versions
        """
        def handler(json, data):
            for hit in json['hits']:
                if remove_dates:
                    data[hit['version']] = hit['throttle']
                else:
                    data[hit['version']] = (hit['start_date'], hit['throttle'])

        data = {}
        ProductVersions(params={'version': versions,
                                'product': product},
                        handler=handler, handlerdata=data).wait()

        return data

    @staticmethod
    def get_version_info(versions, channel='', product='Firefox'):
        """Get the throttle for versions

        Args:
            versions (List[str]): versions
            channel (Optional[str]): the channel
            product (Optional[str]): product to use, by default 'Firefox'

        Returns:
            dict: version info
        """
        if not isinstance(versions, list):
            versions = [versions]

        info = {}
        if versions:
            v_without_throttle = []
            for v in versions:
                if isinstance(v, six.integer_types) or (isinstance(v, six.string_types) and '.' not in v):
                    vs = ProductVersions.get_active(vnumber=int(v), product=product, active=None, remove_dates=False, remove_throttle=False)[channel]
                    for v in vs:
                        info[v[0]] = v[1:]
                elif isinstance(v, six.string_types):
                    v_without_throttle.append(v)

            if v_without_throttle:
                t = ProductVersions.get_throttle(v_without_throttle, product=product, remove_dates=False)
                info.update(t)
        else:
            vs = ProductVersions.get_active(product=product, active=None, remove_dates=False, remove_throttle=False)[channel]
            for v in vs:
                info[v[0]] = v[1:]

        return info

    @staticmethod
    def get_info_from_major(major_numbers, product='Firefox', active=True):
        """Get information for a given channel and major number version

        Args:
            major_numbers (dict): a dictionary channel->major_number_version
            product (Optional[str]): the product to use, by default 'Firefox'
            active (Optional[bool]): True for actives versions

        Returns:
            dict: version info
        """
        def handler(json, data, majors=major_numbers):
            if json['total']:
                ffs = json['hits']
                for ff in ffs:
                    build_type = ff['build_type'].lower()
                    if build_type in majors:
                        version = ff['version']  # 45.x
                        version_n = ProductVersions.get_major_version(version)
                        if version_n == majors[build_type]:
                            info = {'version': version,
                                    'throttle': ff['throttle'],
                                    'start_date': ff['start_date'],
                                    'end_date': ff['end_date']}
                            data[build_type].append(info)

        data = {chan: [] for chan in major_numbers.keys()}
        ProductVersions(params={'active': active,
                                'product': product},
                        handler=handler, handlerdata=data).wait()
        return data

    @staticmethod
    def get_all_versions(product='Firefox'):
        """Get information for a given channel and major number version

        Args:
            major_numbers (dict): a dictionary channel->major_number_version
            product (Optional[str]): the product to use, by default 'Firefox'
            active (Optional[bool]): True for actives versions

        Returns:
            dict: version info
        """
        def handler(json, data):
            if json['total']:
                ffs = json['hits']
                for ff in ffs:
                    channel = ff['build_type'].lower()
                    start_date = utils.get_date_ymd(ff['start_date'])
                    version = ff['version']  # 45.x
                    version_n = ProductVersions.get_major_version(version)  # 45
                    info = data[channel]
                    if version_n in info:
                        info[version_n]['versions'][version] = start_date
                        if start_date < info[version_n]['dates'][0]:
                            info[version_n]['dates'][0] = start_date
                    else:
                        info[version_n] = {'dates': [start_date], 'all': [], 'versions': {version: start_date}}
                    if not version.endswith('b'):
                        info[version_n]['all'].append(version)

        data = {'nightly': {}, 'aurora': {}, 'beta': {}, 'release': {}, 'esr': {}}
        ProductVersions(params={'product': product},
                        handler=handler, handlerdata=data).wait()

        for info in data.values():
            keys = sorted(info.keys())
            for i in range(len(keys)):
                if i != len(keys) - 1:
                    end_date = info[keys[i + 1]]['dates'][0] - relativedelta(days=1)
                else:
                    end_date = None
                info[keys[i]]['dates'].append(end_date)

        return data


class TCBS(Socorro):
    """TCBS: https://crash-stats.mozilla.com/api/#TCBS
    """

    URL = Socorro.API_URL + '/TCBS'

    def __init__(self, params=None, handler=None, handlerdata=None, queries=None, **kwargs):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            queries (Optional[List[Query]]): queries to execute
        """
        if queries:
            super(TCBS, self).__init__(queries, **kwargs)
        else:
            super(TCBS, self).__init__(Query(TCBS.URL, params, handler, handlerdata), **kwargs)

    @staticmethod
    def default_handler(json, data):
        """Default handler

        Args:
            json (dict): json
            data (list): list to append the platforms name
        """
        data.append(json)

    @staticmethod
    def get_firefox_topcrashes(version=None, channel=None, days=7, crash_type='all', limit=50, platforms=None):
        """Get top crashes for Firefox

        Args:
            version (Optional[str]): the version
            channel (Optional[str]): 'nightly', 'aurora', 'beta' or 'release'
            days (Optional[int]): the duration
            crash_type (Optional[str]): 'all' (default) or 'browser' or 'content' or 'plugin'
            limit (Optional[int]): the number of crashes to retrieve
            platforms (Optional[str]): 'all' or 'windows' or 'linux' or 'mac os x'

        Returns:
            dict: a json
        """
        if not version:
            version = ProductVersions.get_last_version(channel)
            if not version:
                return None

        data = []
        TCBS(params={'product': 'Firefox',
                     'version': version,
                     'crash_type': crash_type,
                     'limit': limit,
                     'os': platforms,
                     'duration': days * 24},  # duration is expressed in hours !!
             handler=TCBS.default_handler, handlerdata=data).wait()

        return data[0]


class SignatureTrend(Socorro):
    """SignatureTrend: https://crash-stats.mozilla.com/api/#SignatureTrend
    """

    URL = Socorro.API_URL + '/SignatureTrend'

    def __init__(self, params=None, handler=None, handlerdata=None, queries=None, **kwargs):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            queries (Optional[List[Query]]): queries to execute
        """
        if queries:
            super(SignatureTrend, self).__init__(queries, **kwargs)
        else:
            super(SignatureTrend, self).__init__(Query(SignatureTrend.URL, params, handler, handlerdata), **kwargs)

    @staticmethod
    def default_handler(json, data):
        """Default handler

        Args:
            json (dict): json
            data (list): list to append the platforms name
        """
        if json['total']:
            data += json['hits']

    @staticmethod
    def get_trend(signatures, version=None, channel=None, duration=7, end_date='today', product='Firefox'):
        """Get signatures trend

        Args:
            version (Optional[str]): the version
            channel (Optional[str]): 'nightly', 'aurora', 'beta' or 'release'
            duration (Optional[int]): the duration
            end_date (Optional[str]): the last date
            product: (Optional[str]): the product, by default 'Firefox'

        Returns:
            dict: the trend for each signature
        """
        if not version:
            version = ProductVersions.get_last_version(channel)
            if not version:
                return None

        data = {}
        start_date = utils.get_date(end_date, duration)
        end_date = utils.get_date(end_date)
        __base = {'product': product,
                  'version': version,
                  'start_date': start_date,
                  'end_date': end_date,
                  'signature': None}

        if isinstance(signatures, six.string_types):
            __base['signature'] = signatures
            _list = []
            data[signatures] = _list
            SignatureTrend(params=__base, handler=SignatureTrend.default_handler, handlerdata=_list).wait()
        else:
            queries = []
            for signature in signatures:
                cparams = __base.copy()
                cparams['signature'] = signature
                _list = []
                data[signature] = _list
                queries.append(Query(SignatureTrend.URL, cparams, SignatureTrend.default_handler, _list))
            SignatureTrend(queries=queries).wait()

        return data


class ADI(Socorro):
    """ADI: https://crash-stats.mozilla.com/api/#ADI
    """

    URL = Socorro.API_URL + '/ADI'

    def __init__(self, params=None, handler=None, handlerdata=None, queries=None, **kwargs):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            queries (Optional[List[Query]]): queries to execute
        """
        if queries:
            super(ADI, self).__init__(queries, **kwargs)
        else:
            super(ADI, self).__init__(Query(ADI.URL, params, handler, handlerdata), **kwargs)

    @staticmethod
    def default_handler(json, data):
        """Default handler

        Args:
            json (dict): json
            data (list): list to append the platforms name
        """
        if json['total']:
            for adi in json['hits']:
                date = utils.get_date_ymd(adi['date'])
                adi_count = adi['adi_count']
                data[date] = data[date] + adi_count if date in data else adi_count

    @staticmethod
    def get(version=None, channel=None, duration=7, end_date='today', product='Firefox', platforms=None):
        """Get ADI

        Args:
            version (Optional[str]): the version
            channel (Optional[str]): 'nightly', 'aurora', 'beta' or 'release'
            duration (Optional[int]): the duration
            end_date (Optional[str]): the last date
            product: (Optional[str]): the product, by default 'Firefox'
            platforms: (Optional[list[str]]): list of platforms

        Returns:
            dict: the trend for each signature
        """
        if not version:
            version = ProductVersions.get_last_version(channel)
            if not version:
                return None

        data = {}
        start_date = utils.get_date(end_date, duration - 1)
        end_date = utils.get_date(end_date)

        start_date_dt = utils.get_date_ymd(start_date)
        for i in range(duration):
            data[start_date_dt + timedelta(i)] = 0

        ADI(params={'product': product,
                    'versions': version,
                    'start_date': start_date,
                    'end_date': end_date,
                    'platforms': platforms if platforms else Platforms.get_cached_all()},
            handler=ADI.default_handler,
            handlerdata=data).wait()

        return data


class SignatureURLs(Socorro):
    """SignatureURLs: https://crash-stats.mozilla.com/api/#SignatureURLs
    """

    URL = Socorro.API_URL + '/SignatureURLs'

    def __init__(self, params=None, handler=None, handlerdata=None, queries=None, **kwargs):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            queries (Optional[List[Query]]): queries to execute
        """
        if queries:
            super(SignatureURLs, self).__init__(queries, **kwargs)
        else:
            super(SignatureURLs, self).__init__(Query(SignatureURLs.URL, params, handler, handlerdata), **kwargs)

    @staticmethod
    def get_default_handler(trunc):
        def handler(json, data):
            """Default handler

            Args:
                json (dict): json
                data (list): list to append the urls
            """
            if json['total']:
                for hit in json['hits']:
                    if 'url' in hit:
                        url = hit['url']
                        if trunc:
                            url = urlparse(url).netloc
                        count = hit['crash_count']
                        data[url] = data[url] + count if url in data else count

        return handler

    @staticmethod
    def get_urls(signatures, version=None, channel=None, duration=7, end_date='today', product='Firefox', trunc=True):
        """Get signatures urls

        Args:
            signatures (List[str]): the signatures
            version (Optional[str]): the version
            channel (Optional[str]): 'nightly', 'aurora', 'beta' or 'release'
            duration (Optional[int]): the duration
            end_date (Optional[str]): the last date
            trunc (Optional[bool]): if True, then the url are truncated to their first part (netloc)
                                    e.g. http://foo.com/bar/blah/blah.html will be truncated in foo.com

        Returns:
            dict: the URLs for each signature
        """
        if not version:
            version = ProductVersions.get_last_version(channel)
            if not version:
                return None

        data = {}
        start_date = utils.get_date(end_date, duration)
        end_date = utils.get_date(end_date)
        __base = {'products': product,
                  'versions': '%s:%s' % (product, version),
                  'start_date': start_date,
                  'end_date': end_date,
                  'signature': None}
        handler = SignatureURLs.get_default_handler(trunc)

        if isinstance(signatures, six.string_types):
            __base['signature'] = signatures
            _list = []
            data[signatures] = _list
            SignatureURLs(params=__base, handler=handler, handlerdata=_list).wait()
        else:
            queries = []
            for signature in signatures:
                cparams = __base.copy()
                cparams['signature'] = signature
                _list = []
                data[signature] = _list
                queries.append(Query(SignatureURLs.URL, cparams, handler, _list))
            SignatureURLs(queries=queries).wait()

        return data


class Bugs(Socorro):
    """Bugs: https://crash-stats.mozilla.com/api/#Bugs
    """

    URL = Socorro.API_URL + '/Bugs'

    def __init__(self, params=None, handler=None, handlerdata=None, queries=None, **kwargs):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            queries (Optional[List[Query]]): queries to execute
        """
        if queries:
            super(Bugs, self).__init__(queries, **kwargs)
        else:
            super(Bugs, self).__init__(Query(Bugs.URL, params, handler, handlerdata), **kwargs)

    @staticmethod
    def get_bugs(signatures):
        """Get signatures bugs

        Args:
            signatures (List[str]): the signatures

        Returns:
            dict: the bugs for each signature
        """
        def default_handler(json, data):
            if json['total']:
                for hit in json['hits']:
                    signature = hit['signature']
                    if signature in data:
                        data[signature].add(hit['id'])

        if isinstance(signatures, six.string_types):
            data = {signatures: set()}
            Bugs(params={'signatures': signatures}, handler=default_handler, handlerdata=data).wait()
        else:
            data = {s: set() for s in signatures}
            queries = []
            for sgns in Connection.chunks(signatures, 10):
                queries.append(Query(Bugs.URL, {'signatures': sgns}, default_handler, data))
            Bugs(queries=queries).wait()

        for k, v in data.items():
            data[k] = list(v)

        return data

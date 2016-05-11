# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import six
import functools
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
from .connection import (Connection, Query)
from . import utils
from datetime import timedelta


class Socorro(Connection):
    """Socorro connection: https://crash-stats.mozilla.com
    """

    CRASH_STATS_URL = 'https://crash-stats.mozilla.com'
    API_URL = CRASH_STATS_URL + '/api'

    def __init__(self, queries, credentials=None):
        """Constructor

        Args:
            queries (List[Query]): queries to pass to Socorro
            credentials (Optional[dict]): credentials to use with Socorro
        """
        super(Socorro, self).__init__(self.CRASH_STATS_URL, queries=queries, credentials=credentials)

    def get_header(self):
        return {'Auth-Token': self.get_apikey(self.CRASH_STATS_URL)}


class SuperSearch(Socorro):
    """SuperSearch: https://crash-stats.mozilla.com/search/?product=&_dont_run=1
    """

    URL = Socorro.API_URL + '/SuperSearch'
    URL_UNREDACTED = URL + 'Unredacted'

    def __init__(self, params=None, handler=None, handlerdata=None, credentials=None, queries=None):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            credentials (Optional[dict]): credentials to use with Socorro
            queries (Optional[List[Query]]): queries to execute
        """
        if queries:
            super(SuperSearch, self).__init__(queries, credentials)
        else:
            url = SuperSearch.URL
            if '_facets' in params:
                facets = params['_facets']
                if 'url' in facets or 'email' in facets:
                    url = SuperSearch.URL_UNREDACTED
            super(SuperSearch, self).__init__(Query(url, params, handler, handlerdata), credentials)

    @staticmethod
    def get_search_date(start, end):
        """Get a search date list for [start, end[ (end can be in the future)

        Args:
            start (str): start date in 'YYYY-mm-dd' format or 'today'
            end (str): start date in 'YYYY-mm-dd' format por 'today'

        Returns:
            List(str): containing acceptabl interval for Socorro.SuperSearch
        """
        _start = utils.get_date(start)
        _end = utils.get_date_ymd(end) + timedelta(1)
        today = utils.get_date_ymd('today')
        if _end > today:
            search_date = ['>=' + _start]
        else:
            search_date = ['>=' + _start, '<' + utils.get_date_str(_end)]

        return search_date


class ProcessedCrash(Socorro):
    """ProcessedCrash: https://crash-stats.mozilla.com/api/#ProcessedCrash
    """

    URL = Socorro.API_URL + '/ProcessedCrash'

    def __init__(self, params=None, handler=None, handlerdata=None, credentials=None, queries=None):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            credentials (Optional[dict]): credentials to use with Socorro
            queries (Optional[List[Query]]): queries to execute
        """
        if queries:
            super(ProcessedCrash, self).__init__(queries, credentials)
        else:
            super(ProcessedCrash, self).__init__(Query(ProcessedCrash.URL, params, handler, handlerdata), credentials)

    @staticmethod
    def default_handler(json, data):
        """Default handler

        Args:
            json (dict): json
            data (dict): dictionary to update with data
        """
        data.update(json)

    @staticmethod
    def get_processed(crashids, credentials=None):
        """Get processed crashes

        Args:
            crashids (Optional[list[str]]): the crash ids
            credentials (Optional[dict]): credentials to use with Socorro

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
            ProcessedCrash(params=__base, credentials=credentials, handler=ProcessedCrash.default_handler, handlerdata=_dict).wait()
        else:
            queries = []
            for crashid in crashids:
                cparams = __base.copy()
                cparams['crash_id'] = crashid
                _dict = {}
                data[crashid] = _dict
                queries.append(Query(ProcessedCrash.URL, cparams, ProcessedCrash.default_handler, _dict))
            ProcessedCrash(queries=queries, credentials=credentials).wait()

        return data


class Platforms(Socorro):
    """Platforms: https://crash-stats.mozilla.com/api/#Platforms
    """

    URL = Socorro.API_URL + '/Platforms'
    __cached_platforms = None

    def __init__(self, params=None, handler=None, handlerdata=None, credentials=None):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            credentials (Optional[dict]): credentials to use with Socorro
            queries (Optional[List[Query]]): queries to execute
        """
        super(Platforms, self).__init__(Query(Platforms.URL, params, handler, handlerdata), credentials)

    @staticmethod
    def get_cached_all(credentials=None):
        """Get all the platforms

        Args:
            credentials (Optional[dict]): credentials to use with Socorro

        Returns:
            List[str]: the different platforms
        """
        if not Platforms.__cached_platforms:
            Platforms.__cached_platforms = Platforms.get_all(credentials)

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
    def get_all(credentials=None):
        """Get all the platforms

        Args:
            credentials (Optional[dict]): credentials to use with Socorro

        Returns:
            List[str]: the different platforms
        """
        platforms = []
        Platforms(credentials=credentials, handler=Platforms.default_handler, handlerdata=platforms).wait()
        return platforms


class ProductVersions(Socorro):
    """ProductVersions: https://crash-stats.mozilla.com/api/#ProductVersions
    """

    URL = Socorro.API_URL + '/ProductVersions'
    __cached_versions = {}

    def __init__(self, params=None, handler=None, handlerdata=None, credentials=None):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            credentials (Optional[dict]): credentials to use with Socorro
        """
        super(ProductVersions, self).__init__(Query(ProductVersions.URL, params, handler, handlerdata), credentials)

    @staticmethod
    def get_cached_versions(product='Firefox', credentials=None):
        """Get the versions (which has been put in a cache)

        Args:
            product (Optional[str]): product to use, by default 'Firefox'
            credentials (Optional[dict]): credentials to use with Socorro

        Returns:
            dict: versions
        """
        if product not in ProductVersions.__cached_versions:
            ProductVersions.__cached_versions[product] = ProductVersions.get_active(product, credentials=credentials)
        return ProductVersions.__cached_versions[product]

    @staticmethod
    def get_last_version(channel, product='Firefox', credentials=None):
        """Get last version for a channel

        Args:
            channel (str): 'nightly', 'aurora', 'beta' or 'release'
            product (Optional[str]): product to use, by default 'Firefox'
            credentials (Optional[dict]): credentials to use with Socorro

        Returns:
            str: the last version corresponding to the channel
        """
        return ProductVersions.get_versions(channel, product, credentials)[0]

    @staticmethod
    def get_versions(channel, product='Firefox', credentials=None):
        """Get last version for a channel

        Args:
            channel (str): 'nightly', 'aurora', 'beta' or 'release'
            product (Optional[str]): product to use, by default 'Firefox'
            credentials (Optional[dict]): credentials to use with Socorro

        Returns:
            str: the last version corresponding to the channel
        """
        if channel:
            return [p[1] for p in ProductVersions.get_cached_versions(product, credentials)[channel.lower()]]
        else:
            return None

    @staticmethod
    def __get_version(v):
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
                version = ff['version']  # 45.x
                version_n = ProductVersions.__get_version(version)
                # take only the latest versions, e.g. if 45.x and 44.x are "release"
                # then 45.x is only considered
                if number:
                    if number == version_n:
                        if build_type in _data:
                            _data[build_type][1].append((ff['start_date'], version))
                        else:
                            _data[build_type] = (version_n, [(ff['start_date'], version)])
                else:
                    if build_type in _data:
                        t = _data[build_type]
                        if version_n == t[0]:
                            t[1].append((ff['start_date'], version))
                        elif version_n > t[0]:
                            _data[build_type] = (version_n, [(ff['start_date'], version)])
                    else:
                        _data[build_type] = (version_n, [(ff['start_date'], version)])

            for k, v in _data.items():
                versions = v[1]
                if len(versions) > 1:
                    sorted(versions, key=lambda t: utils.get_date_ymd(t[0]))
                data[k] = versions

    @staticmethod
    def get_active(product='Firefox', vnumber=None, is_rapid_beta=False, remove_dates=True, credentials=None):
        """Get the active versions

        Args:
            product (Optional[str]): product to use, by default 'Firefox'
            vnumber (Optional[int]): a version number 45, 46, ...
            is_rapid_beta (Optional[bool]): for version which are rapid beta, by default False
            credentials (Optional[dict]): credentials to use with Socorro

        Returns:
            dict: versions
        """
        versions = {}
        ProductVersions(params={'active': True,
                                'product': product,
                                'is_rapid_beta': is_rapid_beta},
                        credentials=credentials, handler=functools.partial(ProductVersions.default_handler, vnumber), handlerdata=versions).wait()

        if remove_dates:
            _versions = {}
            for k, v in versions.items():
                _versions[k] = list(map(lambda p: p[1], v))
            return _versions

        return versions


class TCBS(Socorro):
    """TCBS: https://crash-stats.mozilla.com/api/#TCBS
    """

    URL = Socorro.API_URL + '/TCBS'

    def __init__(self, params=None, handler=None, handlerdata=None, credentials=None, queries=None):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            credentials (Optional[dict]): credentials to use with Socorro
            queries (Optional[List[Query]]): queries to execute
        """
        if queries:
            super(TCBS, self).__init__(queries, credentials)
        else:
            super(TCBS, self).__init__(Query(TCBS.URL, params, handler, handlerdata), credentials)

    @staticmethod
    def default_handler(json, data):
        """Default handler

        Args:
            json (dict): json
            data (list): list to append the platforms name
        """
        data.append(json)

    @staticmethod
    def get_firefox_topcrashes(version=None, channel=None, days=7, crash_type='all', limit=50, platforms=None, credentials=None):
        """Get top crashes for Firefox

        Args:
            version (Optional[str]): the version
            channel (Optional[str]): 'nightly', 'aurora', 'beta' or 'release'
            days (Optional[int]): the duration
            crash_type (Optional[str]): 'all' (default) or 'browser' or 'content' or 'plugin'
            limit (Optional[int]): the number of crashes to retrieve
            platforms (Optional[str]): 'all' or 'windows' or 'linux' or 'mac os x'
            credentials (Optional[dict]): credentials to use with Socorro

        Returns:
            dict: a json
        """
        if not version:
            version = ProductVersions.get_last_version(channel, credentials)
            if not version:
                return None

        data = []
        TCBS(params={'product': 'Firefox',
                     'version': version,
                     'crash_type': crash_type,
                     'limit': limit,
                     'os': platforms,
                     'duration': days * 24},  # duration is expressed in hours !!
             credentials=credentials, handler=TCBS.default_handler, handlerdata=data).wait()

        return data[0]


class SignatureTrend(Socorro):
    """SignatureTrend: https://crash-stats.mozilla.com/api/#SignatureTrend
    """

    URL = Socorro.API_URL + '/SignatureTrend'

    def __init__(self, params=None, handler=None, handlerdata=None, credentials=None, queries=None):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            credentials (Optional[dict]): credentials to use with Socorro
            queries (Optional[List[Query]]): queries to execute
        """
        if queries:
            super(SignatureTrend, self).__init__(queries, credentials)
        else:
            super(SignatureTrend, self).__init__(Query(SignatureTrend.URL, params, handler, handlerdata), credentials)

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
    def get_trend(signatures, version=None, channel=None, duration=7, end_date='today', product='Firefox', credentials=None):
        """Get signatures trend

        Args:
            version (Optional[str]): the version
            channel (Optional[str]): 'nightly', 'aurora', 'beta' or 'release'
            duration (Optional[int]): the duration
            end_date (Optional[str]): the last date
            product: (Optional[str]): the product, by default 'Firefox'
            credentials (Optional[dict]): credentials to use with Socorro

        Returns:
            dict: the trend for each signature
        """
        if not version:
            version = ProductVersions.get_last_version(channel, credentials)
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
            SignatureTrend(params=__base, credentials=credentials, handler=SignatureTrend.default_handler, handlerdata=_list).wait()
        else:
            queries = []
            for signature in signatures:
                cparams = __base.copy()
                cparams['signature'] = signature
                _list = []
                data[signature] = _list
                queries.append(Query(SignatureTrend.URL, cparams, SignatureTrend.default_handler, _list))
            SignatureTrend(queries=queries, credentials=credentials).wait()

        return data


class ADI(Socorro):
    """ADI: https://crash-stats.mozilla.com/api/#ADI
    """

    URL = Socorro.API_URL + '/ADI'

    def __init__(self, params=None, handler=None, handlerdata=None, credentials=None, queries=None):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            credentials (Optional[dict]): credentials to use with Socorro
            queries (Optional[List[Query]]): queries to execute
        """
        if queries:
            super(ADI, self).__init__(queries, credentials)
        else:
            super(ADI, self).__init__(Query(ADI.URL, params, handler, handlerdata), credentials)

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
    def get(version=None, channel=None, duration=7, end_date='today', product='Firefox', platforms=None, credentials=None):
        """Get ADI

        Args:
            version (Optional[str]): the version
            channel (Optional[str]): 'nightly', 'aurora', 'beta' or 'release'
            duration (Optional[int]): the duration
            end_date (Optional[str]): the last date
            product: (Optional[str]): the product, by default 'Firefox'
            platforms: (Optional[list[str]]): list of platforms
            credentials (Optional[dict]): credentials to use with Socorro

        Returns:
            dict: the trend for each signature
        """
        if not version:
            version = ProductVersions.get_last_version(channel, credentials)
            if not version:
                return None

        data = {}
        start_date = utils.get_date(end_date, duration)
        end_date = utils.get_date(end_date)
        ADI(params={'product': product,
                    'versions': version,
                    'start_date': start_date,
                    'end_date': end_date,
                    'platforms': platforms if platforms else Platforms.get_cached_all(credentials=credentials)},
            handler=ADI.default_handler,
            handlerdata=data,
            credentials=credentials).wait()

        return data


class SignatureURLs(Socorro):
    """SignatureURLs: https://crash-stats.mozilla.com/api/#SignatureURLs
    """

    URL = Socorro.API_URL + '/SignatureURLs'

    def __init__(self, params=None, handler=None, handlerdata=None, credentials=None, queries=None):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            credentials (Optional[dict]): credentials to use with Socorro
            queries (Optional[List[Query]]): queries to execute
        """
        if queries:
            super(SignatureURLs, self).__init__(queries, credentials)
        else:
            super(SignatureURLs, self).__init__(Query(SignatureURLs.URL, params, handler, handlerdata), credentials)

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
    def get_urls(signatures, version=None, channel=None, duration=7, end_date='today', product='Firefox', credentials=None, trunc=True):
        """Get signatures urls

        Args:
            signatures (List[str]): the signatures
            version (Optional[str]): the version
            channel (Optional[str]): 'nightly', 'aurora', 'beta' or 'release'
            duration (Optional[int]): the duration
            end_date (Optional[str]): the last date
            credentials (Optional[dict]): credentials to use with Socorro
            trunc (Optional[bool]): if True, then the url are truncated to their first part (netloc)
                                    e.g. http://foo.com/bar/blah/blah.html will be truncated in foo.com

        Returns:
            dict: the URLs for each signature
        """
        if not version:
            version = ProductVersions.get_last_version(channel, credentials)
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
            SignatureURLs(params=__base, credentials=credentials, handler=handler, handlerdata=_list).wait()
        else:
            queries = []
            for signature in signatures:
                cparams = __base.copy()
                cparams['signature'] = signature
                _list = []
                data[signature] = _list
                queries.append(Query(SignatureURLs.URL, cparams, handler, _list))
            SignatureURLs(queries=queries, credentials=credentials).wait()

        return data


class Bugs(Socorro):
    """Bugs: https://crash-stats.mozilla.com/api/#Bugs
    """

    URL = Socorro.API_URL + '/Bugs'

    def __init__(self, params=None, handler=None, handlerdata=None, credentials=None, queries=None):
        """Constructor

        Args:
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            credentials (Optional[dict]): credentials to use with Socorro
            queries (Optional[List[Query]]): queries to execute
        """
        if queries:
            super(Bugs, self).__init__(queries, credentials)
        else:
            super(Bugs, self).__init__(Query(Bugs.URL, params, handler, handlerdata), credentials)

    @staticmethod
    def default_handler(json, data):
        """Default handler

        Args:
            json (dict): json
            data (set): set to append the bugs id
        """
        if json['total']:
            for hit in json['hits']:
                data.add(hit['id'])

    @staticmethod
    def get_bugs(signatures, credentials=None):
        """Get signatures bugs

        Args:
            signatures (List[str]): the signatures
            credentials (Optional[dict]): credentials to use with Socorro

        Returns:
            dict: the bugs for each signature
        """
        data = {}

        if isinstance(signatures, six.string_types):
            _set = set()
            data[signatures] = _set
            Bugs(params={'signatures': signatures}, credentials=credentials, handler=Bugs.default_handler, handlerdata=_set).wait()
        else:
            queries = []
            for signature in signatures:
                _set = set()
                data[signature] = _set
                queries.append(Query(Bugs.URL, {'signatures': signature}, Bugs.default_handler, _set))
            Bugs(queries=queries, credentials=credentials).wait()

        _data = {}
        for s, b in data.items():
            _data[s] = list(b)

        return _data

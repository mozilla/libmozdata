# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import six
import functools
from datetime import timedelta
from .connection import (Connection, Query)
from . import utils


class Redash(Connection):
    """re:dash connection: https://sql.telemetry.mozilla.org
    """

    RE_DASH_URL = 'https://sql.telemetry.mozilla.org'
    API_URL = RE_DASH_URL + '/api/queries'

    def __init__(self, queries, credentials=None):
        """Constructor

        Args:
            queries (List[Query]): queries to pass to re:dash
            credentials (Optional[dict]): credentials to use with re:dash
        """
        super(Redash, self).__init__(self.RE_DASH_URL, queries=queries, credentials=credentials)

    def get_header(self):
        return {'Authorization': 'Key %s' % self.get_apikey(self.RE_DASH_URL)}

    @staticmethod
    def default_handler(query_id, json, data):
        """Default handler

        Args:
            query_id (str): query id
            json (dict): json
            data (dict): data
        """
        data[query_id] = json

    @staticmethod
    def get(query_ids, credentials=None):
        """Get queries results in json format

        Args:
            query_ids (List[str]): query id
            credentials (Optional[dict]): credentials to use with re:dash

        Returns:
            dict: containing result in json for each query
        """
        data = {}
        if isinstance(query_ids, six.string_types):
            url = Redash.API_URL + '/' + query_ids + '/results.json'
            Redash(Query(url, None, functools.partial(Redash.default_handler, query_ids), data), credentials=credentials).wait()
        else:
            queries = []
            url = Redash.API_URL + '/%s/results.json'
            for query_id in query_ids:
                queries.append(Query(url % query_id, None, functools.partial(Redash.default_handler, query_id), data))
            Redash(queries=queries, credentials=credentials).wait()

        return data

    @staticmethod
    def get_khours(start_date, end_date, channel, versions, product, credentials=None):
        """Get the results for query 346, 387: https://sql.telemetry.mozilla.org/queries/346
                                               https://sql.telemetry.mozilla.org/queries/387
        Args:
            start_date (datetime.datetime): start date
            end_date (datetime.datetime): end date
            channel (str): the channel
            versions (List[str]): the versions
            product (str): the product
            credentials (dict): credentials to use with re:dash

        Returns:
            dict: containing result in json for each query
        """
        qid = '387' if product == 'FennecAndroid' else '346'

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

    @staticmethod
    def get_number_of_crash(start_date, end_date, channel, versions, product, credentials=None):
        """Get the results for query 399, 400: https://sql.telemetry.mozilla.org/queries/399
                                               https://sql.telemetry.mozilla.org/queries/400
        Args:
            start_date (datetime.datetime): start date
            end_date (datetime.datetime): end date
            channel (str): the channel
            versions (List[str]): the versions
            product (str): the product
            credentials (dict): credentials to use with re:dash

        Returns:
            dict: containing result in json for each query
        """
        qid = '400' if product == 'FennecAndroid' else '399'

        crashes = Redash.get(qid, credentials=credentials)
        rows = crashes[qid]['query_result']['data']['rows']
        res = {}
        stats = {'m+c': 0.,
                 'main': 0.,
                 'content': 0.,
                 'plugin': 0.,
                 'all': 0.}

        # init the data
        duration = (end_date - start_date).days
        for i in range(duration + 1):
            res[start_date + timedelta(i)] = stats.copy()

        if channel == 'beta':
            versions = set([v[:-2] for v in versions])
        else:
            versions = set(versions)

        for row in rows:
            if row['channel'] == channel:
                v = row['build_version']
                if v in versions:
                    d = utils.get_date_ymd(row['date'])
                    if d >= start_date and d <= end_date:
                        stats = res[d]
                        stats['m+c'] = row['main'] + row['content']
                        stats['main'] = row['main']
                        stats['content'] = row['content']
                        stats['plugin'] = row['plugin'] + row['gmplugin']
                        stats['all'] = row['total']

        return res

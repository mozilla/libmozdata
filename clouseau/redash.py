# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import six
import functools
from .connection import (Connection, Query)


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

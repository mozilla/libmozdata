# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import six
from .connection import (Connection, Query)
from . import config


class Mercurial(Connection):
    """Mozilla mercurial connection: http://hg.mozilla.org
    """

    HG_URL = config.get('Mercurial', 'URL', 'https://hg.mozilla.org')
    remote = HG_URL == 'https://hg.mozilla.org'

    def __init__(self, queries, channel='nightly', credentials=None):
        """Constructor

        Args:
            queries (List[Query]): queries to pass to mercurial server
            channel (Optional[str]): the channel, by default 'nightly'
            credentials (Optional[dict]): credentials to use with mercurial
        """
        super(Mercurial, self).__init__(self.HG_URL, queries, credentials)
        self.channel = channel

    @staticmethod
    def get_repo(channel):
        """Get the repo name

        Args:
            channel (str): channel version of firefox

        Returns:
            str: the repo name
        """
        if channel == 'nightly':
            return 'mozilla-central'
        else:
            return 'releases/mozilla-' + channel

    @staticmethod
    def get_repo_url(channel):
        """Get the repo url

        Args:
            channel (str): channel version of firefox

        Returns:
            str: the repo url
        """
        if Mercurial.remote:
            return Mercurial.HG_URL + '/' + Mercurial.get_repo(channel)
        else:
            return Mercurial.HG_URL


class Revision(Mercurial):
    """Connection to get a revision
    """

    def __init__(self, channel='nightly', params=None, handler=None, handlerdata=None, credentials=None, queries=None):
        """Constructor

        Args:
            channel (Optional[str]): the channel, by default 'nightly'
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            credentials (Optional[dict]): credentials to use with mercurial
            queries (List[Query]): queries to pass to mercurial server
        """
        if queries:
            super(Revision, self).__init__(queries, credentials)
        else:
            super(Revision, self).__init__(Query(Revision.get_url(channel), params, handler, handlerdata), credentials)

    @staticmethod
    def get_url(channel):
        """Get the api url

        Args:
            channel (str): channel version of firefox

        Returns:
            str: the api url
        """
        return Mercurial.get_repo_url(channel) + '/json-rev'

    @staticmethod
    def default_handler(json, data):
        """Default handler

        Args:
            json (dict): json
            data (dict): dictionary to update with data
        """
        data.update(json)

    @staticmethod
    def get_revision(channel='nightly', node='tip', credentials=None):
        """Get the revision for a node

        Args:
            channel (str): channel version of firefox
            node (Optional[str]): the node, by default 'tip'
            credentials (Optional[dict]): credentials to use with mercurial

        Returns:
            dict: the revision corresponding to the node
        """
        data = {}
        Revision(channel, {'node': node}, Revision.default_handler, data, credentials).wait()
        return data


class FileInfo(Mercurial):
    """Connection to get file info
    """

    def __init__(self, channel='nightly', params=None, handler=None, handlerdata=None, credentials=None, queries=None):
        """Constructor

        Args:
            channel (Optional[str]): the channel, by default 'nightly'
            params (Optional[dict]): the params for the query
            handler (Optional[function]): handler to use with the result of the query
            handlerdata (Optional): data used in second argument of the handler
            credentials (Optional[dict]): credentials to use with mercurial
            queries (List[Query]): queries to pass to mercurial server
        """
        if queries:
            super(FileInfo, self).__init__(queries, credentials)
        else:
            super(FileInfo, self).__init__(Query(FileInfo.get_url(channel), params, handler, handlerdata), credentials)

    @staticmethod
    def get_url(channel):
        """Get the api url

        Args:
            channel (str): channel version of firefox

        Returns:
            str: the api url
        """
        return Mercurial.get_repo_url(channel) + '/json-filelog'

    @staticmethod
    def default_handler(json, data):
        """Default handler

        Args:
            json (dict): json
            data (dict): dictionary to update with data
        """
        data.update(json)

    @staticmethod
    def get(paths, channel='nightly', node='tip', credentials=None):
        """Get the file info for several paths

        Args:
            paths (List[str]): the paths
            channel (str): channel version of firefox
            node (Optional[str]): the node, by default 'tip'
            credentials (Optional[dict]): credentials to use with mercurial

        Returns:
            dict: the files info
        """
        data = {}

        __base = {'node': node,
                  'file': None}

        if isinstance(paths, six.string_types):
            __base['file'] = paths
            _dict = {}
            data[paths] = _dict
            FileInfo(channel=channel, params=__base, handler=FileInfo.default_handler, handlerdata=_dict, credentials=credentials).wait()
        else:
            url = FileInfo.get_url(channel)
            queries = []
            for path in paths:
                cparams = __base.copy()
                cparams['file'] = path
                _dict = {}
                data[path] = _dict
                queries.append(Query(url, cparams, FileInfo.default_handler, _dict))
            FileInfo(queries=queries, credentials=credentials).wait()

        return data

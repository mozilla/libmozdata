import os
from .connection import Connection


class CrashInfo(Connection):

    # TODO: count is probably erroneous since there is a range by default in supersearch...
    CRASH_STATS_URL = 'https://crash-stats.mozilla.com'
    SUPERSEARCH_URL = CRASH_STATS_URL + '/api/SuperSearch'

    def __init__(self, paths, credentials=None):
        super(CrashInfo, self).__init__(self.CRASH_STATS_URL, credentials=credentials)
        self.info = {}
        self.paths = [paths] if type(paths) == str else paths
        for path in self.paths:
            self.info[path] = {'crashes': -1}

        self.__get_info()

    def get(self):
        self.wait()
        return self.info

    def __get_apikey(self):
        return self.get_apikey(self.CRASH_STATS_URL)

    def __info_cb(self, path):
        def cb(sess, res):
            self.info[path]['crashes'] = res.json()['total']

        return cb

    def __get_info(self):
        header = {'Auth-Token': self.__get_apikey()}
        for path in self.paths:
            self.results.append(self.session.get(self.SUPERSEARCH_URL,
                                                 params={'product': 'Firefox',
                                                         'topmost_filenames': '~' + path,
                                                         '_results_number': 0,
                                                         '_facets': 'product',
                                                         '_facets_size': 1},
                                                 headers=header,
                                                 timeout=self.TIMEOUT,
                                                 background_callback=self.__info_cb(path)))

# ci = CrashInfo('netwerk/protocol/http/nsHttpConnectionMgr.cpp')

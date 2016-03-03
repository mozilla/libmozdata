import os
import multiprocessing
from requests.adapters import HTTPAdapter
from requests_futures.sessions import FuturesSession
from pprint import pprint

class CrashInfo(object):

    # TODO: count is probably erroneous since there is a range by default in supersearch...
    CRASH_STATS_URL = 'https://crash-stats.mozilla.com'
    SUPERSEARCH_URL = CRASH_STATS_URL + '/api/SuperSearch'
    TIMEOUT = 5
    MAX_RETRIES = 5
    MAX_WORKERS = multiprocessing.cpu_count()

    def __init__(self, paths, credentials = None):
        self.results = [ ]
        self.credentials = credentials
        self.info = { }
        self.paths = [paths] if type(paths) == str else paths 
        for path in self.paths:
            self.info[path] = { 'crashes': -1 }
                                
        self.session = FuturesSession(max_workers = self.MAX_WORKERS)
        self.session.mount(self.CRASH_STATS_URL, HTTPAdapter(max_retries = self.MAX_RETRIES))
        self.__get_info()

    def get(self):
        for r in self.results:
            r.result()
        return self.info

    def __get_apikey(self):
        if self.credentials:
            return self.credentials['tokens'][self.CRASH_STATS_URL]
        else:
            return ''
    
    def __info_cb(self, path):
        def cb(sess, res):
            self.info[path]['crashes'] = res.json()['total']

        return cb

    def __get_info(self):
        header = { 'Auth-Token': self.__get_apikey() }
        for path in self.paths:
            filename = os.path.basename(path)
            self.results.append(self.session.get(self.SUPERSEARCH_URL,
                                                 params = { 'product': 'Firefox',
                                                            'topmost_filenames': filename, 
                                                            '_results_number': 0,
                                                            '_facets': 'product',
                                                            '_facets_size': 1 },
                                                 headers = header,
                                                 timeout = self.TIMEOUT,
                                                 background_callback = self.__info_cb(path)))

#ci = CrashInfo('netwerk/protocol/http/nsHttpConnectionMgr.cpp')

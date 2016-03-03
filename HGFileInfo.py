from requests.adapters import HTTPAdapter
from requests_futures.sessions import FuturesSession
from pprint import pprint
import re
from datetime import datetime

class HGFileInfo(object):

    HG_URL = 'http://pandaroux:8000'
    #HG_URL = 'http://hg.mozilla.org/mozilla-central'
    FILELOG_URL = HG_URL + '/json-filelog'
    REV_URL = HG_URL + '/json-rev'
    TIMEOUT = 5
    MAX_RETRIES = 5
    
    def __init__(self, paths, repo = 'mozilla-central', rev = 'tip', utc_ts = None, credentials = None):
        self.rev = rev
        self.utc_ts = utc_ts
        self.results = [ ]
        self.info = { }
        self.paths = [paths] if isinstance(paths, basestring) else paths
        for path in self.paths:
            self.info[path] = { 'authors': { },
                                'bugs': set(),
                                'last': None }
                                
        self.session = FuturesSession()
        self.session.mount(self.HG_URL, HTTPAdapter(max_retries = self.MAX_RETRIES))
        self.bug_pattern = re.compile('[Bb][Uu][Gg][\t ]*([0-9]+)')
        self.rev_pattern = re.compile('r=([a-zA-Z0-9]+)')
        self.__get_info()

    def get(self):
        for r in self.results:
            r.result()
        return self.info

    def __utc_ts_cb(self, sess, res):
        pushdate = res.json()['pushdate']
        if pushdate:
            self.utc_ts = pushdate[0]

    def get_utc_ts(self):
        if not self.utc_ts:
            self.utc_ts_res.result()

        return self.utc_ts
    
    def __get_info_from_desc(self, desc):
        desc = desc.strip()
        info = { 'starter': '',
                 'refs': set(),
                 'reviewers': set() }
        s = info['refs']
        for m in self.bug_pattern.finditer(desc):
            if m.start(0) == 0:
                # the description begins with Bug 1234....
                info['starter'] = m.group(1)
            s.add(m.group(1))

        for m in self.rev_pattern.finditer(desc):
            info['reviewers'].add(m.group(1))
               
        return info

    def __info_cb(self, sess, res):
        if res.status_code == 200:
            json = res.json()
            path = json['file']
            entries = json['entries']
            info = self.info[path]
            authors = info['authors']
            patchs_found = False
            patchs = None
            for entry in entries:
                utc_ts = self.get_utc_ts()
                if utc_ts and not patchs_found:
                    # we get the last patches which have been pushed the same day
                    utc_pushdate = entry['pushdate']
                    if utc_pushdate:
                        utc_pushdate = utc_pushdate[0]
                        if utc_pushdate <= utc_ts:
                            if patchs:
                                last_date = patchs[-1]['pushdate'][0]
                                last_date = datetime.utcfromtimestamp(last_date)
                                push_date = datetime.utcfromtimestamp(utc_pushdate)
                                if last_date.year == push_date.year and last_date.month == push_date.month and last_date.day == push_date.day:
                                    patchs.append(entry)
                                else:
                                    patchs_found = True    
                            else:
                                patchs = [entry]
                author = entry['author']
                if author not in authors:
                    authors[author] = { 'count': 1, 'reviewers': { } }
                else:
                    authors[author]['count'] += 1

                info_desc = self.__get_info_from_desc(entry['desc'])
                starter = info_desc['starter']
                if starter:
                     info['bugs'].add(info_desc['starter'])
                reviewers = info_desc['reviewers']
                if reviewers:
                     _reviewers = authors[author]['reviewers']
                     for reviewer in reviewers:
                         if reviewer not in _reviewers:
                             _reviewers[reviewer] = 1
                         else:
                             _reviewers[reviewer] += 1

            if patchs:
                info['last'] = patchs
            

    def __get_info(self):
        if not self.utc_ts:
            self.utc_ts_res = self.session.get(self.REV_URL,
                                                   params = { 'node': self.rev},
                                                   timeout = self.TIMEOUT,
                                                   background_callback = self.__utc_ts_cb)
        
        for path in self.paths:
            self.results.append(self.session.get(self.FILELOG_URL,
                                                 params = { 'node': 'tip',
                                                            'file': path },
                                                 timeout = self.TIMEOUT,
                                                 background_callback = self.__info_cb))

#fi = HGFileInfo('netwerk/protocol/http/nsHttpConnectionMgr.cpp', 1455339746)
#pprint(fi.get()['netwerk/protocol/http/nsHttpConnectionMgr.cpp']['last'])

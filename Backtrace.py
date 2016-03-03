import multiprocessing
from requests.adapters import HTTPAdapter
from requests_futures.sessions import FuturesSession
from pprint import pprint
from datetime import timedelta
import utils
import re
from FileStats import FileStats
from random import randint

class Backtrace(object):

    CRASH_STATS_URL = 'https://crash-stats.mozilla.com'
    PROCESSED_URL = CRASH_STATS_URL + '/api/ProcessedCrash/'
    TIMEOUT = 5
    MAX_RETRIES = 5
    MAX_WORKERS = multiprocessing.cpu_count()
    
    def __init__(self, uuids, fraction = 0.2, just_hg = False, credentials = None):
        self.just_hg = just_hg
        self.results = [ ]
        self.credentials = credentials
        self.uuids = uuids
        self.fraction = max(0., min(fraction, 1.))
        self.info = { }
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
    
    @staticmethod
    def __cycles_detection(funs):
        # TODO: improve this algorithm (not sure that's a good one)
        positions = { }
        # we get the function positions in the trace
        for i in range(len(funs)):
            fun = funs[i]
            if fun in positions:
                positions[fun].append(i)
            else:
                positions[fun] = [ i ]

        lengths = { }
        for k, v in positions.iteritems():
            if len(v) >= 2:
                l = v[1] - v[0]
                good = True
                for i in range(2, len(v)):
                    if v[i] - v[i - 1] != l:
                        good = False
                        break
                if good:
                    if l in lengths:
                        lengths[l].append((k, v))
                    else:
                        lengths[l] = [ (k, v) ]

        cycles = [ ]
        for k, v in lengths.iteritems():
            l = sorted(v, cmp = lambda x, y: cmp(x[1][0], y[1][0]))
            pat = [ ]
            container = [ l[0][0] ]
            pos = l[0][1][0]
            for i in range(1, len(l)):
                _pos = l[i][1][0]
                if _pos == pos + 1:
                    container.append(l[i][0])
                    pos = _pos
                else:
                    pat.append(tuple(container))
                    container = [ l[i][0] ]
                    pos = _pos

            pat.append(tuple(container))
            cycles += pat

        cycles = tuple(cycles)
        
        return cycles
    
    def __info_cb(self, sess, res):
        json = res.json()
        if 'json_dump' in json:
            uuid = json['uuid']
            jd = json['json_dump']
            if 'crashedThread' in json and 'threads' in jd:
                ct = json['crashedThread']
                ct = jd['threads'][ct]
                self.info[uuid] = { 'cycles': [ ],
                                        'address': '',
                                        'cpu_name': json['cpu_name'],
                                        'cpu_info': json['cpu_info'],
                                        'reason': json['reason'],
                                        'os': json['os_pretty_version'] }
                if 'frames' in ct:
                    frames = ct['frames']
                    functions = [ ]
                    # we get the functions in the backtrace (to check if there is a recursion)
                    for frame in frames:
                        if 'function' in frame:
                            functions.append(frame['function'])
                    # check for duplicated entries in function
                    self.info[uuid]['cycles'] = Backtrace.__cycles_detection(functions)
                if 'crash_info' in jd:
                    addr = jd['crash_info']['address']
                    self.info[uuid]['address'] = addr


    def __hginfo_cb(self, sess, res):
        json = res.json()
        if 'json_dump' in json:
            uuid = json['uuid']
            jd = json['json_dump']
            if 'crashedThread' in json and 'threads' in jd:
                ct = json['crashedThread']
                ct = jd['threads'][ct]
                
                self.info[uuid] = { 'hgfiles': [ ] }
                if 'frames' in ct:
                    frames = ct['frames']
                    files = [ ]
                    # _files is just used to avoid duplicated in files
                    _files = set()
                    for frame in frames:
                        if 'file' in frame:
                            f = frame['file']
                            if f not in _files:
                                files.append(f)
                                _files.add(f)
                                
                    self.info[uuid] = files
        
    def __get_info(self):
        header = { 'Auth-Token': self.__get_apikey() }
        if self.just_hg:
            self.results.append(self.session.get(self.PROCESSED_URL,
                                                 params = { 'crash_id': self.uuids[0] },
                                                 headers = header,
                                                 timeout = self.TIMEOUT,
                                                 background_callback = self.__hginfo_cb))
            return
        
        if self.fraction != 1:
            L = len(self.uuids)
            indices = set()
            ratio = self.fraction if self.fraction <= 0.5 else 1 - self.fraction 
            N = int(float(L) * ratio)
            # we analyze only a fraction of all the uuids
            while len(indices) != N:
                indices.add(randint(0, L - 1))
            if self.fraction <= 0.5:
                uuids = [self.uuids[i] for i in indices]
            else:
                uuids = [ ]
                for i in range(L):
                    if i not in indices:
                        uuids.append(self.uuids[i])
        else:
            uuids = self.uuids
            
        for uuid in uuids:
            self.results.append(self.session.get(self.PROCESSED_URL,
                                                 params = { 'crash_id': uuid },
                                                 headers = header,
                                                 timeout = self.TIMEOUT,
                                                 background_callback = self.__info_cb))


#t = Track('msvcr120.dll@0xf608 | nsZipItemPtr<T>::Forget', '2016-02-25')
#t = Track('mozilla::gfx::DrawTargetCairo::FillGlyphs', '2016-02-29')
#t = Track('nss3.dll@0x1eab60 | GetFileInfo', '2016-02-28')
#t = Track('PR_DestroyThreadPrivate | PR_CleanupThread | PR_NativeRunThread | pr_root', '2016-02-26')
#t = Track('mp4parse_new', '2016-02-28')
#t = Track('mozilla::ipc::MessageListener::IntentionalCrash', '2016-01-30')

#pprint(t.get())

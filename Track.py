import multiprocessing
from requests.adapters import HTTPAdapter
from requests_futures.sessions import FuturesSession
from pprint import pprint
from datetime import timedelta
import utils
import math
import re
from FileStats import FileStats
from Backtrace import Backtrace

class Track(object):

    CRASH_STATS_URL = 'https://crash-stats.mozilla.com'
    SUPERSEARCH_URL = CRASH_STATS_URL + '/api/SuperSearch'
    TIMEOUT = 5
    MAX_RETRIES = 5
    MAX_WORKERS = multiprocessing.cpu_count()
    HG_PATTERN = re.compile('hg:hg.mozilla.org/mozilla-central:([^:]*):([a-z0-9]+)')
    
    def __init__(self, signature, day, day_delta = 1, credentials = None):
        self.results = [ ]
        self.credentials = credentials
        self.has_results = False
        self.day_delta = day_delta
        self.signature = signature
        self.info = { }
        self.date = utils.get_date_ymd(day)
        self.session = FuturesSession(max_workers = self.MAX_WORKERS)
        self.session.mount(self.CRASH_STATS_URL, HTTPAdapter(max_retries = self.MAX_RETRIES))
        self.__get_info()

    def get(self):
        if not self.has_results:
            for r in self.results:
                r.result()
            self.has_results = True
        return self.info

    def has_addons(self):
        return len(self.get()['addons']) != 0

    def __get_apikey(self):
        if self.credentials:
            pprint(self.credentials)
            return self.credentials['tokens'][self.CRASH_STATS_URL]
        else:
            return ''

    @staticmethod
    def __get_stats(info, field):
        l = info[field]
        total = float(info['total'])
        stats = { }
        for e in l:
            stats[e['term']] = utils.percent(float(e['count']) / total)
        return stats
    
    @staticmethod
    def __get_system_memory_use_mean(info):
        l = info['system_memory_use_percentage']
        total = float(info['total'])
        l = [(float(e['count']) / total, float(e['term'])) for e in l]  
        m = 0.
        for e in l:
            m += e[0] * e[1]

        v = 0.
        for e in l:
            v += e[0] * (m - e[1]) ** 2

        return {'mean': utils.simple_percent(round(m, 0)), 'stddev': utils.simple_percent(round(math.sqrt(v), 0))}

    @staticmethod
    def __is_weird_address(addr, cpu_name):
        if addr == '0x0':
            return True
        if utils.is64(cpu_name):
            if len(addr) <= 10:
                val = long(addr, 16)
                if val <= 1L << 16: # val <= 0xffff (ie: first 64k)
                    return True
            elif addr.startswith('0xffffffff'):
                addr = addr[10:] # 10 == len('0xffffffff')
                val = long(addr, 16)
                if val >= ((1L << 32) - (1L << 16)): # val >= 0xfffffffffff0000 (ie: last 64k)
                    return True
        else:
            val = long(addr, 16)
            if val <= 1L << 16: # val <= 0xffff (ie: first 64k)
                return True
            if val >= ((1L << 32) - (1L << 16)): # val >= 0xffff0000 (ie: last 64k)
                return True

        return False
    
    @staticmethod
    def __get_bt_stats(info, credentials):
        hits = info['hits']
        uuids = [ hit['uuid'] for hit in hits ]
        bt = Backtrace(uuids, fraction = 1, credentials = credentials)#0.5)
        bt_info = bt.get()
        total = 0
        rec = 0.
        weird_address = { }
        os_cpu = { }
        cpu_info = { }
        reason = { }
        cycles = { }
        if bt_info:
            recursive_bt = 0
            addrs = { }
                        
            total = float(len(bt_info))
            for v in bt_info.itervalues():
                _cycles = v['cycles']
                if _cycles:
                    recursive_bt += 1
                    cycles[_cycles] = cycles[_cycles] + 1 if _cycles in cycles else 1
                        
                addr = v['address']
                t = (addr, v['cpu_name'])
                addrs[t] = addrs[t] + 1 if t in addrs else 1
                t = (v['os'], v['cpu_name'])
                os_cpu[t] = os_cpu[t] + 1 if t in os_cpu else 1
                ci = v['cpu_info']
                cpu_info[ci] = cpu_info[ci] + 1 if ci in cpu_info else 1
                r = v['reason']
                reason[r] = reason[r] + 1 if r in reason else 1
                
            rec = utils.percent(float(recursive_bt) / total)

            for k, v in os_cpu.iteritems():
                os_cpu[k] = utils.percent(float(v) / total)

            for k, v in cpu_info.iteritems():
                cpu_info[k] = utils.percent(float(v) / total)

            for k, v in reason.iteritems():
                reason[k] = utils.percent(float(v) / total)

            for k, v in addrs.iteritems():
                percent = float(v) / total
                if Track.__is_weird_address(*k):
                    weird_address[k] = utils.percent(percent)
                elif percent >= 0.25:
                    weird_address[k] = utils.percent(percent)

            total = int(total)

        return { 'sample_size': total, 'bt_has_rec': rec, 'weird_address': weird_address, 'cycles': cycles, 'os_cpu': os_cpu, 'cpu_info': cpu_info }

    @staticmethod
    def __get_filename_rev(path):
        m = Track.HG_PATTERN.search(path)
        filename = m.group(1)
        rev = m.group(2)
        return (filename, rev)
    
    @staticmethod
    def __get_topmost_filename(info):
        path = info['hits'][0]['topmost_filenames']
        return Track.__get_filename_rev(path)

    @staticmethod
    def __walk_on_the_backtrace(info):
        uuid = info['hits'][0]['uuid']
        fileinfo = None
        bt = Backtrace([uuid], just_hg = True, credentials = self.credentials).get()[uuid]
        if len(bt) >= 2:
            # remove the first (already done)
            for i in range(1, len(bt)):
                m = Track.HG_PATTERN.match(bt[i])
                if m:
                    filename = m.group(1)
                    rev = m.group(2)
                    fs = FileStats(path = filename, rev = rev, credentials = self.credentials)
                    fileinfo = fs.get_info(dig_when_non_pertinent = False)
                    if fileinfo:
                        # hurrah \o/ we found a pertinent file !
                        break
        return fileinfo
        
    def __info_cb(self, sess, res):
        json = res.json()
        #pprint(json)
        total = json['total']
        info = { 'total': total, 'hits': json['hits'] }
        info.update(json['facets'])
        
        self.info['total'] = total
        self.info['platforms'] = Track.__get_stats(info, 'platform_pretty_version')
        self.info['buildids'] = Track.__get_stats(info, 'build_id')
        self.info['versions'] = Track.__get_stats(info, 'version')
        self.info['channels'] = Track.__get_stats(info, 'release_channel')
        self.info['system_memory_use'] = Track.__get_system_memory_use_mean(info)
        filename, rev = Track.__get_topmost_filename(info)
        self.info['filename'] = filename
        self.info['revision'] = rev
        fs = FileStats(path = filename, rev = rev, credentials = self.credentials)
        # don't dig: if non-pertinent we'll try in the next function in the backtrace
        #fileinfo = fs.get_info(dig_when_non_pertinent = False)
        fileinfo = fs.get_info(dig_when_non_pertinent = True)
        if fileinfo:
            self.info['fileinfo'] = fileinfo
        else:
            self.info['fileinfo'] = Track.__walk_on_the_backtrace(info)
        self.info['btinfo'] = Track.__get_bt_stats(info, self.credentials)
        
    def __get_info(self):
        header = { 'Auth-Token': self.__get_apikey() }
        self.results.append(self.session.get(self.SUPERSEARCH_URL,
                                                 params = { 'product': 'Firefox',
                                                            'signature': '=' + self.signature,
                                                            'date': ['>=' + utils.get_date_str(self.date),
                                                                     '<' + utils.get_date_str(self.date + timedelta(self.day_delta))],
                                                            'release_channel': 'nightly',
                                                            '_sort': 'build_id',
                                                            '_columns': ['uuid', 'topmost_filenames'],
                                                            '_facets': ['platform_pretty_version', 'build_id', 'version', 'release_channel', 'system_memory_use_percentage', 'addons'],
                                                            '_results_number': 100,
                                                                },
                                                 headers = header,
                                                 timeout = self.TIMEOUT,
                                                 background_callback = self.__info_cb))


#t = Track('msvcr120.dll@0xf608 | nsZipItemPtr<T>::Forget', '2016-02-25')
#t = Track('mozilla::gfx::DrawTargetCairo::FillGlyphs', '2016-02-27', day_delta = 3)
#t = Track('nss3.dll@0x1eab60 | GetFileInfo', '2016-02-28', day_delta = 2)
#t = Track('PR_DestroyThreadPrivate | PR_CleanupThread | PR_NativeRunThread | pr_root', '2016-02-26')
t = Track('mp4parse_new', '2016-02-28', credentials = utils.get_credentials('/home/calixte/credentials.json'))
#t = Track('mozilla::ipc::MessageListener::IntentionalCrash', '2016-02-27', day_delta = 3)
#t = Track('js::gc::GCRuntime::sweepBackgroundThings', '2015-12-22', day_delta = 3)
#t = Track('nsCOMPtr_base::assign_from_qi | nsCOMPtr<T>::nsCOMPtr<T> | nsDocShell::EnsureFind', '2016-02-29', day_delta = 2)
#t = Track('mozilla::layers::TextureWrapperImage::GetAsSourceSurface', '2015-12-12', day_delta = 2)
#t = Track('PLDHashTable::Remove', '2015-12-29', day_delta = 10)
#t = Track('mozilla::net::nsHttpTransaction::WriteSegments(mozilla::net::nsAHttpSegmentWriter*, unsigned int, unsigned int*)', '2015-04-13', day_delta = 1) 
#t = Track('mozilla::ipc::MessageChannel::ShouldDeferMessage', '2016-03-01', day_delta = 2)
#t = Track('mozalloc_abort | NS_DebugBreak | nsDebugImpl::Abort | XPTC__InvokebyIndex', '2016-03-01', day_delta = 2) 

pprint(t.get())

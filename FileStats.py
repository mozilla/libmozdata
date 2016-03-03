from pprint import pprint
from datetime import datetime
import time
import re
import numbers

from HGFileInfo import HGFileInfo
from HGFiles import HGFiles
from BZInfo import BZInfo
from CrashInfo import CrashInfo
import utils

class FileStats(object):

    MAX_DAYS = 3
    
    def __init__(self, path, rev = 'tip', utc_ts = None, credentials = None):
        self.utc_ts = utc_ts if isinstance(utc_ts, numbers.Number) and utc_ts > 0 else None
        self.path = path
        self.rev = rev
        self.credentials = credentials
        #ci = CrashInfo(path)
        self.hi = HGFileInfo(path, rev = self.rev, utc_ts = self.utc_ts, credentials = self.credentials)
        self.info = self.hi.get()[path]
        #self.ci = ci.get()

    def get_info(self, dig_when_non_pertinent = True):
        info = { 'path': self.path,
                 'guilty': None,
                 'needinfo': None }
                        
        c = self.__check_dates()
        if not c and not dig_when_non_pertinent:
                return None

        if isinstance(c, bool):
            bugs = self.info['bugs']
            bi = BZInfo(bugs, credentials = self.credentials) if bugs else None
            #pprint(bi.get())
            if c: # we have a 'guilty' set of patches
                author_pattern = re.compile('<([^>]+>)')
                stats = { }
                last = self.info['last']
                last_author = None
                for patch in last:                        
                    m = author_pattern.search(patch['author'])
                    if m:
                        author = m.group(1)
                    else:
                        author = patch['author']
                    if not last_author:
                        last_author = author
                    stats[author] = stats[author] + 1 if author in stats else 1
                info['guilty'] = { 'main_author': utils.get_best(stats) if stats else None,
                                   'last_author': last_author,
                                   'patches' : last }
            else:
                # find out the good person to query for a needinfo
                info['needinfo'] = bi.get_best_collaborator() if bi else None

            comp_prod = bi.get_best_component_product() if bi else None
            if comp_prod:
                info['component'] = comp_prod[0]
                info['product'] = comp_prod[1] 

        return info
                    
    def __check_dates(self):
        if self.hi.get_utc_ts():
            last = self.info['last']
            if last:
                date = datetime.utcfromtimestamp(self.hi.get_utc_ts())
                pushdate = datetime.utcfromtimestamp(last[0]['pushdate'][0])
                td = date - pushdate
                return td.days <= self.MAX_DAYS
        return None

#'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
#fs = FileStats('gfx/layers/TextureWrapperImage.cpp', rev = '143ea6152229', utc_ts = utils.get_now_timestamp())
#pprint(fs.get_info())

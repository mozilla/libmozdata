# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
from datetime import datetime
import numbers
from pprint import pprint
import re

from .HGFileInfo import HGFileInfo
from .BZInfo import BZInfo
from .modules import MozillaModules
from . import utils
from . import config


class FileStats(object):
    """Stats about a file in the repo.
    """

    def __init__(self, path, channel='nightly', node='tip', utc_ts=None, credentials=None):
        """Constructor

        Args:
            path (str): file path
            channel (str): channel version of firefox
            node (Optional[str]): the node, by default 'tip'
            utc_ts (Optional[int]): UTC timestamp, file pushdate <= utc_ts
            credentials (Optional[dict]): credentials to use
        """
        self.utc_ts = utc_ts if isinstance(utc_ts, numbers.Number) and utc_ts > 0 else None
        self.path = path
        self.max_days = int(config.get('FileStats', 'MaxDays', 3))
        self.credentials = credentials
        self.hi = HGFileInfo(path, channel=channel, node=node, utc_ts=self.utc_ts, credentials=self.credentials)
        self.info = self.hi.get()
        self.module = MozillaModules().module_from_path(path)

    def get_info(self, dig_when_non_pertinent=True):
        """Get info

        Args:
            dig_when_non_pertinent (Optional[bool]): when True, even if the last patch is non-pertinent
            (i.e. its push date isn't around utc_ts modulo max_days), the info about it are collected.

        Returns:
            dict: info
        """
        info = {
            'path': self.path,
            'guilty': None,
            'needinfo': None,
            'module': self.module['name'],
            'components': set(self.module['bugzillaComponents']),
            'owners': self.module['owners'],
            'peers': self.module['peers'],
        }

        c = self.__check_dates()
        if not c and not dig_when_non_pertinent:
            return None

        if isinstance(c, bool):
            bugs = self.info['bugs']
            bi = BZInfo(bugs, credentials=self.credentials) if bugs else None
            if c:  # we have a 'guilty' set of patches
                author_pattern = re.compile('<([^>]+>)')
                stats = {}
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

                info['guilty'] = {'main_author': utils.get_best(stats) if stats else None,
                                  'last_author': last_author,
                                  'patches': last}

            if bi:
                # find out the good person to query for a needinfo
                info['needinfo'] = bi.get_best_collaborator()
                comp_prod = bi.get_best_component_product()
                info['components'].add(comp_prod[1] + '::' + comp_prod[0])
                info['bugs'] = len(bugs)

        return info

    def __check_dates(self):
        """Check if the last patch has been pushed (cf pushdate) max_days before the utc_ts

        Returns:
            bool: a boolean
        """
        if self.hi.get_utc_ts():
            # we get the last patch (according to utc_ts)
            last = self.info['last']
            if last:
                date = datetime.utcfromtimestamp(self.hi.get_utc_ts())
                pushdate = datetime.utcfromtimestamp(last[0]['pushdate'][0])
                td = date - pushdate
                return td.days <= self.max_days
        return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='File Stats')
    parser.add_argument('-p', '--path', action='store', help='file path')
    parser.add_argument('-n', '--node', action='store', default='tip', help='Mercurial node, by default \'tip\'')
    parser.add_argument('-c', '--channel', action='store', default='nightly', help='release channel')
    parser.add_argument('-d', '--date', action='store', default='today', help='max date for pushdate, format YYYY-mm-dd')
    parser.add_argument('-C', '--credentials', action='store', default='', help='credentials file to use')

    args = parser.parse_args()

    if args.path:
        credentials = utils.get_credentials(args.credentials) if args.credentials else None
        fs = FileStats(args.path, args.channel, args.node, utils.get_timestamp(args.date), credentials)
        pprint(fs.get_info())

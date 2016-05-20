# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
from datetime import (datetime, timedelta)
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
        self.max_days = int(config.get('FileStats', 'MaxDays', 3))
        utc_ts_from = utils.get_timestamp(datetime.utcfromtimestamp(utc_ts) + timedelta(-self.max_days)) if isinstance(utc_ts, numbers.Number) and utc_ts > 0 else None
        self.path = path
        self.credentials = credentials
        self.hi = HGFileInfo(path, channel=channel, node=node)
        self.info = self.hi.get(path, utc_ts_from, utc_ts)
        self.module = MozillaModules().module_from_path(path)

    def get_info(self):
        """Get info

        Returns:
            dict: info
        """
        info = {
            'path': self.path,
            'guilty': None,
            'needinfo': None,
            'components': set(),
        }

        if self.module is not None:
            info['module'] = self.module['name']
            info['components'].update(self.module['bugzillaComponents'])
            info['owners'] = self.module['owners']
            info['peers'] = self.module['peers']

        bugs = self.info['bugs']
        bi = BZInfo(bugs, credentials=self.credentials) if bugs else None
        last = self.info['patches']
        if len(last) > 0:  # we have a 'guilty' set of patches
            author_pattern = re.compile('<([^>]+)>')
            stats = {}
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

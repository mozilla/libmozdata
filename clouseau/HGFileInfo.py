# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import six
from datetime import datetime
from .connection import Query
from . import hgmozilla


class HGFileInfo(object):
    """File info from Mercurial

       We collect the different authors, reviewers and related bugs from the patches which touched to the file.
       The patches can be filtered according to pushdate.
    """

    def __init__(self, paths, channel='nightly', node='tip', utc_ts=None, credentials=None):
        """Constructor

        Args:
            paths (List[str]): the paths
            channel (str): channel version of firefox
            node (Optional[str]): the node, by default 'tip'
            utc_ts (Optional[int]): UTC timestamp, file pushdate <= utc_ts
            credentials (Optional[dict]): credentials to use
        """
        self.channel = channel
        self.node = node
        self.utc_ts = utc_ts
        self.data = {}
        self.paths = [paths] if isinstance(paths, six.string_types) else paths
        self.bug_pattern = re.compile('[\t ]*[Bb][Uu][Gg][\t ]*([0-9]+)')
        self.rev_pattern = re.compile('r=([a-zA-Z0-9]+)')
        self.__get_info()

    def get(self):
        self.conn.wait()

        info = {}

        for path in self.paths:
            info[path] = {
                'authors': {},
                'bugs': set(),
                'last': None
            }

            entries = self.data[path]

            authors = info[path]['authors']
            patches_found = False
            patches = None
            for entry in entries:
                if self.utc_ts and not patches_found:
                    # we get the last patches which have been pushed the same day
                    utc_pushdate = entry['pushdate']
                    if utc_pushdate:
                        utc_pushdate = utc_pushdate[0]
                        if utc_pushdate <= self.utc_ts:
                            if patches:
                                last_date = patches[-1]['pushdate'][0]
                                last_date = datetime.utcfromtimestamp(last_date)
                                push_date = datetime.utcfromtimestamp(utc_pushdate)
                                if last_date.year == push_date.year and last_date.month == push_date.month and last_date.day == push_date.day:
                                    patches.append(entry)
                                else:
                                    patches_found = True
                            else:
                                patches = [entry]
                author = entry['author']
                if author not in authors:
                    authors[author] = {'count': 1, 'reviewers': {}}
                else:
                    authors[author]['count'] += 1

                info_desc = self.__get_info_from_desc(entry['desc'])
                starter = info_desc['starter']
                if starter:
                    info[path]['bugs'].add(info_desc['starter'])
                reviewers = info_desc['reviewers']
                if reviewers:
                    _reviewers = authors[author]['reviewers']
                    for reviewer in reviewers:
                        if reviewer not in _reviewers:
                            _reviewers[reviewer] = 1
                        else:
                            _reviewers[reviewer] += 1

            if patches:
                info[path]['last'] = patches

        return info

    def get_utc_ts(self):
        """Get the utc timestamp

        Returns:
            int: the utc timestamp
        """
        return self.utc_ts

    def __get_info_from_desc(self, desc):
        """Get some information from the patch description

        Args:
            desc (str): the description

        Returns:
            dict: some information
        """
        desc = desc.strip()
        info = {'starter': '',
                'refs': set(),
                'reviewers': set()}
        s = info['refs']
        for m in self.bug_pattern.finditer(desc):
            if m.start(0) == 0:
                # the description begins with Bug 1234....
                info['starter'] = m.group(1)
            s.add(m.group(1))

        for m in self.rev_pattern.finditer(desc):
            info['reviewers'].add(m.group(1))

        return info

    def __handler(self, json, path):
        """Handler

        Args:
            json (dict): json
            info (dict): info
        """
        self.data[path] = json['entries']

    def __get_info(self):
        """Get info
        """
        if not self.utc_ts:
            revision = hgmozilla.Revision.get_revision(self.channel, self.node)
            pushdate = revision.get('pushdate', None)
            if pushdate:
                self.utc_ts = pushdate[0]

        __base = {'node': self.node,
                  'file': None}
        queries = []
        url = hgmozilla.FileInfo.get_url(self.channel)
        for path in self.paths:
            cparams = __base.copy()
            cparams['file'] = path
            queries.append(Query(url, cparams, handler=self.__handler, handlerdata=path))

        self.conn = hgmozilla.FileInfo(queries=queries)

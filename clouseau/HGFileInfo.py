# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import six
from .connection import Query
from . import hgmozilla


class HGFileInfo(object):
    """File info from Mercurial

       We collect the different authors, reviewers and related bugs from the patches which touched to the file.
       The patches can be filtered according to pushdate.
    """

    def __init__(self, paths, channel='nightly', node='tip'):
        """Constructor

        Args:
            paths (List[str]): the paths
            channel (str): channel version of firefox
            node (Optional[str]): the node, by default 'tip'
        """
        self.channel = channel
        self.node = node
        self.data = {}
        self.paths = [paths] if isinstance(paths, six.string_types) else paths
        self.bug_pattern = re.compile('[\t ]*[Bb][Uu][Gg][\t ]*([0-9]+)')
        self.rev_pattern = re.compile('r=([a-zA-Z0-9]+)')
        self.__get_info()

    def get(self, path, utc_ts_from=None, utc_ts_to=None, author=None):
        if utc_ts_to is None:
            revision = hgmozilla.Revision.get_revision(self.channel, self.node)
            assert 'pushdate' in revision
            assert isinstance(revision['pushdate'], list)
            utc_ts_to = revision['pushdate'][0]

        self.conn.wait()

        entries = self.data[path]

        authors = {}
        bugs = set()
        patches = []

        for entry in entries:
            assert 'pushdate' in entry
            assert isinstance(entry['pushdate'], list)
            utc_date = entry['pushdate'][0]

            if (utc_ts_from is not None and utc_ts_from > utc_date) or utc_ts_to < utc_date:
                continue

            patch_author = entry['author']
            if author is not None and author != patch_author:
                continue

            if patch_author not in authors:
                authors[patch_author] = {'count': 1, 'reviewers': {}}
            else:
                authors[patch_author]['count'] += 1

            info_desc = self.__get_info_from_desc(entry['desc'])
            starter = info_desc['starter']
            if starter:
                bugs.add(info_desc['starter'])

            reviewers = info_desc['reviewers']
            if reviewers:
                _reviewers = authors[patch_author]['reviewers']
                for reviewer in reviewers:
                    if reviewer not in _reviewers:
                        _reviewers[reviewer] = 1
                    else:
                        _reviewers[reviewer] += 1

            patches.append(entry)

        return {
            'authors': authors,
            'bugs': bugs,
            'patches': patches,
        }

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
        __base = {'node': self.node,
                  'file': None}
        queries = []
        url = hgmozilla.FileInfo.get_url(self.channel)
        for path in self.paths:
            cparams = __base.copy()
            cparams['file'] = path
            queries.append(Query(url, cparams, handler=self.__handler, handlerdata=path))

        self.conn = hgmozilla.FileInfo(queries=queries)

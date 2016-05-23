# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from clouseau import hgmozilla
from clouseau.connection import Query


class RevisionTest(unittest.TestCase):

    def test_revision(self):
        rev = hgmozilla.Revision.get_revision()
        self.assertIsNotNone(rev)

    def test_revisions(self):
        data1 = {
            'first': {},
            'second': {},
        }
        data2 = {}

        def handler1(json, data):
            if 'tip' in json['tags']:
                data['first'].update(json)
            else:
                data['second'].update(json)

        def handler2(json, data):
            data.update(json)

        hgmozilla.Revision(queries=[
            Query(hgmozilla.Revision.get_url('nightly'), [{'node': 'tip'}, {'node': '1584ba8c1b86'}], handler1, data1),
            Query(hgmozilla.Revision.get_url('nightly'), {'node': 'tip'}, handler2, data2),
        ]).wait()

        self.assertTrue(data1['first'])
        self.assertTrue(data1['second']['node'].startswith('1584ba8c1b86'))
        self.assertTrue(data2)


class FileInfoTest(unittest.TestCase):

    def test_fileinfo(self):
        path = 'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
        info = hgmozilla.FileInfo.get(path)

        self.assertIsNotNone(info)
        self.assertIsNotNone(info['netwerk/protocol/http/nsHttpConnectionMgr.cpp'])

    def test_fileinfo_multiple_files(self):
        paths = ['netwerk/protocol/http/nsHttpConnectionMgr.cpp', 'netwerk/protocol/http/nsHttpConnectionMgr.h']
        info = hgmozilla.FileInfo.get(paths)

        self.assertIsNotNone(info)
        self.assertIsNotNone(info['netwerk/protocol/http/nsHttpConnectionMgr.cpp'])
        self.assertIsNotNone(info['netwerk/protocol/http/nsHttpConnectionMgr.h'])

    def test_fileinfo_release_channel(self):
        path = 'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
        info = hgmozilla.FileInfo.get(path, 'release')

        self.assertIsNotNone(info)
        self.assertIsNotNone(info['netwerk/protocol/http/nsHttpConnectionMgr.cpp'])


if __name__ == '__main__':
    unittest.main()

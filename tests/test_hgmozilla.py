# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from libmozdata import hgmozilla
from libmozdata.connection import Query


class RevisionTest(unittest.TestCase):
    def test_revision(self):
        rev = hgmozilla.Revision.get_revision()
        self.assertIn('pushid', rev)
        self.assertIn('pushuser', rev)
        self.assertIn('pushdate', rev)
        self.assertIn('user', rev)
        self.assertIn('branch', rev)
        self.assertIn('date', rev)
        self.assertIn('desc', rev)

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

        for rev in [data1['first'], data1['second'], data2]:
            self.assertIn('pushid', rev)
            self.assertIn('pushuser', rev)
            self.assertIn('pushdate', rev)
            self.assertIn('user', rev)
            self.assertIn('branch', rev)
            self.assertIn('date', rev)
            self.assertIn('desc', rev)
            self.assertIn('node', rev)

        self.assertEqual(data1['second']['node'], '1584ba8c1b86f9c4de5ccda5241cef36e80f042c')
        self.assertNotEqual(data1['first']['node'], data1['second']['node'])
        self.assertEqual(data1['first']['node'], data2['node'])


class RawRevisionTest(unittest.TestCase):
    def test_revision(self):
        rev = hgmozilla.RawRevision.get_revision('central', '1584ba8c1b86')
        self.assertIn('# Node ID 1584ba8c1b86f9c4de5ccda5241cef36e80f042c', rev)

    def test_revisions(self):
        data1 = {
            'first': None,
            'second': None,
        }
        data2 = {
            'first': None
        }

        def handler1(response):
            if '1584ba8c1b86' in response:
                data1['first'] = response
            elif 'f5578fdc50ef' in response:
                data1['second'] = response

        def handler2(response):
            data2['first'] = response

        hgmozilla.Revision(queries=[
            Query(hgmozilla.RawRevision.get_url('nightly'), [{'node': 'f5578fdc50ef'}, {'node': '1584ba8c1b86'}], handler1),
            Query(hgmozilla.RawRevision.get_url('nightly'), {'node': '1584ba8c1b86'}, handler2),
        ]).wait()

        self.assertIn('# Node ID 1584ba8c1b86f9c4de5ccda5241cef36e80f042c', data1['first'])
        self.assertIn('# Node ID f5578fdc50ef11b7f12451c88297f327abb0e9da', data1['second'])
        self.assertIn('# Node ID 1584ba8c1b86f9c4de5ccda5241cef36e80f042c', data2['first'])


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

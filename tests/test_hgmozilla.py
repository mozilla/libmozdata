# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import unittest
from libmozdata import hgmozilla
from libmozdata.connection import Query
import os
import tempfile
import time
import shutil

if sys.version_info < (3, 0):  # NOQA
    import mercurial  # NOQA
    from mercurial import hg, commands  # NOQA


class HGMozillaTest(unittest.TestCase):

    def create_repo(self, dest, ui):
        vct = 'http://hg.mozilla.org/hgcustom/version-control-tools'
        commands.clone(ui, vct, dest=os.path.join(dest, 'vct.hg'))

        ui.setconfig('extensions', 'pushlog', os.path.join(dest, 'vct.hg/hgext/pushlog'))
        ui.setconfig('extensions', 'hgmo', os.path.join(dest, 'vct.hg/hgext/hgmo'))

        srcdir = os.path.join(dest, 'test')
        destdir = os.path.join(dest, 'testwork')

        if not os.path.exists(srcdir):
            os.makedirs(srcdir)

        commands.init(ui, srcdir)
        commands.init(ui, destdir)

        repo = hg.repository(ui, destdir)

        myfile1 = os.path.join(destdir, 'myfile1')
        myfile2 = os.path.join(destdir, 'myfile2')
        for i in range(5):
            with open(myfile1, 'a') as In:
                In.write(str(i))
            with open(myfile2, 'a') as In:
                In.write(str(i))
            if i == 4:
                commands.commit(ui, repo, myfile1, myfile2, message='bug %d -- message, r=hwolowitz, r=affowler' % i, user='scooper@tbbt.com', addremove=True)
            else:
                commands.commit(ui, repo, myfile1, myfile2, message='message%d' % i, user='scooper@tbbt.com', addremove=True)
            commands.push(ui, repo, dest=srcdir)
            time.sleep(1.01)

        return srcdir

    def __getfilelog(self, hgmo):
        data = hgmo.get_filelog(['myfile1', 'myfile2'])
        self.assertIn('myfile1', data)
        self.assertIn('myfile2', data)
        self.assertEqual(len(data['myfile1']), 5)
        self.assertEqual(len(data['myfile2']), 5)
        self.assertIn('user', data['myfile2'][3])
        self.assertIn('desc', data['myfile2'][3])
        self.assertIn('node', data['myfile2'][3])
        self.assertIn('date', data['myfile2'][3])
        self.assertIn('pushdate', data['myfile2'][3])

        self.assertEqual(data['myfile2'][3]['user'], 'scooper@tbbt.com')
        self.assertEqual(data['myfile2'][3]['desc'], 'message1')
        self.assertIsInstance(data['myfile2'][3]['pushdate'], list)
        self.assertEqual(len(data['myfile2'][3]['pushdate']), 2)
        self.assertIsInstance(data['myfile2'][3]['date'], list)
        self.assertEqual(len(data['myfile2'][3]['date']), 2)
        self.assertIsInstance(data['myfile2'][3]['node'], str)

    def __getrevision(self, hgmo):
        data = hgmo.get_revision(node='tip')
        self.assertEqual(data['author'], 'scooper@tbbt.com')
        self.assertEqual(data['desc'], 'bug 4 -- message, r=hwolowitz, r=affowler')
        self.assertIsInstance(data['bugs'], list)
        self.assertEqual(len(data['bugs']), 1)
        self.assertEqual(data['bugs'][0]['no'], '4')
        self.assertEqual(data['bugs'][0]['url'], 'https://bugzilla.mozilla.org/show_bug.cgi?id=4')

        self.assertIsInstance(data['reviewers'], list)
        self.assertEqual(len(data['reviewers']), 2)
        self.assertEqual(data['reviewers'][0]['name'], 'hwolowitz')
        self.assertEqual(data['reviewers'][1]['name'], 'affowler')

    def test(self):
        if sys.version_info >= (3, 0):
            return

        try:
            tmpdst = tempfile.mkdtemp()
            ui = mercurial.ui.ui().copy()
            hgmo = hgmozilla.HGMozilla(self.create_repo(tmpdst, ui), ui=ui)
            self.__getfilelog(hgmo)
            self.__getrevision(hgmo)
        finally:
            shutil.rmtree(tmpdst)


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


class AnnotateTest(unittest.TestCase):

    def test_annotate(self):
        path = 'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
        info = hgmozilla.Annotate.get(path)

        self.assertIsNotNone(info)
        self.assertTrue(path in info)
        annotations = info[path]
        self.assertIsNotNone(annotations)
        self.assertTrue('abspath' in annotations)
        self.assertEqual(annotations['abspath'], path)
        self.assertTrue('annotate' in annotations)

    def test_annotate_multiple_files(self):
        paths = ['netwerk/protocol/http/nsHttpConnectionMgr.cpp',
                 'netwerk/protocol/http/nsHttpConnectionMgr.h']
        info = hgmozilla.Annotate.get(paths)

        self.assertIsNotNone(info)

        for path in paths:
            self.assertTrue(path in info)
            annotations = info[path]
            self.assertIsNotNone(annotations)
            self.assertTrue('abspath' in annotations)
            self.assertEqual(annotations['abspath'], path)
            self.assertTrue('annotate' in annotations)

    def test_annotate_release_channel(self):
        path = 'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
        info = hgmozilla.Annotate.get(path, 'release')

        self.assertIsNotNone(info)
        self.assertTrue(path in info)
        annotations = info[path]
        self.assertIsNotNone(annotations)
        self.assertTrue('abspath' in annotations)
        self.assertEqual(annotations['abspath'], path)
        self.assertTrue('annotate' in annotations)


if __name__ == '__main__':
    unittest.main()

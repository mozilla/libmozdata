# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import six
from libmozdata.FileStats import FileStats
from libmozdata import utils


class FileStatsTest(unittest.TestCase):

    def test_filestats(self):
        path = 'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
        info = FileStats(path).get_info()
        self.assertIsNotNone(info)
        self.assertEqual(info['path'], 'netwerk/protocol/http/nsHttpConnectionMgr.cpp')
        self.assertEqual(info['module'], 'Necko')
        six.assertCountEqual(self, info['components'], ['Core::Networking', 'Core::Networking: Cache', 'Core::Networking: Cookies', 'Core::Networking: FTP', 'Core::Networking: File', 'Core::Networking: HTTP', 'Core::Networking: JAR', 'Core::Networking: Websockets'])
        self.assertGreater(len(info['owners']), 0)
        self.assertGreater(len(info['peers']), 0)

    def test_filestats_no_bugs(self):
        path = 'LEGAL'
        info = FileStats(path).get_info()
        self.assertEqual(info['components'], set())
        self.assertIsNone(info['needinfo'])
        self.assertEqual(info['path'], path)
        self.assertEqual(len(info['guilty']['patches']), 1)
        self.assertEqual(info['guilty']['main_author'], 'hg@mozilla.com')
        self.assertEqual(info['guilty']['last_author'], 'hg@mozilla.com')
        self.assertNotIn('bugs', info)

    def test_filestats_date(self):
        path = 'LICENSE'
        info = FileStats(path, utc_ts=utils.get_timestamp('today')).get_info()
        self.assertEqual(info['components'], set())
        self.assertIsNotNone(info['needinfo'])
        self.assertEqual(info['path'], path)
        self.assertIsNone(info['guilty'])

        info = FileStats(path, utc_ts=utils.get_timestamp('2010-04-06')).get_info()
        self.assertEqual(info['infered_component'], 'Core::General')
        self.assertEqual(info['needinfo'], 'philringnalda@gmail.com')
        self.assertEqual(info['path'], path)
        self.assertEqual(len(info['guilty']['patches']), 1)
        self.assertEqual(info['guilty']['main_author'], 'philringnalda@gmail.com')
        self.assertEqual(info['guilty']['last_author'], 'philringnalda@gmail.com')
        self.assertEqual(info['bugs'], 1)

        self.assertEqual(info, FileStats(path, utc_ts=utils.get_timestamp('2010-04-07')).get_info())
        self.assertEqual(info, FileStats(path, utc_ts=utils.get_timestamp('2010-04-08')).get_info())

        info = FileStats(path, utc_ts=utils.get_timestamp('2010-04-09')).get_static_info()
        self.assertEqual(info['components'], set())
        self.assertIsNone(info['needinfo'])
        self.assertEqual(info['path'], path)
        self.assertIsNone(info['guilty'])
        self.assertNotIn('bugs', info)

        info = FileStats(path, utc_ts=utils.get_timestamp('2008-03-21')).get_info()
        self.assertEqual(info['infered_component'], 'Core::General')
        self.assertEqual(info['needinfo'], 'philringnalda@gmail.com')
        self.assertEqual(info['path'], path)
        self.assertEqual(len(info['guilty']['patches']), 1)
        self.assertEqual(info['guilty']['main_author'], 'hg@mozilla.com')
        self.assertEqual(info['guilty']['last_author'], 'hg@mozilla.com')
        self.assertEqual(info['bugs'], 1)


if __name__ == '__main__':
    unittest.main()

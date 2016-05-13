# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import six
from clouseau.FileStats import FileStats


class FileStatsTest(unittest.TestCase):

    def test_filestats(self):
        path = 'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
        info = FileStats(path).get_info()
        self.assertIsNot(info, None)
        self.assertEqual(info['path'], 'netwerk/protocol/http/nsHttpConnectionMgr.cpp')
        self.assertEqual(info['module'], 'Necko')
        six.assertCountEqual(self, info['components'], ['Core::Networking', 'Core::Networking: Cache', 'Core::Networking: Cookies', 'Core::Networking: FTP', 'Core::Networking: File', 'Core::Networking: HTTP', 'Core::Networking: JAR', 'Core::Networking: Websockets'])
        self.assertGreater(len(info['owners']), 0)
        self.assertGreater(len(info['peers']), 0)


if __name__ == '__main__':
    unittest.main()

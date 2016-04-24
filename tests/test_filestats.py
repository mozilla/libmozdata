# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from clouseau.FileStats import FileStats


class FileStatsTest(unittest.TestCase):

    def test_filestats(self):
        path = 'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
        info = FileStats(path).get_info()
        self.assertIsNot(info, None)


if __name__ == '__main__':
    unittest.main()

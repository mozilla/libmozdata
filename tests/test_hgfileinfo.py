# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from clouseau.HGFileInfo import HGFileInfo


class HGFileInfoTest(unittest.TestCase):

    def test_hgfileinfo(self):
        path = 'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
        fi = HGFileInfo(path).get()

        self.assertTrue(path in fi)
        self.assertTrue('authors' in fi[path])
        self.assertIsNot(fi[path]['authors'], None)
        self.assertTrue('bugs' in fi[path])
        self.assertIsNot(fi[path]['bugs'], None)


if __name__ == '__main__':
    unittest.main()

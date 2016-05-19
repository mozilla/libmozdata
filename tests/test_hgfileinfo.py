# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from clouseau.HGFileInfo import HGFileInfo


class HGFileInfoTest(unittest.TestCase):

    def test_hgfileinfo(self):
        path = 'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
        hi = HGFileInfo(path)
        fi = hi.get()

        self.assertTrue(path in fi)
        self.assertTrue('authors' in fi[path])
        self.assertIsNot(fi[path]['authors'], None)
        self.assertTrue('bugs' in fi[path])
        self.assertIsNot(fi[path]['bugs'], None)

    def test_hgfileinfo_multiple(self):
        path1 = 'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
        path2 = 'LICENSE'
        hi = HGFileInfo([path1, path2])
        fi = hi.get()

        self.assertTrue(path1 in fi)
        self.assertTrue(path2 in fi)
        self.assertTrue('authors' in fi[path1])
        self.assertTrue('authors' in fi[path2])
        self.assertIsNot(fi[path1]['authors'], None)
        self.assertIsNot(fi[path2]['authors'], None)
        self.assertTrue('bugs' in fi[path1])
        self.assertTrue('bugs' in fi[path2])
        self.assertIsNot(fi[path1]['bugs'], None)
        self.assertIsNot(fi[path2]['bugs'], None)


if __name__ == '__main__':
    unittest.main()

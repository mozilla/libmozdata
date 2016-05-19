# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from clouseau.HGFileInfo import HGFileInfo


class HGFileInfoTest(unittest.TestCase):

    def test_hgfileinfo(self):
        path = 'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
        hi = HGFileInfo(path)
        fi = hi.get(path)

        self.assertTrue('authors' in fi)
        self.assertIsNot(fi['authors'], None)
        self.assertTrue('bugs' in fi)
        self.assertIsNot(fi['bugs'], None)

    def test_hgfileinfo_multiple(self):
        path1 = 'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
        path2 = 'LICENSE'
        hi = HGFileInfo([path1, path2])
        fi1 = hi.get(path1)
        fi2 = hi.get(path2)

        self.assertTrue('authors' in fi1)
        self.assertTrue('authors' in fi2)
        self.assertIsNot(fi1['authors'], None)
        self.assertIsNot(fi2['authors'], None)
        self.assertTrue('bugs' in fi1)
        self.assertTrue('bugs' in fi2)
        self.assertIsNot(fi1['bugs'], None)
        self.assertIsNot(fi2['bugs'], None)


if __name__ == '__main__':
    unittest.main()

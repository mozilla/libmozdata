# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from clouseau import hgmozilla


class RevisionTest(unittest.TestCase):

    def test_revision(self):
        rev = hgmozilla.Revision.get_revision()
        self.assertIsNot(rev, None)


class FileInfoTest(unittest.TestCase):

    def test_fileinfo(self):
        path = 'netwerk/protocol/http/nsHttpConnectionMgr.cpp'
        info = hgmozilla.FileInfo.get(path)

        self.assertIsNot(info, None)


if __name__ == '__main__':
    unittest.main()

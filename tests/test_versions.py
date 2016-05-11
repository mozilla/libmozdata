# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import clouseau.versions as versions


class VersionsTest(unittest.TestCase):

    def test_versions(self):
        v = versions.get(base=True)
        self.assertTrue(v['release'] < v['beta'] < v['aurora'] < v['nightly'])


if __name__ == '__main__':
    unittest.main()

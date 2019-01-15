# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from libmozdata import release_owners as ro


class ReleaseOwnersTest(unittest.TestCase):
    def test_ro(self):
        owners = ro.get_owners()
        self.assertIsNotNone(owners)


if __name__ == '__main__':
    unittest.main()

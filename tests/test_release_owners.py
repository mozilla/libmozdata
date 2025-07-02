# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from libmozdata import release_owners as ro
from libmozdata.wiki_parser import InvalidWiki


class ReleaseOwnersTest(unittest.TestCase):
    def test_ro(self):
        # The wiki hosting release owners table may provide 403 to CI tasks
        try:
            owners = ro.get_owners()
        except InvalidWiki as e:
            if str(e) == "Failed to load wiki data":
                self.skipTest("Wiki data not available")
            else:
                raise

        self.assertIsNotNone(owners)


if __name__ == "__main__":
    unittest.main()

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from datetime import timedelta
from libmozdata.redash import Redash
import libmozdata.socorro as socorro
import libmozdata.utils as utils
import libmozdata.versions


class RedashTest(unittest.TestCase):
    def test_redash(self):
        if not Redash.TOKEN:
            return

        versions = libmozdata.versions.get()

        end_date = utils.get_date_ymd('yesterday')
        start_date = utils.get_date_ymd(end_date - timedelta(10))

        for channel in ['release', 'beta', 'nightly']:
            khours = Redash.get_khours(start_date, end_date, channel, [versions[channel]], 'Firefox')
            self.assertEqual(len(khours), 11)
            for i in range(11):
                self.assertIn(start_date + timedelta(i), khours)


if __name__ == '__main__':
    unittest.main()

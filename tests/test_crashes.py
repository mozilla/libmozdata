# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import os
from clouseau.stability import crashes
from clouseau.redash import Redash


class CrashesTest(unittest.TestCase):

    def test_crashes(self):
        tok = os.environ.get('API_KEY_346')
        if tok:
            Redash.TOKEN = tok
        stats = crashes.get('release', 'yesterday', versions=46, duration=11, tc_limit=50)

        self.assertIn('start_date', stats)
        self.assertIn('end_date', stats)
        self.assertIn('versions', stats)
        self.assertIn('adi', stats)
        self.assertIn('khours', stats)
        self.assertIn('crash_by_day', stats)
        self.assertIn('throttle', stats)
        for sign in stats['signatures'].values():
            self.assertIn('bugs', sign)
            self.assertIn('startup_percent', sign)
            self.assertIn('tc_rank', sign)
            self.assertIn('crash_count', sign)
            self.assertIn('crash_by_day', sign)


if __name__ == '__main__':
    unittest.main()
